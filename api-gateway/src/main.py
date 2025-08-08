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

from .config.simple_config import get_config

# Import database service client for direct read access
from .native_database_client import get_native_database, initialize_native_database, close_native_database

# Import V2 API router
from .v2_hierarchical_api import v2_router

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
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

async def main():
    """Main entry point for the containerized API Gateway service."""
    try:
        logger.info(json.dumps({
            "event": "service_start",
            "host": config.server.host,
            "port": config.server.port,
            "timestamp": datetime.utcnow().isoformat()
        }))
        
        config_dict = uvicorn.Config(
            app,
            host=config.server.host,
            port=config.server.port,
            log_level=config.logging.level.lower(),
            access_log=False
        )
        
        server = uvicorn.Server(config_dict)
        await server.serve()
        
    except Exception as e:
        logger.error(json.dumps({
            "event": "service_error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }))
        sys.exit(1)


def sync_main():
    """Synchronous wrapper for watchfiles compatibility."""
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


if __name__ == "__main__":
    sync_main()
