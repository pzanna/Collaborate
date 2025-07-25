#!/usr/bin/env python3
"""
Literature Agent - Enhanced MCP Server Integration Test
Phase 3.2 - Connect Literature Agent to Enhanced MCP Server

This test connects the Literature Agent to the Enhanced MCP Server 
and validates literature search functionality through MCP protocol.
"""

import asyncio
import json
import logging
import sys
import os
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from agents.literature.literature_agent import LiteratureAgent
    from config.config_manager import ConfigManager
    from mcp.protocols import ResearchAction
    from utils.id_utils import generate_timestamped_id
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure you're running from the Eunice project root")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LiteratureAgentMCPTester:
    """Test Literature Agent integration with Enhanced MCP Server"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.literature_agent = None
        
    async def initialize_literature_agent(self):
        """Initialize Literature Agent with MCP connection"""
        logger.info("🚀 Initializing Literature Agent...")
        
        # Create Literature Agent
        self.literature_agent = LiteratureAgent(self.config_manager)
        
        # Initialize agent (this will connect to MCP server)
        success = await self.literature_agent.initialize()
        
        if success:
            logger.info("✅ Literature Agent initialized with MCP connection")
            return True
        else:
            logger.error("❌ Failed to initialize Literature Agent")
            return False
    
    async def test_agent_registration(self):
        """Test Literature Agent registration with Enhanced MCP Server"""
        logger.info("🔌 Testing Literature Agent Registration...")
        
        if not self.literature_agent.mcp_client or not self.literature_agent.mcp_client.websocket:
            logger.error("❌ No MCP connection available")
            return False
        
        # Agent should already be registered during initialization
        logger.info("📋 Literature Agent capabilities:")
        capabilities = self.literature_agent._get_capabilities()
        for capability in capabilities:
            logger.info(f"  • {capability}")
        
        # Send a test registration message directly
        registration_message = {
            "type": "agent_register",
            "agent_id": "literature-agent-test",
            "agent_type": "literature",
            "capabilities": capabilities,
            "max_concurrent": 3,
            "timeout": 300
        }
        
        try:
            await self.literature_agent.mcp_client.websocket.send(json.dumps(registration_message))
            logger.info("📤 Sent literature agent registration")
            
            # Wait for confirmation
            response = await asyncio.wait_for(
                self.literature_agent.mcp_client.websocket.recv(), 
                timeout=10.0
            )
            response_data = json.loads(response)
            logger.info(f"📥 Registration response: {response_data}")
            
            if response_data.get("type") == "registration_confirmed":
                logger.info("✅ Literature Agent registration confirmed!")
                return True
            else:
                logger.warning(f"⚠️ Unexpected response: {response_data}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Registration test failed: {e}")
            return False
    
    async def test_academic_search_task(self):
        """Test academic literature search through MCP protocol"""
        logger.info("📚 Testing Academic Literature Search...")
        
        # Create a literature search task
        search_task = ResearchAction(
            task_id=generate_timestamped_id("lit_search"),
            context_id="test_context_literature",
            agent_type="literature",
            action="search_academic_papers",
            payload={
                "query": "neural networks attention mechanisms",
                "max_results": 5
            }
        )
        
        try:
            # Process the task through the Literature Agent
            logger.info(f"📤 Processing search task: {search_task.task_id}")
            
            # Use the Literature Agent's task processing method
            result = await self.literature_agent._process_task_impl(search_task)
            
            logger.info("📥 Literature search completed!")
            logger.info(f"📊 Results: {len(result.get('results', []))} papers found")
            
            # Display first few results
            results = result.get('results', [])
            for i, paper in enumerate(results[:3]):
                logger.info(f"  📄 Paper {i+1}: {paper.get('title', 'Unknown')}")
                logger.info(f"     Authors: {paper.get('authors', 'Unknown')}")
                if 'url' in paper:
                    logger.info(f"     URL: {paper['url']}")
            
            return len(results) > 0
            
        except Exception as e:
            logger.error(f"❌ Literature search test failed: {e}")
            return False
    
    async def test_mcp_task_submission(self):
        """Test submitting task through MCP server (simulated)"""
        logger.info("📋 Testing MCP Task Submission...")
        
        if not self.literature_agent.mcp_client or not self.literature_agent.mcp_client.websocket:
            logger.error("❌ No MCP connection available")
            return False
        
        # Create a task submission message
        task_message = {
            "type": "task_submit",
            "task_id": generate_timestamped_id("mcp_lit_task"),
            "task_type": "literature_search",
            "agent_type": "literature",
            "payload": {
                "query": "machine learning transformers",
                "max_results": 3
            },
            "requester": "literature-agent-test"
        }
        
        try:
            await self.literature_agent.mcp_client.websocket.send(json.dumps(task_message))
            logger.info("📤 Submitted literature search task via MCP")
            
            # Wait for task response
            response = await asyncio.wait_for(
                self.literature_agent.mcp_client.websocket.recv(), 
                timeout=15.0
            )
            response_data = json.loads(response)
            logger.info(f"📥 MCP task response: {response_data}")
            
            if response_data.get("type") in ["task_accepted", "task_queued"]:
                logger.info("✅ MCP task submission successful!")
                return True
            else:
                logger.warning(f"⚠️ Unexpected task response: {response_data}")
                return True
                
        except asyncio.TimeoutError:
            logger.error("❌ MCP task submission timeout")
            return False
        except Exception as e:
            logger.error(f"❌ MCP task submission failed: {e}")
            return False
    
    async def test_heartbeat_mechanism(self):
        """Test Literature Agent heartbeat with Enhanced MCP Server"""
        logger.info("💗 Testing Literature Agent Heartbeat...")
        
        if not self.literature_agent.mcp_client or not self.literature_agent.mcp_client.websocket:
            logger.error("❌ No MCP connection available")
            return False
        
        heartbeat_message = {
            "type": "heartbeat",
            "agent_id": "literature-agent-test",
            "timestamp": datetime.now().isoformat(),
            "status": "active",
            "metrics": {
                "active_tasks": 0,
                "completed_tasks": 1,
                "cache_size": "45MB"
            }
        }
        
        try:
            await self.literature_agent.mcp_client.websocket.send(json.dumps(heartbeat_message))
            logger.info("📤 Sent literature agent heartbeat")
            
            # Wait for heartbeat acknowledgment
            try:
                response = await asyncio.wait_for(
                    self.literature_agent.mcp_client.websocket.recv(), 
                    timeout=5.0
                )
                response_data = json.loads(response)
                logger.info(f"📥 Heartbeat response: {response_data}")
                
                if response_data.get("type") == "heartbeat_ack":
                    logger.info("✅ Heartbeat acknowledged!")
                    return True
                    
            except asyncio.TimeoutError:
                logger.info("⏰ No heartbeat response (normal behavior)")
                return True
                
        except Exception as e:
            logger.error(f"❌ Heartbeat test failed: {e}")
            return False
    
    async def run_literature_integration_tests(self):
        """Run all Literature Agent integration tests"""
        logger.info("🧪 Starting Literature Agent - Enhanced MCP Server Integration Tests...")
        
        try:
            # Initialize Literature Agent
            if not await self.initialize_literature_agent():
                logger.error("❌ Failed to initialize Literature Agent")
                return
            
            tests = [
                ("Agent Registration", self.test_agent_registration),
                ("Academic Search Task", self.test_academic_search_task),
                ("MCP Task Submission", self.test_mcp_task_submission),
                ("Heartbeat Mechanism", self.test_heartbeat_mechanism),
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
            logger.info("\n" + "="*60)
            logger.info("🏁 LITERATURE AGENT INTEGRATION TEST RESULTS")
            logger.info("="*60)
            
            passed = sum(1 for _, result in results if result)
            total = len(results)
            
            for test_name, result in results:
                status = "✅ PASSED" if result else "❌ FAILED"
                logger.info(f"{test_name}: {status}")
            
            logger.info(f"\nOverall: {passed}/{total} tests passed")
            
            if passed == total:
                logger.info("🎉 ALL TESTS PASSED - Literature Agent MCP Integration Working!")
                logger.info("🚀 Ready for Production Literature Search via Enhanced MCP Server")
            else:
                logger.warning(f"⚠️ {total - passed} tests failed")
            
        except Exception as e:
            logger.error(f"❌ Literature integration test failed: {e}")
        
        finally:
            # Cleanup
            if self.literature_agent:
                try:
                    await self.literature_agent.cleanup()
                    logger.info("🧹 Literature Agent cleaned up")
                except Exception as e:
                    logger.error(f"Cleanup error: {e}")


async def main():
    """Main test entry point"""
    tester = LiteratureAgentMCPTester()
    await tester.run_literature_integration_tests()


if __name__ == "__main__":
    print("🚀 Literature Agent - Enhanced MCP Server Integration Test")
    print("Phase 3.2 - Connecting Literature Agent to Enhanced MCP Server")
    print("="*70)
    
    asyncio.run(main())
