"""
Generates dialogue for a specific character based on their profile,
current state, relevant memories, relationships, and scene context.
"""

import logging
from typing import List, Dict, Optional, Any

from .character_profile import CharacterProfile
from .character_memory import CharacterMemory
from .relationship_manager import RelationshipManager

from ..utils import LLMwrapper

logger = logging.getLogger(__name__)

class DialogueGenerator:
    def __init__(self, memory_system: CharacterMemory, relationship_manager: RelationshipManager):
        """
        Initializes the Dialogue Generator.

        Args:
            llm_wrapper: An instance of the LLM wrapper.
            memory_system: Instance of CharacterMemory to retrieve memories.
            relationship_manager: Instance of RelationshipManager.
        """
        self.llm_wrapper = LLMwrapper
        self.memory_system = memory_system
        self.relationship_manager = relationship_manager
        if not self.llm_wrapper:
            raise ValueError("LLM wrapper instance is required for DialogueGenerator.")
        logger.info("DialogueGenerator initialized.")

    async def generate_dialogue(
        self,
        character: CharacterProfile,
        scene_context: str,
        recent_dialogue: List[str],
        other_characters_in_scene: List[CharacterProfile],
        scene_objective: Optional[str] = None,
        max_tokens: int = 100
    ) -> Optional[str]:
        """
        Generates a line of dialogue for the character in the given context.

        Args:
            character: The CharacterProfile of the speaking character.
            scene_context: A description of the current scene, setting, and action.
            recent_dialogue: List of the last few lines of dialogue spoken.
            other_characters_in_scene: Profiles of other characters present.
            scene_objective: Optional goal for the character in this scene.
            max_tokens: Max length of the generated dialogue line.

        Returns:
            The generated dialogue string, or None on failure.
        """
        logger.info(f"Generating dialogue for {character.name}...")

        # Retrieve Relevant memory
        memory_query = f"{scene_context}\nRecent Dialogue:\n{''.join(recent_dialogue[-10:])}" # Query based on scene + recent talk
        relevant_memories = self.memory_system.retrieve_relevant_memories(
            character_id=character.character_id,
            query_text=memory_query,
            n_results=5 
        )
        memory_str = "\nRelevant Memories:\n" + "\n".join([f"- {mem['summary']} (Impact: {mem.get('emotional_impact', 'N/A')})" for mem in relevant_memories]) if relevant_memories else "\nRelevant Memories: None."

        #  Get Relationship Summaries
        relationship_str = "\nRelationships with characters present:"
        if not other_characters_in_scene:
             relationship_str += "\n- Alone"
        else:
            for other_char in other_characters_in_scene:
                 rel_summary = self.relationship_manager.get_relationship_summary_for_prompt(character.character_id, other_char.character_id)
                 relationship_str += f"\n- {other_char.name}: {rel_summary}"
        
        prompt = f"""
        You are roleplaying as the character: {character.name}.

        Character Profile:
        {character.get_core_summary()}

        Current Situation:
        {scene_context}

        {relationship_str}
        {memory_str}

        Scene Objective for {character.name}: {scene_objective or 'Engage naturally in the scene.'}

        Recent Dialogue History (last few lines):
        {''.join(recent_dialogue) if recent_dialogue else 'Start of conversation.'}

        Instructions:
        Generate the *next* line of dialogue spoken ONLY by {character.name}.
        - Speak in their distinct voice, reflecting their traits, mood ({character.current_state.current_mood or 'Neutral'}), and motivations.
        - Consider their relationships with others present and relevant memories.
        - Dialogue should be natural, concise (around 1-3 sentences unless necessary), and move the scene forward or reveal character.
        - Do NOT add actions or descriptions, only the spoken words.
        - Do NOT say "{character.name}: ". Just output the dialogue itself.

        {character.name}'s next line:
        """

        try:
            dialogue = await self.llm_wrapper.query_llm_async(prompt, max_tokens=max_tokens, temperature=0.75) # Slightly higher temp for creativity

            # Post-process: Remove potential artifacts like quotes or character name prefixes if LLM adds them
            dialogue = dialogue.strip().strip('"').strip("'")
            if dialogue.lower().startswith(f"{character.name.lower()}:"):
                dialogue = dialogue.split(":", 1)[1].strip()

            logger.info(f"Generated dialogue for {character.name}: \"{dialogue}\"")
            return dialogue if dialogue else None 

        except Exception as e:
            logger.error(f"LLM call failed during dialogue generation for {character.name}: {e}", exc_info=True)
            return None