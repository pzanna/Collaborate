#!/usr/bin/env python3
"""
Integration Test for Enhanced MCP Server and API Gateway

Tests the communication between the updated API Gateway MCP client 
and the improved MCP server to verify:
- Enhanced connection management with exponential backoff
- Proper message routing with entity_id/client_id
- Task submission and result handling
- Heartbeat functionality
- Error handling and recovery
- Graceful shutdown and reconnection
"""

import asyncio
import json
import logging
import sys
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

# Add the services to the path for imports
sys.path.append('/Users/paulzanna/GitHub/Eunice/services/api-gateway')
sys.path.append('/Users/paulzanna/GitHub/Eunice/services/mcp-server')

try:
    from mcp_client import MCPClient
    from mcp_server import MCPServer
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure the MCP client and server modules are available")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_integration_test")


class MockLiteratureAgent:
    """Mock literature agent for testing purposes."""
    
    def __init__(self, host: str = "localhost", port: int = 9000):
        self.host = host
        self.port = port
        self.agent_id = f"literature-test-{uuid.uuid4().hex[:8]}"
        self.websocket = None
        self.is_connected = False
        self.running = False
        
    async def connect(self):
        """Connect to MCP server as a mock agent."""
        try:
            import websockets
            
            uri = f"ws://{self.host}:{self.port}"
            self.websocket = await websockets.connect(uri)
            self.is_connected = True
            
            # Register as literature agent
            registration = {
                "type": "agent_register",
                "agent_id": self.agent_id,
                "agent_type": "literature",
                "capabilities": ["search_literature", "process_papers"],
                "timestamp": datetime.now().isoformat()
            }
            
            await self.websocket.send(json.dumps(registration))
            logger.info(f"Mock agent {self.agent_id} registered")
            
            # Start listening for tasks
            asyncio.create_task(self._listen_for_tasks())
            
            return True
        except Exception as e:
            logger.error(f"Mock agent connection failed: {e}")
            return False
    
    async def _listen_for_tasks(self):
        """Listen for task requests from MCP server."""
        try:
            async for message_str in self.websocket:
                message = json.loads(message_str)
                await self._handle_message(message)
        except Exception as e:
            logger.error(f"Mock agent listener error: {e}")
            self.is_connected = False
    
    async def _handle_message(self, message: Dict[str, Any]):
        """Handle incoming messages."""
        message_type = message.get("type")
        
        if message_type == "task_request":
            await self._handle_task_request(message)
        elif message_type == "registration_confirmed":
            logger.info(f"Mock agent {self.agent_id} registration confirmed")
    
    async def _handle_task_request(self, message: Dict[str, Any]):
        """Handle task request and send mock result."""
        task_id = message.get("task_id")
        task_type = message.get("task_type")
        data = message.get("data", {})
        
        logger.info(f"Mock agent processing task {task_id}: {task_type}")
        
        # Simulate processing time
        await asyncio.sleep(0.5)
        
        # Send mock result
        result = {
            "type": "task_result",
            "task_id": task_id,
            "status": "completed",
            "result": {
                "action": task_type,
                "data": data,
                "processed_by": self.agent_id,
                "timestamp": datetime.now().isoformat(),
                "mock": True
            },
            "agent_id": self.agent_id,
            "timestamp": datetime.now().isoformat()
        }
        
        await self.websocket.send(json.dumps(result))
        logger.info(f"Mock agent sent result for task {task_id}")
    
    async def disconnect(self):
        """Disconnect the mock agent."""
        if self.websocket:
            await self.websocket.close()
        self.is_connected = False


class MCPIntegrationTest:
    """Integration test suite for MCP server and API Gateway."""
    
    def __init__(self):
        self.server = None
        self.client = None
        self.mock_agent = None
        self.test_results = []
        
    async def setup(self):
        """Setup test environment."""
        logger.info("Setting up MCP integration test environment...")
        
        # Start MCP server
        self.server = MCPServer(host="localhost", port=9001)  # Use different port for testing
        await self.server.start()
        logger.info("MCP server started for testing")
        
        # Give server time to start
        await asyncio.sleep(1)
        
        # Create API Gateway client
        config = {
            "max_retries": 5,
            "base_retry_delay": 1,
            "heartbeat_interval": 10,
            "ping_timeout": 5
        }
        self.client = MCPClient(host="localhost", port=9001, config=config)
        
        # Create mock literature agent
        self.mock_agent = MockLiteratureAgent(host="localhost", port=9001)
        
        logger.info("Test environment setup complete")
    
    async def teardown(self):
        """Cleanup test environment."""
        logger.info("Tearing down test environment...")
        
        if self.mock_agent:
            await self.mock_agent.disconnect()
        
        if self.client:
            await self.client.disconnect()
        
        if self.server:
            await self.server.stop()
        
        logger.info("Test environment cleanup complete")
    
    def log_test_result(self, test_name: str, success: bool, message: str = ""):
        """Log test result."""
        status = "PASS" if success else "FAIL"
        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        logger.info(f"Test {test_name}: {status} - {message}")
    
    async def test_api_gateway_connection(self):
        """Test API Gateway connection to MCP server."""
        try:
            success = await self.client.connect()
            self.log_test_result(
                "api_gateway_connection", 
                success, 
                "API Gateway connected to MCP server" if success else "Connection failed"
            )
            return success
        except Exception as e:
            self.log_test_result("api_gateway_connection", False, f"Exception: {e}")
            return False
    
    async def test_mock_agent_connection(self):
        """Test mock agent connection to MCP server."""
        try:
            success = await self.mock_agent.connect()
            await asyncio.sleep(1)  # Give time for registration
            
            self.log_test_result(
                "mock_agent_connection", 
                success, 
                "Mock agent connected and registered" if success else "Connection failed"
            )
            return success
        except Exception as e:
            self.log_test_result("mock_agent_connection", False, f"Exception: {e}")
            return False
    
    async def test_task_submission_and_result(self):
        """Test complete task submission and result flow."""
        try:
            # Submit a research action
            task_data = {
                "task_id": str(uuid.uuid4()),
                "agent_type": "literature",
                "action": "search_literature",
                "payload": {
                    "query": "machine learning ethics",
                    "max_results": 10
                },
                "context_id": str(uuid.uuid4())
            }
            
            # Send research action
            success = await self.client.send_research_action(task_data)
            if not success:
                self.log_test_result("task_submission", False, "Failed to submit research action")
                return False
            
            # Wait for result
            task_id = task_data["task_id"]
            result = await self.client.wait_for_task_result(task_id, timeout=10.0)
            
            if result and result.get("status") == "completed":
                self.log_test_result(
                    "task_submission_and_result", 
                    True, 
                    f"Task {task_id} completed successfully"
                )
                return True
            else:
                self.log_test_result(
                    "task_submission_and_result", 
                    False, 
                    f"Task failed or timed out: {result}"
                )
                return False
                
        except Exception as e:
            self.log_test_result("task_submission_and_result", False, f"Exception: {e}")
            return False
    
    async def test_server_stats(self):
        """Test server statistics request."""
        try:
            stats = await self.client.get_server_stats()
            
            if stats:
                self.log_test_result(
                    "server_stats", 
                    True, 
                    f"Retrieved server stats: {stats}"
                )
                return True
            else:
                self.log_test_result("server_stats", False, "No stats returned")
                return False
                
        except Exception as e:
            self.log_test_result("server_stats", False, f"Exception: {e}")
            return False
    
    async def test_connection_info(self):
        """Test connection information retrieval."""
        try:
            info = self.client.connection_info
            
            expected_fields = ["host", "port", "client_id", "is_connected"]
            has_required_fields = all(field in info for field in expected_fields)
            
            if has_required_fields and info.get("is_connected"):
                self.log_test_result(
                    "connection_info", 
                    True, 
                    f"Connection info valid: {info}"
                )
                return True
            else:
                self.log_test_result(
                    "connection_info", 
                    False, 
                    f"Invalid connection info: {info}"
                )
                return False
                
        except Exception as e:
            self.log_test_result("connection_info", False, f"Exception: {e}")
            return False
    
    async def test_health_check(self):
        """Test health check functionality."""
        try:
            health = await self.client.health_check()
            
            if health and health.get("status") == "healthy":
                self.log_test_result(
                    "health_check", 
                    True, 
                    f"Health check passed: {health}"
                )
                return True
            else:
                self.log_test_result(
                    "health_check", 
                    False, 
                    f"Health check failed: {health}"
                )
                return False
                
        except Exception as e:
            self.log_test_result("health_check", False, f"Exception: {e}")
            return False
    
    async def test_reconnection(self):
        """Test reconnection capability."""
        try:
            # Force disconnect by closing websocket if it exists
            if self.client.websocket:
                try:
                    await self.client.websocket.close()
                except:
                    pass
                self.client.is_connected = False
            
            # Wait a moment
            await asyncio.sleep(2)
            
            # Try to send a message (should trigger reconnection)
            success = await self.client.send_research_action({
                "task_id": str(uuid.uuid4()),
                "agent_type": "literature", 
                "action": "search_literature",
                "payload": {"query": "test reconnection"}
            })
            
            if success and self.client.is_connected:
                self.log_test_result(
                    "reconnection", 
                    True, 
                    "Successfully reconnected and sent message"
                )
                return True
            else:
                self.log_test_result(
                    "reconnection", 
                    False, 
                    "Failed to reconnect"
                )
                return False
                
        except Exception as e:
            self.log_test_result("reconnection", False, f"Exception: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all integration tests."""
        logger.info("Starting MCP integration tests...")
        
        tests = [
            self.test_api_gateway_connection,
            self.test_mock_agent_connection,
            self.test_task_submission_and_result,
            self.test_server_stats,
            self.test_connection_info,
            self.test_health_check,
            self.test_reconnection
        ]
        
        for test in tests:
            try:
                await test()
                await asyncio.sleep(1)  # Brief pause between tests
            except Exception as e:
                logger.error(f"Test {test.__name__} failed with exception: {e}")
        
        # Print summary
        self.print_test_summary()
    
    def print_test_summary(self):
        """Print test results summary."""
        print("\n" + "="*80)
        print("MCP INTEGRATION TEST RESULTS")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["status"] == "PASS")
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print("-"*80)
        
        for result in self.test_results:
            status_symbol = "✓" if result["status"] == "PASS" else "✗"
            print(f"{status_symbol} {result['test']}: {result['status']} - {result['message']}")
        
        print("="*80)
        
        if failed_tests == 0:
            print("🎉 ALL TESTS PASSED! MCP integration is working correctly.")
        else:
            print(f"⚠️  {failed_tests} test(s) failed. Please review the results above.")
        print()


async def main():
    """Main test execution."""
    test_suite = MCPIntegrationTest()
    
    try:
        await test_suite.setup()
        await test_suite.run_all_tests()
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
    finally:
        await test_suite.teardown()


if __name__ == "__main__":
    print("MCP Integration Test Suite")
    print("Testing enhanced API Gateway MCP client with improved MCP server")
    print("="*80)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest suite interrupted by user")
    except Exception as e:
        print(f"Test suite failed: {e}")
        sys.exit(1)
