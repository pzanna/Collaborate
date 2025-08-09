#!/usr/bin/env python3
"""
Clean API Gateway Service for Eunice Research Platform

This service provides a unified REST API interface. Features:
- FastAPI-based REST API
- Direct PostgreSQL read access for performance
- V2 hierarchical research endpoints
- Structured JSON logging for monitoring

Note: File watching enabled in development mode
"""

import asyncio
import logging
import sys
import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional
import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

from config import get_config

# Import database service client for direct read access
from native_database_client import get_native_database, initialize_native_database, close_native_database

# Import V2 API router
from v2_hierarchical_api import v2_router

# Import MCP client for direct read access
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# Get configuration
config = get_config()

# Configure structured JSON logging
logging.basicConfig(
    level=getattr(logging, config.logging.level.upper()),
    format='%(message)s',  # JSON formatter will handle structure
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/api-gateway.log') if config.logging.level.upper() == 'DEBUG' else logging.NullHandler()
    ]
)

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.now().isoformat(),
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
                "timestamp": datetime.now().isoformat()
            }))
            raise HTTPException(status_code=503, detail="Database service not available")
    return native_database_client


async def test_mcp_connection():
    """Test MCP server connection without creating persistent connections."""
        # Basic connectivity check using direct HTTP calls to avoid session issues
    import aiohttp
    import asyncio as aio
    server_id = "database"
    server_url = "http://database-service:8010/mcp/"
    try:
        # Make direct HTTP call to list tools
        logger.info("Checking health of server %s at %s", server_id, server_url)
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            }
            data = {
                "jsonrpc": "2.0",
                "id": "1",
                "method": "tools/list",
                "params": {}
            }
            
            timeout = aiohttp.ClientTimeout(total=5.0)
            async with session.post(server_url, json=data, headers=headers, timeout=timeout) as response:
                logger.info("Received response from server %s: %s", server_id, response.status)
                if response.status == 200:
                    # Handle streamable HTTP response
                    content = await response.text()
                    
                    # Parse event-stream format
                    server_tools = []
                    if content.startswith("event: message"):
                        lines = content.split('\n')
                        for line in lines:
                            if line.startswith("data: "):
                                import json
                                try:
                                    json_data = json.loads(line[6:])  # Remove "data: " prefix
                                    if "result" in json_data and "tools" in json_data["result"]:
                                        server_tools = [tool["name"] for tool in json_data["result"]["tools"]]
                                        logger.info("MCP server %s tools: %s", server_id, server_tools)
                                except:
                                    pass
        
    except Exception as e:
        logger.warning(json.dumps({
            "event": "mcp_connection_test_failed",
            "error": str(e),
            "message": "MCP server not available - continuing without MCP functionality",
            "timestamp": datetime.now().isoformat()
        }))
        return False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    logger.info(json.dumps({
        "event": "application_startup_start",
        "timestamp": datetime.now().isoformat()
    }))
    
    try:
        # Try to initialize native database connection (gracefully handle failures in development)
        try:
            db_initialized = await initialize_native_database()
            if not db_initialized:
                logger.warning(json.dumps({
                    "event": "database_initialization_warning",
                    "message": "Database initialization failed - running in degraded mode",
                    "timestamp": datetime.now().isoformat()
                }))
        except Exception as db_error:
            logger.warning(json.dumps({
                "event": "database_connection_warning",
                "error": str(db_error),
                "message": "Database not available - API will work with limited functionality",
                "timestamp": datetime.now().isoformat()
            }))
        
        # Set up V2 API router
        app.include_router(v2_router)
        
        logger.info(json.dumps({
            "event": "application_startup_success",
            "timestamp": datetime.now().isoformat()
        }))
        
    except Exception as e:
        logger.error(json.dumps({
            "event": "application_startup_error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }))
        # Don't raise the exception - allow service to start without database
        logger.warning("Starting service in limited mode without database connectivity")
    
    yield
    
    # Shutdown
    logger.info(json.dumps({
        "event": "application_shutdown_start",
        "timestamp": datetime.now().isoformat()
    }))
    try:
        await close_native_database()
        logger.info(json.dumps({
            "event": "application_shutdown_success",
            "timestamp": datetime.now().isoformat()
        }))
    except Exception as e:
        logger.error(json.dumps({
            "event": "application_shutdown_error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }))


# Create FastAPI application
app = FastAPI(
    title="API Gateway",
    description="Eunice Research Platform API Gateway",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.security.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"]
)


@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


@app.get("/test/mcp-connection")
async def test_mcp_connection_endpoint():
    """Test MCP server connection endpoint."""
    try:
        connection_successful = await test_mcp_connection()
        if connection_successful:
            return {
                "status": "success",
                "message": "MCP connection successful",
                "mcp_server": "http://database-service:8010/mcp/",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "failed", 
                "message": "MCP connection failed",
                "mcp_server": "http://database-service:8010/mcp",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(json.dumps({
            "event": "mcp_test_endpoint_error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }))
        raise HTTPException(status_code=500, detail=f"MCP test failed: {str(e)}")

async def main():
    """Main entry point for the containerized API Gateway service."""
    try:
        logger.info(json.dumps({
            "event": "service_start",
            "host": config.server.host,
            "port": config.server.port,
            "timestamp": datetime.now().isoformat()
        }))
        
        config_dict = uvicorn.Config(
            app,
            host=config.server.host,
            port=config.server.port,
            log_level=config.logging.level.lower(),
            access_log=False
        )
        
        # Test MCP connection during startup (non-blocking)
        await test_mcp_connection()

        server = uvicorn.Server(config_dict)
        await server.serve()
        
    except Exception as e:
        logger.error(json.dumps({
            "event": "service_error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }))
        sys.exit(1)


def sync_main():
    """Synchronous wrapper for watchfiles compatibility."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info(json.dumps({
            "event": "service_stopped_by_user", 
            "timestamp": datetime.now().isoformat()
        }))
    except Exception as e:
        logger.error(json.dumps({
            "event": "service_start_failed",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }))
        sys.exit(1)


if __name__ == "__main__":
    sync_main()
