import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
from frontend.utils.api_client import (
    require_unit, get_graph, get_graph_stats, get_neighbours, get_impact,
)

st.set_page_config(page_title="Process Graph", layout="wide")
st.title("🕸️ Process Graph")

unit = require_unit()
unit_name = unit["name"]

TYPE_COLOURS = {
    "pump":       "#3B82F6",
    "vessel":     "#6B7280",
    "valve":      "#F97316",
    "instrument": "#14B8A6",
    "exchanger":  "#22C55E",
    "compressor": "#8B5CF6",
    "line":       "#CBD5E1",
    "other":      "#94A3B8",
}

# ── Controls ──────────────────────────────────────────────────────────────────
ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([2, 1, 1, 1])
with ctrl1:
    highlight = st.text_input(
        "Highlight tag",
        value=st.session_state.pop("graph_highlight", ""),
        placeholder="P-101",
    )
with ctrl2:
    cross_unit = st.toggle("Cross-unit", value=False)
with ctrl3:
    physics = st.toggle("Physics", value=True)
with ctrl4:
    node_size = st.slider("Node size", 10, 40, 18, label_visibility="collapsed")

# ── Fetch graph data ───────────────────────────────────────────────────────────
graph_data = get_graph(unit_name, include_cross_unit=cross_unit)
nodes_raw  = graph_data.get("nodes", [])
edges_raw  = graph_data.get("edges", [])

# ── Build agraph objects ───────────────────────────────────────────────────────
nodes, edges = [], []

for n in nodes_raw:
    tag      = n.get("id", "")
    typ      = n.get("tag_type") or "other"
    colour   = TYPE_COLOURS.get(typ, "#94A3B8")
    is_cross = n.get("cross_unit", False)
    size     = node_size + 8 if tag == highlight else node_size
    border   = "#FFFFFF" if is_cross else colour

    nodes.append(Node(
        id=tag,
        label=tag,
        size=size,
        color=colour,
        borderWidth=3 if tag == highlight or is_cross else 1,
        borderWidthSelected=5,
    ))

for e in edges_raw:
    is_cross = e.get("cross_unit", False)
    edges.append(Edge(
        source=e["source"],
        target=e["target"],
        color="#64748B" if is_cross else "#94A3B8",
        dashes=is_cross,
    ))

# ── Render graph + detail panel ───────────────────────────────────────────────
col_graph, col_detail = st.columns([3, 1])

with col_graph:
    if not nodes:
        st.info(f"No graph data for **{unit_name}**. Upload and process P&ID files first.")
    else:
        config = Config(
            width=850,
            height=580,
            directed=True,
            physics=physics,
            hierarchical=False,
            nodeHighlightBehavior=True,
            highlightColor="#F6F6F6",
        )
        selected = agraph(nodes=nodes, edges=edges, config=config)

        # Stats row
        stats = get_graph_stats(unit_name)
        s1, s2, s3 = st.columns(3)
        s1.metric("Nodes", stats.get("nodes", 0))
        s2.metric("Edges", stats.get("edges", 0))
        s3.caption("Click a node to inspect it")

with col_detail:
    selected_node = highlight or (selected if isinstance(selected, str) else None)

    if selected_node:
        st.subheader(f"⚙️ {selected_node}")

        neighbours = get_neighbours(unit_name, selected_node, depth=1)
        upstream   = neighbours.get("upstream", [])
        downstream = neighbours.get("downstream", [])

        if upstream:
            st.markdown("**⬆️ Upstream:**")
            for t in upstream[:10]:
                if st.button(t, key=f"up_{t}"):
                    st.session_state["graph_highlight"] = t
                    st.rerun()

        if downstream:
            st.markdown("**⬇️ Downstream:**")
            for t in downstream[:10]:
                if st.button(t, key=f"dn_{t}"):
                    st.session_state["graph_highlight"] = t
                    st.rerun()

        if not upstream and not downstream:
            st.caption("No connections found.")

        st.divider()

        # Impact analysis
        impact = get_impact(unit_name, selected_node)
        if impact and impact.get("found"):
            sev = impact["severity"]
            colour = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(sev, "⚪")
            st.markdown(f"**Impact:** {colour} {sev.title()}")
            st.metric("Affected downstream", impact["affected_count"])

        st.divider()
        if st.button("💬 Ask about this tag"):
            st.session_state["pending_query"] = f"Tell me about {selected_node}"
            st.switch_page("pages/4_chat.py")
    else:
        st.info("Click a node in the graph to inspect it.")

        # Legend
        st.markdown("**Legend:**")
        for typ, col in TYPE_COLOURS.items():
            if typ != "other":
                st.markdown(
                    f'<span style="display:inline-block;width:12px;height:12px;'
                    f'border-radius:50%;background:{col};margin-right:6px"></span> {typ.title()}',
                    unsafe_allow_html=True,
                )
