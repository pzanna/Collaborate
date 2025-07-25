#!/usr/bin/env python3
"""
Enhanced MCP Server Test Client - Phase 3.1
Test script to validate the Enhanced MCP Server functionality
"""

import asyncio
import json
import logging
import websockets
from datetime import datetime
import uuid


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MCPTestClient:
    """Test client for Enhanced MCP Server"""
    
    def __init__(self, server_url: str = "ws://localhost:9000"):
        self.server_url = server_url
        self.websocket = None
        self.agent_id = f"test-agent-{uuid.uuid4()}"
        
    async def connect(self):
        """Connect to MCP server"""
        try:
            self.websocket = await websockets.connect(self.server_url)
            logger.info(f"Connected to MCP server at {self.server_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from MCP server"""
        if self.websocket:
            await self.websocket.close()
            logger.info("Disconnected from MCP server")
    
    async def send_message(self, message: dict):
        """Send message to server"""
        if not self.websocket:
            logger.error("Not connected to server")
            return
        
        try:
            await self.websocket.send(json.dumps(message))
            logger.info(f"Sent: {message['type']}")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
    
    async def receive_message(self):
        """Receive message from server"""
        if not self.websocket:
            return None
        
        try:
            message = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
            data = json.loads(message)
            logger.info(f"Received: {data['type']}")
            return data
        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for message")
            return None
        except Exception as e:
            logger.error(f"Failed to receive message: {e}")
            return None
    
    async def register_agent(self):
        """Register as a test agent"""
        registration_message = {
            "type": "agent_register",
            "agent_id": self.agent_id,
            "agent_type": "literature_search",
            "capabilities": ["search", "retrieve", "summarize"],
            "timestamp": datetime.now().isoformat()
        }
        
        await self.send_message(registration_message)
        response = await self.receive_message()
        
        if response and response.get("type") == "registration_confirmed":
            logger.info(f"Agent {self.agent_id} registered successfully")
            return True
        else:
            logger.error("Agent registration failed")
            return False
    
    async def send_heartbeat(self):
        """Send heartbeat to server"""
        heartbeat_message = {
            "type": "heartbeat",
            "agent_id": self.agent_id,
            "timestamp": datetime.now().isoformat()
        }
        
        await self.send_message(heartbeat_message)
        response = await self.receive_message()
        
        if response and response.get("type") == "heartbeat_ack":
            logger.info("Heartbeat acknowledged")
            return True
        else:
            logger.warning("Heartbeat not acknowledged")
            return False
    
    async def submit_test_task(self):
        """Submit a test task"""
        task_message = {
            "type": "task_submit",
            "task_id": str(uuid.uuid4()),
            "task_type": "search",
            "task_data": {
                "query": "machine learning neural networks",
                "limit": 10
            },
            "timestamp": datetime.now().isoformat()
        }
        
        await self.send_message(task_message)
        response = await self.receive_message()
        
        if response and response.get("type") == "task_accepted":
            logger.info(f"Task {response.get('task_id')} accepted")
            return True
        else:
            logger.error("Task submission failed")
            return False
    
    async def listen_for_tasks(self):
        """Listen for incoming task requests"""
        logger.info("Listening for task requests...")
        
        while True:
            try:
                message = await self.receive_message()
                if not message:
                    continue
                
                if message.get("type") == "task_request":
                    # Simulate task processing
                    task_id = message.get("task_id")
                    logger.info(f"Received task request: {task_id}")
                    
                    # Send task result
                    await asyncio.sleep(2)  # Simulate processing time
                    
                    result_message = {
                        "type": "task_result",
                        "task_id": task_id,
                        "status": "completed",
                        "result": {
                            "message": "Task completed successfully",
                            "processed_at": datetime.now().isoformat(),
                            "data": ["result1", "result2", "result3"]
                        },
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    await self.send_message(result_message)
                    logger.info(f"Task {task_id} completed and result sent")
                
            except Exception as e:
                logger.error(f"Error listening for tasks: {e}")
                break


async def test_mcp_server():
    """Test the Enhanced MCP Server functionality"""
    logger.info("Starting Enhanced MCP Server tests...")
    
    # Test 1: Basic Connection
    client = MCPTestClient()
    if not await client.connect():
        logger.error("Test 1 FAILED: Could not connect to server")
        return
    
    logger.info("Test 1 PASSED: Successfully connected to server")
    
    # Test 2: Agent Registration
    if not await client.register_agent():
        logger.error("Test 2 FAILED: Agent registration failed")
        await client.disconnect()
        return
    
    logger.info("Test 2 PASSED: Agent registration successful")
    
    # Test 3: Heartbeat
    if not await client.send_heartbeat():
        logger.error("Test 3 FAILED: Heartbeat failed")
        await client.disconnect()
        return
    
    logger.info("Test 3 PASSED: Heartbeat successful")
    
    # Test 4: Task Submission
    if not await client.submit_test_task():
        logger.error("Test 4 FAILED: Task submission failed")
        await client.disconnect()
        return
    
    logger.info("Test 4 PASSED: Task submission successful")
    
    # Test 5: Listen for tasks (run for a short time)
    logger.info("Test 5: Listening for incoming tasks for 10 seconds...")
    try:
        await asyncio.wait_for(client.listen_for_tasks(), timeout=10.0)
    except asyncio.TimeoutError:
        logger.info("Test 5 PASSED: Task listening completed")
    
    await client.disconnect()
    logger.info("All tests completed successfully!")


async def test_health_endpoint():
    """Test the health check endpoint"""
    import aiohttp
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8080/health') as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Health check PASSED: {data}")
                    return True
                else:
                    logger.error(f"Health check FAILED: Status {response.status}")
                    return False
    except Exception as e:
        logger.error(f"Health check FAILED: {e}")
        return False


if __name__ == "__main__":
    async def main():
        # Test health endpoint
        logger.info("Testing health endpoint...")
        await test_health_endpoint()
        
        # Test MCP functionality
        await test_mcp_server()
    
    asyncio.run(main())
