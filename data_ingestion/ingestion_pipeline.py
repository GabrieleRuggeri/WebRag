from text_extraction import DocumentExtractor
from chunking_embedding import Chunker, Embedder
from vector_store import VectorStore
import uuid
from utils.logging_config import configure_logging_from_env, get_logger

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class IngestionPipeline:
    def __init__(self):
        # configure based on env and create a module logger
        configure_logging_from_env(log_file=None)
        self.logger = get_logger(__name__)
        self.logger.info("Initializing IngestionPipeline")
        self.extractor = DocumentExtractor()
        self.chunker = Chunker()
        self.embedder = Embedder()
        self.logger.info("IngestionPipeline components initialized successfully")

    def _setup_logging(self):
        # legacy method kept for compatibility but no longer used; configuration
        # is performed centrally via utils.logging_config.configure_logging_from_env
        pass

    def run(self, file_path: str):
        """
        Run the ingestion pipeline.

        :param file_path: Path to the document.
        """
        try:
            self.logger.info(f"Starting ingestion pipeline for file: {file_path}")
            
            # Extract text and images
            self.logger.debug("Extracting text from document")
            text = self.extractor.extract_text(file_path)
            self.logger.info(f"Successfully extracted {len(text)} text segments")
            
            self.logger.debug("Extracting images from document")
            images = self.extractor.extract_images(file_path)
            self.logger.info(f"Successfully extracted {len(images)} images")

            # Chunk text
            self.logger.debug("Chunking extracted text")
            chunks = self.chunker.chunk_text(text)
            self.logger.info(f"Created {len(chunks)} chunks from text")

            # Create embeddings
            self.logger.debug("Generating embeddings for chunks")
            embeddings = self.embedder.embed(chunks)
            self.logger.info(f"Generated {len(embeddings)} embeddings")

            # Store in vector database
            self.logger.debug("Initializing vector store")
            vector_store = VectorStore()
            
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings), 1):
                try:
                    guid = str(uuid.uuid4())
                    metadata = {
                        "file_path": file_path,
                        "length": len(chunk),
                        "chunk_index": i
                    }
                    vector_store.add_data(guid, chunk, embedding, metadata)
                    self.logger.debug(f"Added chunk {i}/{len(chunks)} with GUID: {guid}")
                except Exception as e:
                    self.logger.error(f"Failed to add chunk {i} to vector store: {str(e)}")
                    raise
            
            self.logger.info("Ingestion pipeline completed successfully")
            
        except Exception as e:
            self.logger.error(f"Ingestion pipeline failed: {str(e)}")
            raise

    def test(self):
        """
        Test the ingestion pipeline.
        """
        try:
            self.logger.info("Starting ingestion pipeline test")
            test_file_path = "data/pdf_test.pdf"
            self.run(test_file_path)
            self.logger.info("Ingestion pipeline test completed successfully")
        except Exception as e:
            self.logger.error(f"Ingestion pipeline test failed: {str(e)}")
            raise

# if __name__ == "__main__":
#     pipeline = IngestionPipeline()
#     pipeline.test()