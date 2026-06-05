import time
import streamlit as st
from frontend.utils.api_client import require_unit, upload_pid_files, get_upload_status
from frontend.utils.styles import inject_css, upload_file_row, processing_row, section_title, card_wrap

st.set_page_config(page_title="Upload P&IDs", layout="wide")
inject_css()
st.markdown("# 📤 Upload P&ID Sheets")

unit      = require_unit()
unit_id   = unit["id"]
unit_name = unit["name"]
st.caption(f"Unit: **{unit_name}**")

uploaded_files = st.file_uploader(
    "Drop P&ID PDF files here",
    type=["pdf"],
    accept_multiple_files=True,
    help="PDF only · Max 50 MB per file · Up to 50 files",
)

if uploaded_files:
    valid_files = []
    rows_html   = ""
    for f in uploaded_files:
        size_mb = f.size / (1024 * 1024)
        valid   = size_mb <= 50
        rows_html += upload_file_row(f.name, size_mb, valid)
        if valid:
            valid_files.append(f)

    # Styled file table
    header = (
        '<div style="display:flex;justify-content:space-between;padding:8px 14px;'
        'background:#262B3D;border-radius:8px 8px 0 0;border:1px solid #2D3748;border-bottom:none">'
        '<span style="font-size:11px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:.05em">Filename</span>'
        '<span style="font-size:11px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:.05em">Size</span>'
        '<span style="font-size:11px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:.05em">Status</span>'
        '</div>'
    )
    st.markdown(header + card_wrap(rows_html), unsafe_allow_html=True)
    st.markdown("")

    if valid_files and st.button("🚀 Upload & Process", type="primary"):
        st.markdown(section_title("Uploading"), unsafe_allow_html=True)
        bar      = st.progress(0)
        doc_ids  = []
        results  = upload_pid_files(unit_id, valid_files)

        for i, r in enumerate(results):
            bar.progress((i + 1) / len(results))
            if r["status"] == 200:
                doc_id = r["data"].get("files", [{}])[0].get("document_id")
                if doc_id:
                    doc_ids.append((r["filename"], doc_id))
            else:
                st.error(f"❌ {r['filename']} — {r['data'].get('detail', 'Upload error')}")

        if doc_ids:
            st.markdown(section_title("Processing Status"), unsafe_allow_html=True)
            st.caption("Auto-refreshes every 5 s. You can close this tab — processing continues in the background.")

            status_slots = {fname: st.empty() for fname, _ in doc_ids}
            max_polls    = 24

            for _ in range(max_polls):
                all_done   = True
                table_html = ""
                for fname, doc_id in doc_ids:
                    s          = get_upload_status(doc_id)
                    proc_status= s.get("status", "unknown")
                    tags       = s.get("tags_extracted", 0)
                    pages      = s.get("page_count") or "?"
                    table_html += processing_row(fname, proc_status, tags, str(pages))
                    if proc_status not in ("completed", "failed"):
                        all_done = False

                # Render all rows in one HTML block
                list(status_slots.values())[0].markdown(
                    card_wrap(table_html), unsafe_allow_html=True
                )
                # Clear other slots
                for slot in list(status_slots.values())[1:]:
                    slot.empty()

                if all_done:
                    st.success("✅ All files processed!")
                    break
                time.sleep(5)
                st.rerun()
