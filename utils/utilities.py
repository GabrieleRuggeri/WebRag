import time
from backend.question_answering import QA
from typing import List, Dict

def response_stream(AI : QA, prompt : str):
    """
    Function to stream the response from the AI model.
    """
    response = AI.run(prompt)
    for word in response.split():
        yield word + " "
        time.sleep(0.05)

# Funzione per la modalità Deep Research
def deep_research_response(AI: QA, prompt: str):
    """
    Funzione per elaborare la risposta in modalità Deep Research.
    """
    # response = AI.run_deep_research(prompt)  # Supponendo che QA abbia un metodo `run_deep_research`
    response = "fake message with deep-search"
    for word in response.split():
        yield word + " "
        time.sleep(0.1)


def generate_conversation_title(
    AI: QA,
    messages: List[Dict[str, str]],
    fallback_content: str = "",
    max_messages: int = 10,
    max_title_words: int = 8,
    max_len: int = 80,
) -> str:
    """
    Generate a concise conversation title using the LLM from a list of messages.

    The function does not interact with storage; it only returns a title.
    """
    try:
        recent = messages[-max_messages:] if len(messages) > max_messages else messages
        convo_snippet = "\n".join([f"{m['role']}: {m['content']}" for m in recent])
        title_prompt = (
            "You are helping to name a chat thread.\n"
            f"Given the following conversation messages, generate a concise, descriptive title of maximum {max_title_words} words. "
            "Do not include quotes or trailing punctuation.\n\n"
            f"Conversation messages:\n{convo_snippet}\n\nTitle:"
        )
        raw_title = AI.run(title_prompt)
        title = (raw_title or "").strip().splitlines()[0]
        # Cleanup
        title = title.strip("\"' ")
        if title.endswith((".", "!", "?", ":", ";")):
            title = title[:-1]
        # Word cap
        words = title.split()
        if len(words) > max_title_words:
            title = " ".join(words[:max_title_words])
        if not title:
            title = fallback_content[:max_len]
        return title[:max_len]
    except Exception:
        return (fallback_content or "")[:max_len]
