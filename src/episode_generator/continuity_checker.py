from typing import Dict, List, Set, Tuple, Optional
import difflib

class ContinuityError:
    """Represents a continuity error in a story."""
    
    def __init__(self, error_type: str, description: str, location: Dict):
        """
        Initialize a continuity error.
        
        Args:
            error_type: Type of continuity error
            description: Detailed description of the error
            location: Where the error occurs (episode, scene, etc.)
        """
        self.error_type = error_type
        self.description = description
        self.location = location
        
    def __str__(self):
        """String representation of the error."""
        return f"{self.error_type}: {self.description} at {self.location}"


class ContinuityChecker:
    """Checks for continuity errors across episodes."""
    
    def __init__(self):
        """Initialize the ContinuityChecker."""
        # Track various elements across episodes
        self.character_traits = {}  # Character name -> traits
        self.objects = {}  # Object name -> properties
        self.locations = {}  # Location name -> properties
        self.events = []  # List of events in chronological order
        self.relationships = {}  # Character pairs -> relationship status
        
    def check_episode_continuity(self, 
                               episode_script: Dict, 
                               previous_episodes: List[Dict],
                               character_profiles: Dict) -> List[ContinuityError]:
        """
        Check for continuity errors in an episode.
        
        Args:
            episode_script: Script of the current episode
            previous_episodes: Scripts of previous episodes
            character_profiles: Character profiles for reference
            
        Returns:
            List of continuity errors found
        """
        errors = []
        
        # Update knowledge base with previous episodes
        for prev_episode in previous_episodes:
            self._extract_knowledge_from_episode(prev_episode)
            
        # Check current episode against knowledge base
        errors.extend(self._check_character_continuity(episode_script, character_profiles))
        errors.extend(self._check_object_continuity(episode_script))
        errors.extend(self._check_location_continuity(episode_script))
        errors.extend(self._check_timeline_continuity(episode_script))
        
        # Update knowledge base with current episode
        self._extract_knowledge_from_episode(episode_script)
        
        return errors
    
    def _extract_knowledge_from_episode(self, episode: Dict) -> None:
        """Extract knowledge elements from an episode."""
        for scene in episode.get('scenes', []):
            # Extract setting
            setting = scene.get('setting')
            if setting and setting not in self.locations:
                self.locations[setting] = {'first_appearance': episode.get('episode_number')}
                
            # Process elements in the scene
            for element in scene.get('elements', []):
                element_type = element.get('type')
                
                if element_type == 'dialogue':
                    # Extract character from dialogue
                    character = element.get('character')
                    if character and character not in self.character_traits:
                        self.character_traits[character] = {
                            'first_appearance': episode.get('episode_number')
                        }
                        
                    # Extract content for potential object/location mentions
                    content = element.get('content', '')
                    self._extract_entities_from_text(content, episode.get('episode_number'))
                    
                elif element_type == 'action':
                    # Extract entities from action descriptions
                    content = element.get('content', '')
                    self._extract_entities_from_text(content, episode.get('episode_number'))
                    
                    # Add to events timeline
                    self.events.append({
                        'episode': episode.get('episode_number'),
                        'scene': scene.get('setting'),
                        'description': content
                    })
    
    def _extract_entities_from_text(self, text: str, episode_number: int) -> None:
        """
        Extract entities from text.
        This is a simplistic implementation - in a real system, 
        you would use NLP techniques for entity extraction.
        """
        # Simple capitalized word extraction as example
        words = text.split()
        for i, word in enumerate(words):
            if word and word[0].isupper() and len(word) > 1:
                # Check if it's a potential noun (not at start of sentence)
                is_noun = i > 0 or (word[0].isupper() and word[1:].islower())
                
                if is_noun and word not in self.objects and word not in self.character_traits:
                    # Could be an object or location
                    self.objects[word] = {
                        'first_appearance': episode_number,
                        'mentioned_in': [episode_number]
                    }
    
    def _check_character_continuity(self, 
                                 episode: Dict, 
                                 character_profiles: Dict) -> List[ContinuityError]:
        """Check for character continuity errors."""
        errors = []
        episode_number = episode.get('episode_number')
        
        # Track characters in this episode
        episode_characters = set()
        
        for scene in episode.get('scenes', []):
            for element in scene.get('elements', []):
                if element.get('type') == 'dialogue':
                    character = element.get('character')
                    episode_characters.add(character)
                    
                    # Check if character exists in profiles
                    if character not in character_profiles:
                        errors.append(ContinuityError(
                            'Unknown Character',
                            f"Character '{character}' appears but is not defined in character profiles",
                            {'episode': episode_number, 'scene': scene.get('setting')}
                        ))
                        
                    # Check for consistent dialogue style (if significant deviation)
                    if character in character_profiles and character in self.character_traits:
                        # Simple consistency check - comparing dialogue to profile
                        dialogue_style = character_profiles[character].get('dialogue_style', '')
                        dialogue_content = element.get('content', '')
                        
                        # Very simple heuristic - in reality, use NLP
                        if len(dialogue_content) > 20 and dialogue_style:
                            # Check for formal vs informal mismatches
                            is_formal = 'formal' in dialogue_style.lower()
                            has_contractions = "'" in dialogue_content
                            has_slang = any(word in dialogue_content.lower() for word in ['yeah', 'nope', 'gonna', 'wanna'])
                            
                            if is_formal and (has_contractions or has_slang):
                                errors.append(ContinuityError(
                                    'Dialogue Style Inconsistency',
                                    f"Character '{character}' uses informal language despite formal profile",
                                    {'episode': episode_number, 'scene': scene.get('setting')}
                                ))
        
        return errors
    
    def _check_object_continuity(self, episode: Dict) -> List[ContinuityError]:
        """Check for object continuity errors."""
        errors = []
        episode_number = episode.get('episode_number')
        
        # Track objects that appear/disappear
        objects_in_scenes = {}
        
        for i, scene in enumerate(episode.get('scenes', [])):
            objects_in_scenes[i] = set()
            
            # Extract objects from scene elements
            for element in scene.get('elements', []):
                content = element.get('content', '')
                
                # Simple object extraction (would use NLP in real implementation)
                for obj in self.objects:
                    if obj in content:
                        objects_in_scenes[i].add(obj)
                        
                        # Update object's episode mentions
                        if 'mentioned_in' in self.objects[obj] and episode_number not in self.objects[obj]['mentioned_in']:
                            self.objects[obj]['mentioned_in'].append(episode_number)
            
            # Check for objects that should be present but aren't
            if i > 0:
                prev_scene_objects = objects_in_scenes[i-1]
                for obj in prev_scene_objects:
                    # If object was important and not mentioned in next scene
                    # This is a very simplistic check
                    if obj not in objects_in_scenes[i] and len(self.objects[obj].get('mentioned_in', [])) > 2:
                        errors.append(ContinuityError(
                            'Object Disappearance',
                            f"Object '{obj}' was present in previous scene but disappeared",
                            {'episode': episode_number, 'scene': scene.get('setting')}
                        ))
                        
        return errors
    
    def _check_location_continuity(self, episode: Dict) -> List[ContinuityError]:
        """Check for location continuity errors."""
        errors = []
        episode_number = episode.get('episode_number')
        
        # Check for location transitions that don't make sense
        previous_location = None
        
        for i, scene in enumerate(episode.get('scenes', [])):
            current_location = scene.get('setting')
            
            if current_location and previous_location:
                # In a real implementation, check for logical transitions based on
                # world geography, travel times, etc.
                if previous_location == current_location:
                    # Check if there should be a transition scene
                    pass
                
            previous_location = current_location
            
        return errors
    
    def _check_timeline_continuity(self, episode: Dict) -> List[ContinuityError]:
        """Check for timeline continuity errors."""
        errors = []
        episode_number = episode.get('episode_number')
        
        # This would be a complex check in reality
        # You would need to extract time references, event sequences, etc.
        
        return errors
