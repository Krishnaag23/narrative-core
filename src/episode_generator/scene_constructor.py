from typing import Dict, List, Optional, Any
from ..utils import LLMwrapper, PromptManager
from ..character_system import CharacterProfile
import json
import logging

logger = logging.getLogger(__name__)

class SceneConstructor:
    """Constructs detailed scenes based on outlines, using LLM."""

    def __init__(self, llm_wrapper: LLMwrapper):
        """
        Initialize the SceneConstructor.

        Args:
            llm_wrapper: Interface for LLM interactions.
        """
        self.llm_wrapper = llm_wrapper
        self.prompt_manager = PromptManager() # Assumes singleton access
        if not self.llm_wrapper:
             # If no LLM, we can only generate default scenes. Log warning.
             logger.warning("SceneConstructor initialized without LLM wrapper. LLM-based scene generation disabled.")

    async def construct_scene(self,
                       scene_outline: Dict,
                       characters: Dict[str, CharacterProfile], # Expect Dict[name, Profile] of relevant chars
                       episode_context: Dict,
                       pacing: str = "standard",
                       scene_number: Optional[int] = None,
                       scene_objective: Optional[str] = None,
                       previous_scene_summary: Optional[str] = None
                       ) -> Optional[Dict]:
        """
        Construct a well-paced scene using LLM or default logic.

        Args:
            scene_outline: Basic outline including keys like 'characters' (list of names), 'setting', 'action', 'dialogue_focus'.
            characters: Dictionary mapping character names (present in scene) to their CharacterProfile objects.
            episode_context: Context of the current episode (e.g., number, summary).
            pacing: Desired pacing ("slow", "standard", "fast").
            scene_number: The sequence number of this scene.
            scene_objective: The main goal or purpose of this scene.
            previous_scene_summary: Summary of the preceding scene, if any.


        Returns:
            Constructed scene dict with elements, or None on failure.
        """
        logger.debug(f"Constructing scene {scene_number or 'N/A'} with {len(characters)} characters.")
        if self.llm_wrapper:
            # Pass all necessary context down to the LLM prompt generation
            return await self._construct_scene_with_llm(
                scene_outline=scene_outline,
                characters=characters,
                episode_context=episode_context,
                pacing=pacing,
                scene_number=scene_number,
                scene_objective=scene_objective,
                previous_scene_summary=previous_scene_summary
            )
        else:
            # Fallback if LLM is not available
            logger.warning("LLM wrapper not available, generating default scene.")
            return self._construct_default_scene(scene_outline, characters, pacing, scene_number=scene_number)

    async def _construct_scene_with_llm(self,
                               scene_outline: Dict,
                               characters: Dict[str, CharacterProfile], # Dict[name, Profile]
                               episode_context: Dict,
                               pacing: str,
                               scene_number: Optional[int] = None,
                               scene_objective: Optional[str] = None,
                               previous_scene_summary: Optional[str] = None
                               ) -> Optional[Dict]:
        """Construct a scene using LLM (async)."""
        prompt = self._create_scene_construction_prompt(
            scene_outline=scene_outline,
            characters=characters,
            episode_context=episode_context,
            pacing=pacing,
            scene_number=scene_number,
            scene_objective=scene_objective,
            previous_scene_summary=previous_scene_summary
        )

        if not prompt:
             logger.error(f"Failed to generate prompt for scene {scene_number}.")
             return None # Cannot proceed without prompt

        try:
            response = await self.llm_wrapper.query_llm_async(prompt, max_tokens=1500, temperature=0.7) # Increased tokens

            if not response:
                 logger.error(f"LLM did not return a response for scene {scene_number} construction.")
                 # Optionally fallback to default scene here?
                 return self._construct_default_scene(scene_outline, characters, pacing, scene_number=scene_number)


            # --- Attempt to Parse LLM Output ---
            # This section needs to be robust based on whether the prompt reliably yields JSON
            # or if it yields text that needs parsing. The current prompt ASKS for JSON.
            try:
                scene_data = json.loads(response)
                logger.info(f"Successfully parsed LLM response as JSON for scene {scene_number}.")
                # Add identifiers/context if not included by LLM
                scene_data['scene_number'] = scene_number
                scene_data['characters_present'] = list(characters.keys()) # Add list of names from input dict
                # TODO: Validate scene_data structure against a Pydantic model
                return scene_data
            except json.JSONDecodeError:
                logger.warning(f"LLM response for scene {scene_number} was not valid JSON. Using raw text as description.")
                # Fallback: Create a basic scene structure with the raw text
                scene_data = self._construct_default_scene(scene_outline, characters, pacing, scene_number=scene_number)
                # Replace default elements with the LLM's raw response
                scene_data['elements'] = [{"type": "description", "content": response.strip()}]
                scene_data['llm_parse_error'] = True # Flag parsing failure
                return scene_data

        except Exception as e:
            logger.error(f"Error during LLM scene construction for scene {scene_number}: {e}", exc_info=True)
            # Fallback to default scene on any LLM error
            return self._construct_default_scene(scene_outline, characters, pacing, scene_number=scene_number)


    def _create_scene_construction_prompt(self,
                                       scene_outline: Dict,
                                       characters: Dict[str, CharacterProfile], # Dict[name, Profile]
                                       episode_context: Dict,
                                       pacing: str,
                                       scene_number: Optional[int] = None,
                                       scene_objective: Optional[str] = None,
                                       previous_scene_summary: Optional[str] = None
                                       ) -> Optional[str]:
        """Create a prompt for scene construction using PromptManager."""

        # --- Format Character Info ---
        character_profiles_summary_parts = []
        # Use the keys from the passed 'characters' dictionary (which should only contain relevant characters)
        for char_name, profile in characters.items():
             # Use the profile's method to get a concise summary
             summary = profile.get_core_summary()
             # Maybe shorten further if needed for the prompt
             short_summary = "\n".join(summary.splitlines()[:7]) # Example: first 7 lines
             character_profiles_summary_parts.append(f"--- {char_name} ---\n{short_summary}\n")

        character_profiles_summary = "\n".join(character_profiles_summary_parts) or "No characters present or details available."

        # --- Extract info from scene_outline ---
        # The scene_outline passed from ScriptBuilder should contain the necessary details
        plot_points_str = "\n".join([f"- {p}" for p in scene_outline.get('plot_points', [])]) or "Focus on character interaction and scene objective."


        # --- Get Prompt Template ---
        # Using the key defined in 'episode_generation_prompts.yaml'
        prompt = self.prompt_manager.get_prompt(
            "construct_scene", # Template key
            episode_number=episode_context.get('episode_number', 'N/A'),
            scene_number=scene_number or 'N/A',
            scene_objective=scene_objective or scene_outline.get('dialogue_focus', 'Fulfill narrative requirements.'),
            plot_points=plot_points_str,
            character_profiles_summary=character_profiles_summary,
            previous_scene_summary=previous_scene_summary or "This is the first scene.",
            episode_summary=episode_context.get('summary_objective', 'Episode context not available.'),
            tone=episode_context.get('desired_tone', 'Neutral') # Get tone from episode context or fallback
        )

        if not prompt:
            logger.error("Failed to retrieve 'construct_scene' prompt template.")
            return None

        # The prompt itself should guide the LLM on structure (JSON requested) and pacing.

        return prompt

    def _construct_default_scene(self,
                              scene_outline: Dict,
                              characters: Dict[str, CharacterProfile], # Dict[name, Profile]
                              pacing: str,
                              scene_number: Optional[int] = None) -> Dict:
        """Construct a default scene without using LLM (synchronous)."""
        logger.debug(f"Generating default scene content for scene {scene_number or 'N/A'}.")
        scene_elements = []
        scene_setting = scene_outline.get('setting', 'Default Location')

        # Opening
        scene_elements.append({"type": "description", "content": f"The scene opens in {scene_setting}."})

        char_list = list(characters.keys()) # Use keys from the passed dictionary

        for char_name in char_list:
            scene_elements.append({"type": "action", "character": char_name, "content": f"{char_name} is present."})

        # Interaction
        if len(char_list) >= 2:
            scene_elements.append({"type": "dialogue", "character": char_list[0], "content": f"[Placeholder dialogue for {char_list[0]}]"})
            scene_elements.append({"type": "dialogue", "character": char_list[1], "content": f"[Placeholder response from {char_list[1]}]"})
        scene_elements.append({"type": "action", "content": "[Placeholder action driving the scene.]"})

        # Climax/Key Moment
        scene_elements.append({"type": "action", "content": "[Placeholder key moment or revelation.]"})
        if char_list:
            scene_elements.append({"type": "dialogue", "character": char_list[0], "content": f"[Placeholder dialogue related to key moment - {char_list[0]}]"})

        # Resolution
        scene_elements.append({"type": "action", "content": "[Placeholder concluding action.]"})

        scene = {
            "scene_number": scene_number or -1,
            "setting": scene_setting, # Use extracted setting
            "mood": "neutral",
            "elements": scene_elements,
            "dramatic_function": scene_outline.get('dialogue_focus', 'Default function'),
            "characters_present": char_list
        }
        return scene

    # adjust_pacing method remains unchanged
    def adjust_pacing(self, scene: Dict, desired_pacing: str) -> Dict:
        # ... (Keep the existing adjust_pacing logic) ...
        adjusted_scene = scene.copy()
        elements = adjusted_scene.get('elements', [])

        if desired_pacing == "fast":
            new_elements = []
            skip_next = False
            for i, element in enumerate(elements):
                if skip_next: skip_next = False; continue
                if element.get('type') == 'description':
                    content = element.get('content', '')
                    if len(content) > 50: element['content'] = content.split('.')[0] + '.'
                elif element.get('type') == 'dialogue':
                    content = element.get('content', '')
                    if len(content) > 30: element['content'] = ' '.join(content.split()[:7]) + '...'
                    if i < len(elements) - 1 and elements[i+1].get('type') == 'dialogue':
                        next_elem = elements[i+1]
                        element['content'] += f" {next_elem.get('character')}: {next_elem.get('content')}"
                        skip_next = True
                new_elements.append(element)
            adjusted_scene['elements'] = new_elements
        elif desired_pacing == "slow":
            new_elements = []
            for i, element in enumerate(elements):
                new_elements.append(element)
                if element.get('type') == 'dialogue' and i > 0:
                    char = element.get('character', '')
                    if char: new_elements.append({"type": "action", "character": char, "content": f"{char} pauses..."})
                if i > 0 and i % 3 == 0:
                    new_elements.append({"type": "description", "content": "The atmosphere shifts..."})
            adjusted_scene['elements'] = new_elements
        return adjusted_scene