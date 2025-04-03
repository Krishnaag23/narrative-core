"""
Quality Control Module for NarrativeCore.

Provides tools to assess the coherence, consistency, and cultural validity
of generated story content.
"""

import logging

logger = logging.getLogger(__name__)
logger.info("Initializing Quality Control Module...")

from .quality_report import QualityReport, Issue, Severity
from .coherence_checker import CoherenceChecker
from .cultural_validator import CulturalValidator
from .qc_facade import QualityControlFacade

__all__ = [
    "QualityReport",
    "Issue",
    "Severity",
    "CoherenceChecker",
    "CulturalValidator",
    "QualityControlFacade",
]