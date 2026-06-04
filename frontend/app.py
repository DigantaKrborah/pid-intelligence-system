import streamlit as st
from frontend.utils.api_client import (
    get_units, create_unit, get_unit_stats, set_selected_unit,
    get_health, report_bug,
)

st.set_page_config(
    page_title="P&ID Intelligence System",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ P&ID Intel")

    # Backend health indicator
    health = get_health()
    h_status = health.get("status", "unreachable")
    st.caption(f"API: {'🟢 Online' if h_status == 'ok' else '🟡 Degraded' if h_status == 'degraded' else '🔴 Offline'}")
    st.divider()

    # Unit selector
    units = get_units()
    unit_names = [u["name"] for u in units]
    unit_map = {u["name"]: u for u in units}

    prev_unit = st.session_state.get("selected_unit", "— Select Unit —")
    options = ["— Select Unit —"] + unit_names
    default_idx = options.index(prev_unit) if prev_unit in options else 0

    selected_name = st.selectbox("Process Unit", options, index=default_idx, label_visibility="collapsed")

    if selected_name != "— Select Unit —" and selected_name in unit_map:
        set_selected_unit(unit_map[selected_name])
    elif selected_name == "— Select Unit —":
        st.session_state.pop("selected_unit_obj", None)

    if st.button("＋ New Unit", use_container_width=True):
        st.session_state["show_create_unit"] = True

    st.divider()
    st.page_link("pages/1_upload.py",    label="📤 Upload P&IDs")
    st.page_link("pages/2_search.py",    label="🔍 Search Tags")
    st.page_link("pages/3_graph.py",     label="🕸️ Process Graph")
    st.page_link("pages/4_chat.py",      label="💬 Ask a Question")
    st.page_link("pages/5_documents.py", label="📄 Documents")
    st.page_link("pages/6_incidents.py", label="🚨 Incidents")

    st.divider()
    if st.button("🐛 Report Bug", use_container_width=True):
        st.session_state["show_bug_report"] = True

# ── Main Content ───────────────────────────────────────────────────────────────
unit_obj = st.session_state.get("selected_unit_obj")

if not unit_obj:
    st.header("Welcome to P&ID Intelligence System")
    st.info("👈 Select a process unit from the sidebar to get started.")

    # Global summary
    total_tags = sum(u.get("tag_count", 0) for u in units)
    total_docs = sum(u.get("document_count", 0) for u in units)
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Units", len(units))
    c2.metric("Total Tags", total_tags)
    c3.metric("P&ID Sheets", total_docs)

    if units:
        st.subheader("Available Units")
        for u in units:
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                col1.markdown(f"**{u['name']}** — {u.get('display_name', '')}")
                col2.metric("Tags", u.get("tag_count", 0))
                col3.metric("Sheets", u.get("document_count", 0))
                if col4.button("Open", key=f"open_{u['id']}"):
                    set_selected_unit(u)
                    st.rerun()
else:
    unit_id = unit_obj["id"]
    unit_name = unit_obj["name"]

    stats = get_unit_stats(unit_id)

    st.header(f"⚙️ {unit_name}")
    st.caption(stats.get("unit_name", unit_name))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Equipment Tags",  stats.get("total_tags", "—"))
    c2.metric("P&ID Sheets",     stats.get("total_documents", "—"))
    c3.metric("SOPs Indexed",    stats.get("total_sop_documents", "—"))
    c4.metric("Graph Nodes",     stats.get("graph_node_count", "—"))

    col_left, col_right = st.columns([2, 1])
    with col_left:
        st.subheader("Quick Actions")
        qa1, qa2, qa3 = st.columns(3)
        if qa1.button("📤 Upload P&IDs", use_container_width=True):
            st.switch_page("pages/1_upload.py")
        if qa2.button("🔍 Search Tags", use_container_width=True):
            st.switch_page("pages/2_search.py")
        if qa3.button("💬 Ask a Question", use_container_width=True):
            st.switch_page("pages/4_chat.py")

    with col_right:
        st.subheader("Graph")
        g1, g2 = st.columns(2)
        g1.metric("Nodes", stats.get("graph_node_count", 0))
        g2.metric("Edges", stats.get("graph_edge_count", 0))
        if st.button("🕸️ View Graph", use_container_width=True):
            st.switch_page("pages/3_graph.py")

# ── Create Unit Dialog ─────────────────────────────────────────────────────────
if st.session_state.get("show_create_unit"):
    with st.form("create_unit_form"):
        st.subheader("Create New Process Unit")
        name = st.text_input("Unit Name *", placeholder="e.g. CDU, VDU, HCU")
        description = st.text_area("Description (optional)")
        col_s, col_c = st.columns(2)
        submitted = col_s.form_submit_button("✅ Create", type="primary", use_container_width=True)
        cancelled = col_c.form_submit_button("Cancel", use_container_width=True)

        if cancelled:
            st.session_state["show_create_unit"] = False
            st.rerun()
        if submitted:
            if not name.strip():
                st.error("Unit name is required.")
            else:
                ok, result = create_unit(name.strip(), description)
                if ok:
                    st.success(f"Unit **{name.upper()}** created!")
                    st.session_state["show_create_unit"] = False
                    st.rerun()
                else:
                    st.error(f"Error: {result}")

# ── Bug Report Dialog ──────────────────────────────────────────────────────────
if st.session_state.get("show_bug_report"):
    with st.form("bug_report_form"):
        st.subheader("🐛 Report a Bug")
        component = st.selectbox("Component", [
            "PDF Upload & Processing", "Tag Extraction", "Knowledge Graph",
            "Natural Language Query", "Equipment Search", "Graph Visualisation",
            "Documents", "Frontend (UI)", "Backend API", "Other",
        ])
        severity = st.selectbox("Severity", ["High", "Medium", "Low", "Critical"])
        description = st.text_area("What went wrong? *")
        steps = st.text_area("Steps to reproduce")
        col_s, col_c = st.columns(2)
        submitted = col_s.form_submit_button("Submit", type="primary", use_container_width=True)
        cancelled = col_c.form_submit_button("Cancel", use_container_width=True)

        if cancelled:
            st.session_state["show_bug_report"] = False
            st.rerun()
        if submitted and description:
            ok, url = report_bug(
                component=component, description=description, steps=steps,
                severity=severity.lower(),
                unit_name=unit_obj["name"] if unit_obj else None,
                page="Dashboard",
            )
            if ok and url:
                st.success(f"Bug reported! [View issue]({url})")
            else:
                st.info(url or "Bug report submitted.")
            st.session_state["show_bug_report"] = False
