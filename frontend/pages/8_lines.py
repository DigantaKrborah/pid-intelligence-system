import io
import streamlit as st
import pandas as pd
from frontend.utils.api_client import require_unit, get_graph, list_all_documents
from frontend.utils.styles import inject_css, section_title, tag_chip

st.set_page_config(page_title="Process Line List", layout="wide")
inject_css()
st.markdown("# 🔀 Process Line List")

unit      = require_unit()
unit_id   = unit["id"]
unit_name = unit["name"]
st.caption(f"Unit: **{unit_name}**")

# Drawing scope
all_docs    = [d for d in list_all_documents(unit_id) if d["processing_status"] == "completed"]
doc_options = {"All drawings": None, **{d["filename"]: d["document_id"] for d in all_docs}}
sel_drawing = st.selectbox("Drawing scope", list(doc_options.keys()), index=0)
selected_doc_id = doc_options[sel_drawing]

with st.spinner("Loading graph…"):
    graph_data = get_graph(unit_name, include_cross_unit=False)

nodes_raw = graph_data.get("nodes", [])
edges_raw = graph_data.get("edges", [])

# Apply drawing filter if specified
if selected_doc_id:
    visible_ids = {n["id"] for n in nodes_raw if str(n.get("document_id", "")) == selected_doc_id}
    nodes_raw   = [n for n in nodes_raw if n["id"] in visible_ids]
    edges_raw   = [e for e in edges_raw if e["source"] in visible_ids and e["target"] in visible_ids]

# Filter to line-type nodes
line_nodes = [n for n in nodes_raw if n.get("tag_type", "").lower() == "line"]

if not line_nodes:
    st.info("No process lines found. Ensure P&ID drawings with line tags have been uploaded.")
    st.stop()

# Build line list with connected equipment
edge_index: dict[str, dict[str, list]] = {}
for e in edges_raw:
    src, tgt = e["source"], e["target"]
    edge_index.setdefault(src, {"downstream": [], "upstream": []})["downstream"].append(tgt)
    edge_index.setdefault(tgt, {"downstream": [], "upstream": []})["upstream"].append(src)

rows: list[dict] = []
for ln in line_nodes:
    tag  = ln["id"]
    conn = edge_index.get(tag, {})
    rows.append({
        "Line Number": tag,
        "Description": ln.get("description") or "—",
        "From":        ", ".join(conn.get("upstream",   [])[:4]) or "—",
        "To":          ", ".join(conn.get("downstream", [])[:4]) or "—",
        "Drawing":     ln.get("drawing_ref", "—"),
        "Page":        ln.get("page_number")  or "—",
    })

df = pd.DataFrame(rows).sort_values("Line Number")

# ── Metrics ────────────────────────────────────────────────────────────────────
c1, c2 = st.columns(2)
c1.metric("Total Lines", len(df))
c2.metric("Lines with connections", len(df[(df["From"] != "—") | (df["To"] != "—")]))

st.divider()

# ── Download ───────────────────────────────────────────────────────────────────
buf = io.StringIO()
df.to_csv(buf, index=False)
st.download_button(
    "⬇️ Download Line List (CSV)",
    buf.getvalue().encode("utf-8"),
    file_name=f"{unit_name.replace(' ','_')}_line_list.csv",
    mime="text/csv",
    type="primary",
)

st.markdown(section_title("Line Register"), unsafe_allow_html=True)
st.dataframe(df, use_container_width=True, hide_index=True)
