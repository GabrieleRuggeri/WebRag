import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from llm.llama_3_1 import Llama31_8B

class QA:

    def __init__(self):
        """
        Initialize the QA class.
        """
        self.model = Llama31_8B()
        

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
