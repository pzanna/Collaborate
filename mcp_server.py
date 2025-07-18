#!/usr/bin/env python3
"""
MCP Server Launcher

Simple launcher script for the MCP server that can be called from start_web.sh
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Ensure logs directory exists
Path('logs').mkdir(exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/mcp_server.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Main entry point for MCP server"""
    try:
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # Import and create config manager
        from src.config.config_manager import ConfigManager
        config_manager = ConfigManager()
        
        # Import and create MCP server
        from src.mcp.server import MCPServer
        server = MCPServer(config_manager)
        
        logger.info("Starting MCP Server...")
        await server.run_forever()
        
    except KeyboardInterrupt:
        logger.info("MCP Server shutdown by user")
    except Exception as e:
        logger.error(f"MCP Server error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
