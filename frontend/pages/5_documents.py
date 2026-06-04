import streamlit as st
import httpx
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Documents", layout="wide")
st.title("📄 SOPs & Manuals")

unit = st.session_state.get("selected_unit")
if not unit:
    st.warning("Select a unit first.")
    st.stop()

st.caption(f"Unit: **{unit}**")

# ── Upload Section ─────────────────────────────────────────────────────────────
with st.expander("📤 Upload a Document", expanded=True):
    col1, col2 = st.columns([3, 1])
    with col1:
        doc_file = st.file_uploader("SOP / Manual / Datasheet", type=["pdf", "docx"])
    with col2:
        doc_type = st.selectbox("Document Type", ["SOP", "Manual", "Procedure", "Datasheet", "Standard"])

    if doc_file and st.button("Upload & Index", type="primary"):
        unit_id_placeholder = "00000000-0000-0000-0000-000000000001"
        with st.spinner(f"Uploading {doc_file.name}..."):
            try:
                resp = httpx.post(
                    f"{BACKEND_URL}/api/v1/upload/document",
                    data={"unit_id": unit_id_placeholder, "doc_type": doc_type},
                    files={"file": (doc_file.name, doc_file.read(), "application/octet-stream")},
                    timeout=30,
                )
                if resp.status_code == 200:
                    st.success(f"✅ {doc_file.name} uploaded and queued for indexing")
                else:
                    st.error(f"Upload failed: {resp.text}")
            except Exception as e:
                st.error(f"Backend unreachable: {e}")

st.divider()

# ── Document Search ────────────────────────────────────────────────────────────
search_q = st.text_input("🔍 Search documents", placeholder="startup procedure, pressure relief, isolation...")

st.subheader("Indexed Documents")

# TODO: fetch real document list from API
st.info("No documents indexed yet for this unit. Upload SOPs and manuals above.")
