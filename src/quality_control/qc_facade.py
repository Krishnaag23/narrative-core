"""
Facade for the Quality Control module, orchestrating various checks.
"""
import logging
from typing import List, Dict, Optional, Any

from .quality_report import QualityReport, Issue
from .coherence_checker import CoherenceChecker
from .cultural_validator import CulturalValidator
from ..utils import LLMwrapper 
from ..input_processing import StoryConcept
from ..character_system import CharacterProfile 

logger = logging.getLogger(__name__)

class QualityControlFacade:
    """Orchestrates quality checks and generates a final report."""

    def __init__(self, llm_wrapper: LLMwrapper):
        self.llm = llm_wrapper
        self.coherence_checker = CoherenceChecker(llm_wrapper)
        self.cultural_validator = CulturalValidator(llm_wrapper)
        logger.info("QualityControlFacade initialized.")

    async def run_all_checks(
        self,
        story_concept: StoryConcept,
        generated_episodes: List[Dict[str, Any]], # List of episode script dicts
        character_profiles: Dict[str, CharacterProfile] # character_id -> profile map
    ) -> QualityReport:
        """
        Runs all configured quality checks on the generated story content.

        Args:
            story_concept: The initial validated story concept.
            generated_episodes: List of generated episode script dictionaries.
            character_profiles: Dictionary mapping character IDs to their profiles.

        Returns:
            A QualityReport summarizing all findings.
        """
        logger.info(f"Running quality checks on {len(generated_episodes)} episodes...")
        all_issues: List[Issue] = []
        episode_summaries: Dict[int, str] = {} # Store summaries for cross-episode checks

        # --- Per-Episode Checks ---
        previous_summary = None
        for i, episode_data in enumerate(generated_episodes):
            episode_number = i + 1
            logger.debug(f"Checking Episode {episode_number}...")
            # Assuming episode_data has keys like 'summary', 'elements' (list of dicts)
            current_summary = episode_data.get("summary", f"Episode {episode_number} content") # Need a way to get/generate summary
            episode_elements = episode_data.get("elements", [])
            episode_summaries[episode_number] = current_summary

            # Coherence: Plot Logic (vs previous episode)
            plot_logic_issues = await self.coherence_checker.check_episode_plot_logic(
                current_episode_summary=current_summary,
                previous_episode_summary=previous_summary,
                genre=story_concept.genre_analysis.primary_genre[0],
                episode_number=episode_number
            )
            all_issues.extend(plot_logic_issues)

            # Coherence: Character Consistency & Cultural Validation (needs character profiles)
            # Get characters appearing in this episode (simplified logic)
            chars_in_episode = set(el.get("character") for el in episode_elements if el.get("character"))
            for char_name in chars_in_episode:
                 # Find the profile (assuming names are unique identifiers for now)
                 profile = next((p for p in character_profiles.values() if p.name == char_name), None)
                 if profile:
                     char_consistency_issues = await self.coherence_checker.check_character_consistency_in_episode(
                         character_profile=profile,
                         episode_script_elements=episode_elements,
                         episode_number=episode_number
                     )
                     all_issues.extend(char_consistency_issues)
                 else:
                     logger.warning(f"Profile for character '{char_name}' not found for consistency check in Ep {episode_number}.")


            # Cultural Validation
            cultural_issues = await self.cultural_validator.validate_cultural_aspects(
                story_concept=story_concept,
                episode_script_elements=episode_elements,
                episode_number=episode_number
            )
            all_issues.extend(cultural_issues)

            previous_summary = current_summary # Update for next iteration

        # --- Overall Story Checks ---
        logger.debug("Running overall story checks...")
        # Coherence: Plot Point Resolution
        if story_concept.initial_plot.major_plot_points:
             # Check resolution status for each major plot point
             # In a real scenario, you might prioritize checking only the most critical ones
             for plot_point in story_concept.initial_plot.major_plot_points:
                 resolution_issues = await self.coherence_checker.check_plot_point_resolution_status(
                     story_concept=story_concept,
                     plot_point_to_check=plot_point,
                     all_episode_summaries=episode_summaries
                 )
                 all_issues.extend(resolution_issues)

        # --- Generate Final Report ---
        logger.info(f"Quality checks completed. Found {len(all_issues)} potential issues.")
        report = QualityReport(issues=all_issues, overall_score=0.0, passed=False) # Initial values
        report.calculate_score() # Calculate final score and passed status

        logger.info(f"Final Quality Report - Score: {report.overall_score:.2f}, Passed: {report.passed}")

        return report