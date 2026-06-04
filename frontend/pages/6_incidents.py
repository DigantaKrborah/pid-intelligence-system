import streamlit as st
from frontend.utils.api_client import (
    require_unit, list_incidents, create_incident, resolve_incident,
)

st.set_page_config(page_title="Incidents", layout="wide")
st.title("🚨 Incidents")

unit = require_unit()
unit_id   = unit["id"]
unit_name = unit["name"]

st.caption(f"Unit: **{unit_name}**")

SEVERITY_COLOUR = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
STATUS_BADGE    = {"open": "🔓 Open", "investigating": "🔎 Investigating", "resolved": "✅ Resolved"}

# ── Report new incident ────────────────────────────────────────────────────────
with st.expander("➕ Report New Incident", expanded=False):
    with st.form("new_incident_form"):
        title       = st.text_input("Title *", placeholder="P-101 seal failure")
        description = st.text_area("Description *")
        col1, col2  = st.columns(2)
        severity    = col1.selectbox("Severity", ["medium", "high", "critical", "low"])
        tags_input  = col2.text_input("Related Tags (comma separated)", placeholder="P-101, FCV-101")
        submitted   = st.form_submit_button("Report Incident", type="primary")

        if submitted:
            if not title or not description:
                st.error("Title and description are required.")
            else:
                related_tags = [t.strip() for t in tags_input.split(",") if t.strip()]
                ok, data = create_incident(unit_id, title, description, severity, related_tags)
                if ok:
                    st.success(f"Incident reported: **{title}**")
                    st.rerun()
                else:
                    st.error(f"Failed: {data.get('detail', 'Unknown error')}")

st.divider()

# ── Filter ────────────────────────────────────────────────────────────────────
col_f1, col_f2 = st.columns([2, 1])
with col_f1:
    status_filter = col_f1.selectbox("Status filter", ["All", "open", "investigating", "resolved"])
with col_f2:
    show_all_units = st.checkbox("Show all units", value=False)

filter_uid    = None if show_all_units else unit_id
filter_status = None if status_filter == "All" else status_filter

# ── Incident list ─────────────────────────────────────────────────────────────
incidents = list_incidents(unit_id=filter_uid, status=filter_status)

if not incidents:
    st.info("No incidents found for the current filter.")
else:
    st.caption(f"{len(incidents)} incident(s)")
    for inc in incidents:
        sev    = inc.get("severity", "medium")
        status = inc.get("status", "open")
        icon   = SEVERITY_COLOUR.get(sev, "⚪")
        badge  = STATUS_BADGE.get(status, status)

        with st.container(border=True):
            col_left, col_right = st.columns([4, 1])
            with col_left:
                st.markdown(f"{icon} **{inc['title']}** · {badge}")
                if inc.get("description"):
                    st.caption(inc["description"][:150])
                tags = inc.get("related_tags") or []
                if tags:
                    st.write(" ".join(f"`{t}`" for t in tags))
                st.caption(f"Reported: {inc.get('reported_at', '')[:10]}")

            with col_right:
                if status != "resolved":
                    if st.button("Resolve", key=f"resolve_{inc['id']}"):
                        st.session_state[f"resolving_{inc['id']}"] = True
                        st.rerun()
                else:
                    st.caption(f"✅ {(inc.get('resolved_at') or '')[:10]}")

            # Inline resolution form
            if st.session_state.get(f"resolving_{inc['id']}"):
                with st.form(f"resolve_form_{inc['id']}"):
                    resolution = st.text_area("Resolution notes *")
                    col_s, col_c = st.columns(2)
                    if col_s.form_submit_button("Confirm Resolve", type="primary"):
                        if resolution:
                            ok, _ = resolve_incident(inc["id"], resolution)
                            if ok:
                                st.session_state.pop(f"resolving_{inc['id']}", None)
                                st.rerun()
                            else:
                                st.error("Failed to resolve.")
                        else:
                            st.error("Resolution notes required.")
                    if col_c.form_submit_button("Cancel"):
                        st.session_state.pop(f"resolving_{inc['id']}", None)
                        st.rerun()
