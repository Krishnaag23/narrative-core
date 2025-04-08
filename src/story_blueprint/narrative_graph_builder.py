from typing import Dict, List, Optional, Set, Tuple, Any
import networkx as nx
import logging


from ..utils.graph_database import GraphDB 
from ..input_processing import StoryConcept

logger = logging.getLogger(__name__)

REL_INTERACTS_WITH = "INTERACTS_WITH"
REL_LOCATED_IN = "LOCATED_IN"
REL_PART_OF = "PART_OF" # e.g., Event PART_OF Episode
REL_HAS_TRAIT = "HAS_TRAIT"
REL_HAS_GOAL = "HAS_GOAL"
REL_AFFECTS = "AFFECTS" # e.g., Event AFFECTS Character
REL_MENTIONS = "MENTIONS" # e.g., Dialogue MENTIONS Object/Character
REL_LEADS_TO = "LEADS_TO" # e.g., Event LEADS_TO Event
REL_CONTAINS = "CONTAINS" # e.g., Episode CONTAINS Event

NODE_CHARACTER = "Character"
NODE_LOCATION = "Location"
NODE_EVENT = "Event"
NODE_EPISODE = "Episode"
NODE_THEME = "Theme"
NODE_PLOT_POINT = "PlotPoint" # More specific than Event maybe?
REL_PART_OF = "PART_OF"
REL_LOCATED_IN = "LOCATED_IN"
REL_INVOLVES = "INVOLVES" # PlotPoint INVOLVES Character
REL_ADVANCES = "ADVANCES" # PlotPoint ADVANCES Theme/Goal
REL_FOLLOWS = "FOLLOWS" # PlotPoint FOLLOWS PlotPoint

class NarrativeGraphBuilder:
    """Builds and updates the narrative knowledge graph based on story components."""

    def __init__(self, graph_db_instance: Optional[GraphDB] = None):
        self.db = graph_db_instance or GraphDB()
        logger.info("NarrativeGraphBuilder initialized.")

    def build_initial_graph(self, story_concept: StoryConcept):
        """Populates the graph with initial entities from the StoryConcept."""
        logger.info("Building initial narrative graph from StoryConcept...")
        self.db.clear_graph() # Start fresh for this story

        # Add Characters
        for char_input in story_concept.initial_characters:
            # Use name as ID for now, consider generating UUIDs later
            char_id = char_input.name
            properties = {"name": char_input.name, "role": char_input.role.value}
            if char_input.description: properties["description"] = char_input.description
            self.db.add_node(char_id, node_type=NODE_CHARACTER, properties=properties)
            for goal in char_input.goals:
                 goal_id = f"goal_{goal.replace(' ','_').lower()}"
                 self.db.add_node(goal_id, node_type="Goal", properties={"description": goal})
                 self.db.add_edge(char_id, goal_id, "HAS_GOAL")
            for trait in char_input.traits:
                 trait_id = f"trait_{trait.replace(' ','_').lower()}"
                 self.db.add_node(trait_id, node_type="Trait", properties={"description": trait})
                 self.db.add_edge(char_id, trait_id, "HAS_TRAIT")

        # Add Setting/Location
        setting = story_concept.initial_setting
        loc_id = setting.location.replace(' ','_').lower() # Simple ID generation
        loc_props = {"name": setting.location, "time_period": setting.time_period}
        if setting.atmosphere: loc_props["atmosphere"] = setting.atmosphere
        if setting.cultural_context_notes: loc_props["cultural_notes"] = setting.cultural_context_notes
        self.db.add_node(loc_id, node_type=NODE_LOCATION, properties=loc_props)

        # Add Themes
        for theme in story_concept.initial_plot.potential_themes:
             theme_id = f"theme_{theme.replace(' ','_').lower()}"
             self.db.add_node(theme_id, node_type=NODE_THEME, properties={"description": theme})

        logger.info("Initial graph structure built.")


    def add_plot_arc_to_graph(self, plot_arc_data: Dict[str, Any], story_concept: StoryConcept):
        """Adds plot points from the generated arc to the graph."""
        logger.info("Adding plot arc details to the narrative graph...")
        plot_stages = plot_arc_data.get("plot_arc", [])
        last_plot_point_id = None

        if not plot_stages:
            logger.warning("No plot arc stages found to add to graph.")
            return

        # Find primary location ID from concept (simple match)
        primary_loc_id = story_concept.initial_setting.location.replace(' ','_').lower()

        for stage_idx, stage in enumerate(plot_stages):
            stage_name = stage.get("stage_name", f"Stage_{stage_idx+1}")
            for point_idx, point_desc in enumerate(stage.get("plot_points", [])):
                point_id = f"pp_{stage_idx+1}_{point_idx+1}"
                self.db.add_node(point_id, node_type=NODE_PLOT_POINT, properties={"description": point_desc, "stage": stage_name})

                # Link chronologically
                if last_plot_point_id:
                    self.db.add_edge(last_plot_point_id, point_id, REL_FOLLOWS)
                last_plot_point_id = point_id

                # Link to involved characters (simple parsing, needs improvement)
                for char_input in story_concept.initial_characters:
                     if char_input.name.lower() in point_desc.lower():
                         self.db.add_edge(point_id, char_input.name, REL_INVOLVES)

                # Link to themes mentioned (simple parsing)
                for theme in story_concept.initial_plot.potential_themes:
                     if theme.lower() in point_desc.lower():
                         theme_id = f"theme_{theme.replace(' ','_').lower()}"
                         self.db.add_edge(point_id, theme_id, REL_ADVANCES)

                # Link to location (assume primary location for now)
                # TODO: Parse setting_notes from arc if available
                self.db.add_edge(point_id, primary_loc_id, REL_LOCATED_IN)

        logger.info(f"Added {sum(len(s.get('plot_points',[])) for s in plot_stages)} plot points to graph.")


    def add_episode_structure_to_graph(self, episode_outlines: List[Dict[str, Any]]):
        """Adds episode nodes and links plot points to them."""
        logger.info("Adding episode structure to the narrative graph...")
        if not episode_outlines:
            return

        for ep_outline in episode_outlines:
            ep_num = ep_outline.get("episode_number")
            ep_id = f"ep_{ep_num}"
            self.db.add_node(ep_id, node_type=NODE_EPISODE, properties={"number": ep_num, "title": ep_outline.get("title")})

            # Find corresponding plot points added previously and link them
            # This relies on plot point descriptions matching, might need better ID mapping
            for point_desc in ep_outline.get("plot_points", []):
                 # Find node with matching description (inefficient with NetworkX)
                 found_nodes = self.db.find_nodes({"description": point_desc, "type": NODE_PLOT_POINT})
                 if found_nodes:
                      point_id = found_nodes[0][0] # Get the ID of the first match
                      self.db.add_edge(ep_id, point_id, REL_CONTAINS) # Episode contains PlotPoint
                      self.db.add_edge(point_id, ep_id, REL_PART_OF) # PlotPoint part of Episode
                 else:
                      logger.warning(f"Could not find graph node for plot point: '{point_desc[:50]}...' to link to episode {ep_num}")

        logger.info(f"Added {len(episode_outlines)} episodes and linked plot points to graph.")


    def get_graph(self) -> Any:
         """Returns the underlying graph object (NetworkX graph in this case)."""
         return self.db.graph