"""
Manages the ChromaDB client instance and specific collections
for the character system (embeddings, memories).
Ensures a single client instance is used.
"""

from ..utils import VectorStoreInterface

# Define collection names centrally
CHARACTER_EMBEDDINGS_COLLECTION = "character_aspects"
CHARACTER_MEMORIES_COLLECTION = "character_memories"

class VectorStoreManager (VectorStoreInterface):

    super().get_or_create_collection(CHARACTER_EMBEDDINGS_COLLECTION)
    super().get_or_create_collection(CHARACTER_MEMORIES_COLLECTION)

    def get_character_embedding_collection(self):
        """Convenience method to get the character aspects collection."""
        return super().get_or_create_collection(CHARACTER_EMBEDDINGS_COLLECTION)

    def get_character_memory_collection(self):
        """Convenience method to get the character memories collection."""
        return super().get_or_create_collection(CHARACTER_MEMORIES_COLLECTION)
