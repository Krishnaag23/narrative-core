import json
from typing import Dict, List, Optional, Union

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
    
    def __init__(self, llm_wrapper=None):
        """
        Initialize the PlotArcGenerator.
        
        Args:
            llm_wrapper: Interface for LLM interactions (optional)
        """
        self.llm_wrapper = llm_wrapper
        self.plot_structures = {
            "three_act": PlotStructure.THREE_ACT,
            "hero_journey": PlotStructure.HERO_JOURNEY,
            "five_act": PlotStructure.FIVE_ACT
        }
    
    def generate_plot_arc(self, 
                          concept: Dict, 
                          structure_type: str = "three_act", 
                          genre: str = "drama",
                          cultural_context: Optional[str] = None) -> Dict:
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
        # Get the base structure
        if structure_type not in self.plot_structures:
            raise ValueError(f"Unknown structure_type: {structure_type}")
            
        base_structure = self.plot_structures[structure_type].copy()
        
        # If using LLM to generate plot points
        if self.llm_wrapper:
            # Create a prompt for the LLM
            prompt = self._create_plot_generation_prompt(concept, base_structure, genre, cultural_context)
            
            # Generate plot points using LLM
            response = self.llm_wrapper.generate(prompt)
            
            # Parse the response
            try:
                plot_arc = json.loads(response)
            except json.JSONDecodeError:
                # If response isn't valid JSON, try to extract structured data
                plot_arc = self._extract_plot_from_text(response, base_structure)
        else:
            # Placeholder for non-LLM implementation
            plot_arc = self._create_default_plot_arc(concept, base_structure, genre)
            
        return plot_arc
    
    def _create_plot_generation_prompt(self, concept, structure, genre, cultural_context):
        """Create a prompt for the LLM to generate plot points."""
        prompt = f"""
        Generate a detailed plot arc for a {genre} story with the following concept:
        
        Title: {concept.get('title', 'Untitled')}
        Main Theme: {concept.get('theme', 'N/A')}
        Setting: {concept.get('setting', 'N/A')}
        Main Character: {concept.get('protagonist', 'Unknown')}
        
        Use the {structure['name']} as a framework with the following stages:
        """
        
        for stage in structure['stages']:
            prompt += f"\n- {stage['name']}: {stage['description']}"
            
        if cultural_context:
            prompt += f"\n\nThe story should incorporate elements from {cultural_context} culture."
            
        prompt += """
        
        Return a JSON object with each stage containing:
        1. A summary of the events in this stage
        2. Key plot points
        3. Character development moments
        4. Important settings or locations
        
        Format the response as valid JSON.
        """
        
        return prompt
    
    def _extract_plot_from_text(self, text, structure):
        """Extract structured plot data from text if JSON parsing fails."""
        # Simple implementation - can be enhanced
        plot_arc = {"stages": []}
        
        for stage in structure['stages']:
            stage_data = {
                "name": stage['name'],
                "summary": f"Default summary for {stage['name']}",
                "plot_points": [f"Default plot point for {stage['name']}"],
                "character_development": [],
                "settings": []
            }
            plot_arc["stages"].append(stage_data)
            
        return plot_arc
    
    def _create_default_plot_arc(self, concept, structure, genre):
        """Create a default plot arc without using LLM."""
        plot_arc = {
            "title": concept.get('title', 'Untitled'),
            "genre": genre,
            "structure": structure['name'],
            "stages": []
        }
        
        for stage in structure['stages']:
            stage_data = {
                "name": stage['name'],
                "summary": f"Events for {stage['name']} stage of the story",
                "plot_points": [f"Key event in {stage['name']}", f"Another event in {stage['name']}"],
                "character_development": [f"Character change during {stage['name']}"],
                "settings": [f"Location during {stage['name']}"]
            }
            plot_arc["stages"].append(stage_data)
            
        return plot_arc
