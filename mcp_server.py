#!/usr/bin/env python3
"""
Model Context Protocol (MCP) Server for Eunice
Provides research capabilities through the MCP protocol
"""

import asyncio
import os
import sys
import logging
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    # Set up logging
    log_path = os.getenv("EUNICE_LOG_PATH", "logs")
    log_level = os.getenv("EUNICE_LOG_LEVEL", "INFO")

    # Ensure log directory exists
    Path(log_path).mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(os.path.join(log_path, 'mcp_server.log')),
        ]
    )
    # Import and run the MCP server
    try:
        from old_src.mcp.server import main
        print("🔧 Starting MCP Server...")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 MCP Server stopped by user")
    except Exception as e:
        print(f"❌ MCP Server error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
