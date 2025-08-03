"""
Data models for literature search functionality.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class SearchQuery:
    """Search query data model for literature search requests."""
    lit_review_id: str
    plan_id: str = ""
    research_plan: str = ""
    query: str = ""
    filters: Dict[str, Any] = field(default_factory=dict)
    sources: List[str] = field(default_factory=list)
    max_results: int = 50
    search_depth: str = "standard"


@dataclass
class SearchReport:
    """Search report data model for literature search results."""
    lit_review_id: str
    total_fetched: int
    total_unique: int
    per_source_counts: Dict[str, int]
    start_time: datetime
    end_time: datetime
    errors: List[str] = field(default_factory=list)
    records: List[Dict[str, Any]] = field(default_factory=list)
