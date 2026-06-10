import io
import streamlit as st
import pandas as pd
from frontend.utils.api_client import require_unit, list_unit_tags, list_all_documents
from frontend.utils.styles import inject_css, section_title, type_badge

st.set_page_config(page_title="Equipment Register", layout="wide")
inject_css()
st.markdown("# 📋 Equipment Register")

unit      = require_unit()
unit_id   = unit["id"]
unit_name = unit["name"]
st.caption(f"Unit: **{unit_name}**")

# Drawing scope
all_docs    = [d for d in list_all_documents(unit_id) if d["processing_status"] == "completed"]
doc_options = {"All drawings": None, **{d["filename"]: d["document_id"] for d in all_docs}}
sel_drawing = st.selectbox("Drawing scope", list(doc_options.keys()), index=0)
doc_id_filt = doc_options[sel_drawing]

with st.spinner("Loading equipment…"):
    tags = list_unit_tags(unit_id, doc_id_filt)

if not tags:
    st.info("No equipment found. Upload and process P&ID drawings first.")
    st.stop()

df = pd.DataFrame(
    [{"Tag": t["tag"], "Type": t["tag_type"], "Description": t["description"],
      "Page": t["page_number"], "Drawing": t["drawing"]} for t in tags]
)

# ── Summary metrics ────────────────────────────────────────────────────────────
type_counts = df["Type"].value_counts()
metric_cols  = st.columns(min(len(type_counts) + 1, 6))
metric_cols[0].metric("Total Equipment", len(df))
for i, (typ, cnt) in enumerate(type_counts.items(), 1):
    if i < len(metric_cols):
        metric_cols[i].metric(typ.title() + "s", cnt)

st.divider()

# ── Full register download ─────────────────────────────────────────────────────
st.markdown(section_title("Full Equipment Register"), unsafe_allow_html=True)
buf = io.StringIO()
df.to_csv(buf, index=False)
st.download_button(
    "⬇️ Download Equipment Register (CSV)",
    buf.getvalue().encode("utf-8"),
    file_name=f"{unit_name.replace(' ','_')}_equipment_register.csv",
    mime="text/csv",
    type="primary",
)
st.dataframe(df, use_container_width=True, hide_index=True, height=300)

st.divider()

# ── Filtered equipment lists ───────────────────────────────────────────────────
st.markdown(section_title("Equipment List by Type"), unsafe_allow_html=True)
type_filter = st.selectbox(
    "Select type",
    ["All"] + sorted(df["Type"].unique().tolist()),
)
filtered = df if type_filter == "All" else df[df["Type"] == type_filter]
st.caption(f"{len(filtered)} item(s)")
st.dataframe(filtered, use_container_width=True, hide_index=True)

if type_filter != "All":
    fbuf = io.StringIO()
    filtered.to_csv(fbuf, index=False)
    st.download_button(
        f"⬇️ Download {type_filter.title()} List (CSV)",
        fbuf.getvalue().encode("utf-8"),
        file_name=f"{unit_name.replace(' ','_')}_{type_filter}_list.csv",
        mime="text/csv",
    )
