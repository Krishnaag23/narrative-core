"""
Output Formatter Module for NarrativeCore.

Provides tools to convert generated story scripts into various
output formats suitable for consumption (e.g., audio production, API display).
"""
import logging

logger = logging.getLogger(__name__)
logger.info("Initializing Output Formatter Module...")

from .audio_adapter import AudioAdapter, AudioFormat
from .metadate_generator import MetadataGenerator

__all__ = [
    "AudioAdapter",
    "AudioFormat",
    "MetadataGenerator",
]