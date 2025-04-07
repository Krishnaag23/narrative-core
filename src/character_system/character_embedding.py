"""
Handles the creation and querying of vector embeddings for character profiles
and their aspects (traits, goals, backstory summaries) using ChromaDB.
"""

import logging
from typing import List, Dict, Optional, Any
from .vector_store_manager import VectorStoreManager
from .character_profile import CharacterProfile

#TODO: check for the need of custom embedding model.

logger = logging.getLogger(__name__)

class CharacterEmbedding:

    def __init__(self):
        """Initializes the embedding system with access to the vector store."""
        self.vector_store_manager = VectorStoreManager()
        self.collection = self.vector_store_manager.get_or_create_collection("character_aspects")
        

    def add_or_update_character_aspects(self, character: CharacterProfile):
        """
        Generates embeddings for key aspects of a character and upserts them
        into the vector store. Uses Chroma's automatic embedding generation.

        Args:
            character: The CharacterProfile object.
        """
        aspects_to_embed: Dict[str, List[str]] = {
            "trait": character.core_traits,
            "goal": character.goals,
            "motivation": character.motivations,
            "flaw": character.flaws,
            "strength": character.strengths,
            "mannerism": character.mannerisms,
            "backstory_summary": [character.backstory[:500]], # Example: first 500 chars
            "voice": [character.voice_description],
            "physical_desc": [character.physical_description[:500]]
        }

        documents: List[str] = []
        metadatas: List[Dict[str, Any]] = []
        ids: List[str] = []

        for aspect_type, values in aspects_to_embed.items():
            for i, value in enumerate(values):
                if value and isinstance(value, str) and value.strip(): # Ensure non-empty strings
                    doc_id = f"{character.character_id}_{aspect_type}_{i}"
                    documents.append(value.strip())
                    metadatas.append({
                        "character_id": character.character_id,
                        "character_name": character.name,
                        "aspect_type": aspect_type,
                        "timestamp": character.last_profile_update.isoformat() # Track update time
                    })
                    ids.append(doc_id)

        if not documents:
            logger.warning(f"No valid text aspects found to embed for character {character.name} ({character.character_id}).")
            return

        try:
            # Let Chroma handle embedding generation internally via its configured function
            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            logger.info(f"Upserted {len(ids)} aspects for character {character.name} ({character.character_id}) into vector store.")

        except Exception as e:
            logger.error(f"Failed to upsert character aspects for {character.name}: {e}", exc_info=True)

    def find_similar_aspects(self, query_text: str, character_id: Optional[str] = None, aspect_type: Optional[str] = None, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Finds character aspects semantically similar to the query text.

        Args:
            query_text: The text to search for similarities.
            character_id: Optional filter to search within a specific character's aspects.
            aspect_type: Optional filter for the type of aspect (e.g., 'trait', 'goal').
            n_results: Number of results to return.

        Returns:
            A list of search results, including documents, metadata, and distances. Returns empty list on error.
        """
        where_filter = {}
        if character_id:
            where_filter["character_id"] = character_id
        if aspect_type:
            where_filter["aspect_type"] = aspect_type

        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where_filter if where_filter else None,
                include=["documents", "metadatas", "distances"] # Request necessary fields
            )
            logger.debug(f"Vector query for '{query_text}' (filter: {where_filter}) returned {len(results.get('ids', [[]])[0])} results.")

            # Process results into a more usable format
            processed_results = []
            # Chroma returns lists of lists, one inner list per query text. We only have one query text.
            ids = results.get('ids', [[]])[0]
            distances = results.get('distances', [[]])[0]
            metadatas = results.get('metadatas', [[]])[0]
            documents = results.get('documents', [[]])[0]

            for i, doc_id in enumerate(ids):
                processed_results.append({
                    "id": doc_id,
                    "distance": distances[i] if distances else None,
                    "metadata": metadatas[i] if metadatas else None,
                    "document": documents[i] if documents else None,
                })

            return processed_results

        except Exception as e:
            logger.error(f"Error querying character aspects for '{query_text}': {e}", exc_info=True)
            return []

    def get_aspects_for_character(self, character_id: str, aspect_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves all stored aspects for a given character ID."""
        where_filter = {"character_id": character_id}
        if aspect_type:
            where_filter["aspect_type"] = aspect_type

        try:
            # Use get instead of query when just filtering by metadata
            results = self.collection.get(
                where=where_filter,
                include=["documents", "metadatas"]
            )
            logger.debug(f"Retrieved {len(results.get('ids', []))} aspects for character {character_id} (filter: {where_filter}).")

            processed_results = []
            ids = results.get('ids', [])
            metadatas = results.get('metadatas', [])
            documents = results.get('documents', [])

            for i, doc_id in enumerate(ids):
                 processed_results.append({
                    "id": doc_id,
                    "metadata": metadatas[i] if metadatas else None,
                    "document": documents[i] if documents else None,
                })
            return processed_results
        except Exception as e:
            logger.error(f"Error getting aspects for character {character_id}: {e}", exc_info=True)
            return []