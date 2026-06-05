import streamlit as st
from frontend.utils.api_client import (
    require_unit, upload_document, list_documents, search_documents,
)
from frontend.utils.styles import inject_css, doc_row, section_title, card_wrap, table_header

st.set_page_config(page_title="Documents", layout="wide")
inject_css()
st.markdown("# 📄 SOPs & Manuals")

unit      = require_unit()
unit_id   = unit["id"]
unit_name = unit["name"]
st.caption(f"Unit: **{unit_name}**")

# ── Upload ────────────────────────────────────────────────────────────────────
with st.expander("📤 Upload a Document"):
    c1, c2 = st.columns([3, 1])
    with c1: doc_file = st.file_uploader("PDF or DOCX", type=["pdf", "docx"])
    with c2: doc_type = st.selectbox("Type", ["SOP", "Manual", "Procedure", "Datasheet", "Standard"])
    if doc_file and st.button("Upload & Index", type="primary"):
        with st.spinner(f"Uploading {doc_file.name}…"):
            ok, data = upload_document(unit_id, doc_type, doc_file)
        if ok:
            st.success(f"✅ **{doc_file.name}** uploaded — indexing in background."); st.rerun()
        else:
            st.error(f"Upload failed: {data.get('detail', data.get('error', 'Unknown'))}")

st.divider()

# ── Semantic search ───────────────────────────────────────────────────────────
search_q = st.text_input("🔍 Search documents", placeholder="startup procedure, pressure relief, isolation valve…")
if search_q:
    with st.spinner("Searching…"):
        hits = search_documents(search_q, unit_id)
    if hits:
        st.markdown(section_title(f"{len(hits)} result(s)"), unsafe_allow_html=True)
        for h in hits:
            with st.container(border=True):
                st.markdown(
                    f'<div style="font-size:12px;color:#94A3B8;margin-bottom:4px">'
                    f'📄 <strong style="color:#F1F5F9">{h.get("source","")}</strong>'
                    f' · page {h.get("page","?")} · <code style="font-size:11px">{h.get("unit","")}</code></div>'
                    f'<div style="font-size:13px;color:#CBD5E1;line-height:1.6">{h.get("content","")[:280]}…</div>',
                    unsafe_allow_html=True,
                )
    else:
        st.info("No matching sections found. Try different keywords.")

st.divider()

# ── Document list ─────────────────────────────────────────────────────────────
st.markdown(section_title("Indexed Documents"), unsafe_allow_html=True)
docs = list_documents(unit_id)

if not docs:
    st.info("No documents uploaded yet for this unit.")
else:
    header_html = table_header("Filename", "Type", "Pages", "Chunks", "Indexed")
    rows_html   = "".join(doc_row(d) for d in docs)
    st.markdown(header_html + card_wrap(rows_html), unsafe_allow_html=True)
