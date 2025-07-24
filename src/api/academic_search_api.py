"""API endpoints for academic search functionality."""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from src.agents.literature_agent import LiteratureAgent
from src.config.config_manager import ConfigManager
from src.models.academic_search_models import (
    AcademicPaper,
    AcademicSearchError,
    AcademicSearchRequest,
    AcademicSearchResponse,
    AcademicSourceInfo,
    AcademicSourcesResponse,
)

# Create router for academic search endpoints
v2_academic_router = APIRouter(prefix="/api / v2 / academic", tags=["v2 - academic - search"])

# Global instances
_config_manager: Optional[ConfigManager] = None
_literature_agent: Optional[LiteratureAgent] = None


async def get_literature_agent() -> LiteratureAgent:
    """Dependency to get or create a literature agent instance."""
    global _config_manager, _literature_agent

    try:
        if _config_manager is None:
            _config_manager = ConfigManager()

        if _literature_agent is None:
            _literature_agent = LiteratureAgent(_config_manager)

        return _literature_agent

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to initialize Literature Agent: {str(e)}")


def convert_results_to_response_format(
    query: str, results_by_source: Dict[str, List[Dict[str, Any]]], cache_used: bool = False
) -> AcademicSearchResponse:
    """Convert LiteratureAgent results to API response format."""

    # Convert individual results to AcademicPaper models
    formatted_results = {}
    total_results = 0
    sources_with_results = []

    for source, results in results_by_source.items():
        if results:
            sources_with_results.append(source)
            formatted_papers = []

            for result in results:
                paper = AcademicPaper(
                    title=result.get("title", ""),
                    url=result.get("url", ""),
                    content=result.get("content", ""),
                    source=result.get("source", source),
                    type=result.get("type", "academic_paper"),
                    link_type=result.get("link_type", ""),
                    relevance_score=result.get("relevance_score", 0),
                    metadata=result.get("metadata", {}),
                )
                formatted_papers.append(paper)

            formatted_results[source] = formatted_papers
            total_results += len(results)
        else:
            formatted_results[source] = []

    return AcademicSearchResponse(
        query=query,
        total_results=total_results,
        sources_searched=list(results_by_source.keys()),
        sources_with_results=sources_with_results,
        results_by_source=formatted_results,
        search_timestamp=datetime.utcnow().isoformat() + "Z",
        cache_used=cache_used,
    )


@v2_academic_router.post("/search", response_model=AcademicSearchResponse)
async def comprehensive_academic_search(
    request: AcademicSearchRequest, literature_agent: LiteratureAgent = Depends(get_literature_agent)
):
    """
    Perform comprehensive academic search across multiple databases.

    This endpoint searches PubMed, arXiv, and Semantic Scholar for academic papers
    based on the provided query. Results include rich metadata such as authors,
    publication dates, citation counts, and abstracts.

    **Features:**
    - Multi - database search (PubMed, arXiv, Semantic Scholar)
    - Configurable result limits per source
    - Caching support for improved performance
    - Rich metadata extraction
    - SSL - secured connections to all databases

    **Usage Examples:**
    ```python
    # Basic search
    {
        "query": "machine learning neural networks",
        "max_results_per_source": 10
    }

    # Search specific sources only
    {
        "query": "quantum computing",
        "max_results_per_source": 5,
        "include_pubmed": true,
        "include_arxiv": true,
        "include_semantic_scholar": false
    }
    ```
    """
    try:
        # Validate that at least one source is selected
        if not (request.include_pubmed or request.include_arxiv or request.include_semantic_scholar):
            raise HTTPException(status_code=400, detail="At least one search source must be enabled")

        # Execute the comprehensive academic search
        results_by_source = await literature_agent.comprehensive_academic_search(
            query=request.query,
            max_results_per_source=request.max_results_per_source,
            include_pubmed=request.include_pubmed,
            include_arxiv=request.include_arxiv,
            include_semantic_scholar=request.include_semantic_scholar,
            use_cache=request.use_cache,
        )

        # Convert to response format
        response = convert_results_to_response_format(
            query=request.query, results_by_source=results_by_source, cache_used=request.use_cache
        )

        return response

    except ValueError as e:
        # Handle validation errors
        error_response = AcademicSearchError(
            error="Invalid search parameters",
            details=str(e),
            query=request.query,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        raise HTTPException(status_code=400, detail=error_response.dict())

    except asyncio.TimeoutError:
        # Handle timeout errors
        error_response = AcademicSearchError(
            error="Search timeout",
            details="The search request timed out. Please try again with a more specific query.",
            query=request.query,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        raise HTTPException(status_code=408, detail=error_response.dict())

    except Exception as e:
        # Handle unexpected errors
        error_response = AcademicSearchError(
            error="Internal server error",
            details=f"An unexpected error occurred: {str(e)}",
            query=request.query,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        raise HTTPException(status_code=500, detail=error_response.dict())


@v2_academic_router.get("/search", response_model=AcademicSearchResponse)
async def comprehensive_academic_search_get(
    query: str = Query(..., description="Search query", min_length=1, max_length=500),
    max_results_per_source: int = Query(default=10, description="Maximum results per source", ge=1, le=50),
    include_pubmed: bool = Query(default=True, description="Include PubMed in search"),
    include_arxiv: bool = Query(default=True, description="Include arXiv in search"),
    include_semantic_scholar: bool = Query(default=True, description="Include Semantic Scholar in search"),
    use_cache: bool = Query(default=True, description="Use cached results if available"),
    literature_agent: LiteratureAgent = Depends(get_literature_agent),
):
    """
    GET version of comprehensive academic search for simple queries.

    This is a convenience endpoint that allows simple searches using URL parameters
    instead of a JSON request body. For more complex searches, use the POST endpoint.

    **Example:**
    ```
    GET /api / v1 / academic / search?query=machine % 20learning&max_results_per_source=5
    ```
    """
    # Create request object from query parameters
    request = AcademicSearchRequest(
        query=query,
        max_results_per_source=max_results_per_source,
        include_pubmed=include_pubmed,
        include_arxiv=include_arxiv,
        include_semantic_scholar=include_semantic_scholar,
        use_cache=use_cache,
    )

    # Use the same logic as the POST endpoint
    return await comprehensive_academic_search(request, literature_agent)


@v2_academic_router.get("/sources", response_model=AcademicSourcesResponse)
async def get_available_sources():
    """
    Get information about available academic search sources.

    Returns details about each supported database including capabilities,
    rate limits, and current status.
    """
    sources_info = {
        "pubmed": AcademicSourceInfo(
            name="PubMed",
            description="Biomedical literature database maintained by NCBI",
            url="https://pubmed.ncbi.nlm.nih.gov/",
            fields=["title", "abstract", "authors", "journal", "publication_date", "pmid", "doi"],
            specialties=["medicine", "biology", "life_sciences", "biomedical_research"],
            api_documentation="https://www.ncbi.nlm.nih.gov / books / NBK25501/",
            rate_limit="3 requests per second",
            ssl_enabled=True,
            features=["mesh_terms", "clinical_trials", "free_full_text"],
        ),
        "arxiv": AcademicSourceInfo(
            name="arXiv",
            description="Open - access repository of electronic preprints",
            url="https://arxiv.org/",
            fields=["title", "abstract", "authors", "categories", "publication_date", "arxiv_id"],
            specialties=["physics", "mathematics", "computer_science", "quantitative_biology"],
            api_documentation="https://arxiv.org / help / api/",
            rate_limit="1 request per 3 seconds",
            ssl_enabled=True,
            features=["preprints", "open_access", "full_text_available"],
        ),
        "semantic_scholar": AcademicSourceInfo(
            name="Semantic Scholar",
            description="AI - powered research tool for scientific literature",
            url="https://www.semanticscholar.org/",
            fields=["title", "abstract", "authors", "venue", "year", "citation_count", "doi", "pdf_url"],
            specialties=["computer_science", "medicine", "biology", "multidisciplinary"],
            api_documentation="https://api.semanticscholar.org/",
            rate_limit="1 request per second (higher with API key)",
            ssl_enabled=True,
            features=["citation_tracking", "open_access_detection", "paper_recommendations"],
        ),
    }

    return AcademicSourcesResponse(
        sources=sources_info,
        total_sources=len(sources_info),
        ssl_verification="enabled",
        last_updated=datetime.utcnow().isoformat() + "Z",
    )


@v2_academic_router.get("/health", response_model=Dict[str, Any])
async def health_check(literature_agent: LiteratureAgent = Depends(get_literature_agent)):
    """
    Health check endpoint for academic search service.

    Returns the status of the service and its dependencies.
    """
    try:
        # Basic health check - ensure agent is available
        agent_status = "healthy" if literature_agent else "unavailable"

        return {
            "status": "healthy",
            "service": "academic_search_api",
            "version": "1.0.0",
            "literature_agent": agent_status,
            "ssl_verification": "enabled",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "sources": {"pubmed": "available", "arxiv": "available", "semantic_scholar": "available"},
        }

    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e), "timestamp": datetime.utcnow().isoformat() + "Z"},
        )
