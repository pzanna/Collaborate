"""
Research Manager Service for Eunice Research Platform.

This module provides a containerized Research Manager that coordinates:
- Multi-agent research task orchestration
- Research workflow management
- Cost estimation and approval
- Task delegation and monitoring
- Progress tracking and reporting
"""

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

import uvicorn
import websockets
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ResearchStage(Enum):
    """Research task stages."""
    PLANNING = "planning"
    LITERATURE_REVIEW = "literature_review"
    REASONING = "reasoning"
    EXECUTION = "execution"
    SYNTHESIS = "synthesis"
    SYSTEMATIC_REVIEW = "systematic_review"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class ResearchContext:
    """Research context for tracking task state."""
    task_id: str
    query: str
    user_id: str
    project_id: Optional[str] = None
    stage: ResearchStage = ResearchStage.PLANNING
    estimated_cost: float = 0.0
    actual_cost: float = 0.0
    cost_approved: bool = False
    single_agent_mode: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_stages: List[ResearchStage] = field(default_factory=list)
    failed_stages: List[ResearchStage] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 2
    context_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Results storage
    search_results: List[Dict[str, Any]] = field(default_factory=list)
    reasoning_output: str = ""
    execution_results: List[Dict[str, Any]] = field(default_factory=list)
    synthesis: str = ""


@dataclass
class ResearchAction:
    """Research action for agent communication."""
    task_id: str
    context_id: str
    agent_type: str
    action: str
    payload: Dict[str, Any]
    priority: str = "normal"
    parallelism: int = 1
    timeout: int = 300
    retry_count: int = 0
    dependencies: List[str] = field(default_factory=list)


@dataclass
class AgentResponse:
    """Response from an agent."""
    task_id: str
    context_id: str
    agent_type: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ResearchManagerService:
    """
    Research Manager Service for coordinating multi-agent research tasks.
    
    Handles research workflow orchestration, cost estimation, task delegation,
    and progress monitoring via MCP protocol.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Research Manager Service."""
        self.config = config
        self.agent_id = "research_manager"
        self.agent_type = "research_manager"
        
        # Service configuration
        self.service_host = config.get("service_host", "0.0.0.0")
        self.service_port = config.get("service_port", 8002)
        self.mcp_server_url = config.get("mcp_server_url", "ws://mcp-server:9000")
        
        # Research configuration
        self.max_concurrent_tasks = config.get("max_concurrent_tasks", 5)
        self.task_timeout = config.get("task_timeout", 600)
        self.response_timeout = config.get("response_timeout", 300)
        
        # MCP connection
        self.websocket = None
        self.mcp_connected = False
        
        # Active research contexts
        self.active_contexts: Dict[str, ResearchContext] = {}
        
        # Agent capabilities and availability
        self.agent_capabilities: Dict[str, List[str]] = {}
        self.agent_availability: Dict[str, bool] = {}
        
        # Response tracking for agent communications
        self.pending_responses: Dict[str, asyncio.Future] = {}
        
        # Callbacks for UI updates
        self.progress_callbacks: List[Callable] = []
        self.completion_callbacks: List[Callable] = []
        
        # Task processing queue
        self.task_queue = asyncio.Queue()
        
        logger.info(f"Research Manager Service initialized on port {self.service_port}")
    
    async def start(self):
        """Start the Research Manager Service."""
        try:
            # Connect to MCP server
            await self._connect_to_mcp_server()
            
            # Start task processing
            asyncio.create_task(self._process_task_queue())
            
            logger.info("Research Manager Service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Research Manager Service: {e}")
            raise
    
    async def stop(self):
        """Stop the Research Manager Service."""
        try:
            # Cancel all active tasks
            for task_id in list(self.active_contexts.keys()):
                await self.cancel_task(task_id)
            
            # Close MCP connection
            if self.websocket:
                await self.websocket.close()
            
            logger.info("Research Manager Service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping Research Manager Service: {e}")
    
    async def _connect_to_mcp_server(self):
        """Connect to MCP server."""
        max_retries = 10
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Connecting to MCP server at {self.mcp_server_url} (attempt {attempt + 1})")
                
                self.websocket = await websockets.connect(
                    self.mcp_server_url,
                    ping_interval=30,
                    ping_timeout=10
                )
                
                # Register with MCP server
                await self._register_with_mcp_server()
                
                # Start message handler
                asyncio.create_task(self._handle_mcp_messages())
                
                self.mcp_connected = True
                logger.info("Successfully connected to MCP server")
                return
                
            except Exception as e:
                logger.warning(f"Failed to connect to MCP server (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("Failed to connect to MCP server after all retries")
                    raise
    
    async def _register_with_mcp_server(self):
        """Register this agent with the MCP server."""
        capabilities = [
            "start_research_task",
            "cancel_task",
            "get_task_status",
            "orchestrate_research",
            "estimate_task_cost",
            "coordinate_agents",
            "monitor_progress"
        ]
        
        registration_message = {
            "type": "register",
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": capabilities,
            "service_info": {
                "host": self.service_host,
                "port": self.service_port,
                "health_endpoint": f"http://{self.service_host}:{self.service_port}/health"
            }
        }
        
        await self.websocket.send(json.dumps(registration_message))
        logger.info(f"Registered with MCP server: {len(capabilities)} capabilities")
    
    async def _handle_mcp_messages(self):
        """Handle incoming MCP messages."""
        try:
            while self.websocket:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                if data.get("type") == "task":
                    await self.task_queue.put(data)
                elif data.get("type") == "agent_response":
                    await self._handle_agent_response(data)
                elif data.get("type") == "ping":
                    await self.websocket.send(json.dumps({"type": "pong"}))
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("MCP server connection closed")
            self.mcp_connected = False
        except Exception as e:
            logger.error(f"Error handling MCP messages: {e}")
            self.mcp_connected = False
    
    async def _process_task_queue(self):
        """Process tasks from the MCP queue."""
        while True:
            try:
                # Get task from queue
                task_data = await self.task_queue.get()
                
                # Process the task
                result = await self._process_research_manager_task(task_data)
                
                # Send result back to MCP server
                if self.websocket and self.mcp_connected:
                    response = {
                        "type": "task_result",
                        "task_id": task_data.get("task_id"),
                        "agent_id": self.agent_id,
                        "result": result
                    }
                    await self.websocket.send(json.dumps(response))
                
                # Mark task as done
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing task: {e}")
                await asyncio.sleep(1)
    
    async def _process_research_manager_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a research manager task."""
        try:
            action = task_data.get("action", "")
            payload = task_data.get("payload", {})
            
            # Route to appropriate handler
            if action == "start_research_task":
                return await self._handle_start_research_task(payload)
            elif action == "cancel_task":
                return await self._handle_cancel_task(payload)
            elif action == "get_task_status":
                return await self._handle_get_task_status(payload)
            elif action == "estimate_task_cost":
                return await self._handle_estimate_task_cost(payload)
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            logger.error(f"Error processing research manager task: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_start_research_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle start research task request."""
        try:
            query = payload.get("query", "")
            user_id = payload.get("user_id", "")
            project_id = payload.get("project_id")
            options = payload.get("options", {})
            
            if not query or not user_id:
                return {"success": False, "error": "Query and user_id are required"}
            
            # Start research task
            task_id, cost_info = await self.start_research_task(query, user_id, project_id, options)
            
            return {
                "success": True,
                "task_id": task_id,
                "cost_info": cost_info
            }
            
        except Exception as e:
            logger.error(f"Failed to handle start research task: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_cancel_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle cancel task request."""
        try:
            task_id = payload.get("task_id", "")
            
            if not task_id:
                return {"success": False, "error": "Task ID is required"}
            
            success = await self.cancel_task(task_id)
            
            return {"success": success}
            
        except Exception as e:
            logger.error(f"Failed to handle cancel task: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_get_task_status(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get task status request."""
        try:
            task_id = payload.get("task_id", "")
            
            if not task_id:
                return {"success": False, "error": "Task ID is required"}
            
            status = self.get_task_status(task_id)
            
            return {
                "success": True,
                "status": status
            }
            
        except Exception as e:
            logger.error(f"Failed to handle get task status: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_estimate_task_cost(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle estimate task cost request."""
        try:
            query = payload.get("query", "")
            task_id = payload.get("task_id", str(uuid.uuid4()))
            options = payload.get("options", {})
            
            if not query:
                return {"success": False, "error": "Query is required"}
            
            cost_info, should_proceed, single_agent_mode = await self._estimate_task_cost(query, task_id, options)
            
            return {
                "success": True,
                "cost_info": cost_info,
                "should_proceed": should_proceed,
                "single_agent_mode": single_agent_mode
            }
            
        except Exception as e:
            logger.error(f"Failed to handle estimate task cost: {e}")
            return {"success": False, "error": str(e)}
    
    async def start_research_task(
        self,
        query: str,
        user_id: str,
        project_id: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> tuple[str, Dict[str, Any]]:
        """
        Start a new research task with cost estimation and control.

        Args:
            query: Research query to process
            user_id: ID of the user making the request
            project_id: ID of the project (optional)
            options: Optional task configuration

        Returns:
            tuple: (task_id, cost_info)
        """
        task_id = str(uuid.uuid4())

        try:
            # Estimate cost for the research task
            cost_info, should_proceed, single_agent_mode = await self._estimate_task_cost(query, task_id, options)

            # Create research context
            context = ResearchContext(
                task_id=task_id,
                query=query,
                user_id=user_id,
                project_id=project_id or (options.get("project_id") if options else None),
                estimated_cost=cost_info["estimate"]["estimated_cost_usd"],
                single_agent_mode=single_agent_mode,
            )

            # Apply options if provided
            if options:
                context.max_retries = options.get("max_retries", context.max_retries)
                context.metadata.update(options.get("metadata", {}))
                context.cost_approved = options.get("cost_override", False)

            # Only proceed if cost is approved or automatically acceptable
            if should_proceed or context.cost_approved:
                context.cost_approved = True

                # Store context
                self.active_contexts[task_id] = context

                # Start task orchestration
                asyncio.create_task(self._orchestrate_research_task(context))

                logger.info(
                    f"Started research task {task_id} for query: {query}, "
                    f"estimated cost: ${cost_info['estimate']['estimated_cost_usd']:.4f}"
                )
            else:
                # Task not approved due to cost
                cost_info["task_started"] = False
                logger.warning(f"Research task blocked due to cost: {cost_info['cost_reason']}")

            cost_info["task_started"] = should_proceed or context.cost_approved
            return task_id, cost_info

        except Exception as e:
            logger.error(f"Failed to start research task: {e}")
            raise
    
    async def _estimate_task_cost(
        self, query: str, task_id: str, options: Optional[Dict[str, Any]] = None
    ) -> tuple[Dict[str, Any], bool, bool]:
        """
        Estimate cost for a research task with approval logic.

        Args:
            query: Research query to process
            task_id: ID of the task for cost tracking
            options: Optional task configuration

        Returns:
            tuple: (cost_info, should_proceed, single_agent_mode)
        """
        # Determine agent configuration
        single_agent_mode = options.get("single_agent_mode", False) if options else False

        if single_agent_mode:
            agents_to_use = ["literature"]  # Use only literature in single agent mode
            parallel_execution = False
            estimated_tokens = 1000
            estimated_cost = 0.02
        else:
            agents_to_use = ["literature", "planning", "executor", "memory"]
            parallel_execution = True
            estimated_tokens = 5000
            estimated_cost = 0.10

        # Simple cost estimation logic
        # In a real implementation, this would be more sophisticated
        cost_estimate = {
            "estimated_tokens": estimated_tokens,
            "estimated_cost_usd": estimated_cost,
            "task_complexity": "medium",
            "agent_count": len(agents_to_use),
            "confidence": 0.8,
            "reasoning": f"Estimated for {len(agents_to_use)} agents with {'parallel' if parallel_execution else 'sequential'} execution"
        }

        # Auto-approve tasks under $0.50
        should_proceed = estimated_cost < 0.50
        cost_reason = "Auto-approved" if should_proceed else "Requires approval"

        # Prepare cost information
        cost_info = {
            "estimate": cost_estimate,
            "should_proceed": should_proceed,
            "cost_reason": cost_reason,
            "recommendations": ["Consider single-agent mode for cost optimization"] if not single_agent_mode else []
        }

        return cost_info, should_proceed, single_agent_mode
    
    async def _orchestrate_research_task(self, context: ResearchContext) -> None:
        """
        Orchestrate the complete research task workflow.

        Args:
            context: Research context to process
        """
        try:
            # Execute research stages
            if context.single_agent_mode:
                # Single agent mode - only use literature
                stages = [
                    (ResearchStage.PLANNING, self._execute_planning_stage),
                    (ResearchStage.LITERATURE_REVIEW, self._execute_literature_review_stage),
                    (ResearchStage.SYNTHESIS, self._execute_synthesis_stage),
                ]
                logger.info(f"Running task {context.task_id} in single-agent mode (cost-optimized)")
            else:
                # Full multi-agent mode
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

                    # Notify progress
                    await self._notify_progress(context)

                    # Execute stage
                    success = await executor(context)

                    if success:
                        context.completed_stages.append(stage)
                        context.updated_at = datetime.now()
                        logger.info(f"Completed stage {stage.value} for task {context.task_id}")
                    else:
                        context.failed_stages.append(stage)
                        context.updated_at = datetime.now()
                        logger.error(f"Failed stage {stage.value} for task {context.task_id}")

                        # Retry logic
                        if context.retry_count < context.max_retries:
                            context.retry_count += 1
                            context.failed_stages.remove(stage)
                            logger.info(f"Retrying stage {stage.value} for task {context.task_id} (attempt {context.retry_count})")
                            success = await executor(context)
                            if success:
                                context.completed_stages.append(stage)
                            else:
                                context.failed_stages.append(stage)
                                break
                        else:
                            break

                except Exception as e:
                    logger.error(f"Error in stage {stage.value} for task {context.task_id}: {e}")
                    context.failed_stages.append(stage)
                    break

            # Determine final status
            if len(context.completed_stages) == len(stages):
                context.stage = ResearchStage.COMPLETE
                context.updated_at = datetime.now()
                await self._notify_completion(context, success=True)
            else:
                context.stage = ResearchStage.FAILED
                context.updated_at = datetime.now()
                await self._notify_completion(context, success=False)

        except Exception as e:
            logger.error(f"Critical error in research task orchestration: {e}")
            context.stage = ResearchStage.FAILED
            context.updated_at = datetime.now()
            await self._notify_completion(context, success=False)
        finally:
            # Clean up context after delay
            asyncio.create_task(self._cleanup_context(context.task_id, delay=3600))  # 1 hour
    
    async def _execute_planning_stage(self, context: ResearchContext) -> bool:
        """Execute the planning stage of research."""
        try:
            # Create planning action
            action = ResearchAction(
                task_id=f"{context.task_id}_planning",
                context_id=context.task_id,
                agent_type="planning",
                action="plan_research",
                payload={
                    "query": context.query,
                    "context": context.context_data,
                    "user_id": context.user_id,
                    "task_id": context.task_id,
                },
            )

            # Send to planning agent
            response = await self._send_to_agent("planning", action)

            if response and response.status == "completed":
                # Update context with planning results
                context.context_data["research_plan"] = response.result
                return True

            return False

        except Exception as e:
            logger.error(f"Planning stage failed: {e}")
            return False
    
    async def _execute_literature_review_stage(self, context: ResearchContext) -> bool:
        """Execute the literature review stage of research."""
        try:
            # Get the research plan from the context
            research_plan = context.context_data.get("research_plan")

            # Create literature review action
            action = ResearchAction(
                task_id=f"{context.task_id}_literature",
                context_id=context.task_id,
                agent_type="literature",
                action="search_academic_papers",
                payload={
                    "query": context.query,
                    "research_plan": research_plan,
                    "search_depth": "comprehensive",
                    "max_results": 10,
                },
            )

            # Send to literature agent
            response = await self._send_to_agent("literature", action)

            if response and response.status == "completed":
                # Store search results
                if response.result:
                    context.search_results = response.result.get("results", [])
                    context.context_data["search_results"] = context.search_results
                return True

            return False

        except Exception as e:
            logger.error(f"Literature review stage failed: {e}")
            return False
    
    async def _execute_reasoning_stage(self, context: ResearchContext) -> bool:
        """Execute the reasoning stage of research."""
        try:
            # Create reasoning action
            action = ResearchAction(
                task_id=f"{context.task_id}_reasoning",
                context_id=context.task_id,
                agent_type="planning",
                action="analyze_information",
                payload={
                    "query": context.query,
                    "context": context.context_data,
                    "analysis_type": "comprehensive",
                    "include_sources": True,
                },
            )

            # Send to planning agent
            response = await self._send_to_agent("planning", action)

            if response and response.status == "completed":
                # Store reasoning output
                if response.result:
                    context.reasoning_output = response.result.get("analysis", "")
                    context.context_data["reasoning_output"] = context.reasoning_output
                return True

            return False

        except Exception as e:
            logger.error(f"Reasoning stage failed: {e}")
            return False
    
    async def _execute_execution_stage(self, context: ResearchContext) -> bool:
        """Execute the execution stage of research."""
        try:
            # Create execution action
            action = ResearchAction(
                task_id=f"{context.task_id}_execution",
                context_id=context.task_id,
                agent_type="executor",
                action="execute_research",
                payload={
                    "query": context.query,
                    "context": context.context_data,
                    "execution_type": "comprehensive",
                },
            )

            # Send to execution agent
            response = await self._send_to_agent("executor", action)

            if response and response.status == "completed":
                # Store execution results
                if response.result:
                    context.execution_results = response.result.get("results", [])
                    context.context_data["execution_results"] = context.execution_results
                return True

            return False

        except Exception as e:
            logger.error(f"Execution stage failed: {e}")
            return False
    
    async def _execute_synthesis_stage(self, context: ResearchContext) -> bool:
        """Execute the synthesis stage of research."""
        try:
            # Create synthesis action
            action = ResearchAction(
                task_id=f"{context.task_id}_synthesis",
                context_id=context.task_id,
                agent_type="planning",
                action="synthesize_results",
                payload={
                    "query": context.query,
                    "context": context.context_data,
                    "synthesis_type": "comprehensive",
                    "include_citations": True,
                },
            )

            # Send to planning agent for synthesis
            response = await self._send_to_agent("planning", action)

            if response and response.status == "completed":
                # Store synthesis
                if response.result:
                    context.synthesis = response.result.get("synthesis", "")
                    context.context_data["synthesis"] = context.synthesis
                return True

            return False

        except Exception as e:
            logger.error(f"Synthesis stage failed: {e}")
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
            if not self.websocket or not self.mcp_connected:
                logger.error("MCP client not connected")
                return None

            # Create a future to wait for the response
            response_future = asyncio.Future()
            self.pending_responses[action.task_id] = response_future

            # Send action via MCP
            task_message = {
                "type": "task",
                "task_id": action.task_id,
                "context_id": action.context_id,
                "agent_type": agent_type,
                "action": action.action,
                "payload": action.payload,
                "priority": action.priority,
                "parallelism": action.parallelism,
                "timeout": action.timeout,
                "retry_count": action.retry_count,
                "dependencies": action.dependencies
            }

            await self.websocket.send(json.dumps(task_message))

            # Wait for response with timeout
            try:
                response = await asyncio.wait_for(response_future, timeout=self.response_timeout)
                return response
            except asyncio.TimeoutError:
                logger.error(f"Timeout waiting for response from {agent_type} for task {action.task_id}")
                return None
            finally:
                # Clean up pending response
                self.pending_responses.pop(action.task_id, None)

        except Exception as e:
            logger.error(f"Failed to send action to {agent_type}: {e}")
            # Clean up pending response on error
            self.pending_responses.pop(action.task_id, None)
            return None
    
    async def _handle_agent_response(self, message_data: Dict[str, Any]) -> None:
        """Handle response from agent."""
        try:
            # Create AgentResponse object from message data
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
                    logger.debug(f"Completed pending response for task {task_id}")

        except Exception as e:
            logger.error(f"Error handling agent response: {e}")
    
    async def _notify_progress(self, context: ResearchContext) -> None:
        """Notify progress callbacks about research progress."""
        try:
            # Calculate progress based on mode
            total_stages = 3 if context.single_agent_mode else 5
            progress_data = {
                "task_id": context.task_id,
                "stage": context.stage.value,
                "progress": min(len(context.completed_stages) / total_stages * 100, 100.0),
                "query": context.query,
                "updated_at": context.updated_at.isoformat(),
            }

            # Call progress callbacks
            for callback in self.progress_callbacks:
                try:
                    await callback(progress_data)
                except Exception as e:
                    logger.error(f"Progress callback error: {e}")

        except Exception as e:
            logger.error(f"Error notifying progress: {e}")
    
    async def _notify_completion(self, context: ResearchContext, success: bool) -> None:
        """Notify completion callbacks about research completion."""
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
                    logger.error(f"Completion callback error: {e}")

        except Exception as e:
            logger.error(f"Error notifying completion: {e}")
    
    async def _cleanup_context(self, task_id: str, delay: int = 0) -> None:
        """Clean up research context after delay."""
        try:
            if delay > 0:
                await asyncio.sleep(delay)

            if task_id in self.active_contexts:
                del self.active_contexts[task_id]
                logger.info(f"Cleaned up context for task {task_id}")

        except Exception as e:
            logger.error(f"Error cleaning up context: {e}")
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel an active research task."""
        try:
            if task_id in self.active_contexts:
                context = self.active_contexts[task_id]
                context.stage = ResearchStage.FAILED
                context.updated_at = datetime.now()

                await self._notify_completion(context, success=False)
                del self.active_contexts[task_id]
                logger.info(f"Cancelled task {task_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error cancelling task: {e}")
            return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of research task."""
        if task_id not in self.active_contexts:
            return None

        context = self.active_contexts[task_id]
        
        # Calculate progress based on mode
        total_stages = 3 if context.single_agent_mode else 5
        
        return {
            "task_id": task_id,
            "stage": context.stage.value,
            "progress": min(len(context.completed_stages) / total_stages * 100, 100.0),
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
        """Get list of all active research tasks."""
        active_tasks = []
        for task_id in self.active_contexts.keys():
            status = self.get_task_status(task_id)
            if status:
                active_tasks.append(status)
        return active_tasks


# Request/Response models for FastAPI
class StartResearchTaskRequest(BaseModel):
    query: str
    user_id: str
    project_id: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class TaskRequest(BaseModel):
    action: str
    payload: Dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    agent_type: str
    mcp_connected: bool
    capabilities: List[str]
    active_tasks: int
    max_concurrent_tasks: int


# Global service instance
research_manager_service: Optional[ResearchManagerService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global research_manager_service
    
    # Load configuration
    config_path = Path("/app/config/config.json")
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
    else:
        config = {
            "service_host": "0.0.0.0",
            "service_port": 8002,
            "mcp_server_url": "ws://mcp-server:9000",
            "max_concurrent_tasks": 5,
            "task_timeout": 600,
            "response_timeout": 300
        }
    
    # Start service
    research_manager_service = ResearchManagerService(config)
    await research_manager_service.start()
    
    try:
        yield
    finally:
        # Cleanup
        if research_manager_service:
            await research_manager_service.stop()


# FastAPI application
app = FastAPI(
    title="Research Manager Service",
    description="Research Manager for coordinating multi-agent research tasks",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    if not research_manager_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    capabilities = [
        "start_research_task",
        "cancel_task",
        "get_task_status",
        "orchestrate_research",
        "estimate_task_cost",
        "coordinate_agents",
        "monitor_progress"
    ]
    
    return HealthResponse(
        status="healthy",
        agent_type="research_manager",
        mcp_connected=research_manager_service.mcp_connected,
        capabilities=capabilities,
        active_tasks=len(research_manager_service.active_contexts),
        max_concurrent_tasks=research_manager_service.max_concurrent_tasks
    )


@app.post("/start_research")
async def start_research(request: StartResearchTaskRequest):
    """Start a new research task."""
    if not research_manager_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        task_id, cost_info = await research_manager_service.start_research_task(
            request.query,
            request.user_id,
            request.project_id,
            request.options
        )
        return {
            "task_id": task_id,
            "cost_info": cost_info
        }
    except Exception as e:
        logger.error(f"Error starting research task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/task/{task_id}/status")
async def get_task_status(task_id: str):
    """Get status of a research task."""
    if not research_manager_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    status = research_manager_service.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return status


@app.delete("/task/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a research task."""
    if not research_manager_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    success = await research_manager_service.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"message": "Task cancelled successfully"}


@app.get("/tasks")
async def get_active_tasks():
    """Get all active research tasks."""
    if not research_manager_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return research_manager_service.get_active_tasks()


@app.post("/task")
async def process_task(request: TaskRequest):
    """Process a research manager task directly (for testing)."""
    if not research_manager_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        result = await research_manager_service._process_research_manager_task({
            "action": request.action,
            "payload": request.payload
        })
        return result
    except Exception as e:
        logger.error(f"Error processing task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "research_manager_service:app",
        host="0.0.0.0",
        port=8002,
        log_level="info"
    )
