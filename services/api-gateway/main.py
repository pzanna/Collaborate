#!/usr/bin/env python3
"""
Containerized API Gateway Service for Eunice Research Platform

This service provides a unified REST API interface that routes requests to appropriate 
research agents via the MCP (Message Control Protocol) server. It's designed to run 
as a containerized microservice in Version 0.3 architecture.

Key Features:
- REST API endpoints for all research operations
- MCP p            
            return AcademicSearchResponse(
                papers=papers,
                total_results=len(papers),
                query=request.query,
                execution_time=None,
                sources=["literature_agent"]
            )tocol integration for agent communication
- Health checks and monitoring
- Graceful shutdown handling
- Production-ready configuration
"""

import asyncio
import logging
import signal
import sys
import json
from uuid import uuid4
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from config import Config
from mcp_client import MCPClient

# Import database service client for direct read access
from native_database_client import get_native_database, initialize_native_database, close_native_database

# Import hierarchical data models for v2 endpoints
from src.data_models.hierarchical_data_models import (
    # Request models
    ProjectRequest, ResearchTopicRequest, ResearchPlanRequest, TaskRequest,
    # Update models
    ProjectUpdate, ResearchTopicUpdate, ResearchPlanUpdate, TaskUpdate,
    # Response models
    ProjectResponse as HierarchicalProjectResponse, ResearchTopicResponse, 
    ResearchPlanResponse, TaskResponse,
    # Utility models  
    SuccessResponse, ProjectHierarchy, ProjectStats, TopicStats, PlanStats
)

# Import V2 API router
from v2_hierarchical_api import v2_router, set_mcp_client

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL.upper()),
    format=Config.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/api-gateway.log') if Config.LOG_LEVEL.upper() == 'DEBUG' else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global MCP client instance
mcp_client = None

# Global database client for direct read access
native_database_client = None


def get_database():
    """Get database client for direct read operations using native PostgreSQL."""
    global native_database_client
    if native_database_client is None:
        try:
            # Initialize native PostgreSQL client for read operations
            native_database_client = get_native_database()
        except Exception as e:
            logger.error(f"Failed to initialize native database client: {e}")
            raise HTTPException(status_code=503, detail="Database service not available")
    return native_database_client


class APIGateway:
    """
    Containerized API Gateway for Version 0.3 microservices architecture.
    
    Provides unified REST interface and routes requests to research agents
    via the MCP server using WebSocket communication.
    """
    
    def __init__(self):
        self.mcp_client: Optional[MCPClient] = None
        self.active_requests: Dict[str, Dict[str, Any]] = {}
        
    async def initialize(self) -> bool:
        """Initialize the API Gateway and connect to MCP server."""
        try:
            logger.info("Initializing API Gateway...")
            
            # Validate configuration
            Config.validate_config()
            
            # Initialize MCP client
            mcp_config = Config.get_mcp_config()
            self.mcp_client = MCPClient(
                host=mcp_config["host"],
                port=mcp_config["port"]
            )
            
            # Connect to MCP server with retries
            for attempt in range(mcp_config["retry_attempts"]):
                try:
                    if await self.mcp_client.connect():
                        logger.info(f"API Gateway connected to MCP server at {mcp_config['url']}")
                        return True
                    else:
                        logger.warning(f"Connection attempt {attempt + 1} failed")
                        if attempt < mcp_config["retry_attempts"] - 1:
                            await asyncio.sleep(mcp_config["retry_delay"])
                except Exception as e:
                    logger.error(f"Connection attempt {attempt + 1} error: {e}")
                    if attempt < mcp_config["retry_attempts"] - 1:
                        await asyncio.sleep(mcp_config["retry_delay"])
            
            logger.error("Failed to connect to MCP server after all attempts")
            return False
            
        except Exception as e:
            logger.error(f"Error initializing API Gateway: {e}")
            return False
    
    async def shutdown(self):
        """Cleanup resources on shutdown."""
        try:
            logger.info("Shutting down API Gateway...")
            if self.mcp_client:
                await self.mcp_client.disconnect()
            logger.info("API Gateway shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for the API Gateway service."""
        health_status = {
            "service": "api-gateway",
            "status": "healthy",
            "timestamp": None,
            "version": Config.API_VERSION,
            "dependencies": {}
        }
        
        try:
            from datetime import datetime
            health_status["timestamp"] = datetime.utcnow().isoformat()
            
            # Check MCP server connection
            if self.mcp_client and self.mcp_client.is_connected:
                health_status["dependencies"]["mcp_server"] = "connected"
            else:
                health_status["dependencies"]["mcp_server"] = "disconnected"
                health_status["status"] = "degraded"
            
            # Check native database connection
            try:
                db_client = get_native_database()
                db_health = await db_client.health_check()
                if db_health["status"] == "healthy":
                    health_status["dependencies"]["database"] = "connected"
                else:
                    health_status["dependencies"]["database"] = "unhealthy"
                    health_status["status"] = "degraded"
            except Exception as e:
                logger.error(f"Database health check failed: {e}")
                health_status["dependencies"]["database"] = "disconnected"
                health_status["status"] = "degraded"
            
            # Add more dependency checks as needed
            health_status["dependencies"]["redis"] = "not_implemented"
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
            return health_status
    
          

    
# Global gateway instance
gateway = APIGateway()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan (startup and shutdown)."""
    # Startup
    logger.info("Starting API Gateway...")
    
    try:
        # Initialize native database connection
        if not await initialize_native_database():
            logger.error("Failed to initialize native database connection")
            raise Exception("Database initialization failed")
        
        # Initialize gateway
        if not await gateway.initialize():
            logger.error("Failed to initialize API Gateway")
            raise Exception("Gateway initialization failed")
        
        # Set MCP client for V2 API
        await set_v2_mcp_client()
        
        logger.info("API Gateway startup completed successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        # Don't raise here to allow graceful degradation
    
    yield
    
    # Shutdown
    logger.info("Shutting down API Gateway...")
    try:
        await gateway.shutdown()
        await close_native_database()
        logger.info("API Gateway shutdown completed")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


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
    return gateway.mcp_client

# Set MCP client reference for V2 API
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
        "active_requests": len(gateway.active_requests)
    }

@app.get("/metrics")
async def get_metrics():
    """Get service metrics for monitoring."""
    return {
        "active_requests": len(gateway.active_requests),
        "mcp_connected": gateway.mcp_client.is_connected if gateway.mcp_client else False,
        "service": "api-gateway",
        "version": Config.API_VERSION
    }





# Signal handlers for graceful shutdown

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


async def main():
    """Main entry point for the containerized API Gateway service."""
    try:
        logger.info(f"Starting API Gateway service on {Config.HOST}:{Config.PORT}")
        
        # Create uvicorn server configuration
        server_config = Config.get_server_config()
        config = uvicorn.Config(
            app,
            host=server_config["host"],
            port=server_config["port"],
            log_level=server_config["log_level"],
            access_log=server_config["access_log"]
        )
        
        # Start the server
        server = uvicorn.Server(config)
        await server.serve()
        
    except Exception as e:
        logger.error(f"API Gateway service error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("API Gateway service stopped by user")
    except Exception as e:
        logger.error(f"Failed to start API Gateway service: {e}")
        sys.exit(1)
