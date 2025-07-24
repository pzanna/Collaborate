"""
Parallelism Coordinator (Phase 2)

Integrates all Phase 2 parallelism components including dependency management,
fanout management, and enhanced RM prompting for intelligent parallel execution.
"""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from .dependency_manager import TaskDependencyManager
    from .fanout_manager import FanoutStrategy, TaskFanoutManager
    from .protocols import ResearchAction
    from .rm_system_prompt import (get_enhanced_rm_prompt, suggest_parallelism,
                                   validate_parallelism_value)
except ImportError:
    from dependency_manager import TaskDependencyManager
    from fanout_manager import FanoutStrategy, TaskFanoutManager
    from protocols import ResearchAction
    from rm_system_prompt import (get_enhanced_rm_prompt, suggest_parallelism,
                                  validate_parallelism_value)


class ParallelismMode(Enum):
    """Parallelism execution modes."""

    SEQUENTIAL = "sequential"
    AUTOMATIC = "automatic"
    EXPLICIT = "explicit"
    ADAPTIVE = "adaptive"


@dataclass
class ParallelExecution:
    """Represents a parallel execution plan."""

    original_task: ResearchAction
    execution_mode: ParallelismMode
    parallel_tasks: List[ResearchAction]
    dependencies: List[str]
    estimated_completion_time: float
    strategy: FanoutStrategy
    created_at: float


class ParallelismCoordinator:
    """
    Central coordinator for intelligent parallel task execution.

    Integrates dependency management, fanout execution, and RM prompting
    to provide comprehensive parallelism support for the MCP system.
    """

    def __init__(self):
        """Initialize the parallelism coordinator."""
        self.logger = logging.getLogger(__name__)
        self.dependency_manager = TaskDependencyManager()
        self.fanout_manager = TaskFanoutManager()

        # Active parallel executions
        self.active_executions: Dict[str, ParallelExecution] = {}

        # Performance tracking
        self.execution_stats = {
            "total_parallel_tasks": 0,
            "completed_parallel_tasks": 0,
            "average_speedup": 0.0,
            "parallel_success_rate": 0.0,
        }

        self.logger.info("Parallelism coordinator initialized")

    async def get_enhanced_system_prompt(self) -> str:
        """
        Get the enhanced RM system prompt with parallelism support.

        Returns:
            str: Enhanced system prompt
        """
        return get_enhanced_rm_prompt()

    async def analyze_task_for_parallelism(
        self, task: ResearchAction, context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, int, ParallelismMode]:
        """
        Analyze a task to determine if it should be executed in parallel.

        Args:
            task: The research action to analyze
            context: Optional context information

        Returns:
            Tuple of (should_parallelize, suggested_parallelism, mode)
        """
        try:
            # Check if task already has explicit parallelism setting
            if (
                hasattr(task, "parallelism")
                and task.parallelism
                and task.parallelism > 1
            ):
                validated_parallelism = validate_parallelism_value(task.parallelism)
                self.logger.info(
                    f"Task {task.task_id} has explicit parallelism: {validated_parallelism}"
                )
                return True, validated_parallelism, ParallelismMode.EXPLICIT

            # Analyze task characteristics for automatic parallelism
            item_count = self._extract_item_count(task)
            task_description = f"{task.action} {str(task.payload)}"

            suggested = suggest_parallelism(task_description, item_count)

            if suggested > 1:
                self.logger.info(
                    f"Task {task.task_id} suggests parallelism: {suggested}"
                )
                return True, suggested, ParallelismMode.AUTOMATIC
            else:
                self.logger.info(f"Task {task.task_id} will run sequentially")
                return False, 1, ParallelismMode.SEQUENTIAL

        except Exception as e:
            self.logger.error(
                f"Error analyzing task {task.task_id} for parallelism: {e}"
            )
            return False, 1, ParallelismMode.SEQUENTIAL

    def _extract_item_count(self, task: ResearchAction) -> int:
        """
        Extract the number of items to process from a task.

        Args:
            task: The research action

        Returns:
            int: Number of items to process
        """
        payload = task.payload

        if isinstance(payload, dict):
            # Common patterns for item counting
            item_indicators = [
                "queries",
                "documents",
                "files",
                "items",
                "chunks",
                "sources",
                "urls",
                "papers",
                "results",
                "data_points",
            ]

            for indicator in item_indicators:
                if indicator in payload:
                    items = payload[indicator]
                    if isinstance(items, list):
                        return len(items)
                    elif isinstance(items, int):
                        return items

            # Check for batch size indicators
            batch_indicators = ["batch_size", "chunk_size", "page_size"]
            for indicator in batch_indicators:
                if indicator in payload:
                    return max(payload[indicator], 1)

        # Default to 1 if we can't determine item count
        return 1

    async def create_parallel_execution(
        self,
        task: ResearchAction,
        parallelism: int,
        mode: ParallelismMode,
        strategy: FanoutStrategy = FanoutStrategy.ROUND_ROBIN,
    ) -> Optional[ParallelExecution]:
        """
        Create a parallel execution plan for a task.

        Args:
            task: The original task
            parallelism: Number of parallel subtasks
            mode: Parallelism mode
            strategy: Fanout strategy to use

        Returns:
            ParallelExecution object or None if creation failed
        """
        try:
            # Check dependencies (simplified)
            dependencies = []
            if hasattr(task, "dependencies") and task.dependencies:
                dependencies = task.dependencies

                # Simple dependency check using completed_tasks set
                for dep_id in dependencies:
                    if dep_id not in self.dependency_manager.completed_tasks:
                        self.logger.info(
                            f"Task {task.task_id} blocked by dependency {dep_id}"
                        )
                        return None

            # Create fanout subtasks
            subtasks = await self.fanout_manager.create_fanout_task(
                task, parallelism=parallelism, strategy=strategy
            )

            if not subtasks:
                self.logger.error(f"Failed to create fanout for task {task.task_id}")
                return None

            # Estimate completion time (simplified heuristic)
            estimated_time = self._estimate_completion_time(task, parallelism)

            # Create execution plan
            execution = ParallelExecution(
                original_task=task,
                execution_mode=mode,
                parallel_tasks=subtasks,
                dependencies=dependencies,
                estimated_completion_time=estimated_time,
                strategy=strategy,
                created_at=asyncio.get_event_loop().time(),
            )

            self.active_executions[task.task_id] = execution

            self.logger.info(
                f"Created parallel execution for {task.task_id} with {len(subtasks)} subtasks"
            )

            return execution

        except Exception as e:
            self.logger.error(
                f"Error creating parallel execution for {task.task_id}: {e}"
            )
            return None

    def _estimate_completion_time(
        self, task: ResearchAction, parallelism: int
    ) -> float:
        """
        Estimate completion time for a parallel task.

        Args:
            task: The original task
            parallelism: Number of parallel subtasks

        Returns:
            float: Estimated completion time in seconds
        """
        # Base time estimates by action type (in seconds)
        action_times = {
            "search": 30,
            "retrieve": 20,
            "analyze": 60,
            "process": 45,
            "compute": 40,
            "synthesize": 15,
            "summarize": 20,
        }

        base_time = action_times.get(task.action, 30)

        # Apply parallelism speedup (not linear due to overhead)
        speedup_factor = min(parallelism * 0.8, parallelism)  # 80% efficiency
        estimated_time = base_time / speedup_factor

        return max(estimated_time, 5)  # Minimum 5 seconds

    async def execute_parallel_task(
        self,
        execution: ParallelExecution,
        execution_callback: Optional[Callable] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Execute a parallel task plan.

        Args:
            execution: The parallel execution plan
            execution_callback: Optional callback for subtask execution

        Returns:
            Aggregated results or None if execution failed
        """
        try:
            task_id = execution.original_task.task_id

            self.logger.info(f"Starting parallel execution for {task_id}")

            # Track execution start time
            start_time = asyncio.get_event_loop().time()

            # Execute subtasks (this would integrate with the actual agent execution system)
            if execution_callback:
                # Execute subtasks through provided callback
                for subtask in execution.parallel_tasks:
                    asyncio.create_task(execution_callback(subtask))

                # Wait for all subtasks to complete or timeout
                await self._wait_for_subtasks_completion(execution)

            # Get aggregated results from fanout manager
            fanout_info = await self.fanout_manager.get_fanout_task_info(task_id)
            if fanout_info and fanout_info["is_complete"]:
                # Execution completed successfully
                end_time = asyncio.get_event_loop().time()
                end_time - start_time

                self.logger.info(f"Parallel execution completed for {task_id}")

                # Update stats
                self.execution_stats["completed_parallel_tasks"] += 1

                # Clean up
                del self.active_executions[task_id]

                return fanout_info
            else:
                self.logger.warning(f"Parallel execution incomplete for {task_id}")
                return None

        except Exception as e:
            self.logger.error(
                f"Error in parallel execution for {execution.original_task.task_id}: {e}"
            )
            return None

    async def _wait_for_subtasks_completion(
        self, execution: ParallelExecution, timeout: int = 300
    ) -> bool:
        """
        Wait for all subtasks in a parallel execution to complete.

        Args:
            execution: The parallel execution
            timeout: Maximum time to wait in seconds

        Returns:
            bool: True if all subtasks completed, False if timeout
        """
        task_id = execution.original_task.task_id
        start_time = asyncio.get_event_loop().time()

        while True:
            # Check if execution is complete
            fanout_info = await self.fanout_manager.get_fanout_task_info(task_id)
            if fanout_info and fanout_info["is_complete"]:
                return True

            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                self.logger.warning(f"Parallel execution timeout for {task_id}")
                return False

            # Wait a bit before checking again
            await asyncio.sleep(1)

    async def get_execution_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a parallel execution.

        Args:
            task_id: The task ID

        Returns:
            Dict with execution status or None if not found
        """
        if task_id not in self.active_executions:
            return None

        execution = self.active_executions[task_id]
        fanout_info = await self.fanout_manager.get_fanout_task_info(task_id)

        current_time = asyncio.get_event_loop().time()
        elapsed_time = current_time - execution.created_at

        return {
            "task_id": task_id,
            "mode": execution.execution_mode.value,
            "strategy": execution.strategy.value,
            "parallel_task_count": len(execution.parallel_tasks),
            "elapsed_time": elapsed_time,
            "estimated_completion_time": execution.estimated_completion_time,
            "fanout_info": fanout_info,
            "dependencies": execution.dependencies,
        }

    async def cancel_parallel_execution(self, task_id: str) -> bool:
        """
        Cancel a parallel execution.

        Args:
            task_id: The task ID to cancel

        Returns:
            bool: True if cancellation successful
        """
        try:
            if task_id not in self.active_executions:
                return False

            # Cancel fanout task
            await self.fanout_manager.cancel_fanout_task(task_id)

            # Remove from active executions
            del self.active_executions[task_id]

            self.logger.info(f"Cancelled parallel execution for {task_id}")

            return True

        except Exception as e:
            self.logger.error(f"Error cancelling parallel execution for {task_id}: {e}")
            return False

    async def get_coordinator_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about parallel execution.

        Returns:
            Dict with coordinator statistics
        """
        fanout_stats = await self.fanout_manager.get_stats()
        dependency_stats = await self.dependency_manager.get_stats()

        return {
            "active_executions": len(self.active_executions),
            "execution_stats": self.execution_stats,
            "fanout_stats": fanout_stats,
            "dependency_stats": dependency_stats,
            "total_components": 3,  # dependency_manager, fanout_manager, rm_prompt
        }


# Factory function for easy instantiation
async def create_parallelism_coordinator() -> ParallelismCoordinator:
    """
    Create and initialize a parallelism coordinator.

    Returns:
        ParallelismCoordinator: Initialized coordinator
    """
    coordinator = ParallelismCoordinator()

    # Log the enhanced system prompt availability
    prompt = await coordinator.get_enhanced_system_prompt()
    coordinator.logger.info(
        f"Coordinator initialized with enhanced prompt ({len(prompt)} chars)"
    )

    return coordinator
