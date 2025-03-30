"""
Input Processing Module for NarrativeCore.

Provides functionality to gather user input (via CLI or potentially API),
analyze it using NLP, genre classification, and cultural context detection,
and build a structured StoryConcept object.
"""
import logging
from .concept_builder import ConceptBuilder
from .story_elements import StoryConcept 
from typing import Optional

# Configure basic logging for the module
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def process_user_input_cli() -> Optional[StoryConcept]:
    """
    High-level function to run the CLI-based input processing pipeline.

    Initializes the ConceptBuilder and starts the interactive process.

    Returns:
        A validated StoryConcept object if successful, otherwise None.
    """
    logger.info("Starting user input processing via CLI...")
    builder = ConceptBuilder()
    story_concept = builder.build_concept_from_cli()

    if story_concept:
        logger.info("Successfully generated Story Concept.")
    else:
        logger.warning("Failed to generate Story Concept.")

    return story_concept

# Make the main output model easily importable
__all__ = ["process_user_input_cli", "StoryConcept"]