import streamlit as st
from frontend.utils.api_client import (
    require_unit, upload_document, list_documents, search_documents,
)

st.set_page_config(page_title="Documents", layout="wide")
st.title("📄 SOPs & Manuals")

unit = require_unit()
unit_id   = unit["id"]
unit_name = unit["name"]

st.caption(f"Unit: **{unit_name}**")

# ── Upload ────────────────────────────────────────────────────────────────────
with st.expander("📤 Upload a Document", expanded=False):
    col1, col2 = st.columns([3, 1])
    with col1:
        doc_file = st.file_uploader("PDF or DOCX", type=["pdf", "docx"])
    with col2:
        doc_type = st.selectbox("Type", ["SOP", "Manual", "Procedure", "Datasheet", "Standard"])

    if doc_file and st.button("Upload & Index", type="primary"):
        with st.spinner(f"Uploading {doc_file.name}..."):
            ok, data = upload_document(unit_id, doc_type, doc_file)
        if ok:
            st.success(f"✅ **{doc_file.name}** uploaded — indexing in background.")
            st.rerun()
        else:
            st.error(f"Upload failed: {data.get('detail', data.get('error', 'Unknown'))}")

st.divider()

# ── Search ────────────────────────────────────────────────────────────────────
search_q = st.text_input("🔍 Search documents", placeholder="startup procedure, pressure relief, isolation valve...")

if search_q:
    with st.spinner("Searching..."):
        results = search_documents(search_q, unit_id)
    if results:
        st.subheader(f"{len(results)} result(s)")
        for r in results:
            with st.container(border=True):
                st.markdown(f"**📄 {r.get('source', 'Unknown')}** · page {r.get('page', '?')} · `{r.get('unit', '')}`")
                st.write(r.get("content", "")[:300] + "…")
    else:
        st.info("No matching sections found. Try different keywords.")

st.divider()

# ── Document list ─────────────────────────────────────────────────────────────
st.subheader("Indexed Documents")

docs = list_documents(unit_id)

if not docs:
    st.info("No documents uploaded yet for this unit. Upload SOPs and manuals above.")
else:
    col_h1, col_h2, col_h3, col_h4, col_h5 = st.columns([3, 1, 1, 1, 1])
    col_h1.markdown("**Filename**")
    col_h2.markdown("**Type**")
    col_h3.markdown("**Pages**")
    col_h4.markdown("**Chunks**")
    col_h5.markdown("**Indexed**")

    for d in docs:
        c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
        c1.text(d.get("filename", "—"))
        c2.text(d.get("doc_type", "—"))
        c3.text(str(d.get("page_count") or "—"))
        c4.text(str(d.get("chunk_count") or "—"))
        c5.markdown("✅" if d.get("indexed") else "⏳")
