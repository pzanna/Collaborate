"""
Database Layer for Eunice Research Platform

This module provides the centralized database access layer following the
Architecture.md North Star design. It encapsulates all database operations
and provides a clean API that shields other components from schema changes.

Structure:
- core/: Core database manager and schema definitions
- cache/: Caching functionality for performance optimization  
- connectors/: External database connectors (PubMed, Semantic Scholar, etc.)
- specialized/: Specialized database extensions (systematic reviews, etc.)
- utils/: Database utility functions and validators
"""

# Main exports for backward compatibility and ease of use
from .core.manager import HierarchicalDatabaseManager
from .cache.academic_cache import AcademicCacheManager
from .specialized.systematic_review import SystematicReviewDatabase

# Maintain backward compatibility
from .core.manager import HierarchicalDatabaseManager as HierarchicalDatabaseManager

__all__ = [
    "HierarchicalDatabaseManager",
    "AcademicCacheManager", 
    "SystematicReviewDatabase"
]

# Version information
__version__ = "2.0.0"
__author__ = "Eunice AI System"
