"""
Literature Search Package

This package provides modular literature search functionality for the Eunice Research Platform.
"""

from .models import SearchQuery, SearchReport
from .service import LiteratureSearchService

__all__ = ['SearchQuery', 'SearchReport', 'LiteratureSearchService']
