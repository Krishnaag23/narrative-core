"""
Optimizes the context provided to the LLM for generation tasks by selecting
the most relevant information from various memory sources within token limits.
"""

import logging
from typing import List, Dict, Optional, Any, Tuple

from ..utils import LLMwrapper 
from .hierarchical_summarization import HierarchicalSummarizer
from .knowledge_graph import KnowledgeGraphManager
from ..character_system import CharacterMemory

logger = logging.getLogger(__name__)

# Rough estimate, replace with actual tokenizer later
TOKEN_ESTIMATE_PER_CHAR = 0.3

class ContextOptimizer:
    """Selects and ranks context information for LLM prompts."""

    def __init__(
        self,
        llm_wrapper: LLMwrapper,
        
        summarizer: HierarchicalSummarizer,
        kg_manager: KnowledgeGraphManager,
        character_memory: CharacterMemory 
    ):
        self.llm = llm_wrapper
        self.summarizer = summarizer
        self.kg_manager = kg_manager
        self.character_memory = character_memory
        # TODO: Add other memory managers as needed
        logger.info("ContextOptimizer initialized.")

    def _estimate_tokens(self, text: str) -> int:
        """Basic token estimation. Replace with a proper tokenizer (e.g., tiktoken)."""
        return int(len(text) * TOKEN_ESTIMATE_PER_CHAR)

    async def retrieve_and_optimize_context(
        self,
        context_query: str, # What the next generation step is about
        character_ids: List[str], # Characters involved in the next step
        max_tokens: int,
        current_episode_num: Optional[int] = None,
        # Include summaries from previous steps if available
        previous_ep_summary: Optional[str] = None,
        previous_scene_summary: Optional[str] = None
    ) -> str:
        """
        Retrieves relevant information from memory systems and optimizes it
        to fit within the token budget.

        Args:
            context_query: Description of the current task (e.g., "Generate dialogue for scene").
            character_ids: List of character IDs relevant to the task.
            max_tokens: The maximum number of tokens allowed for the context.
            current_episode_num: The current episode number.
            previous_ep_summary: Summary of the previous episode.
            previous_scene_summary: Summary of the previous scene.

        Returns:
            A formatted string containing the optimized context.
        """
        logger.info(f"Optimizing context for query '{context_query[:50]}...' with budget {max_tokens} tokens.")
        available_tokens = max_tokens
        context_elements: List[Tuple[float, str, str]] = [] # (score, type, content)

        # --- Gather Potential Context ---

       
        if previous_scene_summary:
            tokens = self._estimate_tokens(previous_scene_summary)
            if tokens < available_tokens * 0.2: # Limit recent summary size
                 context_elements.append((1.0, "Previous Scene Summary", previous_scene_summary))
                 available_tokens -= tokens
        if previous_ep_summary:
             tokens = self._estimate_tokens(previous_ep_summary)
             if tokens < available_tokens * 0.3:
                 context_elements.append((0.95, "Previous Episode Summary", previous_ep_summary))
                 available_tokens -= tokens

       
        for char_id in character_ids:
            
             # core_summary = get_character_core_summary(char_id) # Need access to Character System Facade potentially
             # For now, retrieve from KG if available
             kg_char_info = self.kg_manager.get_character_info(char_id)
             if kg_char_info:
                  # Format KG info concisely
                  kg_summary = f"KG Info ({kg_char_info.get('name', char_id)}): Role={kg_char_info.get('role')}, Traits={kg_char_info.get('traits', [])}, Goals={kg_char_info.get('goals', [])}"
                  tokens = self._estimate_tokens(kg_summary)
                  if tokens < available_tokens * 0.2: # Limit per character
                      context_elements.append((0.9, f"Character KG Summary ({char_id})", kg_summary))
                      available_tokens -= tokens

             # Retrieve relevant memories for character
             relevant_memories = self.character_memory.retrieve_relevant_memories(
                 character_id=char_id,
                 query_text=context_query, # Use task description
                 n_results=3 # Get top 3 relevant memories
             )
             for mem in relevant_memories:
                 mem_text = f"Memory ({char_id}): {mem['summary']}"
                 mem_score = mem.get('relevance_score', 0.6) # Use pre-calculated relevance
                 tokens = self._estimate_tokens(mem_text)
                 if tokens < available_tokens * 0.15:
                      context_elements.append((mem_score, f"Character Memory ({char_id})", mem_text))
                      available_tokens -= tokens

        #  Knowledge Graph Context (Medium Priority)
        # Get broader context around characters/locations mentioned in query
        # Placeholder: Use KG context around primary character
        if character_ids:
            kg_context = self.kg_manager.get_context_around_character(character_ids[0], depth=1)
            # Format KG context concisely
            kg_context_str = f"KG Context ({character_ids[0]}): {str(kg_context)}" # Basic string representation
            tokens = self._estimate_tokens(kg_context_str)
            if tokens < available_tokens * 0.25:
                context_elements.append((0.7, "Knowledge Graph Context", kg_context_str))
                available_tokens -= tokens

        # Higher-Level Summaries (Lower Priority, if space allows)
        # Placeholder: Fetch summary of the 'act' or last few episodes if needed
        # act_summary = await self.summarizer.summarize_act_or_chunk(...)
        # if act_summary:
        #     tokens = self._estimate_tokens(act_summary)
        #     if tokens < available_tokens:
        #          context_elements.append((0.5, "Act Summary", act_summary))
        #          available_tokens -= tokens


        # --- Rank and Select ---
        # Sort by score (descending)
        context_elements.sort(key=lambda x: x[0], reverse=True)

        # Build final context string within the *original* token budget
        final_context_parts = []
        current_tokens = 0
        logger.debug(f"Optimizing context. Initial candidates: {len(context_elements)}")
        for score, c_type, content in context_elements:
            element_tokens = self._estimate_tokens(f"{c_type}:\n{content}\n\n") # Estimate tokens for formatted element
            if current_tokens + element_tokens <= max_tokens:
                final_context_parts.append(f"--- {c_type} (Score: {score:.2f}) ---\n{content}")
                current_tokens += element_tokens
                logger.debug(f"Added context: {c_type} ({element_tokens} tokens). Total: {current_tokens}/{max_tokens}")
            else:
                 logger.debug(f"Skipped context (budget exceeded): {c_type} ({element_tokens} tokens)")

        final_context = "\n\n".join(final_context_parts)
        logger.info(f"Final optimized context size: ~{current_tokens} tokens.")
        return final_context