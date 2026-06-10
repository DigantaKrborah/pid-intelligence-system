import time
import streamlit as st
from frontend.utils.api_client import (
    require_unit, upload_pid_files, get_upload_status,
    list_all_documents, delete_document,
)
from frontend.utils.styles import (
    inject_css, upload_file_row, processing_row, section_title, card_wrap, status_badge,
)

st.set_page_config(page_title="Upload P&IDs", layout="wide")
inject_css()
st.markdown("# 📤 Upload P&ID Sheets")

unit      = require_unit()
unit_id   = unit["id"]
unit_name = unit["name"]
st.caption(f"Unit: **{unit_name}**")

# ── Managed drawings ──────────────────────────────────────────────────────────
st.markdown(section_title("Uploaded Drawings"), unsafe_allow_html=True)

docs = list_all_documents(unit_id)
if not docs:
    st.info("No drawings uploaded yet for this unit.")
else:
    for doc in docs:
        with st.container(border=True):
            col_info, col_meta, col_del = st.columns([5, 3, 1])

            col_info.markdown(
                f'<p style="margin:0;font-family:\'Roboto Mono\',monospace;'
                f'font-size:12px;font-weight:600;color:#0F172A;word-break:break-all">'
                f'{doc["filename"]}</p>',
                unsafe_allow_html=True,
            )

            with col_meta:
                st.markdown(status_badge(doc["processing_status"]), unsafe_allow_html=True)
                st.caption(f'{doc["tags_extracted"]} tags &nbsp;·&nbsp; {doc["page_count"]} pages')

            with col_del:
                if st.button(
                    "🗑️ Delete",
                    key=f"del_{doc['document_id']}",
                    help=f"Delete {doc['filename']}",
                    use_container_width=True,
                ):
                    ok, msg = delete_document(doc["document_id"])
                    if ok:
                        st.success(f"Deleted **{msg}**")
                        st.rerun()
                    else:
                        st.error(f"Delete failed: {msg}")

st.divider()

# ── Upload new drawings ───────────────────────────────────────────────────────
st.markdown(section_title("Upload New Drawings"), unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "Drop P&ID PDF files here",
    type=["pdf"],
    accept_multiple_files=True,
    help="PDF only · Max 50 MB per file",
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

    header = (
        '<div style="display:flex;justify-content:space-between;padding:8px 14px;'
        'background:#F8FAFC;border-radius:8px 8px 0 0;border:1px solid #E2E8F0;border-bottom:none">'
        '<span style="font-size:11px;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:.05em">Filename</span>'
        '<span style="font-size:11px;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:.05em">Size</span>'
        '<span style="font-size:11px;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:.05em">Status</span>'
        '</div>'
    )
    st.markdown(header + card_wrap(rows_html), unsafe_allow_html=True)
    st.markdown("")

    if valid_files and st.button("🚀 Upload & Process", type="primary"):
        st.markdown(section_title("Uploading"), unsafe_allow_html=True)
        bar     = st.progress(0)
        doc_ids = []
        results = upload_pid_files(unit_id, valid_files)

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
            st.caption("Auto-refreshes every 5 s.")
            status_slots = {fname: st.empty() for fname, _ in doc_ids}
            max_polls    = 24

            for _ in range(max_polls):
                all_done   = True
                table_html = ""
                for fname, doc_id in doc_ids:
                    s           = get_upload_status(doc_id)
                    proc_status = s.get("status", "unknown")
                    tags        = s.get("tags_extracted", 0)
                    pages       = s.get("page_count") or "?"
                    table_html += processing_row(fname, proc_status, tags, str(pages))
                    if proc_status not in ("completed", "failed"):
                        all_done = False
                list(status_slots.values())[0].markdown(card_wrap(table_html), unsafe_allow_html=True)
                for slot in list(status_slots.values())[1:]:
                    slot.empty()
                if all_done:
                    st.success("✅ All files processed!")
                    st.rerun()
                    break
                time.sleep(5)
                st.rerun()
