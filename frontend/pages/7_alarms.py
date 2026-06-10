import re
import io
import streamlit as st
import pandas as pd
from frontend.utils.api_client import require_unit, list_unit_tags
from frontend.utils.styles import inject_css, section_title, tag_chip

st.set_page_config(page_title="Alarms & Interlocks", layout="wide")
inject_css()
st.markdown("# 🚨 Alarm & Interlock Inventory")

unit      = require_unit()
unit_id   = unit["id"]
unit_name = unit["name"]
st.caption(f"Unit: **{unit_name}**")

# ── Classification helpers ─────────────────────────────────────────────────────
# Strip area prefix (04-PAH-001 → PAH-001) before matching
_AREA_PREFIX = re.compile(r'^\d{2,4}-')

_ALARM_RE = re.compile(
    r'^[A-Z]{1,3}A(H{1,2}|L{1,2})$'           # PAH, TAL, LAHH, FALL …
    r'|^[A-Z]{1,2}(HH|LL)$',                    # FHH, TLL (no explicit A)
    re.I,
)
_INTERLOCK_RE = re.compile(
    r'^(ESDV|PSDV|SDV|SOV|BDV|FSV|XV)\b', re.I
)
_SAFETY_VALVE_RE = re.compile(
    r'^(PSV|PRV|RV|SV|TSV|PCV|PCVS)\b', re.I
)


def _classify(tag: str) -> str | None:
    """Return 'alarm', 'interlock', 'safety_valve', or None."""
    clean = _AREA_PREFIX.sub('', tag)
    # Extract the type abbreviation (before the trailing number)
    m = re.match(r'^([A-Z]+)', clean, re.I)
    abbr = m.group(1).upper() if m else clean.upper()

    if _INTERLOCK_RE.match(abbr):
        return "interlock"
    if _SAFETY_VALVE_RE.match(abbr):
        return "safety_valve"
    if _ALARM_RE.match(abbr):
        return "alarm"
    return None


with st.spinner("Loading tags…"):
    tags = list_unit_tags(unit_id)

if not tags:
    st.info("No tags found. Upload and process a P&ID drawing first.")
    st.stop()

# Classify
rows: list[dict] = []
for t in tags:
    cat = _classify(t["tag"])
    if cat:
        rows.append({
            "Category":    cat.replace("_", " ").title(),
            "Tag":         t["tag"],
            "Description": t["description"] or "—",
            "Page":        t["page_number"] or "—",
            "Drawing":     t["drawing"] or "—",
        })

if not rows:
    st.info("No alarm or interlock tags found in the current drawings.")
    st.stop()

df = pd.DataFrame(rows)

# ── Metrics ────────────────────────────────────────────────────────────────────
alarms   = df[df["Category"] == "Alarm"]
interlocks = df[df["Category"] == "Interlock"]
svs      = df[df["Category"] == "Safety Valve"]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Safety Items", len(df))
c2.metric("Alarms",        len(alarms))
c3.metric("Interlocks",    len(interlocks))
c4.metric("Safety Valves", len(svs))

st.divider()

# ── Download ───────────────────────────────────────────────────────────────────
buf = io.StringIO()
df.to_csv(buf, index=False)
st.download_button(
    "⬇️ Download Alarm & Interlock Inventory (CSV)",
    buf.getvalue().encode("utf-8"),
    file_name=f"{unit_name.replace(' ','_')}_alarms_interlocks.csv",
    mime="text/csv",
    type="primary",
)

# ── Tables by category ─────────────────────────────────────────────────────────
tab_alarms, tab_interlocks, tab_svs, tab_all = st.tabs(
    ["Alarms", "Interlocks", "Safety Valves", "All"]
)

with tab_alarms:
    st.caption(f"{len(alarms)} alarm tag(s)")
    st.dataframe(alarms.drop(columns=["Category"]), use_container_width=True, hide_index=True)

with tab_interlocks:
    st.caption(f"{len(interlocks)} interlock tag(s)")
    st.dataframe(interlocks.drop(columns=["Category"]), use_container_width=True, hide_index=True)

with tab_svs:
    st.caption(f"{len(svs)} safety valve tag(s)")
    st.dataframe(svs.drop(columns=["Category"]), use_container_width=True, hide_index=True)

with tab_all:
    st.dataframe(df, use_container_width=True, hide_index=True)
