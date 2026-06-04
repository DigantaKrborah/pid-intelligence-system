import streamlit as st
import httpx
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Search Tags", layout="wide")
st.title("🔍 Equipment Tag Search")

unit = st.session_state.get("selected_unit")

col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    query = st.text_input("Search tags", placeholder="P-101, TIC-301, control valve...")
with col2:
    tag_type = st.selectbox("Type", ["All Types", "pump", "vessel", "valve", "instrument", "exchanger"])
with col3:
    limit = st.number_input("Max results", min_value=5, max_value=100, value=20)

if query:
    params = {"q": query, "limit": limit}
    if tag_type != "All Types":
        params["tag_type"] = tag_type
    if unit:
        params["unit_name"] = unit

    try:
        resp = httpx.get(f"{BACKEND_URL}/api/v1/search/tags", params=params, timeout=5)
        results = resp.json() if resp.status_code == 200 else []
    except Exception:
        results = []

    if not results:
        st.info("No results found. Upload P&ID sheets first.")
    else:
        for r in results:
            with st.expander(f"**{r['tag']}** — {r.get('tag_type', '').title()} | {r.get('unit_name', '')}"):
                st.write(r.get("description", "No description"))
                st.caption(f"Score: {r.get('score', 0):.2f}")
