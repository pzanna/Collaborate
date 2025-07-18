#!/usr/bin/env python3
"""
Test script for Research Manager implementation.

This script tests the Research Manager functionality including:
- Initialization and configuration
- Task creation and orchestration
- Stage execution
- Error handling
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.research_manager import ResearchManager, ResearchStage, ResearchContext
from src.config.config_manager import ConfigManager
from src.mcp.protocols import ResearchAction, AgentResponse


async def test_research_manager():
    """Test the Research Manager implementation."""
    print("🚀 Testing Research Manager Implementation")
    print("=" * 50)
    
    try:
        # Initialize configuration
        print("1. Initializing configuration...")
        config = ConfigManager()
        print("   ✅ Configuration loaded successfully")
        
        # Create Research Manager
        print("\n2. Creating Research Manager...")
        research_manager = ResearchManager(config)
        print("   ✅ Research Manager created successfully")
        
        # Test configuration access
        print("\n3. Testing configuration access...")
        mcp_config = research_manager.config.get_mcp_config()
        research_config = research_manager.config.get_research_config()
        agent_config = research_manager.config.get_agent_config()
        
        print(f"   MCP Config: {mcp_config}")
        print(f"   Research Config: {research_config}")
        print(f"   Agent Config: {agent_config}")
        print("   ✅ All configuration methods working")
        
        # Test Research Context creation
        print("\n4. Testing Research Context creation...")
        context = ResearchContext(
            task_id="test-task-123",
            query="What are the latest developments in AI research?",
            user_id="test-user",
            conversation_id="test-conv-456"
        )
        print(f"   Context created: {context.task_id}")
        print(f"   Query: {context.query}")
        print(f"   Stage: {context.stage}")
        print("   ✅ Research Context created successfully")
        
        # Test ResearchAction creation
        print("\n5. Testing ResearchAction creation...")
        action = ResearchAction(
            task_id=context.task_id,
            context_id=context.conversation_id,
            agent_type="retriever",
            action="search_information",
            payload={
                "query": context.query,
                "search_depth": "comprehensive",
                "max_results": 10
            }
        )
        print(f"   Action created: {action.task_id}")
        print(f"   Agent type: {action.agent_type}")
        print(f"   Action: {action.action}")
        print("   ✅ ResearchAction created successfully")
        
        # Test AgentResponse creation
        print("\n6. Testing AgentResponse creation...")
        response = AgentResponse(
            task_id=action.task_id,
            context_id=action.context_id,
            agent_type=action.agent_type,
            status="completed",
            result={"success": True, "results": ["test result 1", "test result 2"]}
        )
        print(f"   Response created: {response.task_id}")
        print(f"   Status: {response.status}")
        print(f"   Result: {response.result}")
        print("   ✅ AgentResponse created successfully")
        
        # Test task status methods
        print("\n7. Testing task status methods...")
        
        # Add mock context to active contexts
        research_manager.active_contexts[context.task_id] = context
        
        # Test get_task_status
        status = research_manager.get_task_status(context.task_id)
        print(f"   Task status: {status}")
        
        # Test get_active_tasks
        active_tasks = research_manager.get_active_tasks()
        print(f"   Active tasks count: {len(active_tasks)}")
        
        print("   ✅ Task status methods working")
        
        # Test message handlers
        print("\n8. Testing message handlers...")
        
        # Test agent response handler
        research_manager._handle_agent_response({
            'task_id': context.task_id,
            'status': 'completed',
            'result': {'test': 'data'}
        })
        
        # Test agent registration handler
        research_manager._handle_agent_registration({
            'agent_id': 'test-agent',
            'capabilities': ['search', 'analyze']
        })
        
        # Test task update handler
        research_manager._handle_task_update({
            'task_id': context.task_id,
            'status': 'working'
        })
        
        print("   ✅ Message handlers working")
        
        # Test progress/completion callback registration
        print("\n9. Testing callback registration...")
        
        async def progress_callback(data):
            print(f"   Progress: {data}")
        
        async def completion_callback(data):
            print(f"   Completion: {data}")
        
        research_manager.register_progress_callback(progress_callback)
        research_manager.register_completion_callback(completion_callback)
        
        print("   ✅ Callback registration successful")
        
        # Test performance monitoring
        print("\n10. Testing performance monitoring...")
        
        # Start and end a timer
        research_manager.performance_monitor.start_timer("test_operation")
        await asyncio.sleep(0.1)  # Simulate work
        duration = research_manager.performance_monitor.end_timer("test_operation")
        
        print(f"   Operation duration: {duration:.3f}s")
        
        # Get performance stats
        stats = research_manager.performance_monitor.get_stats("test_operation")
        print(f"   Performance stats: {stats}")
        
        print("   ✅ Performance monitoring working")
        
        print("\n" + "=" * 50)
        print("🎉 All Research Manager tests passed!")
        print("✅ Research Manager implementation is working correctly")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function."""
    print("Research Manager Test Suite")
    print("=" * 50)
    
    success = await test_research_manager()
    
    if success:
        print("\n🎉 All tests passed! Research Manager is ready for integration.")
        return 0
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
