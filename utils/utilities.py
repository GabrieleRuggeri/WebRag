import time
from backend.question_answering import QA

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
