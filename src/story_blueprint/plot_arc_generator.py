import json
from typing import Dict, List, Optional, Union
import logging 

from ..utils import LLMwrapper, PromptManager
from ..input_processing import StoryConcept

logger = logging.getLogger(__name__)

class PlotStructure:
    """Defines common plot structures that can be used as templates."""
    
    THREE_ACT = {
        "name": "Three-Act Structure",
        "stages": [
            {"name": "Setup", "description": "Introduce main characters, setting, and the status quo"},
            {"name": "Inciting Incident", "description": "Event that sets the story in motion"},
            {"name": "First Plot Point", "description": "Protagonist commits to addressing the conflict"},
            {"name": "Rising Action", "description": "Protagonist faces obstacles and complications"},
            {"name": "Midpoint", "description": "Major turning point or revelation"},
            {"name": "Complications & Higher Stakes", "description": "Difficulties increase, stakes are raised"},
            {"name": "Second Plot Point", "description": "Final piece of information needed to resolve the conflict"},
            {"name": "Climax", "description": "Protagonist faces the main conflict directly"},
            {"name": "Resolution", "description": "Fallout from the climax, new status quo established"}
        ]
    }
    
    HERO_JOURNEY = {
        "name": "Hero's Journey",
        "stages": [
            {"name": "Ordinary World", "description": "Hero's normal life before the adventure"},
            {"name": "Call to Adventure", "description": "Challenge or quest is presented"},
            {"name": "Refusal of the Call", "description": "Hero initially resists the adventure"},
            {"name": "Meeting the Mentor", "description": "Hero gains guidance from a mentor figure"},
            {"name": "Crossing the Threshold", "description": "Hero commits to the adventure"},
            {"name": "Tests, Allies, Enemies", "description": "Hero explores the new world, faces tests"},
            {"name": "Approach to the Inmost Cave", "description": "Hero prepares for major challenge"},
            {"name": "Ordeal", "description": "Hero faces a major crisis"},
            {"name": "Reward", "description": "Hero gains reward from the crisis"},
            {"name": "The Road Back", "description": "Hero begins journey back to ordinary world"},
            {"name": "Resurrection", "description": "Final challenge where hero applies lessons learned"},
            {"name": "Return with Elixir", "description": "Hero returns with something to benefit the world"}
        ]
    }
    
    FIVE_ACT = {
        "name": "Five-Act Structure",
        "stages": [
            {"name": "Exposition", "description": "Introduces characters, setting, and basic conflict"},
            {"name": "Rising Action", "description": "Conflict develops, complications arise"},
            {"name": "Climax", "description": "Turning point of the story, highest tension"},
            {"name": "Falling Action", "description": "Events resulting from the climax"},
            {"name": "Resolution", "description": "Conflict is resolved, new status quo"}
        ]
    }


class PlotArcGenerator:
    """Generates a complete narrative structure based on input themes and concepts."""
    
    def __init__(self, llm_wrapper: LLMwrapper):
        """
        Initialize the PlotArcGenerator.
        
        Args:
            llm_wrapper: Interface for LLM interactions (optional)
        """
        self.llm_wrapper = llm_wrapper
        self.prompt_manager = PromptManager()
        self.plot_structures = {
            "three_act": PlotStructure.THREE_ACT,
            "hero_journey": PlotStructure.HERO_JOURNEY,
            "five_act": PlotStructure.FIVE_ACT
        }
        logger.info("PLOT ARC generator initialised")
    
    async def generate_plot_arc(self, 
                          story_concept:StoryConcept,
                          structure_type: str = "three_act", 
                          ) -> Optional[Dict[str , any]]:
        """
        Generate a complete plot arc based on input concept and structure type.
        
        Args:
            concept: Dictionary containing story concept details
            structure_type: Type of plot structure to use as template
            genre: Genre of the story (affects pacing and plot points)
            cultural_context: Cultural context to consider in plot generation
            
        Returns:
            Dictionary containing the complete plot arc
        """
        logger.info(f"Generating plot arc for concept: {story_concept.title_suggestion or 'Untitled'}")
        # Get the base structure
        if structure_type not in self.plot_structures:
            raise ValueError(f"Unknown structure_type: {structure_type}")
            
        structure_template = self.plot_structures[structure_type].copy()
        
        structure_stages_text = "\n".join([f"- {s['name']}: {s['description']}" for s in structure_template['stages']])
        character_summaries = [
            f"- {c.name} ({c.role.value}): {c.description[:100]}..." 
            for c in story_concept.initial_characters
        ]

        prompt = self.prompt_manager.get_prompt(
            "generate_plot_arc_points",
            title_suggestion=story_concept.title_suggestion,
            logline=story_concept.initial_plot.logline,
            genre=story_concept.genre_analysis.primary_genre[0],
            audience=story_concept.target_audience.value,
            conflict=story_concept.initial_plot.primary_conflict.value,
            themes=", ".join(story_concept.initial_plot.potential_themes),
            character_summaries="\n".join(character_summaries),
            setting_summary=f"{story_concept.initial_setting.location} ({story_concept.initial_setting.time_period})",
            cultural_notes=", ".join(story_concept.cultural_analysis.detected_keywords) or "None",
            structure_name=structure_template['name'],
            structure_stages=structure_stages_text
        )

        if not prompt:
            logger.error("Failed to get 'generate_plot_arc_points' prompt.")
            return None

        try:
            response = await self.llm.query_llm_async(prompt, max_tokens=20000, temperature=0.7)

            if not response:
                logger.error("LLM did not return a response for plot arc generation.")
                return None

            try:
                plot_arc_data = json.loads(response)
                logger.info("Successfully parsed LLM response as JSON for plot arc.")
                # TODO: Add validation against a Pydantic model for the plot arc structure
                return plot_arc_data
            except json.JSONDecodeError:
                logger.warning("LLM response for plot arc was not valid JSON. Returning raw text (needs parsing).")
                # Fallback: Return the raw text, indicating it needs parsing downstream
                return {"raw_llm_output": response, "error": "JSON parsing failed"}

        except Exception as e:
            logger.error(f"LLM call failed during plot arc generation: {e}", exc_info=True)
            return None 