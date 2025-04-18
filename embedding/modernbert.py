from sentence_transformers import SentenceTransformer
from numpy import ndarray
from torch import Tensor

class EmbeddingModel:
    def __init__(self, model_name: str = "nomic-ai/modernbert-embed-base"):
        
        self.model = SentenceTransformer(model_name)

    def encode(self, query : str, type_query : str) -> list:
        '''
        Encodes the query into a vector representation.
        :param query: The query string to encode.
        :param type: The type of the query (e.g., "search_query" or "search_document").
        :return: The encoded vector representation of the query.
        '''
        if type_query not in ["search_query", "search_document"]:
            raise ValueError("Type must be 'search_query' or 'search_document'")
        
        input_query = [f"{type_query}: {query}"]
        return self.model.encode(input_query)

    def similarity(self, query_embeddings : ndarray, doc_embeddings : ndarray) -> Tensor:
        return self.model.similarity(query_embeddings, doc_embeddings)
    
    def test(self):
        '''
        Test the embedding model with a sample query and document.
        :return: None
        '''
        query_embeddings = self.encode("What is TSNE?", "search_query")
        doc_embeddings = self.encode("TSNE is a dimensionality reduction algorithm created by Laurens van Der Maaten", "search_document")
        
        similarities = self.similarity(query_embeddings, doc_embeddings)
        print(similarities)


# if __name__ == "__main__":
#     # Example usage
#     embedding_model = EmbeddingModel("nomic-ai/modernbert-embed-base")
#     embedding_model.test()