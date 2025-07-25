#!/usr/bin/env python3
"""
Test Literature Agent Connection to MCP Server
"""

import asyncio
import json
import websockets

async def test_connection():
    """Test connection and registration with MCP server"""
    mcp_url = "ws://localhost:9000"
    
    try:
        print(f"Connecting to {mcp_url}...")
        async with websockets.connect(mcp_url) as websocket:
            print("✅ Connected to MCP server")
            
            # Send registration message
            registration_message = {
                "type": "agent_register",
                "agent_id": "test-literature-agent",
                "agent_type": "literature_search",
                "capabilities": ["academic_search", "literature_review"],
                "max_concurrent": 3,
                "timeout": 300
            }
            
            print("Sending registration message...")
            await websocket.send(json.dumps(registration_message))
            
            # Wait for response
            print("Waiting for response...")
            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            response_data = json.loads(response)
            
            print(f"Response: {response_data}")
            
            if response_data.get("type") == "registration_confirmed":
                print("✅ Registration successful!")
                return True
            else:
                print(f"❌ Registration failed: {response_data}")
                return False
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_connection())
    exit(0 if result else 1)
