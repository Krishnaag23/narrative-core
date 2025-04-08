# ================================================
# FILE: src/episode_generator/script_builder.py (CORRECTED)
# ================================================
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
        self.llm_wrapper = llm_wrapper
        self.prompt_manager = PromptManager()
        self.character_facade = character_facade
        # Ensure SceneConstructor gets initialized correctly
        self.scene_constructor = SceneConstructor(llm_wrapper=llm_wrapper)
        logger.info("ScriptBuilder initialized.")

    async def build_script(self,
        episode_outline: Dict[str, Any],
        character_profiles: Dict[str, CharacterProfile] # Expecting Dict[name, Profile]
    ) -> Optional[Dict[str, Any]]:
        """
        Build a complete script for an episode.

        Args:
            episode_outline: Outline containing plot points, objectives, etc.
            character_profiles: Dictionary of available character profiles (name -> Profile object).

        Returns:
            A dictionary representing the final episode script, or None on failure.
        """
        episode_number = episode_outline.get("episode_number", "N/A")
        logger.info(f"Building script for Episode {episode_number}...")

        final_scenes = []
        previous_scene_summary = None # TODO: Integrate summarizer to update this

        plot_points = episode_outline.get("plot_points", [])
        # Determine number of scenes. Simple logic for now.
        num_scenes = max(3, len(plot_points))
        points_per_scene = max(1, -(-len(plot_points) // num_scenes)) if num_scenes > 0 else 0 # Ceiling division

        for i in range(num_scenes):
            scene_num = i + 1
            start_idx = i * points_per_scene
            end_idx = min((i + 1) * points_per_scene, len(plot_points))
            scene_plot_points = plot_points[start_idx:end_idx]
            scene_objective = f"Advance plot points: {', '.join(scene_plot_points)}" if scene_plot_points else f"Develop character interactions or setting for Episode {episode_number}, Scene {scene_num}"

            # --- Determine Characters ACTUALLY in this scene ---
            # Heuristic: Characters mentioned in plot points for this scene or objective
            scene_content_lower = scene_objective.lower() + " ".join(scene_plot_points).lower()
            actual_chars_in_scene_dict = {
                name: profile for name, profile in character_profiles.items()
                if name.lower() in scene_content_lower # Simple check, could be improved
            }
            # Fallback if heuristic finds no one but characters exist overall
            if not actual_chars_in_scene_dict and character_profiles:
                logger.warning(f"Scene {scene_num} heuristic found no characters based on plot points/objective. Including first character as fallback.")
                first_char_name = next(iter(character_profiles))
                actual_chars_in_scene_dict = {first_char_name: character_profiles[first_char_name]}

            actual_char_names_list = list(actual_chars_in_scene_dict.keys())
            logger.debug(f"Characters determined for Scene {scene_num}: {actual_char_names_list}")

            # --- Prepare Scene Outline for SceneConstructor ---
            # Try to get a relevant setting note from the episode outline if available
            setting_notes_arc = episode_outline.get("setting_notes_arc", ["Default Setting"])
            scene_setting_hint = setting_notes_arc[i % len(setting_notes_arc)] if setting_notes_arc else "Default Setting"

            scene_outline_for_constructor = {
                "setting": scene_setting_hint,
                "characters": actual_char_names_list, # List of names
                "action": f"Actions related to plot points: {', '.join(scene_plot_points)}", # Action hint
                "dialogue_focus": scene_objective, # Dialogue hint based on objective
                "plot_points": scene_plot_points # Pass the specific points for this scene
            }

            # --- Construct Scene Base ---
            logger.debug(f"Calling SceneConstructor for Scene {scene_num}...")
            constructed_scene_base = await self.scene_constructor.construct_scene(
                scene_outline=scene_outline_for_constructor,
                characters=actual_chars_in_scene_dict, # Pass DICTIONARY of relevant characters
                episode_context=episode_outline,
                pacing="standard", # TODO: Get pacing dynamically
                scene_number=scene_num,
                scene_objective=scene_objective,
                previous_scene_summary=previous_scene_summary # Pass summary if available
            )

            if not constructed_scene_base:
                 logger.warning(f"Failed to construct base for Scene {scene_num}. Skipping scene.")
                 continue

            # Ensure scene base dict has necessary keys before refinement
            constructed_scene_base.setdefault("scene_number", scene_num)
            constructed_scene_base.setdefault("characters_present", actual_char_names_list)
            constructed_scene_base.setdefault("elements", [])

            # --- Refine Scene & Generate Dialogue ---
            logger.debug(f"Refining elements and generating dialogue for Scene {scene_num}...")
            refined_elements = await self._refine_scene_elements(
                scene_base=constructed_scene_base,
                characters=actual_chars_in_scene_dict, # Pass filtered dict
                scene_objective=scene_objective
            )

            constructed_scene_base["elements"] = refined_elements
            final_scenes.append(constructed_scene_base)

            # TODO: Update previous_scene_summary using summarizer here
            # previous_scene_summary = await summarizer.summarize_scene(refined_elements)

        # --- Assemble Final Script ---
        if not final_scenes:
            logger.error(f"Failed to build any scenes for Episode {episode_number}.")
            return None

        final_script = {
            "episode_number": episode_number,
            "title": episode_outline.get("title", f"Episode {episode_number}"),
            "scenes": final_scenes
        }

        logger.info(f"Successfully built script for Episode {episode_number}.")
        return final_script


    async def _refine_scene_elements(
        self,
        scene_base: Dict[str, Any],
        characters: Dict[str, CharacterProfile], # name -> profile map of chars PRESENT
        scene_objective: str
    ) -> List[Dict[str, Any]]:
        """
        Iterates through scene elements, generates dialogue using CharacterSystemFacade.
        """
        refined_elements = []
        dialogue_history: List[str] = []
        scene_setting_desc = scene_base.get("setting", "Scene setting description missing")
        scene_description = f"Setting: {scene_setting_desc}. Mood: {scene_base.get('mood', 'neutral')}."

        chars_present_names = scene_base.get("characters_present", [])
        chars_present_profiles = [characters[name] for name in chars_present_names if name in characters]

        if not chars_present_profiles:
             logger.warning(f"Scene {scene_base.get('scene_number')} has no characters for dialogue. Returning base elements.")
             return scene_base.get("elements", [])

        speaker_turn_index = 0
        elements_to_process = scene_base.get("elements", [])

        # Process existing elements and insert dialogue turns
        for element in elements_to_process:
            refined_elements.append(element) # Keep original description/action

            # Simple trigger: Add dialogue after non-dialogue elements if characters are present
            if element.get("type") != "dialogue" and chars_present_profiles:
                # Determine who speaks next
                if not chars_present_profiles: continue # Skip if no characters somehow
                speaker_profile = chars_present_profiles[speaker_turn_index % len(chars_present_profiles)]
                speaker_turn_index += 1

                logger.debug(f"Attempting dialogue for {speaker_profile.name} after element type '{element.get('type')}'...")

                recent_dialogue_lines = [line.split(":", 1)[1].strip() for line in dialogue_history[-5:] if ":" in line]
                other_chars_in_scene = [p for p in chars_present_profiles if p.character_id != speaker_profile.character_id]
                other_char_ids = [p.character_id for p in other_chars_in_scene]

                dialogue_scene_context = f"{scene_description}\nCurrent situation/action: {element.get('content', 'Interacting')}"

                # Call Character System Facade
                generated_line = await self.character_facade.generate_dialogue_for_character(
                    character_id=speaker_profile.character_id,
                    scene_context=dialogue_scene_context,
                    recent_dialogue=recent_dialogue_lines,
                    other_character_ids=other_char_ids,
                    scene_objective=scene_objective # Pass scene objective to guide dialogue
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

            elif element.get("type") == "dialogue":
                 # Just record existing dialogue for history
                 char_name = element.get("character", "Unknown")
                 line_content = element.get("content", "")
                 dialogue_history.append(f"{char_name}: {line_content}")


        # Check if enough interaction occurred, maybe add closing action/dialogue if needed
        if len(chars_present_profiles) > 0 and not any(el.get("type") == "dialogue" for el in refined_elements):
             logger.debug(f"No dialogue generated for scene {scene_base.get('scene_number')}. May be non-verbal or scene construction failed.")
             # Add a comment or simple closing action
             refined_elements.append({"type": "action", "content": "[Scene concludes.]"})

        return refined_elements