import streamlit as st
import httpx
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

EXAMPLE_QUERIES = [
    "List all pumps in this unit",
    "What is downstream of V-101?",
    "Which instruments monitor the reactor pressure?",
    "What is the process path from P-101 to the fractionator?",
    "Show me the startup procedure for the vacuum system",
]

st.set_page_config(page_title="Ask a Question", layout="wide")
st.title("💬 Ask a Question")

unit = st.session_state.get("selected_unit")
if not unit:
    st.warning("Select a unit first.")
    st.stop()

st.caption(f"Querying unit: **{unit}**")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Example query chips (shown only on empty chat)
if not st.session_state.chat_history:
    st.write("**Try asking:**")
    cols = st.columns(len(EXAMPLE_QUERIES))
    for col, ex in zip(cols, EXAMPLE_QUERIES):
        if col.button(ex, use_container_width=True):
            st.session_state.pending_query = ex

# Render chat history
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Chat input
query = st.chat_input("Ask about equipment, process paths, or SOPs...")
if not query and st.session_state.get("pending_query"):
    query = st.session_state.pop("pending_query")

if query:
    st.session_state.chat_history.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.write(query)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                resp = httpx.post(
                    f"{BACKEND_URL}/api/v1/query/nl",
                    json={
                        "question": query,
                        "chat_history": st.session_state.chat_history[:-1],
                    },
                    timeout=30,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    answer = data["answer"]
                    sources = data.get("sources", [])
                else:
                    answer = f"Error {resp.status_code}: {resp.text}"
                    sources = []
            except Exception as e:
                answer = f"Could not reach backend: {e}"
                sources = []

        st.write(answer)
        if sources:
            with st.expander("Sources"):
                for s in sources:
                    st.caption(f"📄 {s.get('source', '')} — {s.get('page', '')}")

    st.session_state.chat_history.append({"role": "assistant", "content": answer})

if st.session_state.chat_history:
    if st.button("🗑️ Clear Chat"):
        st.session_state.chat_history = []
        st.rerun()
