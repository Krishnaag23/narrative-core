"""
Utilities Module for NarrativeCore.

Provides centralized access to common functionalities like configuration,
LLM interaction, vector store operations, and prompt management.
"""

import logging

logger = logging.getLogger(__name__)
logger.info("Initializing NarrativeCore Utilities Module...")

# Expose key components for easy import
from .config import settings
from .llm_utils import LLMwrapper
from .vector_store_utils import VectorStoreInterface, QueryResult, GetResult, Metadata
from .prompt_manager import PromptManager

__all__ = [
    "settings",
    "LLMwrapper",
    "VectorStoreInterface",
    "PromptManager",
    "QueryResult",
    "GetResult",
    "Metadata",
]

# Perform a basic check or initialization if needed upon module import
try:
    # Ensure singletons are instantiated (they handle their own initialization logic)
    prompt_manager_instance = PromptManager()
    vector_store_instance = VectorStoreInterface()
    # LLMUtils uses class methods, no instance needed here. Client init is lazy.
    logger.info("Utilities (PromptManager, VectorStoreInterface) initialized/accessed.")
except Exception as e:
    logger.critical(f"FATAL error during utility module initialization: {e}", exc_info=True)
    #TODO: Depending on security raise or return 
    raise