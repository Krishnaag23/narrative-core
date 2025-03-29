# Narrative Core - Utilities Module (`src/utils/`)

This module provides centralized, reusable components for the Narrative Core project. Using these utilities ensures consistency, simplifies maintenance, and makes development easier for the team.

## Modules

### 1. Configuration (`config.py`)

-   **Purpose:** Manages application settings like API keys, file paths, and model names.
-   **Mechanism:** Uses `pydantic-settings` to load configuration from environment variables and a `.env` file located at the project root.
-   **Usage:** Import the `settings` singleton object.
    ```python
    from src.utils.config import settings

    api_key = settings.OPENAI_API_KEY
    model = settings.LLM_MODEL_NAME
    db_path = settings.VECTOR_DB_PATH

    print(f"Using OpenAI Key (first 5 chars): {api_key[:5]}...")
    print(f"Default LLM Model: {model}")
    ```
-   **Setup:** Create a `.env` file in the project root directory (alongside `src/`) and add your `OPENAI_API_KEY` and any other overrides.
    ```env
    # .env
    OPENAI_API_KEY="sk-your-key-here..."
    # LLM_MODEL_NAME="gpt-4" # Optional override
    ```

### 2. Prompt Manager (`prompt_manager.py`)

-   **Purpose:** Loads prompt templates from YAML files and formats them with runtime data. Avoids hardcoding prompts in the main logic.
-   **Mechanism:** Scans the directory specified by `settings.PROMPT_DIRECTORY` (defaults to `src/config/prompts/`) for `.yaml` or `.yml` files. Each key-value pair in the YAML file (where the value is a string) becomes a loadable prompt template.
-   **Usage:** Get the `PromptManager` singleton instance and call `get_prompt`.
    ```python
    from src.utils import PromptManager # Import singleton

    prompt_manager = PromptManager() # Get the instance

    # Assuming a prompt with key 'welcome_message' exists in a YAML file:
    # welcome_message: "Hello, {user_name}! Welcome to {app_name}."
    formatted_prompt = prompt_manager.get_prompt(
        "welcome_message",
        user_name="Alice",
        app_name="Narrative Core"
    )

    if formatted_prompt:
        print(formatted_prompt)
        # Output: Hello, Alice! Welcome to Narrative Core.
    else:
        print("Prompt key not found or formatting error.")

    # To reload prompts if files change:
    # prompt_manager.reload_prompts()
    ```
-   **Setup:** Create YAML files (e.g., `dialogue.yaml`, `summarization.yaml`) inside `src/config/prompts/`. Define prompts using unique keys and use `{variable_name}` for placeholders.

### 3. LLM Utilities (`llm_utils.py`)

-   **Purpose:** Provides a consistent interface for interacting with LLMs, currently focused on OpenAI's Chat Completions API. Handles client setup, API calls, and basic error management.
-   **Mechanism:** Uses the `openai` library and the API key from `settings`. Provides both synchronous and asynchronous methods.
-   **Usage:** Use the class methods directly.
    ```python
    import asyncio
    from src.utils import LLMUtils

    # Synchronous call
    prompt = "What is the capital of France?"
    sync_response = LLMUtils.query_llm_sync(prompt, max_tokens=50)
    if sync_response:
        print(f"Sync Response: {sync_response}")

    # Asynchronous call
    async def run_async():
        async_response = await LLMUtils.query_llm_async(
            prompt,
            max_tokens=50,
            temperature=0.5,
            system_message="You are a helpful assistant."
        )
        if async_response:
            print(f"Async Response: {async_response}")

    # asyncio.run(run_async()) # Uncomment to run async example
    ```

### 4. Vector Store Interface (`vector_store_utils.py`)

-   **Purpose:** Provides a simplified interface for interacting with the vector database (ChromaDB). Handles client initialization, collection management, adding/upserting data, and querying.
-   **Mechanism:** Wraps the `chromadb` library. Uses the persistent storage path defined in `settings.VECTOR_DB_PATH`. Chroma automatically handles embedding generation using a default model (ensure `sentence-transformers` is installed).
-   **Usage:** Get the `VectorStoreInterface` singleton instance.
    ```python
    from src.utils import VectorStoreInterface

    vs_interface = VectorStoreInterface() # Get the instance
    COLLECTION_NAME = "story_elements"

    # Ensure collection exists
    collection = vs_interface.get_or_create_collection(COLLECTION_NAME)

    if collection:
        # Add/Update data
        vs_interface.upsert(
            collection_name=COLLECTION_NAME,
            ids=["char_001_trait1", "char_001_goal1"],
            documents=["Brave and adventurous", "Find the lost artifact"],
            metadatas=[
                {"character_id": "char_001", "type": "trait"},
                {"character_id": "char_001", "type": "goal"}
            ]
        )

        # Query data
        query = "What drives the character?"
        # Note: query returns a list of results *per query text*. We sent one query.
        results_list = vs_interface.query(
            collection_name=COLLECTION_NAME,
            query_texts=[query],
            n_results=2,
            where_filter={"character_id": "char_001"} # Optional filter
        )

        if results_list and results_list[0]: # Access results for the first query
             print(f"Found {len(results_list[0])} relevant items for query '{query}':")
             for item in results_list[0]:
                 print(f"- ID: {item['id']}, Distance: {item['distance']:.4f}, Doc: {item['document']}")
        else:
             print(f"No results found for query '{query}'")

        # Get specific items
        items = vs_interface.get_items(COLLECTION_NAME, ids=["char_001_trait1"])
        if items:
             print(f"Retrieved item by ID: {items[0]}")

    else:
        print("Failed to get or create vector store collection.")

    ```
