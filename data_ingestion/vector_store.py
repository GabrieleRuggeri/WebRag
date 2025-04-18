import os
import json 
import uuid
import numpy as np

DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data')

class VectorStore:

    def __init__(self):
        file_in_folder : list = os.listdir(DATA_PATH)
        if "vector_store.json" not in file_in_folder:
            self.vector_store = {
                "mock_guid" : {"text": None, "embedding" : None, "metadata": None}
            }

            with open(os.path.join(DATA_PATH, "vector_store.json"), 'w') as f:
                json.dump(self.vector_store, f)
        else:
            with open(os.path.join(DATA_PATH, "vector_store.json"), 'r') as f:
                self.vector_store = json.load(f)


    def add_data(self, guid, text, embedding, metadata):
        """
        Add data to the vector store.

        :param guid: Unique identifier for the data.
        :param text: Text data.
        :param embedding: Embedding data.
        :param metadata: Metadata associated with the data.
        """
        self.vector_store[guid] = {
            "text": text,
            "embedding": embedding,
            "metadata": metadata
        }
        self._save_vector_store()
        print(f"Added data with GUID: {guid}")
    
    def get_data(self, guid):
        """
        Retrieve data from the vector store.

        :param guid: Unique identifier for the data.
        :return: Data associated with the GUID.
        """
        return self.vector_store.get(guid, None)
    
    def _save_vector_store(self):
        """
        Save the vector store to a JSON file.
        """
        def default(o):
            if isinstance(o, np.ndarray):
                return o.tolist()
            raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")
        
        with open(os.path.join(DATA_PATH, "vector_store.json"), 'w') as f:
            json.dump(self.vector_store, f, default=default)


    def delete_data(self, guid):
        """
        Delete data from the vector store.

        :param guid: Unique identifier for the data.
        """
        if guid in self.vector_store:
            del self.vector_store[guid]
            self._save_vector_store()
            print(f"Deleted data with GUID: {guid}")
        else:
            print(f"GUID {guid} not found in vector store.")

    def update_data(self, guid, text=None, embedding=None, metadata=None):
        """
        Update data in the vector store.

        :param guid: Unique identifier for the data.
        :param text: Updated text data.
        :param embedding: Updated embedding data.
        :param metadata: Updated metadata associated with the data.
        """
        if guid in self.vector_store:
            if text is not None:
                self.vector_store[guid]["text"] = text
            if embedding is not None:
                self.vector_store[guid]["embedding"] = embedding
            if metadata is not None:
                self.vector_store[guid]["metadata"] = metadata
            self._save_vector_store()
            print(f"Updated data with GUID: {guid}")
        else:
            print(f"GUID {guid} not found in vector store.")    
    
    def test(self):
        """
        Test the vector store functionality.
        """
        test_guid = str(uuid.uuid4())
        test_text = "This is a test text."
        test_embedding = [0.1, 0.2, 0.3]
        test_metadata = {"file_path": "test.txt", "length": len(test_text)}

        self.add_data(test_guid, test_text, test_embedding, test_metadata)
        print(self.get_data(test_guid))
        
        self.update_data(test_guid, text="Updated text.")
        print(self.get_data(test_guid))
        
        self.delete_data(test_guid)
        print(self.get_data(test_guid))

# if __name__ == "__main__":
#     vector_store = VectorStore()
#     vector_store.test()
            






