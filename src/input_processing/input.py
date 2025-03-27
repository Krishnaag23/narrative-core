''' I want to have a series of questions / options that the user can answer/select and based on that 
I would have a basic idea of the kind of story they wish to generate, do I just ask question and get 
the concept from there or employ some nlp technique to extract the basic idea, can this even be done 
with nlp?'''
'''what sort of questions? what would be the input and output of this class? '''
'''I want the input to be all the text content in a dictionary format and the process it and return
concept in another dictionary format'''


'''List of elements of a story :- 
    -character
    (would be defined in the character_system in a more verbose manner)
        protagonist, antagonist, supporting characters ,relationships 
    -plot :
        rising action, climax, falling action, and resolution. 
    -setting :
        time and place where the story unfolds, including the physical environment and cultural context. 
    -Theme:
        underlying message or idea explored in the story, often dealing with universal human experiences or concepts. 
    -Point of View:
        perspective from which the story is told, which can be first-person, third-person limited, or third-person omniscient. 
    -Conflict:
        central problem or struggle that drives the plot forward, creating tension and drama. 
    -Tone:
        the author's attitude or feeling towards the subject matter, which can be conveyed through word choice and style. 
'''


from typing import Dict, Any, List
import questionary
from .story_elements import *

class StoryQuestionnaire:
    def __init__(self):
        self.questions = self._initialize_questions()

    def gather_story_elements(self) -> Dict[str, Any]:
        """Interactively gather story elements through a series of questions"""
        story_data = {}
        
        # Basic Story Concept
        story_data["basic_concept"] = self._gather_basic_concept()
        
        # Characters
        story_data["characters"] = self._gather_character_information()
        
        # Setting
        story_data["setting"] = self._gather_setting_information()
        
        # Plot and Conflict
        story_data["plot"] = self._gather_plot_information()
        
        # Theme and Tone
        story_data["theme_tone"] = self._gather_theme_tone()
        
        return story_data

    def _gather_basic_concept(self) -> Dict[str, str]:
        """Gather basic story concept information"""
        return {
            "genre": questionary.select(
                "What is the primary genre of your story?",
                choices=[
                    "Fantasy", "Science Fiction", "Mystery", "Romance",
                    "Historical Fiction", "Contemporary", "Horror", "Adventure"
                ]
            ).ask(),
            
            "target_audience": questionary.select(
                "Who is your target audience?",
                choices=[
                    "Children", "Young Adults", "Adults", "All Ages"
                ]
            ).ask(),
            
            "story_length": questionary.select(
                "How long should the story be?",
                choices=[
                    "Short (1-3 episodes)",
                    "Medium (4-10 episodes)",
                    "Long (10+ episodes)"
                ]
            ).ask()
        }

    def _gather_character_information(self) -> List[Dict[str, Any]]:
        """Gather information about characters"""
        characters = []
        while questionary.confirm("Would you like to add a character?").ask():
            character = {
                "name": questionary.text("What is the character's name?").ask(),
                "role": questionary.select(
                    "What is the character's role?",
                    choices=["Protagonist", "Antagonist", "Supporting"]
                ).ask(),
                "description": questionary.text(
                    "Provide a brief description of the character:"
                ).ask(),
                "goals": questionary.text(
                    "What are the character's main goals? (comma-separated)"
                ).ask().split(","),
                "traits": questionary.text(
                    "List some key personality traits: (comma-separated)"
                ).ask().split(",")
            }
            characters.append(character)
        return characters

    def _gather_setting_information(self) -> Dict[str, str]:
        """Gather information about the story's setting"""
        return {
            "time_period": questionary.text(
                "In what time period does the story take place?"
            ).ask(),
            "location": questionary.text(
                "Where does the story take place?"
            ).ask(),
            "cultural_context": questionary.text(
                "Describe the cultural context of the story:"
            ).ask()
        }

    def _gather_plot_information(self) -> Dict[str, Any]:
        """Gather information about the plot and conflict"""
        return {
            "conflict_type": questionary.select(
                "What is the main type of conflict?",
                choices=[conflict.value for conflict in ConflictType]
            ).ask(),
            "plot_summary": questionary.text(
                "Provide a brief summary of the main plot:"
            ).ask(),
            "major_events": questionary.text(
                "List some major events in the story (comma-separated):"
            ).ask().split(",")
        }

    def _gather_theme_tone(self) -> Dict[str, Any]:
        """Gather information about theme and tone"""
        return {
            "themes": questionary.text(
                "What are the main themes of the story? (comma-separated)"
            ).ask().split(","),
            "tone": questionary.select(
                "What is the overall tone of the story?",
                choices=[
                    "Light and Humorous",
                    "Dark and Serious",
                    "Romantic and Emotional",
                    "Mysterious and Suspenseful",
                    "Educational and Informative"
                ]
            ).ask()
        }
