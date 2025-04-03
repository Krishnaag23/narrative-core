"""
Provides functions for creating multi-level summaries of story content
(scenes, episodes, acts) to manage context for LLMs.
"""

import logging
from typing import List, Dict, Optional, Any

from ..utils import LLMwrapper, PromptManager, VectorStoreInterface, GraphDB
#TODO : Link with vector db and graph correctly


logger = logging.getLogger(__name__)

class HierarchicalSummarizer:
    """Handles creation of summaries at different narrative levels."""

    def __init__(self, llm_wrapper: LLMwrapper):
        self.llm = llm_wrapper
        self.prompt_manager = PromptManager()
        self.vector_store = VectorStoreInterface() 
        self.graph_db = GraphDB() 
        logger.info("HierarchicalSummarizer initialized.")
        

    async def summarize_scene(self, scene_elements: List[Dict[str, Any]]) -> Optional[str]:
        """Generates a concise summary of a single scene."""
        if not scene_elements:
            return None

        # Combine scene elements into text, prioritizing dialogue and actions
        scene_content = "\n".join([
            f"{el.get('type', 'TEXT').upper()}: {el.get('content', '')}"
            for el in scene_elements
        ])
        # Limit input length for LLM
        scene_content_for_llm = scene_content[:3000]

        prompt = self.prompt_manager.get_prompt(
            "summarize_scene_content",
            scene_content=scene_content_for_llm
        )
        if not prompt:
            logger.error("Failed to get 'summarize_scene_content' prompt.")
            return None

        try:
            summary = await self.llm.query_llm_async(prompt, max_tokens=100, temperature=0.5)
            logger.debug(f"Generated scene summary: {summary}")
            # Optional: Store summary in vector store/KG linked to scene ID
            return summary.strip() if summary else None
        except Exception as e:
            logger.error(f"LLM call failed for scene summarization: {e}", exc_info=True)
            return None

    async def summarize_episode(self, episode_data: Dict[str, Any], scene_summaries: Optional[List[str]] = None) -> Optional[str]:
        """Generates a summary of an episode, potentially using scene summaries."""
        if scene_summaries:
            content_to_summarize = "\n".join(scene_summaries)
        else:
            # Fallback: use raw elements if no scene summaries provided
            elements = episode_data.get("elements", [])
            content_to_summarize = "\n".join([f"{el.get('type','TEXT').upper()}: {el.get('content','')}" for el in elements])

        if not content_to_summarize:
             return None

        # Limit input length
        content_for_llm = content_to_summarize[:4000]

        prompt = self.prompt_manager.get_prompt(
            "summarize_episode_for_memory",
            episode_content=content_for_llm
        )
        if not prompt:
            logger.error("Failed to get 'summarize_episode_for_memory' prompt.")
            return None

        try:
            summary = await self.llm.query_llm_async(prompt, max_tokens=200, temperature=0.5)
            logger.debug(f"Generated episode memory summary: {summary}")
            # Optional: Store summary linked to episode ID
            return summary.strip() if summary else None
        except Exception as e:
            logger.error(f"LLM call failed for episode summarization: {e}", exc_info=True)
            return None

    async def summarize_act_or_chunk(self, episode_summaries: List[str]) -> Optional[str]:
        """Summarizes a sequence of episodes (representing an act or chunk)."""
        if not episode_summaries:
            return None

        summaries_text = "\n\n".join([f"Ep Summary {i+1}: {s}" for i, s in enumerate(episode_summaries)])
        # Limit input length
        summaries_for_llm = summaries_text[:6000] # Allow more context for higher-level summary

        prompt = self.prompt_manager.get_prompt(
            "summarize_multiple_episodes",
            episode_summaries_text=summaries_for_llm
        )
        if not prompt:
            logger.error("Failed to get 'summarize_multiple_episodes' prompt.")
            return None

        try:
            summary = await self.llm.query_llm_async(prompt, max_tokens=300, temperature=0.6)
            logger.debug(f"Generated multi-episode summary: {summary}")
            # Optional: Store summary linked to the act/chunk ID
            VectorStoreInterface.add("")
            return summary.strip() if summary else None
        except Exception as e:
            logger.error(f"LLM call failed for multi-episode summarization: {e}", exc_info=True)
            return None