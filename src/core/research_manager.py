"""
Research Manager - Orchestrates multi-agent research tasks using MCP protocol.

This module provides the core Research Manager that coordinates between different
AI agents (Retriever, Reasoner, Executor, Memory) to perform complex research tasks.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from mcp.client import MCPClient
from mcp.protocols import ResearchAction, AgentResponse, TaskStatus
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
        
        # MCP client for agent communication
        self.mcp_client: Optional[MCPClient] = None
        
        # Active research contexts
        self.active_contexts: Dict[str, ResearchContext] = {}
        
        # Agent capabilities and availability
        self.agent_capabilities: Dict[str, List[str]] = {}
        self.agent_availability: Dict[str, bool] = {}
        
        # Callbacks for UI updates
        self.progress_callbacks: List[Callable] = []
        self.completion_callbacks: List[Callable] = []
        
        # Configuration
        self.research_config = self.config.get_research_config()
        self.max_concurrent_tasks = self.research_config.get('max_concurrent_tasks', 5)
        self.task_timeout = self.research_config.get('task_timeout', 300)  # 5 minutes
        
        self.logger.info("Research Manager initialized")
    
    async def initialize(self) -> bool:
        """
        Initialize the Research Manager and establish MCP connection.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            # Initialize MCP client
            mcp_config = self.config.get_mcp_config()
            self.mcp_client = MCPClient(
                host=mcp_config.get('host', 'localhost'),
                port=mcp_config.get('port', 8765)
            )
            
            # Connect to MCP server
            await self.mcp_client.connect()
            
            # Register message handlers
            self.mcp_client.add_message_handler('agent_response', self._handle_agent_response)
            self.mcp_client.add_message_handler('agent_registration', self._handle_agent_registration)
            self.mcp_client.add_message_handler('task_update', self._handle_task_update)
            
            self.logger.info("Research Manager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Research Manager: {e}")
            self.error_handler.handle_error(e, "research_manager_init")
            return False
    
    async def start_research_task(
        self, 
        query: str, 
        user_id: str, 
        conversation_id: str,
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start a new research task.
        
        Args:
            query: Research query to process
            user_id: ID of the user making the request
            conversation_id: ID of the conversation
            options: Optional task configuration
            
        Returns:
            str: Task ID for tracking
        """
        task_id = str(uuid.uuid4())
        
        try:
            # Create research context
            context = ResearchContext(
                task_id=task_id,
                query=query,
                user_id=user_id,
                conversation_id=conversation_id
            )
            
            # Apply options if provided
            if options:
                context.max_retries = options.get('max_retries', context.max_retries)
                context.metadata.update(options.get('metadata', {}))
            
            # Store context
            self.active_contexts[task_id] = context
            
            # Start task orchestration
            asyncio.create_task(self._orchestrate_research_task(context))
            
            self.logger.info(f"Started research task {task_id} for query: {query}")
            return task_id
            
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
            
            # Execute research stages sequentially
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
            
            # Send action via MCP client
            success = await self.mcp_client.send_task(action)
            
            if success:
                # Wait for response (simplified for now)
                # In a real implementation, we'd wait for the actual response
                # For now, return a mock successful response
                return AgentResponse(
                    task_id=action.task_id,
                    context_id=action.context_id,
                    agent_type=agent_type,
                    status="completed",
                    result={"success": True}
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to send action to {agent_type}: {e}")
            return None
    
    def _handle_agent_response(self, message_data: Dict[str, Any]) -> None:
        """
        Handle response from agent.
        
        Args:
            message_data: Message data from agent
        """
        try:
            # Extract task ID from message
            task_id = message_data.get('task_id')
            if task_id and task_id in self.active_contexts:
                context = self.active_contexts[task_id]
                # Response handling is done in stage execution methods
                self.logger.debug(f"Received response for task {task_id}")
            
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
            
            for callback in self.progress_callbacks:
                try:
                    await callback(progress_data)
                except Exception as e:
                    self.logger.error(f"Progress callback error: {e}")
            
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
