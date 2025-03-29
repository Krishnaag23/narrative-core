"""
Character System Module for NarrativeCore.

Handles creation, management, memory, relationships, and dialogue generation
for consistent and evolving characters.
"""
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# --- Import key classes for easier access ---
from .character_profile import CharacterProfile, CharacterInput, CharacterState
from .vector_store_manager import VectorStoreManager
from .character_embedding import CharacterEmbedding
from .character_memory import CharacterMemory, MemoryRecord
from .relationship_manager import RelationshipManager
from .character_genesis import CharacterGenesis
from .dialogue_generator import DialogueGenerator


# --- Define a Facade Class (Optional but recommended) ---
from typing import List, Dict, Optional, Any
from ..utils import LLMwrapper

class CharacterSystemFacade:
    """Provides a unified interface to the character system components."""

    def __init__(self, llm_wrapper = LLMwrapper): 

        self.llm_wrapper = llm_wrapper
        self.vector_store_manager = VectorStoreManager() # Ensures DB is ready
        self.embedding_manager = CharacterEmbedding()
        self.relationship_manager = RelationshipManager()
        self.memory_manager = CharacterMemory(llm_wrapper=self.llm_wrapper)
        self.genesis_manager = CharacterGenesis(llm_wrapper=self.llm_wrapper)
        self.dialogue_manager = DialogueGenerator(
            memory_system=self.memory_manager,
            relationship_manager=self.relationship_manager
        )
        self.active_characters: Dict[str, CharacterProfile] = {}
        logger.info("CharacterSystemFacade initialized.")

    async def load_or_create_character(self, character_input: CharacterInput, story_context: Optional[Dict] = None) -> Optional[CharacterProfile]:
        """Creates a new character profile, embeds it, and adds to active list."""
        #TODO: create a robust check for if character already exists
        # For now, assume we create anew based on input object ID or name uniqueness is handled upstream

        logger.info(f"Creating profile for character input: {character_input.name}")
        profile = await self.genesis_manager.create_character_profile(character_input, story_context)
        if profile:
            logger.info(f"Profile created for {profile.name}, adding embeddings...")
            self.embedding_manager.add_or_update_character_aspects(profile)
            self.active_characters[profile.character_id] = profile
            logger.info(f"Character {profile.name} ({profile.character_id}) added to active characters.")
            return profile
        else:
            logger.error(f"Failed to create profile for character input: {character_input.name}")
            return None

    def get_character(self, character_id: str) -> Optional[CharacterProfile]:
        """Retrieves an active character profile by ID."""
        return self.active_characters.get(character_id)

    def get_all_active_characters(self) -> List[CharacterProfile]:
         """Returns a list of all currently active characters."""
         return list(self.active_characters.values())

    def update_character_state(self, character_id: str, updates: Dict[str, Any]):
        """Updates the dynamic state of an active character."""
        character = self.get_character(character_id)
        if character:
            character.update_state(updates)
            # Maybe re-embed certain state aspects if needed? (e.g., mood) - skip for now
            logger.debug(f"Updated state for {character.name}.")
        else:
            logger.warning(f"Attempted to update state for non-active character ID: {character_id}")

    async def add_character_memory(self, character_id: str, event_description: str, **kwargs):
         """Adds a memory to a character."""
         # Add memory via memory manager
         await self.memory_manager.add_memory(character_id, event_description, **kwargs)
         # Potentially update character state based on memory's emotional impact
         if 'emotional_impact' in kwargs and kwargs['emotional_impact']:
              self.update_character_state(character_id, {'current_mood': kwargs['emotional_impact'], 'last_significant_event_summary': event_description[:150]})


    def update_relationship(self, char_id1: str, char_id2: str, interaction_summary: str, **kwargs):
        """Updates relationship between two characters."""
        self.relationship_manager.update_relationship(char_id1, char_id2, interaction_summary, **kwargs)

    async def generate_dialogue_for_character(self, character_id: str, scene_context: str, recent_dialogue: List[str], other_character_ids: List[str], **kwargs) -> Optional[str]:
        """Generates dialogue for a specific active character."""
        character = self.get_character(character_id)
        if not character:
            logger.error(f"Cannot generate dialogue for unknown character ID: {character_id}")
            return None

        other_characters = [self.get_character(cid) for cid in other_character_ids if self.get_character(cid)]
        if len(other_characters) != len(other_character_ids):
             logger.warning("Some other characters specified in scene were not found in active list.")

        return await self.dialogue_manager.generate_dialogue(
            character=character,
            scene_context=scene_context,
            recent_dialogue=recent_dialogue,
            other_characters_in_scene=other_characters,
            **kwargs
        )

    # Add methods for saving/loading state if needed for persistence beyond ChromaDB


# Expose the Facade and core models
__all__ = [
    "CharacterProfile",
    "CharacterInput", 
    "CharacterState",
    "MemoryRecord",
    "CharacterSystemFacade",
    "VectorStoreManager", 
    "CharacterEmbedding",
    "CharacterMemory",
    "RelationshipManager",
    "CharacterGenesis",
    "DialogueGenerator",
]