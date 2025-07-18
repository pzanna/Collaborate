#!/usr/bin/env python3
"""
Test script for MCP server components
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.mcp.protocols import ResearchAction, AgentResponse, TaskStatus
from src.mcp.queue import TaskQueue
from src.mcp.registry import AgentRegistry, AgentRegistration

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_protocols():
    """Test protocol message serialization"""
    logger.info("Testing protocol message serialization...")
    
    # Test ResearchAction
    action = ResearchAction(
        task_id="test-123",
        context_id="ctx-456",
        agent_type="Retriever",
        action="web_search",
        payload={"query": "test search"},
        priority="high"
    )
    
    # Test serialization
    action_dict = action.to_dict()
    action_restored = ResearchAction.from_dict(action_dict)
    
    assert action.task_id == action_restored.task_id
    assert action.context_id == action_restored.context_id
    assert action.agent_type == action_restored.agent_type
    
    logger.info("✅ Protocol serialization test passed")


async def test_task_queue():
    """Test task queue functionality"""
    logger.info("Testing task queue...")
    
    queue = TaskQueue(max_size=10, retry_attempts=3)
    
    # Create test task
    action = ResearchAction(
        task_id="queue-test-123",
        context_id="ctx-456",
        agent_type="Retriever",
        action="web_search",
        payload={"query": "test search"},
        priority="normal"
    )
    
    # Add task to queue
    success = await queue.add_task(action)
    assert success, "Failed to add task to queue"
    
    # Get task from queue
    task = await queue.get_next_task()
    assert task is not None, "Failed to get task from queue"
    assert task.action.task_id == action.task_id
    
    # Complete task
    await queue.complete_task(task.action.task_id, {"result": "success"})
    
    # Check stats
    stats = await queue.get_queue_stats()
    assert stats['completed_tasks'] == 1
    
    logger.info("✅ Task queue test passed")


async def test_agent_registry():
    """Test agent registry functionality"""
    logger.info("Testing agent registry...")
    
    registry = AgentRegistry(heartbeat_timeout=30)
    
    # Create test agent registration
    registration = AgentRegistration(
        agent_type="Retriever",
        capabilities=["web_search", "document_extraction"],
        max_concurrent=3,
        timeout=60,
        agent_id="test-agent-001"
    )
    
    # Register agent
    success = await registry.register_agent(registration)
    assert success, "Failed to register agent"
    
    # Check agent availability
    agents = await registry.get_available_agents("web_search")
    assert len(agents) == 1
    assert agents[0] == "test-agent-001"
    
    # Assign task to agent
    await registry.assign_task("test-agent-001", "task-123")
    
    # Check agent info
    agent_info = await registry.get_agent_info("test-agent-001")
    assert agent_info is not None
    assert len(agent_info.current_tasks) == 1
    
    # Complete task
    await registry.complete_task("test-agent-001", "task-123")
    
    # Check stats
    stats = await registry.get_stats()
    assert stats['total_agents'] == 1
    assert stats['healthy_agents'] == 1
    
    logger.info("✅ Agent registry test passed")


async def test_integration():
    """Test integration between components"""
    logger.info("Testing component integration...")
    
    # Create components
    queue = TaskQueue(max_size=10, retry_attempts=3)
    registry = AgentRegistry(heartbeat_timeout=30)
    
    # Register agent
    registration = AgentRegistration(
        agent_type="Retriever",
        capabilities=["web_search"],
        max_concurrent=1,
        timeout=60,
        agent_id="integration-agent"
    )
    await registry.register_agent(registration)
    
    # Create and queue task
    action = ResearchAction(
        task_id="integration-test",
        context_id="ctx-integration",
        agent_type="Retriever",
        action="web_search",
        payload={"query": "integration test"},
        priority="high"
    )
    await queue.add_task(action)
    
    # Simulate task processing
    task = await queue.get_next_task()
    assert task is not None
    
    # Find available agent
    agents = await registry.get_available_agents("web_search")
    assert len(agents) == 1
    
    # Assign task
    agent_id = agents[0]
    await registry.assign_task(agent_id, task.action.task_id)
    await queue.assign_agent(task.action.task_id, agent_id)
    
    # Simulate task completion
    await queue.complete_task(task.action.task_id, {"result": "integration success"})
    await registry.complete_task(agent_id, task.action.task_id)
    
    # Check final state
    queue_stats = await queue.get_queue_stats()
    registry_stats = await registry.get_stats()
    
    assert queue_stats['completed_tasks'] == 1
    assert registry_stats['total_agents'] == 1
    
    logger.info("✅ Integration test passed")


async def main():
    """Run all tests"""
    logger.info("Starting MCP component tests...")
    
    try:
        await test_protocols()
        await test_task_queue()
        await test_agent_registry()
        await test_integration()
        
        logger.info("🎉 All tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
