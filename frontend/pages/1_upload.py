import streamlit as st
import httpx
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Upload P&IDs", layout="wide")
st.title("📤 Upload P&ID Sheets")

unit = st.session_state.get("selected_unit")
if not unit:
    st.warning("Please select a process unit from the Home page first.")
    st.stop()

st.subheader(f"Unit: {unit}")

uploaded_files = st.file_uploader(
    "Drop P&ID PDF files here",
    type=["pdf"],
    accept_multiple_files=True,
    help="Max 50 MB per file. Multiple files allowed.",
)

if uploaded_files:
    st.write(f"**{len(uploaded_files)} file(s) selected:**")
    for f in uploaded_files:
        size_mb = f.size / (1024 * 1024)
        status = "⚠️ Too large" if size_mb > 50 else "✅ Ready"
        st.write(f"- {f.name} ({size_mb:.1f} MB) {status}")

    if st.button("🚀 Process P&IDs", type="primary"):
        # TODO: get real unit_id from session/API
        unit_id_placeholder = "00000000-0000-0000-0000-000000000001"
        progress = st.progress(0)
        for i, f in enumerate(uploaded_files):
            with st.spinner(f"Uploading {f.name}..."):
                try:
                    resp = httpx.post(
                        f"{BACKEND_URL}/api/v1/upload/pid",
                        data={"unit_id": unit_id_placeholder},
                        files={"files": (f.name, f.read(), "application/pdf")},
                        timeout=60,
                    )
                    if resp.status_code == 200:
                        st.success(f"✅ {f.name} queued for processing")
                    else:
                        st.error(f"❌ {f.name}: {resp.text}")
                except Exception as e:
                    st.error(f"❌ {f.name}: {e}")
            progress.progress((i + 1) / len(uploaded_files))
        st.balloons()
