"""Data models for academic search API endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

SourceType = Literal["pubmed", "arxiv", "semantic_scholar"]


class AcademicSearchRequest(BaseModel):
    """Request model for comprehensive academic search."""

    query: str = Field(..., description="Search query", min_length=1, max_length=500)
    max_results_per_source: int = Field(
        default=10, description="Maximum results per source", ge=1, le=50
    )
    include_pubmed: bool = Field(default=True, description="Include PubMed in search")
    include_arxiv: bool = Field(default=True, description="Include arXiv in search")
    include_semantic_scholar: bool = Field(
        default=True, description="Include Semantic Scholar in search"
    )
    use_cache: bool = Field(default=True, description="Use cached results if available")


class AcademicPaper(BaseModel):
    """Model for individual academic paper result."""

    title: str = Field(..., description="Paper title")
    url: str = Field(default="", description="URL to the paper")
    content: str = Field(default="", description="Paper description / summary")
    source: str = Field(
        ..., description="Source database (pubmed, arxiv, semantic_scholar)"
    )
    type: str = Field(default="academic_paper", description="Result type")
    link_type: str = Field(default="", description="Type of link (doi, pdf, etc.)")
    relevance_score: int = Field(default=0, description="Relevance score")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class SourceResults(BaseModel):
    """Results from a specific source."""

    source: SourceType = Field(..., description="Source database name")
    count: int = Field(..., description="Number of results from this source")
    papers: List[AcademicPaper] = Field(
        ..., description="List of papers from this source"
    )


class AcademicSearchResponse(BaseModel):
    """Response model for comprehensive academic search."""

    query: str = Field(..., description="Original search query")
    total_results: int = Field(
        ..., description="Total number of results across all sources"
    )
    sources_searched: List[str] = Field(
        ..., description="List of sources that were searched"
    )
    sources_with_results: List[str] = Field(
        ..., description="List of sources that returned results"
    )
    results_by_source: Dict[str, List[AcademicPaper]] = Field(
        ..., description="Results organized by source"
    )
    search_timestamp: str = Field(
        ..., description="ISO timestamp of when search was performed"
    )
    cache_used: bool = Field(..., description="Whether cached results were used")

    class Config:
        """TODO: Add class docstring for Config."""

        json_schema_extra = {
            "example": {
                "query": "machine learning neural networks",
                "total_results": 30,
                "sources_searched": ["pubmed", "arxiv", "semantic_scholar"],
                "sources_with_results": ["pubmed", "arxiv", "semantic_scholar"],
                "results_by_source": {
                    "pubmed": [
                        {
                            "title": "Deep Neural Networks for Medical Image Analysis",
                            "url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
                            "content": (
                                "Academic paper: Deep Neural Networks for Medical Image Analysis | "
                                "Authors: Smith, J., Doe, A. | Journal: Nature Medicine | "
                                "Published: 2023-01-15 | Citations: 150"
                            ),
                            "source": "pubmed",
                            "type": "academic_paper",
                            "link_type": "pubmed",
                            "relevance_score": 10,
                            "metadata": {
                                "authors": ["Smith, J.", "Doe, A."],
                                "journal": "Nature Medicine",
                                "publication_date": "2023 - 01 - 15T00:00:00Z",
                                "pmid": "12345678",
                                "citation_count": 150,
                            },
                        }
                    ]
                },
                "search_timestamp": "2025 - 01 - 20T10:30:00Z",
                "cache_used": False,
            }
        }


class AcademicSearchError(BaseModel):
    """Error response model for academic search API."""

    success: bool = Field(False, description="Always false for errors")
    error: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class AcademicSourceInfo(BaseModel):
    """Information about an academic search source."""

    name: str = Field(..., description="Display name of the source")
    description: str = Field(..., description="Brief description of the source")
    url: str = Field(..., description="URL of the source")
    fields: List[str] = Field(..., description="Available metadata fields")
    specialties: List[str] = Field(..., description="Subject specialties")
    api_documentation: Optional[str] = Field(None, description="API documentation URL")
    rate_limit: Optional[str] = Field(None, description="Rate limiting information")
    ssl_enabled: bool = Field(..., description="Whether SSL is enabled")
    features: List[str] = Field(..., description="Special features of this source")


class AcademicSourcesResponse(BaseModel):
    """Response model for academic sources information."""

    sources: Dict[str, AcademicSourceInfo] = Field(
        ..., description="Information about each source"
    )
    total_sources: int = Field(..., description="Total number of available sources")
    ssl_verification: str = Field(..., description="SSL verification status")
    last_updated: str = Field(..., description="Last update timestamp")

    class Config:
        """TODO: Add class docstring for Config."""

        json_schema_extra = {
            "example": {
                "sources": {
                    "pubmed": {
                        "name": "PubMed",
                        "description": "MEDLINE / PubMed database of biomedical literature",
                        "url": "https://pubmed.ncbi.nlm.nih.gov/",
                        "fields": [
                            "title",
                            "abstract",
                            "authors",
                            "journal",
                            "pub_date",
                            "pmid",
                            "doi",
                        ],
                        "specialties": ["medicine", "biology", "life_sciences"],
                        "api_documentation": "https://www.ncbi.nlm.nih.gov / books / NBK25497/",
                        "rate_limit": "3 requests per second",
                        "ssl_enabled": True,
                        "features": [
                            "mesh_terms",
                            "publication_types",
                            "clinical_trials",
                        ],
                    }
                },
                "total_sources": 3,
                "ssl_verification": "enabled",
                "last_updated": "2025 - 07 - 24T12:00:00.000000Z",
            }
        }
