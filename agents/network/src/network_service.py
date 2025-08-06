"""
Network Agent Service for Eunice Research Platform.

This module provides a containerized Network Agent that specializes in:
- Google Custom Search Engine integration
- Web search and result parsing
- Search result normalization and filtering
- Integration with MCP protocol for task coordination

ARCHITECTURE COMPLIANCE:
- ONLY exposes health check API endpoint (/health)
- ALL business operations via MCP protocol exclusively
- NO direct HTTP/REST endpoints for business logic
"""

import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI

# Import the standardized health check service
from .health_check import create_health_check_app

# Import the Google search service and MCP agent
from .google_search_service import GoogleSearchService
from .network_mcp_agent import NetworkMCPAgent

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global service instances
search_service: Optional[GoogleSearchService] = None
mcp_agent: Optional[NetworkMCPAgent] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global search_service, mcp_agent
    
    # Load configuration
    config_path = Path(__file__).parent.parent / "config" / "config.json"
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        logger.info("Configuration loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        config = {}
    
    # Initialize services
    try:
        # Initialize Google Search Service
        search_service = GoogleSearchService(config)
        
        # Initialize MCP Agent
        mcp_agent = NetworkMCPAgent(config)
        await mcp_agent.start()
        
        logger.info("🚀 Network Agent Service (Google Search) started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start Network Agent Service: {e}")
        raise
    finally:
        # Cleanup
        if mcp_agent:
            await mcp_agent.stop()
        if search_service:
            await search_service.stop()
        logger.info("🛑 Network Agent Service stopped")


def create_network_app() -> FastAPI:
    """Create the Network Agent FastAPI application."""
    
    def get_mcp_status() -> Dict[str, Any]:
        """Get MCP connection status."""
        if mcp_agent:
            return {
                "connected": mcp_agent.is_connected(),
                "last_heartbeat": mcp_agent.get_last_heartbeat()
            }
        return {"connected": False, "last_heartbeat": "unknown"}
    
    def get_additional_metadata() -> Dict[str, Any]:
        """Get additional agent metadata."""
        metadata: Dict[str, Any] = {
            "agent_type": "network",
            "protocol": "MCP-JSON-RPC",
            "api_compliance": "health_check_only",
            "search_engine": "google_custom_search"
        }
        
        if search_service:
            metadata["search_capabilities"] = search_service.get_capabilities()
            metadata["api_configured"] = search_service.is_api_configured()
        
        return metadata
    
    # Create health check app
    app = create_health_check_app(
        agent_type="network",
        agent_id="network-agent-001",
        version="1.0.0",
        get_mcp_status=get_mcp_status,
        get_additional_metadata=get_additional_metadata
    )
    
    # Set lifespan
    app.router.lifespan_context = lifespan
    
    return app


def main():
    """Main entry point for the Network Agent Service."""
    logger.info("🔥 Starting Network Agent Service (Google Search)")
    logger.info("🚨 ARCHITECTURE COMPLIANCE: Only health check API exposed")
    logger.info("All business operations via MCP protocol exclusively")
    
    # Get configuration from environment
    host = os.getenv("SERVICE_HOST", "0.0.0.0")
    port = int(os.getenv("SERVICE_PORT", "8004"))
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    
    # Create the application
    app = create_network_app()
    
    # Run the service
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
        access_log=False  # Minimize logging for health checks
    )


if __name__ == "__main__":
    main()
