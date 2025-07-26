#!/usr/bin/env python3
"""
Health check for Integrated Planning Agent Service
"""

import asyncio
import json
import sys
import os
from datetime import datetime

import websockets


async def health_check():
    """Check if the Planning Agent service is healthy"""
    try:
        # Check if we can connect to MCP server
        mcp_server_url = os.getenv("MCP_SERVER_URL", "ws://mcp-server:9000")
        
        async with websockets.connect(mcp_server_url, timeout=5) as websocket:
            # Send a simple ping
            ping_message = {
                "type": "ping",
                "agent_id": "health-check",
                "timestamp": datetime.now().isoformat()
            }
            
            await websocket.send(json.dumps(ping_message))
            
            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            response_data = json.loads(response)
            
            if response_data.get("type") == "pong":
                print("✅ Planning Agent service is healthy")
                return True
            else:
                print(f"❌ Unexpected response: {response_data}")
                return False
                
    except Exception as e:
        print(f"❌ Health check failed: {str(e)}")
        return False


if __name__ == "__main__":
    is_healthy = asyncio.run(health_check())
    sys.exit(0 if is_healthy else 1)
