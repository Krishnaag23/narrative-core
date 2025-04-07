"""
Handles the interactive command-line interface for gathering
story details from the user using.
Allows for both guided questioning and free-form text.
"""

import questionary
from typing import Dict, Any, List, Optional
from .story_elements import (
    StoryLength, TargetAudience, CharacterRole, ConflictType, StoryTone,
    CharacterInput, SettingInput, PlotInput
)
import sys

class StoryQuestionnaire:
    """Manages the interactive questionnaire flow."""

    async def gather_input(self, genre_suggestions: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Main method to interactively gather story elements.

        Args:
            genre_suggestions: Optional dictionary with genre-specific questions
                               provided by the GenreClassifier.

        Returns:
            A dictionary containing the raw user input, structured similarly
            to the Pydantic models but before validation/analysis.
        """
        print("Welcome to the NarrativeCore Story Builder!")
        print("Let's gather some initial ideas for your story.")

        input_data = {}

        # --- Input Mode ---
        input_mode = await questionary.select(
            "How would you like to provide the initial concept?",
            choices=[
                "Answer guided questions (Recommended for detailed structure)",
                "Paste a free-form concept note/brief",
                "Both: Paste a note AND answer questions"
            ]
        ).ask_async()

        if input_mode is None:
            print("Input cancelled. Exiting.")
            sys.exit(0)

        input_data["concept_note"] = None
        if "Paste" in input_mode:
            print("\nPlease paste your concept note/brief below.")
            print("Press Ctrl+D (Unix) or Ctrl+Z then Enter (Windows) when done:")
            try:
                input_data["concept_note"] = sys.stdin.read().strip()
                if not input_data["concept_note"]:
                     print("Warning: No text pasted for concept note.")
                     input_data["concept_note"] = None # Ensure it's None if empty
            except EOFError:
                pass # Expected way to end input
            print("-" * 20)


        if "Answer guided questions" in input_mode or "Both" in input_mode:
             # Use structured questioning if requested
             basic_info = await self._gather_basic_info()
             input_data.update(basic_info) # genre, audience, length

             input_data["characters"] = await self._gather_character_info()
             input_data["setting"] = await self._gather_setting_info()
             input_data["plot"] = await self._gather_plot_info(genre_suggestions)
             input_data["metadata"] = {"input_mode": input_mode}
        elif input_data["concept_note"]:
             # If only concept note is provided, ask minimal essential questions
             print("\nSince you provided a concept note, I just need a few basics:")
             input_data["target_audience"] = await questionary.select(
                 "Target Audience?", choices=[e.value for e in TargetAudience]
             ).ask_async()
             input_data["story_length"] = await questionary.select(
                 "Desired Story Length?", choices=[e.value for e in StoryLength]
             ).ask_async()
             input_data["metadata"] = {"input_mode": input_mode}
             # Initialize other keys expected by ConceptBuilder
             input_data["characters"] = await self._gather_character_info()
             input_data["setting"] = await self._gather_setting_info()
             input_data["plot"] = await self._gather_plot_info(genre_suggestions)
           
        else:
            print("Error: No input method selected or no input provided. Exiting.")
            sys.exit(1)

        return input_data


    async def _gather_basic_info(self) -> Dict[str, str]:
        """Gathers genre, audience, and length."""
        # Note: Genre is asked here but might be refined by GenreClassifier later
        return {
            "genre_hint": questionary.text(
                "Briefly describe the main genre(s) (e.g., 'Sci-Fi Mystery', 'Fantasy Romance'):"
                ).ask_async(), # Use text for more flexibility initially
            "target_audience": await questionary.select(
                "Target Audience?", choices=[e.value for e in TargetAudience]
            ).ask_async(),
            "story_length": await questionary.select(
                "Desired Story Length?", choices=[e.value for e in StoryLength]
            ).ask_async()
        }

    async def _gather_character_info(self) -> List[Dict[str, Any]]:
        """Gathers details for multiple characters."""
        characters = []
        print("\n--- Character Definition ---")
        while True:
            add_char = await questionary.confirm(
                f"Add a {'new' if characters else 'first'} character?", default=True
                ).ask_async()
            if not add_char:
                break

            name = await questionary.text("Character Name:", validate=lambda text: True if len(text) > 0 else "Name cannot be empty").ask_async()
            role = await questionary.select("Role:", choices=[e.value for e in CharacterRole]).ask_async()
            desc = await questionary.text(f"Brief description for {name}:").ask_async()
            goals_str = await questionary.text(f"Main goals/motivations for {name} (comma-separated):").ask_async()
            traits_str = await questionary.text(f"Key personality traits for {name} (comma-separated):").ask_async()
            relationships = await questionary.text(f"Initial relationship notes for {name} (optional):").ask_async()

            characters.append({
                "name": name,
                "role": role,
                "description": desc,
                "goals": [g.strip() for g in goals_str.split(',') if g.strip()],
                "traits": [t.strip() for t in traits_str.split(',') if t.strip()],
                "initial_relationships": relationships if relationships else None
            })
            print("-" * 10) 

        if not characters:
            print("Warning: No characters were defined. This might cause issues.")
        return characters

    async def _gather_setting_info(self) -> Dict[str, str]:
        """Gathers setting details."""
        print("\n--- Setting Definition ---")
        return {
            "time_period": await questionary.text("Time Period (e.g., 'Ancient India', '23rd Century Mars'):").ask_async(),
            "location": await questionary.text("Primary Location(s) (e.g., 'A hidden jungle temple', 'New York City'):").ask_async(),
            "atmosphere": await questionary.text("Desired Atmosphere (e.g., 'Mysterious', 'Joyful', 'Tense') (optional):").ask_async(),
            "cultural_context_notes": await questionary.text("Any specific cultural notes for the setting? (optional):").ask_async()
        }

    async def _gather_plot_info(self, genre_suggestions: Optional[Dict] = None) -> Dict[str, Any]:
        """Gathers core plot elements, potentially using genre suggestions."""
        print("\n--- Plot & Concept Definition ---")
        plot_data = {}

        plot_data["logline"] = await questionary.text("Can you provide a one-sentence logline? (optional):").ask_async()
        # Concept note might have been pasted earlier, don't ask again if so.
        if "concept_note" not in plot_data: # Check if already gathered
             plot_data["concept_note"] = await questionary.text("Briefly describe the main plot idea or concept:").ask_async()

        plot_data["primary_conflict"] = await questionary.select(
            "Main type of conflict?", choices=[e.value for e in ConflictType]
        ).ask_async()
        major_plot_response = await questionary.text("List any key plot points or events you envision (comma-separated, optional):").ask_async()
        plot_data["major_plot_points"] = [
            p.strip() for p in major_plot_response.split(',') if p.strip()
        ]
        potential_themes_response = await questionary.text("What are the main themes you want to explore? (comma-separated):").ask_async()
        plot_data["potential_themes"] = [
            t.strip() for t in potential_themes_response.split(',') if t.strip()
        ]
        plot_data["desired_tone"] = await questionary.select(
            "Overall story tone?", choices=[e.value for e in StoryTone]
        ).ask_async()

        # Ask genre-specific questions if available
        if genre_suggestions and genre_suggestions.get('genre_specific_prompts'):
            print("\n--- Genre Specifics ---")
            plot_data['genre_specific_answers'] = {}
            for key, prompt in genre_suggestions['genre_specific_prompts'].items():
                answer = await questionary.text(f"{prompt}:").ask_async()
                plot_data['genre_specific_answers'][key] = answer

        return plot_data