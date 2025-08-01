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
sys.path.append(str(Path(__file__).parent.parent))
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
    task_description: str
    user_id: str
    topic_id: str
    max_results: int = 10
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
    
    # Delegation tracking
    delegated_tasks: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
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
        
        logger.info(f"Research Manager Service initialized on port {self.service_port} - File watching enabled!")
    
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
            "type": "agent_register",
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "capabilities": self.capabilities,
            "timestamp": datetime.now().isoformat(),
            "service_info": {
                    "host": self.service_host,
                    "port": self.service_port,
                    "health_endpoint": f"http://{self.service_host}:{self.service_port}/health"
                }
            
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
                    logger.info(f"Received raw WebSocket message: {message}")
                    data = json.loads(message)
                    logger.info(f"Parsed message data: {data}")
                    await self.task_queue.put(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse MCP message: {e}, raw message: {message}")
                except Exception as e:
                    logger.error(f"Error handling MCP message: {e}, message: {message}")
                    
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
                logger.info("Waiting for task from queue...")
                task_data = await self.task_queue.get()
                logger.info(f"Got task from queue: {task_data}")
                
                # Process the task
                logger.info("Processing research task...")
                result = await self._process_research_task(task_data)
                logger.info(f"Task processing result: {result}")
                
                # Send result back to MCP server (only for actual tasks, not control messages)
                message_type = task_data.get("type", "")
                if self.websocket and self.mcp_connected and message_type not in ["registration_confirmed", "heartbeat", "ping", "pong"]:
                    response = {
                        "type": "task_result",
                        "task_id": task_data.get("task_id"),
                        "agent_id": self.agent_id,
                        "result": result,
                        "status": result.get("status", "completed") if isinstance(result, dict) else "completed"
                    }
                    logger.info(f"Sending response to MCP server: {response}")
                    await self.websocket.send(json.dumps(response))
                elif message_type in ["registration_confirmed", "heartbeat", "ping", "pong"]:
                    logger.info(f"Skipping response for control message: {message_type}")
                
                # Mark task as done
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing task: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                await asyncio.sleep(1)
    
    async def _process_research_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a research coordination task."""
        try:
            # Handle MCP server task format
            task_type = task_data.get("type", "")
            
            logger.info(f"Processing message type: {task_type}")
            logger.info(f"Full task data: {task_data}")
            
            # Handle MCP control messages (don't process as tasks)
            if task_type in ["registration_confirmed", "heartbeat", "ping", "pong"]:
                logger.info(f"Received MCP control message: {task_type}")
                return {
                    "status": "acknowledged",
                    "message_type": task_type,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Handle research_action messages from MCP server
            if task_type == "research_action":
                data = task_data.get("data", {})
                action = data.get("action", "")
                task_id = data.get("task_id", "")
                context_id = data.get("context_id", "")
                payload = data.get("payload", {})
                
                logger.info(f"Processing research action: {action} for task_id: {task_id}")
                
                if action == "coordinate_research":
                    # Add task_id from MCP message structure to payload
                    payload["task_id"] = task_id
                    return await self._handle_coordinate_research(payload)
                elif action == "estimate_costs":
                    return await self._handle_estimate_costs(payload)
                elif action == "track_progress":
                    return await self._handle_track_progress(payload)
                elif action == "delegate_tasks":
                    return await self._handle_delegate_tasks(payload)
                elif action == "manage_workflows":
                    return await self._handle_manage_workflows(payload)
                elif action == "approve_actions":
                    return await self._handle_approve_actions(payload)
                else:
                    return {
                        "status": "failed",
                        "error": f"Unknown research action: {action}",
                        "timestamp": datetime.now().isoformat()
                    }
            
            # Handle task_result messages from delegated agents
            elif task_type == "task_result":
                logger.info(f"Received task result from delegated agent")
                return await self._handle_task_result(task_data)
            
            # Handle legacy formats
            task_id = task_data.get("task_id", "")
            action = task_data.get("task_type", "")
            data = task_data.get("data", {})
            context_id = task_data.get("context_id", "")
            
            # Handle different task types (legacy format)
            if task_type == "task_request" and action == "coordinate_research":
                # Include task_id in data for handler
                data["task_id"] = task_id
                data["context_id"] = context_id
                return await self._handle_coordinate_research(data)
            elif task_type == "task_request" and action == "estimate_costs":
                data["task_id"] = task_id
                return await self._handle_estimate_costs(data)
            elif task_type == "task_request" and action == "track_progress":
                data["task_id"] = task_id
                return await self._handle_track_progress(data)
            elif task_type == "task_request" and action == "delegate_tasks":
                data["task_id"] = task_id
                return await self._handle_delegate_tasks(data)
            elif task_type == "task_request" and action == "manage_workflows":
                data["task_id"] = task_id
                return await self._handle_manage_workflows(data)
            elif task_type == "task_request" and action == "approve_actions":
                data["task_id"] = task_id
                return await self._handle_approve_actions(data)
            elif task_type == "ping":
                return {"status": "alive", "timestamp": datetime.now().isoformat()}
            else:
                # Legacy JSON-RPC format support
                method = task_data.get("method", "")
                params = task_data.get("params", {})
                
                if method == "task/execute":
                    task_type_legacy = params.get("task_type", "")
                    data_legacy = params.get("data", {})
                    
                    if task_type_legacy == "coordinate_research":
                        return await self._handle_coordinate_research(data_legacy)
                    elif task_type_legacy == "estimate_costs":
                        return await self._handle_estimate_costs(data_legacy)
                    elif task_type_legacy == "track_progress":
                        return await self._handle_track_progress(data_legacy)
                    elif task_type_legacy == "delegate_tasks":
                        return await self._handle_delegate_tasks(data_legacy)
                    elif task_type_legacy == "manage_workflows":
                        return await self._handle_manage_workflows(data_legacy)
                    elif task_type_legacy == "approve_actions":
                        return await self._handle_approve_actions(data_legacy)
                    else:
                        return {
                            "status": "failed",
                            "error": f"Unknown task type: {task_type_legacy}",
                            "timestamp": datetime.now().isoformat()
                        }
                elif method == "agent/ping":
                    return {"status": "alive", "timestamp": datetime.now().isoformat()}
                elif method == "agent/status":
                    return await self._get_agent_status()
                else:
                    return {
                        "status": "failed",
                        "error": f"Unknown message format. Task type: {task_type}, Action: {action}, Method: {method}",
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
            # Extract task information from API Gateway payload format
            task_id = data.get("task_id", "")
            
            # Map API Gateway payload to Research Manager expected format
            topic_id = data.get("topic_id", "")
            topic_name = data.get("topic_name", "")
            topic_description = data.get("topic_description", "")
            research_plan = data.get("research_plan", {})
            task_type = data.get("task_type", "research")
            depth = data.get("depth", "standard")

            # API Gateway format - derive parameters from topic data
            task_name = topic_name
            task_description = topic_description
            topic_id = topic_id  # Use topic_id as plan reference
            user_id = "api_user"  # Default for API requests. TODO: Extract from auth context if available
            max_results = 50 if depth == "phd" else 25 if depth == "masters" else 10
            
            if not task_id:
                return {
                    "status": "failed",
                    "error": "Task ID is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            logger.info(f"Coordinating research for task {task_id}")
            logger.info(f"Research plan received: {research_plan}")
            
            # Check if research plan is empty and needs to be fetched from database
            if not research_plan or research_plan == {}:
                logger.info(f"Research plan is empty, attempting to fetch from database using topic_id: {topic_id}")
                research_plan = await self._fetch_research_plan_from_database(topic_id)
                if not research_plan or research_plan == {}:
                    logger.warning(f"No research plan found for topic_id {topic_id}, will delegate to planning agent")
                    research_plan = await self._generate_research_plan(topic_name, topic_description)
            
            logger.info(f"Final research plan for delegation: {research_plan}")
            
            # Create research context using the provided task ID
            context = ResearchContext(
                task_id=task_id,
                task_description=task_description,
                user_id=user_id,
                topic_id=topic_id,
                max_results=max_results
            )
            
            # Add additional context
            context.metadata = {
                "task_name": task_name,
                "task_type": task_type,
                "max_results": max_results,
                "topic_id": topic_id,
                "topic_name": topic_name,
                "research_plan": research_plan,
                "depth": depth
            }
            
            # Store context
            self.active_contexts[task_id] = context
            
            # Start research workflow which will trigger literature search
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
            context.stage = ResearchStage.LITERATURE_REVIEW
            context.updated_at = datetime.now()
            
            # Estimate initial costs
            estimated_cost = await self._estimate_research_costs(context)
            context.estimated_cost = estimated_cost
            
            logger.info(f"Started research workflow for task {context.task_id}")
            
            # Start the complete workflow - literature search first
            literature_result = await self._start_literature_search(context)
            
            # Store literature search results and continue workflow
            if literature_result.get("delegated"):
                # Mark literature stage as initiated
                context.metadata["literature_delegated"] = True
                context.metadata["literature_delegation_id"] = literature_result.get("delegation_id")
                
                logger.info(f"Literature search delegated for task {context.task_id}, workflow will continue upon completion")
                
                return {
                    "workflow_started": True,
                    "initial_stage": context.stage.value,
                    "estimated_cost": estimated_cost,
                    "task_id": context.task_id,
                    "literature_search_status": "delegated",
                    "workflow_status": "literature_search_initiated"
                }
            else:
                logger.error(f"Failed to delegate literature search for task {context.task_id}")
                context.stage = ResearchStage.FAILED
                return {
                    "workflow_started": False,
                    "error": "Failed to delegate literature search"
                }
            
        except Exception as e:
            logger.error(f"Failed to start research workflow: {e}")
            context.stage = ResearchStage.FAILED
            return {
                "workflow_started": False,
                "error": str(e)
            }
    
    async def _start_literature_search(self, context: ResearchContext) -> Dict[str, Any]:
        """Start literature search for the research task."""
        try:
            if not self.websocket or not self.mcp_connected:
                logger.error("Cannot start literature search: MCP connection not available")
                return {"status": "failed", "error": "MCP connection not available"}
            
            # Get the actual research plan from context metadata
            research_plan = context.metadata.get("research_plan", {})
            
            logger.info(f"Starting literature search with research plan: {research_plan}")
            
            # Use the delegation method to properly route through MCP server
            delegation_result = await self._delegate_to_agent(
                task_id=context.task_id,
                agent_type="literature",
                action_data={
                    "action": "search_literature",
                    "lit_review_id": context.task_id,
                    "research_plan": research_plan,  # Use the actual research plan
                    "max_results": context.metadata.get("max_results", 50)
                }
            )
            
            # Track delegation if successful
            if delegation_result.get("delegated"):
                delegation_id = f"literature_search_{delegation_result.get('delegation_id')}"
                context.delegated_tasks[delegation_id] = {
                    "agent_type": "literature_search",
                    "task_id": delegation_result.get("delegation_id"),
                    "action": "search_literature",
                    "status": "in_progress",
                    "started_at": datetime.now().isoformat()
                }
                context.metadata["literature_delegation_id"] = delegation_id
            
            logger.info(f"Literature search delegation result: {delegation_result}")
            
            return delegation_result
            
        except Exception as e:
            logger.error(f"Failed to start literature search: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }

    async def _continue_workflow_after_literature(self, context: ResearchContext, literature_results: Dict[str, Any]) -> Dict[str, Any]:
        """Continue the research workflow after literature search completion."""
        try:
            logger.info(f"Continuing workflow for task {context.task_id} after literature search")
            
            # Store literature search results
            context.search_results = literature_results.get("records", [])
            context.metadata["literature_search_completed"] = True
            context.metadata["literature_results"] = literature_results
            
            # Move to synthesis stage
            context.stage = ResearchStage.SYNTHESIS
            
            # Start synthesis process
            synthesis_result = await self._start_synthesis(context)
            
            if synthesis_result.get("delegated"):
                context.metadata["synthesis_delegated"] = True
                context.metadata["synthesis_delegation_id"] = synthesis_result.get("delegation_id")
                logger.info(f"Synthesis delegated for task {context.task_id}")
                
                return {
                    "workflow_continued": True,
                    "current_stage": context.stage.value,
                    "synthesis_status": "delegated"
                }
            else:
                logger.error(f"Failed to delegate synthesis for task {context.task_id}")
                return {
                    "workflow_continued": False,
                    "error": "Failed to delegate synthesis"
                }
                
        except Exception as e:
            logger.error(f"Failed to continue workflow after literature search: {e}")
            return {
                "workflow_continued": False,
                "error": str(e)
            }

    async def _start_synthesis(self, context: ResearchContext) -> Dict[str, Any]:
        """Start synthesis of literature search results."""
        try:
            if not self.websocket or not self.mcp_connected:
                logger.error("Cannot start synthesis: MCP connection not available")
                return {"status": "failed", "error": "MCP connection not available"}
            
            # Get the actual research plan from context metadata
            research_plan = context.metadata.get("research_plan", {})
            
            # Prepare synthesis payload
            synthesis_payload = {
                "action": "synthesize_evidence",
                "task_id": context.task_id,
                "literature_results": context.search_results,
                "research_plan": research_plan,  # Use the actual research plan
                "synthesis_type": "comprehensive",
                "include_citations": True
            }
            
            # Delegate to synthesis agent
            delegation_result = await self._delegate_to_agent(
                task_id=context.task_id,
                agent_type="synthesis_review",
                action_data=synthesis_payload
            )
            
            # Track delegation if successful
            if delegation_result.get("delegated"):
                delegation_id = f"synthesis_review_{delegation_result.get('delegation_id')}"
                context.delegated_tasks[delegation_id] = {
                    "agent_type": "synthesis_review",
                    "task_id": delegation_result.get("delegation_id"),
                    "action": "synthesize_evidence",
                    "status": "in_progress",
                    "started_at": datetime.now().isoformat()
                }
                context.metadata["synthesis_delegation_id"] = delegation_id
            
            logger.info(f"Synthesis delegation result: {delegation_result}")
            
            return delegation_result
            
        except Exception as e:
            logger.error(f"Failed to start synthesis: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }

    async def _continue_workflow_after_synthesis(self, context: ResearchContext, synthesis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Continue the research workflow after synthesis completion."""
        try:
            logger.info(f"Continuing workflow for task {context.task_id} after synthesis")
            
            # Store synthesis results
            context.synthesis = synthesis_results.get("synthesis", "")
            context.metadata["synthesis_completed"] = True
            context.metadata["synthesis_results"] = synthesis_results
            
            # Move to systematic review stage
            context.stage = ResearchStage.SYSTEMATIC_REVIEW
            
            # Start review process
            review_result = await self._start_review(context)
            
            if review_result.get("delegated"):
                context.metadata["review_delegated"] = True
                context.metadata["review_delegation_id"] = review_result.get("delegation_id")
                logger.info(f"Review delegated for task {context.task_id}")
                
                return {
                    "workflow_continued": True,
                    "current_stage": context.stage.value,
                    "review_status": "delegated"
                }
            else:
                logger.error(f"Failed to delegate review for task {context.task_id}")
                return {
                    "workflow_continued": False,
                    "error": "Failed to delegate review"
                }
                
        except Exception as e:
            logger.error(f"Failed to continue workflow after synthesis: {e}")
            return {
                "workflow_continued": False,
                "error": str(e)
            }

    async def _start_review(self, context: ResearchContext) -> Dict[str, Any]:
        """Start review of synthesized results."""
        try:
            if not self.websocket or not self.mcp_connected:
                logger.error("Cannot start review: MCP connection not available")
                return {"status": "failed", "error": "MCP connection not available"}
            
            # Get the actual research plan from context metadata
            research_plan = context.metadata.get("research_plan", {})
            
            # Prepare review payload
            review_payload = {
                "action": "screen_literature",
                "task_id": context.task_id,
                "literature_results": context.search_results,
                "synthesis_results": context.synthesis,
                "research_plan": research_plan,  # Use the actual research plan
                "review_criteria": {
                    "quality_assessment": True,
                    "relevance_scoring": True,
                    "bias_detection": True
                }
            }
            
            # Delegate to screening agent for review
            delegation_result = await self._delegate_to_agent(
                task_id=context.task_id,
                agent_type="screening",
                action_data=review_payload
            )
            
            # Track delegation if successful
            if delegation_result.get("delegated"):
                delegation_id = f"screening_agent_{delegation_result.get('delegation_id')}"
                context.delegated_tasks[delegation_id] = {
                    "agent_type": "screening_agent",
                    "task_id": delegation_result.get("delegation_id"),
                    "action": "screen_literature",
                    "status": "in_progress",
                    "started_at": datetime.now().isoformat()
                }
                context.metadata["review_delegation_id"] = delegation_id
            
            logger.info(f"Review delegation result: {delegation_result}")
            
            return delegation_result
            
        except Exception as e:
            logger.error(f"Failed to start review: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }

    async def _complete_workflow(self, context: ResearchContext, review_results: Dict[str, Any]) -> Dict[str, Any]:
        """Complete the research workflow."""
        try:
            logger.info(f"Completing workflow for task {context.task_id}")
            
            # Store review results
            context.metadata["review_completed"] = True
            context.metadata["review_results"] = review_results
            context.stage = ResearchStage.COMPLETE
            
            # Compile final results
            final_results = {
                "task_id": context.task_id,
                "workflow_status": "completed",
                "stages_completed": ["literature_search", "synthesis", "review"],
                "literature_results": context.metadata.get("literature_results", {}),
                "synthesis_results": context.metadata.get("synthesis_results", {}),
                "review_results": review_results,
                "total_duration": (datetime.now() - context.created_at).total_seconds(),
                "estimated_cost": context.estimated_cost
            }
            
            logger.info(f"Research workflow completed for task {context.task_id}")
            
            return {
                "workflow_completed": True,
                "final_stage": context.stage.value,
                "results": final_results
            }
            
        except Exception as e:
            logger.error(f"Failed to complete workflow: {e}")
            return {
                "workflow_completed": False,
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
            
            # Create research_action message for delegation
            delegation_message = {
                "type": "research_action",
                "data": {
                    "task_id": str(uuid.uuid4()),
                    "context_id": f"delegation-{task_id}",
                    "agent_type": agent_type,
                    "action": action_data.get("action", "search_literature"),
                    "payload": {
                        **action_data,
                        "delegated_from": self.agent_id,
                        "original_task_id": task_id
                    }
                },
                "client_id": self.agent_id,
                "timestamp": datetime.now().isoformat()
            }
            
            # Send delegation
            await self.websocket.send(json.dumps(delegation_message))
            
            logger.info(f"Delegated task {task_id} to {agent_type} with action {action_data.get('action', 'search_literature')}")
            
            return {
                "delegated": True,
                "target_agent": agent_type,
                "delegation_id": delegation_message["data"]["task_id"]
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
        
        # Adjust based on task description complexity
        description_length = len(context.task_description.split())
        complexity_multiplier = min(description_length / 10, 3.0)
        
        # Adjust based on single agent mode
        mode_multiplier = 0.7 if context.single_agent_mode else 1.0
        
        estimated_cost = base_cost * complexity_multiplier * mode_multiplier
        
        return round(estimated_cost, 2)
    
    async def _start_workflow(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Start a new workflow."""
        try:
            task_description = data.get("task_description", data.get("query", ""))
            user_id = data.get("user_id", "anonymous")
            topic_id = data.get("topic_id", "default_topic")
            max_results = data.get("max_results", 10)
            
            if not task_description:
                return {"error": "Task description is required"}
            
            # Create new context
            task_id = str(uuid.uuid4())
            context = ResearchContext(
                task_id=task_id,
                task_description=task_description,
                user_id=user_id,
                topic_id=topic_id,
                max_results=max_results
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
            "timestamp": datetime.now().isoformat(),
            "mcp_connected": self.mcp_connected,
            "active_tasks": len(self.active_contexts),
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "agent_availability": self.agent_availability,
            "timestamp": datetime.now().isoformat()
        }

    async def _fetch_research_plan_from_database(self, topic_id: str) -> Dict[str, Any]:
        """Fetch research plan from database using topic_id."""
        try:
            if not self.websocket or not self.mcp_connected:
                logger.warning("Cannot fetch research plan: MCP connection not available")
                return {}
            
            # Request database agent to fetch research plan for topic
            db_request = {
                "type": "task",
                "task_id": f"fetch_plan_{uuid.uuid4().hex[:8]}",
                "target_agent": "database_agent",
                "action": "get_approved_plan_for_topic",
                "payload": {
                    "topic_id": topic_id
                },
                "timestamp": datetime.now().isoformat()
            }
            
            await self.websocket.send(json.dumps(db_request))
            logger.info(f"Sent request to fetch research plan for topic {topic_id}")
            
            # Wait for response with timeout
            response_timeout = 10.0  # 10 seconds for database query
            start_time = datetime.now()
            
            while (datetime.now() - start_time).total_seconds() < response_timeout:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    
                    if (data.get("type") == "task_result" and 
                        data.get("task_id") == db_request["task_id"]):
                        
                        result = data.get("result", {})
                        if result.get("status") == "completed":
                            plan_data = result.get("plan_data", {})
                            plan_structure = plan_data.get("plan_structure", {})
                            logger.info(f"Successfully fetched research plan from database: {plan_structure}")
                            return plan_structure
                        else:
                            logger.warning(f"Database agent failed to fetch plan: {result.get('error', 'Unknown error')}")
                            return {}
                        
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Error receiving database response: {e}")
                    break
            
            logger.warning("Timeout waiting for database response")
            return {}
            
        except Exception as e:
            logger.error(f"Error fetching research plan from database: {e}")
            return {}

    async def _generate_research_plan(self, topic_name: str, topic_description: str) -> Dict[str, Any]:
        """Generate a research plan using the planning agent."""
        try:
            if not self.websocket or not self.mcp_connected:
                logger.warning("Cannot generate research plan: MCP connection not available")
                return {}
            
            # Request planning agent to generate research plan
            planning_request = {
                "type": "task",
                "task_id": f"generate_plan_{uuid.uuid4().hex[:8]}",
                "target_agent": "planning_agent",
                "action": "generate_research_plan",
                "payload": {
                    "topic_name": topic_name,
                    "topic_description": topic_description,
                    "plan_type": "literature_review",
                    "depth": "standard"
                },
                "timestamp": datetime.now().isoformat()
            }
            
            await self.websocket.send(json.dumps(planning_request))
            logger.info(f"Sent request to generate research plan for topic: {topic_name}")
            
            # Wait for response with timeout
            response_timeout = 30.0  # 30 seconds for AI planning
            start_time = datetime.now()
            
            while (datetime.now() - start_time).total_seconds() < response_timeout:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    
                    if (data.get("type") == "task_result" and 
                        data.get("task_id") == planning_request["task_id"]):
                        
                        result = data.get("result", {})
                        if result.get("status") == "completed":
                            generated_plan = result.get("research_plan", {})
                            logger.info(f"Successfully generated research plan: {generated_plan}")
                            return generated_plan
                        else:
                            logger.warning(f"Planning agent failed to generate plan: {result.get('error', 'Unknown error')}")
                            return {}
                        
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Error receiving planning agent response: {e}")
                    break
            
            logger.warning("Timeout waiting for planning agent response")
            return {}
            
        except Exception as e:
            logger.error(f"Error generating research plan: {e}")
            return {}

    async def _handle_task_result(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task result from delegated agents and continue workflow."""
        try:
            task_id = task_data.get("task_id")
            agent_id = task_data.get("agent_id")
            result = task_data.get("result", {})
            
            logger.info(f"Received task result from {agent_id} for task {task_id}")
            logger.info(f"Result status: {result.get('status')}")
            
            # Find the context and delegation info for this task result
            found_context = None
            found_delegation_id = None
            found_agent_type = None
            
            # Search through all active contexts to find the matching delegation
            for ctx_task_id, ctx in self.active_contexts.items():
                for delegation_id, delegation_info in ctx.delegated_tasks.items():
                    if delegation_info["task_id"] == task_id:
                        found_context = ctx
                        found_delegation_id = delegation_id
                        found_agent_type = delegation_info["agent_type"]
                        break
                if found_context:
                    break
            
            if not found_context or not found_delegation_id:
                logger.warning(f"No active context found for task result {task_id}")
                return {
                    "status": "acknowledged",
                    "message": "Task result received but no active context found",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Update delegation status
            found_context.delegated_tasks[found_delegation_id]["status"] = "completed"
            found_context.delegated_tasks[found_delegation_id]["result"] = result
            found_context.delegated_tasks[found_delegation_id]["completed_at"] = datetime.now().isoformat()
            
            logger.info(f"Found delegation: {found_delegation_id} for agent type: {found_agent_type}")
            
            # Continue workflow based on current stage and completed delegation
            if found_agent_type == "literature_search" and found_context.stage == ResearchStage.LITERATURE_REVIEW:
                logger.info("Literature search completed, continuing to synthesis")
                await self._continue_workflow_after_literature(found_context, result)
            elif found_agent_type == "synthesis_review" and found_context.stage == ResearchStage.SYNTHESIS:
                logger.info("Synthesis completed, continuing to review")
                await self._continue_workflow_after_synthesis(found_context, result)
            elif found_agent_type == "screening_agent" and found_context.stage == ResearchStage.SYSTEMATIC_REVIEW:
                logger.info("Review completed, finalizing workflow")
                await self._complete_workflow(found_context, result)
            else:
                logger.warning(f"Unexpected task result: agent_type={found_agent_type}, stage={found_context.stage}")
            
            return {
                "status": "acknowledged",
                "message": f"Task result processed for {found_agent_type}",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error handling task result: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "status": "failed",
                "error": str(e),
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
