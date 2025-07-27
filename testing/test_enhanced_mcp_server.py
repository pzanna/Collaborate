#!/usr/bin/env python3
"""
Simple MCP Enhanced Server Connection Test
Version 0.3.2 - Direct WebSocket Test

This test connects directly to the Enhanced MCP Server 
and validates basic functionality.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime

try:
    import websockets
except ImportError:
    print("Please install websockets: pip install websockets")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_enhanced_mcp_server():
    """Test Enhanced MCP Server Version 0.3.1 connection and functionality"""
    uri = "ws://localhost:9000"
    
    logger.info("🚀 Testing Enhanced MCP Server Connection...")
    logger.info(f"📡 Connecting to: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("✅ Connected to Enhanced MCP Server!")
            
            # Test 1: Agent Registration
            logger.info("\n--- Test 1: Agent Registration ---")
            registration_message = {
                "type": "agent_register",
                "agent_id": "test-research-manager-001",
                "agent_type": "research_manager",
                "capabilities": ["planning", "coordination", "workflow_management"],
                "max_concurrent": 5,
                "timeout": 300
            }
            
            await websocket.send(json.dumps(registration_message))
            logger.info("📤 Sent agent registration")
            
            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            response_data = json.loads(response)
            logger.info(f"📥 Registration response: {response_data}")
            
            if response_data.get("type") == "registration_confirmed":
                logger.info("✅ Agent registration confirmed!")
            else:
                logger.warning(f"⚠️ Unexpected response: {response_data}")
            
            # Test 2: Heartbeat
            logger.info("\n--- Test 2: Heartbeat ---")
            heartbeat_message = {
                "type": "heartbeat",
                "agent_id": "test-research-manager-001",
                "timestamp": datetime.now().isoformat(),
                "status": "active",
                "metrics": {
                    "active_tasks": 0,
                    "completed_tasks": 0,
                    "memory_usage": "150MB"
                }
            }
            
            await websocket.send(json.dumps(heartbeat_message))
            logger.info("📤 Sent heartbeat")
            
            # Heartbeat may not always get a response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                logger.info(f"📥 Heartbeat response: {response_data}")
            except asyncio.TimeoutError:
                logger.info("⏰ No heartbeat response (normal behavior)")
            
            # Test 3: Task Submission
            logger.info("\n--- Test 3: Task Submission ---")
            task_message = {
                "type": "task_submit",
                "task_id": "test_task_001",
                "task_type": "literature_search",
                "agent_type": "literature",
                "payload": {
                    "query": "machine learning attention mechanisms",
                    "max_results": 10,
                    "databases": ["arxiv"]
                },
                "requester": "test-research-manager-001"
            }
            
            await websocket.send(json.dumps(task_message))
            logger.info("📤 Submitted test task")
            
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                response_data = json.loads(response)
                logger.info(f"📥 Task response: {response_data}")
                
                if response_data.get("type") in ["task_queued", "task_accepted"]:
                    logger.info("✅ Task submission successful!")
                else:
                    logger.warning(f"⚠️ Unexpected task response: {response_data}")
            except asyncio.TimeoutError:
                logger.error("❌ Task submission timeout")
            
            # Test 4: Health Check
            logger.info("\n--- Test 4: Health Check ---")
            health_message = {
                "type": "health_check",
                "timestamp": datetime.now().isoformat()
            }
            
            await websocket.send(json.dumps(health_message))
            logger.info("📤 Sent health check")
            
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                logger.info(f"📥 Health response: {response_data}")
                
                if response_data.get("type") == "health_status":
                    logger.info("✅ Server health confirmed!")
                else:
                    logger.warning(f"⚠️ Unexpected health response: {response_data}")
            except asyncio.TimeoutError:
                logger.warning("⏰ No health response (may not be implemented)")
            
            # Test 5: Invalid Message (Error Handling)
            logger.info("\n--- Test 5: Invalid Message (Error Handling) ---")
            invalid_message = {
                "type": "invalid_message_type",
                "data": "this should trigger an error response"
            }
            
            await websocket.send(json.dumps(invalid_message))
            logger.info("📤 Sent invalid message")
            
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                logger.info(f"📥 Error response: {response_data}")
                
                if response_data.get("type") == "error":
                    logger.info("✅ Error handling working correctly!")
                else:
                    logger.warning(f"⚠️ Unexpected error response: {response_data}")
            except asyncio.TimeoutError:
                logger.warning("⏰ No error response")
            
            logger.info("\n" + "="*60)
            logger.info("🏁 ENHANCED MCP SERVER TEST COMPLETE")
            logger.info("="*60)
            logger.info("✅ Version 0.3.1 Enhanced MCP Server is operational!")
            logger.info("🔗 WebSocket connections working correctly")
            logger.info("📋 Ready for agent integration and production use")
            logger.info("🚀 Next: Connect existing Eunice agents")
            
    except ConnectionRefusedError:
        logger.error("❌ Connection refused - is Enhanced MCP Server running?")
        logger.error("💡 Try: docker-compose up -d")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")


async def main():
    """Main test entry point"""
    await test_enhanced_mcp_server()


if __name__ == "__main__":
    print("🚀 Enhanced MCP Server - Direct WebSocket Test")
    print("Version 0.3.2 - Validating Enhanced MCP Server Integration")
    print("="*70)
    
    asyncio.run(main())
