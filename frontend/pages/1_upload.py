import time
import streamlit as st
from frontend.utils.api_client import require_unit, upload_pid_files, get_upload_status

st.set_page_config(page_title="Upload P&IDs", layout="wide")
st.title("📤 Upload P&ID Sheets")

unit = require_unit()
unit_id   = unit["id"]
unit_name = unit["name"]

st.caption(f"Unit: **{unit_name}**")

uploaded_files = st.file_uploader(
    "Drop P&ID PDF files here",
    type=["pdf"],
    accept_multiple_files=True,
    help="Max 50 MB per file. Up to 50 files at once.",
)

if uploaded_files:
    st.write(f"**{len(uploaded_files)} file(s) selected:**")
    col_h1, col_h2, col_h3 = st.columns([4, 1, 1])
    col_h1.markdown("**Filename**")
    col_h2.markdown("**Size**")
    col_h3.markdown("**Status**")

    valid_files = []
    for f in uploaded_files:
        size_mb = f.size / (1024 * 1024)
        col1, col2, col3 = st.columns([4, 1, 1])
        col1.text(f.name)
        col2.text(f"{size_mb:.1f} MB")
        if size_mb > 50:
            col3.markdown("⚠️ Too large")
        else:
            col3.markdown("✅ Ready")
            valid_files.append(f)

    if valid_files and st.button("🚀 Upload & Process", type="primary"):
        st.divider()
        st.subheader("Upload Progress")
        progress_bar = st.progress(0)
        status_area  = st.empty()
        doc_ids = []

        results = upload_pid_files(unit_id, valid_files)

        for i, r in enumerate(results):
            progress_bar.progress((i + 1) / len(results))
            if r["status"] == 200:
                doc_id = r["data"].get("files", [{}])[0].get("document_id")
                if doc_id:
                    doc_ids.append((r["filename"], doc_id))
                status_area.success(f"✅ {r['filename']} — queued")
            else:
                status_area.error(f"❌ {r['filename']} — {r['data'].get('detail', 'Error')}")

        # Poll processing status
        if doc_ids:
            st.divider()
            st.subheader("Processing Status")
            st.caption("Refreshes every 5 seconds. Close this tab when done — processing continues in the background.")

            status_slots = {fname: st.empty() for fname, _ in doc_ids}
            max_polls = 24   # 2 minutes max

            for _ in range(max_polls):
                all_done = True
                for fname, doc_id in doc_ids:
                    s = get_upload_status(doc_id)
                    proc_status = s.get("status", "unknown")
                    tags = s.get("tags_extracted", 0)
                    pages = s.get("page_count") or "?"

                    badge = {
                        "queued":        "⏳ Queued",
                        "processing":    "🔄 Processing...",
                        "extracting":    "🔍 Extracting tags...",
                        "building_graph":"🕸️ Building graph...",
                        "completed":     f"✅ Done — {tags} tags from {pages} pages",
                        "failed":        f"❌ Failed: {s.get('error', '')}",
                    }.get(proc_status, f"⏳ {proc_status}")

                    status_slots[fname].markdown(f"**{fname}** — {badge}")

                    if proc_status not in ("completed", "failed"):
                        all_done = False

                if all_done:
                    st.success("All files processed!")
                    break
                time.sleep(5)
                st.rerun()
