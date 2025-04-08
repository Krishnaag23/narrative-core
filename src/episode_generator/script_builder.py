import json
from typing import Dict, List, Optional, Any
import logging 

from ..utils import LLMwrapper, PromptManager
from ..character_system import CharacterSystemFacade, CharacterProfile
from .scene_constructor import SceneConstructor

logger = logging.getLogger(__name__)


class ScriptBuilder:
    """Assembles scenes into full episode scripts generating dialogue."""
    
    def __init__(self, llm_wrapper: LLMwrapper, character_facade:CharacterSystemFacade):
        """
        Initialize the ScriptBuilder.
        """

        self.llm_wrapper = llm_wrapper
        self.prompt_manager = PromptManager()
        self.character_facade = character_facade
        self.scene_constructor = SceneConstructor(llm_wrapper)
    
    async def build_script(self,
        episode_outline: Dict[str, Any],
        character_profiles: Dict[str, CharacterProfile] 
    ) -> Optional[Dict[str, Any]]:
        """
        Build a complete script for an episode.
        
        Args:
            episode_outline: Outline containing plot points, objectives, etc.
            character_profiles: Dictionary of available character profiles.

        Returns:
            A dictionary representing the final episode script, or None on failure. 
        """
        episode_number = episode_outline.get("episode_number", "N/A")
        logger.info(f"Building script for Episode {episode_number}...")

        final_scenes = []
        previous_scene_summary = None # Track summary for context

        # Estimate scenes needed based on plot points (simple logic)
        num_scenes = max(3, len(episode_outline.get("plot_points", []))) # At least 3 scenes
        plot_points = episode_outline.get("plot_points", [])
        points_per_scene = max(1, len(plot_points) // num_scenes)

        for i in range(num_scenes):
            scene_num = i + 1
            start_idx = i * points_per_scene
            end_idx = (i + 1) * points_per_scene if i < num_scenes - 1 else len(plot_points)
            scene_plot_points = plot_points[start_idx:end_idx]
            scene_objective = f"Advance plot points: {', '.join(scene_plot_points)}" if scene_plot_points else f"Develop character interactions for Episode {episode_number}"

            # Identify characters likely involved (basic: all characters mentioned in points?)
            # Needs refinement - map characters to plot points better in blueprint phase
            chars_in_scene_profiles = list(character_profiles.values()) # Placeholder: Assume all chars potentially present

            # Construct Scene Base (Setting, Actions, Dialogue Placeholders/Directions)
            constructed_scene_base = await self.scene_constructor.construct_scene(
                scene_outline=scene_objective,
                characters=chars_in_scene_profiles,
                episode_context=episode_outline,
                # TODO: Get tone from story concept or episode outline
                pacing=episode_outline.get("tone", "Neutral")
            )

            if not constructed_scene_base:
                 logger.warning(f"Failed to construct base for Scene {scene_num}. Skipping scene.")
                 continue

            #  Refine Scene & Generate Dialogue
            refined_elements = await self._refine_scene_elements(
                scene_base=constructed_scene_base,
                characters=character_profiles,
                scene_objective=scene_objective
            )

            constructed_scene_base["elements"] = refined_elements
            final_scenes.append(constructed_scene_base)

            # TODO: Generate summary for this scene to feed into the next
            # previous_scene_summary = await self.summarizer.summarize_scene(refined_elements)

        if not final_scenes:
            logger.error(f"Failed to build any scenes for Episode {episode_number}.")
            return None

        final_script = {
            "episode_number": episode_number,
            "title": episode_outline.get("title", f"Episode {episode_number}"),
            "scenes": final_scenes
            # TODO: Add overall episode summary generated from final scenes
        }

        logger.info(f"Successfully built script for Episode {episode_number}.")
        return final_script


    async def _refine_scene_elements(
        self,
        scene_base: Dict[str, Any],
        characters: Dict[str, CharacterProfile], # name -> profile map
        scene_objective: str
    ) -> List[Dict[str, Any]]:
        """
        Iterates through scene elements, identifies dialogue needs,
        and calls the CharacterSystemFacade to generate dialogue.
        This version assumes scene_base might contain placeholder elements
        or descriptions hinting at dialogue turns.

        Args:
            scene_base: The scene dictionary from SceneConstructor.
            characters: All available character profiles.
            scene_objective: The overall objective for this scene.

        Returns:
            An updated list of scene elements with generated dialogue.
        """
        refined_elements = []
        dialogue_history: List[str] = [] # Track recent lines for context: ["CharacterName: Line", ...]
        scene_description = scene_base.get("setting_description", "Scene context") # Use generated description
        chars_present_names = scene_base.get("characters_present", [])
        chars_present_profiles = [characters[name] for name in chars_present_names if name in characters]

        # --- TODO: refinement based on how SceneConstructor outputs hints ---
        # Example: Iterate through elements, looking for descriptions implying dialogue
        #          or placeholder elements like {"type": "dialogue_turn", "character": "Name"}

        # Placeholder: Simple turn-taking between characters present for demo
        speaker_turn_index = 0
        elements_to_process = scene_base.get("elements", [])

        for element in elements_to_process:
            refined_elements.append(element) # Keep the original element (description, action)

            # Check if this element implies a dialogue turn or if we need to insert one
            # Simplified logic: Add dialogue after descriptions mentioning characters
            content = element.get("content", "").lower() if element.get("type") == "description" else ""
            mentioned_chars = [name for name in chars_present_names if name.lower() in content]

            if mentioned_chars and chars_present_profiles:
                 # Determine who speaks next based on turn index
                 speaker_profile = chars_present_profiles[speaker_turn_index % len(chars_present_profiles)]
                 speaker_turn_index += 1 # Move to next character for the subsequent turn

                 logger.debug(f"Attempting dialogue generation for {speaker_profile.name}...")

                 # Prepare context for dialogue generation
                 # Get recent dialogue strings only
                 recent_dialogue_lines = [line.split(":", 1)[1].strip() for line in dialogue_history[-5:]] # Last 5 lines content

                 # Find other characters *besides* the speaker
                 other_chars_in_scene = [p for p in chars_present_profiles if p.character_id != speaker_profile.character_id]
                 other_char_ids = [p.character_id for p in other_chars_in_scene]

                 # Generate dialogue using the CharacterSystemFacade
                 generated_line = await self.character_facade.generate_dialogue_for_character(
                     character_id=speaker_profile.character_id,
                     scene_context=scene_description + "\nCurrent Action Hint: " + element.get("content", "Ongoing interaction"),
                     recent_dialogue=recent_dialogue_lines,
                     other_character_ids=other_char_ids,
                     # TODO: Extract character-specific objective if available from blueprint
                     scene_objective=scene_objective # Pass overall scene objective for now
                 )

                 if generated_line:
                      dialogue_element = {
                          "type": "dialogue",
                          "character": speaker_profile.name,
                          "content": generated_line
                      }
                      refined_elements.append(dialogue_element)
                      dialogue_history.append(f"{speaker_profile.name}: {generated_line}")
                      logger.debug(f"Added dialogue for {speaker_profile.name}: {generated_line[:50]}...")
                 else:
                      logger.warning(f"Failed to generate dialogue for {speaker_profile.name} in scene {scene_base.get('scene_number')}.")
                     
                      refined_elements.append({"type": "comment", "content": f"[Dialogue generation failed for {speaker_profile.name}]"})

        # If no dialogue was generated at all (e.g., only action scenes), add a comment
        if not any(el.get("type") == "dialogue" for el in refined_elements) and chars_present_profiles:
             logger.debug(f"No dialogue generated for scene {scene_base.get('scene_number')}. It might be action-focused.")
             refined_elements.append({"type": "comment", "content": "[Scene concludes without dialogue]"})


        return refined_elements