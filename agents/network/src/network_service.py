"""
Updated Network Agent Service for Eunice Research Platform v0.4.0

Enhancements:
- Integrated with ExternalAPIService
- Updated health check with API-specific metadata
- Enhanced configuration validation
"""

import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, ValidationError

from .health_check import create_health_check_app
from .external_api_service import ExternalAPIService
from .network_mcp_agent import NetworkMCPAgent

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "service": "network-agent",
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno
        }
        return json.dumps(log_record)

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)
for handler in logger.handlers:
    handler.setFormatter(JSONFormatter())

search_service: Optional[ExternalAPIService] = None
mcp_agent: Optional[NetworkMCPAgent] = None

class NetworkConfig(BaseModel):
    google_search: Optional[Dict[str, Any]] = None
    ai_models: List[Dict[str, Any]] = []
    literature_dbs: List[Dict[str, Any]] = []
    mcp: Dict[str, Any]
    cache_expiry: int = 3600

@asynccontextmanager
async def lifespan(app: FastAPI):
    global search_service, mcp_agent
    try:
        config_path = Path(__file__).parent.parent / "config" / "config.json"
        with open(config_path, 'r') as f:
            raw_config = json.load(f)
        
        raw_config["google_search"]["api_key"] = os.getenv("GOOGLE_API_KEY") or raw_config.get("google_search", {}).get("api_key")
        raw_config["google_search"]["search_engine_id"] = os.getenv("GOOGLE_SEARCH_ENGINE_ID") or raw_config.get("google_search", {}).get("search_engine_id")
        for ai_model in raw_config.get("ai_models", []):
            ai_model["api_key"] = os.getenv(f"{ai_model['provider'].upper()}_API_KEY") or ai_model.get("api_key")
        for db in raw_config.get("literature_dbs", []):
            db["api_key"] = os.getenv(f"{db['provider'].upper()}_API_KEY") or db.get("api_key")
        
        config = NetworkConfig(**raw_config)
        logger.info("Configuration loaded and validated successfully")
        
        search_service = ExternalAPIService(config.dict())
        mcp_agent = NetworkMCPAgent(config.dict())
        await mcp_agent.start()
        
        logger.info("Network Agent Service started successfully")
        yield
        
    except ValidationError as e:
        logger.error(f"Configuration validation failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to start Network Agent Service: {e}")
        raise
    finally:
        if mcp_agent:
            await mcp_agent.stop()
        if search_service:
            await search_service.stop()
        logger.info("Network Agent Service stopped")

def create_network_app() -> FastAPI:
    def get_mcp_status() -> Dict[str, Any]:
        if mcp_agent:
            return {"connected": mcp_agent.connected, "last_heartbeat": mcp_agent.last_heartbeat}
        return {"connected": False, "last_heartbeat": "unknown"}
    
    def get_additional_metadata() -> Dict[str, Any]:
        metadata = {
            "agent_type": "network",
            "protocol": "MCP-JSON-RPC",
            "api_compliance": "health_check_only"
        }
        if search_service:
            metadata["capabilities"] = search_service.get_capabilities()
            metadata["api_configured"] = search_service.is_api_configured()
            metadata["rate_limits"] = {key: handler.rate_limiter.get_status() for key, handler in search_service.handlers.items()}
        return metadata
    
    app = create_health_check_app(
        agent_type="network",
        agent_id="network-agent-001",
        version="1.0.0",
        get_mcp_status=get_mcp_status,
        get_additional_metadata=get_additional_metadata
    )
    
    app.router.lifespan_context = lifespan
    return app

def main():
    logger.info("Starting Network Agent Service (External APIs)")
    logger.info("ARCHITECTURE COMPLIANCE: Only health check API exposed")
    
    host = os.getenv("SERVICE_HOST", "0.0.0.0")
    port = int(os.getenv("SERVICE_PORT", "8004"))
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    
    app = create_network_app()
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
        access_log=False
    )

if __name__ == "__main__":
    main()