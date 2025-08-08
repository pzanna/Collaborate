"""
Research Manager Service for Eunice Research Platform.

This module provides a containerized Research Manager that coordinates:
- Multi-agent research task orchestration
- Research workflow management
- Cost estimation and approval
- Task delegation and monitoring
- Progress tracking and reporting

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
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI

# Import the modular research manager components
from research_manager import ResearchManagerService

# Import watchfiles with fallback
try:
    from watchfiles import awatch
    WATCHFILES_AVAILABLE = True
except ImportError as e:
    awatch = None  # type: ignore
    WATCHFILES_AVAILABLE = False

# Import the standardized health check service
sys.path.append(str(Path(__file__).parent.parent))
from research_manager.health_check import create_health_check_app

# Configure logging with namespace
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("research_manager.service")


# Global service instance
research_manager_service: Optional[ResearchManagerService] = None


def get_mcp_status() -> Dict[str, Any]:
    """Get MCP connection status for health check."""
    if research_manager_service:
        return {
            "connected": research_manager_service.mcp_communicator.mcp_connected,
            "last_heartbeat": datetime.now().isoformat()
        }
    return {"connected": False, "last_heartbeat": "never"}


def get_additional_metadata() -> Dict[str, Any]:
    """Get additional metadata for health check."""
    if research_manager_service:
        return {
            "capabilities": research_manager_service.capabilities,
            "active_tasks": len(research_manager_service.active_contexts),
            "max_concurrent_tasks": research_manager_service.max_concurrent_tasks,
            "watchfiles_available": WATCHFILES_AVAILABLE,
            "agent_id": research_manager_service.agent_id
        }
    return {"watchfiles_available": WATCHFILES_AVAILABLE}


# Create health check only FastAPI application
app = create_health_check_app(
    agent_type="research_manager",
    agent_id="research-manager-agent",
    version="1.0.0",
    get_mcp_status=get_mcp_status,
    get_additional_metadata=get_additional_metadata
)


async def main():
    """Main entry point for the research manager agent service."""
    global research_manager_service
    
    try:
        # Load configuration
        config_path = Path("/app/config/config.json")
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
        else:
            config = {
                "service_host": "0.0.0.0",
                "service_port": 8002,
                "mcp_server_url": "ws://mcp-server:9000",
                "max_concurrent_tasks": 5,
                "task_timeout": 600
            }
        
        # Initialize service
        research_manager_service = ResearchManagerService(config)
        
        # Get host and port from environment variables
        service_host = os.getenv("SERVICE_HOST", "0.0.0.0")
        service_port = int(os.getenv("SERVICE_PORT", "8002"))
        
        # Start FastAPI health check server in background
        config_uvicorn = uvicorn.Config(
            app,
            host=service_host,
            port=service_port,
            log_level="info"
        )
        server = uvicorn.Server(config_uvicorn)
        
        logger.info("🚨 ARCHITECTURE COMPLIANCE: Research Manager Agent")
        logger.info("✅ ONLY health check API exposed")
        logger.info("✅ All business operations via MCP protocol exclusively")
        
        # Start server and MCP service concurrently
        await asyncio.gather(
            server.serve(),
            research_manager_service.start()
        )
        
    except KeyboardInterrupt:
        logger.info("Research manager agent shutdown requested")
    except Exception as e:
        logger.error(f"Research manager agent failed: {e}")
        sys.exit(1)
    finally:
        if research_manager_service:
            await research_manager_service.stop()


if __name__ == "__main__":
    asyncio.run(main())
