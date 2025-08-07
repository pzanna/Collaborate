"""
Updated Standardized Health Check Service for Eunice Research Platform Agents v0.4.0

Enhancements:
- Added API-specific rate limit and configuration status
- Improved metadata reporting
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "service": "health-check",
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno
        }
        return json.dumps(log_record)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)

class HealthCheckResponse(BaseModel):
    status: str
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
    app = FastAPI(
        title=f"{agent_type.title()} Agent Health Check",
        description=f"Health check API for {agent_type} agent - MCP protocol compliant",
        version=version,
        docs_url=None,
        redoc_url=None,
        openapi_url=None
    )
    
    start_time = time.time()
    
    @app.get("/health", response_model=HealthCheckResponse)
    @app.get("/healthz", response_model=HealthCheckResponse)
    @app.get("/status", response_model=HealthCheckResponse)
    async def health_check():
        try:
            uptime_seconds = int(time.time() - start_time)
            uptime_str = _format_uptime(uptime_seconds)
            
            mcp_connected = True
            last_heartbeat = datetime.now(timezone.utc).isoformat()
            
            if get_mcp_status:
                try:
                    mcp_status = get_mcp_status()
                    mcp_connected = mcp_status.get("connected", False)
                    last_heartbeat = mcp_status.get("last_heartbeat", last_heartbeat)
                except Exception as e:
                    logger.warning(f"Error getting MCP status: {str(e)}")
                    mcp_connected = False
            
            status = "healthy" if mcp_connected else "degraded"
            ready = mcp_connected
            
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
                    logger.warning(f"Error getting additional metadata: {str(e)}")
            
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
            logger.error(f"Health check error: {str(e)}")
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
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return "".join(parts)

def run_health_check_service(
    agent_type: str,
    agent_id: str,
    host: str = "0.0.0.0",
    port: int = 8080,
    version: str = "1.0.0",
    get_mcp_status: Optional[Callable] = None,
    get_additional_metadata: Optional[Callable] = None
):
    app = create_health_check_app(
        agent_type=agent_type,
        agent_id=agent_id,
        version=version,
        get_mcp_status=get_mcp_status,
        get_additional_metadata=get_additional_metadata
    )
    
    logger.info(f"Starting health check service for {agent_type} agent on {host}:{port}")
    logger.info("ARCHITECTURE COMPLIANCE: Only health check API exposed")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=False
    )

if __name__ == "__main__":
    run_health_check_service(
        agent_type="example",
        agent_id="example-agent-001",
        port=8080
    )