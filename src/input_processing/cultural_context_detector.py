"""
Analyzes input for specific cultural keywords, themes, or patterns
Integrates RAG with a vector store of cultural narratives.
"""
import logging
from typing import List, Optional, Dict, Any
from pydantic import ValidationError

from ..utils import VectorStoreInterface

from .story_elements import CulturalAnalysis

logger = logging.getLogger(__name__)

# Define a constant for the RAG collection name
CULTURAL_NARRATIVES_COLLECTION = "cultural_narratives"

class CulturalContextDetector:
    """Detects cultural elements and suggests relevant frameworks using keywords and RAG."""

    def __init__(self, vector_store: Optional[VectorStoreInterface] = None):
        """
        Initializes the detector.

        Args:
            vector_store: An instance of the vector store client (e.g., VectorStoreInterface).
        """
        # TODO: expand with RAG
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
        self.vector_store = vector_store
        if self.vector_store:
            logger.info("Vector store provided. RAG features enabled.")
            # Ensure the collection exists (optional, depends on VectorStoreInterface implementation)
        else:
            logger.info("No vector store provided. Using only keyword matching for cultural context.")

    def analyze(self, text_inputs: List[str]) -> CulturalAnalysis:
        """
        Analyzes combined text inputs for cultural context using keywords and RAG.

        Args:
            text_inputs: A list of strings containing user input
                         (e.g., concept note, setting description, theme list).

        Returns:
            A CulturalAnalysis object.
        """
        combined_text = " ".join(filter(None, text_inputs)).lower()
        detected_keywords = []
        suggested_frameworks = []
        rag_info = [] # Store info retrieved via RAG
        requires_sensitivity_check = False # Default

        if not combined_text:
            logger.warning("No text provided for cultural context analysis.")
            return CulturalAnalysis() # Return empty analysis

        # --- Keyword Matching ---
        logger.info("Analyzing for cultural context keywords...")
        for framework, keywords in self.cultural_keywords.items():
            for keyword in keywords:
                if keyword in combined_text:
                    if framework not in detected_keywords:
                        detected_keywords.append(framework)
                    # Suggest framework if a primary keyword is found
                    if framework in self.framework_suggestions and self.framework_suggestions[framework] not in suggested_frameworks:
                         suggested_frameworks.append(self.framework_suggestions[framework])
                    # Flag sensitivity for certain topics (e.g., religion, mythology)
                    if framework in ["Mahabharata", "Ramayana", "Vedas/Upanishads", "Indian Mythology"]:
                         requires_sensitivity_check = True
                    break # Move to next framework once a keyword is found for this one

        # --- RAG Implementation ---
        if self.vector_store:
            logger.info("Performing RAG query for cultural context...")
            try:
                # Query the dedicated collection
                # Assuming query returns list of results per query text, take first list
                rag_results_list = self.vector_store.query(
                    collection_name=CULTURAL_NARRATIVES_COLLECTION,
                    query_texts=[combined_text],
                    n_results=3 # Retrieve top 3 relevant cultural docs
                )

                if rag_results_list and rag_results_list[0]:
                    rag_items = rag_results_list[0] # Results for the first query text
                    logger.info(f"RAG query found {len(rag_items)} relevant cultural documents.")
                    for item in rag_items:
                        # Process RAG results - extract relevant info from metadata or document
                        doc_summary = item.get('document', '')[:100] + "..." # Short summary
                        metadata = item.get('metadata', {})
                        rag_framework = metadata.get('framework') # Example metadata field
                        rag_theme = metadata.get('theme')         # Example metadata field

                        rag_info.append(f"Related Concept: {metadata.get('title', doc_summary)}") # Add source info

                        # Add detected keywords/frameworks based on RAG results
                        if rag_framework and rag_framework not in detected_keywords:
                            detected_keywords.append(f"RAG:{rag_framework}")
                            if rag_framework in self.framework_suggestions and self.framework_suggestions[rag_framework] not in suggested_frameworks:
                                suggested_frameworks.append(self.framework_suggestions[rag_framework] + " (Suggested by RAG)")
                        if rag_theme and f"RAG:{rag_theme}" not in detected_keywords:
                             detected_keywords.append(f"RAG:{rag_theme}")

                        # Flag sensitivity based on RAG results if metadata indicates it
                        if metadata.get('is_sensitive'):
                            requires_sensitivity_check = True
                else:
                    logger.info("RAG query returned no relevant cultural documents.")

            except Exception as e:
                logger.error(f"Error during RAG vector store query: {e}", exc_info=True)
        # --- End RAG ---

        logger.info(f"Cultural Context Analysis - Detected: {detected_keywords}, Suggested Frameworks: {len(suggested_frameworks)}, RAG Info Count: {len(rag_info)}, Sensitivity Check: {requires_sensitivity_check}")

        try:
            # Add RAG info to suggestions or a dedicated field if needed
            # For simplicity, adding to suggested_frameworks for now
            if rag_info:
                 suggested_frameworks.append(f"RAG Context Hints: {'; '.join(rag_info)}")

            return CulturalAnalysis(
                detected_keywords=list(set(detected_keywords)), # Ensure unique
                suggested_frameworks=list(set(suggested_frameworks)),
                requires_cultural_sensitivity_check=requires_sensitivity_check
            )
        except ValidationError as e:
             logger.error(f"Validation error creating CulturalAnalysis: {e}")
             return CulturalAnalysis() # Return default on error