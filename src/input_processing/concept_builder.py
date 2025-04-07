"""
Orchestrates the input processing pipeline.
Takes raw user input (from questionnaire/free-text), runs it through
analyzers (NLP, Genre, Cultural), and constructs the final, validated
StoryConcept object to be passed to the next stage (story_blueprint).
"""

import logging
from typing import Dict, Any, Optional, List
from pydantic import ValidationError

from .questionnaire import StoryQuestionnaire
from .nlp_analyser import NlpAnalyzer
from .genre_classifier import GenreClassifier
from .cultural_context_detector import CulturalContextDetector
from .story_elements import (
    StoryConcept, CharacterInput, SettingInput, PlotInput, GenreAnalysis,
    CulturalAnalysis, NLPExtraction, TargetAudience, StoryLength,
    CharacterRole, ConflictType, StoryTone
)
from ..utils.vector_store_utils import VectorStoreInterface

logger = logging.getLogger(__name__)

class ConceptBuilder:
    """Builds the structured StoryConcept from various inputs and analyses."""

    def __init__(self):
        """Initializes all necessary components."""
        self.questionnaire = StoryQuestionnaire()
        self.nlp_analyzer = NlpAnalyzer()
        self.genre_classifier = GenreClassifier()
        #TODO: Pass vector store when available
        self.cultural_detector = CulturalContextDetector(vector_store=VectorStoreInterface())
        logger.info("ConceptBuilder initialized with analysis components.")

    async def build_concept_from_cli(self) -> Optional[StoryConcept]:
        """
        Runs the full input processing pipeline starting with the CLI questionnaire.

        Returns:
            A validated StoryConcept object, or None if input is cancelled or invalid.
        """
        # Gather Raw Input (potentially using genre suggestions later)
        raw_input = await self.questionnaire.gather_input()
        if not raw_input:
            logger.warning("Input gathering cancelled or failed.")
            return None

        logger.info("Raw input gathered. Starting analysis...")
        concept_note = raw_input.get("concept_note")
        genre_hint = raw_input.get("genre_hint") 

        # NLP ANALYSIS if free text 
        nlp_analysis: Optional[NLPExtraction] = self.nlp_analyzer.analyze_text(concept_note)

        # Perform Genre Classification
        genre_analysis_result: Optional[GenreAnalysis] = self.genre_classifier.classify(
            text_input=concept_note,
            genre_hint=genre_hint
        )
        # If classification failed, create a default object or handle error
        if not genre_analysis_result:
             logger.warning("Genre classification failed. Using defaults.")
             #Placeholder for error neeeded for downstream
             genre_analysis_result = GenreAnalysis(
                 primary_genre=("Unknown", 0.0),
                 secondary_genres=[],
                 genre_specific_prompts={"error": "Genre classification failed"}
             )
             # Alternatively, could return None here if genre is absolutely critical

        # --- Potential Re-Querying ---
        # If genre classification is uncertain or suggests specific follow-ups,
        # you *could* re-prompt the user here using questionnaire, passing
        # genre_analysis_result.genre_specific_prompts.
        # For simplicity now, we'll just pass the prompts along.
        # Example:
        # if genre_analysis_result.genre_specific_prompts:
        #    refined_plot_input = self.questionnaire.ask_genre_specifics(genre_analysis_result.genre_specific_prompts)
        #    raw_input['plot'].update(refined_plot_input) # Update raw input

        # Perform Cultural Context Analysis
        text_for_cultural_analysis = [
            concept_note,
            raw_input.get("setting", {}).get("cultural_context_notes"),
            raw_input.get("setting", {}).get("location"),
            ", ".join(raw_input.get("plot", {}).get("potential_themes", [])),
        ]
        cultural_analysis: CulturalAnalysis = self.cultural_detector.analyze(
            [text for text in text_for_cultural_analysis if text] # Filter out None values
        )

        # Structure and Validate the Final Concept
        logger.info("Structuring and validating the final StoryConcept...")
        try:
            plot_raw = raw_input.get("plot", {})
            setting_raw = raw_input.get("setting", {})
            characters_raw = raw_input.get("characters", [])

            story_concept = StoryConcept(
                title_suggestion=raw_input.get("title_suggestion"), 
                target_audience=raw_input.get("target_audience", TargetAudience.ADULTS.value), # Default if missing
                story_length=raw_input.get("story_length", StoryLength.MEDIUM.value), # Default if missing
                initial_characters=[CharacterInput(**char_data) for char_data in characters_raw],
                initial_setting=SettingInput(
                    time_period=setting_raw.get("time_period", "Undefined"),
                    location=setting_raw.get("location", "Undefined"),
                    atmosphere=setting_raw.get("atmosphere"),
                    cultural_context_notes=setting_raw.get("cultural_context_notes")
                ),
                initial_plot=PlotInput(
                    logline=plot_raw.get("logline"),
                    concept_note=concept_note, # Already have this
                    primary_conflict=plot_raw.get("primary_conflict", ConflictType.PERSON_VS_PERSON.value), # Default
                    major_plot_points=plot_raw.get("major_plot_points", []),
                    potential_themes=plot_raw.get("potential_themes", []),
                    desired_tone=plot_raw.get("desired_tone", StoryTone.DARK_SERIOUS.value) # Default
                ),

                # Analysis Results
                genre_analysis=genre_analysis_result, # Already validated or handled failure
                cultural_analysis=cultural_analysis, # Already validated
                nlp_analysis=nlp_analysis, # Can be None

                # Metadata and Flags
                processing_flags=self._generate_processing_flags(cultural_analysis, genre_analysis_result),
                generation_metadata=raw_input.get("metadata", {"input_mode": "unknown"}) # Store how input was given
            )

            logger.info("StoryConcept successfully built and validated.")
            print("\n--- Generated Story Concept ---") 
            # print(story_concept.json(indent=2)) #for debugging
            return story_concept

        except ValidationError as e:
            logger.error(f"Failed to validate StoryConcept: {e}", exc_info=True)
            # Provide feedback to the user maybe?
            print(f"\nError: There was an issue processing the input. Details:\n{e}")
            return None
        except Exception as e:
             logger.error(f"An unexpected error occurred during concept building: {e}", exc_info=True)
             print(f"\nAn unexpected error occurred: {e}")
             return None

    def _generate_processing_flags(self, cultural: CulturalAnalysis, genre: GenreAnalysis) -> Dict[str, Any]:
        """Generate hints/flags for downstream modules based on analysis."""
        flags = {}
        if cultural.requires_cultural_sensitivity_check:
            flags["requires_cultural_sensitivity_check"] = True
        if "Panchatantra" in cultural.detected_keywords:
             flags["suggested_structure"] = "Panchatantra-style (moral focus)"
        if "Ashtarasa" in cultural.detected_keywords:
             flags["suggested_emotional_framework"] = "Ashtarasa"
        # Add flags based on genre if needed (e.g., for specific generation styles)
        if "Hard Sci-Fi" == genre.primary_genre[0]:
             flags["emphasize_scientific_accuracy"] = True

        logger.debug(f"Generated processing flags: {flags}")
        return flags