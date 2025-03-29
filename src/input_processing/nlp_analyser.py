"""
Uses NLP techniques 
to extract structured information (entities, themes, sentiment)
from free-form text input provided by the user.
"""
from typing import Dict, List, Optional, Tuple
from pydantic import ValidationError
import logging

# TODO: use 'sentence-transformers' for potential embedding-based theme analysis
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
except ImportError:
    logging.error("Transformers library not found. NLP analysis will be limited. pip install transformers sentence-transformers torch")
    pipeline = None # type: ignore

try:
    import spacy
    try:
        NER_MODEL = spacy.load("en_core_web_sm")
    except OSError:
        logging.warning("spaCy 'en_core_web_sm' model not found. Run 'python -m spacy download en_core_web_sm'. Falling back to basic NER.")
        NER_MODEL = None
except ImportError:
    logging.warning("spaCy library not found. Advanced NER will be disabled. pip install spacy")
    NER_MODEL = None
    spacy = None # type: ignore


from .story_elements import NLPExtraction

logger = logging.getLogger(__name__)

class NlpAnalyzer:
    """Analyzes free-text input to extract entities, themes, and sentiment."""

    def __init__(self):
        """Initializes NLP pipelines if available."""
        self.ner_pipeline = None
        self.sentiment_pipeline = None
        self.theme_classifier = None 

        if pipeline:
            try:
                # Using a standard NER pipeline if spaCy isn't available or fails
                if not NER_MODEL:
                    self.ner_pipeline = pipeline("ner", grouped_entities=True)
                    logger.info("Initialized Transformers NER pipeline.")
                else:
                     logger.info("Using spaCy for NER.") 

                self.sentiment_pipeline = pipeline("sentiment-analysis")
                logger.info("Initialized Transformers Sentiment Analysis pipeline.")
                # Using zero-shot for flexible theme identification
                self.theme_classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
                logger.info("Initialized Transformers Zero-Shot Classification pipeline for themes.")

            except Exception as e:
                logger.error(f"Error initializing Hugging Face pipelines: {e}", exc_info=True)
                # Fallback gracefully if models can't load
                self.ner_pipeline = None
                self.sentiment_pipeline = None
                self.theme_classifier = None
        else:
            logger.warning("Transformers library not available. NLP analysis disabled.")


    def analyze_text(self, text: Optional[str]) -> Optional[NLPExtraction]:
        """
        Performs NLP analysis on the provided text.

        Args:
            text: The free-form text input (e.g., concept note).

        Returns:
            An NLPExtraction object containing the analysis results, or None if
            no text is provided or NLP tools are unavailable.
        """
        if not text or not (self.ner_pipeline or NER_MODEL or self.sentiment_pipeline or self.theme_classifier):
            logger.info("Skipping NLP analysis: No text provided or NLP tools unavailable.")
            return None

        logger.info("Performing NLP analysis on input text...")
        extracted_entities = self._extract_entities(text)
        extracted_themes = self._extract_themes(text)
        sentiment = self._analyze_sentiment(text)

        try:
            nlp_results = NLPExtraction(
                extracted_entities=extracted_entities,
                extracted_themes=extracted_themes,
                sentiment=sentiment
            )
            logger.info(f"NLP Analysis Results: {nlp_results}")
            return nlp_results
        except ValidationError as e:
             logger.error(f"Validation error creating NLPExtraction: {e}")
             return None


    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extracts named entities (PERSON, ORG, LOC, etc.)."""
        entities = {}
        try:
            if NER_MODEL: 
                doc = NER_MODEL(text)
                for ent in doc.ents:
                    label = ent.label_
                    if label not in entities:
                        entities[label] = []
                    if ent.text not in entities[label]: # Avoid duplicates
                        entities[label].append(ent.text)
                logger.debug(f"spaCy NER results: {entities}")

            elif self.ner_pipeline: # Fallback to Transformers
                results = self.ner_pipeline(text)
                for entity_group in results:
                     #TODO: Adjust Transformer NER format 
                     label = entity_group.get('entity_group', 'UNKNOWN')
                     word = entity_group.get('word', '')
                     if label not in entities:
                         entities[label] = []
                     if word not in entities[label]:
                         entities[label].append(word)
                logger.debug(f"Transformers NER results: {entities}")
            else:
                 logger.warning("No NER tool available.")

        except Exception as e:
            logger.error(f"Error during NER: {e}", exc_info=True)

        return entities

    def _extract_themes(self, text: str, candidate_themes: Optional[List[str]] = None) -> List[Tuple[str, float]]:
        """Identifies potential themes using zero-shot classification."""
        if not self.theme_classifier:
            logger.warning("Theme classifier not available.")
            return []

        # Define a broad set of candidate themes relevant to storytelling
        if candidate_themes is None:
            candidate_themes = [
                "Love", "Betrayal", "Revenge", "Friendship", "Family", "Courage",
                "Loss", "Discovery", "Power", "Corruption", "Justice", "Sacrifice",
                "Identity", "Coming of Age", "Survival", "Technology Impact",
                "Social Commentary", "Humanity vs Nature", "Good vs Evil", "Redemption"
            ]

        try:
            #TODO: Adjust length limit by testing 
            max_length = 2048 
            truncated_text = text[:max_length]

            results = self.theme_classifier(truncated_text, candidate_themes, multi_label=True) # Allow multiple themes

            # Filter themes with a reasonable confidence score 
            themes = sorted(
                [(label, score) for label, score in zip(results["labels"], results["scores"]) if score > 0.5],
                key=lambda item: item[1], reverse=True # Sort by score descending
            )
            logger.debug(f"Zero-shot theme results: {themes}")
            return themes
        except Exception as e:
            logger.error(f"Error during theme classification: {e}", exc_info=True)
            return []

    def _analyze_sentiment(self, text: str) -> Optional[Tuple[str, float]]:
        """Analyzes the overall sentiment of the text."""
        if not self.sentiment_pipeline:
             logger.warning("Sentiment analysis pipeline not available.")
             return None
        try:
            #TODO: split or summarise to get shorter text 
            # For now, analyze the first N characters
            max_length = 512
            truncated_text = text[:max_length]
            result = self.sentiment_pipeline(truncated_text)[0] 
            sentiment = (result['label'].lower(), round(result['score'], 3))
            logger.debug(f"Sentiment analysis result: {sentiment}")
            return sentiment
        except Exception as e:
            logger.error(f"Error during sentiment analysis: {e}", exc_info=True)
            return None