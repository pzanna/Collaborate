"""
Base Agent class for all research agents.

This module provides the abstract base class that all specialized agents
(Literature, Planning, Executor, Memory) inherit from.
"""

import asyncio
import json
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from enum import Enum

from ..mcp.client import MCPClient
from ..mcp.protocols import ResearchAction, AgentResponse, AgentRegistration
from ..config.config_manager import ConfigManager
from ..utils.error_handler import ErrorHandler
from ..utils.performance import PerformanceMonitor


class AgentStatus(Enum):
    """Agent status enumeration."""
    INITIALIZING = "initializing"
    READY = "ready"
    WORKING = "working"
    ERROR = "error"
    SHUTDOWN = "shutdown"


class BaseAgent(ABC):
    """
    Abstract base class for all research agents.
    
    This class provides the common functionality that all agents need:
    - MCP communication
    - Task processing
    - Error handling
    - Performance monitoring
    - Status management
    """
    
    def __init__(self, agent_type: str, config_manager: ConfigManager):
        """
        Initialize the base agent.
        
        Args:
            agent_type: Type of agent (e.g., 'literature', 'planning')
            config_manager: Configuration manager instance
        """
        self.agent_type = agent_type
        self.agent_id = f"{agent_type}_{uuid.uuid4().hex[:8]}"
        self.config = config_manager
        self.logger = logging.getLogger(f"{__name__}.{agent_type}")
        self.error_handler = ErrorHandler()
        self.performance_monitor = PerformanceMonitor()
        
        # Agent state
        self.status = AgentStatus.INITIALIZING
        self.mcp_client: Optional[MCPClient] = None
        self.is_running = False
        self.current_task: Optional[ResearchAction] = None
        
        # Agent configuration
        self.agent_config = self._get_agent_config()
        self.max_concurrent_tasks = self.agent_config.get('max_concurrent', 3)
        self.task_timeout = self.agent_config.get('timeout', 60)
        self.capabilities = self._get_capabilities()
        
        # Task management
        self.active_tasks: Dict[str, ResearchAction] = {}
        self.completed_tasks: List[str] = []
        self.failed_tasks: List[str] = []
        
        # Performance metrics
        self.task_count = 0
        self.success_count = 0
        self.error_count = 0
        
        self.logger.info(f"Agent {self.agent_id} initialized with capabilities: {self.capabilities}")
    
    async def initialize(self) -> bool:
        """
        Initialize the agent and establish MCP connection.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            self.logger.info(f"Initializing agent {self.agent_id}")
            
            # Initialize MCP client
            mcp_config = self.config.get_mcp_config()
            self.mcp_client = MCPClient(
                host=mcp_config.get('host', 'localhost'),
                port=mcp_config.get('port', 9000)
            )
            
            # Connect to MCP server
            await self.mcp_client.connect()
            
            # Register with MCP server
            await self._register_with_mcp()
            
            # Perform agent-specific initialization
            await self._initialize_agent()
            
            self.status = AgentStatus.READY
            self.logger.info(f"Agent {self.agent_id} initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize agent {self.agent_id}: {e}")
            self.status = AgentStatus.ERROR
            self.error_handler.handle_error(e, f"agent_{self.agent_type}_init")
            return False
    
    async def start(self) -> None:
        """Start the agent task processing loop."""
        if self.status != AgentStatus.READY:
            raise RuntimeError(f"Agent {self.agent_id} is not ready to start")
        
        self.is_running = True
        self.logger.info(f"Starting agent {self.agent_id}")
        
        # Start task processing loop
        await self._task_processing_loop()
    
    async def run(self) -> None:
        """Initialize and run the agent (convenience method)."""
        success = await self.initialize()
        if success:
            await self.start()
        else:
            raise RuntimeError(f"Failed to initialize agent {self.agent_id}")
    
    async def stop(self) -> None:
        """Stop the agent and clean up resources."""
        self.logger.info(f"Stopping agent {self.agent_id}")
        self.is_running = False
        self.status = AgentStatus.SHUTDOWN
        
        # Cancel active tasks
        for task_id in list(self.active_tasks.keys()):
            await self._cancel_task(task_id)
        
        # Disconnect from MCP
        if self.mcp_client:
            await self.mcp_client.disconnect()
        
        # Perform agent-specific cleanup
        await self._cleanup_agent()
        
        self.logger.info(f"Agent {self.agent_id} stopped")
    
    async def process_task(self, task: ResearchAction) -> AgentResponse:
        """
        Process a research task.
        
        Args:
            task: Research task to process
            
        Returns:
            AgentResponse: Response with results or error
        """
        task_id = task.task_id
        self.logger.info(f"Processing task {task_id} for agent {self.agent_id}")
        
        # Check if agent can handle this task
        if not self._can_handle_task(task):
            return AgentResponse(
                task_id=task_id,
                context_id=task.context_id,
                agent_type=self.agent_type,
                status="failed",
                error=f"Agent {self.agent_type} cannot handle task: {task.action}"
            )
        
        # Check capacity
        if len(self.active_tasks) >= self.max_concurrent_tasks:
            return AgentResponse(
                task_id=task_id,
                context_id=task.context_id,
                agent_type=self.agent_type,
                status="failed",
                error=f"Agent {self.agent_type} at capacity: {len(self.active_tasks)}/{self.max_concurrent_tasks}"
            )
        
        try:
            # Update status
            self.status = AgentStatus.WORKING
            self.active_tasks[task_id] = task
            self.current_task = task
            self.task_count += 1
            
            # Start performance monitoring
            self.performance_monitor.start_timer(f"task_{task_id}")
            
            # Process the task (implemented by subclasses)
            result = await self._process_task_impl(task)
            
            # End performance monitoring
            duration = self.performance_monitor.end_timer(f"task_{task_id}")
            
            # Update status
            self.status = AgentStatus.READY
            self.active_tasks.pop(task_id, None)
            self.current_task = None
            self.completed_tasks.append(task_id)
            self.success_count += 1
            
            self.logger.info(f"Task {task_id} completed in {duration:.2f}s")
            
            return AgentResponse(
                task_id=task_id,
                context_id=task.context_id,
                agent_type=self.agent_type,
                status="completed",
                result=result
            )
            
        except Exception as e:
            # Error handling
            self.logger.error(f"Task {task_id} failed: {e}")
            self.status = AgentStatus.READY
            self.active_tasks.pop(task_id, None)
            self.current_task = None
            self.failed_tasks.append(task_id)
            self.error_count += 1
            
            # End performance monitoring
            self.performance_monitor.end_timer(f"task_{task_id}")
            
            self.error_handler.handle_error(e, f"agent_{self.agent_type}_task")
            
            return AgentResponse(
                task_id=task_id,
                context_id=task.context_id,
                agent_type=self.agent_type,
                status="failed",
                error=str(e)
            )
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current agent status.
        
        Returns:
            Dict[str, Any]: Agent status information
        """
        return {
            'agent_id': self.agent_id,
            'agent_type': self.agent_type,
            'status': self.status.value,
            'capabilities': self.capabilities,
            'active_tasks': len(self.active_tasks),
            'max_concurrent_tasks': self.max_concurrent_tasks,
            'task_count': self.task_count,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'success_rate': self.success_count / max(self.task_count, 1) * 100,
            'current_task': self.current_task.task_id if self.current_task else None,
            'is_running': self.is_running
        }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics.
        
        Returns:
            Dict[str, Any]: Performance statistics
        """
        return self.performance_monitor.get_performance_stats()
    
    # Abstract methods that must be implemented by subclasses
    
    @abstractmethod
    async def _process_task_impl(self, task: ResearchAction) -> Dict[str, Any]:
        """
        Process a task (implemented by subclasses).
        
        Args:
            task: Research task to process
            
        Returns:
            Dict[str, Any]: Task result
        """
        pass
    
    @abstractmethod
    def _get_capabilities(self) -> List[str]:
        """
        Get agent capabilities (implemented by subclasses).
        
        Returns:
            List[str]: List of capabilities
        """
        pass
    
    @abstractmethod
    async def _initialize_agent(self) -> None:
        """Initialize agent-specific resources (implemented by subclasses)."""
        pass
    
    @abstractmethod
    async def _cleanup_agent(self) -> None:
        """Clean up agent-specific resources (implemented by subclasses)."""
        pass
    
    # Helper methods
    
    def _get_agent_config(self) -> Dict[str, Any]:
        """Get agent-specific configuration."""
        agent_config = self.config.get_agent_config()
        return agent_config.get(self.agent_id, {})
    
    def _can_handle_task(self, task: ResearchAction) -> bool:
        """
        Check if agent can handle a specific task.
        
        Args:
            task: Task to check
            
        Returns:
            bool: True if agent can handle the task
        """
        # Check if task action is in agent capabilities
        return task.action in self.capabilities
    
    async def _register_with_mcp(self) -> None:
        """Register agent with MCP server."""
        if not self.mcp_client:
            raise RuntimeError("MCP client not initialized")
        
        registration = AgentRegistration(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            capabilities=self.capabilities,
            max_concurrent=self.max_concurrent_tasks,
            timeout=self.task_timeout
        )
        
        # Send registration message directly to MCP server
        message = {
            'type': 'agent_registration',
            'data': registration.to_dict(),
            'timestamp': datetime.now().isoformat()
        }
        
        if self.mcp_client.websocket:
            await self.mcp_client.websocket.send(json.dumps(message))
            self.logger.info(f"Registered agent {self.agent_id} with MCP server")
        else:
            raise RuntimeError("MCP client not connected")
    
    async def _task_processing_loop(self) -> None:
        """Main task processing loop."""
        # Set up message handler for incoming tasks
        if self.mcp_client:
            self.mcp_client.add_message_handler('research_task', self._handle_incoming_task)
        
        # Initialize heartbeat tracking
        last_heartbeat = datetime.now()
        heartbeat_interval = 15  # Send heartbeat every 15 seconds
        
        while self.is_running:
            try:
                # Keep the agent alive and responsive
                await asyncio.sleep(0.1)
                
                # Send heartbeat periodically
                current_time = datetime.now()
                if (current_time - last_heartbeat).total_seconds() >= heartbeat_interval:
                    await self._send_heartbeat()
                    last_heartbeat = current_time
                
                # Check for agent health
                if self.mcp_client and not self.mcp_client.is_connected:
                    self.logger.warning(f"Agent {self.agent_id} lost connection to MCP server")
                    # Try to reconnect
                    await asyncio.sleep(5)
                    await self.mcp_client.connect()
                    if self.mcp_client.is_connected:
                        await self._register_with_mcp()
                        self.mcp_client.add_message_handler('research_task', self._handle_incoming_task)
                
            except Exception as e:
                self.logger.error(f"Error in task processing loop: {e}")
                await asyncio.sleep(1)
    
    async def _handle_incoming_task(self, task_data: Dict[str, Any]) -> None:
        """Handle incoming task from MCP server."""
        try:
            # Check if this task is for this agent type
            target_agent_type = task_data.get('agent_type')
            if target_agent_type and target_agent_type != self.agent_type:
                return  # Task not for this agent
            
            # Create ResearchAction from task data
            from ..mcp.protocols import ResearchAction
            task = ResearchAction(
                task_id=task_data.get('task_id', ''),
                context_id=task_data.get('context_id', ''),
                agent_type=task_data.get('agent_type', ''),
                action=task_data.get('action', ''),
                payload=task_data.get('payload', {}),
                priority=task_data.get('priority', 'normal'),
                status=task_data.get('status', 'pending')
            )
            
            if task:
                # Process the task
                response = await self.process_task(task)
                
                # Send response back to MCP server
                if self.mcp_client:
                    self.logger.info(f"Sending response for task {response.task_id} with status {response.status}")
                    success = await self.mcp_client.send_response(response)
                    if success:
                        self.logger.info(f"✓ Successfully sent response for task {response.task_id}")
                    else:
                        self.logger.error(f"✗ Failed to send response for task {response.task_id}")
                else:
                    self.logger.error(f"No MCP client available to send response for task {response.task_id}")
            
        except Exception as e:
            self.logger.error(f"Error handling incoming task: {e}")
            # Send error response if possible
            if self.mcp_client and 'task_id' in task_data:
                error_response = AgentResponse(
                    task_id=task_data['task_id'],
                    context_id=task_data.get('context_id', 'unknown'),
                    agent_type=self.agent_type,
                    status="failed",
                    error=f"Task processing error: {str(e)}"
                )
                await self.mcp_client.send_response(error_response)
    
    async def _cancel_task(self, task_id: str) -> None:
        """Cancel an active task."""
        if task_id in self.active_tasks:
            task = self.active_tasks.pop(task_id)
            self.failed_tasks.append(task_id)
            self.logger.info(f"Cancelled task {task_id}")
            
            # Send cancellation response
            if self.mcp_client:
                response = AgentResponse(
                    task_id=task_id,
                    context_id="unknown",
                    agent_type=self.agent_type,
                    status="cancelled"
                )
                await self.mcp_client.send_response(response)
    
    async def _send_heartbeat(self) -> None:
        """Send heartbeat to MCP server to maintain health status."""
        try:
            if self.mcp_client and self.mcp_client.websocket:
                heartbeat_message = {
                    'type': 'agent_heartbeat',
                    'data': {
                        'agent_id': self.agent_id,
                        'timestamp': datetime.now().isoformat(),
                        'status': self.status.value,
                        'active_tasks': len(self.active_tasks)
                    }
                }
                await self.mcp_client.websocket.send(json.dumps(heartbeat_message))
                self.logger.debug(f"Sent heartbeat for agent {self.agent_id}")
        except Exception as e:
            self.logger.warning(f"Failed to send heartbeat: {e}")
