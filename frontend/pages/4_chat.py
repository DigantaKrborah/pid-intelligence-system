import streamlit as st
from frontend.utils.api_client import require_unit, nl_query
from frontend.utils.styles import inject_css, chat_user_bubble, chat_ai_card, tag_chip, section_title

st.set_page_config(page_title="Ask a Question", layout="wide")
inject_css()
st.markdown("# 💬 Ask a Question")

unit      = require_unit()
unit_id   = unit["id"]
unit_name = unit["name"]

st.markdown(
    f'<div style="font-size:13px;color:#94A3B8;margin-bottom:16px">'
    f'Querying unit: <strong style="color:#F1F5F9">{unit_name}</strong></div>',
    unsafe_allow_html=True,
)

EXAMPLE_QUERIES = [
    "List all pumps",
    "What is downstream of V-101?",
    "Which instruments monitor reactor pressure?",
    "Process path from P-101 to the fractionator",
    "Startup procedure for the vacuum system",
]

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Example query chips (shown on empty chat)
if not st.session_state.chat_history:
    st.markdown(section_title("Try asking"), unsafe_allow_html=True)
    cols = st.columns(len(EXAMPLE_QUERIES))
    for col, ex in zip(cols, EXAMPLE_QUERIES):
        if col.button(ex, use_container_width=True):
            st.session_state.pending_query = ex

# Chat history — render as styled HTML bubbles
chat_html = ""
for msg in st.session_state.chat_history:
    if msg["role"] == "user":
        chat_html += chat_user_bubble(msg["content"])
    else:
        chat_html += chat_ai_card(msg["content"], msg.get("sources"))

if chat_html:
    st.markdown(chat_html, unsafe_allow_html=True)

# Input
query = st.chat_input(f"Ask about {unit_name} equipment, process paths, or SOPs…")
if not query and st.session_state.get("pending_query"):
    query = st.session_state.pop("pending_query")

if query:
    st.session_state.chat_history.append({"role": "user", "content": query})
    st.markdown(chat_user_bubble(query), unsafe_allow_html=True)

    with st.spinner("Thinking…"):
        # Send only role+content to backend (strip 'sources' — backend expects str values only)
        clean_history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.chat_history[:-1]
        ]
        data = nl_query(question=query, unit_id=unit_id, chat_history=clean_history)
    answer  = data.get("answer", "No response.")
    sources = data.get("sources", [])

    st.markdown(chat_ai_card(answer, sources), unsafe_allow_html=True)
    st.session_state.chat_history.append({"role": "user" if False else "assistant",
                                           "content": answer, "sources": sources})

if st.session_state.chat_history:
    if st.button("🗑️ Clear chat"):
        st.session_state.chat_history = []
        st.rerun()
