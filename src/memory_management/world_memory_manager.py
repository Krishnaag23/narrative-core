"""
World Memory Manager
====================
Stores historical events, world rules, and lore.
Uses vector embeddings for similarity-based retrieval.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any
from pydantic import BaseModel, Field
import uuid

from .vector_store_manager import VectorStoreManager

logger = logging.getLogger(__name__)

class WorldMemoryRecord(BaseModel):
    """Represents a world-building memory entry."""
    memory_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str  # e.g., "The Fall of the Empire", "Discovery of Magic"
    date: str  # Can be in-world date or real-world timestamp
    description: str  # Details about the historical event or world lore
    category: str  # e.g., "Political", "Mythology", "Technology"
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0) 

class WorldMemoryManager:
    def __init__(self):
        """
        Initializes the world memory system.
        """
        self.vector_store_manager = VectorStoreManager()
        self.collection = self.vector_store_manager.get_world_memory_collection()
        logger.info("WorldMemoryManager initialized.")

    def add_event(self, title: str, date: str, description: str, category: str, importance: float = 0.5):
        """
        Adds a historical event or lore entry to world memory.

        Args:
            title: The name of the event (e.g., "The Great War").
            date: The date (real or fictional) of the event.
            description: A summary of the event.
            category: The category of the event (e.g., "Political", "Technological").
            importance: A score indicating how crucial this event is.
        """
        memory = WorldMemoryRecord(
            title=title,
            date=date,
            description=description[:500],  # Basic truncation for now
            category=category,
            importance_score=importance
        )

        # Store in vector database
        try:
            metadata = {
                "title": memory.title,
                "date": memory.date,
                "category": memory.category,
                "importance": memory.importance_score,
            }
            self.collection.add(
                ids=[memory.memory_id],
                documents=[memory.description], 
                metadatas=[metadata]
            )
            logger.info(f"Added world event: {title} ({date}).")

        except Exception as e:
            logger.error(f"Failed to add event {title}: {e}", exc_info=True)

    def retrieve_event_by_title(self, title: str) -> Dict[str, Any]:
        """
        Retrieves a specific historical event by title.

        Args:
            title: The event title to search for.

        Returns:
            A dictionary containing the event's details.
        """
        try:
            results = self.collection.query(
                query_texts=[title],
                n_results=1,
                include=["documents", "metadatas"]
            )

            if not results.get('ids', [[]])[0]:
                return {}

            metadata = results.get('metadatas', [[]])[0][0]
            return {
                "title": metadata.get("title"),
                "date": metadata.get("date"),
                "category": metadata.get("category"),
                "importance": metadata.get("importance"),
                "description": results.get('documents', [[]])[0][0]
            }

        except Exception as e:
            logger.error(f"Error retrieving event {title}: {e}", exc_info=True)
            return {}

    def retrieve_relevant_events(self, query_text: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves historical events based on semantic similarity.

        Args:
            query_text: A description of the event to search for.
            n_results: The maximum number of events to return.

        Returns:
            A list of historically relevant memories.
        """
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                include=["documents", "metadatas"]
            )

            processed_events = []
            for i, doc_id in enumerate(results.get('ids', [[]])[0]):
                metadata = results.get('metadatas', [[]])[0][i]
                processed_events.append({
                    "memory_id": doc_id,
                    "title": metadata.get("title"),
                    "date": metadata.get("date"),
                    "category": metadata.get("category"),
                    "importance": metadata.get("importance"),
                    "description": results.get('documents', [[]])[0][i]
                })

            return processed_events

        except Exception as e:
            logger.error(f"Error retrieving relevant events: {e}", exc_info=True)
            return []
#memory
