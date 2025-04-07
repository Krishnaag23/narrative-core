#!/usr/bin/env python

"""
Script to populate the ChromaDB vector store with example cultural narratives for RAG.
Run this script ONCE before running the main pipeline script.
"""

import sys
import os
import logging

# --- Path Setup ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_PATH = os.path.join(PROJECT_ROOT, 'src')
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

try:
    from src.utils import VectorStoreInterface
    # Define collection name consistent with CulturalContextDetector
    CULTURAL_NARRATIVES_COLLECTION = "cultural_narratives"
except ImportError as e:
    print(f"ERROR: Failed to import VectorStoreInterface. Ensure src path is correct.")
    print(f"Import error details: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PopulateRAG")

# --- Example Cultural Data ---
# Add more diverse and detailed examples relevant to KukuFM's audience
CULTURAL_DATA = [
    {
        "id": "panch_lion_rabbit",
        "document": "In the Panchatantra tale 'The Lion and the Clever Rabbit', a cunning rabbit outsmarts a greedy lion who demands daily animal sacrifices. The rabbit tricks the lion into seeing his own reflection in a well, convincing him it's a rival. The enraged lion leaps into the well to his demise. The story teaches that intelligence can overcome brute strength.",
        "metadata": {
            "title": "Panchatantra: The Lion and the Clever Rabbit",
            "framework": "Panchatantra",
            "theme": "Intelligence over Strength",
            "characters": ["Lion", "Rabbit"],
            "is_sensitive": False,
            "source": "Panchatantra Fable"
        }
    },
    {
        "id": "rasa_shringara",
        "document": "Shringara Rasa, the Erotic or Romantic sentiment in Indian aesthetics (Ashtarasa/Navarasa), explores love, beauty, and attraction. It has two aspects: Samyoga (love in union) and Vipralambha (love in separation). It is often associated with deities like Krishna and Radha, depicting divine love and longing. Evoking Shringara requires depicting attractive settings, characters, and expressions of affection or yearning.",
        "metadata": {
            "title": "Ashtarasa: Shringara Rasa (Romantic Sentiment)",
            "framework": "Ashtarasa",
            "theme": "Love, Romance, Beauty, Longing",
            "is_sensitive": False, # Can be sensitive depending on depiction
            "source": "Natya Shastra / Indian Aesthetics"
        }
    },
    {
        "id": "rasa_karuna",
        "document": "Karuna Rasa represents compassion, sadness, or pathos in the Ashtarasa framework. It arises from witnessing suffering, loss, or grief. Unlike mere sadness, Karuna often involves empathy and a desire to alleviate the suffering observed. It can be evoked through depicting tragic events, separation from loved ones, or the plight of the unfortunate.",
         "metadata": {
            "title": "Ashtarasa: Karuna Rasa (Compassion/Sadness)",
            "framework": "Ashtarasa",
            "theme": "Compassion, Sadness, Grief, Pathos",
            "is_sensitive": True, # Depictions of suffering can be sensitive
            "source": "Natya Shastra / Indian Aesthetics"
        }
    },
    # Add more examples: Mahabharata summaries, Ramayana themes, regional folklore snippets, etc.
]

def populate():
    """Adds the example data to the vector store."""
    logger.info("Attempting to populate the RAG vector store...")
    try:
        vs_interface = VectorStoreInterface()
        # Ensure the collection exists explicitly
        collection = vs_interface.get_or_create_collection(CULTURAL_NARRATIVES_COLLECTION)
        if not collection:
             logger.error("Failed to get or create the cultural narratives collection. Aborting.")
             return

        existing_ids = set(collection.get(limit=1000).get('ids', [])) # Get existing IDs to avoid duplicates
        logger.info(f"Found {len(existing_ids)} existing documents in '{CULTURAL_NARRATIVES_COLLECTION}'.")

        ids_to_add = []
        docs_to_add = []
        metadatas_to_add = []

        added_count = 0
        skipped_count = 0
        for item in CULTURAL_DATA:
            if item["id"] in existing_ids:
                logger.debug(f"Skipping existing document ID: {item['id']}")
                skipped_count += 1
                continue

            ids_to_add.append(item["id"])
            docs_to_add.append(item["document"])
            metadatas_to_add.append(item["metadata"])
            added_count += 1

        if ids_to_add:
            success = vs_interface.add(
                collection_name=CULTURAL_NARRATIVES_COLLECTION,
                ids=ids_to_add,
                documents=docs_to_add,
                metadatas=metadatas_to_add
            )
            if success:
                logger.info(f"Successfully added {added_count} new documents to '{CULTURAL_NARRATIVES_COLLECTION}'.")
            else:
                logger.error("Failed to add documents to the vector store.")
        else:
            logger.info("No new documents to add.")

        logger.info(f"RAG population summary: Added={added_count}, Skipped={skipped_count}")

    except Exception as e:
        logger.critical(f"An error occurred during RAG database population: {e}", exc_info=True)

if __name__ == "__main__":
    print("--- Populating Cultural RAG Database ---")
    print(f"This script adds example documents to the '{CULTURAL_NARRATIVES_COLLECTION}' collection.")
    print("Run this only once, or if you want to reset/add new examples.")
    # Add confirmation?
    # confirm = input("Proceed? (y/n): ")
    # if confirm.lower() == 'y':
    populate()
    print("--- RAG Population Attempt Finished ---")