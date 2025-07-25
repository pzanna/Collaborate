#!/usr/bin/env python3
"""
Simple script to start the MCP server
"""
import sys
import asyncio
from pathlib import Path


def main_runner():
    """Set up path and run server."""
    # Add src directory to path
    sys.path.insert(0, str(Path(__file__).parent / 'src'))
    from mcp.server import main

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("MCP Server stopped by user")
    except Exception as e:
        print(f"MCP Server error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main_runner()
