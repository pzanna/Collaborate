#!/usr/bin/env python3
"""
Test agent response communication directly
"""

import asyncio
import json
import websockets
from datetime import datetime

async def test_agent_response():
    """Test if agents are sending responses back to MCP server"""
    
    uri = "ws://127.0.0.1:9000/ws"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✓ Connected to MCP server")
            
            # Listen for messages for 30 seconds
            print("📡 Listening for agent responses...")
            
            timeout_duration = 30
            start_time = asyncio.get_event_loop().time()
            
            while True:
                current_time = asyncio.get_event_loop().time()
                if current_time - start_time > timeout_duration:
                    print("⏱️ Timeout reached")
                    break
                
                try:
                    # Wait for message with short timeout
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    
                    print(f"📨 Received message: {data.get('type', 'unknown')}")
                    
                    if data.get('type') == 'agent_response':
                        print(f"🎯 Agent response received!")
                        print(f"   Task ID: {data.get('data', {}).get('task_id')}")
                        print(f"   Status: {data.get('data', {}).get('status')}")
                        print(f"   Agent: {data.get('data', {}).get('agent_type')}")
                        
                except asyncio.TimeoutError:
                    # No message received, continue listening
                    continue
                except Exception as e:
                    print(f"❌ Error receiving message: {e}")
                    break
            
            print("🏁 Finished listening")
            
    except Exception as e:
        print(f"❌ Failed to connect to MCP server: {e}")

if __name__ == "__main__":
    asyncio.run(test_agent_response())
