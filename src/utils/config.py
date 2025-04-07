"""
Handles application configuration using Pydantic BaseSettings.
Loads settings from environment variables and .env files.
Provides a singleton 'settings' object for easy access.
"""

import os
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

logger = logging.getLogger(__name__)

# Define the path to the root of the project (adjust if needed)
# Assuming this file is in src/utils/, root is two levels up.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_ENV_FILE = os.path.join(PROJECT_ROOT, '.env')
DEFAULT_PROMPT_DIR = os.path.join(PROJECT_ROOT, 'src', 'config', 'prompts')
DEFAULT_CHROMA_PATH = os.path.join(PROJECT_ROOT, '.chroma_db_persistence')


class Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""
    # LLM Configuration
    OPENAI_API_KEY: Optional[str] = None
    LLM_MODEL_NAME: str = "gpt-4o" # Default model
    LLM_MAX_TOKENS_DEFAULT: int = 150
    LLM_TEMPERATURE_DEFAULT: float = 0.7
    DEMO_VERBOSE_CONTEXT: bool = True

    # Vector Store Configuration
    VECTOR_DB_PATH: str = DEFAULT_CHROMA_PATH
    # Specify embedding model if not relying on Chroma's default
    # EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"

    # Prompt Configuration
    PROMPT_DIRECTORY: str = DEFAULT_PROMPT_DIR

    # Add other configurations as needed
    LOG_LEVEL: str = "INFO"

    # Pydantic-settings configuration
    model_config = SettingsConfigDict(
        env_file=DEFAULT_ENV_FILE,  # Load from .env file
        env_file_encoding='utf-8',
        extra='ignore'  # Ignore extra fields not defined in the model
    )

# --- Environment Variable Loading and Validation ---
try:
    settings = Settings()
    # Basic validation
    if not settings.OPENAI_API_KEY:
        logger.warning(f"OPENAI_API_KEY not found in environment variables or {DEFAULT_ENV_FILE}. LLM calls will fail.")
        # raise ValueError("OPENAI_API_KEY is not set. Please set it in your environment or .env file.")

    # Ensure directories exist
    if not os.path.exists(settings.PROMPT_DIRECTORY):
         logger.warning(f"Prompt directory not found: {settings.PROMPT_DIRECTORY}. Creating it.")
         os.makedirs(settings.PROMPT_DIRECTORY, exist_ok=True)
         # You might want to add default prompt files here if they don't exist

    # Chroma path will be created by ChromaDB if it doesn't exist, but we can log it
    logger.info(f"Using ChromaDB persistence path: {settings.VECTOR_DB_PATH}")


    # Set log level globally based on config
    logging.basicConfig(level=settings.LOG_LEVEL.upper(),
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info(f"Log level set to: {settings.LOG_LEVEL.upper()}")


except Exception as e:
    logger.error(f"FATAL: Error loading application settings: {e}", exc_info=True)
    # Provide default settings object on failure? Or raise? Raising is safer.
    raise RuntimeError(f"Failed to load settings: {e}")

