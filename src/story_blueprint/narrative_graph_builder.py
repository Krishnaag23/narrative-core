from typing import Dict, List, Optional, Set, Tuple
import networkx as nx

class NarrativeGraphBuilder:
    """Builds a graph representation of narrative elements and their relationships."""
    
    def __init__(self):
        """Initialize the NarrativeGraphBuilder."""
        self.graph = nx.MultiDiGraph()
        
    def build_from_plot_arc(self, plot_arc: Dict) -> nx.MultiDiGraph:
        """
        Build a narrative graph from a plot arc.
        
        Args:
            plot_arc: Complete plot arc with stages, characters, etc.
            
        Returns:
            NetworkX graph representing the narrative
        """
        # Extract entities from the plot arc
        characters = self._extract_characters(plot_arc)
        locations = self._extract_locations(plot_arc)
        events = self._extract_events(plot_arc)
        
        # Add nodes to the graph
        self._add_character_nodes(characters)
        self._add_location_nodes(locations)
        self._add_event_nodes(events)
        
        # Connect events in sequence
        self._connect_sequential_events(events)
        
        # Connect characters to events they participate in
        self._connect_characters_to_events(characters, events)
        
        # Connect events to locations where they occur
        self._connect_events_to_locations(events, locations)
        
        return self.graph
    
    def add_relationship(self, 
                        source: str, 
                        target: str, 
                        relationship_type: str,
                        properties: Optional[Dict] = None) -> None:
        """
        Add a relationship to the narrative graph.
        
        Args:
            source: Source node ID
            target: Target node ID
            relationship_type: Type of relationship
            properties: Additional properties for the relationship
        """
        # Add nodes if they don't exist
        if source not in self.graph:
            self.graph.add_node(source)
        if target not in self.graph:
            self.graph.add_node(target)
        
        # Add the edge with properties
        if properties is None:
            properties = {}
            
        self.graph.add_edge(source, target, type=relationship_type, **properties)
    
    def get_character_arcs(self) -> Dict[str, List[str]]:
        """
        Extract character arcs from the narrative graph.
        
        Returns:
            Dictionary mapping characters to their story arcs
        """
        character_arcs = {}
        
        # Find character nodes
        character_nodes = [n for n, d in self.graph.nodes(data=True) if d.get('type') == 'character']
        
        for character in character_nodes:
            # Get events connected to this character
            events = []
            for _, event, data in self.graph.out_edges(character, data=True):
                if data.get('type') == 'participates_in':
                    # Get event data
                    event_data = self.graph.nodes[event]
                    events.append((event_data.get('sequence', 0), event, event_data.get('description', '')))
            
            # Sort events by sequence
            events.sort()
            
            # Extract arc
            character_arcs[character] = [desc for _, _, desc in events]
            
        return character_arcs
    
    def visualize(self, output_file: Optional[str] = None):
        """
        Visualize the narrative graph.
        
        Args:
            output_file: Path to save the visualization (optional)
        """
        try:
            import matplotlib.pyplot as plt
            
            # Create a layout
            pos = nx.spring_layout(self.graph)
            
            # Draw nodes with different colors based on type
            character_nodes = [n for n, d in self.graph.nodes(data=True) if d.get('type') == 'character']
            location_nodes = [n for n, d in self.graph.nodes(data=True) if d.get('type') == 'location']
            event_nodes = [n for n, d in self.graph.nodes(data=True) if d.get('type') == 'event']
            
            plt.figure(figsize=(12, 8))
            
            nx.draw_networkx_nodes(self.graph, pos, nodelist=character_nodes, node_color='blue', node_size=500, alpha=0.8)
            nx.draw_networkx_nodes(self.graph, pos, nodelist=location_nodes, node_color='green', node_size=500, alpha=0.8)
            nx.draw_networkx_nodes(self.graph, pos, nodelist=event_nodes, node_color='red', node_size=500, alpha=0.8)
            
            # Draw edges
            nx.draw_networkx_edges(self.graph, pos, width=1.0, alpha=0.5)
            
            # Draw labels
            nx.draw_networkx_labels(self.graph, pos, font_size=10)
            
            plt.title("Narrative Graph")
            plt.axis('off')
            
            if output_file:
                plt.savefig(output_file)
            else:
                plt.show()
                
        except ImportError:
            print("Matplotlib is required for visualization")
    
    def _extract_characters(self, plot_arc: Dict) -> Set[str]:
        """Extract character names from the plot arc."""
        characters = set()
        
        # Extract from character_development in stages
        for stage in plot_arc.get('stages', []):
            for development in stage.get('character_development', []):
                # Simple extraction - assume character name is at the beginning of development
                parts = development.split()
                if parts:
                    characters.add(parts[0])
        
        # If no characters found, add a placeholder
        if not characters:
            characters.add("Protagonist")
            
        return characters
    
    def _extract_locations(self, plot_arc: Dict) -> Set[str]:
        """Extract location names from the plot arc."""
        locations = set()
        
        # Extract from settings in stages
        for stage in plot_arc.get('stages', []):
            for setting in stage.get('settings', []):
                locations.add(setting)
        
        # If no locations found, add a placeholder
        if not locations:
            locations.add("Main Setting")
            
        return locations
    
    def _extract_events(self, plot_arc: Dict) -> List[Dict]:
        """Extract events from the plot arc."""
        events = []
        
        # Extract from plot points in stages
        sequence = 0
        for stage in plot_arc.get('stages', []):
            for plot_point in stage.get('plot_points', []):
                sequence += 1
                events.append({
                    'id': f"event_{sequence}",
                    'description': plot_point,
                    'stage': stage['name'],
                    'sequence': sequence
                })
        
        return events
    
    def _add_character_nodes(self, characters: Set[str]) -> None:
        """Add character nodes to the graph."""
        for character in characters:
            self.graph.add_node(character, type='character')
    
    def _add_location_nodes(self, locations: Set[str]) -> None:
        """Add location nodes to the graph."""
        for location in locations:
            self.graph.add_node(location, type='location')
    
    def _add_event_nodes(self, events: List[Dict]) -> None:
        """Add event nodes to the graph."""
        for event in events:
            self.graph.add_node(
                event['id'], 
                type='event', 
                description=event['description'],
                stage=event['stage'],
                sequence=event['sequence']
            )
    
    def _connect_sequential_events(self, events: List[Dict]) -> None:
        """Connect events in sequence."""
        for i in range(len(events) - 1):
            self.graph.add_edge(
                events[i]['id'],
                events[i+1]['id'],
                type='follows',
                weight=1
            )
    
    def _connect_characters_to_events(self, characters: Set[str], events: List[Dict]) -> None:
        """Connect characters to events they participate in (simple implementation)."""
        for character in characters:
            # For now, simple heuristic: connect character to every third event
            for i, event in enumerate(events):
                if i % 3 == 0:  # Arbitrary pattern for demo
                    self.graph.add_edge(
                        character,
                        event['id'],
                        type='participates_in'
                    )
    
    def _connect_events_to_locations(self, events: List[Dict], locations: Set[str]) -> None:
        """Connect events to locations (simple implementation)."""
        location_list = list(locations)
        for i, event in enumerate(events):
            # Simple assignment: cycle through locations
            location = location_list[i % len(location_list)]
            self.graph.add_edge(
                event['id'],
                location,
                type='occurs_at'
            )


########################################################
# import logging
# from typing import Dict, List, Optional, Any

# from ..utils.graph_database import GraphDB # Use the alias/implementation
# from ..input_processing import StoryConcept

# logger = logging.getLogger(__name__)

# # Re-using constants from knowledge_graph.py for consistency
# NODE_CHARACTER = "Character"
# NODE_LOCATION = "Location"
# NODE_EVENT = "Event"
# NODE_EPISODE = "Episode"
# NODE_THEME = "Theme"
# NODE_PLOT_POINT = "PlotPoint" # More specific than Event maybe?
# REL_PART_OF = "PART_OF"
# REL_LOCATED_IN = "LOCATED_IN"
# REL_INVOLVES = "INVOLVES" # PlotPoint INVOLVES Character
# REL_ADVANCES = "ADVANCES" # PlotPoint ADVANCES Theme/Goal
# REL_FOLLOWS = "FOLLOWS" # PlotPoint FOLLOWS PlotPoint

# class NarrativeGraphBuilder:
#     """Builds and updates the narrative knowledge graph based on story components."""

#     def __init__(self, graph_db_instance: Optional[GraphDB] = None):
#         self.db = graph_db_instance or GraphDB()
#         logger.info("NarrativeGraphBuilder initialized.")

#     def build_initial_graph(self, story_concept: StoryConcept):
#         """Populates the graph with initial entities from the StoryConcept."""
#         logger.info("Building initial narrative graph from StoryConcept...")
#         self.db.clear_graph() # Start fresh for this story

#         # Add Characters
#         for char_input in story_concept.initial_characters:
#             # Use name as ID for now, consider generating UUIDs later
#             char_id = char_input.name
#             properties = {"name": char_input.name, "role": char_input.role.value}
#             if char_input.description: properties["description"] = char_input.description
#             self.db.add_node(char_id, node_type=NODE_CHARACTER, properties=properties)
#             for goal in char_input.goals:
#                  goal_id = f"goal_{goal.replace(' ','_').lower()}"
#                  self.db.add_node(goal_id, node_type="Goal", properties={"description": goal})
#                  self.db.add_edge(char_id, goal_id, "HAS_GOAL")
#             for trait in char_input.traits:
#                  trait_id = f"trait_{trait.replace(' ','_').lower()}"
#                  self.db.add_node(trait_id, node_type="Trait", properties={"description": trait})
#                  self.db.add_edge(char_id, trait_id, "HAS_TRAIT")

#         # Add Setting/Location
#         setting = story_concept.initial_setting
#         loc_id = setting.location.replace(' ','_').lower() # Simple ID generation
#         loc_props = {"name": setting.location, "time_period": setting.time_period}
#         if setting.atmosphere: loc_props["atmosphere"] = setting.atmosphere
#         if setting.cultural_context_notes: loc_props["cultural_notes"] = setting.cultural_context_notes
#         self.db.add_node(loc_id, node_type=NODE_LOCATION, properties=loc_props)

#         # Add Themes
#         for theme in story_concept.initial_plot.potential_themes:
#              theme_id = f"theme_{theme.replace(' ','_').lower()}"
#              self.db.add_node(theme_id, node_type=NODE_THEME, properties={"description": theme})

#         logger.info("Initial graph structure built.")


#     def add_plot_arc_to_graph(self, plot_arc_data: Dict[str, Any], story_concept: StoryConcept):
#         """Adds plot points from the generated arc to the graph."""
#         logger.info("Adding plot arc details to the narrative graph...")
#         plot_stages = plot_arc_data.get("plot_arc", [])
#         last_plot_point_id = None

#         if not plot_stages:
#             logger.warning("No plot arc stages found to add to graph.")
#             return

#         # Find primary location ID from concept (simple match)
#         primary_loc_id = story_concept.initial_setting.location.replace(' ','_').lower()

#         for stage_idx, stage in enumerate(plot_stages):
#             stage_name = stage.get("stage_name", f"Stage_{stage_idx+1}")
#             for point_idx, point_desc in enumerate(stage.get("plot_points", [])):
#                 point_id = f"pp_{stage_idx+1}_{point_idx+1}"
#                 self.db.add_node(point_id, node_type=NODE_PLOT_POINT, properties={"description": point_desc, "stage": stage_name})

#                 # Link chronologically
#                 if last_plot_point_id:
#                     self.db.add_edge(last_plot_point_id, point_id, REL_FOLLOWS)
#                 last_plot_point_id = point_id

#                 # Link to involved characters (simple parsing, needs improvement)
#                 for char_input in story_concept.initial_characters:
#                      if char_input.name.lower() in point_desc.lower():
#                          self.db.add_edge(point_id, char_input.name, REL_INVOLVES)

#                 # Link to themes mentioned (simple parsing)
#                 for theme in story_concept.initial_plot.potential_themes:
#                      if theme.lower() in point_desc.lower():
#                          theme_id = f"theme_{theme.replace(' ','_').lower()}"
#                          self.db.add_edge(point_id, theme_id, REL_ADVANCES)

#                 # Link to location (assume primary location for now)
#                 # TODO: Parse setting_notes from arc if available
#                 self.db.add_edge(point_id, primary_loc_id, REL_LOCATED_IN)

#         logger.info(f"Added {sum(len(s.get('plot_points',[])) for s in plot_stages)} plot points to graph.")


#     def add_episode_structure_to_graph(self, episode_outlines: List[Dict[str, Any]]):
#         """Adds episode nodes and links plot points to them."""
#         logger.info("Adding episode structure to the narrative graph...")
#         if not episode_outlines:
#             return

#         for ep_outline in episode_outlines:
#             ep_num = ep_outline.get("episode_number")
#             ep_id = f"ep_{ep_num}"
#             self.db.add_node(ep_id, node_type=NODE_EPISODE, properties={"number": ep_num, "title": ep_outline.get("title")})

#             # Find corresponding plot points added previously and link them
#             # This relies on plot point descriptions matching, might need better ID mapping
#             for point_desc in ep_outline.get("plot_points", []):
#                  # Find node with matching description (inefficient with NetworkX)
#                  found_nodes = self.db.find_nodes({"description": point_desc, "type": NODE_PLOT_POINT})
#                  if found_nodes:
#                       point_id = found_nodes[0][0] # Get the ID of the first match
#                       self.db.add_edge(ep_id, point_id, REL_CONTAINS) # Episode contains PlotPoint
#                       self.db.add_edge(point_id, ep_id, REL_PART_OF) # PlotPoint part of Episode
#                  else:
#                       logger.warning(f"Could not find graph node for plot point: '{point_desc[:50]}...' to link to episode {ep_num}")

#         logger.info(f"Added {len(episode_outlines)} episodes and linked plot points to graph.")


#     def get_graph(self) -> Any:
#          """Returns the underlying graph object (NetworkX graph in this case)."""
#          if isinstance(self.db, NetworkXGraphDB):
#              return self.db.graph
#          else:
#              logger.warning("get_graph() currently only returns NetworkX graph instances.")
#              return None # Or raise error