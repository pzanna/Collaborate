"""
Simple test to validate Phase 3 agent implementations.
"""

import asyncio
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config.config_manager import ConfigManager
from src.agents.retriever_agent import RetrieverAgent
from src.agents.reasoner_agent import ReasonerAgent
from src.agents.executor_agent import ExecutorAgent
from src.agents.memory_agent import MemoryAgent


async def test_phase3_agents():
    """Test all Phase 3 agents."""
    print("🧪 Phase 3 Agent Validation")
    print("=" * 50)
    
    try:
        # Initialize configuration
        config = ConfigManager()
        print("✅ Configuration loaded")
        
        # Test each agent type
        agents = [
            ("Retriever", RetrieverAgent),
            ("Reasoner", ReasonerAgent),
            ("Executor", ExecutorAgent),
            ("Memory", MemoryAgent)
        ]
        
        results = []
        
        for name, agent_class in agents:
            print(f"\n🔧 Testing {name} Agent...")
            
            try:
                # Create and initialize agent
                agent = agent_class(config)
                await agent.initialize()
                
                print(f"   ✅ {name} Agent initialized successfully")
                print(f"   Status: {agent.status}")
                print(f"   Agent ID: {agent.agent_id}")
                print(f"   Capabilities: {len(agent.capabilities)}")
                
                # Test basic functionality
                status = agent.get_status()
                print(f"   Active tasks: {status.get('active_tasks', 0)}")
                print(f"   Success rate: {status.get('success_rate', 0):.1%}")
                
                # Clean up
                await agent.stop()
                results.append(True)
                
            except Exception as e:
                print(f"   ❌ {name} Agent failed: {e}")
                results.append(False)
        
        # Summary
        print(f"\n📊 Test Results")
        print("-" * 30)
        
        total = len(results)
        passed = sum(results)
        
        for i, (name, _) in enumerate(agents):
            status = "✅ PASS" if results[i] else "❌ FAIL"
            print(f"{name}: {status}")
        
        print(f"\nTotal: {passed}/{total} agents working")
        
        if passed == total:
            print("🎉 Phase 3 Complete! All agents are functional.")
        else:
            print("⚠️  Some agents need attention.")
        
        return passed == total
        
    except Exception as e:
        print(f"❌ Phase 3 test failed: {e}")
        return False


async def main():
    """Run Phase 3 validation."""
    success = await test_phase3_agents()
    
    if success:
        print("\n🚀 Ready for Phase 4: Integration with Research Manager")
    else:
        print("\n🔧 Please fix failing agents before proceeding")


if __name__ == "__main__":
    asyncio.run(main())
