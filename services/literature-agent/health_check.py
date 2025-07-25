#!/usr/bin/env python3
"""
Literature Agent Health Check
Simple health check for containerized Literature Agent
"""

import sys
import asyncio
import json
import os

async def check_health():
    """Check if Literature Agent service is healthy"""
    try:
        # Import required modules
        import websockets
        
        # Check MCP server connection
        mcp_url = os.getenv("MCP_SERVER_URL", "ws://localhost:9000")
        
        # Try to connect briefly
        async with websockets.connect(mcp_url) as websocket:
            # Send a simple ping
            ping_message = {
                "type": "health_check",
                "agent_id": os.getenv("AGENT_ID", "literature-agent-001")
            }
            
            await websocket.send(json.dumps(ping_message))
            
            # Wait briefly for any response (optional)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                print("✅ Health check passed - MCP server reachable")
            except asyncio.TimeoutError:
                print("✅ Health check passed - MCP server connected")
            
            return True
            
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(check_health())
    sys.exit(0 if result else 1)
