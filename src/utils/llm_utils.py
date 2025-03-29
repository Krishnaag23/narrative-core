"""
Utility functions and classes for interacting with Large Language Models (LLMs),
primarily focusing on the OpenAI API. Handles client initialization, requests,
and basic error handling.
"""

import logging
import asyncio
from typing import Optional, Any, Dict
from openai import OpenAI, AsyncOpenAI, APIError, RateLimitError, APIConnectionError

from .config import settings 

logger = logging.getLogger(__name__)

class LLMwrapper:
    _sync_client: Optional[OpenAI] = None
    _async_client: Optional[AsyncOpenAI] = None

    @classmethod
    def _get_sync_client(cls) -> Optional[OpenAI]:
        """Initializes and returns the synchronous OpenAI client."""
        if cls._sync_client is None:
            if settings.OPENAI_API_KEY:
                try:
                    cls._sync_client = OpenAI(api_key=settings.OPENAI_API_KEY)
                    logger.info("Initialized synchronous OpenAI client.")
                except Exception as e:
                    logger.error(f"Failed to initialize synchronous OpenAI client: {e}", exc_info=True)
            else:
                logger.error("Cannot initialize synchronous OpenAI client: OPENAI_API_KEY not set.")
        return cls._sync_client

    @classmethod
    def _get_async_client(cls) -> Optional[AsyncOpenAI]:
        """Initializes and returns the asynchronous OpenAI client."""
        if cls._async_client is None:
            if settings.OPENAI_API_KEY:
                try:
                    cls._async_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                    logger.info("Initialized asynchronous OpenAI client.")
                except Exception as e:
                    logger.error(f"Failed to initialize asynchronous OpenAI client: {e}", exc_info=True)
            else:
                logger.error("Cannot initialize asynchronous OpenAI client: OPENAI_API_KEY not set.")
        return cls._async_client

    @classmethod
    def query_llm_sync(
        cls,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system_message: Optional[str] = None,
        **kwargs # Pass additional OpenAI params
    ) -> Optional[str]:
        """
        Sends a synchronous query to the configured LLM (OpenAI).

        Args:
            prompt: The main user prompt/query.
            model: Override the default model from settings.
            max_tokens: Override the default max tokens.
            temperature: Override the default temperature.
            system_message: An optional system message to guide the AI's behavior.
            **kwargs: Additional arguments for the OpenAI API completion create call.

        Returns:
            The LLM's response content as a string, or None on failure.
        """
        client = cls._get_sync_client()
        if not client:
            return None

        model_to_use = model or settings.LLM_MODEL_NAME
        max_tokens_to_use = max_tokens or settings.LLM_MAX_TOKENS_DEFAULT
        temp_to_use = temperature if temperature is not None else settings.LLM_TEMPERATURE_DEFAULT

        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        try:
            logger.debug(f"Sending SYNC query to {model_to_use} (Max Tokens: {max_tokens_to_use}, Temp: {temp_to_use})")
            completion = client.chat.completions.create(
                model=model_to_use,
                messages=messages,
                max_tokens=max_tokens_to_use,
                temperature=temp_to_use,
                **kwargs
            )
            response_content = completion.choices[0].message.content
            logger.debug(f"Received SYNC response (Tokens: {completion.usage.total_tokens if completion.usage else 'N/A'})")
            return response_content.strip() if response_content else None

        except RateLimitError as e:
            logger.error(f"OpenAI API rate limit exceeded: {e}. Check your usage plan and limits.")
        except APIConnectionError as e:
             logger.error(f"OpenAI API connection error: {e}. Check network connectivity.")
        except APIError as e:
            logger.error(f"OpenAI API returned an API Error: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during synchronous LLM query: {e}", exc_info=True)

        return None

    @classmethod
    async def query_llm_async(
        cls,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system_message: Optional[str] = None,
        **kwargs # Pass additional OpenAI params
    ) -> Optional[str]:
        """
        Sends an asynchronous query to the configured LLM (OpenAI).

        Args:
            prompt: The main user prompt/query.
            model: Override the default model from settings.
            max_tokens: Override the default max tokens.
            temperature: Override the default temperature.
            system_message: An optional system message to guide the AI's behavior.
            **kwargs: Additional arguments for the OpenAI API completion create call.


        Returns:
            The LLM's response content as a string, or None on failure.
        """
        client = cls._get_async_client()
        if not client:
            return None

        model_to_use = model or settings.LLM_MODEL_NAME
        max_tokens_to_use = max_tokens or settings.LLM_MAX_TOKENS_DEFAULT
        temp_to_use = temperature if temperature is not None else settings.LLM_TEMPERATURE_DEFAULT

        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        try:
            logger.debug(f"Sending ASYNC query to {model_to_use} (Max Tokens: {max_tokens_to_use}, Temp: {temp_to_use})")
            completion = await client.chat.completions.create(
                model=model_to_use,
                messages=messages,
                max_tokens=max_tokens_to_use,
                temperature=temp_to_use,
                **kwargs
            )
            response_content = completion.choices[0].message.content
            logger.debug(f"Received ASYNC response (Tokens: {completion.usage.total_tokens if completion.usage else 'N/A'})")
            return response_content.strip() if response_content else None

        except RateLimitError as e:
            logger.error(f"OpenAI API rate limit exceeded: {e}. Check your usage plan and limits.")
        except APIConnectionError as e:
             logger.error(f"OpenAI API connection error: {e}. Check network connectivity.")
        except APIError as e:
            logger.error(f"OpenAI API returned an API Error: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during asynchronous LLM query: {e}", exc_info=True)

        return None

