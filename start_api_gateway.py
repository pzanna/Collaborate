#!/usr/bin/env python3
"""
Start script for API Gateway

Starts the API Gateway server with proper configuration.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from old_src.api.gateway import create_app
from old_src.config.config_manager import ConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def start_api_gateway():
    """Start the API Gateway server"""
    try:
        # Initialize configuration manager
        config_manager = ConfigManager()
        
        # Create the FastAPI app
        app = create_app(config_manager)
        
        # Start the FastAPI server using uvicorn
        import uvicorn
        
        logger.info("Starting API Gateway server on http://localhost:8001")
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=8001,
            log_level="info",
            access_log=True
        )
        
        server = uvicorn.Server(config)
        await server.serve()
        
    except KeyboardInterrupt:
        logger.info("API Gateway shutdown requested by user")
    except Exception as e:
        logger.error(f"API Gateway error: {e}")
        raise


def main():
    """Main entry point"""
    logger.info("API Gateway Starting...")
    
    try:
        asyncio.run(start_api_gateway())
    except KeyboardInterrupt:
        logger.info("API Gateway stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to start API Gateway: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
