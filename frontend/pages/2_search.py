import streamlit as st
from frontend.utils.api_client import (
    get_units, search_tags, get_tag_detail, get_neighbours, get_impact,
)

st.set_page_config(page_title="Search Tags", layout="wide")
st.title("🔍 Equipment Tag Search")

# Unit filter (optional — can search across all units)
units = get_units()
unit_map = {u["name"]: u for u in units}
unit_options = ["All Units"] + [u["name"] for u in units]
selected_unit_name = st.session_state.get("selected_unit", "All Units")
default_idx = unit_options.index(selected_unit_name) if selected_unit_name in unit_options else 0

col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
with col1:
    query = st.text_input("Search tags", placeholder="P-101, TIC-301, control valve, reactor feed...")
with col2:
    filter_unit = st.selectbox("Unit", unit_options, index=default_idx)
with col3:
    tag_type = st.selectbox("Type", ["All Types", "pump", "vessel", "valve", "instrument", "exchanger", "compressor"])
with col4:
    semantic = st.toggle("Semantic search", value=False, help="Vector search instead of SQL LIKE")

unit_id = unit_map[filter_unit]["id"] if filter_unit != "All Units" and filter_unit in unit_map else None

# ── Results ────────────────────────────────────────────────────────────────────
if query:
    with st.spinner("Searching..."):
        results = search_tags(
            q=query,
            unit_id=unit_id,
            tag_type=tag_type if tag_type != "All Types" else None,
            semantic=semantic,
        )

    if not results:
        st.info("No results found. Try a different query or upload P&ID sheets first.")
    else:
        st.caption(f"{len(results)} result(s)")
        col_list, col_detail = st.columns([2, 3])

        with col_list:
            for r in results:
                tag_str   = r.get("tag", "")
                type_str  = r.get("tag_type", "other") or "other"
                unit_str  = r.get("unit_name", "")
                score     = r.get("score", 1.0)

                type_emoji = {
                    "pump": "💧", "vessel": "🏭", "valve": "🔧",
                    "instrument": "📊", "exchanger": "♨️", "compressor": "💨",
                }.get(type_str, "⚙️")

                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.markdown(f"**{tag_str}** {type_emoji} `{type_str}` · {unit_str}")
                    c2.caption(f"{score:.0%}")
                    desc = r.get("description", "")
                    if desc:
                        st.caption(desc[:100])
                    if st.button("View details", key=f"detail_{tag_str}_{unit_str}"):
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
                    st.subheader(f"⚙️ {tag_data['tag']}")
                    st.caption(f"{tag_data.get('tag_type', '').title()} · {tag_data.get('unit_name', '')}")
                    if tag_data.get("description"):
                        st.write(tag_data["description"])

                    neighbours = tag_data.get("neighbours", [])
                    if neighbours:
                        st.markdown("**Connected equipment:**")
                        st.write(", ".join(f"`{n}`" for n in neighbours[:20]))

                    if tag_data.get("page_number"):
                        st.caption(f"Source: page {tag_data['page_number']}")

                    col_a, col_b = st.columns(2)
                    if col_a.button("🕸️ View in Graph", key="to_graph"):
                        st.session_state["graph_highlight"] = detail_tag
                        st.switch_page("pages/3_graph.py")
                    if col_b.button("💬 Ask about this", key="to_chat"):
                        st.session_state["pending_query"] = f"Tell me about {detail_tag}"
                        st.switch_page("pages/4_chat.py")

                    # Impact analysis
                    with st.expander("⚠️ Impact analysis — what fails if this is isolated?"):
                        impact = get_impact(detail_unit or detail_tag, detail_tag)
                        if impact and impact.get("found"):
                            sev = impact["severity"]
                            colour = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(sev, "⚪")
                            st.markdown(f"**Severity:** {colour} {sev.title()}")
                            st.metric("Affected equipment", impact["affected_count"])
                            by_type = impact.get("affected_by_type", {})
                            for typ, tags in by_type.items():
                                st.write(f"**{typ.title()}s:** {', '.join(f'`{t}`' for t in tags)}")
                        else:
                            st.info("No impact data available.")
            else:
                st.info("Click **View details** on a result to see connections and impact analysis.")
