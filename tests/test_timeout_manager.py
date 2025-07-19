"""
Unit tests for Task Timeout Implementation (Phase 1)

Tests for timeout handling, task tracking, and retry management.
"""

import pytest
import asyncio
from datetime import datetime
from src.mcp.timeout_manager import TaskTimeoutManager, RetryManager
from src.mcp.protocols import ResearchAction, TimeoutEvent


class TestTaskTimeoutManager:
    """Test the task timeout manager"""
    
    @pytest.fixture
    async def timeout_manager(self):
        """Create a timeout manager for testing"""
        manager = TaskTimeoutManager(default_timeout=1)  # 1 second for fast tests
        await manager.start()
        yield manager
        await manager.stop()
    
    @pytest.fixture
    def sample_action(self):
        """Create a sample research action"""
        return ResearchAction(
            task_id="test-task-123",
            context_id="test-context-123",
            agent_type="Retriever",
            action="search",
            payload={"query": "test"},
            timeout=2
        )
    
    @pytest.mark.asyncio
    async def test_start_task_timeout(self, timeout_manager, sample_action):
        """Test starting timeout tracking for a task"""
        task_id = timeout_manager.start_task_timeout(sample_action)
        
        assert task_id == "test-task-123"
        assert task_id in timeout_manager.running_tasks
        assert task_id in timeout_manager.timeout_tasks
        
        task_status = timeout_manager.get_task_status(task_id)
        assert task_status is not None
        assert task_status['status'] == 'running'
        assert task_status['timeout_duration'] == 2
    
    @pytest.mark.asyncio
    async def test_complete_task_success(self, timeout_manager, sample_action):
        """Test successful task completion"""
        task_id = timeout_manager.start_task_timeout(sample_action)
        
        # Complete the task
        success = timeout_manager.complete_task(task_id, success=True)
        assert success is True
        
        # Check task status
        task_status = timeout_manager.get_task_status(task_id)
        assert task_status['status'] == 'completed'
        assert 'duration' in task_status
        
        # Timeout task should be cancelled
        assert task_id not in timeout_manager.timeout_tasks
    
    @pytest.mark.asyncio
    async def test_complete_task_failure(self, timeout_manager, sample_action):
        """Test failed task completion"""
        task_id = timeout_manager.start_task_timeout(sample_action)
        
        # Mark task as failed
        success = timeout_manager.complete_task(task_id, success=False)
        assert success is True
        
        task_status = timeout_manager.get_task_status(task_id)
        assert task_status['status'] == 'failed'
    
    @pytest.mark.asyncio
    async def test_task_timeout(self, sample_action):
        """Test task timeout handling"""
        timeout_events = []
        
        async def timeout_callback(event: TimeoutEvent):
            timeout_events.append(event)
        
        # Create manager with very short timeout
        manager = TaskTimeoutManager(default_timeout=0.1)
        await manager.start()
        
        try:
            # Start task with timeout callback
            task_id = manager.start_task_timeout(sample_action, timeout_callback)
            
            # Wait for timeout to occur
            await asyncio.sleep(0.2)
            
            # Check that timeout occurred
            assert len(timeout_events) == 1
            timeout_event = timeout_events[0]
            assert timeout_event.task_id == task_id
            assert timeout_event.timeout_duration == 2  # From sample_action
            
            # Check task status
            task_status = manager.get_task_status(task_id)
            assert task_status['status'] == 'timeout'
            
        finally:
            await manager.stop()
    
    @pytest.mark.asyncio
    async def test_get_running_tasks(self, timeout_manager, sample_action):
        """Test getting running tasks"""
        # Initially no running tasks
        running_tasks = timeout_manager.get_running_tasks()
        assert len(running_tasks) == 0
        
        # Start a task
        task_id = timeout_manager.start_task_timeout(sample_action)
        
        # Should have one running task
        running_tasks = timeout_manager.get_running_tasks()
        assert len(running_tasks) == 1
        assert task_id in running_tasks
        
        # Complete the task
        timeout_manager.complete_task(task_id)
        
        # Should have no running tasks
        running_tasks = timeout_manager.get_running_tasks()
        assert len(running_tasks) == 0
    
    @pytest.mark.asyncio
    async def test_complete_nonexistent_task(self, timeout_manager):
        """Test completing a non-existent task"""
        success = timeout_manager.complete_task("nonexistent-task")
        assert success is False


class TestRetryManager:
    """Test the retry manager"""
    
    @pytest.fixture
    def retry_manager(self):
        """Create a retry manager for testing"""
        return RetryManager(max_retries=3, base_delay=0.1)
    
    def test_should_retry_first_attempt(self, retry_manager):
        """Test retry decision for first attempt"""
        should_retry = retry_manager.should_retry("task-123", "connection_error")
        assert should_retry is True
        
        # Check retry history
        history = retry_manager.retry_history["task-123"]
        assert history['attempts'] == 1
        assert "connection_error" in history['reasons']
    
    def test_should_retry_max_attempts(self, retry_manager):
        """Test retry behavior at max attempts"""
        task_id = "task-123"
        
        # Make max_retries attempts
        for i in range(3):
            should_retry = retry_manager.should_retry(task_id, f"error_{i}")
            assert should_retry is True
        
        # Next attempt should not retry
        should_retry = retry_manager.should_retry(task_id, "final_error")
        assert should_retry is False
        
        # Check history
        history = retry_manager.retry_history[task_id]
        assert history['attempts'] == 4  # 3 retries + 1 final attempt
    
    def test_get_retry_delay(self, retry_manager):
        """Test exponential backoff calculation"""
        task_id = "task-123"
        
        # First retry
        retry_manager.should_retry(task_id, "error1")
        delay1 = retry_manager.get_retry_delay(task_id)
        assert delay1 == 0.1  # base_delay
        
        # Second retry
        retry_manager.should_retry(task_id, "error2")
        delay2 = retry_manager.get_retry_delay(task_id)
        assert delay2 == 0.2  # base_delay * 2
        
        # Third retry
        retry_manager.should_retry(task_id, "error3")
        delay3 = retry_manager.get_retry_delay(task_id)
        assert delay3 == 0.4  # base_delay * 4
    
    @pytest.mark.asyncio
    async def test_wait_for_retry(self, retry_manager):
        """Test waiting for retry delay"""
        task_id = "task-123"
        retry_manager.should_retry(task_id, "error")
        
        start_time = asyncio.get_event_loop().time()
        await retry_manager.wait_for_retry(task_id)
        end_time = asyncio.get_event_loop().time()
        
        # Should have waited approximately the base delay
        elapsed = end_time - start_time
        assert 0.08 <= elapsed <= 0.15  # Allow some tolerance
    
    def test_clear_retry_history(self, retry_manager):
        """Test clearing retry history"""
        task_id = "task-123"
        retry_manager.should_retry(task_id, "error")
        
        assert task_id in retry_manager.retry_history
        
        retry_manager.clear_retry_history(task_id)
        assert task_id not in retry_manager.retry_history
    
    def test_get_retry_stats(self, retry_manager):
        """Test getting retry statistics"""
        retry_manager.should_retry("task-1", "error1")
        retry_manager.should_retry("task-2", "error2")
        
        stats = retry_manager.get_retry_stats()
        assert len(stats) == 2
        assert "task-1" in stats
        assert "task-2" in stats
        
        assert stats["task-1"]["attempts"] == 1
        assert stats["task-2"]["attempts"] == 1


class TestTimeoutIntegration:
    """Integration tests for timeout and retry systems"""
    
    @pytest.mark.asyncio
    async def test_timeout_with_retry(self):
        """Test timeout handling combined with retry logic"""
        timeout_manager = TaskTimeoutManager(default_timeout=0.1)
        retry_manager = RetryManager(max_retries=2, base_delay=0.05)
        
        await timeout_manager.start()
        
        try:
            # Create action that will timeout
            action = ResearchAction(
                task_id="timeout-retry-task",
                context_id="test-context",
                agent_type="Retriever",
                action="search",
                payload={"query": "test"},
                timeout=0.1
            )
            
            # Start task
            task_id = timeout_manager.start_task_timeout(action)
            
            # Wait for timeout
            await asyncio.sleep(0.15)
            
            # Check if task timed out
            task_status = timeout_manager.get_task_status(task_id)
            assert task_status['status'] == 'timeout'
            
            # Test retry logic
            should_retry = retry_manager.should_retry(task_id, "timeout")
            assert should_retry is True
            
            # Test retry delay
            delay = retry_manager.get_retry_delay(task_id)
            assert delay == 0.05
            
        finally:
            await timeout_manager.stop()


if __name__ == "__main__":
    pytest.main([__file__])
