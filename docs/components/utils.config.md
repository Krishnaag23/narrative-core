 --- Example Usage ---
``` 

 from src.utils.config import settings
 api_key = settings.OPENAI_API_KEY
 print(f"Using model: {settings.LLM_MODEL_NAME}")
 src/utils/config.py

```

Handles application configuration using Pydantic BaseSettings.
Loads settings from environment variables and .env files.
Provides a singleton 'settings' object for easy access.
