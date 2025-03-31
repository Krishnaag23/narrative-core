"""
Vector Store Manager (ChromaDB)
===============================
- Handles embedding storage and retrieval for memory management.
- Supports similarity search for memory retrieval.
- Stores character, plot, theme, and world memories separately.
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import logging
import datetime

logger = logging.getLogger(__name__)

# Define memory collections
MEMORY_COLLECTIONS = ["character_memory", "plot_memory", "theme_memory", "world_memory"]

class VectorStoreManager:
    def __init__(self, persist_directory: str = "memory_db"):
        """
        Initializes the ChromaDB vector store.

        Args:
            persist_directory: Directory where the ChromaDB database is stored.
        """
        self.client = chromadb.PersistentClient(path=persist_directory, settings=Settings(allow_reset=True))
        self.collections = {name: self._get_or_create_collection(name) for name in MEMORY_COLLECTIONS}
        logger.info("VectorStoreManager initialized with persistence at %s", persist_directory)

    def _get_or_create_collection(self, name: str):
        """
        Retrieves an existing collection or creates a new one.

        Args:
            name: Name of the collection.

        Returns:
            The ChromaDB collection object.
        """
        try:
            return self.client.get_collection(name)
        except ValueError:
            logger.info(f"Creating new collection: {name}")
            return self.client.create_collection(name)

    def add_memory(self, collection_name: str, memory_text: str, embedding: List[float], metadata: Optional[Dict[str, Any]] = None):
        """
        Adds a new memory to the specified collection.

        Args:
            collection_name: Name of the memory collection.
            memory_text: The memory description.
            embedding: The vector embedding of the memory.
            metadata: Additional metadata like timestamp and importance.
        """
        if collection_name not in self.collections:
            raise ValueError(f"Collection '{collection_name}' does not exist.")

        memory_id = str(datetime.datetime.now().timestamp())
        metadata = metadata or {}
        metadata.update({"timestamp": memory_id, "event_description": memory_text})

        self.collections[collection_name].add(
            ids=[memory_id],
            documents=[memory_text],
            embeddings=[embedding],
            metadatas=[metadata]
        )

        logger.info(f"Added memory to {collection_name}: {memory_text[:50]}...")

    def retrieve_similar_memories(self, collection_name: str, query_embedding: List[float], top_k: int = 5):
        """
        Retrieves the top-k most similar memories from the collection.

        Args:
            collection_name: Name of the memory collection.
            query_embedding: The vector embedding to search for.
            top_k: Number of similar memories to retrieve.

        Returns:
            A list of retrieved memory descriptions.
        """
        if collection_name not in self.collections:
            raise ValueError(f"Collection '{collection_name}' does not exist.")

        results = self.collections[collection_name].query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents"]
        )

        return results.get("documents", [[]])[0]

    def delete_memory(self, collection_name: str, memory_id: str):
        """
        Deletes a memory from the specified collection.

        Args:
            collection_name: Name of the memory collection.
            memory_id: Unique ID of the memory to delete.
        """
        if collection_name not in self.collections:
            raise ValueError(f"Collection '{collection_name}' does not exist.")

        self.collections[collection_name].delete(ids=[memory_id])
        logger.info(f"Deleted memory {memory_id} from {collection_name}.")

    def reset_memory(self, collection_name: Optional[str] = None):
        """
        Deletes all memories from a specified collection or resets all.

        Args:
            collection_name: Name of the collection to reset. If None, resets all.
        """
        if collection_name:
            self.client.delete_collection(collection_name)
            self.collections[collection_name] = self._get_or_create_collection(collection_name)
            logger.info(f"Reset memory collection: {collection_name}")
        else:
            for name in MEMORY_COLLECTIONS:
                self.client.delete_collection(name)
                self.collections[name] = self._get_or_create_collection(name)
            logger.info("Reset all memory collections.")


