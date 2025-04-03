"""
Memory Management Module
=========================
Handles storage, retrieval, summarization, and optimization of narrative memory
across different scopes (character, plot, world, knowledge graph).
"""
import logging

logger = logging.getLogger(__name__)
logger.info("Initializing Memory Management Module...")

# Assuming character memory is primarily handled within character_system now
# Re-exporting for potential unified access if needed, but focus on new components here.
# from ..character_system import CharacterMemory # If needed

from .character_memory_manager import CharacterMemoryManager
from .plot_memory_manager import PlotMemoryManager
from .theme_memory_manager import ThemeMemoryManager
from .world_memory_manager import WorldMemoryManager
from .memory_retrieval import MemoryRetrieval
from .episodic_memory import EpisodicMemory
from .memory_optimiser import MemoryOptimizer


from .hierarchical_summarization import HierarchicalSummarizer
from .knowledge_graph import KnowledgeGraphManager
from .context_optimiser import ContextOptimizer
# Add back Plot/Theme/World managers if they offer distinct functionality beyond KG/VectorStore
# from .plot_memory_manager import PlotMemoryManager
# from .theme_memory_manager import ThemeMemoryManager
# from .world_memory_manager import WorldMemoryManager

# Keep Episodic and MemoryOptimizer if they were intended additions
# from .episodic_memory import EpisodicMemory
# from .memory_optimiser import MemoryOptimizer

# Keep VectorStoreManager if it's the central ChromaDB access point for memory
# from .vector_store_manager import VectorStoreManager

# Import the GraphDB interface/implementation from utils
from ..utils.graph_database import GraphDB, NetworkXGraphDB

__all__ = [
    "HierarchicalSummarizer",
    "KnowledgeGraphManager",
    "ContextOptimizer",
    "GraphDB", # Expose the graph DB interface/implementation
    "CharacterMemoryManager",
    "ThemeMemoryManager",
    "PlotMemoryManager",
    "WorldMemoryManager",
    "MemoryRetrieval",
    "EpisodicMemory",
    "MemoryOptimizer",
    # Add back other specific managers if implemented/needed
    # "PlotMemoryManager",
    # "ThemeMemoryManager",
    # "WorldMemoryManager",
    # "VectorStoreManager", # Usually accessed via utils.VectorStoreInterface now
    # "EpisodicMemory",
    # "MemoryOptimizer",
]