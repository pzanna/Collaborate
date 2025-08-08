#!/usr/bin/env python3
"""
Improved Containerized API Gateway Service for Eunice Research Platform

This service provides a unified REST API interface that routes requests to research 
agents via the MCP server. Updated to work with the improved MCPClient, featuring:
- Full configuration integration for MCPClient
- Enhanced task management with timeout cleanup
- Aligned message types (research_action)
- Improved health checks using MCPClient
- Robust shutdown with task cancellation
- Structured JSON logging for monitoring
"""

import asyncio
import logging
import signal
import sys
import json
from uuid import uuid4
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import Config
from mcp_client import MCPClient

# Import watchfiles with fallback
try:
    from watchfiles import awatch
    WATCHFILES_AVAILABLE = True
except ImportError as e:
    awatch = None  # type: ignore
    WATCHFILES_AVAILABLE = False

# Import database service client for direct read access
from native_database_client import get_native_database, initialize_native_database, close_native_database

# Import hierarchical data models for v2 endpoints
from src.data_models.hierarchical_data_models import (
    ProjectRequest, ResearchTopicRequest, ResearchPlanRequest, TaskRequest,
    ProjectUpdate, ResearchTopicUpdate, ResearchPlanUpdate, TaskUpdate,
    ProjectResponse as HierarchicalProjectResponse, ResearchTopicResponse, 
    ResearchPlanResponse, TaskResponse,
    SuccessResponse, ProjectHierarchy, ProjectStats, TopicStats, PlanStats
)

# Import V2 API router
from v2_hierarchical_api import v2_router, set_mcp_client

# Configure structured JSON logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL.upper()),
    format='%(message)s',  # JSON formatter will handle structure
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/api-gateway.log') if Config.LOG_LEVEL.upper() == 'DEBUG' else logging.NullHandler()
    ]
)

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "service": "api-gateway",
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno
        }
        return json.dumps(log_record)

logger = logging.getLogger(__name__)
for handler in logger.handlers:
    handler.setFormatter(JSONFormatter())

# Global MCP client instance
mcp_client = None

# Global database client for direct read access
native_database_client = None


def get_database():
    """Get database client for direct read operations."""
    global native_database_client
    if native_database_client is None:
        try:
            native_database_client = get_native_database()
        except Exception as e:
            logger.error(json.dumps({
                "event": "database_initialization_failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }))
            raise HTTPException(status_code=503, detail="Database service not available")
    return native_database_client


class APIGateway:
    """
    Containerized API Gateway for Version 0.3 microservices architecture.
    
    Routes REST API requests to research agents via the MCP server and supports
    direct PostgreSQL reads for performance.
    """
    
    def __init__(self):
        self.mcp_client: Optional[MCPClient] = None
        self.active_requests: Dict[str, Dict[str, Any]] = {}
        self.request_timeout = 3600  # 1 hour
        
    async def initialize(self) -> bool:
        """Initialize the API Gateway and connect to MCP server."""
        try:
            logger.info(json.dumps({
                "event": "gateway_initialization_start",
                "timestamp": datetime.utcnow().isoformat()
            }))
            
            # Validate configuration
            Config.validate_config()
            
            # Initialize MCP client with full configuration
            mcp_config = Config.get_mcp_config()
            self.mcp_client = MCPClient(
                host=mcp_config.get("host", "mcp-server"),
                port=mcp_config.get("port", 9000),
                config={
                    "max_retries": mcp_config.get("retry_attempts", 15),
                    "base_retry_delay": mcp_config.get("retry_delay", 5),
                    "heartbeat_interval": mcp_config.get("heartbeat_interval", 30),
                    "ping_timeout": mcp_config.get("ping_timeout", 10),
                    "request_timeout": mcp_config.get("request_timeout", 3600),
                    "max_reconnect_duration": mcp_config.get("max_reconnect_duration", 3600)
                }
            )
            
            # Connect to MCP server
            if not await self.mcp_client.connect():
                logger.error(json.dumps({
                    "event": "mcp_connection_failed",
                    "timestamp": datetime.utcnow().isoformat()
                }))
                return False
            
            # Start request cleanup task
            asyncio.create_task(self._cleanup_requests())
            
            logger.info(json.dumps({
                "event": "gateway_initialization_success",
                "mcp_url": f"ws://{mcp_config['host']}:{mcp_config['port']}",
                "timestamp": datetime.utcnow().isoformat()
            }))
            return True
            
        except Exception as e:
            logger.error(json.dumps({
                "event": "gateway_initialization_error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }))
            return False
    
    async def shutdown(self):
        """Cleanup resources on shutdown."""
        try:
            logger.info(json.dumps({
                "event": "gateway_shutdown_start",
                "timestamp": datetime.utcnow().isoformat()
            }))
            
            # Cancel pending requests
            for task_id in list(self.active_requests.keys()):
                logger.warning(json.dumps({
                    "event": "request_cancelled",
                    "task_id": task_id,
                    "timestamp": datetime.utcnow().isoformat()
                }))
                self.active_requests.pop(task_id, None)
            
            if self.mcp_client:
                await self.mcp_client.disconnect()
            
            logger.info(json.dumps({
                "event": "gateway_shutdown_complete",
                "timestamp": datetime.utcnow().isoformat()
            }))
            
        except Exception as e:
            logger.error(json.dumps({
                "event": "gateway_shutdown_error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }))
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for the API Gateway service."""
        health_status = {
            "service": "api-gateway",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": Config.API_VERSION,
            "dependencies": {}
        }
        
        try:
            # Check MCP server connection
            mcp_health = await self.mcp_client.health_check() if self.mcp_client else {"status": "unhealthy"}
            health_status["dependencies"]["mcp_server"] = mcp_health["status"]
            if mcp_health["status"] != "healthy":
                health_status["status"] = "degraded"
                health_status["dependencies"]["mcp_details"] = mcp_health
            
            # Check native database connection
            try:
                db_client = get_native_database()
                db_health = await db_client.health_check()
                health_status["dependencies"]["database"] = db_health["status"]
                if db_health["status"] != "healthy":
                    health_status["status"] = "degraded"
                    health_status["dependencies"]["db_details"] = db_health
            except Exception as e:
                logger.error(json.dumps({
                    "event": "database_health_check_failed",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }))
                health_status["dependencies"]["database"] = "unhealthy"
                health_status["status"] = "degraded"
            
            # Add Redis check (placeholder for future implementation)
            health_status["dependencies"]["redis"] = "not_implemented"
            
            return health_status
            
        except Exception as e:
            logger.error(json.dumps({
                "event": "health_check_error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }))
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
            return health_status
    
    async def _cleanup_requests(self):
        """Clean up expired requests."""
        while True:
            try:
                current_time = datetime.now()
                expired = [
                    task_id for task_id, req in self.active_requests.items()
                    if (current_time - req["submitted_at"]).total_seconds() > self.request_timeout
                ]
                
                for task_id in expired:
                    logger.warning(json.dumps({
                        "event": "request_timeout",
                        "task_id": task_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                    self.active_requests.pop(task_id, None)
                
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(json.dumps({
                    "event": "request_cleanup_error",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }))
                await asyncio.sleep(60)


# Global gateway instance
gateway = APIGateway()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    logger.info(json.dumps({
        "event": "application_startup_start",
        "timestamp": datetime.utcnow().isoformat()
    }))
    
    try:
        # Initialize native database connection
        if not await initialize_native_database():
            logger.error(json.dumps({
                "event": "database_initialization_failed",
                "timestamp": datetime.utcnow().isoformat()
            }))
            raise Exception("Database initialization failed")
        
        # Initialize gateway
        if not await gateway.initialize():
            logger.error(json.dumps({
                "event": "gateway_initialization_failed",
                "timestamp": datetime.utcnow().isoformat()
            }))
            raise Exception("Gateway initialization failed")
        
        # Set MCP client for V2 API
        await set_v2_mcp_client()
        
        logger.info(json.dumps({
            "event": "application_startup_success",
            "timestamp": datetime.utcnow().isoformat()
        }))
        
    except Exception as e:
        logger.error(json.dumps({
            "event": "application_startup_error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }))
        raise
    
    yield
    
    # Shutdown
    logger.info(json.dumps({
        "event": "application_shutdown_start",
        "timestamp": datetime.utcnow().isoformat()
    }))
    try:
        await gateway.shutdown()
        await close_native_database()
        logger.info(json.dumps({
            "event": "application_shutdown_success",
            "timestamp": datetime.utcnow().isoformat()
        }))
    except Exception as e:
        logger.error(json.dumps({
            "event": "application_shutdown_error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }))


# Create FastAPI application
app = FastAPI(
    title=Config.API_TITLE,
    description=Config.API_DESCRIPTION,
    version=Config.API_VERSION,
    docs_url=Config.DOCS_URL,
    redoc_url=Config.REDOC_URL,
    lifespan=lifespan
)

# Configure CORS
cors_config = Config.get_cors_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_config["allow_origins"],
    allow_credentials=cors_config["allow_credentials"],
    allow_methods=cors_config["allow_methods"],
    allow_headers=cors_config["allow_headers"]
)

# Include V2 hierarchical API routes
app.include_router(v2_router)

# Setup MCP client reference for V2 API
def get_mcp_client_dependency():
    """Dependency to get MCP client for V2 API."""
    if not gateway.mcp_client or not gateway.mcp_client.is_connected:
        logger.error(json.dumps({
            "event": "mcp_client_unavailable",
            "timestamp": datetime.utcnow().isoformat()
        }))
        raise HTTPException(status_code=503, detail="MCP server not available")
    return gateway.mcp_client

async def set_v2_mcp_client():
    """Set the MCP client for V2 API after initialization."""
    set_mcp_client(gateway.mcp_client)


# API Routes
@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return await gateway.health_check()

@app.get("/status")
async def get_status():
    """Get detailed service status."""
    health = await gateway.health_check()
    return {
        "service": health["service"],
        "status": health["status"],
        "version": health["version"],
        "dependencies": health["dependencies"],
        "active_requests": len(gateway.active_requests),
        "mcp_connection": gateway.mcp_client.connection_info if gateway.mcp_client else None
    }

@app.get("/metrics")
async def get_metrics():
    """Get service metrics for monitoring."""
    mcp_stats = await gateway.mcp_client.get_server_stats() if gateway.mcp_client else None
    return {
        "active_requests": len(gateway.active_requests),
        "mcp_connected": gateway.mcp_client.is_connected if gateway.mcp_client else False,
        "mcp_stats": mcp_stats,
        "service": "api-gateway",
        "version": Config.API_VERSION
    }


# Signal handlers for graceful shutdown
def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(json.dumps({
        "event": "signal_received",
        "signal": signum,
        "timestamp": datetime.utcnow().isoformat()
    }))
    asyncio.create_task(gateway.shutdown())
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


async def main():
    """Main entry point for the containerized API Gateway service."""
    try:
        logger.info(json.dumps({
            "event": "service_start",
            "host": Config.HOST,
            "port": Config.PORT,
            "timestamp": datetime.utcnow().isoformat()
        }))
        
        server_config = Config.get_server_config()
        config = uvicorn.Config(
            app,
            host=server_config["host"],
            port=server_config["port"],
            log_level=server_config["log_level"],
            access_log=server_config["access_log"]
        )
        
        server = uvicorn.Server(config)
        await server.serve()
        
    except Exception as e:
        logger.error(json.dumps({
            "event": "service_error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }))
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info(json.dumps({
            "event": "service_stopped_by_user",
            "timestamp": datetime.utcnow().isoformat()
        }))
    except Exception as e:
        logger.error(json.dumps({
            "event": "service_start_failed",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }))
        sys.exit(1)
