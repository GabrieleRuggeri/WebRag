import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data_ingestion.vector_store import VectorStore
from data_ingestion.chunking_embedding import Embedder

class Retriever:
    
    def __init__(self, vector_store: VectorStore, embedder: Embedder):
        self.vector_store = vector_store
        self.embedder = embedder

    def retrieve(self, query: str, top_k: int = 3) -> list:
        """
        Retrieve the top_k most relevant documents for a given query.
        
        Args:
            query (str): The query string to search for.
            top_k (int): The number of top documents to retrieve.
        
        Returns:
            list: A list of tuples containing the document ID and its relevance score.
        """
        # Embed the query
        query_embedding = self.embedder.encode([query])[0]
        
        # Retrieve the top_k documents from the vector store
        results = self.vector_store.search(query_embedding, top_k)
        results = [(guid, self.vector_score.vector_store[guid], score) for guid, score in results if self.vector_store.get_data(guid)["text"] is not None]
        
        return results
        