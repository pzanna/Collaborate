"""
Task Queue System for MCP Server

Manages task queuing, scheduling, and execution coordination.
"""

import asyncio
import heapq
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from .protocols import Priority, ResearchAction, TaskStatus

logger = logging.getLogger(__name__)


@dataclass
class QueuedTask:
    """Represents a task in the queue"""

    action: ResearchAction
    priority_score: float
    queued_at: datetime = field(default_factory=datetime.now)
    assigned_agent: Optional[str] = None
    started_at: Optional[datetime] = None
    retry_count: int = 0

    def __lt__(self, other):
        """For heap ordering (lower score = higher priority)"""
        return self.priority_score < other.priority_score


class TaskQueue:
    """Task queue with priority scheduling and retry logic"""

    def __init__(self, max_size: int = 100, retry_attempts: int = 3):
        self.max_size = max_size
        self.retry_attempts = retry_attempts
        self._queue: List[QueuedTask] = []
        self._active_tasks: Dict[str, QueuedTask] = {}
        self._completed_tasks: Dict[str, QueuedTask] = {}
        self._failed_tasks: Dict[str, QueuedTask] = {}
        self._lock = asyncio.Lock()
        self._task_callbacks: Dict[str, List[Callable]] = {}

        # Priority mapping
        self._priority_scores = {
            Priority.LOW.value: 3.0,
            Priority.NORMAL.value: 2.0,
            Priority.HIGH.value: 1.0,
        }

    async def add_task(self, action: ResearchAction) -> bool:
        """Add a new task to the queue"""
        async with self._lock:
            if len(self._queue) >= self.max_size:
                logger.warning(f"Task queue full, rejecting task {action.task_id}")
                return False

            # Calculate priority score
            priority_score = self._priority_scores.get(action.priority, 2.0)

            # Add time factor for aging (older tasks get slightly higher priority)
            time_factor = (
                0.1 * (datetime.now() - action.created_at).total_seconds() / 3600
            )
            priority_score -= time_factor

            # Create queued task
            queued_task = QueuedTask(
                action=action,
                priority_score=priority_score,
                retry_count=action.retry_count,
            )

            # Add to priority queue
            heapq.heappush(self._queue, queued_task)

            logger.info(
                f"Added task {action.task_id} to queue with priority {action.priority}"
            )
            return True

    async def get_next_task(self) -> Optional[QueuedTask]:
        """Get the next highest priority task"""
        async with self._lock:
            if not self._queue:
                return None

            # Get highest priority task
            task = heapq.heappop(self._queue)
            task.started_at = datetime.now()

            # Move to active tasks
            self._active_tasks[task.action.task_id] = task

            logger.debug(f"Dequeued task {task.action.task_id}")
            return task

    async def complete_task(
        self, task_id: str, result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Mark a task as completed"""
        async with self._lock:
            if task_id not in self._active_tasks:
                logger.warning(f"Task {task_id} not found in active tasks")
                return False

            task = self._active_tasks.pop(task_id)
            task.action.status = TaskStatus.COMPLETED.value

            # Move to completed tasks
            self._completed_tasks[task_id] = task

            logger.info(f"Completed task {task_id}")

            # Execute callbacks
            await self._execute_callbacks(task_id, "completed", result)
            return True

    async def fail_task(self, task_id: str, error: str, retry: bool = True) -> bool:
        """Mark a task as failed and optionally retry"""
        async with self._lock:
            if task_id not in self._active_tasks:
                logger.warning(f"Task {task_id} not found in active tasks")
                return False

            task = self._active_tasks.pop(task_id)
            task.retry_count += 1

            # Check if we should retry
            if retry and task.retry_count < self.retry_attempts:
                logger.info(f"Retrying task {task_id} (attempt {task.retry_count + 1})")

                # Reset task state
                task.action.status = TaskStatus.PENDING.value
                task.assigned_agent = None
                task.started_at = None

                # Adjust priority for retry (slightly lower priority)
                task.priority_score += 0.1

                # Add back to queue
                heapq.heappush(self._queue, task)

                await self._execute_callbacks(
                    task_id, "retry", {"error": error, "retry_count": task.retry_count}
                )
                return True
            else:
                # Task failed permanently
                task.action.status = TaskStatus.FAILED.value
                self._failed_tasks[task_id] = task

                logger.error(
                    f"Task {task_id} failed permanently after {task.retry_count} attempts: {error}"
                )

                await self._execute_callbacks(task_id, "failed", {"error": error})
                return False

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task (remove from queue or active tasks)"""
        async with self._lock:
            # Check if task is in queue
            for i, queued_task in enumerate(self._queue):
                if queued_task.action.task_id == task_id:
                    self._queue.pop(i)
                    heapq.heapify(self._queue)  # Restore heap property
                    logger.info(f"Cancelled queued task {task_id}")
                    await self._execute_callbacks(task_id, "cancelled", None)
                    return True

            # Check if task is active
            if task_id in self._active_tasks:
                task = self._active_tasks.pop(task_id)
                task.action.status = TaskStatus.CANCELLED.value
                logger.info(f"Cancelled active task {task_id}")
                await self._execute_callbacks(task_id, "cancelled", None)
                return True

            return False

    async def assign_agent(self, task_id: str, agent_id: str) -> bool:
        """Assign an agent to a task"""
        async with self._lock:
            if task_id not in self._active_tasks:
                return False

            self._active_tasks[task_id].assigned_agent = agent_id
            self._active_tasks[task_id].action.status = TaskStatus.WORKING.value

            logger.debug(f"Assigned agent {agent_id} to task {task_id}")
            await self._execute_callbacks(task_id, "assigned", {"agent_id": agent_id})
            return True

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a task"""
        async with self._lock:
            # Check active tasks
            if task_id in self._active_tasks:
                task = self._active_tasks[task_id]
                return {
                    "task_id": task_id,
                    "status": task.action.status,
                    "assigned_agent": task.assigned_agent,
                    "started_at": (
                        task.started_at.isoformat() if task.started_at else None
                    ),
                    "retry_count": task.retry_count,
                }

            # Check completed tasks
            if task_id in self._completed_tasks:
                task = self._completed_tasks[task_id]
                return {
                    "task_id": task_id,
                    "status": TaskStatus.COMPLETED.value,
                    "assigned_agent": task.assigned_agent,
                    "started_at": (
                        task.started_at.isoformat() if task.started_at else None
                    ),
                    "retry_count": task.retry_count,
                }

            # Check failed tasks
            if task_id in self._failed_tasks:
                task = self._failed_tasks[task_id]
                return {
                    "task_id": task_id,
                    "status": TaskStatus.FAILED.value,
                    "assigned_agent": task.assigned_agent,
                    "started_at": (
                        task.started_at.isoformat() if task.started_at else None
                    ),
                    "retry_count": task.retry_count,
                }

            # Check queue
            for queued_task in self._queue:
                if queued_task.action.task_id == task_id:
                    return {
                        "task_id": task_id,
                        "status": TaskStatus.PENDING.value,
                        "assigned_agent": None,
                        "started_at": None,
                        "retry_count": queued_task.retry_count,
                    }

            return None

    async def add_callback(
        self, task_id: str, callback: Callable[[str, str, Any], None]
    ):
        """Add a callback for task status changes"""
        async with self._lock:
            if task_id not in self._task_callbacks:
                self._task_callbacks[task_id] = []
            self._task_callbacks[task_id].append(callback)

    async def _execute_callbacks(self, task_id: str, event: str, data: Any):
        """Execute callbacks for a task event"""
        if task_id in self._task_callbacks:
            for callback in self._task_callbacks[task_id]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(task_id, event, data)
                    else:
                        callback(task_id, event, data)
                except Exception as e:
                    logger.error(f"Error executing callback for task {task_id}: {e}")

    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        async with self._lock:
            pending_tasks = len(self._queue)
            active_tasks = len(self._active_tasks)
            completed_tasks = len(self._completed_tasks)
            failed_tasks = len(self._failed_tasks)

            # Priority distribution in queue
            priority_dist = {p.value: 0 for p in Priority}
            for task in self._queue:
                priority_dist[task.action.priority] += 1

            return {
                "pending_tasks": pending_tasks,
                "active_tasks": active_tasks,
                "completed_tasks": completed_tasks,
                "failed_tasks": failed_tasks,
                "total_tasks": pending_tasks
                + active_tasks
                + completed_tasks
                + failed_tasks,
                "priority_distribution": priority_dist,
                "queue_utilization": pending_tasks / self.max_size,
            }

    async def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Clean up old completed and failed tasks"""
        async with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

            # Clean completed tasks
            to_remove = []
            for task_id, task in self._completed_tasks.items():
                if task.started_at and task.started_at < cutoff_time:
                    to_remove.append(task_id)

            for task_id in to_remove:
                del self._completed_tasks[task_id]
                # Clean up callbacks
                if task_id in self._task_callbacks:
                    del self._task_callbacks[task_id]

            # Clean failed tasks
            to_remove = []
            for task_id, task in self._failed_tasks.items():
                if task.started_at and task.started_at < cutoff_time:
                    to_remove.append(task_id)

            for task_id in to_remove:
                del self._failed_tasks[task_id]
                # Clean up callbacks
                if task_id in self._task_callbacks:
                    del self._task_callbacks[task_id]

            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} old tasks")

    async def get_all_tasks(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all tasks organized by status"""
        async with self._lock:
            result = {"pending": [], "active": [], "completed": [], "failed": []}

            # Pending tasks
            for task in self._queue:
                result["pending"].append(
                    {
                        "task_id": task.action.task_id,
                        "action": task.action.action,
                        "priority": task.action.priority,
                        "queued_at": task.queued_at.isoformat(),
                        "retry_count": task.retry_count,
                    }
                )

            # Active tasks
            for task in self._active_tasks.values():
                result["active"].append(
                    {
                        "task_id": task.action.task_id,
                        "action": task.action.action,
                        "assigned_agent": task.assigned_agent,
                        "started_at": (
                            task.started_at.isoformat() if task.started_at else None
                        ),
                        "retry_count": task.retry_count,
                    }
                )

            # Completed tasks
            for task in self._completed_tasks.values():
                result["completed"].append(
                    {
                        "task_id": task.action.task_id,
                        "action": task.action.action,
                        "assigned_agent": task.assigned_agent,
                        "started_at": (
                            task.started_at.isoformat() if task.started_at else None
                        ),
                        "retry_count": task.retry_count,
                    }
                )

            # Failed tasks
            for task in self._failed_tasks.values():
                result["failed"].append(
                    {
                        "task_id": task.action.task_id,
                        "action": task.action.action,
                        "assigned_agent": task.assigned_agent,
                        "started_at": (
                            task.started_at.isoformat() if task.started_at else None
                        ),
                        "retry_count": task.retry_count,
                    }
                )

            return result

    async def get_active_tasks(self) -> List[QueuedTask]:
        """Get all currently active tasks"""
        async with self._lock:
            return list(self._active_tasks.values())

    async def get_task(self, task_id: str) -> Optional[QueuedTask]:
        """Get a specific task by ID from any status"""
        async with self._lock:
            # Check active tasks first
            if task_id in self._active_tasks:
                return self._active_tasks[task_id]

            # Check completed tasks
            if task_id in self._completed_tasks:
                return self._completed_tasks[task_id]

            # Check failed tasks
            if task_id in self._failed_tasks:
                return self._failed_tasks[task_id]

            # Check pending tasks in queue
            for task in self._queue:
                if task.action.task_id == task_id:
                    return task

            return None
