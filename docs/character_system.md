Goals for this Module:

-   Rich Character Profiles: Go beyond basic descriptions.

-   Semantic Memory: Store and retrieve relevant memories using vector search.

-   Consistent Dialogue: Generate dialogue reflecting personality, current state, and memories.

-   Character Evolution: Allow traits and relationships to change based on story events.

-   Efficient Retrieval: Quickly fetch relevant character data for generation prompts.

```
character_system/
├── __init__.py
├── character_profile.py        # Defines the main CharacterProfile Pydantic model
├── character_genesis.py        # Expands initial input into rich profiles (uses LLM)
├── vector_store_manager.py     # Manages ChromaDB client and collections (specific to characters)
├── character_embedding.py      # Handles embedding generation and vector DB operations for characters
├── character_memory.py         # Manages storing, retrieving, and summarizing character memories
├── relationship_manager.py     # Tracks and updates relationships between characters
└── dialogue_generator.py       # Constructs prompts and generates character-specific dialogue (uses LLM)
```

    