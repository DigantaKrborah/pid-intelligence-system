import streamlit as st
from frontend.utils.api_client import (
    require_unit, list_incidents, create_incident, resolve_incident,
)
from frontend.utils.styles import inject_css, incident_card, section_title, severity_badge, status_badge

st.set_page_config(page_title="Incidents", layout="wide")
inject_css()
st.markdown("# 🚨 Incidents")

unit      = require_unit()
unit_id   = unit["id"]
unit_name = unit["name"]
st.caption(f"Unit: **{unit_name}**")

# ── Report new incident ────────────────────────────────────────────────────────
with st.expander("➕ Report New Incident"):
    with st.form("new_incident"):
        title       = st.text_input("Title *", placeholder="P-101 mechanical seal leak")
        description = st.text_area("Description *")
        c1, c2      = st.columns(2)
        severity    = c1.selectbox("Severity", ["medium", "high", "critical", "low"])
        tags_input  = c2.text_input("Related Tags (comma separated)", placeholder="P-101, FCV-101")
        if st.form_submit_button("Report Incident", type="primary"):
            if not title or not description:
                st.error("Title and description are required.")
            else:
                tags = [t.strip() for t in tags_input.split(",") if t.strip()]
                ok, data = create_incident(unit_id, title, description, severity, tags)
                if ok:
                    st.success(f"Incident reported: **{title}**"); st.rerun()
                else:
                    st.error(f"Failed: {data.get('detail','Unknown')}")

st.divider()

# ── Filters ───────────────────────────────────────────────────────────────────
cf1, cf2 = st.columns([2, 1])
with cf1: status_filter = st.selectbox("Status", ["All", "open", "investigating", "resolved"])
with cf2: show_all      = st.checkbox("Show all units", value=False)

filter_uid    = None if show_all else unit_id
filter_status = None if status_filter == "All" else status_filter

incidents = list_incidents(unit_id=filter_uid, status=filter_status)

if not incidents:
    st.info("No incidents found for the current filter.")
else:
    st.markdown(section_title(f"{len(incidents)} incident(s)"), unsafe_allow_html=True)

    for inc in incidents:
        # Styled card
        st.markdown(incident_card(inc), unsafe_allow_html=True)

        # Resolve button / form
        inc_id = inc["id"]
        if inc.get("status") != "resolved":
            col_btn, _ = st.columns([1, 3])
            if col_btn.button("Resolve", key=f"r_{inc_id}"):
                st.session_state[f"resolving_{inc_id}"] = True
                st.rerun()

        if st.session_state.get(f"resolving_{inc_id}"):
            with st.form(f"resolve_{inc_id}"):
                resolution = st.text_area("Resolution notes *")
                cs, cc = st.columns(2)
                if cs.form_submit_button("✅ Confirm", type="primary"):
                    if resolution:
                        ok, _ = resolve_incident(inc_id, resolution)
                        if ok:
                            st.session_state.pop(f"resolving_{inc_id}", None)
                            st.rerun()
                        else:
                            st.error("Failed to resolve.")
                    else:
                        st.error("Resolution notes required.")
                if cc.form_submit_button("Cancel"):
                    st.session_state.pop(f"resolving_{inc_id}", None)
                    st.rerun()
