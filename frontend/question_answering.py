import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from llm.llm import LLM

class QA:

    def __init__(self, model_name: str = "llama3.1:8b", temperature: float = 0.1):
        """
        Initialize the QA class.
        """
        self.model = LLM(
            model_id=model_name, 
            temperature=temperature)
        

    def run(self, query: str) -> str:
        """
        Run the QA process.
        """
        response = self.model.chat(query)
        return response
    
    def test(self):
        """
        Test the QA process with a sample query.
        """
        query = "What is the capital of France?"
        response = self.run(query)
        print(f"Response: {response}")


if __name__ == "__main__":
    # Example usage
    qa = QA()
    qa.test()
