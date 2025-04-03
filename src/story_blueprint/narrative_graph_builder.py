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