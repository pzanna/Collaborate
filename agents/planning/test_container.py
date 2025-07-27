#!/usr/bin/env python3
"""
Docker Container Test for Planning Agent
"""
import asyncio
import subprocess
import time
import httpx
import sys

async def test_container():
    """Test the Planning Agent Docker container"""
    print("🧪 Testing Planning Agent Docker Container...")
    
    container_name = "planning-agent-test"
    
    # Start container
    print("Starting container...")
    start_cmd = [
        "docker", "run", "--rm", "--name", container_name,
        "-p", "8007:8007",
        "-e", "MCP_SERVER_URL=ws://host.docker.internal:9000",
        "-d", "planning-agent"  # Run in detached mode
    ]
    
    try:
        result = subprocess.run(start_cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"❌ Failed to start container: {result.stderr}")
            return False
        
        container_id = result.stdout.strip()
        print(f"✅ Container started: {container_id[:12]}")
        
        # Wait for container to be ready
        print("Waiting for container to be ready...")
        await asyncio.sleep(5)
        
        # Test health endpoint
        print("Testing health endpoint...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8007/health", timeout=10)
                if response.status_code == 200:
                    health_data = response.json()
                    print("✅ Health endpoint working")
                    print(f"   - Status: {health_data['status']}")
                    print(f"   - Agent type: {health_data['agent_type']}")
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
                response = await client.get("http://localhost:8007/capabilities", timeout=10)
                if response.status_code == 200:
                    capabilities_data = response.json()
                    print("✅ Capabilities endpoint working")
                    print(f"   - Capabilities count: {len(capabilities_data['capabilities'])}")
                else:
                    print(f"❌ Capabilities endpoint failed: {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ Capabilities endpoint error: {e}")
            return False
            
        # Test task execution
        print("Testing task execution...")
        try:
            test_task = {
                "action": "plan_research",
                "payload": {
                    "query": "Container test research planning",
                    "scope": "small"
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post("http://localhost:8007/task", json=test_task, timeout=15)
                if response.status_code == 200:
                    task_result = response.json()
                    print("✅ Task execution working")
                    print(f"   - Status: {task_result['status']}")
                    if task_result['status'] == 'completed':
                        print(f"   - Agent ID: {task_result['agent_id']}")
                else:
                    print(f"❌ Task execution failed: {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ Task execution error: {e}")
            return False
        
        print("✅ All container tests passed!")
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Container start timeout")
        return False
        
    finally:
        # Stop container
        print("Stopping container...")
        stop_cmd = ["docker", "stop", container_name]
        try:
            subprocess.run(stop_cmd, capture_output=True, timeout=10)
            print("✅ Container stopped")
        except Exception as e:
            print(f"⚠️ Error stopping container: {e}")

async def main():
    print("🚀 Planning Agent Docker Container Test")
    print("=" * 50)
    
    success = await test_container()
    
    if success:
        print("\n🎉 Docker container test passed!")
        print("✅ Planning Agent is fully containerized and functional")
    else:
        print("\n❌ Docker container test failed")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
