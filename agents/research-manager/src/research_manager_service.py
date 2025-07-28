"""
Research Manager Service for Eunice Research Platform.

This module provides a containerized Research Manager that coordinates:
- Multi-agent research task orchestration
- Research workflow management
- Cost estimation and approval
- Task delegation and monitoring
- Progress tracking and reporting

ARCHITECTURE COMPLIANCE:
- ONLY exposes health check API endpoint (/health)
- ALL business operations via MCP protocol exclusively
- NO direct HTTP/REST endpoints for business logic
"""

import asyncio
import json
import logging
import uuid
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Union

import uvicorn
import websockets
from fastapi import FastAPI
from websockets.exceptions import ConnectionClosed, WebSocketException

# Import the standardized health check service
sys.path.append(str(Path(__file__).parent.parent.parent))
from health_check_service import create_health_check_app

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
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.mcp_connected = False
        self.should_run = True
        
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
        
        # Capabilities
        self.capabilities = [
            "coordinate_research",
            "estimate_costs",
            "track_progress",
            "delegate_tasks",
            "manage_workflows",
            "approve_actions"
        ]
        
        logger.info(f"Research Manager Service initialized on port {self.service_port}")
    
    async def start(self):
        """Start the Research Manager Service."""
        try:
            # Connect to MCP server
            await self._connect_to_mcp_server()
            
            # Start task processing
            asyncio.create_task(self._process_task_queue())
            
            # Listen for MCP messages
            await self._listen_for_tasks()
            
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
        if not self.websocket:
            raise Exception("WebSocket connection not available")
            
        registration_message = {
            "jsonrpc": "2.0",
            "method": "agent/register",
            "params": {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "capabilities": self.capabilities,
                "service_info": {
                    "host": self.service_host,
                    "port": self.service_port,
                    "health_endpoint": f"http://{self.service_host}:{self.service_port}/health"
                }
            },
            "id": f"register_{self.agent_id}"
        }
        
        await self.websocket.send(json.dumps(registration_message))
        logger.info(f"Registered with MCP server: {len(self.capabilities)} capabilities")
    
    async def _listen_for_tasks(self):
        """Listen for tasks from MCP server."""
        try:
            if not self.websocket:
                logger.error("Cannot listen for tasks: no websocket connection")
                return
                
            logger.info("Starting to listen for tasks from MCP server")
            
            async for message in self.websocket:
                if not self.should_run:
                    break
                    
                try:
                    data = json.loads(message)
                    await self.task_queue.put(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse MCP message: {e}")
                except Exception as e:
                    logger.error(f"Error handling MCP message: {e}")
                    
        except ConnectionClosed:
            logger.warning("MCP server connection closed")
            self.mcp_connected = False
        except WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            self.mcp_connected = False
        except Exception as e:
            logger.error(f"Unexpected error in message listener: {e}")
            self.mcp_connected = False
    
    async def _process_task_queue(self):
        """Process tasks from the MCP queue."""
        while self.should_run:
            try:
                # Get task from queue
                task_data = await self.task_queue.get()
                
                # Process the task
                result = await self._process_research_task(task_data)
                
                # Send result back to MCP server
                if self.websocket and self.mcp_connected:
                    response = {
                        "jsonrpc": "2.0",
                        "id": task_data.get("id"),
                        "result": result
                    }
                    await self.websocket.send(json.dumps(response))
                
                # Mark task as done
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing task: {e}")
                await asyncio.sleep(1)
    
    async def _process_research_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a research coordination task."""
        try:
            method = task_data.get("method", "")
            params = task_data.get("params", {})
            
            # Route to appropriate handler
            if method == "task/execute":
                task_type = params.get("task_type", "")
                data = params.get("data", {})
                
                if task_type == "coordinate_research":
                    return await self._handle_coordinate_research(data)
                elif task_type == "estimate_costs":
                    return await self._handle_estimate_costs(data)
                elif task_type == "track_progress":
                    return await self._handle_track_progress(data)
                elif task_type == "delegate_tasks":
                    return await self._handle_delegate_tasks(data)
                elif task_type == "manage_workflows":
                    return await self._handle_manage_workflows(data)
                elif task_type == "approve_actions":
                    return await self._handle_approve_actions(data)
                else:
                    return {
                        "status": "failed",
                        "error": f"Unknown task type: {task_type}",
                        "timestamp": datetime.now().isoformat()
                    }
            elif method == "agent/ping":
                return {"status": "alive", "timestamp": datetime.now().isoformat()}
            elif method == "agent/status":
                return await self._get_agent_status()
            else:
                return {
                    "status": "failed",
                    "error": f"Unknown method: {method}",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error processing research task: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_coordinate_research(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle research coordination request."""
        try:
            query = data.get("query", "")
            user_id = data.get("user_id", "anonymous")
            project_id = data.get("project_id")
            single_agent_mode = data.get("single_agent_mode", False)
            
            if not query:
                return {
                    "status": "failed",
                    "error": "Query is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Create research context
            task_id = str(uuid.uuid4())
            context = ResearchContext(
                task_id=task_id,
                query=query,
                user_id=user_id,
                project_id=project_id,
                single_agent_mode=single_agent_mode
            )
            
            # Store context
            self.active_contexts[task_id] = context
            
            # Start research workflow
            workflow_result = await self._start_research_workflow(context)
            
            return {
                "status": "completed",
                "task_id": task_id,
                "workflow_result": workflow_result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to coordinate research: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_estimate_costs(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle cost estimation request."""
        try:
            task_id = data.get("task_id", "")
            operations = data.get("operations", [])
            
            if not task_id:
                return {
                    "status": "failed",
                    "error": "Task ID is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Calculate estimated costs
            total_cost = await self._calculate_operation_costs(operations)
            
            return {
                "status": "completed",
                "task_id": task_id,
                "estimated_cost": total_cost,
                "operations": operations,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to estimate costs: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_track_progress(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle progress tracking request."""
        try:
            task_id = data.get("task_id", "")
            
            if not task_id:
                return {
                    "status": "failed",
                    "error": "Task ID is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Get task progress
            context = self.active_contexts.get(task_id)
            if not context:
                return {
                    "status": "failed",
                    "error": f"Task {task_id} not found",
                    "timestamp": datetime.now().isoformat()
                }
            
            progress = await self._get_task_progress(context)
            
            return {
                "status": "completed",
                "task_id": task_id,
                "progress": progress,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to track progress: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_delegate_tasks(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task delegation request."""
        try:
            task_id = data.get("task_id", "")
            agent_type = data.get("agent_type", "")
            action_data = data.get("action_data", {})
            
            if not all([task_id, agent_type]):
                return {
                    "status": "failed",
                    "error": "Task ID and agent type are required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Delegate task to agent
            result = await self._delegate_to_agent(task_id, agent_type, action_data)
            
            return {
                "status": "completed",
                "task_id": task_id,
                "agent_type": agent_type,
                "delegation_result": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to delegate tasks: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_manage_workflows(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle workflow management request."""
        try:
            operation = data.get("operation", "")
            task_id = data.get("task_id", "")
            
            if not operation:
                return {
                    "status": "failed",
                    "error": "Operation is required",
                    "available_operations": ["start", "pause", "resume", "cancel", "status"],
                    "timestamp": datetime.now().isoformat()
                }
            
            if operation == "start":
                result = await self._start_workflow(data)
            elif operation == "pause":
                result = await self._pause_workflow(task_id)
            elif operation == "resume":
                result = await self._resume_workflow(task_id)
            elif operation == "cancel":
                result = await self._cancel_task(task_id)
            elif operation == "status":
                result = await self._get_workflow_status(task_id)
            else:
                return {
                    "status": "failed",
                    "error": f"Unknown operation: {operation}",
                    "available_operations": ["start", "pause", "resume", "cancel", "status"],
                    "timestamp": datetime.now().isoformat()
                }
            
            return {
                "status": "completed",
                "operation": operation,
                "task_id": task_id,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to manage workflows: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_approve_actions(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle action approval request."""
        try:
            task_id = data.get("task_id", "")
            action_id = data.get("action_id", "")
            approved = data.get("approved", False)
            
            if not all([task_id, action_id]):
                return {
                    "status": "failed",
                    "error": "Task ID and action ID are required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Process approval
            result = await self._process_approval(task_id, action_id, approved)
            
            return {
                "status": "completed",
                "task_id": task_id,
                "action_id": action_id,
                "approved": approved,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to approve actions: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _start_research_workflow(self, context: ResearchContext) -> Dict[str, Any]:
        """Start the research workflow for a task."""
        try:
            # Initialize workflow state
            context.stage = ResearchStage.PLANNING
            context.updated_at = datetime.now()
            
            # Estimate initial costs
            estimated_cost = await self._estimate_research_costs(context)
            context.estimated_cost = estimated_cost
            
            logger.info(f"Started research workflow for task {context.task_id}")
            
            return {
                "workflow_started": True,
                "initial_stage": context.stage.value,
                "estimated_cost": estimated_cost,
                "task_id": context.task_id
            }
            
        except Exception as e:
            logger.error(f"Failed to start research workflow: {e}")
            context.stage = ResearchStage.FAILED
            return {
                "workflow_started": False,
                "error": str(e)
            }
    
    async def _calculate_operation_costs(self, operations: List[Dict[str, Any]]) -> float:
        """Calculate estimated costs for operations."""
        total_cost = 0.0
        
        # Simple cost estimation based on operation types
        cost_per_operation = {
            "literature_search": 0.05,
            "reasoning": 0.10,
            "code_execution": 0.15,
            "synthesis": 0.08,
            "systematic_review": 0.20
        }
        
        for operation in operations:
            op_type = operation.get("type", "unknown")
            quantity = operation.get("quantity", 1)
            
            unit_cost = cost_per_operation.get(op_type, 0.10)
            total_cost += unit_cost * quantity
        
        return total_cost
    
    async def _get_task_progress(self, context: ResearchContext) -> Dict[str, Any]:
        """Get progress information for a task."""
        total_stages = len(ResearchStage) - 2  # Exclude COMPLETE and FAILED
        completed_stages = len(context.completed_stages)
        failed_stages = len(context.failed_stages)
        
        progress_percentage = (completed_stages / total_stages) * 100 if total_stages > 0 else 0
        
        return {
            "task_id": context.task_id,
            "current_stage": context.stage.value,
            "progress_percentage": progress_percentage,
            "completed_stages": [stage.value for stage in context.completed_stages],
            "failed_stages": [stage.value for stage in context.failed_stages],
            "retry_count": context.retry_count,
            "estimated_cost": context.estimated_cost,
            "actual_cost": context.actual_cost,
            "created_at": context.created_at.isoformat(),
            "updated_at": context.updated_at.isoformat()
        }
    
    async def _delegate_to_agent(self, task_id: str, agent_type: str, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate a task to a specific agent via MCP."""
        try:
            if not self.websocket or not self.mcp_connected:
                raise Exception("MCP connection not available")
            
            # Create delegation message
            delegation_message = {
                "jsonrpc": "2.0",
                "method": "task/delegate",
                "params": {
                    "task_id": task_id,
                    "target_agent": agent_type,
                    "action_data": action_data,
                    "from_agent": self.agent_id
                },
                "id": f"delegate_{task_id}_{agent_type}"
            }
            
            # Send delegation
            await self.websocket.send(json.dumps(delegation_message))
            
            logger.info(f"Delegated task {task_id} to {agent_type}")
            
            return {
                "delegated": True,
                "target_agent": agent_type,
                "delegation_id": delegation_message["id"]
            }
            
        except Exception as e:
            logger.error(f"Failed to delegate to agent {agent_type}: {e}")
            return {
                "delegated": False,
                "error": str(e)
            }
    
    async def _estimate_research_costs(self, context: ResearchContext) -> float:
        """Estimate costs for a research task."""
        base_cost = 0.50
        
        # Adjust based on query complexity
        query_length = len(context.query.split())
        complexity_multiplier = min(query_length / 10, 3.0)
        
        # Adjust based on single agent mode
        mode_multiplier = 0.7 if context.single_agent_mode else 1.0
        
        estimated_cost = base_cost * complexity_multiplier * mode_multiplier
        
        return round(estimated_cost, 2)
    
    async def _start_workflow(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Start a new workflow."""
        try:
            query = data.get("query", "")
            user_id = data.get("user_id", "anonymous")
            
            if not query:
                return {"error": "Query is required"}
            
            # Create new context
            task_id = str(uuid.uuid4())
            context = ResearchContext(
                task_id=task_id,
                query=query,
                user_id=user_id
            )
            
            self.active_contexts[task_id] = context
            
            # Start workflow
            workflow_result = await self._start_research_workflow(context)
            
            return {
                "started": True,
                "task_id": task_id,
                "workflow_result": workflow_result
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _pause_workflow(self, task_id: str) -> Dict[str, Any]:
        """Pause a workflow."""
        try:
            context = self.active_contexts.get(task_id)
            if not context:
                return {"error": f"Task {task_id} not found"}
            
            # Simple pause implementation - would need more sophisticated state management
            logger.info(f"Paused workflow for task {task_id}")
            
            return {"paused": True, "task_id": task_id}
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _resume_workflow(self, task_id: str) -> Dict[str, Any]:
        """Resume a workflow."""
        try:
            context = self.active_contexts.get(task_id)
            if not context:
                return {"error": f"Task {task_id} not found"}
            
            # Simple resume implementation
            logger.info(f"Resumed workflow for task {task_id}")
            
            return {"resumed": True, "task_id": task_id}
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _cancel_task(self, task_id: str) -> Dict[str, Any]:
        """Cancel a task."""
        try:
            context = self.active_contexts.get(task_id)
            if not context:
                return {"error": f"Task {task_id} not found"}
            
            # Update context state
            context.stage = ResearchStage.FAILED
            context.updated_at = datetime.now()
            
            # Remove from active contexts
            del self.active_contexts[task_id]
            
            logger.info(f"Cancelled task {task_id}")
            
            return {"cancelled": True, "task_id": task_id}
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_workflow_status(self, task_id: str) -> Dict[str, Any]:
        """Get workflow status."""
        try:
            context = self.active_contexts.get(task_id)
            if not context:
                return {"error": f"Task {task_id} not found"}
            
            return await self._get_task_progress(context)
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _process_approval(self, task_id: str, action_id: str, approved: bool) -> Dict[str, Any]:
        """Process an approval decision."""
        try:
            context = self.active_contexts.get(task_id)
            if not context:
                return {"error": f"Task {task_id} not found"}
            
            # Simple approval processing
            if approved:
                logger.info(f"Approved action {action_id} for task {task_id}")
                return {"processed": True, "approved": True}
            else:
                logger.info(f"Rejected action {action_id} for task {task_id}")
                return {"processed": True, "approved": False}
                
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_agent_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": "ready" if self.mcp_connected else "disconnected",
            "capabilities": self.capabilities,
            "mcp_connected": self.mcp_connected,
            "active_tasks": len(self.active_contexts),
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "agent_availability": self.agent_availability,
            "timestamp": datetime.now().isoformat()
        }


# Global service instance
research_manager_service: Optional[ResearchManagerService] = None


def get_mcp_status() -> Dict[str, Any]:
    """Get MCP connection status for health check."""
    if research_manager_service:
        return {
            "connected": research_manager_service.mcp_connected,
            "last_heartbeat": datetime.now().isoformat()
        }
    return {"connected": False, "last_heartbeat": "never"}


def get_additional_metadata() -> Dict[str, Any]:
    """Get additional metadata for health check."""
    if research_manager_service:
        return {
            "capabilities": research_manager_service.capabilities,
            "active_tasks": len(research_manager_service.active_contexts),
            "max_concurrent_tasks": research_manager_service.max_concurrent_tasks,
            "agent_id": research_manager_service.agent_id
        }
    return {}


# Create health check only FastAPI application
app = create_health_check_app(
    agent_type="research_manager",
    agent_id="research-manager-agent",
    version="1.0.0",
    get_mcp_status=get_mcp_status,
    get_additional_metadata=get_additional_metadata
)


async def main():
    """Main entry point for the research manager agent service."""
    global research_manager_service
    
    try:
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
                "task_timeout": 600
            }
        
        # Initialize service
        research_manager_service = ResearchManagerService(config)
        
        # Start FastAPI health check server in background
        config_uvicorn = uvicorn.Config(
            app,
            host=config["service_host"],
            port=config["service_port"],
            log_level="info"
        )
        server = uvicorn.Server(config_uvicorn)
        
        logger.info("🚨 ARCHITECTURE COMPLIANCE: Research Manager Agent")
        logger.info("✅ ONLY health check API exposed")
        logger.info("✅ All business operations via MCP protocol exclusively")
        
        # Start server and MCP service concurrently
        await asyncio.gather(
            server.serve(),
            research_manager_service.start()
        )
        
    except KeyboardInterrupt:
        logger.info("Research manager agent shutdown requested")
    except Exception as e:
        logger.error(f"Research manager agent failed: {e}")
        sys.exit(1)
    finally:
        if research_manager_service:
            await research_manager_service.stop()


if __name__ == "__main__":
    asyncio.run(main())
