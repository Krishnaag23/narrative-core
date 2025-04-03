"""
Checks for narrative coherence, plot logic, and character consistency
within and across episodes.
"""
import logging
from typing import List, Dict, Optional, Any

from ..utils import LLMwrapper, PromptManager
from .quality_report import Issue, Severity
from ..input_processing import StoryConcept 
from ..character_system import CharacterProfile

logger = logging.getLogger(__name__)

class CoherenceChecker:
    """Performs coherence and consistency checks using LLM."""

    def __init__(self, llm_wrapper: LLMwrapper):
        self.llm = llm_wrapper
        self.prompt_manager = PromptManager()
        logger.info("CoherenceChecker initialized.")

    async def check_episode_plot_logic(
        self,
        current_episode_summary: str,
        previous_episode_summary: Optional[str],
        genre: str,
        episode_number: int
    ) -> List[Issue]:
        """Checks if the current episode logically follows the previous one."""
        issues = []
        if not previous_episode_summary:
            return issues.append(Issue(description=f"Previous Episode Summary not available. Analysis Failed")) # Cannot check logic for the first episode this way

        prompt = self.prompt_manager.get_prompt(
            "check_plot_logic",
            genre=genre,
            previous_summary=previous_episode_summary,
            current_episode_summary=current_episode_summary
        )
        if not prompt:
            logger.error("Failed to get 'check_plot_logic' prompt.")
            return issues.append(Issue(description=f"Prompt unavailable. Analysis Failed")) # Cannot proceed without prompt

        try:
            response = await self.llm.query_llm_async(prompt, max_tokens=100, temperature=0.3)
            if response and response.strip().startswith("INCOHERENT:"):
                issues.append(Issue(
                    severity=Severity.MEDIUM,
                    checker="CoherenceChecker",
                    check_type="PlotLogic",
                    description=f"Logical flow issue between Episode {episode_number-1} and {episode_number}: {response.strip()}",
                    location=f"Episode {episode_number}"
                ))
        except Exception as e:
            logger.error(f"LLM call failed for plot logic check: {e}", exc_info=True)

        return issues

    async def check_character_consistency_in_episode(
        self,
        character_profile: CharacterProfile,
        episode_script_elements: List[Dict[str, Any]], # Assuming format like {'type': 'dialogue'/'action', 'character': 'name', 'content': '...'}
        episode_number: int
    ) -> List[Issue]:
        """Checks character actions/dialogue against their profile within an episode."""
        issues = []
        if not character_profile:
            return issues

        # Sample a few dialogue/action snippets for the character
        snippets = []
        snippet_count = 0
        max_snippets_to_check = 3 # Limit API calls
        for element in episode_script_elements:
            if element.get("character") == character_profile.name and element.get("content"):
                snippets.append(element.get("content", ""))
                snippet_count += 1
                if snippet_count >= max_snippets_to_check:
                    break

        if not snippets:
            return issues # No content for this character to check

        for snippet in snippets:
            # Truncate long snippets
            snippet_to_check = snippet[:500] if len(snippet) > 500 else snippet
            prompt = self.prompt_manager.get_prompt(
                "check_character_consistency",
                character_name=character_profile.name,
                character_role=character_profile.role.value, # Use enum value
                character_traits=", ".join(character_profile.core_traits),
                character_motivations=", ".join(character_profile.motivations),
                character_state=f"Mood: {character_profile.current_state.current_mood}, Goal: {character_profile.current_state.short_term_goal}",
                episode_number=episode_number,
                snippet=snippet_to_check
            )
            if not prompt:
                logger.error("Failed to get 'check_character_consistency' prompt.")
                continue # Skip this check

            try:
                response = await self.llm.query_llm_async(prompt, max_tokens=100, temperature=0.4)
                if response and response.strip().startswith("INCONSISTENT:"):
                    issues.append(Issue(
                        severity=Severity.MEDIUM,
                        checker="CoherenceChecker",
                        check_type="CharacterConsistency",
                        description=f"Character '{character_profile.name}' inconsistency in Episode {episode_number}: {response.strip()}",
                        location=f"Episode {episode_number}, Character: {character_profile.name}"
                    ))
            except Exception as e:
                logger.error(f"LLM call failed for character consistency check: {e}", exc_info=True)

        return issues

    async def check_plot_point_resolution_status(
        self,
        story_concept: StoryConcept,
        plot_point_to_check: str, # The specific plot point description
        all_episode_summaries: Dict[int, str] # episode_num: summary
    ) -> List[Issue]:
        """Checks if a specific major plot point seems addressed."""
        issues = []
        if not plot_point_to_check or not all_episode_summaries:
            return issues

        summaries_text = "\n".join([f"Ep {num}: {summary}" for num, summary in sorted(all_episode_summaries.items())])
        logline = story_concept.initial_plot.logline or story_concept.initial_plot.concept_note or "Overall story concept"

        prompt = self.prompt_manager.get_prompt(
            "check_plot_resolution",
            story_logline=logline[:500], # Truncate
            plot_point_description=plot_point_to_check,
            episode_summaries=summaries_text
        )
        if not prompt:
            logger.error("Failed to get 'check_plot_resolution' prompt.")
            return issues

        try:
            response = await self.llm.query_llm_async(prompt, max_tokens=100, temperature=0.3)
            status = response.strip().split(" ")[0] # Get first word (ADDRESSED, PARTIALLY_ADDRESSED, UNADDRESSED)
            reasoning = response.strip()

            if status == "UNADDRESSED":
                issues.append(Issue(
                    severity=Severity.HIGH,
                    checker="CoherenceChecker",
                    check_type="PlotResolution",
                    description=f"Plot point '{plot_point_to_check}' appears unaddressed. Reasoning: {reasoning}",
                    location="Overall Story Arc"
                ))
            elif status == "PARTIALLY_ADDRESSED":
                 issues.append(Issue(
                    severity=Severity.LOW, # Info/Low severity for partial progress
                    checker="CoherenceChecker",
                    check_type="PlotResolution",
                    description=f"Plot point '{plot_point_to_check}' seems only partially addressed. Reasoning: {reasoning}",
                    location="Overall Story Arc"
                ))
        except Exception as e:
            logger.error(f"LLM call failed for plot resolution check: {e}", exc_info=True)

        return issues

    # TODO: Add more checks:
    # - Pacing checks (e.g., too slow/fast based on genre)
    # - Tone consistency checks
    # - Checks for dropped threads (minor plot points, objects, relationships)