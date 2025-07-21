#!/usr/bin/env python3
"""
Simple test to send a task directly through the MCP system.
"""

import asyncio
import json
import websockets
from datetime import datetime
import uuid


async def send_test_task():
    """Send a simple test task to see if agents respond."""
    
    try:
        # Connect to MCP server
        async with websockets.connect("ws://127.0.0.1:9000/ws") as websocket:
            print("✓ Connected to MCP server")
            
            # Create a simple research action
            task_id = str(uuid.uuid4())
            action = {
                'task_id': task_id,
                'context_id': 'test_context',
                'agent_type': 'planning',
                'action': 'plan_research',
                'payload': {
                    'query': 'Simple test query',
                    'context': {},
                    'user_id': 'test_user',
                    'conversation_id': 'test_conv'
                },
                'created_at': datetime.now().isoformat()
            }
            
            # Send as research_action message
            message = {
                'type': 'research_action',
                'data': action,
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"📤 Sending test task: {task_id}")
            await websocket.send(json.dumps(message))
            
            # Wait a bit to see if we get any responses
            print("⏳ Waiting for responses...")
            
            for i in range(10):  # Wait up to 10 seconds
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    response_data = json.loads(response)
                    print(f"📥 Response {i+1}: {json.dumps(response_data, indent=2)}")
                except asyncio.TimeoutError:
                    print(f"⏱️ No response after {i+1} seconds")
                    if i >= 4:  # Stop waiting after 5 seconds of no responses
                        break
                        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(send_test_task())
