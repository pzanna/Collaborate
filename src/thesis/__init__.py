"""
Thesis Generation Module
=======================

This module provides comprehensive tools for generating thesis-quality literature reviews
from PRISMA systematic review data.

Components:
- generators/: Core thesis generation engines
- converters/: Format conversion utilities  
- config/: Configuration management
- templates/: Template system for consistent formatting

Author: GitHub Copilot for Paul Zanna
Date: July 23, 2025
"""

from .generators.enhanced_thesis_generator import EnhancedThesisGenerator
from .generators.basic_thesis_generator import ThesisGenerator  
from .converters.latex_converter import generate_latex_document

__version__ = "1.0.0"
__all__ = ["EnhancedThesisGenerator", "ThesisGenerator", "generate_latex_document"]
