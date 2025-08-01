#!/usr/bin/env python3
"""
Test script for complete research workflow: literature search, synthesis, and review
"""

import asyncio
import websockets
import json
import uuid
from datetime import datetime

MCP_SERVER_URL = "ws://localhost:9000"

async def test_complete_workflow():
    """Test the complete research workflow"""
    
    async with websockets.connect(MCP_SERVER_URL) as websocket:
        print("Connected to MCP server")
        
        # Create a test task for complete workflow
        task_id = str(uuid.uuid4())
        
        research_action = {
            "type": "research_action",
            "data": {
                "task_id": task_id,
                "context_id": f"test-complete-workflow-{task_id}",
                "agent_type": "research_manager",
                "action": "coordinate_research",
                "payload": {
                    "query": "Machine learning applications in healthcare diagnostics: A comprehensive review",
                    "research_plan": {
                        "stage": "literature_review",
                        "max_results": 20,
                        "include_synthesis": True,
                        "include_review": True
                    },
                    "metadata": {
                        "test_complete_workflow": True,
                        "expected_stages": ["literature_search", "synthesis", "systematic_review"]
                    }
                }
            },
            "client_id": "test-client",
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"Sending research task: {task_id}")
        print(f"Query: {research_action['data']['payload']['query']}")
        
        # Send the research action
        await websocket.send(json.dumps(research_action))
        
        print("Task sent! Monitoring for results...")
        print("Expected workflow: Literature Search → Synthesis → Review → Complete")
        print("This may take several minutes...")
        
        # Monitor responses
        stage_count = 0
        max_stages = 10  # Prevent infinite waiting
        
        while stage_count < max_stages:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                data = json.loads(response)
                
                print(f"\n--- Response {stage_count + 1} ---")
                print(f"Type: {data.get('type', 'unknown')}")
                
                if data.get('type') == 'task_result':
                    task_result_id = data.get('task_id')
                    agent_id = data.get('agent_id')
                    result = data.get('result', {})
                    status = result.get('status', 'unknown')
                    
                    print(f"Task Result from {agent_id}")
                    print(f"Status: {status}")
                    
                    if task_result_id == task_id:
                        print("🎯 Main task result received")
                        if status == "completed":
                            if result.get('workflow_completed'):
                                print("✅ Complete workflow finished successfully!")
                                final_results = result.get('results', {})
                                stages = final_results.get('stages_completed', [])
                                print(f"Completed stages: {stages}")
                                break
                            else:
                                print("✅ Research coordination completed")
                                current_stage = result.get('current_stage', 'unknown')
                                print(f"Current stage: {current_stage}")
                    else:
                        print(f"🔄 Delegated task result from {agent_id}")
                        if 'literature' in agent_id.lower():
                            print("📚 Literature search completed")
                        elif 'synthesis' in agent_id.lower():
                            print("🔬 Synthesis completed")
                        elif 'screening' in agent_id.lower():
                            print("📋 Review completed")
                
                elif data.get('type') == 'research_action':
                    action = data.get('data', {}).get('action', 'unknown')
                    target_agent = data.get('data', {}).get('agent_type', 'unknown')
                    print(f"🔄 Research action: {action} → {target_agent}")
                
                else:
                    print(f"Other message: {data}")
                
                stage_count += 1
                
            except asyncio.TimeoutError:
                print("⏰ Timeout waiting for response")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                break
        
        print(f"\n--- Test completed after {stage_count} responses ---")

if __name__ == "__main__":
    print("🧪 Testing complete research workflow...")
    print("Expected: Literature Search → Synthesis → Review → Complete")
    asyncio.run(test_complete_workflow())
