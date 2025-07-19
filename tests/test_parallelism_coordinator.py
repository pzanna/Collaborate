"""
Unit tests for Parallelism Coordinator (Phase 2)

Tests for the integrated parallelism coordination system.
"""

import pytest
import asyncio
from src.mcp.parallelism_coordinator import (
    ParallelismCoordinator, 
    ParallelismMode, 
    ParallelExecution,
    create_parallelism_coordinator
)
from src.mcp.protocols import ResearchAction
from src.mcp.fanout_manager import FanoutStrategy


class TestParallelismCoordinator:
    """Test the parallelism coordinator"""
    
    @pytest.fixture
    async def coordinator(self):
        """Create a parallelism coordinator for testing"""
        return ParallelismCoordinator()
    
    @pytest.fixture
    def search_task(self):
        """Create a search task for testing"""
        return ResearchAction(
            task_id="search-001",
            context_id="ctx-001",
            agent_type="Retriever",
            action="search",
            payload={
                "queries": ["AI research", "machine learning", "deep learning"],
                "max_results": 10
            }
        )
    
    @pytest.fixture
    def parallel_search_task(self):
        """Create a search task with explicit parallelism"""
        return ResearchAction(
            task_id="search-parallel-001",
            context_id="ctx-001",
            agent_type="Retriever",
            action="search",
            payload={
                "queries": ["neural networks", "transformers", "attention"],
                "max_results": 20
            },
            parallelism=3
        )
    
    @pytest.fixture
    def sequential_task(self):
        """Create a task that should run sequentially"""
        return ResearchAction(
            task_id="synthesize-001",
            context_id="ctx-001",
            agent_type="Reasoner",
            action="synthesize",
            payload={
                "results": ["result1", "result2"]
            }
        )
    
    @pytest.mark.asyncio
    async def test_get_enhanced_system_prompt(self, coordinator):
        """Test getting the enhanced RM system prompt"""
        prompt = await coordinator.get_enhanced_system_prompt()
        
        assert isinstance(prompt, str)
        assert len(prompt) > 1000
        assert "parallelism" in prompt.lower()
        assert "Parallelism Guidelines" in prompt
        assert "Message Control Protocol" in prompt
    
    @pytest.mark.asyncio
    async def test_analyze_task_for_parallelism_explicit(self, coordinator, parallel_search_task):
        """Test analyzing task with explicit parallelism"""
        should_parallelize, parallelism, mode = await coordinator.analyze_task_for_parallelism(
            parallel_search_task
        )
        
        assert should_parallelize is True
        assert parallelism == 3
        assert mode == ParallelismMode.EXPLICIT
    
    @pytest.mark.asyncio
    async def test_analyze_task_for_parallelism_automatic(self, coordinator, search_task):
        """Test analyzing task for automatic parallelism"""
        should_parallelize, parallelism, mode = await coordinator.analyze_task_for_parallelism(
            search_task
        )
        
        assert should_parallelize is True
        assert parallelism > 1
        assert mode == ParallelismMode.AUTOMATIC
    
    @pytest.mark.asyncio
    async def test_analyze_task_for_parallelism_sequential(self, coordinator, sequential_task):
        """Test analyzing task that should run sequentially"""
        should_parallelize, parallelism, mode = await coordinator.analyze_task_for_parallelism(
            sequential_task
        )
        
        assert should_parallelize is False
        assert parallelism == 1
        assert mode == ParallelismMode.SEQUENTIAL
    
    def test_extract_item_count(self, coordinator):
        """Test extracting item count from tasks"""
        # Task with queries list
        task1 = ResearchAction(
            task_id="test",
            context_id="ctx",
            agent_type="Agent",
            action="search",
            payload={"queries": ["q1", "q2", "q3", "q4", "q5"]}
        )
        assert coordinator._extract_item_count(task1) == 5
        
        # Task with documents list
        task2 = ResearchAction(
            task_id="test",
            context_id="ctx", 
            agent_type="Agent",
            action="analyze",
            payload={"documents": ["doc1", "doc2"]}
        )
        assert coordinator._extract_item_count(task2) == 2
        
        # Task with batch_size
        task3 = ResearchAction(
            task_id="test",
            context_id="ctx",
            agent_type="Agent", 
            action="process",
            payload={"batch_size": 10}
        )
        assert coordinator._extract_item_count(task3) == 10
        
        # Task with no clear item count
        task4 = ResearchAction(
            task_id="test",
            context_id="ctx",
            agent_type="Agent",
            action="summarize",
            payload={"text": "some text"}
        )
        assert coordinator._extract_item_count(task4) == 1
    
    @pytest.mark.asyncio
    async def test_create_parallel_execution(self, coordinator, search_task):
        """Test creating a parallel execution plan"""
        execution = await coordinator.create_parallel_execution(
            search_task,
            parallelism=3,
            mode=ParallelismMode.AUTOMATIC,
            strategy=FanoutStrategy.ROUND_ROBIN
        )
        
        assert execution is not None
        assert execution.original_task == search_task
        assert execution.execution_mode == ParallelismMode.AUTOMATIC
        assert len(execution.parallel_tasks) == 3
        assert execution.strategy == FanoutStrategy.ROUND_ROBIN
        assert execution.estimated_completion_time > 0
        
        # Check that execution is tracked
        assert search_task.task_id in coordinator.active_executions
    
    @pytest.mark.asyncio
    async def test_create_parallel_execution_with_dependencies(self, coordinator):
        """Test creating parallel execution with dependencies"""
        # Create a task with dependencies
        task = ResearchAction(
            task_id="dependent-task",
            context_id="ctx-001",
            agent_type="Reasoner",
            action="analyze",
            payload={"data": "some data"},
            dependencies=["dep-1", "dep-2"]
        )
        
        # Should fail because dependencies not satisfied
        execution = await coordinator.create_parallel_execution(
            task,
            parallelism=2,
            mode=ParallelismMode.AUTOMATIC
        )
        
        assert execution is None  # Should fail due to unmet dependencies
        
        # Satisfy dependencies
        coordinator.dependency_manager.completed_tasks.add("dep-1")
        coordinator.dependency_manager.completed_tasks.add("dep-2")
        
        # Should succeed now
        execution = await coordinator.create_parallel_execution(
            task,
            parallelism=2,
            mode=ParallelismMode.AUTOMATIC
        )
        
        assert execution is not None
        assert execution.dependencies == ["dep-1", "dep-2"]
    
    def test_estimate_completion_time(self, coordinator):
        """Test completion time estimation"""
        # Search task
        search_task = ResearchAction(
            task_id="test",
            context_id="ctx",
            agent_type="Retriever",
            action="search",
            payload={}
        )
        
        # Sequential execution
        time_seq = coordinator._estimate_completion_time(search_task, 1)
        assert time_seq >= 5  # Minimum 5 seconds
        
        # Parallel execution should be faster
        time_par = coordinator._estimate_completion_time(search_task, 3)
        assert time_par < time_seq
        assert time_par >= 5  # Still minimum 5 seconds
        
        # Higher parallelism should be even faster (up to a point)
        time_high_par = coordinator._estimate_completion_time(search_task, 6)
        assert time_high_par <= time_par
    
    @pytest.mark.asyncio
    async def test_get_execution_status(self, coordinator, search_task):
        """Test getting execution status"""
        # Create execution
        execution = await coordinator.create_parallel_execution(
            search_task,
            parallelism=2,
            mode=ParallelismMode.AUTOMATIC
        )
        
        assert execution is not None
        
        # Get status
        status = await coordinator.get_execution_status(search_task.task_id)
        
        assert status is not None
        assert status['task_id'] == search_task.task_id
        assert status['mode'] == ParallelismMode.AUTOMATIC.value
        assert status['parallel_task_count'] == 2
        assert status['elapsed_time'] >= 0
        assert status['estimated_completion_time'] > 0
        assert 'fanout_info' in status
        assert status['dependencies'] == []
    
    @pytest.mark.asyncio
    async def test_get_execution_status_nonexistent(self, coordinator):
        """Test getting status for non-existent execution"""
        status = await coordinator.get_execution_status("nonexistent-task")
        assert status is None
    
    @pytest.mark.asyncio
    async def test_cancel_parallel_execution(self, coordinator, search_task):
        """Test cancelling a parallel execution"""
        # Create execution
        execution = await coordinator.create_parallel_execution(
            search_task,
            parallelism=2,
            mode=ParallelismMode.AUTOMATIC
        )
        
        assert execution is not None
        assert search_task.task_id in coordinator.active_executions
        
        # Cancel execution
        success = await coordinator.cancel_parallel_execution(search_task.task_id)
        
        assert success is True
        assert search_task.task_id not in coordinator.active_executions
    
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_execution(self, coordinator):
        """Test cancelling non-existent execution"""
        success = await coordinator.cancel_parallel_execution("nonexistent-task")
        assert success is False
    
    @pytest.mark.asyncio
    async def test_get_coordinator_stats(self, coordinator, search_task):
        """Test getting coordinator statistics"""
        # Initial stats
        stats = await coordinator.get_coordinator_stats()
        
        assert 'active_executions' in stats
        assert 'execution_stats' in stats
        assert 'fanout_stats' in stats
        assert 'dependency_stats' in stats
        assert stats['total_components'] == 3
        assert stats['active_executions'] == 0
        
        # Create an execution
        execution = await coordinator.create_parallel_execution(
            search_task,
            parallelism=2,
            mode=ParallelismMode.AUTOMATIC
        )
        
        # Stats should update
        updated_stats = await coordinator.get_coordinator_stats()
        assert updated_stats['active_executions'] == 1
    
    @pytest.mark.asyncio
    async def test_wait_for_subtasks_completion_timeout(self, coordinator, search_task):
        """Test waiting for subtasks with timeout"""
        execution = await coordinator.create_parallel_execution(
            search_task,
            parallelism=2,
            mode=ParallelismMode.AUTOMATIC
        )
        
        assert execution is not None
        
        # Test with very short timeout (should timeout)
        result = await coordinator._wait_for_subtasks_completion(execution, timeout=1)
        assert result is False  # Should timeout


class TestParallelExecution:
    """Test the ParallelExecution dataclass"""
    
    def test_parallel_execution_creation(self):
        """Test creating a ParallelExecution"""
        original_task = ResearchAction(
            task_id="original",
            context_id="ctx",
            agent_type="Agent",
            action="test",
            payload={}
        )
        
        parallel_tasks = [
            ResearchAction(
                task_id="sub1",
                context_id="ctx",
                agent_type="Agent",
                action="test",
                payload={}
            ),
            ResearchAction(
                task_id="sub2",
                context_id="ctx",
                agent_type="Agent", 
                action="test",
                payload={}
            )
        ]
        
        execution = ParallelExecution(
            original_task=original_task,
            execution_mode=ParallelismMode.AUTOMATIC,
            parallel_tasks=parallel_tasks,
            dependencies=[],
            estimated_completion_time=30.0,
            strategy=FanoutStrategy.ROUND_ROBIN,
            created_at=1234567890.0
        )
        
        assert execution.original_task == original_task
        assert execution.execution_mode == ParallelismMode.AUTOMATIC
        assert len(execution.parallel_tasks) == 2
        assert execution.dependencies == []
        assert execution.estimated_completion_time == 30.0
        assert execution.strategy == FanoutStrategy.ROUND_ROBIN
        assert execution.created_at == 1234567890.0


class TestCreateParallelismCoordinator:
    """Test the factory function"""
    
    @pytest.mark.asyncio
    async def test_create_parallelism_coordinator(self):
        """Test creating coordinator with factory function"""
        coordinator = await create_parallelism_coordinator()
        
        assert isinstance(coordinator, ParallelismCoordinator)
        assert coordinator.dependency_manager is not None
        assert coordinator.fanout_manager is not None
        assert coordinator.active_executions == {}
        
        # Test that enhanced prompt is available
        prompt = await coordinator.get_enhanced_system_prompt()
        assert len(prompt) > 1000


class TestIntegration:
    """Integration tests for parallelism coordinator"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test a complete parallelism workflow"""
        coordinator = await create_parallelism_coordinator()
        
        # Create a task suitable for parallelism
        task = ResearchAction(
            task_id="integration-test",
            context_id="ctx-integration",
            agent_type="Retriever",
            action="search",
            payload={
                "queries": ["query1", "query2", "query3", "query4"],
                "max_results": 50
            }
        )
        
        # Analyze for parallelism
        should_parallelize, parallelism, mode = await coordinator.analyze_task_for_parallelism(task)
        assert should_parallelize is True
        assert parallelism > 1
        
        # Create parallel execution
        execution = await coordinator.create_parallel_execution(
            task, parallelism, mode, FanoutStrategy.ROUND_ROBIN
        )
        assert execution is not None
        
        # Check status
        status = await coordinator.get_execution_status(task.task_id)
        assert status is not None
        assert status['parallel_task_count'] == parallelism
        
        # Get stats
        stats = await coordinator.get_coordinator_stats()
        assert stats['active_executions'] == 1
        
        # Cancel execution
        success = await coordinator.cancel_parallel_execution(task.task_id)
        assert success is True
        
        # Verify cleanup
        status_after_cancel = await coordinator.get_execution_status(task.task_id)
        assert status_after_cancel is None
        
        final_stats = await coordinator.get_coordinator_stats()
        assert final_stats['active_executions'] == 0


if __name__ == "__main__":
    pytest.main([__file__])
