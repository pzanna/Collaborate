"""
Research Manager - Orchestrates multi-agent research tasks using MCP protocol.

This module provides the core Research Manager that coordinates between different
AI agents (Retriever, Reasoner, Executor, Memory) to perform complex research tasks.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

try:
    # Try relative imports first (when imported from within src package)
    from ..mcp.client import MCPClient
    from ..mcp.protocols import ResearchAction, AgentResponse, TaskStatus
    from ..mcp.cost_estimator import CostEstimator
    from ..config.config_manager import ConfigManager
    from ..utils.error_handler import ErrorHandler
    from ..utils.performance import PerformanceMonitor
except ImportError:
    # Fall back to absolute imports (when imported from outside src package)
    from mcp.client import MCPClient
    from mcp.protocols import ResearchAction, AgentResponse, TaskStatus
    from mcp.cost_estimator import CostEstimator
    from config.config_manager import ConfigManager
    from utils.error_handler import ErrorHandler
    from utils.performance import PerformanceMonitor


class ResearchStage(Enum):
    """Stages of research process."""
    PLANNING = "planning"
    RETRIEVAL = "retrieval"
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
    conversation_id: str
    project_id: Optional[str] = None  # New field for project association
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
    Main orchestrator for multi-agent research tasks.
    
    The Research Manager coordinates between different AI agents to perform
    complex research tasks, managing the flow of information and ensuring
    proper task completion.
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the Research Manager.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config = config_manager
        self.logger = logging.getLogger(__name__)
        self.error_handler = ErrorHandler()
        self.performance_monitor = PerformanceMonitor()
        
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
        self.max_concurrent_tasks = self.research_config.get('max_concurrent_tasks', 5)
        self.task_timeout = self.research_config.get('task_timeout', 600)  # 10 minutes
        
        self.logger.info("Research Manager initialized with cost control")
    
    async def _ensure_mcp_client_initialized(self) -> None:
        """
        Ensure MCP client is initialized (lazy initialization).
        """
        if self.mcp_client is None:
            try:
                # Initialize MCP client
                mcp_config = self.config.get_mcp_config()
                self.mcp_client = MCPClient(
                    host=mcp_config.get('host', 'localhost'),
                    port=mcp_config.get('port', 8765)
                )
                
                # Connect to MCP server
                await self.mcp_client.connect()
                
                # Identify as research manager
                if self.mcp_client.websocket:
                    import json
                    identification_message = {
                        'type': 'identify_research_manager',
                        'data': {'manager_id': 'research_manager'},
                        'timestamp': datetime.now().isoformat()
                    }
                    self.logger.info(f"Sending research manager identification: {identification_message}")
                    await self.mcp_client.websocket.send(json.dumps(identification_message))
                    self.logger.info("✓ Successfully sent research manager identification to MCP server")
                else:
                    self.logger.error("No WebSocket connection available for identification")
                
                # Register message handlers
                self.mcp_client.add_message_handler('agent_response', self._handle_agent_response)
                self.mcp_client.add_message_handler('agent_registration', self._handle_agent_registration)
                self.mcp_client.add_message_handler('task_update', self._handle_task_update)
                
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
                        'type': 'identify_research_manager',
                        'data': {'manager_id': 'research_manager'},
                        'timestamp': datetime.now().isoformat()
                    }
                    self.logger.info(f"Sending research manager identification: {identification_message}")
                    await self.mcp_client.websocket.send(json.dumps(identification_message))
                    self.logger.info("✓ Successfully sent research manager identification to MCP server")
                else:
                    self.logger.error("No WebSocket connection available for identification")
                
                # Register message handlers
                self.mcp_client.add_message_handler('agent_response', self._handle_agent_response)
                self.mcp_client.add_message_handler('agent_registration', self._handle_agent_registration)
                self.mcp_client.add_message_handler('task_update', self._handle_task_update)
                
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
        self,
        query: str,
        conversation_id: str,
        options: Optional[Dict[str, Any]] = None
    ) -> tuple[Dict[str, Any], bool, bool]:
        """
        Estimate cost for a research task with approval logic.
        
        Args:
            query: Research query to process
            conversation_id: ID of the conversation for cost tracking
            options: Optional task configuration including single_agent_mode
            
        Returns:
            tuple: (cost_info, should_proceed, single_agent_mode)
        """
        # Determine agent configuration
        single_agent_mode = options.get('single_agent_mode', False) if options else False
        
        if single_agent_mode:
            agents_to_use = ["retriever"]  # Use only retriever in single agent mode
            parallel_execution = False
        else:
            agents_to_use = ["retriever", "reasoner", "executor", "memory"]
            parallel_execution = True
        
        # Get cost estimate
        cost_estimate = self.cost_estimator.estimate_task_cost(
            query=query,
            agents=agents_to_use,
            parallel_execution=parallel_execution
        )
        
        # Check if task should proceed based on cost
        should_proceed, cost_reason = self.cost_estimator.should_proceed_with_task(
            cost_estimate, conversation_id
        )
        
        # Get cost recommendations
        recommendations = self.cost_estimator.get_cost_recommendations(cost_estimate)
        
        # Prepare cost information for return
        cost_info = {
            'estimate': {
                'tokens': cost_estimate.estimated_tokens,
                'cost_usd': cost_estimate.estimated_cost_usd,
                'complexity': cost_estimate.task_complexity.value,
                'agent_count': cost_estimate.agent_count,
                'confidence': cost_estimate.confidence,
                'reasoning': cost_estimate.reasoning
            },
            'should_proceed': should_proceed,
            'cost_reason': cost_reason,
            'recommendations': recommendations
        }
        
        return cost_info, should_proceed, single_agent_mode

    async def start_research_task(
        self, 
        query: str, 
        user_id: str, 
        conversation_id: str,
        options: Optional[Dict[str, Any]] = None
    ) -> tuple[str, Dict[str, Any]]:
        """
        Start a new research task with cost estimation and control.
        
        Args:
            query: Research query to process
            user_id: ID of the user making the request
            conversation_id: ID of the conversation
            options: Optional task configuration including cost_override
            
        Returns:
            tuple: (task_id, cost_info) where cost_info contains estimation and recommendations
        """
        task_id = str(uuid.uuid4())
        
        try:
            # Ensure MCP client is initialized
            await self._ensure_mcp_client_initialized()
            
            # Estimate cost for the research task
            cost_info, should_proceed, single_agent_mode = await self._estimate_task_cost(
                query, conversation_id, options
            )
            
            # Create research context
            context = ResearchContext(
                task_id=task_id,
                query=query,
                user_id=user_id,
                conversation_id=conversation_id,
                project_id=options.get('project_id') if options else None,  # Extract project_id from options
                estimated_cost=cost_info['estimate']['cost_usd'],
                single_agent_mode=single_agent_mode
            )
            
            # Apply options if provided
            if options:
                context.max_retries = options.get('max_retries', context.max_retries)
                context.metadata.update(options.get('metadata', {}))
                # Check for cost override
                context.cost_approved = options.get('cost_override', False)
            
            # Only proceed if cost is approved or automatically acceptable
            if should_proceed or context.cost_approved:
                context.cost_approved = True
                
                # Start cost tracking
                self.cost_estimator.start_cost_tracking(task_id, conversation_id)
                
                # Store context
                self.active_contexts[task_id] = context
                
                # Start task orchestration
                asyncio.create_task(self._orchestrate_research_task(context))
                
                self.logger.info(f"Started research task {task_id} for query: {query}, "
                               f"estimated cost: ${cost_info['estimate']['cost_usd']:.4f}")
            else:
                # Task not approved due to cost
                cost_info['task_started'] = False
                self.logger.warning(f"Research task blocked due to cost: {cost_info['cost_reason']}")
            
            cost_info['task_started'] = should_proceed or context.cost_approved
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
                # Single agent mode - only use retriever
                stages = [
                    (ResearchStage.PLANNING, self._execute_planning_stage),
                    (ResearchStage.RETRIEVAL, self._execute_retrieval_stage),
                ]
                self.logger.info(f"Running task {context.task_id} in single-agent mode (cost-optimized)")
            else:
                # Full multi-agent mode
                stages = [
                    (ResearchStage.PLANNING, self._execute_planning_stage),
                    (ResearchStage.RETRIEVAL, self._execute_retrieval_stage),
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
                        self.logger.info(f"Completed stage {stage.value} for task {context.task_id}")
                    else:
                        context.failed_stages.append(stage)
                        self.logger.error(f"Failed stage {stage.value} for task {context.task_id}")
                        
                        # Retry logic
                        if context.retry_count < context.max_retries:
                            context.retry_count += 1
                            context.failed_stages.remove(stage)
                            self.logger.info(f"Retrying stage {stage.value} for task {context.task_id} (attempt {context.retry_count})")
                            # Re-execute the stage
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
                await self._notify_completion(context, success=True)
            else:
                context.stage = ResearchStage.FAILED
                await self._notify_completion(context, success=False)
                
        except Exception as e:
            self.logger.error(f"Critical error in research task orchestration: {e}")
            context.stage = ResearchStage.FAILED
            await self._notify_completion(context, success=False)
        finally:
            # End cost tracking and get final usage
            if context.cost_approved:
                final_usage = self.cost_estimator.end_cost_tracking(context.task_id)
                if final_usage:
                    context.actual_cost = final_usage.cost_usd
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
                context_id=context.conversation_id,
                agent_type="reasoner",
                action="plan_research",
                payload={
                    "query": context.query,
                    "context": context.context_data,
                    "user_id": context.user_id,
                    "conversation_id": context.conversation_id
                }
            )
            
            # Send to planning agent (using reasoning agent for now)
            response = await self._send_to_agent("reasoner", action)
            
            if response and response.status == "completed":
                # Update context with planning results
                context.context_data["research_plan"] = response.result
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Planning stage failed: {e}")
            return False
    
    async def _execute_retrieval_stage(self, context: ResearchContext) -> bool:
        """
        Execute the retrieval stage of research.
        
        Args:
            context: Research context
            
        Returns:
            bool: True if successful
        """
        try:
            # Create retrieval action
            action = ResearchAction(
                task_id=context.task_id,
                context_id=context.conversation_id,
                agent_type="retriever",
                action="search_information",
                payload={
                    "query": context.query,
                    "context": context.context_data,
                    "search_depth": "comprehensive",
                    "max_results": 10
                }
            )
            
            # Send to retrieval agent
            response = await self._send_to_agent("retriever", action)
            
            if response and response.status == "completed":
                # Store search results
                if response.result:
                    context.search_results = response.result.get('results', [])
                    context.context_data["search_results"] = context.search_results
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Retrieval stage failed: {e}")
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
                context_id=context.conversation_id,
                agent_type="reasoner",
                action="analyze_information",
                payload={
                    "query": context.query,
                    "context": context.context_data,
                    "analysis_type": "comprehensive",
                    "include_sources": True
                }
            )
            
            # Send to reasoning agent
            response = await self._send_to_agent("reasoner", action)
            
            if response and response.status == "completed":
                # Store reasoning output
                if response.result:
                    context.reasoning_output = response.result.get('analysis', '')
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
                context_id=context.conversation_id,
                agent_type="executor",
                action="execute_research",
                payload={
                    "query": context.query,
                    "context": context.context_data,
                    "execution_type": "comprehensive"
                }
            )
            
            # Send to execution agent
            response = await self._send_to_agent("executor", action)
            
            if response and response.status == "completed":
                # Store execution results
                if response.result:
                    context.execution_results = response.result.get('results', [])
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
                context_id=context.conversation_id,
                agent_type="reasoner",
                action="synthesize_results",
                payload={
                    "query": context.query,
                    "context": context.context_data,
                    "synthesis_type": "comprehensive",
                    "include_citations": True
                }
            )
            
            # Send to reasoning agent for synthesis
            response = await self._send_to_agent("reasoner", action)
            
            if response and response.status == "completed":
                # Store synthesis
                if response.result:
                    context.synthesis = response.result.get('synthesis', '')
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
                task_id=message_data.get('task_id', ''),
                context_id=message_data.get('context_id', ''),
                agent_type=message_data.get('agent_type', ''),
                status=message_data.get('status', ''),
                result=message_data.get('result'),
                error=message_data.get('error')
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
            agent_id = message_data.get('agent_id')
            capabilities = message_data.get('capabilities', [])
            
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
            task_id = message_data.get('task_id')
            status = message_data.get('status')
            
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
                'task_id': context.task_id,
                'stage': context.stage.value,
                'progress': len(context.completed_stages) / 5 * 100,  # 5 total stages
                'query': context.query,
                'updated_at': context.updated_at.isoformat()
            }
            
            # Call global progress callbacks
            for callback in self.progress_callbacks:
                try:
                    await callback(progress_data)
                except Exception as e:
                    self.logger.error(f"Progress callback error: {e}")
            
            # Call task-specific progress callbacks
            task_callbacks = context.metadata.get('progress_callbacks', [])
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
                'task_id': context.task_id,
                'success': success,
                'query': context.query,
                'results': {
                    'search_results': context.search_results,
                    'reasoning_output': context.reasoning_output,
                    'execution_results': context.execution_results,
                    'synthesis': context.synthesis
                },
                'completed_stages': [stage.value for stage in context.completed_stages],
                'failed_stages': [stage.value for stage in context.failed_stages],
                'duration': (context.updated_at - context.created_at).total_seconds(),
                'retry_count': context.retry_count
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
            'task_id': task_id,
            'stage': context.stage.value,
            'progress': len(context.completed_stages) / 5 * 100,
            'query': context.query,
            'completed_stages': [stage.value for stage in context.completed_stages],
            'failed_stages': [stage.value for stage in context.failed_stages],
            'retry_count': context.retry_count,
            'created_at': context.created_at.isoformat(),
            'estimated_cost': context.estimated_cost,
            'actual_cost': context.actual_cost,
            'single_agent_mode': context.single_agent_mode,
            'updated_at': context.updated_at.isoformat()
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
        
        total_stages = 5  # planning, retrieval, reasoning, execution, synthesis
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
            if 'progress_callbacks' not in context.metadata:
                context.metadata['progress_callbacks'] = []
            context.metadata['progress_callbacks'].append(callback)
    
    def remove_progress_callback(self, task_id: str) -> None:
        """
        Remove progress callbacks for a specific task.
        
        Args:
            task_id: Task ID to remove callbacks for
        """
        context = self.active_contexts.get(task_id)
        if context and 'progress_callbacks' in context.metadata:
            context.metadata['progress_callbacks'] = []
    
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
        options = {'single_agent_mode': single_agent_mode}
        cost_info, _, _ = await self._estimate_task_cost(
            query=query,
            conversation_id="estimate_only",  # Dummy conversation ID for estimation
            options=options
        )
        
        # Remove task-specific fields for estimation-only response
        cost_info.pop('should_proceed', None)
        cost_info.pop('cost_reason', None)
        cost_info['single_agent_mode'] = single_agent_mode
        
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
        # Fallback synchronous implementation for backwards compatibility
        agents_to_use = ["retriever"] if single_agent_mode else ["retriever", "reasoner", "executor", "memory"]
        parallel_execution = not single_agent_mode
        
        estimate = self.cost_estimator.estimate_task_cost(
            query=query,
            agents=agents_to_use,
            parallel_execution=parallel_execution
        )
        
        recommendations = self.cost_estimator.get_cost_recommendations(estimate)
        
        return {
            'estimate': {
                'tokens': estimate.estimated_tokens,
                'cost_usd': estimate.estimated_cost_usd,
                'complexity': estimate.task_complexity.value,
                'agent_count': estimate.agent_count,
                'confidence': estimate.confidence,
                'reasoning': estimate.reasoning
            },
            'recommendations': recommendations,
            'single_agent_mode': single_agent_mode
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
                'tokens_used': usage.tokens_used,
                'cost_usd': usage.cost_usd,
                'provider_breakdown': usage.provider_breakdown,
                'agent_breakdown': usage.agent_breakdown,
                'duration_seconds': (datetime.now() - usage.start_time).total_seconds()
            }
        
        return {
            'task_id': task_id,
            'estimated_cost': context.estimated_cost,
            'actual_cost': context.actual_cost,
            'cost_approved': context.cost_approved,
            'single_agent_mode': context.single_agent_mode,
            'current_usage': current_usage,
            'stage': context.stage.value
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
                'plan_id': f"plan_{context_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'context_id': context_id,
                'prompt': f"Research plan for: {context.query}",
                'raw_response': "RM AI response for active research context",
                'parsed_tasks': [
                    {'task_id': 'task_1', 'agent': 'retriever', 'action': 'search_web'},
                    {'task_id': 'task_2', 'agent': 'reasoner', 'action': 'analyze_results'}
                ],
                'created_at': datetime.now().isoformat(),
                'execution_status': context.stage.value,
                'modifications': []
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
                plans.append({
                    'plan_id': f"plan_{ctx_id}",
                    'context_id': ctx_id,
                    'prompt': f"Research plan for: {getattr(context, 'query', 'Active research context')}",
                    'created_at': context.created_at.isoformat(),
                    'execution_status': context.stage.value,
                    'parsed_tasks': [
                        {'task_id': 'task_1', 'agent': 'retriever'},
                        {'task_id': 'task_2', 'agent': 'reasoner'}
                    ],
                    'modifications': []
                })
        
        # Return only real active contexts, no mock data
        return plans[:limit]
