"""
Memory Optimizer
================
- Prunes low-importance and outdated memories.
- Merges similar memories to reduce redundancy.
- Compresses large memory structures for efficiency.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sklearn.cluster import DBSCAN
import numpy as np

from .vector_store_manager import VectorStoreManager, MEMORY_COLLECTIONS

logger = logging.getLogger(__name__)

class MemoryOptimizer:
    def __init__(self, retention_period: int = 168, similarity_threshold: float = 0.85):
        """
        Initializes the memory optimizer.

        Args:
            retention_period: Time (in hours) before pruning low-importance memories.
            similarity_threshold: Clustering threshold for merging similar memories.
        """
        self.vector_store_manager = VectorStoreManager()
        self.retention_period = timedelta(hours=retention_period)
        self.similarity_threshold = similarity_threshold
        
        logger.info("MemoryOptimizer initialized with retention period of %d hours.", retention_period)

    def prune_memories(self, collection_name: str, importance_threshold: float = 0.3):
        """
        Removes low-importance and outdated memories.

        Args:
            collection_name: The memory collection to optimize.
            importance_threshold: Minimum importance score to retain a memory.
        """
        collection = self.vector_store_manager.get_collection(collection_name)
        now = datetime.now()
        past_time = now - self.retention_period

        try:
            results = collection.query(
                query_texts=[""],
                n_results=100,
                include=["metadatas"]
            )

            for metadata in results.get('metadatas', [[]])[0]:
                timestamp = datetime.fromisoformat(metadata["timestamp"])
                importance = float(metadata.get("importance", 0.5))

                if timestamp < past_time or importance < importance_threshold:
                    collection.delete(ids=[metadata["timestamp"]])
                    logger.info(f"Pruned memory: {metadata['event_description'][:50]}...")

        except Exception as e:
            logger.error(f"Error pruning memories in {collection_name}: {e}", exc_info=True)

    def merge_similar_memories(self, collection_name: str):
        """
        Merges similar memories to prevent redundancy.

        Args:
            collection_name: The memory collection to optimize.
        """
        collection = self.vector_store_manager.get_collection(collection_name)

        try:
            results = collection.query(
                query_texts=[""],
                n_results=100,
                include=["documents", "metadatas", "embeddings"]
            )

            embeddings = np.array(results.get('embeddings', [[]])[0])
            metadatas = results.get('metadatas', [[]])[0]
            documents = results.get('documents', [[]])[0]

            if not embeddings.size:
                return

            clustering = DBSCAN(eps=1 - self.similarity_threshold, min_samples=2, metric='cosine').fit(embeddings)
            cluster_labels = clustering.labels_

            merged_memories = {}
            for idx, label in enumerate(cluster_labels):
                if label == -1:
                    continue  # Outliers are not merged
                if label not in merged_memories:
                    merged_memories[label] = {"text": [], "importance": 0, "count": 0}
                
                merged_memories[label]["text"].append(documents[idx])
                merged_memories[label]["importance"] += float(metadatas[idx].get("importance", 0.5))
                merged_memories[label]["count"] += 1

            for label, data in merged_memories.items():
                merged_text = " ".join(data["text"])
                avg_importance = data["importance"] / data["count"]
                timestamp = datetime.now().isoformat()

                # Add merged memory
                collection.add(
                    ids=[timestamp],
                    documents=[merged_text],
                    metadatas=[{"timestamp": timestamp, "event_description": merged_text, "importance": avg_importance}]
                )

                logger.info(f"Merged {data['count']} similar memories into one.")

                # Delete old clustered memories
                for idx, label_check in enumerate(cluster_labels):
                    if label_check == label:
                        collection.delete(ids=[metadatas[idx]["timestamp"]])

        except Exception as e:
            logger.error(f"Error merging similar memories in {collection_name}: {e}", exc_info=True)

    def optimize_all_memories(self):
        """
        Runs optimization across all memory types (character, plot, theme, world).
        """
        for collection_name in MEMORY_COLLECTIONS:
            self.prune_memories(collection_name)
            self.merge_similar_memories(collection_name)

        logger.info("Memory optimization complete.")
