import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from embedding.embedder import EmbeddingModel
import numpy as np

class Chunker:

    def __init__(self):
        pass

    def chunk_text(self, texts: list) -> list:
        chunks = []
        for text in texts:
            # Split the text into chunks
            current_chunks = text.split("\n\n")
            # Remove empty chunks
            current_chunks = [chunk for chunk in current_chunks if chunk.strip()]
            # Add the chunks to the list
            chunks.extend(current_chunks)
        # Remove duplicates
        return chunks
    
class Embedder:

    def __init__(self):
        self.model = EmbeddingModel()

    def embed(self, chunks: list) -> list:
        embeddings = []
        for chunk in chunks:
            # Generate embedding for each chunk
            embedding = np.ndarray([])
            try:
                embedding = self.model.encode(query=chunk, type_query="search_document")
            except Exception as e:
                print(f"Error generating embedding for chunk: {chunk}\nError: {e}")
                continue
            embeddings.append(embedding)
        return embeddings
    

if __name__ == "__main__":
    # Example usage
    chunker = Chunker()
    embedder = Embedder()

    texts = [
        "This is the first chunk.\n\nThis is the second chunk.",
        "This is another document.\n\nIt has multiple paragraphs."
    ]

    chunks = chunker.chunk_text(texts)
    embeddings = embedder.embed(chunks)

    print("Chunks:", chunks)
    print("Embeddings:", embeddings)
        
        
    
    

