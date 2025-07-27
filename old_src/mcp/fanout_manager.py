"""
Task Fan-out Manager for MCP Server

Enables parallel dispatch of tasks to multiple agent instances for improved throughput.
Handles task splitting, result aggregation, and parallel execution coordination.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from old_src.mcp.protocols import ResearchAction
from old_src.mcp.structured_logger import LogEvent, LogLevel, get_mcp_logger


class FanoutStrategy(Enum):
    """Fanout distribution strategies"""

    ROUND_ROBIN = "round_robin"
    LOAD_BALANCED = "load_balanced"
    BROADCAST = "broadcast"
    CUSTOM = "custom"


@dataclass
class FanoutTask:
    """Represents a task that has been fanned out"""

    parent_task_id: str
    subtask_ids: List[str] = field(default_factory=list)
    original_action: Optional[ResearchAction] = None
    parallelism: int = 1
    strategy: FanoutStrategy = FanoutStrategy.ROUND_ROBIN
    created_at: datetime = field(default_factory=datetime.now)
    completed_subtasks: int = 0
    failed_subtasks: int = 0
    partial_results: Dict[str, Any] = field(default_factory=dict)
    aggregated_result: Optional[Dict[str, Any]] = None
    aggregation_function: Optional[Callable] = None

    @property
    def is_complete(self) -> bool:
        """Check if all subtasks are complete"""
        return (self.completed_subtasks + self.failed_subtasks) >= len(self.subtask_ids)

    @property
    def success_rate(self) -> float:
        """Calculate success rate of subtasks"""
        if not self.subtask_ids:
            return 0.0
        return self.completed_subtasks / len(self.subtask_ids)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "parent_task_id": self.parent_task_id,
            "subtask_ids": self.subtask_ids,
            "parallelism": self.parallelism,
            "strategy": self.strategy.value,
            "created_at": self.created_at.isoformat(),
            "completed_subtasks": self.completed_subtasks,
            "failed_subtasks": self.failed_subtasks,
            "total_subtasks": len(self.subtask_ids),
            "is_complete": self.is_complete,
            "success_rate": self.success_rate,
            "has_aggregated_result": self.aggregated_result is not None,
        }


class TaskFanoutManager:
    """Manages task fan-out, parallel execution, and result aggregation"""

    def __init__(self):
        self.fanout_tasks: Dict[str, FanoutTask] = {}
        self.subtask_mapping: Dict[str, str] = {}  # subtask_id -> parent_task_id
        self._lock = asyncio.Lock()
        self.logger = get_mcp_logger("fanout_manager")

        # Default aggregation functions
        self.aggregation_functions = {
            "search": self._aggregate_search_results,
            "analyze": self._aggregate_analysis_results,
            "execute": self._aggregate_execution_results,
            "default": self._aggregate_default_results,
        }

    async def create_fanout_task(
        self,
        research_action: ResearchAction,
        parallelism: int,
        strategy: FanoutStrategy = FanoutStrategy.ROUND_ROBIN,
        custom_splitter: Optional[Callable] = None,
        custom_aggregator: Optional[Callable] = None,
    ) -> List[ResearchAction]:
        """Create a fan-out task and generate subtasks"""
        async with self._lock:
            parent_task_id = research_action.task_id

            if parent_task_id in self.fanout_tasks:
                self.logger.log_error(
                    f"Fanout task {parent_task_id} already exists",
                    task_id=parent_task_id,
                    error_code="DUPLICATE_FANOUT_TASK",
                )
                return []

            # Create fanout task
            fanout_task = FanoutTask(
                parent_task_id=parent_task_id,
                original_action=research_action,
                parallelism=parallelism,
                strategy=strategy,
                aggregation_function=custom_aggregator,
            )

            # Generate subtasks
            if custom_splitter:
                subtasks = await custom_splitter(research_action, parallelism)
            else:
                subtasks = await self._default_task_splitter(
                    research_action, parallelism, strategy
                )

            # Register subtasks
            for subtask in subtasks:
                fanout_task.subtask_ids.append(subtask.task_id)
                self.subtask_mapping[subtask.task_id] = parent_task_id

            self.fanout_tasks[parent_task_id] = fanout_task

            self.logger.log_event(
                LogLevel.INFO,
                LogEvent.TASK_DISPATCH,
                f"Created fanout task {parent_task_id} with {len(subtasks)} subtasks",
                task_id=parent_task_id,
                context_id=research_action.context_id,
                details={
                    "parallelism": parallelism,
                    "strategy": strategy.value,
                    "subtask_count": len(subtasks),
                    "subtask_ids": [st.task_id for st in subtasks],
                },
            )

            return subtasks

    async def complete_subtask(
        self, subtask_id: str, result: Dict[str, Any], success: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Complete a subtask and return aggregated result if all subtasks are done"""
        async with self._lock:
            if subtask_id not in self.subtask_mapping:
                self.logger.log_error(
                    f"Unknown subtask {subtask_id}",
                    task_id=subtask_id,
                    error_code="UNKNOWN_SUBTASK",
                )
                return None

            parent_task_id = self.subtask_mapping[subtask_id]
            fanout_task = self.fanout_tasks[parent_task_id]

            if success:
                fanout_task.completed_subtasks += 1
                fanout_task.partial_results[subtask_id] = result

                self.logger.log_task_completion(
                    task_id=subtask_id,
                    context_id=(
                        fanout_task.original_action.context_id
                        if fanout_task.original_action
                        else "unknown"
                    ),
                    agent_type=(
                        fanout_task.original_action.agent_type
                        if fanout_task.original_action
                        else "unknown"
                    ),
                    duration=0,  # Would need tracking for actual duration
                    success=True,
                    parent_task_id=parent_task_id,
                )
            else:
                fanout_task.failed_subtasks += 1

                self.logger.log_task_completion(
                    task_id=subtask_id,
                    context_id=(
                        fanout_task.original_action.context_id
                        if fanout_task.original_action
                        else "unknown"
                    ),
                    agent_type=(
                        fanout_task.original_action.agent_type
                        if fanout_task.original_action
                        else "unknown"
                    ),
                    duration=0,
                    success=False,
                    parent_task_id=parent_task_id,
                )

            # Check if all subtasks are complete
            if fanout_task.is_complete:
                # Aggregate results
                aggregated_result = await self._aggregate_results(fanout_task)
                fanout_task.aggregated_result = aggregated_result

                self.logger.log_event(
                    LogLevel.INFO,
                    LogEvent.TASK_COMPLETION,
                    f"Fanout task {parent_task_id} completed with {fanout_task.success_rate:.2%} success rate",
                    task_id=parent_task_id,
                    context_id=(
                        fanout_task.original_action.context_id
                        if fanout_task.original_action
                        else "unknown"
                    ),
                    details={
                        "completed_subtasks": fanout_task.completed_subtasks,
                        "failed_subtasks": fanout_task.failed_subtasks,
                        "success_rate": fanout_task.success_rate,
                        "aggregated_result_size": (
                            len(str(aggregated_result)) if aggregated_result else 0
                        ),
                    },
                )

                return aggregated_result

            return None

    async def _default_task_splitter(
        self,
        research_action: ResearchAction,
        parallelism: int,
        strategy: FanoutStrategy,
    ) -> List[ResearchAction]:
        """Default task splitting logic"""
        subtasks = []
        base_payload = research_action.payload.copy()

        for i in range(parallelism):
            subtask_id = f"{research_action.task_id}_sub_{i + 1}"

            # Modify payload based on strategy
            if strategy == FanoutStrategy.BROADCAST:
                # All subtasks get the same payload
                subtask_payload = base_payload.copy()
            elif strategy == FanoutStrategy.ROUND_ROBIN:
                # Distribute work round-robin style
                subtask_payload = base_payload.copy()
                subtask_payload["subtask_index"] = i
                subtask_payload["total_subtasks"] = parallelism

                # If there's a query or data list, split it
                if "queries" in base_payload and isinstance(
                    base_payload["queries"], list
                ):
                    queries = base_payload["queries"]
                    chunk_size = max(1, len(queries) // parallelism)
                    start_idx = i * chunk_size
                    end_idx = (
                        start_idx + chunk_size if i < parallelism-1 else len(queries)
                    )
                    subtask_payload["queries"] = queries[start_idx:end_idx]
                elif "data_chunks" in base_payload and isinstance(
                    base_payload["data_chunks"], list
                ):
                    chunks = base_payload["data_chunks"]
                    chunk_size = max(1, len(chunks) // parallelism)
                    start_idx = i * chunk_size
                    end_idx = (
                        start_idx + chunk_size if i < parallelism-1 else len(chunks)
                    )
                    subtask_payload["data_chunks"] = chunks[start_idx:end_idx]
            else:
                # Default: add subtask metadata
                subtask_payload = base_payload.copy()
                subtask_payload["subtask_index"] = i
                subtask_payload["total_subtasks"] = parallelism

            # Create subtask
            subtask = ResearchAction(
                task_id=subtask_id,
                context_id=research_action.context_id,
                agent_type=research_action.agent_type,
                action=research_action.action,
                payload=subtask_payload,
                priority=research_action.priority,
                timeout=research_action.timeout,
                parent_task_id=research_action.task_id,
            )

            subtasks.append(subtask)

        return subtasks

    async def _aggregate_results(self, fanout_task: FanoutTask) -> Dict[str, Any]:
        """Aggregate results from all subtasks"""
        if fanout_task.aggregation_function:
            return await fanout_task.aggregation_function(fanout_task)

        # Use default aggregation based on action type
        action = (
            fanout_task.original_action.action
            if fanout_task.original_action
            else "default"
        )
        if action in self.aggregation_functions:
            return await self.aggregation_functions[action](fanout_task)
        else:
            return await self.aggregation_functions["default"](fanout_task)

    async def _aggregate_search_results(
        self, fanout_task: FanoutTask
    ) -> Dict[str, Any]:
        """Aggregate search results"""
        return await self._aggregate_results_by_type(
            fanout_task,
            "search",
            {
                "results": list,  # Extend lists
                "sources": set,  # Union sets
                "relevance_score": "avg",  # Average numbers
            },
        )

    async def _aggregate_analysis_results(
        self, fanout_task: FanoutTask
    ) -> Dict[str, Any]:
        """Aggregate analysis results"""
        return await self._aggregate_results_by_type(
            fanout_task,
            "analyze",
            {"insights": list, "conclusions": list, "confidence": "avg"},
        )

    async def _aggregate_execution_results(
        self, fanout_task: FanoutTask
    ) -> Dict[str, Any]:
        """Aggregate execution results"""
        successful_executions = []
        failed_executions = []
        outputs = []

        for subtask_id, result in fanout_task.partial_results.items():
            if result.get("success", False):
                successful_executions.append(subtask_id)
                if "output" in result:
                    outputs.append(result["output"])
            else:
                failed_executions.append(subtask_id)

        return {
            "action": "execute",
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "outputs": outputs,
            "success_count": len(successful_executions),
            "failure_count": len(failed_executions),
            "subtask_count": len(fanout_task.partial_results),
            "success_rate": fanout_task.success_rate,
        }

    async def _aggregate_results_by_type(
        self, fanout_task: FanoutTask, action_name: str, field_configs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generic aggregation method to reduce code duplication.

        This method aggregates results from multiple subtasks based on the specified
        `field_configs`. It initializes collectors for each field, collects data from
        partial results, and processes the collected data according to the aggregation
        rules defined in `field_configs`.

        Parameters:
            fanout_task (FanoutTask): The task containing partial results to aggregate.
            action_name (str): The name of the action being aggregated (e.g., 'search', 'analyze').
            field_configs (Dict[str, Any]): A dictionary defining the aggregation rules for each field.
               -Keys are field names to aggregate.
               -Values specify the aggregation rule, which can be:
                  * `list`: Collects all values into a list.
                  * `set`: Collects all unique values into a set.
                  * `'avg'`: Computes the average of numeric values.

        Returns:
            Dict[str, Any]: A dictionary containing the aggregated results, including the action name
                and the aggregated fields.
        """
        aggregated: Dict[str, Any] = {"action": action_name}
        collectors: Dict[str, Any] = {}

        # Initialize collectors based on field configs
        for field_name, config in field_configs.items():
            if config == list:
                collectors[field_name] = []
            elif config == set:
                collectors[field_name] = set()
            elif config == "avg":
                collectors[field_name] = []

        # Collect data from all partial results
        for subtask_id, result in fanout_task.partial_results.items():
            for field_name, config in field_configs.items():
                if field_name in result:
                    if config == list and isinstance(result[field_name], list):
                        collectors[field_name].extend(result[field_name])
                    elif config == set:
                        if isinstance(result[field_name], (list, set)):
                            collectors[field_name].update(result[field_name])
                        else:
                            collectors[field_name].add(result[field_name])
                    elif config == "avg" and isinstance(
                        result[field_name], (int, float)
                    ):
                        collectors[field_name].append(result[field_name])

        # Process collected data
        for field_name, config in field_configs.items():
            if config == list:
                aggregated[field_name] = collectors[field_name]
                # Sort by relevance if available
                if (
                    field_name == "results"
                    and collectors[field_name]
                    and isinstance(collectors[field_name][0], dict)
                    and "relevance" in collectors[field_name][0]
                ):
                    aggregated[field_name].sort(
                        key=lambda x: x.get("relevance", 0), reverse=True
                    )
            elif config == set:
                aggregated[field_name] = list(collectors[field_name])
            elif config == "avg":
                values = collectors[field_name]
                aggregated[f"average_{field_name}"] = (
                    sum(values) / max(len(values), 1) if values else 0.0
                )

        # Add common metadata
        aggregated["subtask_count"] = len(fanout_task.partial_results)
        aggregated["success_rate"] = fanout_task.success_rate

        # Add action-specific metadata
        if action_name == "search":
            aggregated["total_results"] = len(aggregated.get("results", []))

        return aggregated

    async def _aggregate_default_results(
        self, fanout_task: FanoutTask
    ) -> Dict[str, Any]:
        """Default result aggregation"""
        return {
            "action": (
                fanout_task.original_action.action
                if fanout_task.original_action
                else "unknown"
            ),
            "partial_results": fanout_task.partial_results,
            "subtask_count": len(fanout_task.partial_results),
            "success_rate": fanout_task.success_rate,
            "completed_subtasks": fanout_task.completed_subtasks,
            "failed_subtasks": fanout_task.failed_subtasks,
        }

    async def get_fanout_task_info(
        self, parent_task_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get information about a fanout task"""
        async with self._lock:
            if parent_task_id not in self.fanout_tasks:
                return None

            return self.fanout_tasks[parent_task_id].to_dict()

    async def get_all_fanout_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all fanout tasks"""
        async with self._lock:
            return {
                task_id: task.to_dict() for task_id, task in self.fanout_tasks.items()
            }

    async def cancel_fanout_task(self, parent_task_id: str) -> List[str]:
        """Cancel a fanout task and all its subtasks"""
        async with self._lock:
            if parent_task_id not in self.fanout_tasks:
                return []

            fanout_task = self.fanout_tasks[parent_task_id]
            cancelled_subtasks = fanout_task.subtask_ids.copy()

            # Remove subtask mappings
            for subtask_id in cancelled_subtasks:
                self.subtask_mapping.pop(subtask_id, None)

            # Remove fanout task
            del self.fanout_tasks[parent_task_id]

            self.logger.log_event(
                LogLevel.INFO,
                LogEvent.TASK_COMPLETION,
                f"Cancelled fanout task {parent_task_id} and {len(cancelled_subtasks)} subtasks",
                task_id=parent_task_id,
                details={"cancelled_subtasks": cancelled_subtasks},
            )

            return cancelled_subtasks

    async def get_stats(self) -> Dict[str, Any]:
        """Get fanout manager statistics"""
        async with self._lock:
            total_subtasks = sum(
                len(task.subtask_ids) for task in self.fanout_tasks.values()
            )
            completed_fanouts = sum(
                1 for task in self.fanout_tasks.values() if task.is_complete
            )

            strategy_counts = {}
            for task in self.fanout_tasks.values():
                strategy = task.strategy.value
                strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

            return {
                "total_fanout_tasks": len(self.fanout_tasks),
                "completed_fanout_tasks": completed_fanouts,
                "total_subtasks": total_subtasks,
                "active_subtasks": len(self.subtask_mapping),
                "strategy_distribution": strategy_counts,
                "average_parallelism": total_subtasks / max(len(self.fanout_tasks), 1),
            }


# Default fanout manager instance
fanout_manager = TaskFanoutManager()
