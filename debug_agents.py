#!/usr/bin/env python3
"""
Debug script to check agent availability in the MCP system.
"""

import asyncio
import json
import websockets
from datetime import datetime


async def check_agent_availability():
    """Check what agents are available for specific capabilities."""
    
    # Connect to MCP server
    try:
        async with websockets.connect("ws://127.0.0.1:9000/ws") as websocket:
            print("✓ Connected to MCP server")
            
            # Request capability query
            message = {
                'type': 'query_capabilities',
                'data': {'capability': 'plan_research'},
                'timestamp': datetime.now().isoformat()
            }
            
            await websocket.send(json.dumps(message))
            print("📤 Sent capability query for 'plan_research'")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                print(f"📥 Response: {json.dumps(response_data, indent=2)}")
            except asyncio.TimeoutError:
                print("⏱️ Timeout waiting for response")
                
            # Also query all capabilities
            message = {
                'type': 'query_capabilities',
                'data': {},
                'timestamp': datetime.now().isoformat()
            }
            
            await websocket.send(json.dumps(message))
            print("📤 Sent query for all capabilities")
            
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                print(f"📥 All capabilities: {json.dumps(response_data, indent=2)}")
            except asyncio.TimeoutError:
                print("⏱️ Timeout waiting for capabilities response")
                
    except Exception as e:
        print(f"❌ Error connecting to MCP server: {e}")


if __name__ == "__main__":
    asyncio.run(check_agent_availability())
