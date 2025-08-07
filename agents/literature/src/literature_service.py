"""
Literature Search Agent Service for Eunice Research Platform.

This module provides a containerized Literature Search Agent that specializes in:
- Academic literature discovery and collection
- Multi-source bibliographic search (PubMed, arXiv, Semantic Scholar)
- Result normalization and deduplication
- Integration with MCP protocol for task coordination

ARCHITECTURE COMPLIANCE:
- ONLY exposes health check API endpoint (/health)
- ALL business operations via MCP protocol exclusively
- NO direct HTTP/REST endpoints for business logic
"""

import asyncio
import json
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI

# Import the standardized health check service
sys.path.append(str(Path(__file__).parent.parent))
from literature_search.health_check import create_health_check_app

# Import the refactored literature search service
from literature_search import LiteratureSearchService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global service instance
literature_service: Optional[LiteratureSearchService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global literature_service
    
    # Load configuration
    config_path = Path("/app/config/config.json")
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
    else:
        config = {
            "service_host": "0.0.0.0",
            "service_port": 8003,
            "mcp_server_url": "ws://mcp-server:9000",
            "max_concurrent_searches": 3,
            "search_timeout": 300,
            "rate_limit_delay": 1.0
        }
    
    # Start service
    literature_service = LiteratureSearchService(config)
    await literature_service.start()
    
    try:
        yield
    finally:
        # Cleanup
        if literature_service:
            await literature_service.stop()


def get_mcp_status() -> Dict[str, Any]:
    """Get MCP connection status for health check."""
    if literature_service:
        return {
            "connected": literature_service.mcp_connected,
            "last_heartbeat": datetime.now().isoformat()
        }
    return {"connected": False, "last_heartbeat": "never"}


def get_additional_metadata() -> Dict[str, Any]:
    """Get additional metadata for health check."""
    if literature_service:
        return {
            "capabilities": [
                "search_academic_papers",
                "search_literature", 
                "normalize_records",
                "deduplicate_results",
                "multi_source_search",
                "bibliographic_search"
            ],
            "supported_sources": ["semantic_scholar", "pubmed", "arxiv", "crossref", "openalex"],
            "api_integrations": {
                "semantic_scholar": "AI-powered academic search with rich metadata",
                "pubmed": "Medical and life sciences literature",
                "arxiv": "Preprint server for physics, mathematics, computer science",
                "crossref": "DOI-based academic publication metadata",
                "core": "Open access research papers aggregator"
            },
            "features": [
                "multi_source_parallel_search",
                "intelligent_deduplication",
                "format_normalization", 
                "rate_limiting",
                "error_recovery",
                "mcp_protocol_integration",
                "ai_search_optimization",
                "caching_system"
            ]
        }
    return {}


# Create health check only FastAPI application
app = create_health_check_app(
    agent_type="literature",
    agent_id="literature-search-agent",
    version="1.0.0",
    get_mcp_status=get_mcp_status,
    get_additional_metadata=get_additional_metadata
)

# Set lifespan for service management
app.router.lifespan_context = lifespan


if __name__ == "__main__":
    logger.info("🚨 ARCHITECTURE COMPLIANCE: Literature Search Agent")
    logger.info("✅ ONLY health check API exposed")
    logger.info("✅ All business operations via MCP protocol exclusively")
    logger.info("✅ Modular architecture with separated concerns")
    
    uvicorn.run(
        "literature_service:app",
        host="0.0.0.0",
        port=8003,
        log_level="info"
    )
