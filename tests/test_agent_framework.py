"""
Simple test to verify the agent framework is working correctly.
"""

import asyncio
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config.config_manager import ConfigManager
from src.agents.retriever_agent import RetrieverAgent
from src.agents.reasoner_agent import ReasonerAgent
from src.mcp.protocols import ResearchAction


async def test_agent_basic_functionality():
    """Test basic agent functionality."""
    print("🧪 Testing Agent Framework")
    print("=" * 50)
    
    try:
        # Initialize configuration
        config = ConfigManager()
        print("✅ Configuration loaded")
        
        # Test Retriever Agent
        print("\n1. Testing Retriever Agent...")
        retriever = RetrieverAgent(config)
        await retriever.initialize()
        print(f"   Status: {retriever.status}")
        print(f"   Capabilities: {retriever.capabilities}")
        
        # Test Reasoner Agent
        print("\n2. Testing Reasoner Agent...")
        reasoner = ReasonerAgent(config)
        await reasoner.initialize()
        print(f"   Status: {reasoner.status}")
        print(f"   Capabilities: {reasoner.capabilities}")
        
        # Test basic task creation
        print("\n3. Testing task creation...")
        task = ResearchAction(
            task_id="test_task_001",
            context_id="test_context",
            agent_type="retriever",
            action="search_information",
            payload={"query": "test query", "max_results": 5}
        )
        print(f"   Task created: {task.action}")
        print(f"   Task ID: {task.task_id}")
        
        # Clean up
        await retriever.stop()
        await reasoner.stop()
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_agent_basic_functionality())
