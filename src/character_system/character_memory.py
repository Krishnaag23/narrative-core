"""
Handles storing, summarizing, retrieving, and managing memories for characters.
Uses vector embeddings for semantic retrieval of relevant memories.
"""
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
import uuid

from .vector_store_manager import VectorStoreManager, CHARACTER_MEMORIES_COLLECTION
from ..utils import LLMwrapper as llm_wrapper

logger = logging.getLogger(__name__)

class MemoryRecord(BaseModel):
    """Represents a single memory entry for a character."""
    memory_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    character_id: str
    timestamp: datetime = Field(default_factory=datetime.datetime.now())
    event_description: str 
    summary: str # LLM-generated summary of the event
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0) 
    related_characters: List[str] = Field(default_factory=list) # IDs of other chars involved
    emotional_impact: Optional[str] = Field(None, description="Dominant emotion felt during/after event")

class CharacterMemory:
    def __init__(self, llm_wrapper = llm_wrapper): 
        """
        Initializes the memory system.

        Args:
            llm_wrapper: An instance of the LLM wrapper for summarization.
        """
        self.vector_store_manager = VectorStoreManager()
        self.collection = self.vector_store_manager.get_character_memory_collection()
        self.llm_wrapper = llm_wrapper 
        logger.info("CharacterMemory initialized.")

    async def _summarize_event(self, event_description: str) -> str:
        """Uses LLM to summarize a detailed event description."""
        if not self.llm_wrapper:
            logger.warning("LLM wrapper not available. Using truncated description as summary.")
            return event_description[:300] # Fallback: truncate

        prompt = (
            f"Event: \"{event_description}\"\n\n"
        )

        system_message = (
            f"You are an expert text summarizer system. When the user sends you an event with an event description, you generate a summarised event description for concise memory management"
            f"(1-2 sentences) focusing on the key actions, outcomes, and emotional impact:\n\n"
            f"Here is the input format: Event: \"event description\"\n\n"
            f"output consise memory summary"
            f"This is important, generate only the summary in the response, no redundant messages ,not even at the end."
        )
        try:
            
            summary = await self.llm_wrapper.query_llm_async(prompt=prompt, system_message=system_message, max_tokens=100)

            logger.debug(f"Summarized event: {summary.strip()}")
            return summary.strip()
        except Exception as e:
            logger.error(f"Failed to summarize event using LLM: {e}", exc_info=True)
            return event_description[:300] # Fallback to truncation on error

    async def add_memory(self, character_id: str, event_description: str, importance: float = 0.5, related_characters: List[str] = None, emotional_impact: Optional[str] = None):
        """
        Adds a new memory for a character, summarizes it, and stores its embedding.

        Args:
            character_id: The ID of the character experiencing the event.
            event_description: A detailed description of what happened.
            importance: A score (0-1) indicating the memory's significance.
            related_characters: List of other character IDs involved.
            emotional_impact: Dominant emotion associated with the memory.
        """
        if not event_description:
             logger.warning("Attempt to add an empty memory.")
             return

        summary = await self._summarize_event(event_description)
        now = datetime.datetime.now()

        memory = MemoryRecord(
            character_id=character_id,
            timestamp=now,
            event_description=event_description, # Store original too? Optional.
            summary=summary,
            importance_score=max(0.0, min(1.0, importance)), # Clamp importance
            related_characters=related_characters or [],
            emotional_impact=emotional_impact
        )

        # Store the summary's embedding in ChromaDB
        try:
            metadata = {
                "character_id": memory.character_id,
                "timestamp": memory.timestamp.isoformat(),
                "importance": memory.importance_score,
                "related_characters": ",".join(memory.related_characters), # Store as comma-sep string
                "emotional_impact": memory.emotional_impact or "N/A"
                #TODO: Add episode number here if available contextually?
            }
            self.collection.add(
                ids=[memory.memory_id],
                documents=[memory.summary], 
                metadatas=[metadata]
            )
            logger.info(f"Added memory {memory.memory_id} for character {character_id}.")

        except Exception as e:
            logger.error(f"Failed to add memory {memory.memory_id} to vector store: {e}", exc_info=True)


    def retrieve_relevant_memories(self, character_id: str, query_text: str, n_results: int = 5, recency_weight: float = 0.1, importance_weight: float = 0.1) -> List[Dict[str, Any]]:
        """
        Retrieves memories relevant to a query, considering similarity, recency, and importance.

        Args:
            character_id: The ID of the character whose memories to search.
            query_text: The context or query to find relevant memories for.
            n_results: The maximum number of memories to return.
            recency_weight: How much to weigh recent memories (0 to disable).
            importance_weight: How much to weigh important memories (0 to disable).

        Returns:
            A list of the most relevant memory summaries and metadata, sorted by relevance.
        """
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results * 3, # Retrieve more initially to allow for re-ranking
                where={"character_id": character_id},
                include=["documents", "metadatas", "distances"]
            )

            processed_memories = []
            now = datetime.datetime.now()

            # Chroma returns lists of lists, one inner list per query text. We only have one query text.
            ids = results.get('ids', [[]])[0]
            distances = results.get('distances', [[]])[0]
            metadatas = results.get('metadatas', [[]])[0]
            documents = results.get('documents', [[]])[0]


            for i, doc_id in enumerate(ids):
                metadata = metadatas[i]
                if not metadata: continue 

                similarity_score = 1.0 - (distances[i] if distances and distances[i] is not None else 1.0) 

                # --- Recency Score ---
                recency_score = 0.0
                if recency_weight > 0:
                    try:
                        timestamp = datetime.fromisoformat(metadata.get("timestamp", ""))
                        time_diff_hours = (now - timestamp).total_seconds() / 3600
                        # Simple exponential decay - adjust decay rate as needed
                        decay_rate = 0.01
                        recency_score = (1 / (1 + decay_rate * time_diff_hours))
                    except (ValueError, TypeError):
                        recency_score = 0.0 # Default if timestamp is invalid

                # --- Importance Score ---
                importance_score = 0.0
                if importance_weight > 0:
                    importance_score = float(metadata.get("importance", 0.0))

                # --- Combined Relevance Score ---
                relevance_score = (
                    (1.0 - recency_weight - importance_weight) * similarity_score +
                    recency_weight * recency_score +
                    importance_weight * importance_score
                )

                processed_memories.append({
                    "memory_id": doc_id,
                    "summary": documents[i],
                    "timestamp": metadata.get("timestamp"),
                    "importance": metadata.get("importance"),
                    "related_characters": metadata.get("related_characters", "").split(','),
                    "emotional_impact": metadata.get("emotional_impact"),
                    "relevance_score": relevance_score,
                    "similarity_score": similarity_score, # Keep for debugging
                    "recency_score": recency_score,       # Keep for debugging
                })

            # Sort by the combined relevance score (highest first)
            processed_memories.sort(key=lambda x: x["relevance_score"], reverse=True)

            logger.info(f"Retrieved {len(processed_memories[:n_results])} relevant memories for char {character_id} based on query '{query_text[:50]}...'.")
            return processed_memories[:n_results]

        except Exception as e:
            logger.error(f"Error retrieving memories for character {character_id}: {e}", exc_info=True)
            return []