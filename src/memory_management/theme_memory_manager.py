"""
Theme Memory Manager
====================
Tracks recurring themes across episodes.
Uses vector embeddings for similarity-based retrieval.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any
from pydantic import BaseModel, Field
import uuid

from .vector_store_manager import VectorStoreManager

logger = logging.getLogger(__name__)

class ThemeMemoryRecord(BaseModel):
    """Represents a recurring theme in the story."""
    memory_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    theme_name: str  # e.g., "Betrayal", "Redemption", "Sacrifice"
    first_appearance: int  # Episode where the theme first appeared
    last_appearance: int  # Episode where the theme was last observed
    summary: str  # A brief summary of how the theme manifests in the story
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0) 

class ThemeMemoryManager:
    def __init__(self):
        """
        Initializes the theme memory system.
        """
        self.vector_store_manager = VectorStoreManager()
        self.collection = self.vector_store_manager.get_theme_memory_collection()
        logger.info("ThemeMemoryManager initialized.")

    def add_theme(self, theme_name: str, episode: int, summary: str, importance: float = 0.5):
        """
        Adds or updates a theme's presence in the story.

        Args:
            theme_name: The recurring theme (e.g., "Betrayal").
            episode: The episode where this theme appears.
            summary: A brief description of how the theme manifests.
            importance: A score indicating how significant this theme is.
        """
        # Check if theme already exists
        existing_theme = self.retrieve_theme_by_name(theme_name)
        if existing_theme:
            last_episode = max(existing_theme["last_appearance"], episode)
        else:
            last_episode = episode

        memory = ThemeMemoryRecord(
            theme_name=theme_name,
            first_appearance=episode if not existing_theme else existing_theme["first_appearance"],
            last_appearance=last_episode,
            summary=summary[:300],  # Basic truncation for now
            importance_score=importance
        )

        # Store theme in vector database
        try:
            metadata = {
                "theme_name": memory.theme_name,
                "first_appearance": memory.first_appearance,
                "last_appearance": memory.last_appearance,
                "importance": memory.importance_score,
            }
            self.collection.add(
                ids=[memory.memory_id],
                documents=[memory.summary], 
                metadatas=[metadata]
            )
            logger.info(f"Added/Updated theme {theme_name} (last seen in episode {last_episode}).")

        except Exception as e:
            logger.error(f"Failed to add theme {theme_name}: {e}", exc_info=True)

    def retrieve_theme_by_name(self, theme_name: str) -> Dict[str, Any]:
        """
        Retrieves a specific theme by name.

        Args:
            theme_name: The theme to search for.

        Returns:
            A dictionary containing the theme's details.
        """
        try:
            results = self.collection.query(
                query_texts=[theme_name],
                n_results=1,
                include=["documents", "metadatas"]
            )

            if not results.get('ids', [[]])[0]:
                return {}

            metadata = results.get('metadatas', [[]])[0][0]
            return {
                "theme_name": metadata.get("theme_name"),
                "first_appearance": metadata.get("first_appearance"),
                "last_appearance": metadata.get("last_appearance"),
                "importance": metadata.get("importance"),
                "summary": results.get('documents', [[]])[0][0]
            }

        except Exception as e:
            logger.error(f"Error retrieving theme {theme_name}: {e}", exc_info=True)
            return {}

    def retrieve_relevant_themes(self, query_text: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves relevant themes based on semantic similarity.

        Args:
            query_text: A description of the thematic idea to search for.
            n_results: The maximum number of themes to return.

        Returns:
            A list of thematically relevant memories.
        """
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                include=["documents", "metadatas"]
            )

            processed_themes = []
            for i, doc_id in enumerate(results.get('ids', [[]])[0]):
                metadata = results.get('metadatas', [[]])[0][i]
                processed_themes.append({
                    "memory_id": doc_id,
                    "theme_name": metadata.get("theme_name"),
                    "first_appearance": metadata.get("first_appearance"),
                    "last_appearance": metadata.get("last_appearance"),
                    "importance": metadata.get("importance"),
                    "summary": results.get('documents', [[]])[0][i]
                })

            return processed_themes

        except Exception as e:
            logger.error(f"Error retrieving relevant themes: {e}", exc_info=True)
            return []

