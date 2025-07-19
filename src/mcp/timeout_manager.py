"""
Task Timeout Manager for MCP Server

Handles task timeouts, tracking, and cancellation for long-running tasks.
"""

import asyncio
import time
from typing import Dict, Optional, Callable
from datetime import datetime, timedelta
from src.mcp.protocols import ResearchAction, TimeoutEvent
from src.mcp.structured_logger import get_mcp_logger, LogLevel, LogEvent


class TaskTimeoutManager:
    """Manages task timeouts and cancellation"""
    
    def __init__(self, default_timeout: float = 300.0):
        self.default_timeout = default_timeout
        self.running_tasks: Dict[str, Dict] = {}
        self.timeout_tasks: Dict[str, asyncio.Task] = {}
        self.cleanup_tasks: Dict[str, asyncio.Task] = {}
        self.logger = get_mcp_logger("timeout_manager")
        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_running = False
    
    async def start(self):
        """Start the timeout manager"""
        self._is_running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self.logger.log_server_lifecycle("start", {"component": "timeout_manager"})
    
    async def stop(self):
        """Stop the timeout manager"""
        self._is_running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all running timeout tasks and wait for them
        timeout_tasks = list(self.timeout_tasks.values())
        cleanup_tasks = list(self.cleanup_tasks.values())
        
        for timeout_task in timeout_tasks:
            timeout_task.cancel()
        for cleanup_task in cleanup_tasks:
            cleanup_task.cancel()
        
        # Wait for all tasks to be cancelled
        all_tasks = timeout_tasks + cleanup_tasks
        if all_tasks:
            await asyncio.gather(*all_tasks, return_exceptions=True)
        
        self.timeout_tasks.clear()
        self.cleanup_tasks.clear()
        self.running_tasks.clear()
        
        self.logger.log_server_lifecycle("stop", {"component": "timeout_manager"})
    
    def start_task_timeout(self, research_action: ResearchAction, 
                          timeout_callback: Optional[Callable] = None) -> str:
        """Start timeout tracking for a task"""
        task_id = research_action.task_id
        timeout_duration = research_action.timeout or self.default_timeout
        
        start_time = time.time()
        
        # Store task info
        self.running_tasks[task_id] = {
            'research_action': research_action,
            'start_time': start_time,
            'timeout_duration': timeout_duration,
            'timeout_callback': timeout_callback,
            'status': 'running'
        }
        
        # Start timeout coroutine
        timeout_task = asyncio.create_task(
            self._timeout_task(task_id, timeout_duration)
        )
        self.timeout_tasks[task_id] = timeout_task
        
        self.logger.log_task_dispatch(
            task_id=task_id,
            context_id=research_action.context_id,
            agent_type=research_action.agent_type,
            action=research_action.action,
            timeout_duration=timeout_duration
        )
        
        return task_id
    
    def complete_task(self, task_id: str, success: bool = True) -> bool:
        """Mark a task as completed and stop timeout tracking"""
        if task_id not in self.running_tasks:
            return False
        
        task_info = self.running_tasks[task_id]
        duration = time.time() - task_info['start_time']
        
        # Cancel timeout task
        if task_id in self.timeout_tasks:
            self.timeout_tasks[task_id].cancel()
            del self.timeout_tasks[task_id]
        
        # Update task status
        task_info['status'] = 'completed' if success else 'failed'
        task_info['duration'] = duration
        
        self.logger.log_task_completion(
            task_id=task_id,
            context_id=task_info['research_action'].context_id,
            agent_type=task_info['research_action'].agent_type,
            duration=duration,
            success=success
        )
        
        # Remove from running tasks after a delay for cleanup
        cleanup_task = asyncio.create_task(self._delayed_cleanup(task_id, 60))
        self.cleanup_tasks[task_id] = cleanup_task
        
        return True
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get the status of a tracked task"""
        if task_id not in self.running_tasks:
            return None
        
        task_info = self.running_tasks[task_id].copy()
        task_info['elapsed_time'] = time.time() - task_info['start_time']
        return task_info
    
    def get_running_tasks(self) -> Dict[str, Dict]:
        """Get all currently running tasks"""
        result = {}
        for task_id in self.running_tasks:
            if self.running_tasks[task_id]['status'] == 'running':
                status = self.get_task_status(task_id)
                if status:
                    result[task_id] = status
        return result
    
    async def _timeout_task(self, task_id: str, timeout_duration: float):
        """Timeout coroutine for a specific task"""
        try:
            await asyncio.sleep(timeout_duration)
            
            # Task timed out
            if task_id in self.running_tasks:
                await self._handle_timeout(task_id)
                
        except asyncio.CancelledError:
            # Task completed before timeout
            pass
    
    async def _handle_timeout(self, task_id: str):
        """Handle a task timeout"""
        if task_id not in self.running_tasks:
            return
        
        task_info = self.running_tasks[task_id]
        research_action = task_info['research_action']
        
        # Update task status
        task_info['status'] = 'timeout'
        
        # Create timeout event
        timeout_event = TimeoutEvent(
            task_id=task_id,
            context_id=research_action.context_id,
            agent_type=research_action.agent_type,
            timeout_duration=task_info['timeout_duration'],
            message=f"Task {task_id} exceeded timeout of {task_info['timeout_duration']}s"
        )
        
        # Log timeout
        self.logger.log_task_timeout(
            task_id=task_id,
            context_id=research_action.context_id,
            agent_type=research_action.agent_type,
            timeout_duration=task_info['timeout_duration']
        )
        
        # Call timeout callback if provided
        if task_info['timeout_callback']:
            try:
                await task_info['timeout_callback'](timeout_event)
            except Exception as e:
                self.logger.log_error(
                    f"Error in timeout callback for task {task_id}: {e}",
                    task_id=task_id,
                    error_code="TIMEOUT_CALLBACK_ERROR"
                )
        
        # Clean up timeout task
        if task_id in self.timeout_tasks:
            del self.timeout_tasks[task_id]
    
    async def _delayed_cleanup(self, task_id: str, delay: int):
        """Remove task info after a delay"""
        try:
            await asyncio.sleep(delay)
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
        except asyncio.CancelledError:
            pass
        finally:
            # Remove from cleanup tasks
            if task_id in self.cleanup_tasks:
                del self.cleanup_tasks[task_id]
    
    async def _cleanup_loop(self):
        """Periodic cleanup of stale tasks"""
        while self._is_running:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                current_time = time.time()
                stale_tasks = []
                
                for task_id, task_info in self.running_tasks.items():
                    # Clean up tasks older than 1 hour that are not running
                    if (task_info['status'] != 'running' and 
                        current_time - task_info['start_time'] > 3600):
                        stale_tasks.append(task_id)
                
                for task_id in stale_tasks:
                    del self.running_tasks[task_id]
                    if task_id in self.timeout_tasks:
                        self.timeout_tasks[task_id].cancel()
                        del self.timeout_tasks[task_id]
                
                if stale_tasks:
                    self.logger.log_event(
                        LogLevel.INFO,
                        LogEvent.SERVER_START,  # Generic cleanup event
                        f"Cleaned up {len(stale_tasks)} stale tasks",
                        details={"cleaned_tasks": stale_tasks}
                    )
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.log_error(
                    f"Error in cleanup loop: {e}",
                    error_code="CLEANUP_ERROR"
                )


class RetryManager:
    """Manages task retry logic with exponential backoff"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.retry_history: Dict[str, Dict] = {}
        self.logger = get_mcp_logger("retry_manager")
    
    def should_retry(self, task_id: str, error_reason: str) -> bool:
        """Determine if a task should be retried"""
        if task_id not in self.retry_history:
            self.retry_history[task_id] = {
                'attempts': 0,
                'last_attempt': datetime.now(),
                'reasons': []
            }
        
        history = self.retry_history[task_id]
        history['attempts'] += 1
        history['reasons'].append(error_reason)
        history['last_attempt'] = datetime.now()
        
        should_retry = history['attempts'] <= self.max_retries
        
        self.logger.log_task_retry(
            task_id=task_id,
            context_id="unknown",  # Context would come from calling code
            agent_type="unknown",  # Agent type would come from calling code
            retry_attempt=history['attempts'],
            reason=error_reason
        )
        
        return should_retry
    
    def get_retry_delay(self, task_id: str) -> float:
        """Calculate retry delay with exponential backoff"""
        if task_id not in self.retry_history:
            return self.base_delay
        
        attempts = self.retry_history[task_id]['attempts']
        delay = self.base_delay * (2 ** (attempts - 1))
        
        # Cap at maximum delay of 60 seconds
        return min(delay, 60.0)
    
    async def wait_for_retry(self, task_id: str):
        """Wait for the appropriate retry delay"""
        delay = self.get_retry_delay(task_id)
        await asyncio.sleep(delay)
    
    def clear_retry_history(self, task_id: str):
        """Clear retry history for a task"""
        if task_id in self.retry_history:
            del self.retry_history[task_id]
    
    def get_retry_stats(self) -> Dict[str, Dict]:
        """Get retry statistics"""
        return self.retry_history.copy()


# Default timeout manager instance
timeout_manager = TaskTimeoutManager()
retry_manager = RetryManager()
