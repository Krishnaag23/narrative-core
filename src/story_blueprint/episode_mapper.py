#TODO : Map prompts to use the config directory prompt and further optimise that.
from typing import Dict, List, Optional, Tuple
import logging 
import json

from ..utils import LLMwrapper, PromptManager

logger = logging.getLogger(__name__)

class EpisodeMapper:
    """Maps a plot arc into logical episodes."""
    
    def __init__(self, llm_wrapper: LLMwrapper):
        """
        Initialize the EpisodeMapper.
        
        Args:
            llm_wrapper: Interface for LLM interactions (optional)
        """
        self.llm_wrapper = llm_wrapper
    
    def map_to_episodes(self, 
                        plot_arc: Dict, 
                        episode_count: Optional[int] = None,
                        min_episodes: int = 5,
                        max_episodes: int = 12,
                        cliffhanger_frequency: float = 0.7) -> List[Dict]:
        """
        Map a plot arc to a series of episodes.
        
        Args:
            plot_arc: Complete plot arc to be divided
            episode_count: Number of episodes (optional, will be calculated if None)
            min_episodes: Minimum number of episodes
            max_episodes: Maximum number of episodes
            cliffhanger_frequency: Probability of ending episodes with cliffhangers
            
        Returns:
            List of episode outlines
        """
        # Determine optimal episode count if not provided
        if episode_count is None:
            episode_count = self._calculate_optimal_episode_count(
                plot_arc, min_episodes, max_episodes
            )
            
        # Get plot points from the arc
        plot_points = self._extract_plot_points(plot_arc)
        
        # Distribute plot points across episodes
        episode_plot_points = self._distribute_plot_points(plot_points, episode_count)
        
        # Build episode outlines
        episodes = []
        for i, points in enumerate(episode_plot_points):
            is_finale = (i == len(episode_plot_points) - 1)
            should_have_cliffhanger = not is_finale and (
                cliffhanger_frequency > 0.5 or i % 2 == 0  # Simple pattern for cliffhangers
            )
            
            episode = self._create_episode_outline(
                i + 1, points, plot_arc, should_have_cliffhanger
            )
            episodes.append(episode)
            
        return episodes
    
    def _calculate_optimal_episode_count(self, plot_arc: Dict, min_episodes: int, max_episodes: int) -> int:
        """Calculate the optimal number of episodes based on plot complexity."""
        # Simple heuristic based on number of plot points
        plot_points = self._extract_plot_points(plot_arc)
        
        # Estimate one plot point per 1-3 minutes of screen time
        # Assume 20-30 minutes per episode
        ideal_points_per_episode = 10
        
        episode_count = max(min_episodes, min(max_episodes, len(plot_points) // ideal_points_per_episode))
        return episode_count
    
    def _extract_plot_points(self, plot_arc: Dict) -> List[Dict]:
        """Extract all plot points from the plot arc."""
        plot_points = []
        
        # Iterate through stages and collect plot points
        for stage in plot_arc.get('stages', []):
            for point in stage.get('plot_points', []):
                plot_points.append({
                    'point': point,
                    'stage': stage['name'],
                    'character_development': stage.get('character_development', []),
                    'settings': stage.get('settings', [])
                })
                
        return plot_points
    
    def _distribute_plot_points(self, plot_points: List[Dict], episode_count: int) -> List[List[Dict]]:
        """Distribute plot points across episodes."""
        episode_plot_points = [[] for _ in range(episode_count)]
        
        # Simple distribution - divide points evenly
        points_per_episode = len(plot_points) // episode_count
        remainder = len(plot_points) % episode_count
        
        point_index = 0
        for episode_index in range(episode_count):
            points_for_this_episode = points_per_episode
            if episode_index < remainder:
                points_for_this_episode += 1
                
            for _ in range(points_for_this_episode):
                if point_index < len(plot_points):
                    episode_plot_points[episode_index].append(plot_points[point_index])
                    point_index += 1
                    
        return episode_plot_points
    
    def _create_episode_outline(self, 
                              episode_number: int, 
                              plot_points: List[Dict], 
                              plot_arc: Dict,
                              should_have_cliffhanger: bool) -> Dict:
        """Create an outline for a single episode."""
        if self.llm_wrapper:
            # Use LLM to create detailed episode outline
            return self._generate_episode_with_llm(
                episode_number, plot_points, plot_arc, should_have_cliffhanger
            )
        else:
            # Create a simple episode outline without LLM
            return self._create_default_episode_outline(
                episode_number, plot_points, should_have_cliffhanger
            )
    
    def _generate_episode_with_llm(self, 
                                episode_number: int, 
                                plot_points: List[Dict],
                                plot_arc: Dict,
                                should_have_cliffhanger: bool) -> Dict:
        """Generate an episode outline using LLM."""
        # Create a prompt
        prompt = self._create_episode_generation_prompt(
            episode_number, plot_points, plot_arc, should_have_cliffhanger
        )
        
        # Generate episode with LLM
        response = self.llm_wrapper.generate(prompt)
        
        # Parse the response (assuming JSON format)
        try:
            episode = json.loads(response)
        except:
            # Fallback to default if parsing fails
            episode = self._create_default_episode_outline(
                episode_number, plot_points, should_have_cliffhanger
            )
            
        return episode
    
    def _create_episode_generation_prompt(self, 
                                       episode_number: int, 
                                       plot_points: List[Dict],
                                       plot_arc: Dict,
                                       should_have_cliffhanger: bool) -> str:
        """Create a prompt for LLM to generate an episode outline."""
        points_text = "\n".join([f"- {p['point']}" for p in plot_points])
        
        prompt = f"""
        Create an outline for Episode {episode_number} of a series titled "{plot_arc.get('title', 'Untitled')}".
        
        This episode should cover the following plot points:
        {points_text}
        
        The episode should {"end with a cliffhanger" if should_have_cliffhanger else "have a satisfying conclusion"}.
        
        Return a JSON object with:
        1. "title": A compelling title for this episode
        2. "summary": A brief summary of the episode
        3. "scenes": An array of scenes, each with:
           - "setting": Where the scene takes place
           - "characters": Characters in the scene
           - "action": What happens in the scene
           - "dialogue_focus": Key conversation topics or revelations
        4. "cliffhanger": Description of the cliffhanger (if applicable)
        
        Format the response as valid JSON.
        """
        
        return prompt
    
    def _create_default_episode_outline(self, 
                                     episode_number: int, 
                                     plot_points: List[Dict],
                                     should_have_cliffhanger: bool) -> Dict:
        """Create a default episode outline without using LLM."""
        # Extract settings and character development from plot points
        settings = []
        character_developments = []
        
        for point in plot_points:
            if 'settings' in point and point['settings']:
                settings.extend(point['settings'])
            if 'character_development' in point and point['character_development']:
                character_developments.extend(point['character_development'])
                
        # Remove duplicates
        settings = list(set(settings))
        character_developments = list(set(character_developments))
        
        # Create scenes (roughly 3-5 per episode)
        scene_count = min(len(plot_points) + 1, 5)
        scenes = []
        
        for i in range(scene_count):
            scene_setting = settings[i % len(settings)] if settings else f"Setting {i+1}"
            scene = {
                "setting": scene_setting,
                "characters": ["Character 1", "Character 2"],
                "action": f"Action for scene {i+1}" if i < len(plot_points) else "Concluding action",
                "dialogue_focus": "Key conversation topic"
            }
            scenes.append(scene)
            
        # Create the episode outline
        episode = {
            "episode_number": episode_number,
            "title": f"Episode {episode_number}",
            "summary": "Summary of the episode",
            "scenes": scenes
        }
        
        if should_have_cliffhanger:
            episode["cliffhanger"] = "Description of the cliffhanger"
            
        return episode