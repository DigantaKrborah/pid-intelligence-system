import streamlit as st
import httpx
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="P&ID Intelligence System",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ P&ID Intel")
    st.divider()

    # Unit selector
    st.subheader("Process Unit")
    unit_options = ["— Select Unit —"]
    try:
        resp = httpx.get(f"{BACKEND_URL}/api/v1/units/", timeout=3)
        if resp.status_code == 200:
            units = resp.json()
            unit_options += [u["name"] for u in units]
    except Exception:
        pass

    selected_unit = st.selectbox("Unit", unit_options, label_visibility="collapsed")
    if st.button("＋ New Unit", use_container_width=True):
        st.session_state["show_create_unit"] = True

    st.divider()
    st.page_link("pages/1_upload.py",   label="📤 Upload P&IDs",    icon="📤")
    st.page_link("pages/2_search.py",   label="🔍 Search Tags",     icon="🔍")
    st.page_link("pages/3_graph.py",    label="🕸️ Process Graph",   icon="🕸️")
    st.page_link("pages/4_chat.py",     label="💬 Ask a Question",  icon="💬")
    st.page_link("pages/5_documents.py",label="📄 Documents",       icon="📄")

    st.divider()
    if st.button("🐛 Report Bug", use_container_width=True):
        st.session_state["show_bug_report"] = True

# ── Main Content ───────────────────────────────────────────────────────────────
if selected_unit == "— Select Unit —":
    st.header("Welcome to P&ID Intelligence System")
    st.info("👈 Select a process unit from the sidebar to get started, or create a new one.")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Units", "—")
    col2.metric("Total Tags", "—")
    col3.metric("Documents Indexed", "—")
else:
    st.session_state["selected_unit"] = selected_unit
    st.header(f"⚙️ {selected_unit}")
    st.caption(f"Process Unit — {selected_unit}")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Equipment Tags", "—")
    col2.metric("P&ID Sheets", "—")
    col3.metric("SOPs Indexed", "—")
    col4.metric("Processing Queue", "—")

    st.subheader("Recent Uploads")
    st.info("Upload P&ID PDFs to get started →  **Upload P&IDs** in the sidebar.")

# ── Create Unit Modal ──────────────────────────────────────────────────────────
if st.session_state.get("show_create_unit"):
    with st.form("create_unit_form"):
        st.subheader("Create New Process Unit")
        name = st.text_input("Unit Name", placeholder="e.g. CDU, VDU, HCU")
        description = st.text_area("Description (optional)")
        submitted = st.form_submit_button("Create Unit")
        if submitted and name:
            try:
                r = httpx.post(
                    f"{BACKEND_URL}/api/v1/units/",
                    json={"name": name.upper(), "description": description},
                    timeout=5,
                )
                if r.status_code == 201:
                    st.success(f"Unit {name.upper()} created!")
                    st.session_state["show_create_unit"] = False
                    st.rerun()
                else:
                    st.error(f"Error: {r.text}")
            except Exception as e:
                st.error(f"Backend unreachable: {e}")
