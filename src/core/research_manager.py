"""
Research Manager - Orchestrates multi - agent research tasks using MCP protocol.

This module provides the core Research Manager that coordinates between different
AI agents (Literature, Planning, Executor, Memory) to perform complex research tasks.
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

try:
    # Try relative imports first (when imported from within src package)
    from ..config.config_manager import ConfigManager
    from ..mcp.client import MCPClient
    from ..mcp.cost_estimator import CostEstimator
    from ..mcp.protocols import AgentResponse, ResearchAction, TaskStatus
    from ..storage.hierarchical_database import HierarchicalDatabaseManager
    from ..utils.error_handler import ErrorHandler
    from ..utils.id_utils import generate_timestamped_id
    from ..utils.performance import PerformanceMonitor
except ImportError:
    # Fall back to absolute imports (when imported from outside src package)
    from config.config_manager import ConfigManager
    from mcp.client import MCPClient
    from mcp.cost_estimator import CostEstimator
    from mcp.protocols import AgentResponse, ResearchAction, TaskStatus
    from storage.hierarchical_database import HierarchicalDatabaseManager
    from utils.error_handler import ErrorHandler
    from utils.id_utils import generate_timestamped_id
    from utils.performance import PerformanceMonitor

# Type for database manager
DatabaseManagerType = HierarchicalDatabaseManager


class ResearchStage(Enum):
    """
    Stages of the research process.

    Attributes:
        PLANNING: Initial planning and setup of the research task.
        LITERATURE_REVIEW: Systematic literature review and information gathering.
        REASONING: Analysis and reasoning over gathered information.
        EXECUTION: Execution of research actions and experiments.
        SYNTHESIS: Synthesis and integration of results into final output.
        COMPLETE: Task completed successfully.
        FAILED: Task failed or was cancelled.
    """

    PLANNING = "planning"
    LITERATURE_REVIEW = "literature_review"
    REASONING = "reasoning"
    EXECUTION = "execution"
    SYNTHESIS = "synthesis"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class ResearchContext:
    """Context for research task execution."""

    task_id: str
    query: str
    user_id: str
    project_id: Optional[str] = None  # Project association
    stage: ResearchStage = ResearchStage.PLANNING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # Research data
    search_results: List[Dict[str, Any]] = field(default_factory=list)
    reasoning_output: Optional[str] = None
    execution_results: List[Dict[str, Any]] = field(default_factory=list)
    synthesis: Optional[str] = None

    # Progress tracking
    completed_stages: List[ResearchStage] = field(default_factory=list)
    failed_stages: List[ResearchStage] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3

    # Cost tracking
    estimated_cost: float = 0.0
    actual_cost: float = 0.0
    cost_approved: bool = False
    single_agent_mode: bool = False

    # Context management
    context_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResearchManager:
    """
    Main orchestrator for multi - agent research tasks.

    The Research Manager coordinates between different AI agents to perform
    complex research tasks, managing the flow of information and ensuring
    proper task completion.
    """

    def __init__(self, config_manager: ConfigManager, db_manager: Optional[DatabaseManagerType] = None):
        """
        Initialize the Research Manager.

        Args:
            config_manager: Configuration manager instance
            db_manager: Database manager instance (optional, will create if not provided)
        """
        self.config = config_manager
        self.logger = logging.getLogger(__name__)
        self.error_handler = ErrorHandler()
        self.performance_monitor = PerformanceMonitor()

        # Database manager for storing research plans and results
        self.db_manager = db_manager if db_manager else HierarchicalDatabaseManager()

        # Cost control
        self.cost_estimator = CostEstimator(config_manager)

        # MCP client for agent communication
        self.mcp_client: Optional[MCPClient] = None

        # Active research contexts
        self.active_contexts: Dict[str, ResearchContext] = {}

        # Agent capabilities and availability
        self.agent_capabilities: Dict[str, List[str]] = {}
        self.agent_availability: Dict[str, bool] = {}

        # Response tracking for agent communications
        self.pending_responses: Dict[str, asyncio.Future] = {}
        self.response_timeout = 60  # seconds

        # Callbacks for UI updates
        self.progress_callbacks: List[Callable] = []
        self.completion_callbacks: List[Callable] = []

        # Configuration
        self.research_config = self.config.get_research_config()
        self.max_concurrent_tasks = self.research_config.get("max_concurrent_tasks", 5)
        self.task_timeout = self.research_config.get("task_timeout", 600)  # 10 minutes

        self.logger.info("Research Manager initialized with cost control")

    async def _ensure_mcp_client_initialized(self) -> None:
        """
        Ensure MCP client is initialized (lazy initialization).
        """
        if self.mcp_client is None:
            try:
                # Initialize MCP client
                mcp_config = self.config.get_mcp_config()
                self.mcp_client = MCPClient(host=mcp_config.get("host", "localhost"), port=mcp_config.get("port", 8765))

                # Connect to MCP server
                await self.mcp_client.connect()

                # Identify as research manager
                if self.mcp_client.websocket:
                    import json

                    identification_message = {
                        "type": "identify_research_manager",
                        "data": {"manager_id": "research_manager"},
                        "timestamp": datetime.now().isoformat(),
                    }
                    self.logger.info(f"Sending research manager identification: {identification_message}")
                    await self.mcp_client.websocket.send(json.dumps(identification_message))
                    self.logger.info("✓ Successfully sent research manager identification to MCP server")
                else:
                    self.logger.error("No WebSocket connection available for identification")

                # Register message handlers
                self.mcp_client.add_message_handler("agent_response", self._handle_agent_response)
                self.mcp_client.add_message_handler("agent_registration", self._handle_agent_registration)
                self.mcp_client.add_message_handler("task_update", self._handle_task_update)

                self.logger.info("MCP client initialized successfully")

            except Exception as e:
                self.logger.error(f"Failed to initialize MCP client: {e}")
                self.error_handler.handle_error(e, "mcp_client_init")
                # Set to None to allow retries
                self.mcp_client = None
                raise

    async def initialize(self, external_mcp_client: Optional[MCPClient] = None) -> bool:
        """
        Initialize the Research Manager and establish MCP connection.

        Args:
            external_mcp_client: Optional external MCP client to use

        Returns:
            bool: True if initialization successful
        """
        try:
            if external_mcp_client:
                # Use external MCP client
                self.mcp_client = external_mcp_client

                # Identify as research manager
                if self.mcp_client.websocket:
                    import json

                    identification_message = {
                        "type": "identify_research_manager",
                        "data": {"manager_id": "research_manager"},
                        "timestamp": datetime.now().isoformat(),
                    }
                    self.logger.info(f"Sending research manager identification: {identification_message}")
                    await self.mcp_client.websocket.send(json.dumps(identification_message))
                    self.logger.info("✓ Successfully sent research manager identification to MCP server")
                else:
                    self.logger.error("No WebSocket connection available for identification")

                # Register message handlers
                self.mcp_client.add_message_handler("agent_response", self._handle_agent_response)
                self.mcp_client.add_message_handler("agent_registration", self._handle_agent_registration)
                self.mcp_client.add_message_handler("task_update", self._handle_task_update)

                self.logger.info("Research Manager initialized with external MCP client")
            else:
                # Use internal initialization
                await self._ensure_mcp_client_initialized()
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize Research Manager: {e}")
            self.error_handler.handle_error(e, "research_manager_init")
            return False

    async def _estimate_task_cost(
        self, query: str, task_id: str, options: Optional[Dict[str, Any]] = None
    ) -> tuple[Dict[str, Any], bool, bool]:
        """
        Estimate cost for a research task with approval logic.

        Args:
            query: Research query to process
            task_id: ID of the task for cost tracking
            options: Optional task configuration including single_agent_mode

        Returns:
            tuple: (cost_info, should_proceed, single_agent_mode)
        """
        # Determine agent configuration
        single_agent_mode = options.get("single_agent_mode", False) if options else False

        if single_agent_mode:
            agents_to_use = ["Literature"]  # Use only literature in single agent mode
            parallel_execution = False
        else:
            agents_to_use = ["Literature", "Planning", "Executor", "Memory"]
            parallel_execution = True

        # Get cost estimate
        cost_estimate = self.cost_estimator.estimate_task_cost(
            query=query, agents=agents_to_use, parallel_execution=parallel_execution
        )

        # Check if task should proceed based on cost
        should_proceed, cost_reason = self.cost_estimator.should_proceed_with_task(cost_estimate, task_id)

        # Get cost recommendations
        recommendations = self.cost_estimator.get_cost_recommendations(cost_estimate)

        # Prepare cost information for return
        cost_info = {
            "estimate": {
                "tokens": cost_estimate.estimated_tokens,
                "cost_usd": cost_estimate.estimated_cost_usd,
                "complexity": cost_estimate.task_complexity.value,
                "agent_count": cost_estimate.agent_count,
                "confidence": cost_estimate.confidence,
                "reasoning": cost_estimate.reasoning,
            },
            "should_proceed": should_proceed,
            "cost_reason": cost_reason,
            "recommendations": recommendations,
        }

        return cost_info, should_proceed, single_agent_mode

    async def start_research_task(
        self, query: str, user_id: str, project_id: Optional[str] = None, options: Optional[Dict[str, Any]] = None
    ) -> tuple[str, Dict[str, Any]]:
        """
        Start a new research task with cost estimation and control.

        Args:
            query: Research query to process
            user_id: ID of the user making the request
            project_id: ID of the project (optional)
            options: Optional task configuration including cost_override

        Returns:
            tuple: (task_id, cost_info) where cost_info contains estimation and recommendations
        """
        task_id = str(uuid.uuid4())

        try:
            # Ensure MCP client is initialized
            await self._ensure_mcp_client_initialized()

            # Estimate cost for the research task
            cost_info, should_proceed, single_agent_mode = await self._estimate_task_cost(query, task_id, options)

            # Create research context
            context = ResearchContext(
                task_id=task_id,
                query=query,
                user_id=user_id,
                project_id=project_id or (options.get("project_id") if options else None),
                estimated_cost=cost_info["estimate"]["cost_usd"],
                single_agent_mode=single_agent_mode,
            )

            # Apply options if provided
            if options:
                context.max_retries = options.get("max_retries", context.max_retries)
                context.metadata.update(options.get("metadata", {}))
                # Add topic_id from options to metadata if provided
                if options.get("topic_id"):
                    context.metadata["topic_id"] = options["topic_id"]
                # Check for cost override
                context.cost_approved = options.get("cost_override", False)

            # Only proceed if cost is approved or automatically acceptable
            if should_proceed or context.cost_approved:
                context.cost_approved = True

                # Create research plan and individual task entries
                try:
                    plan_id = await self._create_research_plan_and_tasks(context)
                    if plan_id:
                        context.metadata["plan_id"] = plan_id
                        self.logger.info(f"Created research plan {plan_id} with individual task entries for {task_id}")
                    else:
                        self.logger.warning(f"Failed to create research plan and tasks for {task_id}")

                except Exception as e:
                    self.logger.error(f"Error creating research plan and tasks for {task_id}: {e}")
                    # Continue with task execution even if database creation fails

                # Start cost tracking
                self.cost_estimator.start_cost_tracking(task_id, task_id)

                # Store context
                self.active_contexts[task_id] = context

                # Start task orchestration
                asyncio.create_task(self._orchestrate_research_task(context))

                self.logger.info(
                    f"Started research task {task_id} for query: {query}, "
                    f"estimated cost: ${cost_info['estimate']['cost_usd']:.4f}"
                )
            else:
                # Task not approved due to cost
                cost_info["task_started"] = False
                self.logger.warning(f"Research task blocked due to cost: {cost_info['cost_reason']}")

            cost_info["task_started"] = should_proceed or context.cost_approved
            return task_id, cost_info

        except Exception as e:
            self.logger.error(f"Failed to start research task: {e}")
            self.error_handler.handle_error(e, "start_research_task")
            raise

    async def _orchestrate_research_task(self, context: ResearchContext) -> None:
        """
        Orchestrate the complete research task workflow.

        Args:
            context: Research context to process
        """
        try:
            # Start performance tracking
            self.performance_monitor.start_timer(f"research_task_{context.task_id}")

            # Execute research stages sequentially (or single agent if specified)
            if context.single_agent_mode:
                # Single agent mode - only use literature
                stages = [
                    (ResearchStage.PLANNING, self._execute_planning_stage),
                    (ResearchStage.LITERATURE_REVIEW, self._execute_literature_review_stage),
                ]
                self.logger.info(f"Running task {context.task_id} in single - agent mode (cost - optimized)")
            else:
                # Full multi - agent mode
                stages = [
                    (ResearchStage.PLANNING, self._execute_planning_stage),
                    (ResearchStage.LITERATURE_REVIEW, self._execute_literature_review_stage),
                    (ResearchStage.REASONING, self._execute_reasoning_stage),
                    (ResearchStage.EXECUTION, self._execute_execution_stage),
                    (ResearchStage.SYNTHESIS, self._execute_synthesis_stage),
                ]

            for stage, executor in stages:
                if stage in context.failed_stages:
                    continue

                try:
                    context.stage = stage
                    context.updated_at = datetime.now()

                    # Create database entry for this stage task (only when it starts)
                    self._create_stage_task_in_database(context)

                    # Update database with current stage
                    self._update_task_in_database(context)

                    # Notify progress
                    await self._notify_progress(context)

                    # Execute stage
                    success = await executor(context)

                    if success:
                        context.completed_stages.append(stage)
                        context.updated_at = datetime.now()
                        self._update_task_in_database(context)
                        self.logger.info(f"Completed stage {stage.value} for task {context.task_id}")

                        # If this was the planning stage, wait for approval before proceeding
                        if stage == ResearchStage.PLANNING:
                            self.logger.info(
                                f"Planning stage completed for task {context.task_id}. Waiting for plan approval."
                            )

                            # Update task status to indicate planning is complete and waiting for approval
                            try:
                                task = self.db_manager.get_research_task(context.task_id)
                                if task:
                                    task["stage"] = "planning_complete"
                                    task["status"] = "waiting_approval"
                                    self.db_manager.update_research_task(task)
                            except Exception as e:
                                self.logger.error(f"Failed to update task status after planning: {e}")

                            # Wait for plan approval (this will pause the workflow)
                            approved = await self._wait_for_plan_approval(context.task_id)
                            if not approved:
                                self.logger.info(
                                    f"Research plan for task {context.task_id} was not approved. Stopping workflow."
                                )
                                context.stage = ResearchStage.FAILED
                                await self._notify_completion(context, success=False)
                                return
                            else:
                                self.logger.info(
                                    f"Research plan for task {context.task_id} approved. Continuing workflow."
                                )

                    else:
                        context.failed_stages.append(stage)
                        context.updated_at = datetime.now()
                        self._update_task_in_database(context)
                        self.logger.error(f"Failed stage {stage.value} for task {context.task_id}")

                        # Retry logic
                        if context.retry_count < context.max_retries:
                            context.retry_count += 1
                            context.failed_stages.remove(stage)
                            self.logger.info(
                                f"Retrying stage {stage.value} for task {context.task_id} (attempt {context.retry_count})"
                            )
                            # Re - execute the stage
                            success = await executor(context)
                            if success:
                                context.completed_stages.append(stage)
                            else:
                                context.failed_stages.append(stage)
                                break
                        else:
                            break

                except Exception as e:
                    self.logger.error(f"Error in stage {stage.value} for task {context.task_id}: {e}")
                    context.failed_stages.append(stage)
                    break

            # End performance tracking
            self.performance_monitor.end_timer(f"research_task_{context.task_id}")

            # Determine final status
            if len(context.completed_stages) == len(stages):
                context.stage = ResearchStage.COMPLETE
                context.updated_at = datetime.now()
                self._update_task_in_database(context)
                await self._notify_completion(context, success=True)
            else:
                context.stage = ResearchStage.FAILED
                context.updated_at = datetime.now()
                self._update_task_in_database(context)
                await self._notify_completion(context, success=False)

        except Exception as e:
            self.logger.error(f"Critical error in research task orchestration: {e}")
            context.stage = ResearchStage.FAILED
            context.updated_at = datetime.now()
            self._update_task_in_database(context)
            await self._notify_completion(context, success=False)
        finally:
            # End cost tracking and get final usage
            if context.cost_approved:
                final_usage = self.cost_estimator.end_cost_tracking(context.task_id)
                if final_usage:
                    context.actual_cost = final_usage.cost_usd
                    context.updated_at = datetime.now()
                    self._update_task_in_database(context)
                    self.logger.info(f"Task {context.task_id} completed with final cost: ${context.actual_cost:.4f}")

            # Clean up context after delay
            asyncio.create_task(self._cleanup_context(context.task_id, delay=3600))  # 1 hour

    async def _execute_planning_stage(self, context: ResearchContext) -> bool:
        """
        Execute the planning stage of research.

        Args:
            context: Research context

        Returns:
            bool: True if successful
        """
        try:
            # Create planning action
            action = ResearchAction(
                task_id=context.task_id,
                context_id=context.task_id,
                agent_type="Planning",
                action="plan_research",
                payload={
                    "query": context.query,
                    "context": context.context_data,
                    "user_id": context.user_id,
                    "task_id": context.task_id,
                },
            )

            # Send to planning agent
            response = await self._send_to_agent("Planning", action)

            if response and response.status == "completed":
                # Update context with planning results
                context.context_data["research_plan"] = response.result

                # Store the research plan in the database
                if response.result:
                    # The planning agent should return the detailed research plan
                    # Try different possible structures for the plan data
                    plan_data = None

                    if isinstance(response.result, dict):
                        if "plan" in response.result:
                            plan_data = response.result["plan"]
                        else:
                            # The entire result might be the plan data
                            plan_data = response.result

                    if plan_data:
                        try:
                            # Get the correct plan ID from context metadata
                            plan_id = context.metadata.get("plan_id")
                            if plan_id:
                                # Update the plan structure with the AI - generated plan
                                result = self.db_manager.update_research_plan(
                                    plan_id, {"plan_structure": plan_data, "status": "active", "plan_approved": True}
                                )
                                if result:
                                    self.logger.info(f"Research plan stored in database for plan {plan_id}")
                                else:
                                    self.logger.warning(f"Failed to store research plan in database for plan {plan_id}")
                            else:
                                self.logger.warning(f"No plan_id found in context metadata for task {context.task_id}")
                        except Exception as e:
                            self.logger.error(f"Error storing research plan in database: {e}")
                    else:
                        self.logger.warning(f"No valid plan data found in response for task {context.task_id}")

                return True

            return False

        except Exception as e:
            self.logger.error(f"Planning stage failed: {e}")
            return False

    async def _execute_literature_review_stage(self, context: ResearchContext) -> bool:
        """
        Execute the literature review stage of research.

        Args:
            context: Research context

        Returns:
            bool: True if successful
        """
        try:
            # Create literature review action
            action = ResearchAction(
                task_id=context.task_id,
                context_id=context.task_id,
                agent_type="Literature",
                action="search_information",
                payload={
                    "query": context.query,
                    "context": context.context_data,
                    "search_depth": "comprehensive",
                    "max_results": 10,
                },
            )

            # Send to literature agent
            response = await self._send_to_agent("Literature", action)

            if response and response.status == "completed":
                # Store search results
                if response.result:
                    context.search_results = response.result.get("results", [])
                    context.context_data["search_results"] = context.search_results
                return True

            return False

        except Exception as e:
            self.logger.error(f"Literature review stage failed: {e}")
            return False

    async def _execute_reasoning_stage(self, context: ResearchContext) -> bool:
        """
        Execute the reasoning stage of research.

        Args:
            context: Research context

        Returns:
            bool: True if successful
        """
        try:
            # Create reasoning action
            action = ResearchAction(
                task_id=context.task_id,
                context_id=context.task_id,
                agent_type="Planning",
                action="analyze_information",
                payload={
                    "query": context.query,
                    "context": context.context_data,
                    "analysis_type": "comprehensive",
                    "include_sources": True,
                },
            )

            # Send to planning agent
            response = await self._send_to_agent("Planning", action)

            if response and response.status == "completed":
                # Store reasoning output
                if response.result:
                    context.reasoning_output = response.result.get("analysis", "")
                    context.context_data["reasoning_output"] = context.reasoning_output
                return True

            return False

        except Exception as e:
            self.logger.error(f"Reasoning stage failed: {e}")
            return False

    async def _execute_execution_stage(self, context: ResearchContext) -> bool:
        """
        Execute the execution stage of research.

        Args:
            context: Research context

        Returns:
            bool: True if successful
        """
        try:
            # Create execution action
            action = ResearchAction(
                task_id=context.task_id,
                context_id=context.task_id,
                agent_type="Executor",
                action="execute_research",
                payload={"query": context.query, "context": context.context_data, "execution_type": "comprehensive"},
            )

            # Send to execution agent
            response = await self._send_to_agent("Executor", action)

            if response and response.status == "completed":
                # Store execution results
                if response.result:
                    context.execution_results = response.result.get("results", [])
                    context.context_data["execution_results"] = context.execution_results
                return True

            return False

        except Exception as e:
            self.logger.error(f"Execution stage failed: {e}")
            return False

    async def _execute_synthesis_stage(self, context: ResearchContext) -> bool:
        """
        Execute the synthesis stage of research.

        Args:
            context: Research context

        Returns:
            bool: True if successful
        """
        try:
            # Create synthesis action
            action = ResearchAction(
                task_id=context.task_id,
                context_id=context.task_id,
                agent_type="Planning",
                action="synthesize_results",
                payload={
                    "query": context.query,
                    "context": context.context_data,
                    "synthesis_type": "comprehensive",
                    "include_citations": True,
                },
            )

            # Send to planning agent for synthesis
            response = await self._send_to_agent("Planning", action)

            if response and response.status == "completed":
                # Store synthesis
                if response.result:
                    context.synthesis = response.result.get("synthesis", "")
                    context.context_data["synthesis"] = context.synthesis
                return True

            return False

        except Exception as e:
            self.logger.error(f"Synthesis stage failed: {e}")
            return False

    async def _send_to_agent(self, agent_type: str, action: ResearchAction) -> Optional[AgentResponse]:
        """
        Send action to specific agent type.

        Args:
            agent_type: Type of agent to send to
            action: Research action to send

        Returns:
            Optional[AgentResponse]: Response from agent
        """
        try:
            if not self.mcp_client:
                self.logger.error("MCP client not initialized")
                return None

            # Create a future to wait for the response
            response_future = asyncio.Future()
            self.pending_responses[action.task_id] = response_future

            # Send action via MCP client
            success = await self.mcp_client.send_task(action)

            if success:
                # Wait for response with timeout
                try:
                    response = await asyncio.wait_for(response_future, timeout=self.response_timeout)
                    return response
                except asyncio.TimeoutError:
                    self.logger.error(f"Timeout waiting for response from {agent_type} for task {action.task_id}")
                    return None
                finally:
                    # Clean up pending response
                    self.pending_responses.pop(action.task_id, None)

            return None

        except Exception as e:
            self.logger.error(f"Failed to send action to {agent_type}: {e}")
            # Clean up pending response on error
            self.pending_responses.pop(action.task_id, None)
            return None

    def _handle_agent_response(self, message_data: Dict[str, Any]) -> None:
        """
        Handle response from agent.

        Args:
            message_data: Message data from agent
        """
        try:
            # Create AgentResponse object from message data
            from ..mcp.protocols import AgentResponse

            response = AgentResponse(
                task_id=message_data.get("task_id", ""),
                context_id=message_data.get("context_id", ""),
                agent_type=message_data.get("agent_type", ""),
                status=message_data.get("status", ""),
                result=message_data.get("result"),
                error=message_data.get("error"),
            )

            task_id = response.task_id

            # Complete pending response future if exists
            if task_id in self.pending_responses:
                future = self.pending_responses[task_id]
                if not future.done():
                    future.set_result(response)
                    self.logger.debug(f"Completed pending response for task {task_id}")

            # Also handle context updates
            if task_id and task_id in self.active_contexts:
                context = self.active_contexts[task_id]
                self.logger.debug(f"Received response for task {task_id} in context")

        except Exception as e:
            self.logger.error(f"Error handling agent response: {e}")

    def _handle_agent_registration(self, message_data: Dict[str, Any]) -> None:
        """
        Handle agent registration.

        Args:
            message_data: Agent registration information
        """
        try:
            agent_id = message_data.get("agent_id")
            capabilities = message_data.get("capabilities", [])

            if agent_id:
                self.agent_capabilities[agent_id] = capabilities
                self.agent_availability[agent_id] = True
                self.logger.info(f"Agent {agent_id} registered with capabilities: {capabilities}")

        except Exception as e:
            self.logger.error(f"Error handling agent registration: {e}")

    def _handle_task_update(self, message_data: Dict[str, Any]) -> None:
        """
        Handle task status update.

        Args:
            message_data: Task update information
        """
        try:
            task_id = message_data.get("task_id")
            status = message_data.get("status")

            if task_id and task_id in self.active_contexts:
                context = self.active_contexts[task_id]
                # Update context based on status
                self.logger.debug(f"Task {task_id} status update: {status}")

        except Exception as e:
            self.logger.error(f"Error handling task update: {e}")

    async def _notify_progress(self, context: ResearchContext) -> None:
        """
        Notify progress callbacks about research progress.

        Args:
            context: Research context
        """
        try:
            progress_data = {
                "task_id": context.task_id,
                "stage": context.stage.value,
                "progress": len(context.completed_stages) / 5 * 100,  # 5 total stages
                "query": context.query,
                "updated_at": context.updated_at.isoformat(),
            }

            # Call global progress callbacks
            for callback in self.progress_callbacks:
                try:
                    await callback(progress_data)
                except Exception as e:
                    self.logger.error(f"Progress callback error: {e}")

            # Call task - specific progress callbacks
            task_callbacks = context.metadata.get("progress_callbacks", [])
            for callback in task_callbacks:
                try:
                    await callback(progress_data)
                except Exception as e:
                    self.logger.error(f"Task progress callback error: {e}")

        except Exception as e:
            self.logger.error(f"Error notifying progress: {e}")

    async def _notify_completion(self, context: ResearchContext, success: bool) -> None:
        """
        Notify completion callbacks about research completion.

        Args:
            context: Research context
            success: Whether task completed successfully
        """
        try:
            completion_data = {
                "task_id": context.task_id,
                "success": success,
                "query": context.query,
                "results": {
                    "search_results": context.search_results,
                    "reasoning_output": context.reasoning_output,
                    "execution_results": context.execution_results,
                    "synthesis": context.synthesis,
                },
                "completed_stages": [stage.value for stage in context.completed_stages],
                "failed_stages": [stage.value for stage in context.failed_stages],
                "duration": (context.updated_at - context.created_at).total_seconds(),
                "retry_count": context.retry_count,
            }

            for callback in self.completion_callbacks:
                try:
                    await callback(completion_data)
                except Exception as e:
                    self.logger.error(f"Completion callback error: {e}")

        except Exception as e:
            self.logger.error(f"Error notifying completion: {e}")

    async def _cleanup_context(self, task_id: str, delay: int = 0) -> None:
        """
        Clean up research context after delay.

        Args:
            task_id: Task ID to clean up
            delay: Delay in seconds before cleanup
        """
        try:
            if delay > 0:
                await asyncio.sleep(delay)

            if task_id in self.active_contexts:
                del self.active_contexts[task_id]
                self.logger.info(f"Cleaned up context for task {task_id}")

        except Exception as e:
            self.logger.error(f"Error cleaning up context: {e}")

    def register_progress_callback(self, callback: Callable) -> None:
        """
        Register callback for progress updates.

        Args:
            callback: Async callback function
        """
        self.progress_callbacks.append(callback)

    def register_completion_callback(self, callback: Callable) -> None:
        """
        Register callback for completion notifications.

        Args:
            callback: Async callback function
        """
        self.completion_callbacks.append(callback)

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of research task.

        Args:
            task_id: Task ID to check

        Returns:
            Optional[Dict[str, Any]]: Task status information
        """
        if task_id not in self.active_contexts:
            return None

        context = self.active_contexts[task_id]
        return {
            "task_id": task_id,
            "stage": context.stage.value,
            "progress": len(context.completed_stages) / 5 * 100,
            "query": context.query,
            "completed_stages": [stage.value for stage in context.completed_stages],
            "failed_stages": [stage.value for stage in context.failed_stages],
            "retry_count": context.retry_count,
            "created_at": context.created_at.isoformat(),
            "estimated_cost": context.estimated_cost,
            "actual_cost": context.actual_cost,
            "single_agent_mode": context.single_agent_mode,
            "updated_at": context.updated_at.isoformat(),
        }

    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """
        Get list of all active research tasks.

        Returns:
            List[Dict[str, Any]]: List of active task statuses
        """
        active_tasks = []
        for task_id in self.active_contexts.keys():
            status = self.get_task_status(task_id)
            if status:
                active_tasks.append(status)
        return active_tasks

    def get_task_context(self, task_id: str) -> Optional[ResearchContext]:
        """
        Get the research context for a task.

        Args:
            task_id: Task ID to get context for

        Returns:
            Optional[ResearchContext]: Research context if found
        """
        return self.active_contexts.get(task_id)

    def calculate_task_progress(self, task_id: str) -> float:
        """
        Calculate progress percentage for a task.

        Args:
            task_id: Task ID to calculate progress for

        Returns:
            float: Progress percentage (0.0 to 100.0)
        """
        context = self.active_contexts.get(task_id)
        if not context:
            return 0.0

        total_stages = 5  # planning, literature review, reasoning, execution, synthesis
        completed_stages = len(context.completed_stages)

        if context.stage == ResearchStage.COMPLETE:
            return 100.0
        elif context.stage == ResearchStage.FAILED:
            return (completed_stages / total_stages) * 100.0
        else:
            # Add partial progress for current stage
            return ((completed_stages + 0.5) / total_stages) * 100.0

    def add_progress_callback(self, task_id: str, callback: Callable) -> None:
        """
        Add a progress callback for a specific task.

        Args:
            task_id: Task ID to add callback for
            callback: Callback function to add
        """
        context = self.active_contexts.get(task_id)
        if context:
            if "progress_callbacks" not in context.metadata:
                context.metadata["progress_callbacks"] = []
            context.metadata["progress_callbacks"].append(callback)

    def remove_progress_callback(self, task_id: str) -> None:
        """
        Remove progress callbacks for a specific task.

        Args:
            task_id: Task ID to remove callbacks for
        """
        context = self.active_contexts.get(task_id)
        if context and "progress_callbacks" in context.metadata:
            context.metadata["progress_callbacks"] = []

    async def cleanup(self) -> None:
        """Clean up the research manager (alias for shutdown)."""
        await self.shutdown()

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel an active research task.

        Args:
            task_id: Task ID to cancel

        Returns:
            bool: True if successfully cancelled
        """
        try:
            if task_id in self.active_contexts:
                context = self.active_contexts[task_id]
                context.stage = ResearchStage.FAILED
                context.updated_at = datetime.now()

                # Update database to mark task as cancelled
                try:
                    task_data = {
                        "id": task_id,
                        "status": "cancelled",
                        "stage": "failed",
                        "updated_at": context.updated_at.isoformat(),
                    }
                    self.db_manager.update_research_task(task_data)
                    self.logger.debug(f"Updated database entry for cancelled task {task_id}")
                except Exception as e:
                    self.logger.error(f"Failed to update database for cancelled task {task_id}: {e}")

                await self._notify_completion(context, success=False)
                del self.active_contexts[task_id]
                self.logger.info(f"Cancelled task {task_id}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Error cancelling task: {e}")
            return False

    async def shutdown(self) -> None:
        """Shutdown the Research Manager."""
        try:
            # Cancel all active tasks
            for task_id in list(self.active_contexts.keys()):
                await self.cancel_task(task_id)

            # Close MCP client
            if self.mcp_client:
                await self.mcp_client.disconnect()

            self.logger.info("Research Manager shutdown complete")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

    async def _create_research_plan_and_tasks(self, context: ResearchContext) -> Optional[str]:
        """
        Create a research plan and individual task entries for each stage.

        Args:
            context: Research context containing task information

        Returns:
            Optional[str]: Plan ID if successful, None otherwise
        """
        try:
            # First, ensure we have a topic for this research
            topic_id = await self._get_or_create_research_topic(context)
            if not topic_id:
                self.logger.error(f"Failed to create or get research topic for task {context.task_id}")
                return None

            # Create the research plan
            plan_id = f"plan_{context.task_id}"
            plan_data = {
                "id": plan_id,
                "topic_id": topic_id,
                "name": f"Research Plan: {context.query[:50]}{'...' if len(context.query) > 50 else ''}",
                "description": f"Research plan for: {context.query}",
                "plan_type": "single_agent" if context.single_agent_mode else "comprehensive",
                "status": "draft",
                "plan_approved": False,
                "estimated_cost": context.estimated_cost,
                "actual_cost": context.actual_cost,
                "plan_structure": json.dumps(
                    {
                        "query": context.query,
                        "single_agent_mode": context.single_agent_mode,
                        "stages": self._get_stage_list(context.single_agent_mode),
                    }
                ),
                "metadata": json.dumps({"task_id": context.task_id, "user_id": context.user_id, **context.metadata}),
            }

            # Create the plan in database
            created_plan = self.db_manager.create_research_plan(plan_data)
            if not created_plan:
                self.logger.error(f"Failed to create research plan for task {context.task_id}")
                return None

            # Create main research task entry for web server compatibility
            main_task_data = {
                "id": context.task_id,
                "project_id": context.project_id or "default_project",
                "plan_id": plan_id,
                "query": context.query,
                "name": f"Research: {context.query[:50]}{'...' if len(context.query) > 50 else ''}",
                "status": "running",
                "stage": "planning",
                "progress": 0.0,
                "estimated_cost": context.estimated_cost,
                "actual_cost": context.actual_cost,
                "cost_approved": context.cost_approved,
                "single_agent_mode": context.single_agent_mode,
                "research_mode": "comprehensive",  # Default value
                "max_results": 10,  # Default value
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "metadata": json.dumps(
                    {"task_id": context.task_id, "user_id": context.user_id, "is_main_task": True, **context.metadata}
                ),
                "task_type": "research",
                "task_order": 0,
            }

            main_task_created = self.db_manager.create_research_task(main_task_data)
            if main_task_created:
                self.logger.info(f"Created main research task entry: {context.task_id}")
            else:
                self.logger.warning(f"Failed to create main research task entry: {context.task_id}")

            # Note: Individual stage tasks will be created when each stage starts executing
            # This avoids creating tasks that may never execute due to failures or single - agent mode

            self.logger.info(f"Successfully created research plan {plan_id} and main task entry")
            return plan_id

        except Exception as e:
            self.logger.error(f"Error creating research plan and tasks: {e}")
            return None

    async def _get_or_create_research_topic(self, context: ResearchContext) -> Optional[str]:
        """
        Get or create a research topic for the given context.

        Args:
            context: Research context

        Returns:
            Optional[str]: Topic ID if successful
        """
        try:
            # Check if an existing topic_id is provided in metadata
            existing_topic_id = context.metadata.get("topic_id")
            if existing_topic_id:
                # Verify the topic exists
                existing_topic = self.db_manager.get_research_topic(existing_topic_id)
                if existing_topic:
                    self.logger.info(f"Using existing research topic {existing_topic_id}")
                    return existing_topic_id
                else:
                    self.logger.warning(f"Specified topic {existing_topic_id} not found, creating new topic")

            # Generate a topic ID based on the task or create a new one
            if context.task_id:
                topic_id = f"topic_{context.task_id}"
            else:
                # For web API requests without task_id, generate timestamp - based ID
                from src.utils.id_utils import generate_timestamped_id

                topic_id = f"topic_{context.task_id}" if context.task_id else generate_timestamped_id("topic")

            # Check if topic already exists
            existing_topic = self.db_manager.get_research_topic(topic_id)
            if existing_topic:
                return topic_id

            # Create new topic
            topic_data = {
                "id": topic_id,
                "project_id": context.project_id or "default_project",
                "name": f"Research Topic: {context.query[:60]}{'...' if len(context.query) > 60 else ''}",
                "description": f"Research topic for task {context.task_id}",
                "status": "active",
                "metadata": json.dumps({"created_from_task": context.task_id}),
            }

            created_topic = self.db_manager.create_research_topic(topic_data)
            if created_topic:
                self.logger.info(f"Created research topic {topic_id}")
                return topic_id
            else:
                self.logger.error(f"Failed to create research topic {topic_id}")
                return None

        except Exception as e:
            self.logger.error(f"Error getting or creating research topic: {e}")
            return None

    def _get_stage_list(self, single_agent_mode: bool) -> List[str]:
        """
        Get the list of stages for the research process.

        Args:
            single_agent_mode: Whether running in single agent mode

        Returns:
            List[str]: List of stage names
        """
        if single_agent_mode:
            return ["planning", "literature_review"]
        else:
            return ["planning", "literature_review", "reasoning", "execution", "synthesis"]

    def _create_stage_task_in_database(self, context: ResearchContext) -> bool:
        """
        Create a database entry for the current stage task.

        Args:
            context: Research context containing task information

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            plan_id = context.metadata.get("plan_id")
            if not plan_id:
                self.logger.warning(f"No plan_id found for task {context.task_id}, cannot create stage task")
                return False

            # Check if stage task already exists to prevent duplicates
            stage_task_id = f"{context.task_id}_{context.stage.value}"
            existing_task = self.db_manager.get_research_task(stage_task_id)
            if existing_task:
                self.logger.debug(f"Stage task {stage_task_id} already exists, skipping creation")
                return True

            # Calculate stage order
            all_stages = self._get_stage_list(context.single_agent_mode)
            try:
                stage_order = all_stages.index(context.stage.value) + 1
            except ValueError:
                stage_order = 1

            # Create stage task entry
            task_data = {
                "id": stage_task_id,
                "project_id": context.project_id,
                "plan_id": plan_id,
                "query": context.query,
                "name": f"{context.stage.value.title()}: {context.query[:40]}{'...' if len(context.query) > 40 else ''}",
                "status": "running",
                "stage": context.stage.value,
                "created_at": context.updated_at.isoformat(),
                "updated_at": context.updated_at.isoformat(),
                "estimated_cost": context.estimated_cost / len(all_stages),  # Distribute cost across stages
                "actual_cost": 0.0,
                "cost_approved": context.cost_approved,
                "single_agent_mode": context.single_agent_mode,
                "research_mode": "single_agent" if context.single_agent_mode else "comprehensive",
                "max_results": 10,
                "progress": 0.0,
                "search_results": json.dumps([]),
                "reasoning_output": None,
                "execution_results": json.dumps([]),
                "synthesis": None,
                "metadata": json.dumps(
                    {
                        "main_task_id": context.task_id,
                        "user_id": context.user_id,
                        "stage_order": stage_order,
                        "total_stages": len(all_stages),
                        **context.metadata,
                    }
                ),
                "task_type": context.stage.value,
                "task_order": stage_order,
            }

            created_task = self.db_manager.create_research_task(task_data)
            if created_task:
                self.logger.info(f"Created database entry for {context.stage.value} stage task: {stage_task_id}")
                return True
            else:
                self.logger.warning(
                    f"Failed to create database entry for {context.stage.value} stage task: {stage_task_id}"
                )
                return False

        except Exception as e:
            self.logger.error(f"Error creating stage task in database: {e}")
            return False

    def _update_task_in_database(self, context: ResearchContext) -> None:
        """
        Update the specific stage task status in the database.

        Args:
            context: Research context to update in database
        """
        try:
            # Calculate progress percentage
            if context.single_agent_mode:
                total_stages = 2  # planning, literature review only
            else:
                total_stages = 5  # planning, literature review, reasoning, execution, synthesis

            progress = (len(context.completed_stages) / total_stages) * 100.0

            # Update the specific stage task
            stage_task_id = f"{context.task_id}_{context.stage.value}"

            # Check if stage task exists first
            existing_task = self.db_manager.get_research_task(stage_task_id)
            if not existing_task:
                self.logger.debug(f"Stage task {stage_task_id} does not exist yet, skipping update")
                return

            # Determine task status based on context
            if context.stage in context.completed_stages:
                task_status = "completed"
            elif context.stage in context.failed_stages:
                task_status = "failed"
            else:
                task_status = "running"

            # Prepare stage - specific task data for update
            stage_task_data = {
                "id": stage_task_id,
                "status": task_status,
                "stage": context.stage.value,
                "updated_at": context.updated_at.isoformat(),
                "progress": (
                    100.0 if context.stage in context.completed_stages else (50.0 if task_status == "running" else 0.0)
                ),
                "metadata": json.dumps(
                    {
                        "main_task_id": context.task_id,
                        "user_id": context.user_id,
                        "retry_count": context.retry_count,
                        "completed_stages": [stage.value for stage in context.completed_stages],
                        "failed_stages": [stage.value for stage in context.failed_stages],
                        **context.metadata,
                    }
                ),
            }

            # Add stage - specific results
            if context.stage == ResearchStage.LITERATURE_REVIEW:
                stage_task_data["search_results"] = json.dumps(context.search_results)
            elif context.stage == ResearchStage.REASONING:
                stage_task_data["reasoning_output"] = context.reasoning_output
            elif context.stage == ResearchStage.EXECUTION:
                stage_task_data["execution_results"] = json.dumps(context.execution_results)
            elif context.stage == ResearchStage.SYNTHESIS:
                stage_task_data["synthesis"] = context.synthesis

            # Update the stage task in database
            updated = self.db_manager.update_research_task(stage_task_data)
            if updated:
                self.logger.debug(f"Updated database entry for stage task {stage_task_id}")
            else:
                self.logger.warning(f"Failed to update database entry for stage task {stage_task_id}")

            # Also update the research plan with overall progress
            plan_id = context.metadata.get("plan_id")
            if plan_id:
                plan_update_data = {
                    "status": "approved" if context.stage != ResearchStage.PLANNING else "draft",
                    "plan_approved": context.stage != ResearchStage.PLANNING,
                    "updated_at": context.updated_at.isoformat(),
                    "actual_cost": context.actual_cost,
                    "metadata": json.dumps(
                        {
                            "main_task_id": context.task_id,
                            "overall_progress": progress,
                            "current_stage": context.stage.value,
                            "completed_stages": [stage.value for stage in context.completed_stages],
                            "failed_stages": [stage.value for stage in context.failed_stages],
                        }
                    ),
                }

                plan_updated = self.db_manager.update_research_plan(plan_id, plan_update_data)
                if plan_updated:
                    self.logger.debug(f"Updated research plan {plan_id} progress")
                else:
                    self.logger.warning(f"Failed to update research plan {plan_id}")

            # Update the main research task entry for web server compatibility
            main_task_update = {
                "id": context.task_id,
                "status": (
                    "completed"
                    if context.stage == ResearchStage.SYNTHESIS and context.stage in context.completed_stages
                    else "running"
                ),
                "stage": context.stage.value,
                "progress": progress,
                "actual_cost": context.actual_cost,
                "updated_at": context.updated_at.isoformat(),
                # Include all results for completed task
                "search_results": json.dumps(context.search_results) if context.search_results else None,
                "reasoning_output": context.reasoning_output if context.reasoning_output else None,
                "execution_results": json.dumps(context.execution_results) if context.execution_results else None,
                "synthesis": context.synthesis if context.synthesis else None,
                "metadata": json.dumps(
                    {
                        "main_task_id": context.task_id,
                        "user_id": context.user_id,
                        "overall_progress": progress,
                        "current_stage": context.stage.value,
                        "completed_stages": [stage.value for stage in context.completed_stages],
                        "failed_stages": [stage.value for stage in context.failed_stages],
                        "is_main_task": True,
                        **context.metadata,
                    }
                ),
            }

            main_task_updated = self.db_manager.update_research_task(main_task_update)
            if main_task_updated:
                self.logger.debug(f"Updated main research task {context.task_id}")
            else:
                self.logger.warning(f"Failed to update main research task {context.task_id}")

        except Exception as e:
            self.logger.error(f"Error updating task {context.task_id} in database: {e}")

    # Cost Control Methods

    def get_cost_summary(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get cost usage summary for a session or all sessions.

        Args:
            session_id: Optional session ID to filter by

        Returns:
            Dict[str, Any]: Cost usage summary
        """
        return self.cost_estimator.get_usage_summary(session_id)

    async def estimate_query_cost_async(self, query: str, single_agent_mode: bool = False) -> Dict[str, Any]:
        """
        Estimate cost for a query without starting the task (async version).

        Args:
            query: Research query to estimate
            single_agent_mode: Whether to use single agent mode

        Returns:
            Dict[str, Any]: Cost estimation details
        """
        options = {"single_agent_mode": single_agent_mode}
        cost_info, _, _ = await self._estimate_task_cost(
            query=query, task_id="estimate_only", options=options  # Dummy task ID for estimation
        )

        # Remove task - specific fields for estimation - only response
        cost_info.pop("should_proceed", None)
        cost_info.pop("cost_reason", None)
        cost_info["single_agent_mode"] = single_agent_mode

        return cost_info

    def estimate_query_cost(self, query: str, single_agent_mode: bool = False) -> Dict[str, Any]:
        """
        Estimate cost for a query without starting the task (synchronous version).

        Args:
            query: Research query to estimate
            single_agent_mode: Whether to use single agent mode

        Returns:
            Dict[str, Any]: Cost estimation details
        """
        agents_to_use = ["Literature"] if single_agent_mode else ["Literature", "Planning", "Executor", "Memory"]
        parallel_execution = not single_agent_mode

        estimate = self.cost_estimator.estimate_task_cost(
            query=query, agents=agents_to_use, parallel_execution=parallel_execution
        )

        recommendations = self.cost_estimator.get_cost_recommendations(estimate)

        return {
            "estimate": {
                "tokens": estimate.estimated_tokens,
                "cost_usd": estimate.estimated_cost_usd,
                "complexity": estimate.task_complexity.value,
                "agent_count": estimate.agent_count,
                "confidence": estimate.confidence,
                "reasoning": estimate.reasoning,
            },
            "recommendations": recommendations,
            "single_agent_mode": single_agent_mode,
        }

    def get_cost_thresholds(self) -> Dict[str, float]:
        """
        Get current cost control thresholds.

        Returns:
            Dict[str, float]: Cost thresholds
        """
        return self.cost_estimator.cost_thresholds.copy()

    def update_cost_thresholds(self, thresholds: Dict[str, float]) -> None:
        """
        Update cost control thresholds.

        Args:
            thresholds: New threshold values
        """
        for key, value in thresholds.items():
            if key in self.cost_estimator.cost_thresholds:
                self.cost_estimator.cost_thresholds[key] = value
                self.logger.info(f"Updated cost threshold {key} to ${value}")

    def get_task_cost_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed cost status for a specific task.

        Args:
            task_id: Task ID to get cost status for

        Returns:
            Optional[Dict[str, Any]]: Cost status details
        """
        if task_id not in self.active_contexts:
            return None

        context = self.active_contexts[task_id]

        # Get current usage if tracking is active
        current_usage = None
        if task_id in self.cost_estimator.active_sessions:
            usage = self.cost_estimator.active_sessions[task_id]
            current_usage = {
                "tokens_used": usage.tokens_used,
                "cost_usd": usage.cost_usd,
                "provider_breakdown": usage.provider_breakdown,
                "agent_breakdown": usage.agent_breakdown,
                "duration_seconds": (datetime.now() - usage.start_time).total_seconds(),
            }

        return {
            "task_id": task_id,
            "estimated_cost": context.estimated_cost,
            "actual_cost": context.actual_cost,
            "cost_approved": context.cost_approved,
            "single_agent_mode": context.single_agent_mode,
            "current_usage": current_usage,
            "stage": context.stage.value,
        }

    # Phase 4: Debug UI Methods

    async def get_latest_plan(self, context_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get the latest RM AI plan for debugging.

        Args:
            context_id: Optional context ID to filter by

        Returns:
            Optional[Dict[str, Any]]: Latest plan data
        """
        # In a full implementation, this would query a plans database
        # For now, only return data for active contexts

        if context_id and context_id in self.active_contexts:
            context = self.active_contexts[context_id]
            return {
                "plan_id": f"plan_{context_id}_{generate_timestamped_id('temp')}",
                "context_id": context_id,
                "prompt": f"Research plan for: {context.query}",
                "raw_response": "RM AI response for active research context",
                "parsed_tasks": [
                    {"task_id": "task_1", "agent": "literature", "action": "search_web"},
                    {"task_id": "task_2", "agent": "planning", "action": "analyze_results"},
                ],
                "created_at": datetime.now().isoformat(),
                "execution_status": context.stage.value,
                "modifications": [],
            }

        # Return None when no plans are available
        return None

    async def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific RM AI plan by ID.

        Args:
            plan_id: Plan ID to retrieve

        Returns:
            Optional[Dict[str, Any]]: Plan data
        """
        # In a full implementation, this would query a plans database
        # For now, return None since we don't have persistent plan storage
        return None

    async def modify_plan(self, plan_id: str, modifications: Dict[str, Any]) -> bool:
        """
        Modify a specific RM AI plan.

        Args:
            plan_id: Plan ID to modify
            modifications: Modifications to apply

        Returns:
            bool: True if successful
        """
        self.logger.info(f"Plan {plan_id} modified with: {modifications}")

        # In a full implementation, this would:
        # 1. Update the plan in the database
        # 2. Apply modifications to active tasks if needed
        # 3. Notify relevant components of changes

        return True

    async def list_plans(self, context_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List RM AI plans with optional context filtering.

        Args:
            context_id: Optional context ID to filter by
            limit: Maximum number of plans to return

        Returns:
            List[Dict[str, Any]]: List of plan summaries
        """
        # In a full implementation, this would query a plans database
        plans = []

        # Include active contexts as plans if they exist
        for ctx_id, context in self.active_contexts.items():
            if context_id is None or ctx_id == context_id:
                plans.append(
                    {
                        "plan_id": f"plan_{ctx_id}",
                        "context_id": ctx_id,
                        "prompt": f"Research plan for: {getattr(context, 'query', 'Active research context')}",
                        "created_at": context.created_at.isoformat(),
                        "execution_status": context.stage.value,
                        "parsed_tasks": [
                            {"task_id": "task_1", "agent": "literature"},
                            {"task_id": "task_2", "agent": "planning"},
                        ],
                        "modifications": [],
                    }
                )

        # Return only real active contexts, no mock data
        return plans[:limit]

    async def _wait_for_plan_approval(self, task_id: str, timeout_minutes: int = 60) -> bool:
        """
        Wait for plan approval for a specific task.

        This method polls the database to check if the research plan has been approved.
        It will wait for up to the specified timeout period.

        Args:
            task_id: The task ID to check for approval
            timeout_minutes: Maximum time to wait in minutes

        Returns:
            bool: True if approved, False if rejected or timeout
        """
        timeout_seconds = timeout_minutes * 60
        check_interval = 5  # Check every 5 seconds
        elapsed_time = 0

        self.logger.info(f"Waiting for plan approval for task {task_id} (timeout: {timeout_minutes} minutes)")

        while elapsed_time < timeout_seconds:
            try:
                # Get the plan ID from context
                context = self.active_contexts.get(task_id)
                plan_id = context.metadata.get("plan_id") if context else None

                if plan_id:
                    # Check the research plan's approval status
                    plan = self.db_manager.get_research_plan(plan_id)
                    if plan and plan.get("plan_approved"):
                        self.logger.info(f"Research plan {plan_id} approved for task {task_id}")

                        # Update the planning stage task status
                        planning_task_id = f"{task_id}_planning"
                        planning_task_data = {
                            "id": planning_task_id,
                            "status": "completed",
                            "updated_at": datetime.now().isoformat(),
                        }
                        self.db_manager.update_research_task(planning_task_data)

                        return True

                    # Check if plan was cancelled or failed
                    if plan and plan.get("status") in ["cancelled", "failed"]:
                        self.logger.info(f"Plan {plan_id} was cancelled or failed while waiting for approval")
                        return False
                else:
                    # Fallback: check the individual planning task
                    planning_task_id = f"{task_id}_planning"
                    planning_task = self.db_manager.get_research_task(planning_task_id)
                    if planning_task and planning_task.get("status") == "completed":
                        self.logger.info(f"Planning task {planning_task_id} completed for task {task_id}")
                        return True

                # Wait before checking again
                await asyncio.sleep(check_interval)
                elapsed_time += check_interval

            except Exception as e:
                self.logger.error(f"Error checking plan approval for task {task_id}: {e}")
                await asyncio.sleep(check_interval)
                elapsed_time += check_interval

        # Timeout reached
        self.logger.warning(f"Timeout waiting for plan approval for task {task_id}")

        # Update task status to indicate timeout
        try:
            task = self.db_manager.get_research_task(task_id)
            if task:
                task["status"] = "waiting_approval_timeout"
                self.db_manager.update_research_task(task)
        except Exception as e:
            self.logger.error(f"Failed to update task status after approval timeout: {e}")

        return False
