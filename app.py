import sys
import os
# assicurati che la root del progetto sia prioritaria nel path

import streamlit as st
from streamlit_chat import message
from backend.question_answering import QA
from backend.web_search import WebSearch
import time
from utils.utilities import response_stream, deep_research_response


# Sidebar
st.sidebar.title("Settings")
llm_model = st.sidebar.selectbox(
    "Select LLM Model",
    ["qwen2.5:1.5b", "llama3.2:3b", "mistral"]  # Replace with actual Ollama served models
)

temperature = st.sidebar.slider(
    "Temperature",
    min_value=0.0,
    max_value=1.0,
    value=0.5,
    step=0.1
)

AI = QA(model_name=llm_model, temperature=temperature)
# File uploader for document upload
st.sidebar.markdown("---")

uploaded_file = st.sidebar.file_uploader(
    "Upload a Document",
    type=["pdf", "docx", "txt"]
)

if uploaded_file:
    st.sidebar.success(f"Uploaded: {uploaded_file.name}")

# Main Page
st.title("WebRage Chatbot")
st.write("Ask me anything! I can help you with your questions.")
st.write("This is a simple chat interface powered by LLM.")

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("What is up?"):
    # Controlla se il pulsante "Deep Research" è stato cliccato
    if "deep_research" in st.session_state and st.session_state.deep_research:
        # Usa un metodo diverso per processare la query
        with st.chat_message("user"):
            st.markdown(f"**[Deep Research Mode]** {prompt}")
        st.session_state.messages.append({"role": "user", "content": f"[Deep Research Mode] {prompt}"})

        # Risposta dell'assistente in modalità Deep Research
        start_time = time.time()  # Inizio del timer
        with st.chat_message("assistant"):
            response = st.write_stream(deep_research_response(AI, prompt))
        generation_time = time.time() - start_time  # Calcolo del tempo di generazione
        st.session_state.messages.append({"role": "assistant", "content": response})

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
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": enhanced_prompt})  
        # Risposta dell'assistente in modalità Web Search
        start_time = time.time()  # Inizio del timer
        with st.chat_message("assistant"):
            response = st.write_stream(response_stream(AI, enhanced_prompt))
        generation_time = time.time() - start_time  # Calcolo del tempo di generazione
        st.session_state.messages.append({"role": "assistant", "content": response})
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

        # Risposta dell'assistente in modalità normale
        start_time = time.time()  # Inizio del timer
        with st.chat_message("assistant"):
            response = st.write_stream(response_stream(AI, prompt))
        generation_time = time.time() - start_time  # Calcolo del tempo di generazione
        st.session_state.messages.append({"role": "assistant", "content": response})

        # Mostra informazioni aggiuntive
        st.markdown(
            f"<small>Model: {llm_model} | Temperature: {temperature} | Generation Time: {generation_time:.2f}s</small>",
            unsafe_allow_html=True
        )

# Aggiungi il pulsante "Deep Research"
st.sidebar.markdown("---")
st.sidebar.title("Deep Research Mode")
st.sidebar.write("Enable Deep Research mode for more in-depth analysis.")
st.sidebar.write("This mode may take longer to respond.")
if st.sidebar.button("Deep Research"):
    st.session_state.deep_research = True
st.sidebar.markdown("---")
st.sidebar.title("Web Search Mode")
st.sidebar.write("Enable Web Search for further context.")
if st.sidebar.button("Web Search"):
    st.session_state.web_search = True

