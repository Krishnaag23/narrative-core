"""
Plot Memory Manager
===================
Manages key story events, ensuring plot continuity across episodes.
Uses memory storage for retrieving significant plot points.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any
from pydantic import BaseModel, Field
import uuid

from .vector_store_manager import VectorStoreManager

logger = logging.getLogger(__name__)

class PlotMemoryRecord(BaseModel):
    """Represents a key plot event."""
    memory_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    episode: int  # Episode number where the event occurred
    timestamp: datetime = Field(default_factory=datetime.now())
    event_description: str 
    summary: str  # Summarized plot event
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)

class PlotMemoryManager:
    def __init__(self):
        """
        Initializes the plot memory system.
        """
        self.vector_store_manager = VectorStoreManager()
        self.collection = self.vector_store_manager.get_plot_memory_collection()
        logger.info("PlotMemoryManager initialized.")

    def add_plot_event(self, episode: int, event_description: str, importance: float = 0.5):
        """
        Adds a new plot memory.

        Args:
            episode: The episode number where the event occurred.
            event_description: Description of the event.
            importance: The significance of the event.
        """
        memory = PlotMemoryRecord(
            episode=episode,
            event_description=event_description,
            summary=event_description[:300],  # Basic truncation for now
            importance_score=importance
        )

        # Store event in vector database
        try:
            metadata = {
                "episode": memory.episode,
                "timestamp": memory.timestamp.isoformat(),
                "importance": memory.importance_score,
            }
            self.collection.add(
                ids=[memory.memory_id],
                documents=[memory.summary], 
                metadatas=[metadata]
            )
            logger.info(f"Added plot memory {memory.memory_id} for episode {episode}.")

        except Exception as e:
            logger.error(f"Failed to add plot memory {memory.memory_id}: {e}", exc_info=True)

    def retrieve_key_events(self, episode: int, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves key plot events from the given episode.

        Args:
            episode: The episode number to retrieve events from.
            n_results: Maximum number of events to return.

        Returns:
            A list of key plot memories.
        """
        try:
            results = self.collection.query(
                query_texts=[""],
                n_results=n_results,
                where={"episode": episode},
                include=["documents", "metadatas"]
            )

            processed_memories = []
            for i, doc_id in enumerate(results.get('ids', [[]])[0]):
                metadata = results.get('metadatas', [[]])[0][i]
                processed_memories.append({
                    "memory_id": doc_id,
                    "summary": results.get('documents', [[]])[0][i],
                    "timestamp": metadata.get("timestamp"),
                    "importance": metadata.get("importance"),
                })

            return processed_memories

        except Exception as e:
            logger.error(f"Error retrieving plot events for episode {episode}: {e}", exc_info=True)
            return []

