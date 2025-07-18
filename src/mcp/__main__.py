"""
MCP Server Module Entry Point

This file allows the MCP server to be run as a module:
python -m src.mcp
"""

import asyncio
from .server import main

if __name__ == "__main__":
    asyncio.run(main())
