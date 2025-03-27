from typing import Dict
from transformers import pipeline

class GenreClassifier:
    def __init__(self):
        """
        Initializes the genre classifier using a pre-trained model.
        """
        self.classifier = pipeline("zero-shot-classification")
        self.genres = [
            "Fantasy", "Science Fiction", "Mystery", "Romance", "Historical",
            "Horror", "Adventure", "Drama", "Comedy", "Thriller", "Literary Fiction",
            "Western", "Young Adult", "Children's", "Dystopian", "Supernatural",
            "Crime", "Mythology", "Magical Realism"
        ]

    def classify_story(self, story_input: Dict[str, any]) -> Dict[str, any]:
        """
        Classifies the story into genres and subgenres based on the input.

        Args:
            story_input: Dictionary containing story elements.

        Returns:
            Dictionary with genre classification and follow-up questions.
        """
        # Extract relevant text for classification
        text_to_classify = f"{story_input.get('plot_summary', '')} {story_input.get('theme_tone', '')}"

        # Get genre predictions
        results = self.classifier(text_to_classify, self.genres)

        # Determine primary and secondary genres
        primary_genre, primary_score = results["labels"][0], results["scores"][0]
        secondary_genres = [(label, score) for label, score in zip(results["labels"][1:], results["scores"][1:]) if score > 0.5]

        # Generate follow-up questions for the primary genre
        follow_up = self._generate_follow_up_questions(primary_genre)

        return {
            "primary_genre": (primary_genre, primary_score),
            "secondary_genres": secondary_genres,
            "follow_up_questions": follow_up
        }

    def _generate_follow_up_questions(self, genre: str) -> Dict[str, any]:
        """
        Generates follow-up questions specific to the given genre.

        Args:
            genre: The primary genre of the story.

        Returns:
            Dictionary of follow-up questions and options.
        """
        follow_up = {}
        #TODO : Implement a follow up question system
        return follow_up
