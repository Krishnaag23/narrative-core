"""
Generates metadata for episodes, such as summaries, keywords,
and content warnings, often using LLMs.
"""
import logging
from typing import Dict, List, Optional, Any

from ..utils import LLMwrapper, PromptManager
from ..input_processing import StoryConcept

logger = logging.getLogger(__name__)

class MetadataGenerator:
    """Generates descriptive metadata for story episodes."""

    def __init__(self, llm_wrapper: LLMwrapper):
        self.llm = llm_wrapper
        self.prompt_manager = PromptManager()
        logger.info("MetadataGenerator initialized.")

    async def generate_episode_metadata(
        self,
        story_concept: StoryConcept,
        episode_script_elements: List[Dict[str, Any]],
        episode_number: int
    ) -> Dict[str, Any]:
        """
        Generates a dictionary of metadata for a single episode.

        Args:
            story_concept: The overall story concept for context.
            episode_script_elements: The list of script elements for the episode.
            episode_number: The number of the episode.

        Returns:
            A dictionary containing generated metadata fields.
        """
        logger.info(f"Generating metadata for Episode {episode_number}...")
        metadata = {}

        # Combine elements into a single text block for LLM analysis
        # Limit length to avoid excessive token usage
        script_content_full = "\n".join([f"{el.get('type','TEXT').upper()}: {el.get('content','')}" for el in episode_script_elements])
        script_content_for_llm = script_content_full[:4000] # Limit context window feed

        # Generate Summary
        summary = await self._generate_summary(script_content_for_llm)
        if summary:
            metadata["summary"] = summary

        # Generate Keywords
        keywords = await self._generate_keywords(story_concept, script_content_for_llm)
        if keywords:
            metadata["keywords"] = keywords

        # Generate Content Warnings
        warnings = await self._generate_content_warnings(script_content_for_llm)
        if warnings and warnings != "None":
            metadata["content_warnings"] = warnings.split(',') # Assuming comma-separated list

        # Add basic metadata
        metadata["episode_number"] = episode_number
        metadata["title"] = f"Episode {episode_number}: {story_concept.title_suggestion or 'Untitled'}" # Placeholder title logic
        # TODO: Potentially extract title from episode data if available

        logger.info(f"Metadata generated for Episode {episode_number}: {list(metadata.keys())}")
        return metadata

    async def _generate_summary(self, script_content: str) -> Optional[str]:
        """Uses LLM to generate a concise episode summary."""
        prompt = self.prompt_manager.get_prompt(
            "generate_episode_summary",
            script_content=script_content
        )
        if not prompt:
            logger.error("Failed to get 'generate_episode_summary' prompt.")
            return None

        try:
            response = await self.llm.query_llm_async(prompt, max_tokens=150, temperature=0.6)
            return response.strip() if response else None
        except Exception as e:
            logger.error(f"LLM call failed for episode summary generation: {e}", exc_info=True)
            return None

    async def _generate_keywords(self, story_concept: StoryConcept, script_content: str) -> Optional[List[str]]:
        """Uses LLM to extract relevant keywords."""
        prompt = self.prompt_manager.get_prompt(
            "generate_keywords",
            genre=story_concept.genre_analysis.primary_genre[0],
            overall_themes=", ".join(story_concept.initial_plot.potential_themes),
            script_content=script_content
        )
        if not prompt:
            logger.error("Failed to get 'generate_keywords' prompt.")
            return None

        try:
            response = await self.llm.query_llm_async(prompt, max_tokens=100, temperature=0.5)
            if response:
                keywords = [kw.strip() for kw in response.strip().split(',') if kw.strip()]
                return keywords
            return None
        except Exception as e:
            logger.error(f"LLM call failed for keyword generation: {e}", exc_info=True)
            return None

    async def _generate_content_warnings(self, script_content: str) -> Optional[str]:
        """Uses LLM to identify potential content warnings."""
        prompt = self.prompt_manager.get_prompt(
            "generate_content_warnings",
            script_content=script_content
        )
        if not prompt:
            logger.error("Failed to get 'generate_content_warnings' prompt.")
            return None

        try:
            response = await self.llm.query_llm_async(prompt, max_tokens=100, temperature=0.3)
            return response.strip() if response else None
        except Exception as e:
            logger.error(f"LLM call failed for content warning generation: {e}", exc_info=True)
            return None