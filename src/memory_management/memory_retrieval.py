"""
Memory Retrieval System
=======================
Unified interface for retrieving and ranking memories 
from character, plot, theme, and world memory managers.
"""

import logging
from typing import List, Dict, Any

from .character_memory_manager import CharacterMemoryManager
from .plot_memory_manager import PlotMemoryManager
from .theme_memory_manager import ThemeMemoryManager
from .world_memory_manager import WorldMemoryManager

logger = logging.getLogger(__name__)

class MemoryRetrieval:
    def __init__(self):
        """
        Initializes the retrieval system by linking all memory managers.
        """
        self.character_memory = CharacterMemoryManager()
        self.plot_memory = PlotMemoryManager()
        self.theme_memory = ThemeMemoryManager()
        self.world_memory = WorldMemoryManager()

        logger.info("MemoryRetrieval system initialized.")

    def retrieve_memories(self, query_text: str, n_results: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieves relevant memories across all memory types.

        Args:
            query_text: The input text describing the memory being searched.
            n_results: The number of relevant results to return per memory type.

        Returns:
            A dictionary containing retrieved memories categorized by type.
        """
        try:
            results = {
                "character_memories": self.character_memory.retrieve_relevant_memories(query_text, n_results),
                "plot_memories": self.plot_memory.retrieve_relevant_events(query_text, n_results),
                "theme_memories": self.theme_memory.retrieve_relevant_themes(query_text, n_results),
                "world_memories": self.world_memory.retrieve_relevant_events(query_text, n_results),
            }

            return results

        except Exception as e:
            logger.error(f"Error retrieving memories: {e}", exc_info=True)
            return {}

    def rank_memories(self, memories: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Ranks retrieved memories based on importance and relevance.

        Args:
            memories: A dictionary of categorized retrieved memories.

        Returns:
            A ranked list of the most relevant memories across all types.
        """
        ranked_memories = []
        
        for category, memory_list in memories.items():
            for memory in memory_list:
                memory["source"] = category
                memory["relevance_score"] = self.calculate_relevance(memory)
                ranked_memories.append(memory)

        # Sort by relevance (higher scores first)
        ranked_memories.sort(key=lambda x: x["relevance_score"], reverse=True)

        return ranked_memories

    def calculate_relevance(self, memory: Dict[str, Any]) -> float:
        """
        Calculates a relevance score for a memory.

        Args:
            memory: A single memory entry.

        Returns:
            A numerical relevance score.
        """
        importance = memory.get("importance", 0.5)
        # Simple formula: (importance * 0.7 + length_factor * 0.3)
        length_factor = min(len(memory.get("description", "")) / 500, 1.0)
        return round(importance * 0.7 + length_factor * 0.3, 2)
