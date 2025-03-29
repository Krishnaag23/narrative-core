"""
Manages the ChromaDB client instance and specific collections
for the character system (embeddings, memories).
Ensures a single client instance is used.
"""

import chromadb
import logging
import os
from chromadb.config import Settings

logger = logging.getLogger(__name__)

# Define collection names centrally
CHARACTER_EMBEDDINGS_COLLECTION = "character_aspects"
CHARACTER_MEMORIES_COLLECTION = "character_memories"

class VectorStoreManager:
    _instance = None
    _client = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(VectorStoreManager, cls).__new__(cls)
            try:
                # Configure ChromaDB - Use persistent storage
                persist_directory = os.path.join(os.getcwd(), ".chroma_db_persistence")
                if not os.path.exists(persist_directory):
                    os.makedirs(persist_directory)
                    logger.info(f"Created ChromaDB persistence directory: {persist_directory}")

                cls._client = chromadb.PersistentClient(
                    path=persist_directory,
                    settings=Settings(
                    #TODO: add chroma db settings as and when needed.
                    )
                )
                logger.info(f"ChromaDB PersistentClient initialized. Storing data in: {persist_directory}")
                # Ensure collections exist
                cls._instance.get_or_create_collection(CHARACTER_EMBEDDINGS_COLLECTION)
                cls._instance.get_or_create_collection(CHARACTER_MEMORIES_COLLECTION)

            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB client: {e}", exc_info=True)
                # Fallback to in-memory if persistence fails (for resilience during dev)
                try:
                    logger.warning("Falling back to in-memory ChromaDB client.")
                    cls._client = chromadb.Client() # In-memory
                    logger.info("ChromaDB InMemoryClient initialized.")
                    cls._instance.get_or_create_collection(CHARACTER_EMBEDDINGS_COLLECTION)
                    cls._instance.get_or_create_collection(CHARACTER_MEMORIES_COLLECTION)
                except Exception as inner_e:
                    logger.critical(f"FATAL: Failed to initialize even in-memory ChromaDB: {inner_e}", exc_info=True)
                    cls._client = None # Mark as unavailable

        return cls._instance

    def get_client(self):
        """Returns the initialized ChromaDB client instance."""
        if self._client is None:
             raise RuntimeError("ChromaDB client is not initialized. Check logs for errors.")
        return self._client

    def get_or_create_collection(self, name: str, embedding_function_name: str = "default"):
        """Gets or creates a ChromaDB collection."""
        client = self.get_client()
        try:
             # Using default SentenceTransformer embedding function provided by Chroma
             # TODO: Test if other custom embedding fuction provide better performance 
             collection = client.get_or_create_collection(name=name)
             logger.info(f"Accessed or created ChromaDB collection: '{name}'")
             return collection
        except Exception as e:
            logger.error(f"Failed to get or create collection '{name}': {e}", exc_info=True)
            raise

    def get_character_embedding_collection(self):
        """Convenience method to get the character aspects collection."""
        return self.get_or_create_collection(CHARACTER_EMBEDDINGS_COLLECTION)

    def get_character_memory_collection(self):
        """Convenience method to get the character memories collection."""
        return self.get_or_create_collection(CHARACTER_MEMORIES_COLLECTION)
