import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from streamlit_chat import message
from question_answering import QA
import time

AI = QA()

def response_stream(AI : QA, prompt : str):
    """
    Function to stream the response from the AI model.
    """
    response = AI.run(prompt)
    for word in response.split():
        yield word + " "
        time.sleep(0.05)

# Sidebar
st.sidebar.title("Settings")
llm_model = st.sidebar.selectbox(
    "Select LLM Model",
    ["llama3.1:8b"]  # Replace with actual Ollama served models
)

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
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        response = st.write_stream(response_stream(AI, prompt))
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})

    