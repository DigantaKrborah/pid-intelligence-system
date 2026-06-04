import streamlit as st
from frontend.utils.api_client import require_unit, nl_query

st.set_page_config(page_title="Ask a Question", layout="wide")
st.title("💬 Ask a Question")

unit = require_unit()
unit_id   = unit["id"]
unit_name = unit["name"]

st.caption(f"Querying unit: **{unit_name}**")

EXAMPLE_QUERIES = [
    "List all pumps",
    "What is downstream of V-101?",
    "Which instruments monitor reactor pressure?",
    "Process path from P-101 to the fractionator",
    "Startup procedure for the vacuum system",
]

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Example chips — only when chat is empty
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

# Input
query = st.chat_input(f"Ask about {unit_name} equipment, process paths, or SOPs...")
if not query and st.session_state.get("pending_query"):
    query = st.session_state.pop("pending_query")

if query:
    st.session_state.chat_history.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.write(query)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            data = nl_query(
                question=query,
                unit_id=unit_id,
                chat_history=st.session_state.chat_history[:-1],
            )
        answer  = data.get("answer", "No response.")
        sources = data.get("sources", [])

        st.write(answer)
        if sources:
            with st.expander("📄 Sources"):
                for s in sources:
                    st.caption(f"{s.get('source', '')} — page {s.get('page', '?')}")

    st.session_state.chat_history.append({"role": "assistant", "content": answer})

# Clear button
if st.session_state.chat_history:
    if st.button("🗑️ Clear chat"):
        st.session_state.chat_history = []
        st.rerun()
