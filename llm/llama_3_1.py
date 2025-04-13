from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama.llms import OllamaLLM


class Llama31_8B:
    def __init__(self, model_id : str = "llama3.1:8b", temperature: float = 0.1):
        """
        Initialize the Llama31_8B class.

        :param port: The port number of the locally hosted Ollama server.
        """
        self.model_id = model_id
        self.temperature = temperature
        self.model = OllamaLLM(model=self.model_id, temperature=self.temperature)
        self.template = "{question}"
        self.prompt = ChatPromptTemplate.from_template(self.template)
        self.chain = self.prompt | self.model

    def chat(self, query: str) -> str:
        """
        Send a query to the locally hosted Llama 3.1:8B model and return the response.

        :param query: The input prompt to send to the model.
        :return: The model's response to the input prompt.
        """
        
        return self.chain.invoke({"question": query})
        
    def test(self):
        """
        Test the Llama31_8B model with a sample query.
        """
        query = "What is the capital of France?"
        response = self.chat(query)
        print(f"Response: {response}")

if __name__ == "__main__":
    # Example usage
    llama = Llama31_8B()
    llama.test()
        