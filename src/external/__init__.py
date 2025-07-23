"""
External Integration Package for Eunice Systematic Review System

This package provides comprehensive integration capabilities with external research databases,
citation management systems, and research tools for seamless workflow automation.

Components:
- database_connectors.py: API connectors for major research databases
- citation_managers.py: Integration with reference management systems
- research_tools.py: Compatibility with external research tools
- data_hub.py: Standardized data import/export functionality

Author: Eunice AI System
Date: July 2025
"""

from .database_connectors import (
    DatabaseConnector,
    PubMedConnector,
    CochraneConnector,
    EmbaseConnector,
    WebOfScienceConnector,
    ArxivConnector,
    ExternalSearchResult,
    DatabaseSearchQuery
)

from .citation_managers import (
    CitationManager,
    ZoteroIntegration,
    MendeleyConnector,
    EndNoteCompatibility,
    BibTeXManager,
    CitationFormat,
    ReferenceLibrary
)

from .research_tools import (
    ResearchToolIntegration,
    RIntegration,
    RevManCompatibility,
    ProsperoRegistration,
    GradeProIntegration,
    ToolInterface,
    AnalysisResult
)

from .data_hub import (
    DataExchangeHub,
    ImportEngine,
    ExportEngine,
    DataFormat,
    ExchangeFormat,
    DataValidator,
    FormatConverter
)

__all__ = [
    # Database connectors
    'DatabaseConnector',
    'PubMedConnector', 
    'CochraneConnector',
    'EmbaseConnector',
    'WebOfScienceConnector',
    'ArxivConnector',
    'ExternalSearchResult',
    'DatabaseSearchQuery',
    
    # Citation management
    'CitationManager',
    'ZoteroIntegration',
    'MendeleyConnector', 
    'EndNoteCompatibility',
    'BibTeXManager',
    'CitationFormat',
    'ReferenceLibrary',
    
    # Research tools
    'ResearchToolIntegration',
    'RIntegration',
    'RevManCompatibility',
    'ProsperoRegistration',
    'GradeProIntegration',
    'ToolInterface',
    'AnalysisResult',
    
    # Data exchange
    'DataExchangeHub',
    'ImportEngine',
    'ExportEngine',
    'DataFormat',
    'ExchangeFormat',
    'DataValidator',
    'FormatConverter'
]
