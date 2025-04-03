#I don't think this is needed as IT is implemented in the character system module already. Check the methods once and use 
# those which are already created to get rid of redundancies.
"""
Episodic Memory System
======================
Stores short-term memory of recent events, affecting immediate decisions.
Automatically moves important memories to long-term storage.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from .vector_store_manager import VectorStoreManager, EPISODIC_MEMORY_COLLECTION
from .character_memory_manager import CharacterMemoryManager  # For long-term transfer

logger = logging.getLogger(__name__)

class EpisodicMemory:
    def __init__(self, retention_period: int = 48):
        """
        Initializes episodic memory with a retention period.

        Args:
            retention_period: Time (in hours) before memories are deleted or transferred.
        """
        self.vector_store_manager = VectorStoreManager()
        self.collection = self.vector_store_manager.get_collection(EPISODIC_MEMORY_COLLECTION)
        self.character_memory_manager = CharacterMemoryManager()
        self.retention_period = timedelta(hours=retention_period)
        
        logger.info("EpisodicMemory initialized with retention period of %d hours.", retention_period)

    def add_memory(self, character_id: str, event_description: str, importance: float = 0.5):
        """
        Stores a short-term memory event.

        Args:
            character_id: The ID of the character experiencing the event.
            event_description: A detailed event description.
            importance: A score (0-1) indicating the event's significance.
        """
        timestamp = datetime.now()
        memory = {
            "character_id": character_id,
            "timestamp": timestamp.isoformat(),
            "event_description": event_description,
            "importance": importance
        }

        self.collection.add(
            ids=[str(timestamp.timestamp())],
            documents=[event_description],
            metadatas=[memory]
        )

        logger.info(f"Episodic memory stored for character {character_id}: {event_description[:50]}...")

    def retrieve_recent_memories(self, character_id: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves the most recent episodic memories.

        Args:
            character_id: The character whose memories should be fetched.
            n_results: Number of recent memories to return.

        Returns:
            A list of recent episodic memories.
        """
        try:
            now = datetime.now()
            past_time = now - self.retention_period

            results = self.collection.query(
                query_texts=[""],
                n_results=n_results,
                where={"character_id": character_id, "timestamp": {"$gte": past_time.isoformat()}},
                include=["documents", "metadatas"]
            )

            return results.get('metadatas', [[]])[0]
        
        except Exception as e:
            logger.error(f"Error retrieving episodic memories for {character_id}: {e}", exc_info=True)
            return []

    def manage_memory_lifecycle(self):
        """
        Periodically reviews episodic memories. Transfers high-importance ones
        to long-term storage and deletes outdated ones.
        """
        now = datetime.now()
        past_time = now - self.retention_period
        try:
            results = self.collection.query(
                query_texts=[""],
                n_results=100,
                include=["documents", "metadatas"]
            )

            for i, metadata in enumerate(results.get('metadatas', [[]])[0]):
                timestamp = datetime.fromisoformat(metadata["timestamp"])
                importance = float(metadata.get("importance", 0.5))

                if timestamp < past_time:
                    if importance >= 0.7:
                        # Transfer to long-term storage
                        self.character_memory_manager.add_memory(
                            character_id=metadata["character_id"],
                            event_description=metadata["event_description"],
                            importance=importance
                        )
                        logger.info(f"Transferred memory to long-term: {metadata['event_description'][:50]}...")
                    
                    # Delete from episodic memory
                    self.collection.delete(ids=[str(timestamp.timestamp())])

        except Exception as e:
            logger.error(f"Error managing episodic memory lifecycle: {e}", exc_info=True)
