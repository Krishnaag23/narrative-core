"""
Manages loading and formatting of prompt templates stored in YAML files.
Allows easy updates to prompts without changing core code.
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional

from .config import settings 

logger = logging.getLogger(__name__)

class PromptManager:
    _instance = None
    _prompts: Dict[str, str] = {} # Store prompts as {key: template_string}

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(PromptManager, cls).__new__(cls)
            cls._instance._load_prompts() # Load prompts on first instantiation
        return cls._instance

    def _load_prompts(self):
        """Loads all YAML files from the configured prompt directory."""
        prompt_dir = settings.PROMPT_DIRECTORY
        if not os.path.isdir(prompt_dir):
            logger.error(f"Prompt directory not found or is not a directory: {prompt_dir}")
            return

        logger.info(f"Loading prompts from directory: {prompt_dir}")
        loaded_count = 0
        for filename in os.listdir(prompt_dir):
            if filename.endswith((".yaml", ".yml")):
                filepath = os.path.join(prompt_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                        if isinstance(data, dict):
                            for key, value in data.items():
                                if isinstance(value, str):
                                     if key in self._prompts:
                                         logger.warning(f"Duplicate prompt key '{key}' found in {filename}. Overwriting.")
                                     self._prompts[key] = value
                                     loaded_count += 1
                                else:
                                    logger.warning(f"Value for key '{key}' in {filename} is not a string. Skipping.")
                        else:
                            logger.warning(f"File {filename} does not contain a dictionary structure. Skipping.")
                except yaml.YAMLError as e:
                    logger.error(f"Error parsing YAML file {filename}: {e}", exc_info=True)
                except Exception as e:
                    logger.error(f"Error reading file {filename}: {e}", exc_info=True)

        logger.info(f"Successfully loaded {loaded_count} prompts from {len(self._prompts)} unique keys.")
        if not self._prompts:
             logger.warning(f"No prompts were loaded. Check the prompt directory ({prompt_dir}) and file contents.")


    def get_prompt(self, prompt_key: str, **kwargs) -> Optional[str]:
        """
        Retrieves a prompt template by key and formats it with provided arguments.

        Args:
            prompt_key: The unique key identifying the prompt (defined in YAML).
            **kwargs: Keyword arguments to format the prompt string.

        Returns:
            The formatted prompt string, or None if the key is not found.
        """
        template = self._prompts.get(prompt_key)
        if template is None:
            logger.error(f"Prompt key '{prompt_key}' not found.")
            return None

        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing keyword argument '{e}' for prompt key '{prompt_key}'. Provided: {kwargs.keys()}")
            return None
        except Exception as e:
            logger.error(f"Error formatting prompt '{prompt_key}': {e}", exc_info=True)
            return None

    def reload_prompts(self):
         """Clears existing prompts and reloads them from the directory."""
         logger.info("Reloading prompts...")
         self._prompts.clear()
         self._load_prompts()
