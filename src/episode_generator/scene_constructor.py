from typing import Dict, List, Optional, Tuple
from ..utils import LLMwrapper
import json

class SceneConstructor:
    """Constructs well-paced scenes with dramatic structure."""
    
    def __init__(self, llm_wrapper=LLMwrapper):
        """
        Initialize the SceneConstructor.
        
        Args:
            llm_wrapper: Interface for LLM interactions (optional)
        """
        self.llm_wrapper = llm_wrapper
        
    def construct_scene(self, 
                       scene_outline: Dict, 
                       characters: Dict,
                       episode_context: Dict,
                       pacing: str = "standard") -> Dict:
        """
        Construct a well-paced scene.
        
        Args:
            scene_outline: Basic outline of the scene
            characters: Character profiles
            episode_context: Context of the current episode
            pacing: Desired pacing ("slow", "standard", "fast")
            
        Returns:
            Constructed scene with dramatic structure
        """
        if self.llm_wrapper:
            return self._construct_scene_with_llm(scene_outline, characters, episode_context, pacing)
        else:
            return self._construct_default_scene(scene_outline, characters, pacing)
    
    async def _construct_scene_with_llm(self, 
                               scene_outline: Dict, 
                               characters: Dict,
                               episode_context: Dict,
                               pacing: str) -> Dict:
        """Construct a scene using LLM."""
        # Create the prompt
        prompt = self._create_scene_construction_prompt(scene_outline, characters, episode_context, pacing)
        
        # Generate scene with LLM
        response = await self.llm_wrapper.query_llm_async(prompt)
        
        # Parse the response
        try:
            scene = json.loads(response)
        except json.JSONDecodeError:
            # Fallback to default if parsing fails
            scene = self._construct_default_scene(scene_outline, characters, pacing)
            
        return scene
    
    def _create_scene_construction_prompt(self, 
                                       scene_outline: Dict, 
                                       characters: List,
                                       episode_context: Dict,
                                       pacing: str) -> str:
        """Create a prompt for scene construction."""
        # Format character information
        character_info = ""
        for char_name, char_data in characters:
            if char_name in scene_outline.get('characters', []):
                char_info = f"""
                {char_name}:
                - Personality: {char_data.get('personality', 'Unknown')}
                - Goals: {char_data.get('goals', 'Unknown')}
                - Current emotional state: {char_data.get('emotional_state', 'Neutral')}
                """
                character_info += char_info
        
        # Adjust pacing instructions
        pacing_instructions = {
            "slow": "Create a deliberately paced scene with atmospheric description and character introspection. Allow moments to breathe.",
            "standard": "Create a balanced scene with a natural rhythm of action, dialogue, and description.",
            "fast": "Create a fast-paced scene with quick exchanges, efficient description, and rapid movement."
        }.get(pacing, "Create a balanced scene with a natural rhythm.")
        
        prompt = f"""
        Construct a detailed scene based on the following outline:
        
        Setting: {scene_outline.get('setting', 'Unknown location')}
        Characters present: {', '.join(scene_outline.get('characters', []))}
        Action: {scene_outline.get('action', 'Unknown action')}
        Dialogue focus: {scene_outline.get('dialogue_focus', 'Unknown focus')}
        
        Episode context:
        {episode_context.get('title', 'Untitled')}
        {episode_context.get('summary', 'No summary')}
        
        Characters:
        {character_info}
        
        Pacing instruction: {pacing_instructions}
        
        Create a dramatically structured scene with:
        1. Opening/establishing elements
        2. Rising tension or development
        3. Peak moment or revelation
        4. Resolution or consequence
        
        Format the response as valid JSON with this structure:
        {{
            "setting": "Detailed setting description",
            "mood": "Emotional tone of the scene",
            "elements": [
                {{
                    "type": "description",
                    "content": "Descriptive text"
                }},
                {{
                    "type": "action",
                    "character": "Character name",  # Optional
                    "content": "Action description"
                }},
                {{
                    "type": "dialogue",
                    "character": "Character name",
                    "content": "Dialogue text"
                }},
                {{
                    "type": "sound",
                    "description": "Sound effect description"
                }},
                ... more elements ...
            ],
            "dramatic_function": "Purpose of this scene in the story"
        }}
        """
        
        return prompt
    
    def _construct_default_scene(self, 
                              scene_outline: Dict, 
                              characters: Dict,
                              pacing: str) -> Dict:
        """Construct a default scene without using LLM."""
        # Create a basic dramatic structure
        scene_elements = []
        
        # 1. Opening/establishing elements
        scene_elements.append({
            "type": "description",
            "content": f"The scene opens in {scene_outline.get('setting', 'the location')}."
        })
        
        char_list = scene_outline.get('characters', [])
        if not char_list and characters:
            # Use first two characters if none specified
            char_list = list(characters.keys())[:2]
            
        # Add character entrance actions
        for char in char_list:
            scene_elements.append({
                "type": "action",
                "character": char,
                "content": f"{char} enters the scene."
            })
            
        # 2. Rising tension or development
        if len(char_list) >= 2:
            # Add dialogue between characters
            scene_elements.append({
                "type": "dialogue",
                "character": char_list[0],
                "content": f"Initial dialogue from {char_list[0]}."
            })
            
            scene_elements.append({
                "type": "dialogue",
                "character": char_list[1],
                "content": f"Response from {char_list[1]}."
            })
            
        # Add action to build tension
        scene_elements.append({
            "type": "action",
            "content": "The tension builds as the scene progresses."
        })
        
        # 3. Peak moment or revelation
        scene_elements.append({
            "type": "sound",
            "description": "Sound effect emphasizing the peak moment."
        })
        
        scene_elements.append({
            "type": "action",
            "content": "A critical moment occurs, changing the dynamic."
        })
        
        if char_list:
            scene_elements.append({
                "type": "dialogue",
                "character": char_list[0],
                "content": "Dialogue revealing important information."
            })
            
        # 4. Resolution or consequence
        scene_elements.append({
            "type": "description",
            "content": "The scene begins to resolve."
        })
        
        if len(char_list) >= 2:
            scene_elements.append({
                "type": "dialogue",
                "character": char_list[1],
                "content": "Final thoughts on the situation."
            })
            
        scene_elements.append({
            "type": "action",
            "content": "The scene concludes with characters reacting to what transpired."
        })
        
        # Construct the scene
        scene = {
            "setting": scene_outline.get('setting', 'Default setting'),
            "mood": "neutral",  # Default mood
            "elements": scene_elements,
            "dramatic_function": "Advance the plot and develop character relationships."
        }
        
        return scene
    
    def adjust_pacing(self, scene: Dict, desired_pacing: str) -> Dict:
        """
        Adjust the pacing of an existing scene.
        
        Args:
            scene: Existing scene
            desired_pacing: Target pacing ("slow", "standard", "fast")
            
        Returns:
            Adjusted scene
        """
        adjusted_scene = scene.copy()
        elements = adjusted_scene.get('elements', [])
        
        if desired_pacing == "fast":
            # For fast pacing:
            # 1. Reduce descriptive text
            # 2. Shorten dialogue
            # 3. Combine or remove less important elements
            new_elements = []
            skip_next = False
            
            for i, element in enumerate(elements):
                if skip_next:
                    skip_next = False
                    continue
                    
                if element.get('type') == 'description':
                    # Shorten descriptions
                    content = element.get('content', '')
                    if len(content) > 50:
                        content = content.split('.')[0] + '.'  # Keep first sentence only
                        element['content'] = content
                
                elif element.get('type') == 'dialogue':
                    # Shorten dialogue
                    content = element.get('content', '')
                    if len(content) > 30:
                        words = content.split()
                        element['content'] = ' '.join(words[:7]) + '...'
                    
                    # Combine dialogue if possible
                    if i < len(elements) - 1 and elements[i+1].get('type') == 'dialogue':
                        next_elem = elements[i+1]
                        element['content'] += f" {next_elem.get('character')}: {next_elem.get('content')}"
                        skip_next = True
                        
                new_elements.append(element)
                
            adjusted_scene['elements'] = new_elements
            
        elif desired_pacing == "slow":
            # For slow pacing:
            # 1. Add more descriptive elements
            # 2. Add character reactions and thoughts
            # 3. Expand dialogue with pauses and reflection
            new_elements = []
            
            for i, element in enumerate(elements):
                new_elements.append(element)
                
                if element.get('type') == 'dialogue' and i > 0:
                    # Add reaction after dialogue
                    char = element.get('character', '')
                    if char:
                        new_elements.append({
                            "type": "action",
                            "character": char,
                            "content": f"{char} pauses, considering the weight of the words."
                        })
                        
                if i > 0 and i % 3 == 0:
                    # Add descriptive element periodically
                    new_elements.append({
                        "type": "description",
                        "content": "The environment shifts subtly, reflecting the changing mood."
                    })
                    
            adjusted_scene['elements'] = new_elements
            
        return adjusted_scene