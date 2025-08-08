"""
Main entry point for the SERVICE_NAME_PLACEHOLDER service.

This module provides the standardized main entry point with:
- Configuration loading
- Logging setup
- Health check endpoints
- Graceful shutdown handling
- MCP client integration (if needed)
"""

import asyncio
import logging
import logging.config
import os
import signal
import sys
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import Config, get_config
from .health_check import HealthCheck
from .models import ServiceInfo, HealthStatus


# Configure logging
def setup_logging(config: Config) -> None:
    """Set up logging based on configuration."""
    try:
        logging_config_path = Path("config/logging.json")
        if logging_config_path.exists():
            import json
            with open(logging_config_path) as f:
                logging_config = json.load(f)
            logging.config.dictConfig(logging_config)
        else:
            logging.basicConfig(
                level=getattr(logging, config.logging.level),
                format=config.logging.format,
                handlers=[logging.StreamHandler(sys.stdout)]
            )
    except Exception as e:
        # Fallback to basic logging
        logging.basicConfig(level=logging.INFO)
        logging.error(f"Failed to setup logging: {e}")


# Global variables
app: Optional[FastAPI] = None
config: Optional[Config] = None
health_check: Optional[HealthCheck] = None
logger = logging.getLogger("SERVICE_NAME_PLACEHOLDER")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    global config, health_check
    
    config = get_config()
    setup_logging(config)
    
    # Create FastAPI app
    app = FastAPI(
        title=config.service.name,
        description=config.service.description,
        version=config.service.version,
        debug=config.service.debug
    )
    
    # Configure CORS
    if config.security.cors_enabled:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.security.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # Initialize health check
    health_check = HealthCheck(config)
    
    # Add standard endpoints
    @app.get("/")
    async def root():
        """Root endpoint with service information."""
        return ServiceInfo(
            name=config.service.name,
            version=config.service.version,
            description=config.service.description,
            status="running"
        )
    
    @app.get("/health", response_model=HealthStatus)
    async def health():
        """Health check endpoint."""
        try:
            health_status = await health_check.check_health()
            if health_status.status != "healthy":
                raise HTTPException(status_code=503, detail=health_status.dict())
            return health_status
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(status_code=503, detail={"status": "unhealthy", "error": str(e)})
    
    @app.get("/metrics")
    async def metrics():
        """Metrics endpoint for monitoring."""
        # Implement metrics collection here
        return {"message": "Metrics endpoint - implement service-specific metrics"}
    
    # Add service-specific routes here
    # Example: app.include_router(your_router, prefix="/api/v1")
    
    return app


async def startup_service():
    """Perform service startup tasks."""
    logger.info(f"Starting {config.service.name} v{config.service.version}")
    logger.info(f"Service running on {config.service.host}:{config.service.port}")
    
    # Initialize service-specific components here
    # Example: await init_database_connection()
    # Example: await init_mcp_client()
    
    logger.info("Service startup completed successfully")


async def shutdown_service():
    """Perform service shutdown tasks."""
    logger.info("Shutting down service...")
    
    # Cleanup service-specific components here
    # Example: await close_database_connection()
    # Example: await close_mcp_client()
    
    logger.info("Service shutdown completed")


async def main():
    """Main service entry point."""
    global app, config
    
    try:
        # Create the FastAPI app
        app = create_app()
        
        # Add startup and shutdown event handlers
        @app.on_event("startup")
        async def on_startup():
            await startup_service()
        
        @app.on_event("shutdown")
        async def on_shutdown():
            await shutdown_service()
        
        # Handle development mode
        if os.getenv("DEVELOPMENT_MODE", "false").lower() == "true":
            logger.info("Running in development mode")
        
        # Run the server
        uvicorn_config = uvicorn.Config(
            app,
            host=config.service.host,
            port=config.service.port,
            log_level=config.logging.level.lower(),
            reload=os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"
        )
        
        server = uvicorn.Server(uvicorn_config)
        await server.serve()
        
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
    except Exception as e:
        logger.error(f"Service failed to start: {e}")
        sys.exit(1)


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down...")
    # Set a flag to trigger graceful shutdown
    asyncio.create_task(shutdown_service())


if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Run the main async function
    asyncio.run(main())
