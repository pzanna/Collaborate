"""
Standardized Health Check Service for Eunice Research Platform Agents

This module provides a standardized health check API implementation that all agents
must use. This is the ONLY HTTP endpoint agents are permitted to expose.

Architecture Compliance:
- ONLY exposes /health endpoint
- All business operations via MCP protocol exclusively
- Returns standardized agent status information
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class HealthCheckResponse(BaseModel):
    """Standardized health check response model."""
    status: str  # "healthy", "unhealthy", "degraded"
    agent: str
    version: str
    uptime: str
    ready: bool
    mcp_connected: bool
    last_heartbeat: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None


def create_health_check_app(
    agent_type: str,
    agent_id: str,
    version: str = "1.0.0",
    get_mcp_status: Optional[Callable] = None,
    get_additional_metadata: Optional[Callable] = None
) -> FastAPI:
    """
    Create a standardized health check FastAPI application.
    
    Args:
        agent_type: Type of agent (e.g., "literature", "planning")
        agent_id: Unique agent identifier
        version: Agent version
        get_mcp_status: Function that returns MCP connection status
        get_additional_metadata: Function that returns additional metadata
        
    Returns:
        FastAPI application with ONLY health check endpoint
    """
    app = FastAPI(
        title=f"{agent_type.title()} Agent Health Check",
        description=f"Health check API for {agent_type} agent - MCP protocol compliant",
        version=version,
        # Disable docs endpoints to minimize attack surface
        docs_url=None,
        redoc_url=None,
        openapi_url=None
    )
    
    # Store start time for uptime calculation
    start_time = time.time()
    
    @app.get("/health", response_model=HealthCheckResponse)
    @app.get("/healthz", response_model=HealthCheckResponse)  # Kubernetes style
    @app.get("/status", response_model=HealthCheckResponse)   # Alternative endpoint
    async def health_check():
        """
        Health check endpoint - THE ONLY HTTP endpoint agents may expose.
        
        Returns standardized health information including:
        - Agent status and readiness
        - MCP connection status
        - Uptime information
        - Version and metadata
        """
        try:
            # Calculate uptime
            uptime_seconds = int(time.time() - start_time)
            uptime_str = _format_uptime(uptime_seconds)
            
            # Get MCP connection status
            mcp_connected = True
            last_heartbeat = datetime.now(timezone.utc).isoformat()
            
            if get_mcp_status:
                try:
                    mcp_status = get_mcp_status()
                    mcp_connected = mcp_status.get("connected", False)
                    last_heartbeat = mcp_status.get("last_heartbeat", last_heartbeat)
                except Exception as e:
                    logger.warning(f"Error getting MCP status: {e}")
                    mcp_connected = False
            
            # Determine overall status
            if mcp_connected:
                status = "healthy"
                ready = True
            else:
                status = "degraded"  # Still running but MCP disconnected
                ready = False
            
            # Get additional metadata
            metadata = {
                "agent_type": agent_type,
                "protocol": "MCP-JSON-RPC",
                "api_compliance": "health_check_only"
            }
            
            if get_additional_metadata:
                try:
                    additional = get_additional_metadata()
                    if isinstance(additional, dict):
                        metadata.update(additional)
                except Exception as e:
                    logger.warning(f"Error getting additional metadata: {e}")
            
            return HealthCheckResponse(
                status=status,
                agent=agent_id,
                version=version,
                uptime=uptime_str,
                ready=ready,
                mcp_connected=mcp_connected,
                last_heartbeat=last_heartbeat,
                timestamp=datetime.now(timezone.utc).isoformat(),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return HealthCheckResponse(
                status="unhealthy",
                agent=agent_id,
                version=version,
                uptime="unknown",
                ready=False,
                mcp_connected=False,
                last_heartbeat="unknown",
                timestamp=datetime.now(timezone.utc).isoformat(),
                metadata={"error": str(e)}
            )
    
    return app


def _format_uptime(seconds: int) -> str:
    """Format uptime seconds into human readable string."""
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if days > 0:
        return f"{days}d{hours}h{minutes}m{secs}s"
    elif hours > 0:
        return f"{hours}h{minutes}m{secs}s"
    elif minutes > 0:
        return f"{minutes}m{secs}s"
    else:
        return f"{secs}s"


def run_health_check_service(
    agent_type: str,
    agent_id: str,
    host: str = "0.0.0.0",
    port: int = 8080,
    version: str = "1.0.0",
    get_mcp_status: Optional[Callable] = None,
    get_additional_metadata: Optional[Callable] = None
):
    """
    Run the health check service.
    
    This is a utility function to quickly start a health check service
    for agents that don't need additional FastAPI configuration.
    """
    app = create_health_check_app(
        agent_type=agent_type,
        agent_id=agent_id,
        version=version,
        get_mcp_status=get_mcp_status,
        get_additional_metadata=get_additional_metadata
    )
    
    logger.info(f"Starting health check service for {agent_type} agent on {host}:{port}")
    logger.info("🚨 ARCHITECTURE COMPLIANCE: Only health check API exposed")
    logger.info("All business operations via MCP protocol exclusively")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=False  # Minimize logging for health checks
    )


if __name__ == "__main__":
    # Example usage for testing
    run_health_check_service(
        agent_type="example",
        agent_id="example-agent-001",
        port=8080
    )
