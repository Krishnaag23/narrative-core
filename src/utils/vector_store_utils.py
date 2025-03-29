"""
Utility class providing an interface for interacting with a vector database,
specifically ChromaDB. Handles client initialization, collection management,
and common operations like adding, querying, and updating data.
"""
import os 
import logging
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Optional, Any, Tuple

from .config import settings 

logger = logging.getLogger(__name__)

# Define types for clarity
Metadata = Dict[str, Any]
QueryResult = List[Dict[str, Any]] # List of dicts like {"id": str, "document": str, "metadata": Metadata, "distance": float}
GetResult = List[Dict[str, Any]]   # List of dicts like {"id": str, "document": str, "metadata": Metadata}


class VectorStoreInterface:
    _instance = None
    _client: Optional[chromadb.ClientAPI] = None
    _collections: Dict[str, chromadb.Collection] = {} # Cache collections

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(VectorStoreInterface, cls).__new__(cls)
            cls._instance._initialize_client()
        return cls._instance

    def _initialize_client(self):
        """Initializes the ChromaDB client (persistent or in-memory)."""
        if self._client is not None:
            return # Already initialized

        try:
            path = settings.VECTOR_DB_PATH
            logger.info(f"Initializing ChromaDB client with path: {path}")
            # Ensure parent directory exists for persistent client
            if not os.path.exists(os.path.dirname(path)):
                 os.makedirs(os.path.dirname(path), exist_ok=True)
                 logger.info(f"Created parent directory for ChromaDB: {os.path.dirname(path)}")

            self._client = chromadb.PersistentClient(
                path=path,
                settings=ChromaSettings(
                    # Optional: Add anonymized_telemetry=False, etc.
                )
            )
            logger.info(f"ChromaDB PersistentClient initialized successfully at {path}.")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB PersistentClient at {settings.VECTOR_DB_PATH}: {e}", exc_info=True)
            try:
                logger.warning("Falling back to in-memory ChromaDB client.")
                self._client = chromadb.Client()
                logger.info("ChromaDB InMemoryClient initialized successfully.")
            except Exception as inner_e:
                logger.critical(f"FATAL: Failed to initialize even in-memory ChromaDB: {inner_e}", exc_info=True)
                self._client = None # Mark as unavailable

    def get_client(self) -> Optional[chromadb.ClientAPI]:
         """Returns the raw ChromaDB client instance if available."""
         return self._client

    def get_or_create_collection(self, name: str, embedding_function_name: str = "default") -> Optional[chromadb.Collection]:
        """
        Gets an existing collection or creates a new one. Caches collection objects.

        Args:
            name: The name of the collection.
            embedding_function_name: Name of embedding function (Chroma handles 'default').

        Returns:
            The ChromaDB Collection object, or None on failure.
        """
        if self._client is None:
            logger.error("Vector store client is not initialized.")
            return None

        if name in self._collections:
            return self._collections[name]

        try:
            # Let Chroma handle the default embedding function resolution
            # Requires `pip install sentence-transformers` for the default
            collection = self._client.get_or_create_collection(name=name)
            self._collections[name] = collection # Cache it
            logger.info(f"Accessed or created ChromaDB collection: '{name}'")
            return collection
        except Exception as e:
            logger.error(f"Failed to get or create collection '{name}': {e}", exc_info=True)
            return None

    def add(self, collection_name: str, ids: List[str], documents: List[str], metadatas: Optional[List[Metadata]] = None) -> bool:
        """
        Adds documents and their embeddings to a collection. Chroma handles embedding.

        Args:
            collection_name: The name of the target collection.
            ids: A list of unique IDs for the documents.
            documents: A list of document texts to embed and store.
            metadatas: Optional list of metadata dictionaries corresponding to each document.

        Returns:
            True if successful, False otherwise.
        """
        collection = self.get_or_create_collection(collection_name)
        if not collection:
            return False

        try:
            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            logger.debug(f"Added {len(ids)} items to collection '{collection_name}'.")
            return True
        except Exception as e:
            logger.error(f"Failed to add items to collection '{collection_name}': {e}", exc_info=True)
            return False

    def upsert(self, collection_name: str, ids: List[str], documents: List[str], metadatas: Optional[List[Metadata]] = None) -> bool:
        """
        Updates existing documents or adds new ones to a collection.

        Args:
            collection_name: The name of the target collection.
            ids: A list of unique IDs for the documents.
            documents: A list of document texts to embed and store/update.
            metadatas: Optional list of metadata dictionaries corresponding to each document.

        Returns:
            True if successful, False otherwise.
        """
        collection = self.get_or_create_collection(collection_name)
        if not collection:
            return False

        try:
            collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            logger.debug(f"Upserted {len(ids)} items in collection '{collection_name}'.")
            return True
        except Exception as e:
            logger.error(f"Failed to upsert items in collection '{collection_name}': {e}", exc_info=True)
            return False

    def query(self, collection_name: str, query_texts: List[str], n_results: int = 5, where_filter: Optional[Dict[str, Any]] = None) -> QueryResult:
        """
        Queries a collection for documents semantically similar to query texts.

        Args:
            collection_name: The name of the collection to query.
            query_texts: A list of query texts.
            n_results: The number of results to return for each query text.
            where_filter: Optional dictionary for metadata filtering (e.g., {"character_id": "xyz"}).

        Returns:
            A list containing results for each query text. Each result is a list of dictionaries,
            where each dictionary represents a found document with its id, text, metadata, and distance.
            Returns an empty list if the query fails or the collection doesn't exist.
        """
        collection = self.get_or_create_collection(collection_name)
        if not collection:
            return [] * len(query_texts) # Return list of empty lists matching query count

        try:
            results = collection.query(
                query_texts=query_texts,
                n_results=n_results,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )

            # Process results into the desired QueryResult format
            processed_results = []
            all_ids = results.get('ids', [])
            all_distances = results.get('distances', [])
            all_metadatas = results.get('metadatas', [])
            all_documents = results.get('documents', [])

            num_queries = len(query_texts)
            for i in range(num_queries):
                query_result = []
                # Check if results exist for this specific query index i
                ids = all_ids[i] if i < len(all_ids) else []
                distances = all_distances[i] if i < len(all_distances) else [None] * len(ids)
                metadatas = all_metadatas[i] if i < len(all_metadatas) else [{}] * len(ids)
                documents = all_documents[i] if i < len(all_documents) else [""] * len(ids)

                for j, doc_id in enumerate(ids):
                    query_result.append({
                        "id": doc_id,
                        "distance": distances[j] if distances else None,
                        "metadata": metadatas[j] if metadatas else None,
                        "document": documents[j] if documents else None,
                    })
                processed_results.append(query_result)

            logger.debug(f"Query in collection '{collection_name}' returned {sum(len(qr) for qr in processed_results)} total results for {num_queries} queries.")
            return processed_results

        except Exception as e:
            logger.error(f"Error querying collection '{collection_name}': {e}", exc_info=True)
            return [[]] * len(query_texts) # Return list of empty lists

    def get_items(self, collection_name: str, ids: Optional[List[str]] = None, where_filter: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> GetResult:
        """
        Retrieves items from a collection by ID or metadata filter.

        Args:
            collection_name: The name of the collection.
            ids: Optional list of IDs to retrieve.
            where_filter: Optional metadata filter.
            limit: Optional maximum number of items to retrieve.

        Returns:
            A list of dictionaries, each representing a retrieved item with id, document, and metadata.
            Returns empty list on failure or if no items match.
        """
        collection = self.get_or_create_collection(collection_name)
        if not collection:
            return []

        try:
            results = collection.get(
                ids=ids,
                where=where_filter,
                limit=limit,
                include=["documents", "metadatas"]
            )

            # Process results into the desired GetResult format
            processed_results = []
            result_ids = results.get('ids', [])
            result_metadatas = results.get('metadatas', [])
            result_documents = results.get('documents', [])

            for i, doc_id in enumerate(result_ids):
                 processed_results.append({
                    "id": doc_id,
                    "metadata": result_metadatas[i] if i < len(result_metadatas) else None,
                    "document": result_documents[i] if i < len(result_documents) else None,
                })

            logger.debug(f"Get operation in '{collection_name}' retrieved {len(processed_results)} items.")
            return processed_results

        except Exception as e:
            logger.error(f"Error getting items from collection '{collection_name}': {e}", exc_info=True)
            return []

    def delete_collection(self, collection_name: str) -> bool:
        """Deletes a collection entirely."""
        if self._client is None:
            logger.error("Vector store client is not initialized.")
            return False
        try:
            self._client.delete_collection(name=collection_name)
            if collection_name in self._collections:
                del self._collections[collection_name] # Remove from cache
            logger.info(f"Successfully deleted collection: '{collection_name}'.")
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection '{collection_name}': {e}", exc_info=True)
            # Collection might not exist, which can be ok depending on context
            return False


