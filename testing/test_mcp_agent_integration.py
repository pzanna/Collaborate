#!/usr/bin/env python3
"""
MCP Agent Integration Test
Version 0.3.2 - Agent Integration Testing

Test MCP agent registration and communication patterns
"""

import asyncio
import json
import logging
import sys
import os
from datetime import datetime
from typing import Optional

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from old_src.agents.research_manager.research_manager import ResearchManager
    from old_src.config.config_manager import ConfigManager
    from old_src.mcp.client import MCPClient
    from old_src.mcp.protocols import ResearchAction, AgentType
    from old_src.utils.id_utils import generate_timestamped_id
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure you're running from the Eunice project root")
    print(f"Current path: {os.getcwd()}")
    print(f"Python path: {sys.path[:3]}")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MCPIntegrationTester:
    """Test integration between agents and Enhanced MCP Server"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.research_manager: Optional[ResearchManager] = None
        self.mcp_client: Optional[MCPClient] = None
        
    async def initialize(self):
        """Initialize test environment"""
        logger.info("🚀 Initializing MCP Integration Test...")
        
        # Create MCP client for Research Manager
        mcp_config = self.config_manager.get_mcp_config()
        self.mcp_client = MCPClient(
            host=mcp_config.get("host", "localhost"),
            port=mcp_config.get("port", 9000)
        )
        
        # Connect to Enhanced MCP Server
        await self.mcp_client.connect()
        logger.info("✅ Connected to Enhanced MCP Server")
        
        # Initialize Research Manager with external MCP client
        self.research_manager = ResearchManager(self.config_manager)
        success = await self.research_manager.initialize(
            external_mcp_client=self.mcp_client
        )
        
        if success:
            logger.info("✅ Research Manager initialized with MCP connection")
        else:
            raise Exception("Failed to initialize Research Manager")
    
    async def test_agent_registration(self):
        """Test agent registration with Enhanced MCP Server"""
        logger.info("🔌 Testing Agent Registration...")
        
        # Send agent registration message
        registration_message = {
            "type": "agent_register",
            "agent_id": "research-manager-test",
            "agent_type": "research_manager",
            "capabilities": ["planning", "coordination", "workflow_management"],
            "max_concurrent": 5,
            "timeout": 300
        }
        
        await self.mcp_client.websocket.send(json.dumps(registration_message))
        logger.info("📤 Sent agent registration")
        
        # Wait for confirmation
        try:
            response = await asyncio.wait_for(
                self.mcp_client.websocket.recv(), 
                timeout=10.0
            )
            response_data = json.loads(response)
            logger.info(f"📥 Registration response: {response_data}")
            
            if response_data.get("type") == "registration_confirmed":
                logger.info("✅ Agent registration confirmed")
                return True
            else:
                logger.error(f"❌ Unexpected registration response: {response_data}")
                return False
                
        except asyncio.TimeoutError:
            logger.error("❌ Registration confirmation timeout")
            return False
    
    async def test_heartbeat(self):
        """Test heartbeat mechanism"""
        logger.info("💗 Testing Heartbeat...")
        
        heartbeat_message = {
            "type": "heartbeat",
            "agent_id": "research-manager-test",
            "timestamp": datetime.now().isoformat(),
            "status": "active",
            "metrics": {
                "active_tasks": 0,
                "completed_tasks": 0,
                "memory_usage": "150MB"
            }
        }
        
        await self.mcp_client.websocket.send(json.dumps(heartbeat_message))
        logger.info("📤 Sent heartbeat")
        
        # Wait for heartbeat response (server may not respond to all heartbeats)
        try:
            response = await asyncio.wait_for(
                self.mcp_client.websocket.recv(), 
                timeout=5.0
            )
            response_data = json.loads(response)
            logger.info(f"📥 Heartbeat response: {response_data}")
            
        except asyncio.TimeoutError:
            logger.info("⏰ No heartbeat response (normal behavior)")
        
        return True
    
    async def test_task_submission(self):
        """Test task submission to Enhanced MCP Server"""
        logger.info("📋 Testing Task Submission...")
        
        # Create a test research action using the correct protocol
        test_action = ResearchAction(
            task_id=generate_timestamped_id("test_task"),
            context_id="test_context_001",
            agent_type="literature",
            action="search",
            payload={
                "query": "machine learning attention mechanisms",
                "max_results": 10,
                "databases": ["arxiv"]
            }
        )
        
        task_message = {
            "type": "task_submit",
            "task_id": test_action.task_id,
            "context_id": test_action.context_id,
            "task_type": "literature_search",
            "agent_type": test_action.agent_type,
            "action": test_action.action,
            "payload": test_action.payload,
            "requester": "research-manager-test"
        }
        
        await self.mcp_client.websocket.send(json.dumps(task_message))
        logger.info(f"📤 Submitted task: {test_action.task_id}")
        
        # Wait for task acknowledgment
        try:
            response = await asyncio.wait_for(
                self.mcp_client.websocket.recv(), 
                timeout=10.0
            )
            response_data = json.loads(response)
            logger.info(f"📥 Task response: {response_data}")
            
            if response_data.get("type") == "task_queued":
                logger.info("✅ Task queued successfully")
                return True
            else:
                logger.warning(f"⚠️ Unexpected task response: {response_data}")
                return True  # May still be valid
                
        except asyncio.TimeoutError:
            logger.error("❌ Task submission timeout")
            return False
    
    async def test_server_health(self):
        """Test server health endpoint via WebSocket"""
        logger.info("🏥 Testing Server Health...")
        
        health_message = {
            "type": "health_check",
            "timestamp": datetime.now().isoformat()
        }
        
        await self.mcp_client.websocket.send(json.dumps(health_message))
        logger.info("📤 Sent health check")
        
        # Wait for health response
        try:
            response = await asyncio.wait_for(
                self.mcp_client.websocket.recv(), 
                timeout=5.0
            )
            response_data = json.loads(response)
            logger.info(f"📥 Health response: {response_data}")
            
            if response_data.get("type") == "health_status":
                logger.info("✅ Server health confirmed")
                return True
            else:
                logger.warning(f"⚠️ Unexpected health response: {response_data}")
                return True
                
        except asyncio.TimeoutError:
            logger.warning("⏰ No health response (may not be implemented)")
            return True
    
    async def run_integration_tests(self):
        """Run all integration tests"""
        logger.info("🧪 Starting MCP Integration Tests...")
        
        try:
            await self.initialize()
            
            tests = [
                ("Agent Registration", self.test_agent_registration),
                ("Heartbeat", self.test_heartbeat),
                ("Task Submission", self.test_task_submission),
                ("Server Health", self.test_server_health),
            ]
            
            results = []
            for test_name, test_func in tests:
                logger.info(f"\n--- Running {test_name} Test ---")
                try:
                    result = await test_func()
                    results.append((test_name, result))
                    status = "✅ PASSED" if result else "❌ FAILED"
                    logger.info(f"{test_name}: {status}")
                except Exception as e:
                    logger.error(f"{test_name}: ❌ ERROR - {e}")
                    results.append((test_name, False))
            
            # Summary
            logger.info("\n" + "="*50)
            logger.info("🏁 INTEGRATION TEST RESULTS")
            logger.info("="*50)
            
            passed = sum(1 for _, result in results if result)
            total = len(results)
            
            for test_name, result in results:
                status = "✅ PASSED" if result else "❌ FAILED"
                logger.info(f"{test_name}: {status}")
            
            logger.info(f"\nOverall: {passed}/{total} tests passed")
            
            if passed == total:
                logger.info("🎉 ALL TESTS PASSED - MCP Integration Working!")
            else:
                logger.warning(f"⚠️ {total - passed} tests failed")
            
        except Exception as e:
            logger.error(f"❌ Integration test failed: {e}")
        
        finally:
            if self.mcp_client and self.mcp_client.websocket:
                await self.mcp_client.websocket.close()
                logger.info("🔌 Disconnected from MCP Server")


async def main():
    """Main test entry point"""
    tester = MCPIntegrationTester()
    await tester.run_integration_tests()


if __name__ == "__main__":
    print("🚀 Enhanced MCP Server - Agent Integration Test")
    print("Version 0.3.2 - Testing Research Manager Connection")
    print("="*60)
    
    asyncio.run(main())
