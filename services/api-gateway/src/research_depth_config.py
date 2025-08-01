"""
Research Depth Configuration for Academic Research Tasks.

This module defines the configuration for different academic research depths,
including resource allocation, source selection, and cost estimation.
"""

from typing import Dict, Any, List


# Research depth configurations mapped to academic levels
RESEARCH_DEPTH_CONFIG: Dict[str, Dict[str, Any]] = {
    "undergraduate": {
        "max_results": 25,
        "sources": ["semantic_scholar", "arxiv"],
        "quality_threshold": "basic",
        "synthesis_depth": "overview",
        "estimated_cost": 0.15,
        "estimated_duration": "3-8 minutes",
        "description": "Basic literature review suitable for undergraduate research projects",
        "search_strategy": "focused",
        "citation_depth": "primary"
    },
    "masters": {
        "max_results": 75,
        "sources": ["semantic_scholar", "arxiv", "pubmed"],
        "quality_threshold": "standard",
        "synthesis_depth": "analytical", 
        "estimated_cost": 0.35,
        "estimated_duration": "8-15 minutes",
        "description": "Comprehensive literature review for masters-level research",
        "search_strategy": "comprehensive",
        "citation_depth": "secondary"
    },
    "phd": {
        "max_results": 200,
        "sources": ["semantic_scholar", "arxiv", "pubmed", "crossref"],
        "quality_threshold": "rigorous",
        "synthesis_depth": "comprehensive",
        "estimated_cost": 0.75,
        "estimated_duration": "15-30 minutes", 
        "description": "Exhaustive literature review meeting PhD-level standards",
        "search_strategy": "exhaustive",
        "citation_depth": "tertiary"
    }
}


def get_depth_config(depth: str) -> Dict[str, Any]:
    """
    Get configuration for a specific research depth.
    
    Args:
        depth: Research depth level (undergraduate, masters, phd)
        
    Returns:
        Configuration dictionary for the specified depth
        
    Raises:
        ValueError: If depth is not supported
    """
    if depth not in RESEARCH_DEPTH_CONFIG:
        supported_depths = list(RESEARCH_DEPTH_CONFIG.keys())
        raise ValueError(f"Unsupported depth '{depth}'. Supported depths: {supported_depths}")
    
    return RESEARCH_DEPTH_CONFIG[depth].copy()


def get_all_depth_levels() -> List[str]:
    """Get all supported research depth levels."""
    return list(RESEARCH_DEPTH_CONFIG.keys())


def estimate_total_cost(depth: str, task_types: List[str]) -> float:
    """
    Estimate total cost for multiple research tasks at a given depth.
    
    Args:
        depth: Research depth level
        task_types: List of task types to estimate
        
    Returns:
        Total estimated cost in USD
    """
    base_cost = get_depth_config(depth)["estimated_cost"]
    
    # Task type multipliers
    task_multipliers = {
        "literature_review": 1.0,
        "systematic_review": 1.5,  # More rigorous, requires additional processing
        "meta_analysis": 2.0       # Most complex, includes statistical analysis
    }
    
    total_cost = 0.0
    for task_type in task_types:
        multiplier = task_multipliers.get(task_type, 1.0)
        total_cost += base_cost * multiplier
    
    return round(total_cost, 2)


def get_sources_for_depth(depth: str) -> List[str]:
    """Get the list of academic sources for a research depth."""
    return get_depth_config(depth)["sources"]


def get_max_results_for_depth(depth: str) -> int:
    """Get the maximum results for a research depth."""
    return get_depth_config(depth)["max_results"]
