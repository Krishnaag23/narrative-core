"""
Validates cultural authenticity and sensitivity based on initial
analysis flags and generated content.
"""
import logging
from typing import List, Dict, Optional, Any

from ..utils import LLMwrapper, PromptManager
from .quality_report import Issue, Severity
from ..input_processing import StoryConcept, CulturalAnalysis, TargetAudience 

logger = logging.getLogger(__name__)

class CulturalValidator:
    """Performs cultural validity and sensitivity checks."""

    def __init__(self, llm_wrapper: LLMwrapper):
        self.llm = llm_wrapper
        self.prompt_manager = PromptManager()
        logger.info("CulturalValidator initialized.")

    async def validate_cultural_aspects(
        self,
        story_concept: StoryConcept,
        episode_script_elements: List[Dict[str, Any]], 
        episode_number: int
    ) -> List[Issue]:
        """
        Validates cultural references and sensitivity flags.

        Args:
            story_concept: The initial validated concept with cultural analysis.
            episode_script_elements: Script elements of the episode to check.
            episode_number: The current episode number.

        Returns:
            A list of cultural validation issues found.
        """
        issues = []
        cultural_analysis: CulturalAnalysis = story_concept.cultural_analysis

        #  Check General Representation if keywords were detected
        if cultural_analysis.detected_keywords:
            # Sample relevant snippets (e.g., descriptions, dialogues mentioning keywords)
            snippet_to_check = self._find_relevant_snippet(episode_script_elements, cultural_analysis.detected_keywords)
            if snippet_to_check:
                prompt = self.prompt_manager.get_prompt(
                    "validate_cultural_representation",
                    genre=story_concept.genre_analysis.primary_genre[0],
                    audience=story_concept.target_audience.value,
                    cultural_keywords=", ".join(cultural_analysis.detected_keywords),
                    episode_number=episode_number,
                    snippet=snippet_to_check[:1000] # Limit length
                )
                if prompt:
                    try:
                        response = await self.llm.query_llm_async(prompt, max_tokens=150, temperature=0.3)
                        if response and response.strip().startswith("CONCERN:"):
                            issues.append(Issue(
                                severity=Severity.HIGH, # Cultural misrepresentation is serious
                                checker="CulturalValidator",
                                check_type="Representation",
                                description=f"Potential cultural representation issue in Episode {episode_number}: {response.strip()}",
                                location=f"Episode {episode_number}"
                            ))
                    except Exception as e:
                        logger.error(f"LLM call failed for cultural representation check: {e}", exc_info=True)

        #  Check Specific Sensitivity Flags
        if cultural_analysis.requires_cultural_sensitivity_check:
            # Identify potentially sensitive content in the episode
            # This might require more sophisticated NLP or specific keyword checks
            # For now, let's assume we identify a sensitive topic mentioned
            # In a real system, this check might be triggered by specific keywords related to the flag
            # Example Placeholder:
            sensitive_topic_mentioned = "Religious Practice" # Assume this was found in the text
            snippet_related_to_topic = self._find_relevant_snippet(episode_script_elements, [sensitive_topic_mentioned.lower()])

            if snippet_related_to_topic:
                 prompt = self.prompt_manager.get_prompt(
                    "check_sensitivity_handling",
                    sensitivity_topic=sensitive_topic_mentioned,
                    episode_number=episode_number,
                    snippet=snippet_related_to_topic[:1000] # Limit length
                 )
                 if prompt:
                    try:
                         response = await self.llm.query_llm_async(prompt, max_tokens=150, temperature=0.3)
                         if response and response.strip().startswith("SENSITIVITY_ISSUE:"):
                             issues.append(Issue(
                                 severity=Severity.CRITICAL, # Mishandling sensitivity is critical
                                 checker="CulturalValidator",
                                 check_type="Sensitivity",
                                 description=f"Potential sensitivity issue regarding '{sensitive_topic_mentioned}' in Episode {episode_number}: {response.strip()}",
                                 location=f"Episode {episode_number}"
                             ))
                    except Exception as e:
                         logger.error(f"LLM call failed for sensitivity handling check: {e}", exc_info=True)


        #  Check Framework Adherence (
        # TODO: Implement checks for framework adherence (e.g., Panchatantra moral, Ashtarasa emotion)
        # This would likely involve analyzing the episode summary or key scenes against the framework's principles.

        return issues

    def _find_relevant_snippet(self, elements: List[Dict[str, Any]], keywords: List[str]) -> Optional[str]:
        """Helper to find the first element containing relevant keywords."""
        # Simple keyword check, can be improved with embedding similarity
        for element in elements:
             content = element.get("content", "").lower()
             if any(keyword.lower() in content for keyword in keywords):
                 # Return the first matching element's content
                 return element.get("content")
        return None