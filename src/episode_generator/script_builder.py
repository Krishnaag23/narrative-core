import json
from typing import Dict, List, Optional

class ScriptBuilder:
    """Generates full episode scripts based on episode outlines."""
    
    def __init__(self, llm_wrapper=None, character_system=None):
        """
        Initialize the ScriptBuilder.
        
        Args:
            llm_wrapper: Interface for LLM interactions (optional)
            character_system: Character generation system for consistent dialogue
        """
        self.llm_wrapper = llm_wrapper
        self.character_system = character_system
    
    def build_script(self, 
                    episode_outline: Dict, 
                    characters: Dict,
                    story_context: Dict) -> Dict:
        """
        Build a complete script for an episode.
        
        Args:
            episode_outline: Outline with scenes and plot points
            characters: Character profiles for dialogue generation
            story_context: Overall story context and background
            
        Returns:
            Complete episode script
        """
        if self.llm_wrapper:
            return self._generate_script_with_llm(episode_outline, characters, story_context)
        else:
            return self._generate_default_script(episode_outline, characters)
    
    def _generate_script_with_llm(self, 
                               episode_outline: Dict, 
                               characters: Dict,
                               story_context: Dict) -> Dict:
        """Generate a script using LLM."""
        # Create the prompt for the LLM
        prompt = self._create_script_generation_prompt(episode_outline, characters, story_context)
        
        # Generate the script
        response = self.llm_wrapper.generate(prompt)
        
        # Parse the response
        try:
            script = json.loads(response)
        except json.JSONDecodeError:
            # If parsing fails, fall back to default script
            script = self._generate_default_script(episode_outline, characters)
            
        return script
    
    def _create_script_generation_prompt(self, 
                                      episode_outline: Dict, 
                                      characters: Dict,
                                      story_context: Dict) -> str:
        """Create a prompt for LLM to generate a script."""
        # Create character summaries
        character_summaries = ""
        for char_name, char_data in characters.items():
            summary = f"""
            {char_name}:
            - Personality: {char_data.get('personality', 'Unknown')}
            - Speech style: {char_data.get('dialogue_style', 'Unknown')}
            - Background: {char_data.get('background', 'Unknown')}
            """
            character_summaries += summary
            
        # Format scenes
        scenes_description = ""
        for i, scene in enumerate(episode_outline.get('scenes', [])):
            scene_text = f"""
            Scene {i+1}:
            - Setting: {scene.get('setting', 'Unknown')}
            - Characters: {', '.join(scene.get('characters', []))}
            - Action: {scene.get('action', 'Unknown')}
            - Dialogue focus: {scene.get('dialogue_focus', 'Unknown')}
            """
            scenes_description += scene_text
            
        # Create the prompt
        prompt = f"""
        Generate a complete script for Episode {episode_outline.get('episode_number', 'Unknown')}: "{episode_outline.get('title', 'Untitled')}"
        
        Story context:
        {story_context.get('title', 'Untitled')}
        {story_context.get('setting', 'Unknown setting')}
        {story_context.get('genre', 'Unknown genre')}
        
        Episode summary:
        {episode_outline.get('summary', 'No summary provided')}
        
        Characters:
        {character_summaries}
        
        Scenes:
        {scenes_description}
        
        Generate a complete script with:
        1. Scene descriptions
        2. Character dialogue (match their personality and speech style)
        3. Narration/voiceover (if appropriate)
        4. Sound effect notes (if appropriate)
        
        Format the response as valid JSON with this structure:
        {{
            "title": "Episode title",
            "episode_number": number,
            "scenes": [
                {{
                    "setting": "Scene setting",
                    "description": "Scene description",
                    "elements": [
                        {{
                            "type": "action",
                            "content": "Character action description"
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
                        {{
                            "type": "narration",
                            "content": "Narration text"
                        }}
                    ]
                }}
            ]
        }}
        """
        
        return prompt
    
    def _generate_default_script(self, episode_outline: Dict, characters: Dict) -> Dict:
        """Generate a default script without using LLM."""
        script = {
            "title": episode_outline.get('title', 'Untitled'),
            "episode_number": episode_outline.get('episode_number', 1),
            "scenes": []
        }
        
        # Create a scene for each scene in the outline
        for i, scene_outline in enumerate(episode_outline.get('scenes', [])):
            scene = {
                "setting": scene_outline.get('setting', f"Scene {i+1}"),
                "description": f"Scene {i+1} of episode {episode_outline.get('episode_number', 1)}",
                "elements": []
            }
            
            # Add scene description
            scene["elements"].append({
                "type": "action",
                "content": scene_outline.get('action', 'Default action')
            })
            
            # Add dialogue for characters in the scene
            char_list = scene_outline.get('characters', [])
            if not char_list and characters:
                # Use first two characters if none specified
                char_list = list(characters.keys())[:2]
                
            for char in char_list:
                scene["elements"].append({
                    "type": "dialogue",
                    "character": char,
                    "content": f"Default dialogue for {char}"
                })
                
            # Add another action
            scene["elements"].append({
                "type": "action",
                "content": "Continued action"
            })
            
            # Add sound effect
            scene["elements"].append({
                "type": "sound",
                "description": "Ambient sound effect"
            })
            
            # Add more dialogue
            if char_list:
                scene["elements"].append({
                    "type": "dialogue",
                    "character": char_list[0],
                    "content": f"More dialogue for {char_list[0]}"
                })
            
            # Add narration if it's first or last scene
            if i == 0 or i == len(episode_outline.get('scenes', [])) - 1:
                scene["elements"].append({
                    "type": "narration",
                    "content": "Narration text"
                })
                
            script["scenes"].append(scene)
            
        return script
    
    def generate_character_dialogue(self, 
                                  character: Dict, 
                                  context: str, 
                                  previous_dialogue: Optional[List[str]] = None) -> str:
        """
        Generate dialogue for a specific character.
        
        Args:
            character: Character profile
            context: Context of the dialogue
            previous_dialogue: Previous lines in the conversation
            
        Returns:
            Generated dialogue line
        """
        if self.character_system:
            # Use character system if available
            return self.character_system.generate_dialogue(character, context, previous_dialogue)
        elif self.llm_wrapper:
            # Use LLM directly if available
            return self._generate_dialogue_with_llm(character, context, previous_dialogue)
        else:
            # Default dialogue
            return f"Default dialogue for {character.get('name', 'Character')}"
    
    def _generate_dialogue_with_llm(self, 
                                 character: Dict, 
                                 context: str, 
                                 previous_dialogue: Optional[List[str]] = None) -> str:
        """Generate character dialogue using LLM."""
        # Create a prompt for dialogue generation
        prompt = self._create_dialogue_generation_prompt(character, context, previous_dialogue)
        
        # Generate dialogue with LLM
        dialogue = self.llm_wrapper.generate(prompt)
        
        return dialogue.strip('"\'')
    
    def _create_dialogue_generation_prompt(self, 
                                        character: Dict, 
                                        context: str, 
                                        previous_dialogue: Optional[List[str]] = None) -> str:
        """Create a prompt for dialogue generation."""
        char_name = character.get('name', 'Character')
        
        prompt = f"""
        Generate a single line of dialogue for {char_name}.
        
        Character details:
        - Personality: {character.get('personality', 'Unknown')}
        - Speech style: {character.get('dialogue_style', 'Unknown')}
        - Background: {character.get('background', 'Unknown')}
        
        Context: {context}
        """
        
        if previous_dialogue:
            dialogue_history = "\n".join(previous_dialogue[-5:])  # Last 5 lines
            prompt += f"""
            
            Previous dialogue:
            {dialogue_history}
            
            {char_name}'s next line:
            """
        
        return prompt