import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
from frontend.utils.api_client import (
    require_unit, get_graph, get_graph_stats, get_neighbours, get_impact,
)
from frontend.utils.styles import inject_css, TYPE_COLOURS, tag_chip, severity_badge, section_title

st.set_page_config(page_title="Process Graph", layout="wide")
inject_css()
st.markdown("# 🕸️ Process Graph")

unit      = require_unit()
unit_name = unit["name"]

# ── Controls ──────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
with c1: highlight   = st.text_input("Highlight tag", value=st.session_state.pop("graph_highlight", ""), placeholder="P-101")
with c2: cross_unit  = st.toggle("Cross-unit", value=False)
with c3: physics     = st.toggle("Physics",    value=True)
with c4: node_size   = st.slider("Node size",  10, 40, 18, label_visibility="collapsed")

# ── Graph data ────────────────────────────────────────────────────────────────
graph_data = get_graph(unit_name, include_cross_unit=cross_unit)
nodes_raw  = graph_data.get("nodes", [])
edges_raw  = graph_data.get("edges", [])

nodes, edges = [], []
for n in nodes_raw:
    tag      = n.get("id", "")
    typ      = (n.get("tag_type") or "other").lower()
    colour   = TYPE_COLOURS.get(typ, "#94A3B8")
    is_cross = n.get("cross_unit", False)
    size     = node_size + 10 if tag == highlight else node_size
    nodes.append(Node(
        id=tag, label=tag, size=size, color=colour,
        borderWidth=3 if (tag == highlight or is_cross) else 1,
    ))

for e in edges_raw:
    is_cross = e.get("cross_unit", False)
    edges.append(Edge(
        source=e["source"], target=e["target"],
        color="#F97316" if is_cross else "#475569",
        dashes=is_cross,
    ))

# ── Layout ────────────────────────────────────────────────────────────────────
col_graph, col_detail = st.columns([3, 1])

selected = None   # initialise before agraph — avoids NameError when nodes is empty

with col_graph:
    if not nodes:
        st.info(f"No graph data for **{unit_name}**. Upload and process P&ID files first.")
    else:
        config = Config(
            width=880, height=560, directed=True,
            physics=physics, hierarchical=False,
            nodeHighlightBehavior=True,
        )
        selected = agraph(nodes=nodes, edges=edges, config=config)

        stats = get_graph_stats(unit_name)
        s1, s2, s3 = st.columns(3)
        s1.metric("Nodes", stats.get("nodes", 0))
        s2.metric("Edges", stats.get("edges", 0))
        s3.caption("Click a node to inspect it")

with col_detail:
    sel_node = highlight or (selected if isinstance(selected, str) else None)

    if sel_node:
        st.markdown(
            f'<h3 style="font-size:16px;font-weight:700;margin-bottom:8px">⚙️ '
            f'<code style="background:transparent;border:none;padding:0;color:inherit;font-size:16px">'
            f'{sel_node}</code></h3>',
            unsafe_allow_html=True,
        )
        nb = get_neighbours(unit_name, sel_node, depth=1)

        if nb.get("upstream"):
            st.markdown(
                '<div style="font-size:11px;color:#94A3B8;margin-bottom:4px">⬆️ Upstream</div>'
                + "".join(tag_chip(t) for t in nb["upstream"][:8]),
                unsafe_allow_html=True,
            )
        if nb.get("downstream"):
            st.markdown(
                '<div style="font-size:11px;color:#94A3B8;margin:8px 0 4px">⬇️ Downstream</div>'
                + "".join(tag_chip(t) for t in nb["downstream"][:8]),
                unsafe_allow_html=True,
            )
        if not nb.get("upstream") and not nb.get("downstream"):
            st.caption("No connections found.")

        st.divider()
        impact = get_impact(unit_name, sel_node)
        if impact and impact.get("found"):
            st.markdown(
                f'<div style="margin-bottom:4px">{severity_badge(impact["severity"])}</div>'
                f'<div style="font-size:12px;color:#94A3B8">{impact["affected_count"]} affected downstream</div>',
                unsafe_allow_html=True,
            )

        st.divider()
        if st.button("💬 Ask about this tag", use_container_width=True, type="primary"):
            st.session_state["pending_query"] = f"Tell me about {sel_node}"
            st.switch_page("pages/4_chat.py")
    else:
        # Legend
        st.markdown(section_title("Legend"), unsafe_allow_html=True)
        for typ, color in TYPE_COLOURS.items():
            if typ not in ("line", "other"):
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:5px;font-size:12px">'
                    f'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;'
                    f'background:{color}"></span>{typ.title()}</div>',
                    unsafe_allow_html=True,
                )
        st.markdown(
            '<div style="display:flex;align-items:center;gap:8px;margin-top:8px;font-size:11px;color:#94A3B8">'
            '<span style="display:inline-block;width:20px;border-top:2px dashed #F97316"></span>Cross-unit link</div>',
            unsafe_allow_html=True,
        )
        st.info("Click a node in the graph to inspect it.")
