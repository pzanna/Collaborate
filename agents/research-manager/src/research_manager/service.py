"""
Main Research Manager Service module.

This module coordinates all the modular components to provide a complete
research workflow orchestration service via MCP protocol.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List

from .models import ResearchContext
from .mcp_communicator import MCPCommunicator
from .task_handlers import TaskHandlers, TaskProcessor, WorkflowOrchestrator

logger = logging.getLogger(__name__)


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
        
        # Service state
        self.should_run = True
        
        # Active research contexts
        self.active_contexts: Dict[str, ResearchContext] = {}
        
        # Agent capabilities and availability
        self.agent_capabilities: Dict[str, List[str]] = {}
        self.agent_availability: Dict[str, bool] = {}
        
        # Callbacks for UI updates
        self.progress_callbacks: List[Callable] = []
        self.completion_callbacks: List[Callable] = []

        # Capabilities
        self.capabilities = [
            "coordinate_research",
            "estimate_costs",
            "track_progress",
            "delegate_tasks",
            "manage_workflows",
            "approve_actions"
        ]
        
        # Initialize modular components
        self.mcp_communicator = MCPCommunicator(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            mcp_server_url=self.mcp_server_url,
            capabilities=self.capabilities
        )
        
        self.task_handlers = TaskHandlers(self)
        self.task_processor = TaskProcessor(self)
        self.workflow_orchestrator = WorkflowOrchestrator(self)
        
        logger.info(f"Research Manager Service initialized on port {self.service_port} - File watching enabled!")
    
    async def start(self):
        """Start the Research Manager Service."""
        try:
            # Connect to MCP server
            await self.mcp_communicator.connect_to_mcp_server()
            
            # Start task processing
            asyncio.create_task(self._process_task_queue())
            
            # Listen for MCP messages
            await self.mcp_communicator.listen_for_tasks()
            
            logger.info("Research Manager Service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Research Manager Service: {e}")
            raise
    
    async def stop(self):
        """Stop the Research Manager Service."""
        try:
            self.should_run = False
            
            # Cancel all active tasks
            for task_id in list(self.active_contexts.keys()):
                await self._cancel_task(task_id)
            
            # Close MCP connection
            await self.mcp_communicator.close()
            
            logger.info("Research Manager Service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping Research Manager Service: {e}")
    
    async def _process_task_queue(self):
        """Process tasks from the MCP queue."""
        while self.should_run:
            try:
                # Get task from queue
                logger.info("Waiting for task from queue...")
                task_data = await self.mcp_communicator.task_queue.get()
                logger.info(f"Got task from queue: {task_data}")
                
                # Process the task
                logger.info("Processing research task...")
                result = await self.task_processor.process_task(task_data)
                logger.info(f"Task processing result: {result}")
                
                # Send result back to MCP server
                await self.mcp_communicator.send_response(task_data, result)
                
                # Mark task as done
                self.mcp_communicator.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing task: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                await asyncio.sleep(1)
    
    async def _cancel_task(self, task_id: str) -> Dict[str, Any]:
        """Cancel a task."""
        try:
            context = self.active_contexts.get(task_id)
            if not context:
                return {"error": f"Task {task_id} not found"}
            
            # Update context state
            from .models import ResearchStage
            context.stage = ResearchStage.FAILED
            context.updated_at = datetime.now()
            
            # Remove from active contexts
            del self.active_contexts[task_id]
            
            logger.info(f"Cancelled task {task_id}")
            
            return {"cancelled": True, "task_id": task_id}
            
        except Exception as e:
            return {"error": str(e)}
