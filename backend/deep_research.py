from .question_answering import QA
from .web_search import WebSearch
from .reranker import Reranker

class DeepResearch:

    def __init__(self):
        self.reformulator = QA(model_name="qwen2.5:1.5b", temperature=0.6)
        self.llm = QA(model_name="qwen2.5:1.5b", temperature=0.1)
        self.web_search = WebSearch()
        self.reranker = Reranker()
        self.system_prompt = """
        You are an AI expert in reformulating user queries in order to provide an equivalent formulation in meaning but different in the form. 
        Your task is to enhance user queries by generating a single reformulation to improve search results."""

    def enhance_query(self, query:str, reformulations:int = 3) -> list[str]:
        # use an LLM to generate reformulations of the query
        reformulations_list = [self.reformulator.run(f"{self.system_prompt}\nUser query: {query}") for i in range(reformulations)]
        return reformulations_list
        

    def search(self, query:str, reformulations:int = 3, topk_context:int = 5) -> str:
        # steps:
        # 1) enhance the query with other variations
        reformulations_list = self.enhance_query(query, reformulations)
        # 2) search the web with the enhanced queries
        web_results = [self.web_search.search(i, num_results=topk_context) for i in reformulations_list]
        web_results = [item['content'] for sublist in web_results for item in sublist]  # flatten
        # 3) gather search results and take a topk
        scores = self.reranker.rerank(query, [chunk for chunk in web_results])
        topk_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:topk_context]
        topk_contexts = [web_results[i] for i in topk_indices]
        web_context = "\n".join(topk_contexts)
        # 4) pass the context to the LLM
        enhanced_prompt = f"Using the following web search results, provide a comprehensive answer to the query: {query}\n\nWeb search results:\n{web_context}"
        response = self.llm.run(enhanced_prompt)
        return response
    
if __name__ == "__main__":
    dr = DeepResearch()
    query = "what has happend in Gaza in September 2025?"
    response = dr.search(query)
    print("Response:", response)

