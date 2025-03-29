"""
Classifies the story's genre based on user input 
and suggests relevant follow-up questions or prompts for the questionnaire
or downstream modules.
"""
from typing import Dict, List, Optional, Tuple, Any
import logging

try:
    from transformers import pipeline
except ImportError:
    logging.error("Transformers library not found. Genre classification disabled. pip install transformers torch")
    pipeline = None # type: ignore

from .story_elements import GenreAnalysis
from pydantic import ValidationError

logger = logging.getLogger(__name__)

class GenreClassifier:
    """Classifies story genre and provides context-specific prompts."""

    def __init__(self, confidence_threshold: float = 0.5):
        """
        Initializes the genre classifier.

        Args:
            confidence_threshold: Minimum score for secondary genres.
        """
        self.classifier = None
        self.confidence_threshold = confidence_threshold
        #TODO: Tailor genres to KUKUFM 
        self.candidate_genres = [
            "Fantasy", "Urban Fantasy", "High Fantasy", "Dark Fantasy",
            "Science Fiction", "Hard Sci-Fi", "Space Opera", "Cyberpunk", "Biopunk", "Dystopian",
            "Mystery", "Cozy Mystery", "Hardboiled", "Thriller", "Psychological Thriller",
            "Romance", "Contemporary Romance", "Historical Romance", "Paranormal Romance",
            "Historical Fiction", "Alternate History",
            "Horror", "Gothic Horror", "Cosmic Horror", "Slasher",
            "Adventure", "Action",
            "Drama", "Family Saga", "Literary Fiction",
            "Comedy", "Satire", "Romantic Comedy",
            "Western",
            "Young Adult (YA)", "Children's Fiction",
            "Mythology", "Folklore", "Magical Realism",
            "Crime", "Noir", "Superhero"
        ]
        if pipeline:
            try:
                # Using a zero-shot model allows classifying against custom labels
                self.classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
                logger.info("Initialized Zero-Shot Classification pipeline for genre.")
            except Exception as e:
                logger.error(f"Failed to initialize genre classification pipeline: {e}", exc_info=True)
        else:
            logger.warning("Transformers library not available. Genre classification disabled.")

    def classify(self, text_input: Optional[str], genre_hint: Optional[str] = None) -> Optional[GenreAnalysis]:
        """
        Classifies the genre based on available text input.

        Args:
            text_input: Free-form concept note or plot summary.
            genre_hint: Specific genre(s) mentioned by the user.

        Returns:
            A GenreAnalysis object or None if classification fails or is disabled.
        """
        if not self.classifier:
            logger.warning("Genre classifier not available. Skipping classification.")
            # Return a default or empty analysis if needed downstream
            return None

        # Combine hint and text for better context, prioritizing hint if strong
        text_to_classify = genre_hint if genre_hint else ""
        if text_input:
             # Append concept note, ensuring separation
            text_to_classify += ("\n" + text_input) if text_to_classify else text_input

        if not text_to_classify:
            logger.warning("No text available for genre classification.")
            return None

        logger.info("Performing genre classification...")
        try:
            # Truncate long inputs if necessary
            max_length = 512
            truncated_text = text_to_classify[:max_length]

            #TODO : Add support for multiple primary genre
            results = self.classifier(truncated_text, self.candidate_genres, multi_label=False) 

            primary_genre = results["labels"][0]
            primary_score = round(results["scores"][0], 3)
            logger.info(f"Predicted primary genre: {primary_genre} (Score: {primary_score})")

            # Identify secondary genres above the threshold
            secondary_genres = sorted(
                [
                    (label, round(score, 3))
                    for label, score in zip(results["labels"][1:], results["scores"][1:])
                    if score >= self.confidence_threshold
                ],
                key=lambda item: item[1], reverse=True
            )
            logger.info(f"Predicted secondary genres: {secondary_genres}")

            # Generate follow-up prompts 
            follow_up_prompts = self._generate_follow_up_prompts(primary_genre)

            genre_analysis = GenreAnalysis(
                primary_genre=(primary_genre, primary_score),
                secondary_genres=secondary_genres,
                genre_specific_prompts=follow_up_prompts
            )
            return genre_analysis

        except Exception as e:
            logger.error(f"Error during genre classification: {e}", exc_info=True)
            return None
        except ValidationError as e:
             logger.error(f"Validation error creating GenreAnalysis: {e}")
             return None


    def _generate_follow_up_prompts(self, genre: str) -> Dict[str, str]:
        """
        Generates specific questions or prompts based on the primary genre.
        These can guide the user (via questionnaire) or prime the AI later.
        """
        prompts = {}
        #TODO : Improve Followups exponentially or use LLM to generate Followups
        if "Fantasy" in genre:
            prompts["magic_system"] = "Briefly describe the magic system (if any): hard/soft, common/rare?"
            prompts["world_lore"] = "Any key races, factions, or historical events in this fantasy world?"
        elif "Science Fiction" in genre or "Sci-Fi" in genre:
            prompts["technology_level"] = "What is the general level of technology (near future, far future, specific tech)?"
            prompts["societal_impact"] = "How does technology impact society or the main characters?"
            if "Cyberpunk" in genre:
                 prompts["cyberpunk_themes"] = "What core cyberpunk themes (e.g., corporate control, body modification, AI consciousness) are central?"
        elif "Mystery" in genre:
            prompts["central_mystery"] = "What is the core mystery or crime to be solved?"
            prompts["detective_type"] = "What kind of investigator is the protagonist (e.g., professional detective, amateur sleuth)?"
        elif "Romance" in genre:
            prompts["relationship_dynamic"] = "What is the central relationship dynamic (e.g., enemies-to-lovers, second chance)?"
            prompts["romantic_obstacles"] = "What are the main obstacles to the romantic relationship?"
        elif "Horror" in genre:
            prompts["horror_source"] = "What is the primary source of horror (e.g., monster, psychological, supernatural entity)?"
            prompts["survival_element"] = "Is survival a key element? How do characters try to survive?"
        elif "Historical" in genre:
            prompts["historical_period_accuracy"] = "How closely should the story adhere to the historical period? Any specific events?"
        elif "Mythology" in genre or "Folklore" in genre:
             prompts["myth_source"] = "Which specific myths, legends, or folklore traditions are being drawn upon?"

        logger.debug(f"Generated prompts for genre '{genre}': {prompts}")
        return prompts