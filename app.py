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

# Sidebar - Settings (always expanded)
with st.sidebar.expander("Settings", expanded=True):
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

# Removed mode indicator icons to simplify UI

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

# Sidebar: Chats
with st.sidebar.expander("Chats", expanded=True):
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

# Sidebar: Modes
with st.sidebar.expander("Modes", expanded=True):
    # Style active (primary) buttons in the sidebar as green (robust selectors)
    st.markdown(
        """
        <style>
        /* Streamlit primary buttons in the sidebar */
        div[data-testid="stSidebar"] .stButton > button[kind="primary"],
        div[data-testid="stSidebar"] button[data-testid="baseButton-primary"],
        div[data-testid="stSidebar"] .stButton > button.st-emotion-cache-primary {
            background-color: #22c55e !important; /* green */
            border-color: #16a34a !important;
            color: #ffffff !important;
        }
        div[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover,
        div[data-testid="stSidebar"] button[data-testid="baseButton-primary"]:hover,
        div[data-testid="stSidebar"] .stButton > button.st-emotion-cache-primary:hover {
            background-color: #16a34a !important;
            border-color: #15803d !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    dr_active = st.session_state.get("deep_research", False)
    ws_active = st.session_state.get("web_search", False)

    if st.button(
        "Deep Research",
        key="deep_research_btn",
        type=("primary" if dr_active else "secondary"),
        use_container_width=True,
    ):
        new_val = not dr_active
        st.session_state.deep_research = new_val
        if new_val:
            st.session_state.web_search = False
        st.rerun()

    if st.button(
        "Web Search",
        key="web_search_btn",
        type=("primary" if ws_active else "secondary"),
        use_container_width=True,
    ):
        new_val = not ws_active
        st.session_state.web_search = new_val
        if new_val:
            st.session_state.deep_research = False
        st.rerun()

# Sidebar: Upload (move to bottom)
with st.sidebar.expander("Upload", expanded=True):
    uploaded_file = st.file_uploader(
        "Upload a Document",
        type=["pdf", "docx", "txt"],
        key="doc_uploader",
    )
    if uploaded_file:
        st.success(f"Uploaded: {uploaded_file.name}")
