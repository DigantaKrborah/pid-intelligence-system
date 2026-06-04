import streamlit as st
import httpx
import os
from streamlit_agraph import agraph, Node, Edge, Config

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

TYPE_COLOURS = {
    "pump": "#3B82F6",
    "vessel": "#6B7280",
    "valve": "#F97316",
    "instrument": "#14B8A6",
    "exchanger": "#22C55E",
    "compressor": "#8B5CF6",
    "other": "#94A3B8",
}

st.set_page_config(page_title="Process Graph", layout="wide")
st.title("🕸️ Process Graph")

unit = st.session_state.get("selected_unit")
if not unit:
    st.warning("Select a unit first.")
    st.stop()

col1, col2 = st.columns([4, 1])
with col2:
    cross_unit = st.checkbox("Show cross-unit connections")
    highlight = st.text_input("Highlight tag", placeholder="P-101")

try:
    resp = httpx.get(f"{BACKEND_URL}/api/v1/graph/{unit}", timeout=5)
    graph_data = resp.json() if resp.status_code == 200 else {"nodes": [], "links": []}
except Exception:
    graph_data = {"nodes": [], "links": []}

nodes = []
edges = []

for n in graph_data.get("nodes", []):
    tag = n.get("id", "")
    typ = n.get("tag_type", "other")
    colour = TYPE_COLOURS.get(typ, "#94A3B8")
    size = 25 if tag == highlight else 15
    nodes.append(Node(id=tag, label=tag, size=size, color=colour))

for e in graph_data.get("links", []):
    edges.append(Edge(source=e["source"], target=e["target"]))

if nodes:
    config = Config(width=900, height=600, directed=True, physics=True, hierarchical=False)
    with col1:
        agraph(nodes=nodes, edges=edges, config=config)
else:
    with col1:
        st.info(f"No graph data for unit {unit}. Upload and process P&ID files first.")

# Stats
try:
    stats_resp = httpx.get(f"{BACKEND_URL}/api/v1/graph/{unit}/stats", timeout=3)
    if stats_resp.status_code == 200:
        stats = stats_resp.json()
        c1, c2 = st.columns(2)
        c1.metric("Nodes", stats["nodes"])
        c2.metric("Edges", stats["edges"])
except Exception:
    pass
