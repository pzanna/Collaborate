#!/usr/bin/env python3
"""
HTTP Server Test for Planning Agent Service
Tests the actual FastAPI server endpoints
"""

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

import httpx

async def test_http_server():
    """Test the Planning Agent HTTP server"""
    print("🧪 Testing Planning Agent HTTP Server...")
    
    base_url = "http://localhost:8007"
    
    # Test health endpoint
    print("Testing health endpoint...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                print("✅ Health endpoint working")
                print(f"   - Status: {health_data['status']}")
                print(f"   - Agent type: {health_data['agent_type']}")
                print(f"   - MCP connected: {health_data['mcp_connected']}")
            else:
                print(f"❌ Health endpoint failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")
        return False

    # Test capabilities endpoint
    print("Testing capabilities endpoint...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/capabilities", timeout=5)
            if response.status_code == 200:
                capabilities_data = response.json()
                print("✅ Capabilities endpoint working")
                print(f"   - Capabilities: {len(capabilities_data['capabilities'])}")
                print(f"   - Capabilities: {capabilities_data['capabilities']}")
            else:
                print(f"❌ Capabilities endpoint failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Capabilities endpoint error: {e}")
        return False

    # Test task execution endpoint
    print("Testing task execution endpoint...")
    try:
        test_task = {
            "action": "plan_research",
            "payload": {
                "query": "Machine learning applications in neuroscience",
                "scope": "medium"
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{base_url}/task", json=test_task, timeout=10)
            if response.status_code == 200:
                task_result = response.json()
                print("✅ Task execution endpoint working")
                print(f"   - Status: {task_result['status']}")
                print(f"   - Agent ID: {task_result['agent_id']}")
                if task_result['status'] == 'completed':
                    print(f"   - Plan objectives: {len(task_result['result']['plan']['objectives'])}")
                    print(f"   - Timeline: {task_result['result']['plan']['timeline']['total_days']} days")
            else:
                print(f"❌ Task execution endpoint failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
    except Exception as e:
        print(f"❌ Task execution endpoint error: {e}")
        return False

    # Test cost estimation endpoint
    print("Testing cost estimation via task endpoint...")
    try:
        cost_task = {
            "action": "cost_estimation",
            "payload": {
                "scope": "medium",
                "duration_days": 21,
                "resources": ["database_access", "analysis_software", "expert_consultation"],
                "query": "Cost estimation test via HTTP",
                "agents": ["planning", "literature", "analysis", "synthesis"]
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{base_url}/task", json=cost_task, timeout=10)
            if response.status_code == 200:
                cost_result = response.json()
                print("✅ Cost estimation endpoint working")
                print(f"   - Status: {cost_result['status']}")
                if cost_result['status'] == 'completed':
                    breakdown = cost_result['result']['cost_breakdown']
                    print(f"   - AI cost: ${breakdown['summary']['ai_cost']:.2f}")
                    print(f"   - Traditional cost: ${breakdown['summary']['traditional_cost']:.2f}")
                    print(f"   - Total cost: ${breakdown['summary']['total']:.2f}")
                    print(f"   - Cost per day: ${breakdown['summary']['cost_per_day']:.2f}")
                    print(f"   - Estimation method: {cost_result['result']['estimation_method']}")
            else:
                print(f"❌ Cost estimation endpoint failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
    except Exception as e:
        print(f"❌ Cost estimation endpoint error: {e}")
        return False

    return True

def start_server_process():
    """Start the server in a separate process"""
    import subprocess
    import os
    
    # Change to the planning agent directory
    planning_dir = Path(__file__).parent
    
    # Start the server
    env = os.environ.copy()
    env['MCP_SERVER_URL'] = 'ws://localhost:9000'  # Will fail to connect but that's OK for testing
    
    process = subprocess.Popen(
        [sys.executable, "-m", "src.planning_service"],
        cwd=planning_dir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    return process

async def main():
    """Main test function"""
    print("🚀 Starting Planning Agent HTTP Server Test")
    print("=" * 60)
    
    # Start the server
    print("Starting Planning Agent server...")
    server_process = start_server_process()
    
    # Give server time to start
    print("Waiting for server to start...")
    await asyncio.sleep(3)
    
    try:
        # Check if server is running
        if server_process.poll() is not None:
            stdout, stderr = server_process.communicate()
            print(f"❌ Server failed to start:")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            return False
        
        # Run tests
        success = await test_http_server()
        
        if success:
            print("\n🎉 All HTTP server tests passed!")
            print("✅ Planning Agent HTTP server is working correctly")
        else:
            print("\n⚠️ Some HTTP server tests failed")
        
        return success
        
    finally:
        # Clean up server process
        print("\nStopping server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
            server_process.wait()

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
