"""
Manages the dynamic relationships between characters in the story.
Stores relationship status and updates based on interactions.
"""

import logging
from typing import Dict, Tuple, Optional, List, Any
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)

#TODO : Expand Relationship Types
RELATIONSHIP_TYPES = [
    "Neutral", "Friend", "Close Friend", "Ally", "Family",
    "Rival", "Enemy", "Distrust", "Fear",
    "Romantic Interest", "Lover", "Ex-Lover",
    "Mentor", "Mentee", "Subordinate", "Superior",
    "Complicated" # Catch-all
]
#TODO : Create a Relationship data class and use that for more structured (refactor)

class RelationshipManager:
    def __init__(self):
        """Initializes the relationship store."""
        # Store relationships as { (char_id1, char_id2) : {"status": "Friend", "intensity": 0.7, "last_interaction_summary": "..."} }
        # Ensure consistent key order (e.g., always store alphabetically sorted IDs)
        self.relationships: Dict[Tuple[str, str], Dict[str, Any]] = defaultdict(lambda: {"status": "Neutral", "intensity": 0.1, "log": []})
        logger.info("RelationshipManager initialized.")

    def _get_key(self, char_id1: str, char_id2: str) -> Tuple[str, str]:
        """Ensures consistent key order for relationship dictionary."""
        return tuple(sorted((char_id1, char_id2)))

    def get_relationship(self, char_id1: str, char_id2: str) -> Dict[str, Any]:
        """Gets the current relationship details between two characters."""
        if char_id1 == char_id2:
             return {"status": "Self", "intensity": 1.0, "log": []} # Relationship with self
        key = self._get_key(char_id1, char_id2)
        # Return a copy to prevent accidental modification
        return self.relationships[key].copy()

    def update_relationship(self, char_id1: str, char_id2: str, interaction_summary: str, new_status: Optional[str] = None, intensity_change: Optional[float] = None):
        """
        Updates the relationship based on an interaction.

        Args:
            char_id1: ID of the first character.
            char_id2: ID of the second character.
            interaction_summary: Brief summary of the interaction.
            new_status: Optional new relationship status (e.g., "Friend", "Enemy").
            intensity_change: Optional change in relationship intensity (-1.0 to 1.0).
        """
        if char_id1 == char_id2:
            return # No updates for self-relationship

        key = self._get_key(char_id1, char_id2)
        current_relationship = self.relationships[key] # Get mutable dict via defaultdict
        

        log_entry = f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {interaction_summary}"

        if new_status and new_status in RELATIONSHIP_TYPES:
            if current_relationship["status"] != new_status:
                log_entry += f" | Status changed from {current_relationship['status']} to {new_status}"
                current_relationship["status"] = new_status
                #TODO : Implement a system to change relationship intensity when status changes drastically
        else:
            log_entry += f" | Status remains {current_relationship['status']}"


        if intensity_change is not None:
            old_intensity = current_relationship["intensity"]
            current_relationship["intensity"] = max(0.0, min(1.0, old_intensity + intensity_change))
            log_entry += f" | Intensity changed from {old_intensity:.2f} to {current_relationship['intensity']:.2f}"

        current_relationship["log"].append(log_entry)
        # Limit log size?
        max_log_entries = 10
        if len(current_relationship["log"]) > max_log_entries:
            current_relationship["log"] = current_relationship["log"][-max_log_entries:]

        logger.info(f"Updated relationship between {char_id1} and {char_id2}: {log_entry}")
        # Note: This directly modifies the defaultdict entry
        # self.relationships[key] = current_relationship # Not strictly needed due to defaultdict reference


    def get_relationship_summary_for_prompt(self, char_id1: str, char_id2: str) -> str:
        """Generates a concise summary string for LLM prompts."""
        rel = self.get_relationship(char_id1, char_id2)
        return f"Relationship Status: {rel['status']} (Intensity: {rel['intensity']:.2f})"


    def get_all_relationships(self) -> Dict[Tuple[str, str], Dict[str, Any]]:
         """Returns all tracked relationships."""
         # Return a deep copy to prevent modification of internal state
         return {k: v.copy() for k, v in self.relationships.items()}