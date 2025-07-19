"""
Unit tests for Task Dependency Tracking (Phase 2)

Tests for task dependency management, parent/child relationships, and execution ordering.
"""

import pytest
import asyncio
from datetime import datetime
from src.mcp.dependency_manager import TaskDependencyManager, TaskNode, DependencyStatus
from src.mcp.protocols import ResearchAction, TaskStatus


class TestTaskDependencyManager:
    """Test the task dependency manager"""
    
    @pytest.fixture
    async def dep_manager(self):
        """Create a dependency manager for testing"""
        return TaskDependencyManager()
    
    @pytest.fixture
    def sample_task(self):
        """Create a sample task without dependencies"""
        return ResearchAction(
            task_id="task-1",
            context_id="context-1",
            agent_type="Retriever",
            action="search",
            payload={"query": "test"}
        )
    
    @pytest.fixture
    def dependent_task(self):
        """Create a task with dependencies"""
        return ResearchAction(
            task_id="task-2",
            context_id="context-1",
            agent_type="Reasoner",
            action="analyze",
            payload={"data": "test"},
            dependencies=["task-1"]
        )
    
    @pytest.fixture
    def child_task(self):
        """Create a child task with parent"""
        return ResearchAction(
            task_id="task-child",
            context_id="context-1",
            agent_type="Executor",
            action="execute",
            payload={"action": "test"},
            parent_task_id="task-1"
        )
    
    @pytest.mark.asyncio
    async def test_add_simple_task(self, dep_manager, sample_task):
        """Test adding a simple task without dependencies"""
        success = await dep_manager.add_task(sample_task)
        assert success is True
        
        # Task should be ready for execution
        ready_task = await dep_manager.get_ready_task()
        assert ready_task == "task-1"
        
        # Check task info
        task_info = await dep_manager.get_task_info("task-1")
        assert task_info is not None
        assert task_info['task_id'] == "task-1"
        assert task_info['is_ready'] is True
        assert task_info['dependencies'] == []
    
    @pytest.mark.asyncio
    async def test_add_dependent_task(self, dep_manager, sample_task, dependent_task):
        """Test adding a task with dependencies"""
        # Add parent task first
        await dep_manager.add_task(sample_task)
        
        # Add dependent task
        success = await dep_manager.add_task(dependent_task)
        assert success is True
        
        # Only parent should be ready
        ready_task = await dep_manager.get_ready_task()
        assert ready_task == "task-1"
        
        # Dependent task should not be ready yet
        task_info = await dep_manager.get_task_info("task-2")
        assert task_info['is_ready'] is False
        assert "task-1" in task_info['dependencies']
    
    @pytest.mark.asyncio
    async def test_task_completion_triggers_dependents(self, dep_manager, sample_task, dependent_task):
        """Test that completing a task makes its dependents ready"""
        # Add both tasks
        await dep_manager.add_task(sample_task)
        await dep_manager.add_task(dependent_task)
        
        # Get and complete parent task
        ready_task = await dep_manager.get_ready_task()
        assert ready_task == "task-1"
        
        newly_ready = await dep_manager.complete_task("task-1", success=True)
        assert "task-2" in newly_ready
        
        # Dependent task should now be ready
        ready_task = await dep_manager.get_ready_task()
        assert ready_task == "task-2"
        
        task_info = await dep_manager.get_task_info("task-2")
        assert task_info['is_ready'] is True
        assert task_info['dependencies'] == []  # Should be empty after parent completion
    
    @pytest.mark.asyncio
    async def test_parent_child_relationship(self, dep_manager, sample_task, child_task):
        """Test parent-child task relationships"""
        # Add parent task
        await dep_manager.add_task(sample_task)
        
        # Add child task
        success = await dep_manager.add_task(child_task)
        assert success is True
        
        # Check parent-child relationship
        children = await dep_manager.get_task_children("task-1")
        assert "task-child" in children
        
        child_info = await dep_manager.get_task_info("task-child")
        assert child_info['parent_task_id'] == "task-1"
        assert "task-1" in child_info['dependencies']
    
    @pytest.mark.asyncio
    async def test_failed_dependency_blocks_dependents(self, dep_manager, sample_task, dependent_task):
        """Test that failed dependencies block dependent tasks"""
        # Add both tasks
        await dep_manager.add_task(sample_task)
        await dep_manager.add_task(dependent_task)
        
        # Get and fail parent task
        ready_task = await dep_manager.get_ready_task()
        assert ready_task == "task-1"
        
        newly_ready = await dep_manager.complete_task("task-1", success=False)
        assert len(newly_ready) == 0  # No tasks should become ready
        
        # Dependent task should be marked as failed
        task_info = await dep_manager.get_task_info("task-2")
        assert task_info['status'] == TaskStatus.FAILED.value
    
    @pytest.mark.asyncio
    async def test_multiple_dependencies(self, dep_manager):
        """Test task with multiple dependencies"""
        # Create tasks
        task_a = ResearchAction(
            task_id="task-a",
            context_id="context-1",
            agent_type="Retriever",
            action="search",
            payload={"query": "a"}
        )
        
        task_b = ResearchAction(
            task_id="task-b",
            context_id="context-1",
            agent_type="Retriever",
            action="search",
            payload={"query": "b"}
        )
        
        task_c = ResearchAction(
            task_id="task-c",
            context_id="context-1",
            agent_type="Reasoner",
            action="analyze",
            payload={"data": "combined"},
            dependencies=["task-a", "task-b"]
        )
        
        # Add all tasks
        await dep_manager.add_task(task_a)
        await dep_manager.add_task(task_b)
        await dep_manager.add_task(task_c)
        
        # task-c should not be ready yet
        task_info = await dep_manager.get_task_info("task-c")
        assert task_info['is_ready'] is False
        assert len(task_info['dependencies']) == 2
        
        # Complete task-a
        await dep_manager.get_ready_task()  # Should be task-a or task-b
        await dep_manager.complete_task("task-a", success=True)
        
        # task-c should still not be ready
        task_info = await dep_manager.get_task_info("task-c")
        assert task_info['is_ready'] is False
        assert len(task_info['dependencies']) == 1
        
        # Complete task-b
        await dep_manager.get_ready_task()  # Should be task-b
        newly_ready = await dep_manager.complete_task("task-b", success=True)
        
        # Now task-c should be ready
        assert "task-c" in newly_ready
        task_info = await dep_manager.get_task_info("task-c")
        assert task_info['is_ready'] is True
    
    @pytest.mark.asyncio
    async def test_dependency_graph_query(self, dep_manager, sample_task, dependent_task):
        """Test querying the complete dependency graph"""
        # Add tasks
        await dep_manager.add_task(sample_task)
        await dep_manager.add_task(dependent_task)
        
        # Get dependency graph
        graph = await dep_manager.get_dependency_graph()
        
        assert graph['total_tasks'] == 2
        assert 'task-1' in graph['tasks']
        assert 'task-2' in graph['tasks']
        assert graph['ready_queue_size'] >= 0
        
        # Check task details in graph
        task1_info = graph['tasks']['task-1']
        task2_info = graph['tasks']['task-2']
        
        assert 'task-2' in task1_info['dependents']
        assert 'task-1' in task2_info['dependencies']
    
    @pytest.mark.asyncio
    async def test_cancel_task_tree(self, dep_manager):
        """Test cancelling a task and all its descendants"""
        # Create a tree: root -> child1, child2 -> grandchild
        root_task = ResearchAction(
            task_id="root",
            context_id="context-1",
            agent_type="Manager",
            action="plan",
            payload={}
        )
        
        child1_task = ResearchAction(
            task_id="child1",
            context_id="context-1",
            agent_type="Worker",
            action="work",
            payload={},
            parent_task_id="root"
        )
        
        child2_task = ResearchAction(
            task_id="child2",
            context_id="context-1",
            agent_type="Worker",
            action="work",
            payload={},
            parent_task_id="root"
        )
        
        grandchild_task = ResearchAction(
            task_id="grandchild",
            context_id="context-1",
            agent_type="Worker",
            action="work",
            payload={},
            parent_task_id="child1"
        )
        
        # Add all tasks
        await dep_manager.add_task(root_task)
        await dep_manager.add_task(child1_task)
        await dep_manager.add_task(child2_task)
        await dep_manager.add_task(grandchild_task)
        
        # Cancel the tree starting from root
        cancelled = await dep_manager.cancel_task_tree("root")
        
        assert "root" in cancelled
        assert "child1" in cancelled
        assert "child2" in cancelled
        assert "grandchild" in cancelled
        
        # Check that all tasks are marked as cancelled
        for task_id in cancelled:
            task_info = await dep_manager.get_task_info(task_id)
            assert task_info['status'] == TaskStatus.CANCELLED.value
    
    @pytest.mark.asyncio
    async def test_get_task_descendants(self, dep_manager):
        """Test getting all descendants of a task"""
        # Create tree structure
        tasks = [
            ResearchAction(task_id="root", context_id="ctx", agent_type="Manager", action="plan", payload={}),
            ResearchAction(task_id="child1", context_id="ctx", agent_type="Worker", action="work", payload={}, parent_task_id="root"),
            ResearchAction(task_id="child2", context_id="ctx", agent_type="Worker", action="work", payload={}, parent_task_id="root"),
            ResearchAction(task_id="grandchild1", context_id="ctx", agent_type="Worker", action="work", payload={}, parent_task_id="child1"),
            ResearchAction(task_id="grandchild2", context_id="ctx", agent_type="Worker", action="work", payload={}, parent_task_id="child2"),
        ]
        
        for task in tasks:
            await dep_manager.add_task(task)
        
        # Get descendants of root
        descendants = await dep_manager.get_task_descendants("root")
        
        assert len(descendants) == 4
        assert "child1" in descendants
        assert "child2" in descendants
        assert "grandchild1" in descendants
        assert "grandchild2" in descendants
        
        # Get descendants of child1
        child1_descendants = await dep_manager.get_task_descendants("child1")
        assert len(child1_descendants) == 1
        assert "grandchild1" in child1_descendants
    
    @pytest.mark.asyncio
    async def test_dependency_manager_stats(self, dep_manager, sample_task, dependent_task):
        """Test getting dependency manager statistics"""
        # Add tasks
        await dep_manager.add_task(sample_task)
        await dep_manager.add_task(dependent_task)
        
        # Complete one task
        await dep_manager.get_ready_task()
        await dep_manager.complete_task("task-1", success=True)
        
        # Get stats
        stats = await dep_manager.get_stats()
        
        assert stats['total_tasks'] == 2
        assert stats['completed_tasks'] == 1
        assert stats['has_dependencies'] >= 1  # task-2 has dependencies
        assert 'status_distribution' in stats
        assert 'average_dependencies' in stats
    
    @pytest.mark.asyncio
    async def test_duplicate_task_handling(self, dep_manager, sample_task):
        """Test handling of duplicate task IDs"""
        # Add task first time
        success1 = await dep_manager.add_task(sample_task)
        assert success1 is True
        
        # Try to add same task again
        success2 = await dep_manager.add_task(sample_task)
        assert success2 is False  # Should fail
        
        # Should still have only one task
        graph = await dep_manager.get_dependency_graph()
        assert graph['total_tasks'] == 1


class TestTaskNode:
    """Test the TaskNode class"""
    
    def test_task_node_creation(self):
        """Test TaskNode creation and properties"""
        action = ResearchAction(
            task_id="test-task",
            context_id="test-context",
            agent_type="Retriever",
            action="search",
            payload={"query": "test"}
        )
        
        node = TaskNode(research_action=action)
        
        assert node.research_action.task_id == "test-task"
        assert node.status == TaskStatus.PENDING
        assert node.is_ready is True  # No dependencies
        assert len(node.dependencies) == 0
        assert len(node.dependents) == 0
    
    def test_task_node_with_dependencies(self):
        """Test TaskNode with dependencies"""
        action = ResearchAction(
            task_id="test-task",
            context_id="test-context",
            agent_type="Retriever",
            action="search",
            payload={"query": "test"}
        )
        
        node = TaskNode(
            research_action=action,
            dependencies={"dep1", "dep2"}
        )
        
        assert node.is_ready is False  # Has dependencies
        assert len(node.dependencies) == 2
        assert "dep1" in node.dependencies
        assert "dep2" in node.dependencies
    
    def test_task_node_serialization(self):
        """Test TaskNode to_dict serialization"""
        action = ResearchAction(
            task_id="test-task",
            context_id="test-context",
            agent_type="Retriever",
            action="search",
            payload={"query": "test"},
            parent_task_id="parent-task"
        )
        
        node = TaskNode(
            research_action=action,
            dependencies={"dep1"},
            dependents={"child1"}
        )
        
        data = node.to_dict()
        
        assert data['task_id'] == "test-task"
        assert data['context_id'] == "test-context"
        assert data['agent_type'] == "Retriever"
        assert data['action'] == "search"
        assert data['status'] == TaskStatus.PENDING.value
        assert data['dependencies'] == ["dep1"]
        assert data['dependents'] == ["child1"]
        assert data['parent_task_id'] == "parent-task"
        assert data['is_ready'] is False


if __name__ == "__main__":
    pytest.main([__file__])
