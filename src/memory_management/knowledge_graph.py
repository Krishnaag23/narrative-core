"""
Manages the storage and retrieval of structured narrative information
(entities, relationships) in a graph format. Uses the GraphDB interface from utils.
"""

import logging
from typing import Dict, List, Optional, Any

from ..utils.graph_database import GraphDB, NetworkXGraphDB 

logger = logging.getLogger(__name__)

# Define standard node types and relationship types
NODE_CHARACTER = "Character"
NODE_LOCATION = "Location"
NODE_EVENT = "Event"
NODE_EPISODE = "Episode"
NODE_THEME = "Theme"
NODE_OBJECT = "Object" # Added node type

REL_INTERACTS_WITH = "INTERACTS_WITH"
REL_LOCATED_IN = "LOCATED_IN"
REL_PART_OF = "PART_OF" # e.g., Event PART_OF Episode
REL_HAS_TRAIT = "HAS_TRAIT"
REL_HAS_GOAL = "HAS_GOAL"
REL_AFFECTS = "AFFECTS" # e.g., Event AFFECTS Character
REL_MENTIONS = "MENTIONS" # e.g., Dialogue MENTIONS Object/Character
REL_LEADS_TO = "LEADS_TO" # e.g., Event LEADS_TO Event
REL_CONTAINS = "CONTAINS" # e.g., Episode CONTAINS Event

class KnowledgeGraphManager:
    """Manages interactions with the narrative knowledge graph."""

    def __init__(self, graph_db_instance: Optional[GraphDB] = None):
        # Use provided instance or get the singleton
        self.db = graph_db_instance or GraphDB()
        logger.info("KnowledgeGraphManager initialized.")
        if isinstance(self.db, NetworkXGraphDB):
             logger.warning("KnowledgeGraphManager is using the NetworkX prototype GraphDB.")

    def add_character(self, character_id: str, name: str, role: str, traits: List[str] = None, goals: List[str] = None):
        """Adds or updates a character node and its core properties."""
        properties = {"name": name, "role": role}
        self.db.add_node(character_id, node_type=NODE_CHARACTER, properties=properties)
        if traits:
            for trait in traits:
                # Add trait as node? Or edge property? Edge for simplicity now.
                self.db.add_edge(character_id, f"trait_{trait.lower()}", REL_HAS_TRAIT, {"value": trait})
        if goals:
             for goal in goals:
                 self.db.add_edge(character_id, f"goal_{goal.lower()}", REL_HAS_GOAL, {"value": goal})

    def add_location(self, location_id: str, name: str, description: Optional[str] = None):
        """Adds a location node."""
        properties = {"name": name}
        if description: properties["description"] = description
        self.db.add_node(location_id, node_type=NODE_LOCATION, properties=properties)

    def add_episode(self, episode_id: str, number: int, title: Optional[str] = None):
        """Adds an episode node."""
        properties = {"number": number}
        if title: properties["title"] = title
        self.db.add_node(episode_id, node_type=NODE_EPISODE, properties=properties)

    def add_event(self, event_id: str, description: str, episode_id: str, characters_involved: List[str] = None, location_id: Optional[str] = None):
        """Adds an event node and links it to episode, characters, and location."""
        properties = {"description": description}
        self.db.add_node(event_id, node_type=NODE_EVENT, properties=properties)

        # Link to episode
        self.db.add_edge(episode_id, event_id, REL_CONTAINS)

        # Link to characters
        if characters_involved:
            for char_id in characters_involved:
                self.db.add_edge(event_id, char_id, REL_AFFECTS) # Event affects character
                self.db.add_edge(char_id, event_id, REL_PART_OF) # Character part of event

        # Link to location
        if location_id:
            self.db.add_edge(event_id, location_id, REL_LOCATED_IN)

    def add_relationship(self, source_id: str, target_id: str, rel_type: str, properties: Optional[Dict[str, Any]] = None):
         """Adds a generic relationship between two existing nodes."""
         self.db.add_edge(source_id, target_id, rel_type, properties)

    def get_character_info(self, character_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves character node and basic relationships."""
        info = self.db.get_node(character_id)
        if info and info.get("type") == NODE_CHARACTER:
            # Fetch related info like goals, traits, recent events
            info['goals'] = [edge_data['edge_data'].get('value') for _, edge_data in self.db.get_neighbors(character_id, REL_HAS_GOAL) if edge_data.get('edge_data')]
            info['traits'] = [edge_data['edge_data'].get('value') for _, edge_data in self.db.get_neighbors(character_id, REL_HAS_TRAIT) if edge_data.get('edge_data')]
            # Get events character participated in
            info['events'] = [node_id for node_id, data in self.db.get_neighbors(character_id, REL_PART_OF) if data.get('node_data', {}).get('type') == NODE_EVENT]
            return info
        return None

    def get_context_around_character(self, character_id: str, depth: int = 1) -> Dict:
         """Retrieves a subgraph centered around a character (simplified)."""
         # This would be more complex with a real graph query language (Cypher)
         # NetworkX version: Get direct neighbors
         context = {}
         char_info = self.get_character_info(character_id)
         if not char_info: return {}
         context[character_id] = char_info

         direct_neighbors = self.db.get_neighbors(character_id) # Get all outgoing relationships
         for neighbor_id, data in direct_neighbors:
              neighbor_node_data = data.get('node_data', {})
              if neighbor_id not in context: # Avoid redundancy
                  context[neighbor_id] = neighbor_node_data
              # Add relationship info
              rel_type = data.get('edge_data', {}).get('type', 'UNKNOWN')
              if 'relationships' not in context[character_id]: context[character_id]['relationships'] = []
              context[character_id]['relationships'].append(f"-[:{rel_type}]->({neighbor_id})")

         # TODO: Implement deeper traversal if depth > 1

         return context

    def get_recent_events(self, limit: int = 5) -> List[Dict]:
        """Retrieves the most recent events based on node properties (requires timestamp property)."""
        # This is hard to do efficiently in NetworkX without iterating.
        # Real graph DBs are better suited. Placeholder logic:
        logger.warning("get_recent_events is inefficient with NetworkX; uses basic filtering.")
        all_events = self.db.find_nodes({"type": NODE_EVENT})
        # Assuming event_id might contain timestamp info or needs linking to Episode node with timestamp
        # Returning last 'limit' found events as a simple proxy for now.
        return [data for _, data in all_events[-limit:]]

    def clear_all(self):
        """Clears the entire knowledge graph."""
        self.db.clear_graph()
        logger.info("Knowledge graph cleared.")