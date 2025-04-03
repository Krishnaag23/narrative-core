"""
Interface for interacting with a graph database.
Placeholder using networkx for the prototype.
#TODO : Replace with Neo4j or other tools for actual production.
"""

import logging
import networkx as nx
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)

# --- NetworkX Implementation (Prototype) ---

class NetworkXGraphDB:
    _instance = None
    graph: nx.MultiDiGraph = nx.MultiDiGraph() # Class level graph for singleton

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(NetworkXGraphDB, cls).__new__(cls)
            logger.info("Initialized NetworkXGraphDB singleton.")
        return cls._instance

    def add_node(self, node_id: str, node_type: Optional[str] = None, properties: Optional[Dict[str, Any]] = None):
        """Adds a node to the graph."""
        if not properties: properties = {}
        if node_type: properties['type'] = node_type
        self.graph.add_node(node_id, **properties)
        logger.debug(f"Added/Updated node: {node_id} with properties: {properties}")

    def add_edge(self, source_id: str, target_id: str, relationship_type: str, properties: Optional[Dict[str, Any]] = None):
        """Adds a directed edge (relationship) between two nodes."""
        if not self.graph.has_node(source_id): self.add_node(source_id)
        if not self.graph.has_node(target_id): self.add_node(target_id)

        if not properties: properties = {}
        properties['type'] = relationship_type # Add type to edge properties

        self.graph.add_edge(source_id, target_id, key=relationship_type, **properties) # Use key for relationship type
        logger.debug(f"Added edge: ({source_id})-[:{relationship_type}]->({target_id}) with props: {properties}")

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves node properties."""
        if self.graph.has_node(node_id):
            return self.graph.nodes[node_id]
        return None

    def get_neighbors(self, node_id: str, edge_type: Optional[str] = None) -> List[Tuple[str, Dict[str, Any]]]:
        """Gets neighbors (nodes connected by outgoing edges) with optional relationship type filtering."""
        neighbors = []
        if self.graph.has_node(node_id):
            for u, v, key, data in self.graph.out_edges(node_id, keys=True, data=True):
                if edge_type is None or key == edge_type:
                     # Include node data along with neighbor ID
                     neighbor_data = self.graph.nodes[v]
                     edge_data = data # Data associated with the edge itself
                     neighbors.append((v, {"node_data": neighbor_data, "edge_data": edge_data}))
        return neighbors

    def find_nodes(self, properties: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """Finds nodes matching specific properties."""
        matching_nodes = []
        for node_id, node_data in self.graph.nodes(data=True):
            match = True
            for key, value in properties.items():
                if node_data.get(key) != value:
                    match = False
                    break
            if match:
                matching_nodes.append((node_id, node_data))
        return matching_nodes

    def clear_graph(self):
        """Clears the entire graph."""
        self.graph.clear()
        logger.info("NetworkX graph cleared.")

# --- Interface Definition (for potential future refactoring) ---

class GraphDatabaseInterface:
    """Abstract base class for graph database interactions."""
    def add_node(self, node_id: str, node_type: Optional[str] = None, properties: Optional[Dict[str, Any]] = None):
        raise NotImplementedError

    def add_edge(self, source_id: str, target_id: str, relationship_type: str, properties: Optional[Dict[str, Any]] = None):
        raise NotImplementedError

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def get_neighbors(self, node_id: str, edge_type: Optional[str] = None) -> List[Tuple[str, Dict[str, Any]]]:
         raise NotImplementedError

    def find_nodes(self, properties: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
         raise NotImplementedError

    def clear_graph(self):
         raise NotImplementedError

# Use the NetworkX implementation for now
GraphDB = NetworkXGraphDB