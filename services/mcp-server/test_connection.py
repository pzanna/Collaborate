#!/usr/bin/env python3
"""
Enhanced MCP Server Test Client - Phase 3.1
Quick test to verify the containerized MCP server is responding
"""

import asyncio
import json
import websockets

async def test_mcp_server():
    """Test connection to Enhanced MCP Server"""
    try:
        # Connect to the MCP server WebSocket
        uri = "ws://localhost:9000"
        
        async with websockets.connect(uri) as websocket:
            # Send an initialize message
            init_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "Enhanced MCP Test Client",
                        "version": "3.1.0"
                    }
                }
            }
            
            await websocket.send(json.dumps(init_message))
            response = await websocket.recv()
            
            print("✅ Enhanced MCP Server Phase 3.1 - Connection successful!")
            print(f"📦 Server Response: {response}")
            
            # Send a ping
            ping_message = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "ping"
            }
            
            await websocket.send(json.dumps(ping_message))
            ping_response = await websocket.recv()
            
            print(f"🏓 Ping Response: {ping_response}")
            
            return True
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Enhanced MCP Server Phase 3.1...")
    success = asyncio.run(test_mcp_server())
    if success:
        print("🎉 Enhanced MCP Server Phase 3.1 is running successfully!")
    else:
        print("💥 Enhanced MCP Server Phase 3.1 test failed")
