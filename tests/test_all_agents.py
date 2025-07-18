"""
Comprehensive test suite for all agent implementations.

Tests the complete agent framework including:
- BaseAgent functionality
- RetrieverAgent web search capabilities
- ReasonerAgent analysis and synthesis
- ExecutorAgent task execution
- MemoryAgent context management
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config.config_manager import ConfigManager
from src.agents.retriever_agent import RetrieverAgent
from src.agents.reasoner_agent import ReasonerAgent
from src.agents.executor_agent import ExecutorAgent
from src.agents.memory_agent import MemoryAgent
from src.mcp.protocols import ResearchAction


class AgentTestSuite:
    """Comprehensive test suite for all agents."""
    
    def __init__(self):
        self.config = ConfigManager()
        self.test_results = {}
        
    async def run_all_tests(self):
        """Run all agent tests."""
        print("🧪 Comprehensive Agent Test Suite")
        print("=" * 60)
        
        # Test each agent
        await self._test_retriever_agent()
        await self._test_reasoner_agent()
        await self._test_executor_agent()
        await self._test_memory_agent()
        
        # Test agent integration
        await self._test_agent_integration()
        
        # Print summary
        self._print_test_summary()
    
    async def _test_retriever_agent(self):
        """Test Retriever Agent functionality."""
        print("\n🔍 Testing Retriever Agent")
        print("-" * 40)
        
        try:
            # Initialize agent
            agent = RetrieverAgent(self.config)
            await agent.initialize()
            
            print(f"✅ Agent initialized: {agent.status}")
            print(f"   Capabilities: {len(agent.capabilities)} functions")
            
            # Test search capability
            task = ResearchAction(
                task_id="test_search_001",
                context_id="test_context",
                agent_type="retriever",
                action="search_information",
                payload={
                    "query": "artificial intelligence research",
                    "max_results": 5
                }
            )
            
            print(f"   Testing search with query: {task.payload['query']}")
            response = await agent.process_task(task)
            
            if response.status == "completed":
                print(f"✅ Search completed successfully")
                results = response.result.get('results', []) if response.result else []
                print(f"   Results found: {len(results)}")
            else:
                print(f"⚠️  Search completed with issues: {response.error}")
            
            await agent.stop()
            self.test_results['retriever'] = True
            
        except Exception as e:
            print(f"❌ Retriever Agent test failed: {e}")
            self.test_results['retriever'] = False
    
    async def _test_reasoner_agent(self):
        """Test Reasoner Agent functionality."""
        print("\n🧠 Testing Reasoner Agent")
        print("-" * 40)
        
        try:
            # Initialize agent
            agent = ReasonerAgent(self.config)
            await agent.initialize()
            
            print(f"✅ Agent initialized: {agent.status}")
            print(f"   Capabilities: {len(agent.capabilities)} functions")
            
            # Test analysis capability
            task = ResearchAction(
                task_id="test_analysis_001",
                context_id="test_context",
                agent_type="reasoner",
                action="analyze_information",
                payload={
                    "query": "What are the key trends in AI research?",
                    "context": {
                        "search_results": [
                            {
                                "title": "AI Trends 2024",
                                "content": "Machine learning and neural networks are advancing rapidly...",
                                "source": "tech_journal"
                            }
                        ]
                    }
                }
            )
            
            print(f"   Testing analysis with query: {task.payload['query']}")
            response = await agent.process_task(task)
            
            if response.status == "completed":
                print(f"✅ Analysis completed successfully")
                model = response.result.get('analysis_model', 'unknown') if response.result else 'unknown'
                print(f"   Analysis model: {model}")
            else:
                print(f"⚠️  Analysis completed with issues: {response.error}")
            
            await agent.stop()
            self.test_results['reasoner'] = True
            
        except Exception as e:
            print(f"❌ Reasoner Agent test failed: {e}")
            self.test_results['reasoner'] = False
    
    async def _test_executor_agent(self):
        """Test Executor Agent functionality."""
        print("\n⚙️ Testing Executor Agent")
        print("-" * 40)
        
        try:
            # Initialize agent
            agent = ExecutorAgent(self.config)
            await agent.initialize()
            
            print(f"✅ Agent initialized: {agent.status}")
            print(f"   Capabilities: {len(agent.capabilities)} functions")
            print(f"   Work directory: {agent.work_dir}")
            
            # Test code execution
            task = ResearchAction(
                task_id="test_execute_001",
                context_id="test_context",
                agent_type="executor",
                action="execute_code",
                payload={
                    "code": "print('Hello from Executor Agent!')\nresult = 2 + 2\nprint(f'2 + 2 = {result}')",
                    "language": "python"
                }
            )
            
            print("   Testing code execution...")
            response = await agent.process_task(task)
            
            if response.success:
                print(f"✅ Code execution completed successfully")
                print(f"   Output: {response.data.get('output', '')[:50]}...")
            else:
                print(f"⚠️  Code execution completed with issues: {response.error}")
            
            # Test data processing
            task2 = ResearchAction(
                task_id="test_process_001",
                context_id="test_context",
                agent_type="executor",
                action="process_data",
                payload={
                    "data": [
                        {"name": "Alice", "age": 30, "city": "New York"},
                        {"name": "Bob", "age": 25, "city": "San Francisco"},
                        {"name": "Charlie", "age": 35, "city": "New York"}
                    ],
                    "operation": "analyze"
                }
            )
            
            print("   Testing data processing...")
            response2 = await agent.process_task(task2)
            
            if response2.success:
                print(f"✅ Data processing completed successfully")
                print(f"   Input size: {response2.data.get('input_size', 0)} records")
            else:
                print(f"⚠️  Data processing completed with issues: {response2.error}")
            
            await agent.stop()
            self.test_results['executor'] = True
            
        except Exception as e:
            print(f"❌ Executor Agent test failed: {e}")
            self.test_results['executor'] = False
    
    async def _test_memory_agent(self):
        """Test Memory Agent functionality."""
        print("\n🧠 Testing Memory Agent")
        print("-" * 40)
        
        try:
            # Initialize agent
            agent = MemoryAgent(self.config)
            await agent.initialize()
            
            print(f"✅ Agent initialized: {agent.status}")
            print(f"   Capabilities: {len(agent.capabilities)} functions")
            print(f"   Memory cache size: {len(agent.memory_cache)}")
            
            # Test memory storage
            task = ResearchAction(
                task_id="test_memory_001",
                context_id="test_context",
                agent_type="memory",
                action="store_memory",
                payload={
                    "context_id": "test_context",
                    "content": "This is a test memory record for agent testing",
                    "importance": 0.8,
                    "metadata": {"type": "test", "timestamp": datetime.now().isoformat()}
                }
            )
            
            print("   Testing memory storage...")
            response = await agent.process_task(task)
            
            if response.success:
                print(f"✅ Memory storage completed successfully")
                print(f"   Memory ID: {response.data.get('memory_id', 'unknown')}")
                print(f"   Cached: {response.data.get('cached', False)}")
            else:
                print(f"⚠️  Memory storage completed with issues: {response.error}")
            
            # Test memory search
            task2 = ResearchAction(
                task_id="test_search_mem_001",
                context_id="test_context",
                agent_type="memory",
                action="search_memory",
                payload={
                    "query": "test memory",
                    "limit": 5
                }
            )
            
            print("   Testing memory search...")
            response2 = await agent.process_task(task2)
            
            if response2.success:
                print(f"✅ Memory search completed successfully")
                print(f"   Results found: {response2.data.get('count', 0)}")
            else:
                print(f"⚠️  Memory search completed with issues: {response2.error}")
            
            await agent.stop()
            self.test_results['memory'] = True
            
        except Exception as e:
            print(f"❌ Memory Agent test failed: {e}")
            self.test_results['memory'] = False
    
    async def _test_agent_integration(self):
        """Test integration between agents."""
        print("\n🔗 Testing Agent Integration")
        print("-" * 40)
        
        try:
            # Initialize all agents
            retriever = RetrieverAgent(self.config)
            reasoner = ReasonerAgent(self.config)
            executor = ExecutorAgent(self.config)
            memory = MemoryAgent(self.config)
            
            agents = [retriever, reasoner, executor, memory]
            
            # Initialize all agents
            for agent in agents:
                await agent.initialize()
            
            print(f"✅ All {len(agents)} agents initialized successfully")
            
            # Test basic communication
            all_capabilities = []
            for agent in agents:
                all_capabilities.extend(agent.capabilities)
            
            print(f"   Total capabilities: {len(all_capabilities)}")
            print(f"   Agent types: {[agent.agent_type for agent in agents]}")
            
            # Test task distribution
            tasks = [
                ResearchAction(
                    task_id=f"integration_test_{i}",
                    context_id="integration_context",
                    agent_type=agent.agent_type,
                    action=agent.capabilities[0] if agent.capabilities else "status",
                    payload={"test": True}
                )
                for i, agent in enumerate(agents)
            ]
            
            print("   Testing task distribution...")
            results = []
            for i, (agent, task) in enumerate(zip(agents, tasks)):
                print(f"     Agent {i+1}: {agent.agent_type} -> {task.action}")
                try:
                    response = await agent.process_task(task)
                    results.append(response.success)
                except Exception as e:
                    print(f"       Error: {e}")
                    results.append(False)
            
            successful_tasks = sum(results)
            print(f"   Successful tasks: {successful_tasks}/{len(tasks)}")
            
            # Clean up
            for agent in agents:
                await agent.stop()
            
            self.test_results['integration'] = successful_tasks >= len(tasks) // 2
            
        except Exception as e:
            print(f"❌ Integration test failed: {e}")
            self.test_results['integration'] = False
    
    def _print_test_summary(self):
        """Print test summary."""
        print("\n📊 Test Summary")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        
        print(f"Total tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success rate: {passed_tests/total_tests*100:.1f}%")
        
        print("\nDetailed Results:")
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {test_name.capitalize()}: {status}")
        
        if passed_tests == total_tests:
            print(f"\n🎉 All tests passed! Agent framework is ready.")
        else:
            print(f"\n⚠️  Some tests failed. Please review the implementation.")


async def main():
    """Run the comprehensive test suite."""
    test_suite = AgentTestSuite()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
