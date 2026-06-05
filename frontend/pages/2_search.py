import streamlit as st
from frontend.utils.api_client import (
    get_units, search_tags, get_tag_detail, get_neighbours, get_impact,
)
from frontend.utils.styles import (
    inject_css, result_card, type_badge, tag_chip, tag_chips_row,
    impact_panel, section_title, TYPE_COLOURS,
)

st.set_page_config(page_title="Search Tags", layout="wide")
inject_css()
st.markdown("# 🔍 Equipment Tag Search")

units    = get_units()
unit_map = {u["name"]: u for u in units}
u_options = ["All Units"] + list(unit_map)
sel_name  = st.session_state.get("selected_unit", "All Units")
def_idx   = u_options.index(sel_name) if sel_name in u_options else 0

c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
with c1: query       = st.text_input("Search", placeholder="P-101, TIC-301, control valve, reactor feed...")
with c2: filter_unit = st.selectbox("Unit", u_options, index=def_idx)
with c3: tag_type    = st.selectbox("Type", ["All Types","pump","vessel","valve","instrument","exchanger","compressor"])
with c4: semantic    = st.toggle("Semantic", value=False, help="Vector search via ChromaDB")

unit_id = unit_map[filter_unit]["id"] if filter_unit != "All Units" and filter_unit in unit_map else None

if query:
    with st.spinner("Searching…"):
        results = search_tags(
            q=query,
            unit_id=unit_id,
            tag_type=tag_type if tag_type != "All Types" else None,
            semantic=semantic,
        )

    if not results:
        st.info("No results. Try a different query or upload P&ID sheets first.")
    else:
        st.caption(f"{len(results)} result(s)")
        col_list, col_detail = st.columns([2, 3])

        with col_list:
            for r in results:
                tag_str  = r.get("tag", "")
                type_str = (r.get("tag_type") or "other").lower()
                unit_str = r.get("unit_name", "")
                score    = r.get("score", 1.0)
                selected = st.session_state.get("detail_tag") == tag_str
                # Render styled card as HTML
                st.markdown(
                    result_card(tag_str, type_str, unit_str, r.get("description",""), score, selected),
                    unsafe_allow_html=True,
                )
                if st.button("View details →", key=f"d_{tag_str}_{unit_str}", use_container_width=True):
                    st.session_state["detail_tag"]  = tag_str
                    st.session_state["detail_unit"] = unit_str
                    st.session_state["detail_uid"]  = unit_id
                    st.rerun()

        with col_detail:
            detail_tag  = st.session_state.get("detail_tag")
            detail_unit = st.session_state.get("detail_unit")
            detail_uid  = st.session_state.get("detail_uid")

            if detail_tag:
                tag_data = get_tag_detail(detail_tag, detail_uid)
                if tag_data:
                    with st.container(border=True):
                        ttype = (tag_data.get("tag_type") or "other").lower()
                        # Header
                        st.markdown(
                            f'<h2 style="font-size:20px;font-weight:700;margin-bottom:4px">'
                            f'⚙️ <code style="font-size:20px;background:transparent;border:none;'
                            f'padding:0;color:inherit">{tag_data["tag"]}</code></h2>'
                            f'<div style="display:flex;gap:8px;margin-bottom:12px">'
                            f'{type_badge(ttype)}'
                            f'<span style="font-size:12px;color:#94A3B8">{tag_data.get("unit_name","")}</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        if tag_data.get("description"):
                            st.caption(tag_data["description"])

                        # Neighbours
                        neighbours = tag_data.get("neighbours", [])
                        if neighbours:
                            st.markdown(section_title("Connected Equipment"), unsafe_allow_html=True)
                            mid = len(neighbours) // 2
                            upstream   = neighbours[:mid] or neighbours
                            downstream = neighbours[mid:] or []
                            if upstream:
                                st.markdown(
                                    f'<div style="font-size:11px;color:#94A3B8;margin-bottom:4px">⬆️ Upstream</div>'
                                    + tag_chips_row(upstream, ttype),
                                    unsafe_allow_html=True,
                                )
                            if downstream:
                                st.markdown(
                                    f'<div style="font-size:11px;color:#94A3B8;margin:8px 0 4px">⬇️ Downstream</div>'
                                    + tag_chips_row(downstream, ttype),
                                    unsafe_allow_html=True,
                                )

                        if tag_data.get("page_number"):
                            st.caption(f"Source: page {tag_data['page_number']}")

                        ca, cb = st.columns(2)
                        if ca.button("🕸️ View in Graph", key="to_graph"):
                            st.session_state["graph_highlight"] = detail_tag
                            st.switch_page("pages/3_graph.py")
                        if cb.button("💬 Ask about this", key="to_chat", type="primary"):
                            st.session_state["pending_query"] = f"Tell me about {detail_tag}"
                            st.switch_page("pages/4_chat.py")

                        # Impact analysis
                        st.markdown("<br>", unsafe_allow_html=True)
                        with st.expander("⚠️ Impact analysis — what fails if this is isolated?"):
                            impact = get_impact(detail_unit or "", detail_tag)
                            if impact and impact.get("found"):
                                st.markdown(
                                    impact_panel(
                                        impact["severity"],
                                        impact["affected_count"],
                                        impact.get("affected_by_type", {}),
                                    ),
                                    unsafe_allow_html=True,
                                )
                            else:
                                st.info("No impact data available.")
            else:
                st.markdown(
                    '<div style="color:#94A3B8;font-size:13px;padding:20px 0">'
                    'Click <strong>View details →</strong> on a result to see connections and impact analysis.</div>',
                    unsafe_allow_html=True,
                )
