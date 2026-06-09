import streamlit as st
from frontend.utils.api_client import require_unit, nl_query, list_all_documents
from frontend.utils.styles import inject_css, chat_user_bubble, chat_ai_card, section_title

st.set_page_config(page_title="Ask a Question", layout="wide")
inject_css()
st.markdown("# 💬 Ask a Question")

unit      = require_unit()
unit_id   = unit["id"]
unit_name = unit["name"]

# ── Drawing scope selector ────────────────────────────────────────────────────
all_docs = [d for d in list_all_documents(unit_id) if d["processing_status"] == "completed"]
doc_map  = {d["filename"]: d["document_id"] for d in all_docs}

with st.expander("📐 Drawing scope", expanded=False):
    if not doc_map:
        st.caption("No processed drawings available.")
        scope_doc_ids = []
    else:
        scope_all = st.toggle("Query all drawings", value=True, key="scope_all")
        if scope_all:
            scope_doc_ids = []
            st.caption(f"Querying all {len(doc_map)} drawing(s) for **{unit_name}**")
        else:
            selected = st.multiselect(
                "Select drawings to query",
                options=list(doc_map.keys()),
                default=list(doc_map.keys())[:1] if doc_map else [],
            )
            scope_doc_ids = [doc_map[k] for k in selected]
            if scope_doc_ids:
                st.caption(f"Querying {len(scope_doc_ids)} of {len(doc_map)} drawing(s)")
            else:
                st.warning("No drawings selected — will query all.")
                scope_doc_ids = []

EXAMPLE_QUERIES = [
    "List all pumps",
    "What is downstream of V-101?",
    "Which instruments monitor reactor pressure?",
    "Process path from P-101 to the fractionator",
    "Startup procedure for the vacuum system",
]

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if not st.session_state.chat_history:
    st.markdown(section_title("Try asking"), unsafe_allow_html=True)
    cols = st.columns(len(EXAMPLE_QUERIES))
    for col, ex in zip(cols, EXAMPLE_QUERIES):
        if col.button(ex, use_container_width=True):
            st.session_state.pending_query = ex

chat_html = ""
for msg in st.session_state.chat_history:
    if msg["role"] == "user":
        chat_html += chat_user_bubble(msg["content"])
    else:
        chat_html += chat_ai_card(msg["content"], msg.get("sources"))

if chat_html:
    st.markdown(f'<div>{chat_html}</div>', unsafe_allow_html=True)

query = st.chat_input(f"Ask about {unit_name} equipment, process paths, or SOPs…")
if not query and st.session_state.get("pending_query"):
    query = st.session_state.pop("pending_query")

if query:
    st.session_state.chat_history.append({"role": "user", "content": query})
    st.markdown(chat_user_bubble(query), unsafe_allow_html=True)

    with st.spinner("Thinking…"):
        clean_history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.chat_history[:-1]
        ]
        data = nl_query(
            question=query,
            unit_id=unit_id,
            chat_history=clean_history,
            drawing_ids=scope_doc_ids,
        )
    answer  = data.get("answer", "No response.")
    sources = data.get("sources", [])

    st.markdown(chat_ai_card(answer, sources), unsafe_allow_html=True)
    st.session_state.chat_history.append({
        "role": "assistant", "content": answer, "sources": sources,
    })

if st.session_state.chat_history:
    if st.button("🗑️ Clear chat"):
        st.session_state.chat_history = []
        st.rerun()
