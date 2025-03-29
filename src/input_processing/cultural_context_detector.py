"""
Analyzes input for specific cultural keywords, themes, or patterns
relevant to KukuFM's audience (e.g., Indian folklore, Panchatantra).
Currently uses keyword matching; intended to integrate RAG with a
vector store of cultural narratives in the future.
"""
import logging
from typing import List, Optional, Dict, Any
from pydantic import ValidationError

#TODO: implement vectorstoreinterface in utils/vecto_store 
# from ..utils.vector_store import VectorStoreInterface 

from .story_elements import CulturalAnalysis

logger = logging.getLogger(__name__)

class CulturalContextDetector:
    """Detects cultural elements and suggests relevant frameworks."""

    def __init__(self, vector_store: Optional[Any] = None): # TODO: Replace Any with VectorStoreInterface 
        """
        Initializes the detector.

        Args:
            vector_store: An instance of the vector store client (for future RAG).
        """
        #TODO: expand with RAG 
        self.cultural_keywords = {
            "Panchatantra": ["panchatantra", "fable", "moral story", "animal tale"],
            "Mahabharata": ["mahabharata", "kurukshetra", "pandava", "kaurava", "krishna", "arjuna"],
            "Ramayana": ["ramayana", "rama", "sita", "ravana", "hanuman", "ayodhya"],
            "Vedas/Upanishads": ["veda", "upanishad", "hindu philosophy", "dharma", "karma"],
            "Indian Mythology": ["ganesha", "shiva", "durga", "kali", "brahma", "vishnu", "avatar"],
            "Ashtarasa": ["ashtarasa", "navarasa", "rasa theory", "shringara", "hasya", "karuna", "raudra", "veera", "bhayanaka", "bibhatsa", "adbutha", "shanta"],
            "Regional Folklore": ["vikram aur betaal", "tenali rama", "akbar birbal", "jataka tales", "bhojpuri folk", "rajasthani folk"] # Add more regions
        }
        self.framework_suggestions = {
            "Panchatantra": "Consider structuring episodes around a moral or lesson, possibly using animal characters.",
            "Ashtarasa": "Focus on evoking specific core emotions (Rasas) in key scenes or character arcs.",
            "Mahabharata": "Explore themes of duty (dharma), conflict, and complex family dynamics.",
            "Ramayana": "Explore themes of righteousness, loyalty, and the battle of good versus evil."
        }
        self.vector_store = vector_store # future use
        if self.vector_store:
            logger.info("Vector store provided. RAG features can be enabled later.")
        else:
            logger.info("No vector store provided. Using keyword matching for cultural context.")

    def analyze(self, text_inputs: List[str]) -> CulturalAnalysis:
        """
        Analyzes combined text inputs for cultural context.

        Args:
            text_inputs: A list of strings containing user input
                         (e.g., concept note, setting description, theme list).

        Returns:
            A CulturalAnalysis object.
        """
        combined_text = " ".join(filter(None, text_inputs)).lower()
        detected_keywords = []
        suggested_frameworks = []
        requires_sensitivity_check = False # Default

        if not combined_text:
            logger.warning("No text provided for cultural context analysis.")
            return CulturalAnalysis() # Return empty analysis

        logger.info("Analyzing for cultural context keywords...")
        for framework, keywords in self.cultural_keywords.items():
            for keyword in keywords:
                if keyword in combined_text:
                    if framework not in detected_keywords:
                        detected_keywords.append(framework)
                    # Suggest framework if a primary keyword is found
                    if framework in self.framework_suggestions and framework not in suggested_frameworks:
                         suggested_frameworks.append(self.framework_suggestions[framework])
                    # Flag sensitivity for certain topics (e.g., religion, mythology)
                    if framework in ["Mahabharata", "Ramayana", "Vedas/Upanishads", "Indian Mythology"]:
                         requires_sensitivity_check = True
                    # Break inner loop once a keyword for this framework is found? Optional.

        # --- Placeholder for RAG ---
        if self.vector_store:
            logger.info("RAG Implementation Placeholder: Querying vector store with input text.")
            # try:
            #     # Example: Find similar cultural narrative snippets
            #     # relevant_docs = self.vector_store.search(combined_text, top_k=3)
            #     # if relevant_docs:
            #     #     detected_keywords.append("RAG_Match") # Indicate a match
            #     #     # Process relevant_docs to potentially suggest frameworks or add keywords
            #     #     logger.info(f"RAG found relevant documents: {relevant_docs}") # Placeholder
            # except Exception as e:
            #     logger.error(f"Error during RAG vector store query: {e}")
            pass # RAG logic goes here
        # --- End RAG Placeholder ---

        logger.info(f"Cultural Context Analysis - Detected: {detected_keywords}, Suggested Frameworks: {len(suggested_frameworks)}, Sensitivity Check: {requires_sensitivity_check}")

        try:
            return CulturalAnalysis(
                detected_keywords=list(set(detected_keywords)), # Ensure unique
                suggested_frameworks=list(set(suggested_frameworks)),
                requires_cultural_sensitivity_check=requires_sensitivity_check
            )
        except ValidationError as e:
             logger.error(f"Validation error creating CulturalAnalysis: {e}")
             return CulturalAnalysis() # Return default on error