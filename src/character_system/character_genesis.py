"""
Takes initial CharacterInput data and uses an LLM to expand it into
a rich, detailed CharacterProfile, including backstory, motivations,
flaws, voice, etc.
"""

import logging
from typing import List, Optional, Any, Dict
from pydantic import ValidationError

from .character_profile import CharacterProfile, CharacterInput, CharacterState
from ..utils import LLMwrapper
from ..utils import PromptManager

logger = logging.getLogger(__name__)

class CharacterGenesis:
    def __init__(self, llm_wrapper = LLMwrapper): 
        """
        Initializes the Character Genesis module.

        Args:
            llm_wrapper: An instance of the LLM wrapper.
        """
        self.llm_wrapper = llm_wrapper
        if not self.llm_wrapper:
            raise ValueError("LLM wrapper instance is required for CharacterGenesis.")
        logger.info("CharacterGenesis initialized.")

    async def _generate_details_with_llm(self, initial_input: CharacterInput, story_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Uses LLM to generate detailed aspects based on initial input."""

        story_ctx_str = ""
        if story_context:
             genre = story_context.get('genre_analysis', {}).get('primary_genre', ('Unknown', 0.0))[0]
             setting_summary = story_context.get('initial_setting', {}).get('location', 'Unknown location')
             time_period = story_context.get('initial_setting', {}).get('time_period', 'Unknown time')
             story_ctx_str = f"\nStory Context:\n- Genre: {genre}\n- Setting: {setting_summary} ({time_period})"

        goals_str = ",".join(initial_input.goals) if initial_input.goals else "None Specified"
        traits_str = ",".join(initial_input.traits) if initial_input.traits else "None Specified"
        prompt = PromptManager.get_prompt("character_genesis_expand",initial_input)
        try:
            logger.info(f"Generating detailed profile for {initial_input.name} using LLM...")
            response = await self.llm_wrapper.query_llm_async(prompt, max_tokens=800) # Allow ample tokens

            # --- Parse the LLM Response ---
            generated_details = {}
            current_key = None
            lines = response.strip().split('\n')
            key_map = {
                "Backstory": "backstory",
                "Core Traits": "core_traits",
                "Motivations": "motivations",
                "Flaws": "flaws",
                "Strengths": "strengths",
                "Long-Term Goals": "goals", 
                "Physical Description": "physical_description",
                "Mannerisms": "mannerisms",
                "Voice Description": "voice_description"
            }

            raw_content = {}
            for line in lines:
                 line = line.strip()
                 if not line: continue

                 found_key = False
                 for heading, key in key_map.items():
                     if line.startswith(heading + ":"):
                         current_key = key
                         content = line.split(":", 1)[1].strip()
                         raw_content[current_key] = content
                         found_key = True
                         break
                 if not found_key and current_key:
                     # Append to the content of the current key if it's multiline (like backstory)
                     raw_content[current_key] += " " + line


            # Post-process parsed content (e.g., split lists)
            for key, content in raw_content.items():
                 if key in ["core_traits", "motivations", "flaws", "strengths", "goals", "mannerisms"]:
                     # Split by comma, handle potential numbering or bullet points
                     items = [item.strip().lstrip('-*. ') for item in content.split(',') if item.strip()]
                     generated_details[key] = items
                 else:
                     generated_details[key] = content.strip()


            # Fill missing keys with defaults if LLM didn't provide them
            #TODO : use the character_genesis_missing_info prompt to fill these values as well.
            for heading, key in key_map.items():
                 if key not in generated_details:
                     logger.warning(f"LLM did not generate '{heading}' for {initial_input.name}. Using default.")
                     if key in ["core_traits", "motivations", "flaws", "strengths", "goals", "mannerisms"]:
                        generated_details[key] = []
                     else:
                         generated_details[key] = "Not generated."


            logger.info(f"Successfully generated details for {initial_input.name}.")
            return generated_details

        except Exception as e:
            logger.error(f"LLM call failed during character genesis for {initial_input.name}: {e}", exc_info=True)
            # Return empty dict or raise? Returning empty allows fallback.
            return {}

    async def create_character_profile(self, initial_input: CharacterInput, story_context: Optional[Dict] = None) -> Optional[CharacterProfile]:
        """
        Creates a full CharacterProfile from initial input using LLM generation.

        Args:
            initial_input: The basic character data from input processing.
            story_context: Optional broader story context (genre, setting) to inform generation.

        Returns:
            A CharacterProfile object, or None if generation fails critically.
        """
        generated_details = await self._generate_details_with_llm(initial_input, story_context)

        if not generated_details:
            logger.error(f"Failed to generate LLM details for {initial_input.name}. Cannot create profile.")
            return None

        try:
            profile_data = {
                "name": initial_input.name,
                "role": initial_input.role,
                "initial_input": initial_input,
                "backstory": generated_details.get("backstory", "Backstory not generated."),
                "core_traits": generated_details.get("core_traits", initial_input.traits),
                "motivations": generated_details.get("motivations", []),
                "flaws": generated_details.get("flaws", []),
                "strengths": generated_details.get("strengths", []),
                "goals": generated_details.get("goals", initial_input.goals),
                "physical_description": generated_details.get("physical_description", initial_input.description), # Fallback
                "mannerisms": generated_details.get("mannerisms", []),
                "voice_description": generated_details.get("voice_description", "Standard voice."),
                "current_state": CharacterState()
            }

            profile = CharacterProfile(**profile_data)
            logger.info(f"Successfully created CharacterProfile for {profile.name} ({profile.character_id}).")
            return profile

        except ValidationError as e:
            logger.error(f"Validation failed creating CharacterProfile for {initial_input.name}: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating CharacterProfile for {initial_input.name}: {e}", exc_info=True)
            return None