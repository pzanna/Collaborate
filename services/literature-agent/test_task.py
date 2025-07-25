#!/usr/bin/env python3
"""
Test task submission to Literature Agent through MCP Server
"""

import asyncio
import json
import uuid
import websockets

async def test_literature_task():
    """Test submitting a literature search task"""
    mcp_url = "ws://localhost:9000"
    
    try:
        print(f"Connecting to {mcp_url}...")
        async with websockets.connect(mcp_url) as websocket:
            print("✅ Connected to MCP server")
            
            # Submit a literature search task
            task_message = {
                "type": "task_submit",
                "task_id": str(uuid.uuid4()),
                "agent_type": "literature_search",
                "task_type": "literature_search",
                "parameters": {
                    "query": "neural networks machine learning",
                    "max_results": 5,
                    "databases": ["pubmed", "arxiv"]
                },
                "priority": "normal",
                "timeout": 300
            }
            
            print("Submitting literature search task...")
            await websocket.send(json.dumps(task_message))
            
            # Wait for response
            print("Waiting for task response...")
            response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
            response_data = json.loads(response)
            
            print(f"Response: {response_data}")
            
            if response_data.get("type") == "task_accepted":
                print("✅ Task accepted by MCP server!")
                
                # Wait for task result
                print("Waiting for task result...")
                result_response = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                result_data = json.loads(result_response)
                print(f"Task result: {result_data}")
                
            return True
                
    except Exception as e:
        print(f"❌ Task submission failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_literature_task())
    exit(0 if result else 1)
