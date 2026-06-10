import pandas as pd
import streamlit as st
from frontend.utils.api_client import (
    require_unit, list_unit_tags, list_all_documents, patch_tag,
)
from frontend.utils.styles import inject_css, section_title

st.set_page_config(page_title="Tag Corrections", layout="wide")
inject_css()
st.markdown("# ✏️ Tag Corrections")

unit      = require_unit()
unit_id   = unit["id"]
unit_name = unit["name"]
st.caption(f"Unit: **{unit_name}**")

TAG_TYPES = ["pump", "vessel", "valve", "instrument", "exchanger", "compressor", "line", "other"]

# Drawing filter
all_docs    = [d for d in list_all_documents(unit_id) if d["processing_status"] == "completed"]
doc_options = {"All drawings": None, **{d["filename"]: d["document_id"] for d in all_docs}}
sel_drawing = st.selectbox("Filter by drawing", list(doc_options.keys()), index=0)
doc_id_filt = doc_options[sel_drawing]

with st.spinner("Loading tags…"):
    tags = list_unit_tags(unit_id, doc_id_filt)

if not tags:
    st.info("No tags found. Upload and process a P&ID drawing first.")
    st.stop()

st.caption(f"{len(tags)} tag(s) found — edit **Type** or **Description** then click Save.")

# Build working DataFrame; keep IDs parallel to rows
tag_ids = [t["id"] for t in tags]
df_edit  = pd.DataFrame(
    [{k: t[k] for k in ("tag", "tag_type", "description", "page_number", "drawing")} for t in tags]
)

# Store pristine copy for change-detection (reset when drawing filter changes)
orig_key = f"tags_orig_{unit_id}_{sel_drawing}"
if orig_key not in st.session_state:
    st.session_state[orig_key] = df_edit.copy()

edited = st.data_editor(
    df_edit,
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    column_config={
        "tag":         st.column_config.TextColumn("Tag",         disabled=True,  width="small"),
        "tag_type":    st.column_config.SelectboxColumn("Type",   options=TAG_TYPES, required=True, width="small"),
        "description": st.column_config.TextColumn("Description", width="large"),
        "page_number": st.column_config.NumberColumn("Page",      disabled=True,  width="small"),
        "drawing":     st.column_config.TextColumn("Drawing",     disabled=True,  width="medium"),
    },
    key=f"editor_{unit_id}_{sel_drawing}",
)

# Detect changed rows
orig = st.session_state[orig_key]
changed: list[dict] = []
for i in range(len(orig)):
    o = orig.iloc[i]
    n = edited.iloc[i]
    diff: dict = {"id": tag_ids[i], "tag": n["tag"]}
    if o["tag_type"] != n["tag_type"]:
        diff["tag_type"] = n["tag_type"]
    if o["description"] != n["description"]:
        diff["description"] = n["description"]
    if len(diff) > 2:
        changed.append(diff)

col_save, col_reset, col_msg = st.columns([1, 1, 5])

if changed:
    col_msg.caption(f"⚠️ {len(changed)} unsaved change(s)")

if col_save.button("💾 Save", type="primary", disabled=not changed):
    ok = err = 0
    for row in changed:
        success = patch_tag(
            row["id"],
            tag_type=row.get("tag_type"),
            description=row.get("description"),
        )
        if success:
            ok += 1
        else:
            err += 1
    if ok:
        st.success(f"Saved {ok} correction(s).")
        del st.session_state[orig_key]
        st.rerun()
    if err:
        st.error(f"{err} save(s) failed — check the backend logs.")

if col_reset.button("↩️ Reset"):
    del st.session_state[orig_key]
    st.rerun()
