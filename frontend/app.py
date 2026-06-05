import streamlit as st
from frontend.utils.api_client import (
    get_units, create_unit, get_unit_stats, set_selected_unit,
    get_health, report_bug,
)
from frontend.utils.styles import inject_css, status_badge, section_title

st.set_page_config(
    page_title="P&ID Intelligence System",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ P&ID Intel")
    health = get_health()
    h_status = health.get("status", "unreachable")
    colour   = {"ok": "🟢", "degraded": "🟡"}.get(h_status, "🔴")
    label    = {"ok": "Online", "degraded": "Degraded"}.get(h_status, "Offline")
    st.markdown(
        f'<div class="pid-health" style="color:#94A3B8;font-size:11px;padding-bottom:8px">'
        f'{colour} API {label}</div>',
        unsafe_allow_html=True,
    )
    st.divider()

    units    = get_units()
    unit_map = {u["name"]: u for u in units}
    prev     = st.session_state.get("selected_unit", "— Select Unit —")
    options  = ["— Select Unit —"] + list(unit_map)
    idx      = options.index(prev) if prev in options else 0

    selected_name = st.selectbox("Unit", options, index=idx, label_visibility="collapsed")
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

# ── Main content ───────────────────────────────────────────────────────────────
unit_obj = st.session_state.get("selected_unit_obj")

if not unit_obj:
    st.markdown("# Welcome to P&ID Intelligence System")
    st.info("👈 Select a process unit from the sidebar to get started.")

    total_tags = sum(u.get("tag_count", 0) for u in units)
    total_docs = sum(u.get("document_count", 0) for u in units)
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Units",  len(units))
    c2.metric("Total Tags",   total_tags)
    c3.metric("P&ID Sheets",  total_docs)

    if units:
        st.markdown(section_title("Available Units"), unsafe_allow_html=True)
        for u in units:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                c1.markdown(
                    f'<span style="font-weight:700;font-size:15px">{u["name"]}</span> '
                    f'<span style="color:#94A3B8;font-size:12px">{u.get("display_name","")}</span>',
                    unsafe_allow_html=True,
                )
                c2.metric("Tags",   u.get("tag_count", 0))
                c3.metric("Sheets", u.get("document_count", 0))
                if c4.button("Open →", key=f"open_{u['id']}", type="primary"):
                    set_selected_unit(u)
                    st.rerun()
else:
    unit_id   = unit_obj["id"]
    unit_name = unit_obj["name"]
    stats     = get_unit_stats(unit_id)

    st.markdown(f"# ⚙️ {unit_name}")
    st.caption(stats.get("unit_name", unit_name))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Equipment Tags", stats.get("total_tags",         "—"))
    c2.metric("P&ID Sheets",    stats.get("total_documents",    "—"))
    c3.metric("SOPs Indexed",   stats.get("total_sop_documents","—"))
    c4.metric("Graph Nodes",    stats.get("graph_node_count",   "—"))

    col_l, col_r = st.columns([2, 1])
    with col_l:
        st.markdown(section_title("Quick Actions"), unsafe_allow_html=True)
        q1, q2, q3 = st.columns(3)
        if q1.button("📤 Upload P&IDs",  use_container_width=True, type="primary"):
            st.switch_page("pages/1_upload.py")
        if q2.button("🔍 Search Tags",   use_container_width=True):
            st.switch_page("pages/2_search.py")
        if q3.button("💬 Ask a Question",use_container_width=True):
            st.switch_page("pages/4_chat.py")

        # Recent uploads table
        from frontend.utils.api_client import _get
        _, docs_raw = _get(f"/api/v1/upload/status/recent?unit_id={unit_id}&limit=5")
        recent = docs_raw if isinstance(docs_raw, list) else []

        if recent:
            st.markdown(section_title("Recent Uploads"), unsafe_allow_html=True)
            rows_html = "".join(
                f'<div style="display:flex;align-items:center;justify-content:space-between;'
                f'padding:9px 14px;background:#1E2130;border-bottom:1px solid #2D3748">'
                f'<code style="font-family:Roboto Mono,monospace;font-size:12px;color:#F1F5F9;'
                f'background:transparent;padding:0;border:none">{d.get("filename","")}</code>'
                f'<span style="font-size:11px;color:#94A3B8">{d.get("page_count") or "—"} pages</span>'
                f'{status_badge(d.get("processing_status","pending"))}</div>'
                for d in recent
            )
            header = (
                '<div style="display:flex;justify-content:space-between;padding:8px 14px;'
                'background:#262B3D;border-radius:8px 8px 0 0;border:1px solid #2D3748;'
                'border-bottom:none">'
                '<span style="font-size:11px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:.05em">Filename</span>'
                '<span style="font-size:11px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:.05em">Pages</span>'
                '<span style="font-size:11px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:.05em">Status</span>'
                '</div>'
            )
            st.markdown(
                header + f'<div style="border:1px solid #2D3748;border-radius:0 0 8px 8px;overflow:hidden">{rows_html}</div>',
                unsafe_allow_html=True,
            )

    with col_r:
        st.markdown(section_title("Process Graph"), unsafe_allow_html=True)
        with st.container(border=True):
            g1, g2 = st.columns(2)
            g1.metric("Nodes", stats.get("graph_node_count", 0))
            g2.metric("Edges", stats.get("graph_edge_count", 0))
            if st.button("🕸️ View Graph", use_container_width=True, type="primary"):
                st.switch_page("pages/3_graph.py")

# ── Create Unit dialog ─────────────────────────────────────────────────────────
if st.session_state.get("show_create_unit"):
    with st.form("create_unit_form"):
        st.subheader("Create New Process Unit")
        name = st.text_input("Unit Name *", placeholder="e.g. CDU, VDU, HCU")
        description = st.text_area("Description (optional)")
        cs, cc = st.columns(2)
        submitted = cs.form_submit_button("✅ Create", type="primary", use_container_width=True)
        cancelled = cc.form_submit_button("Cancel", use_container_width=True)
        if cancelled:
            st.session_state["show_create_unit"] = False; st.rerun()
        if submitted:
            if not name.strip():
                st.error("Unit name is required.")
            else:
                ok, result = create_unit(name.strip(), description)
                if ok:
                    st.success(f"Unit **{name.upper()}** created!")
                    st.session_state["show_create_unit"] = False; st.rerun()
                else:
                    st.error(f"Error: {result}")

# ── Bug Report dialog ──────────────────────────────────────────────────────────
if st.session_state.get("show_bug_report"):
    with st.form("bug_report_form"):
        st.subheader("🐛 Report a Bug")
        component = st.selectbox("Component", [
            "PDF Upload & Processing", "Tag Extraction", "Knowledge Graph",
            "Natural Language Query", "Equipment Search", "Graph Visualisation",
            "Documents", "Frontend (UI)", "Backend API", "Other",
        ])
        severity    = st.selectbox("Severity", ["High", "Medium", "Low", "Critical"])
        description = st.text_area("What went wrong? *")
        steps       = st.text_area("Steps to reproduce")
        cs, cc = st.columns(2)
        submitted = cs.form_submit_button("Submit", type="primary", use_container_width=True)
        cancelled = cc.form_submit_button("Cancel", use_container_width=True)
        if cancelled:
            st.session_state["show_bug_report"] = False; st.rerun()
        if submitted and description:
            ok, url = report_bug(
                component=component, description=description, steps=steps,
                severity=severity.lower(),
                unit_name=unit_obj["name"] if unit_obj else None,
                page="Dashboard",
            )
            st.success(f"Bug reported! [View issue]({url})") if (ok and url) else st.info(url or "Submitted.")
            st.session_state["show_bug_report"] = False
