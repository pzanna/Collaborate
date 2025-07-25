"""
Task Dependency Manager for MCP Server

Manages task dependencies, parent / child relationships, and execution ordering.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from src.mcp.protocols import ResearchAction, TaskStatus
from src.mcp.structured_logger import LogEvent, LogLevel, get_mcp_logger


class DependencyStatus(Enum):
    """Task dependency status"""

    WAITING = "waiting"
    READY = "ready"
    BLOCKED = "blocked"
    SATISFIED = "satisfied"


@dataclass
class TaskNode:
    """Represents a task in the dependency graph"""

    research_action: ResearchAction
    status: TaskStatus = TaskStatus.PENDING
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def is_ready(self) -> bool:
        """Check if task is ready to execute (all dependencies completed)"""
        return len(self.dependencies) == 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "task_id": self.research_action.task_id,
            "context_id": self.research_action.context_id,
            "agent_type": self.research_action.agent_type,
            "action": self.research_action.action,
            "status": self.status.value,
            "dependencies": list(self.dependencies),
            "dependents": list(self.dependents),
            "parent_task_id": self.research_action.parent_task_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "is_ready": self.is_ready,
        }


class TaskDependencyManager:
    """Manages task dependencies and execution ordering"""

    def __init__(self):
        self.task_graph: Dict[str, TaskNode] = {}
        self.ready_queue: asyncio.Queue = asyncio.Queue()
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        self._lock = asyncio.Lock()
        self.logger = get_mcp_logger("dependency_manager")

    async def add_task(self, research_action: ResearchAction) -> bool:
        """Add a task to the dependency graph"""
        async with self._lock:
            task_id = research_action.task_id

            if task_id in self.task_graph:
                self.logger.log_error(
                    f"Task {task_id} already exists in dependency graph",
                    task_id=task_id,
                    error_code="DUPLICATE_TASK",
                )
                return False

            # Create task node
            task_node = TaskNode(research_action=research_action)

            # Set up dependencies from explicit list
            if research_action.dependencies:
                for dep_id in research_action.dependencies:
                    if dep_id in self.completed_tasks:
                        # Dependency already completed, don't add it
                        continue
                    elif dep_id in self.failed_tasks:
                        # Dependency failed, mark task as blocked
                        task_node.status = TaskStatus.FAILED
                        self.logger.log_error(
                            f"Task {task_id} blocked due to failed dependency {dep_id}",
                            task_id=task_id,
                            error_code="DEPENDENCY_FAILED",
                        )
                        return False
                    elif dep_id in self.task_graph:
                        # Add dependency
                        task_node.dependencies.add(dep_id)
                        self.task_graph[dep_id].dependents.add(task_id)
                    else:
                        # Dependency doesn't exist yet-this might be okay for future tasks
                        task_node.dependencies.add(dep_id)

            # Set up parent dependency
            if research_action.parent_task_id:
                parent_id = research_action.parent_task_id
                if parent_id in self.completed_tasks:
                    # Parent already completed
                    pass
                elif parent_id in self.failed_tasks:
                    # Parent failed, block this task
                    task_node.status = TaskStatus.FAILED
                    self.logger.log_error(
                        f"Task {task_id} blocked due to failed parent {parent_id}",
                        task_id=task_id,
                        error_code="PARENT_FAILED",
                    )
                    return False
                elif parent_id in self.task_graph:
                    # Add parent dependency
                    task_node.dependencies.add(parent_id)
                    self.task_graph[parent_id].dependents.add(task_id)
                else:
                    # Parent doesn't exist yet
                    task_node.dependencies.add(parent_id)

            # Add to graph
            self.task_graph[task_id] = task_node

            # If task is ready, add to ready queue
            if task_node.is_ready and task_node.status == TaskStatus.PENDING:
                await self.ready_queue.put(task_id)
                task_node.status = TaskStatus.WORKING
                task_node.started_at = datetime.now()

            self.logger.log_event(
                LogLevel.INFO,
                LogEvent.TASK_DISPATCH,
                f"Added task {task_id} to dependency graph",
                task_id=task_id,
                context_id=research_action.context_id,
                details={
                    "dependencies": list(task_node.dependencies),
                    "parent_task_id": research_action.parent_task_id,
                    "is_ready": task_node.is_ready,
                },
            )

            return True

    async def complete_task(self, task_id: str, success: bool = True) -> List[str]:
        """Mark a task as completed and return newly ready tasks"""
        async with self._lock:
            if task_id not in self.task_graph:
                self.logger.log_error(
                    f"Cannot complete unknown task {task_id}",
                    task_id=task_id,
                    error_code="UNKNOWN_TASK",
                )
                return []

            task_node = self.task_graph[task_id]
            newly_ready = []

            if success:
                task_node.status = TaskStatus.COMPLETED
                task_node.completed_at = datetime.now()
                self.completed_tasks.add(task_id)

                # Check all dependent tasks
                for dependent_id in task_node.dependents:
                    if dependent_id in self.task_graph:
                        dependent_node = self.task_graph[dependent_id]
                        # Remove this dependency
                        dependent_node.dependencies.discard(task_id)

                        # If dependent is now ready, add to queue
                        if (
                            dependent_node.is_ready
                            and dependent_node.status == TaskStatus.PENDING
                        ):
                            await self.ready_queue.put(dependent_id)
                            dependent_node.status = TaskStatus.WORKING
                            dependent_node.started_at = datetime.now()
                            newly_ready.append(dependent_id)

                self.logger.log_task_completion(
                    task_id=task_id,
                    context_id=task_node.research_action.context_id,
                    agent_type=task_node.research_action.agent_type,
                    duration=(
                        (task_node.completed_at - task_node.started_at).total_seconds()
                        if task_node.started_at
                        else 0
                    ),
                    success=True,
                    newly_ready_tasks=newly_ready,
                )
            else:
                task_node.status = TaskStatus.FAILED
                task_node.completed_at = datetime.now()
                self.failed_tasks.add(task_id)

                # Mark all dependent tasks as failed
                failed_dependents = []
                for dependent_id in task_node.dependents:
                    if dependent_id in self.task_graph:
                        dependent_node = self.task_graph[dependent_id]
                        dependent_node.status = TaskStatus.FAILED
                        self.failed_tasks.add(dependent_id)
                        failed_dependents.append(dependent_id)

                self.logger.log_task_completion(
                    task_id=task_id,
                    context_id=task_node.research_action.context_id,
                    agent_type=task_node.research_action.agent_type,
                    duration=(
                        (task_node.completed_at-task_node.started_at).total_seconds()
                        if task_node.started_at
                        else 0
                    ),
                    success=False,
                    failed_dependents=failed_dependents,
                )

            return newly_ready

    async def get_ready_task(self) -> Optional[str]:
        """Get the next ready task for execution"""
        try:
            # Wait for a ready task with timeout
            task_id = await asyncio.wait_for(self.ready_queue.get(), timeout=1.0)
            return task_id
        except asyncio.TimeoutError:
            return None

    async def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific task"""
        async with self._lock:
            if task_id not in self.task_graph:
                return None

            return self.task_graph[task_id].to_dict()

    async def get_dependency_graph(self) -> Dict[str, Any]:
        """Get the complete dependency graph"""
        async with self._lock:
            return {
                "tasks": {
                    task_id: node.to_dict() for task_id, node in self.task_graph.items()
                },
                "completed_tasks": list(self.completed_tasks),
                "failed_tasks": list(self.failed_tasks),
                "ready_queue_size": self.ready_queue.qsize(),
                "total_tasks": len(self.task_graph),
            }

    async def get_task_children(self, task_id: str) -> List[str]:
        """Get all child tasks of a specific task"""
        async with self._lock:
            children = []
            for node in self.task_graph.values():
                if node.research_action.parent_task_id == task_id:
                    children.append(node.research_action.task_id)
            return children

    async def get_task_descendants(self, task_id: str) -> List[str]:
        """Get all descendant tasks (children, grandchildren, etc.)"""
        async with self._lock:
            descendants = []
            to_visit = [task_id]
            visited = set()

            while to_visit:
                current = to_visit.pop(0)
                if current in visited:
                    continue
                visited.add(current)

                # Find direct children
                children = await self.get_task_children(current)
                for child in children:
                    if child not in visited:
                        descendants.append(child)
                        to_visit.append(child)

            return descendants

    async def cancel_task_tree(self, task_id: str) -> List[str]:
        """Cancel a task and all its descendants"""
        async with self._lock:
            cancelled = []

            # Get all descendants
            descendants = await self.get_task_descendants(task_id)

            # Cancel root task and all descendants
            for tid in [task_id] + descendants:
                if tid in self.task_graph:
                    node = self.task_graph[tid]
                    if node.status in [TaskStatus.PENDING, TaskStatus.WORKING]:
                        node.status = TaskStatus.CANCELLED
                        cancelled.append(tid)

            self.logger.log_event(
                LogLevel.INFO,
                LogEvent.TASK_COMPLETION,
                f"Cancelled task tree starting from {task_id}",
                task_id=task_id,
                details={"cancelled_tasks": cancelled},
            )

            return cancelled

    async def get_stats(self) -> Dict[str, Any]:
        """Get dependency manager statistics"""
        async with self._lock:
            status_counts = {}
            for node in self.task_graph.values():
                status = node.status.value
                status_counts[status] = status_counts.get(status, 0) + 1

            return {
                "total_tasks": len(self.task_graph),
                "completed_tasks": len(self.completed_tasks),
                "failed_tasks": len(self.failed_tasks),
                "ready_queue_size": self.ready_queue.qsize(),
                "status_distribution": status_counts,
                "has_dependencies": sum(
                    1 for node in self.task_graph.values() if node.dependencies
                ),
                "average_dependencies": sum(
                    len(node.dependencies) for node in self.task_graph.values()
                )
                / max(len(self.task_graph), 1),
            }


# Default dependency manager instance
dependency_manager = TaskDependencyManager()
