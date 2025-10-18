import streamlit as st
from backend.question_answering import QA
from backend.web_search import WebSearch
from backend.deep_research import DeepResearch
from backend.chat_store import ChatStore
import uuid
import time
from utils.utilities import response_stream, generate_conversation_title
from utils.logging_config import configure_logging_from_env
from utils.env_loader import load_env

# Sidebar
with st.sidebar.expander("Settings", expanded=False):
    llm_model = st.selectbox(
        "LLM Model",
        ["qwen2.5:1.5b", "llama3.2:3b", "mistral"],
        key="llm_model_select",
    )
    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=0.5,
        step=0.1,
        key="temp_slider",
    )

with st.sidebar.expander("Upload", expanded=False):
    uploaded_file = st.file_uploader(
        "Upload a Document",
        type=["pdf", "docx", "txt"],
        key="doc_uploader",
    )
    if uploaded_file:
        st.success(f"Uploaded: {uploaded_file.name}")

AI = QA(model_name=llm_model, temperature=temperature)

# Main Page
st.title("WebRage Chatbot")
st.write("Ask me anything! I can help you with your questions.")
st.write("This is a simple chat interface powered by LLM.")

# Initialize persistent chat store
store = ChatStore()

# Resolve user id from URL (anonymous) and ensure a conversation
params = st.query_params
user_id = params.get("uid")
if not user_id:
    user_id = str(uuid.uuid4())
    # Replace experimental_set_query_params with st.query_params
    st.query_params["uid"] = user_id

conversation_id = params.get("cid")
conversation_id = store.ensure_conversation(user_id, conversation_id)
# Ensure URL always contains both uid and cid
st.query_params["uid"] = user_id
st.query_params["cid"] = conversation_id

# Initialize session state for chat history and track loaded conversation
if "messages" not in st.session_state:
    st.session_state.messages = []
if st.session_state.get("_loaded_cid") != conversation_id:
    # Load messages for the selected conversation from the DB
    msgs = store.get_messages(user_id, conversation_id)
    st.session_state.messages = [{"role": m["role"], "content": m["content"]} for m in msgs]
    st.session_state._loaded_cid = conversation_id

# Load environment variables from .env (if present) and configure logging
load_env()
configure_logging_from_env()

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Mode indicator
current_mode = (
    "Deep Research" if st.session_state.get("deep_research")
    else ("Web Search" if st.session_state.get("web_search") else "Normal")
)
# Visual badge (color + icon), no text label
if current_mode == "Deep Research":
    _mode_color, _mode_icon = "#8b5cf6", "🔬"
elif current_mode == "Web Search":
    _mode_color, _mode_icon = "#3b82f6", "🔎"
else:
    _mode_color, _mode_icon = "#9ca3af", "💬"

_indicator_html = f"""
<div style="display:flex; justify-content:flex-end; margin: 2px 0 6px 0;">
  <div title=\"{current_mode}\" style="
       display:flex; align-items:center; gap:6px;
       padding:4px 10px; border-radius:999px;
       background:rgba(0,0,0,0.04); border:1px solid rgba(0,0,0,0.06);">
    <span style=\"width:10px;height:10px;border-radius:50%;background:{_mode_color};display:inline-block;\"></span>
    <span style=\"font-size:14px\">{_mode_icon}</span>
  </div>
</div>
"""
st.markdown(_indicator_html, unsafe_allow_html=True)

# Accept user input
if prompt := st.chat_input("What is up?"):
    # Controlla se il pulsante "Deep Research" è stato cliccato
    if "deep_research" in st.session_state and st.session_state.deep_research:
        # Usa un metodo diverso per processare la query
        with st.chat_message("user"):
            st.markdown(f"**[Deep Research Mode]** {prompt}")
        user_msg_content = f"[Deep Research Mode] {prompt}"
        st.session_state.messages.append({"role": "user", "content": user_msg_content})
        store.append_message(user_id, conversation_id, "user", user_msg_content)
        # Set conversation title if empty
        conv = store.get_conversation(user_id, conversation_id)
        if conv and not conv.get("title"):
            try:
                msgs = store.get_messages(user_id, conversation_id)
                title = generate_conversation_title(AI, msgs, user_msg_content)
            except Exception:
                title = user_msg_content[:80]
            store.rename_conversation(user_id, conversation_id, title)

        # Risposta dell'assistente in modalità Deep Research
        deep_research = DeepResearch()
        start_time = time.time()  # Inizio del timer
        with st.chat_message("assistant"):
            response = deep_research.search(prompt)
            response = st.write_stream((_ for _ in response))
        generation_time = time.time() - start_time  # Calcolo del tempo di generazione
        st.session_state.messages.append({"role": "assistant", "content": response})
        store.append_message(user_id, conversation_id, "assistant", response)

        # Mostra informazioni aggiuntive
        st.markdown(
            f"<small>Model: {llm_model} | Temperature: {temperature} | Generation Time: {generation_time:.2f}s</small>",
            unsafe_allow_html=True
        )

        # Resetta lo stato di "Deep Research"
        st.session_state.deep_research = False
    elif "web_search" in st.session_state and st.session_state.web_search:
        # use the search method to retrieve the top5 results, append them to the prompt and then generate the response
        web_search_client = WebSearch()
        search_results = web_search_client.search(prompt, num_results=5)
        search_context = "\n".join([f"- {result['title']}: {result['content']}" for result in search_results])
        enhanced_prompt = f"{prompt}\n\nHere are some relevant search results:\n{search_context}"
        with st.chat_message("user"):
            st.markdown(f"**[Web Search]** {prompt}")
        st.session_state.messages.append({"role": "user", "content": prompt})
        store.append_message(user_id, conversation_id, "user", prompt)
        conv = store.get_conversation(user_id, conversation_id)
        if conv and not conv.get("title"):
            store.rename_conversation(user_id, conversation_id, prompt[:80])
        # Risposta dell'assistente in modalità Web Search
        start_time = time.time()  # Inizio del timer
        with st.chat_message("assistant"):
            response = st.write_stream(response_stream(AI, enhanced_prompt))
        generation_time = time.time() - start_time  # Calcolo del tempo di generazione
        st.session_state.messages.append({"role": "assistant", "content": response})
        store.append_message(user_id, conversation_id, "assistant", response)
        # Mostra informazioni aggiuntive
        st.markdown(
            f"<small>Model: {llm_model} | Temperature: {temperature} | Generation Time: {generation_time:.2f}s</small>",
            unsafe_allow_html=True
        )
        # Resetta lo stato di "Web Search"
        st.session_state.web_search = False
    else:
        # Modalità normale
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        store.append_message(user_id, conversation_id, "user", prompt)
        conv = store.get_conversation(user_id, conversation_id)
        if conv and not conv.get("title"):
            store.rename_conversation(user_id, conversation_id, prompt[:80])

        # Risposta dell'assistente in modalità normale
        start_time = time.time()  # Inizio del timer
        with st.chat_message("assistant"):
            response = st.write_stream(response_stream(AI, prompt))
        generation_time = time.time() - start_time  # Calcolo del tempo di generazione
        st.session_state.messages.append({"role": "assistant", "content": response})
        store.append_message(user_id, conversation_id, "assistant", response)

        # Mostra informazioni aggiuntive
        st.markdown(
            f"<small>Model: {llm_model} | Temperature: {temperature} | Generation Time: {generation_time:.2f}s</small>",
            unsafe_allow_html=True
        )

# (Old duplicated mode buttons removed)

# Sidebar: Previous Chats menu and modes
with st.sidebar.expander("Previous Chats", expanded=True):
    convs = store.list_conversations(user_id)
    if not convs:
        conv = store.get_conversation(user_id, conversation_id)
        convs = [conv] if conv else []

    labels = []
    ids = []
    current_index = 0
    for idx, c in enumerate(convs):
        title = c.get("title") or f"Conversation {c['id'][:8]}"
        labels.append(title)
        ids.append(c["id"])
        if c["id"] == conversation_id:
            current_index = idx

    if labels:
        selected = st.selectbox(
            "Select conversation",
            options=list(range(len(labels))),
            format_func=lambda i: labels[i],
            index=current_index,
            key="conversation_select",
        )
        selected_cid = ids[selected]
        if selected_cid != conversation_id:
            st.query_params["uid"] = user_id
            st.query_params["cid"] = selected_cid
            st.rerun()

    if st.button("New conversation", key="new_conv_btn"):
        new_cid = store.create_conversation(user_id)
        st.query_params["uid"] = user_id
        st.query_params["cid"] = new_cid
        st.session_state.messages = []
        st.session_state._loaded_cid = new_cid
        st.rerun()

with st.sidebar.expander("Modes", expanded=False):
    # Visual indicator only (tooltip shows mode)
    st.markdown(_indicator_html, unsafe_allow_html=True)
    if st.button("Deep Research", key="deep_research_btn"):
        current = st.session_state.get("deep_research", False)
        new_val = not current
        st.session_state.deep_research = new_val
        if new_val:
            st.session_state.web_search = False
    if st.button("Web Search", key="web_search_btn"):
        current = st.session_state.get("web_search", False)
        new_val = not current
        st.session_state.web_search = new_val
        if new_val:
            st.session_state.deep_research = False
    # Legend for mode icons/colors
    st.caption("Legend")
    _legend_html = """
    <div style="font-size: 0.9em; margin-top: 2px;">
      <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
        <span style="width:10px;height:10px;border-radius:50%;background:#8b5cf6;display:inline-block;"></span>
        <span>🔬 Deep Research</span>
      </div>
      <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
        <span style="width:10px;height:10px;border-radius:50%;background:#3b82f6;display:inline-block;"></span>
        <span>🔎 Web Search</span>
      </div>
      <div style="display:flex; align-items:center; gap:8px;">
        <span style="width:10px;height:10px;border-radius:50%;background:#9ca3af;display:inline-block;"></span>
        <span>💬 Normal</span>
      </div>
    </div>
    """
    st.markdown(_legend_html, unsafe_allow_html=True)
