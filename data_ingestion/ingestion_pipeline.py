from text_extraction import DocumentExtractor
from chunking_embedding import Chunker, Embedder
from ..embedding import Embedder
from vector_store import VectorStore
import uuid
import logging


class IngestionPipeline:
    def __init__(self):
        self.extractor = DocumentExtractor()
        self.chunker = Chunker()
        self.embedder = Embedder()

    def run(self, file_path: str):
        """
        Run the ingestion pipeline.

        :param file_path: Path to the document.
        """
        # Extract text and images from the document
        text : list   = self.extractor.extract_text(file_path)
        images : list = self.extractor.extract_images(file_path)

        # Chunk the extracted text
        chunks = self.chunker.chunk_text(text)

        # Embed the chunks
        embeddings = self.embedder.embed(chunks)

        # Store the embeddings in the vector store
        vector_store = VectorStore()
        for chunk, embedding in zip(chunks, embeddings):
            guid = str(uuid.uuid4())
            data_entry = {
                guid : {
                    "text": chunk,
                    "embedding": embedding,
                    "metadata": {
                        "file_path": file_path,
                        "length": len(chunk)
                    }
                }
            }
            vector_store.add_data(**data_entry)
            print(f"Added chunk with GUID: {guid}")

    def test(self):
        """
        Test the ingestion pipeline.
        """
        test_file_path = "pdf_test.pdf"
        self.run(test_file_path)
        print("Ingestion pipeline test completed.")