"""
MCP Server Implementation

The core Message Control Protocol server that coordinates communication
between agents in the research system using standard agent registration.
"""

import asyncio
import json
import logging
import os
import signal
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import websockets

from .protocols import (AgentRegistration, AgentResponse, ResearchAction)
from .queue import TaskQueue
from .registry import AgentRegistry
from .structured_logger import get_mcp_logger, LogLevel, LogEvent
from .load_balancer import EnhancedLoadBalancer, LoadBalanceStrategy

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from config.config_manager import ConfigManager
except ImportError:
    # Fallback for test environment
    from old_src.config.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class MCPServer:
    """Message Control Protocol Server"""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager

        # Initialize logging configuration first to ensure AI API logging works
        config_manager.setup_logging()

        # Load config with fallback
        try:
            self.config = config_manager.config.mcp_server
        except AttributeError:
            # Fallback configuration
            class FallbackConfig:
                def __init__(self):
                    self.host = "127.0.0.1"
                    self.port = 9000
                    self.max_concurrent_tasks = 10
                    self.task_timeout = 300
                    self.retry_attempts = 3
                    self.log_level = "INFO"

            self.config = FallbackConfig()

        # Initialize structured logger
        self.logger = get_mcp_logger("server", self.config.log_level, self.config_manager)
        
        # Initialize task-specific logger for mcp_tasks.log
        self.task_logger = get_mcp_logger("tasks", self.config.log_level, self.config_manager, "logs/mcp_tasks.log")

        # Core components
        self.agent_registry = AgentRegistry(heartbeat_timeout=30)

        # Get queue size with fallback
        try:
            max_queue_size = config_manager.config.research_tasks.max_task_queue_size
        except AttributeError:
            max_queue_size = 50

        self.task_queue = TaskQueue(
            max_size=max_queue_size, retry_attempts=self.config.retry_attempts
        )

        # Initialize enhanced load balancer
        load_balance_strategy = getattr(config_manager.config, 'load_balance_strategy', 'adaptive')
        try:
            strategy = LoadBalanceStrategy(load_balance_strategy)
        except ValueError:
            strategy = LoadBalanceStrategy.ADAPTIVE
            
        self.load_balancer = EnhancedLoadBalancer(
            agent_registry=self.agent_registry,
            strategy=strategy,
            health_check_interval=30,
            circuit_breaker_enabled=True
        )

        # Connection management
        self.clients: Dict[str, Any] = {}
        self.agent_to_client: Dict[str, str] = {}  # agent_id -> client_id mapping
        self.client_to_agent: Dict[str, str] = {}  # client_id -> agent_id mapping

        # Server state
        self.is_running = False
        self.server: Optional[Any] = None
        self._background_tasks: List[asyncio.Task] = []

        # Statistics
        self.stats = {
            "started_at": datetime.now(),
            "total_tasks_processed": 0,
            "total_messages_sent": 0,
            "total_messages_received": 0,
            "total_agents_registered": 0,
        }

    async def start(self):
        """Start the MCP server"""
        try:
            # Set running flag first
            self.is_running = True

            # Start background tasks
            await self._start_background_tasks()

            # Start enhanced load balancer
            await self.load_balancer.start()

            # Start WebSocket server
            self.server = await websockets.serve(
                self._handle_client,
                self.config.host,
                self.config.port,
                ping_interval=30,
                ping_timeout=60,
            )

            self.logger.log_server_lifecycle("start", {
                "host": self.config.host,
                "port": self.config.port
            })

            # Set up signal handlers
            self._setup_signal_handlers()

        except Exception as e:
            self.logger.log_error(f"Failed to start MCP server: {e}")
            self.is_running = False  # Reset on error
            raise

    async def stop(self):
        """Stop the MCP server"""
        self.logger.log_server_lifecycle("stop")

        self.is_running = False

        # Stop enhanced load balancer
        await self.load_balancer.stop()

        # Stop background tasks
        for task in self._background_tasks:
            task.cancel()

        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

        # Close all client connections
        if self.clients:
            await asyncio.gather(
                *[client.close() for client in self.clients.values()],
                return_exceptions=True,
            )

        # Stop WebSocket server
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        # Stop registry cleanup
        await self.agent_registry.stop_cleanup_task()

        self.logger.log_server_lifecycle("stop", {"graceful": True})

    async def _start_background_tasks(self):
        """Start background tasks"""
        # Start agent registry cleanup
        await self.agent_registry.start_cleanup_task()

        # Start task processing
        self._background_tasks.append(asyncio.create_task(self._process_tasks()))

        # Start periodic cleanup
        self._background_tasks.append(asyncio.create_task(self._periodic_cleanup()))

    async def _handle_client(self, websocket):
        """Handle new client connection"""
        client_id = str(uuid.uuid4())
        self.clients[client_id] = websocket

        self.logger.log_client_connect(client_id, "websocket")

        try:
            await websocket.send(
                json.dumps(
                    {
                        "type": "connection_established",
                        "data": {"client_id": client_id},
                        "timestamp": datetime.now().isoformat(),
                    },
                    default=str,
                )
            )

            async for message in websocket:
                try:
                    data = json.loads(message)
                    self.logger.log_event(
                        LogLevel.DEBUG,
                        LogEvent.CLIENT_CONNECT,
                        f"Received message from client {client_id}: type={data.get('type', 'unknown')}",
                        client_id=client_id,
                        message_type=data.get('type', 'unknown')
                    )
                    await self._handle_message(client_id, data)
                    self.stats["total_messages_received"] += 1
                except json.JSONDecodeError:
                    self.logger.log_error(f"Invalid JSON from client {client_id}", client_id=client_id)
                except Exception as e:
                    self.logger.log_error(f"Error handling message from {client_id}: {e}", client_id=client_id)

        except websockets.exceptions.ConnectionClosed:
            self.logger.log_client_disconnect(client_id, "connection_closed")
        except Exception as e:
            self.logger.log_error(f"Error with client {client_id}: {e}", client_id=client_id)
        finally:
            # Clean up client
            if client_id in self.clients:
                del self.clients[client_id]

            # Clean up agent mapping if this was an agent
            if client_id in self.client_to_agent:
                agent_id = self.client_to_agent[client_id]

                # Unregister agent
                await self.agent_registry.unregister_agent(agent_id)

                # Clean up mappings
                del self.client_to_agent[client_id]
                if agent_id in self.agent_to_client:
                    del self.agent_to_client[agent_id]

                self.logger.log_event(
                    LogLevel.INFO,
                    LogEvent.CLIENT_DISCONNECT,
                    f"Unregistered agent {agent_id} due to client disconnect",
                    client_id=client_id,
                    agent_id=agent_id
                )

    async def _handle_message(self, client_id: str, message: Dict[str, Any]):
        """Handle incoming message from client"""
        message_type = message.get("type")
        message_data = message.get("data", {})

        self.logger.log_event(
            LogLevel.DEBUG,
            LogEvent.CLIENT_CONNECT,
            f"Processing message type '{message_type}' from client {client_id}",
            client_id=client_id,
            message_type=message_type
        )

        if message_type == "research_action":
            await self._handle_research_action(client_id, message_data)
        elif message_type == "agent_response":
            self.logger.log_event(
                LogLevel.DEBUG,
                LogEvent.CLIENT_CONNECT,
                f"Calling _handle_agent_response for client {client_id}",
                client_id=client_id
            )
            await self._handle_agent_response(client_id, message_data)
        elif message_type == "agent_registration":
            await self._handle_agent_registration(client_id, message_data)
        elif message_type == "agent_heartbeat":
            await self._handle_agent_heartbeat(client_id, message_data)
        elif message_type == "heartbeat":
            await self._handle_heartbeat(client_id, message_data)
        elif message_type == "cancel_task":
            await self._handle_cancel_task(client_id, message_data)
        elif message_type == "get_task_status":
            await self._handle_get_task_status(client_id, message_data)
        elif message_type == "get_server_stats":
            await self._handle_get_server_stats(client_id, message_data)
        elif message_type == "get_active_tasks":
            await self._handle_get_active_tasks(client_id, message_data)
        elif message_type == "get_task_details":
            await self._handle_get_task_details(client_id, message_data)
        else:
            self.logger.log_error(f"Unknown message type from {client_id}: {message_type}", 
                                  client_id=client_id, message_type=message_type)

    async def _handle_research_action(self, client_id: str, data: Dict[str, Any]):
        """Handle research action from any registered agent"""
        try:
            action = ResearchAction.from_dict(data)

            # Add to task queue
            success = await self.task_queue.add_task(action)

            if success:
                self.logger.log_event(
                    LogLevel.INFO,
                    LogEvent.TASK_DISPATCH,
                    f"Added task {action.task_id} to queue",
                    task_id=action.task_id,
                    client_id=client_id
                )
                # Log task queuing to task logger
                self.task_logger.log_event(
                    LogLevel.INFO, 
                    LogEvent.TASK_DISPATCH,
                    f"Task {action.task_id} queued for {action.agent_type}",
                    task_id=action.task_id,
                    agent_type=action.agent_type,
                    action=action.action,
                    client_id=client_id
                )
                self.stats["total_tasks_processed"] += 1

                # Send acknowledgment
                await self._send_to_client(
                    client_id,
                    {
                        "type": "task_queued",
                        "data": {"task_id": action.task_id, "status": "queued"},
                    },
                )
            else:
                # Log task rejection to task logger
                self.task_logger.log_event(
                    LogLevel.ERROR,
                    LogEvent.QUEUE_OVERFLOW,
                    f"Task {action.task_id} rejected - queue full",
                    task_id=action.task_id,
                    agent_type=action.agent_type,
                    client_id=client_id
                )
                # Send error
                await self._send_to_client(
                    client_id,
                    {
                        "type": "task_rejected",
                        "data": {"task_id": action.task_id, "error": "Task queue full"},
                    },
                )

        except Exception as e:
            self.logger.log_error(f"Error handling research action: {e}", client_id=client_id)
            self.task_logger.log_error(
                f"Error handling research action: {e}",
                client_id=client_id
            )

    async def _handle_agent_response(self, client_id: str, data: Dict[str, Any]):
        """Handle response from agent"""
        try:
            self.logger.log_event(
                LogLevel.DEBUG,
                LogEvent.CLIENT_CONNECT,
                f"Received response from client {client_id}",
                client_id=client_id
            )
            response = AgentResponse.from_dict(data)
            self.logger.log_event(
                LogLevel.INFO,
                LogEvent.TASK_COMPLETION,
                f"Received response for task {response.task_id} from agent {response.agent_type}",
                task_id=response.task_id,
                agent_type=response.agent_type
            )

            # Get agent ID from client mapping
            agent_id = self.client_to_agent.get(client_id)
            if agent_id:
                # Update agent registry to mark task as complete
                await self.agent_registry.complete_task(agent_id, response.task_id)
                self.logger.log_event(
                    LogLevel.DEBUG,
                    LogEvent.TASK_COMPLETION,
                    f"Marked task {response.task_id} as complete for agent {agent_id}",
                    task_id=response.task_id,
                    agent_id=agent_id
                )
                
                # Record success/failure metrics with load balancer
                if response.status == "completed":
                    await self.load_balancer.record_request_success(
                        agent_id, response.task_id, response
                    )
                elif response.status == "failed":
                    error = Exception(response.error or "Task failed")
                    await self.load_balancer.record_request_failure(
                        agent_id, response.task_id, error
                    )

            # Mark task as completed or failed and log to task logger
            if response.status == "completed":
                await self.task_queue.complete_task(response.task_id, response.result)
                self.logger.log_event(
                    LogLevel.INFO,
                    LogEvent.TASK_COMPLETION,
                    f"Task {response.task_id} marked as completed",
                    task_id=response.task_id
                )
                
                # Log successful completion to task logger
                self.task_logger.log_task_completion(
                    response.task_id,
                    response.context_id or "unknown",
                    response.agent_type,
                    duration=0.0,  # Duration would need to be calculated from task start time
                    success=True,
                    agent_id=agent_id
                )
                
            elif response.status == "failed":
                await self.task_queue.fail_task(
                    response.task_id, response.error or "Unknown error"
                )
                self.logger.log_event(
                    LogLevel.ERROR,
                    LogEvent.TASK_FAILURE,
                    f"Task {response.task_id} marked as failed",
                    task_id=response.task_id,
                    error=response.error
                )
                
                # Log failure to task logger
                self.task_logger.log_event(
                    LogLevel.ERROR,
                    LogEvent.TASK_FAILURE,
                    f"Task {response.task_id} failed: {response.error or 'Unknown error'}",
                    task_id=response.task_id,
                    agent_type=response.agent_type,
                    agent_id=agent_id,
                    error=response.error
                )

            self.logger.log_event(
                LogLevel.INFO,
                LogEvent.TASK_COMPLETION,
                f"Successfully processed response for task {response.task_id}",
                task_id=response.task_id
            )

        except Exception as e:
            self.logger.log_error(f"Error handling agent response: {e}", client_id=client_id)
            self.task_logger.log_error(
                f"Error handling agent response: {e}",
                client_id=client_id
            )

    async def _handle_agent_registration(self, client_id: str, data: Dict[str, Any]):
        """Handle agent registration"""
        try:
            registration = AgentRegistration.from_dict(data)

            # Register agent
            success = await self.agent_registry.register_agent(registration)

            if success:
                # Track agent-to-client mapping
                self.agent_to_client[registration.agent_id] = client_id
                self.client_to_agent[client_id] = registration.agent_id

                self.stats["total_agents_registered"] += 1
                self.logger.log_agent_registration(
                    registration.agent_id,
                    registration.agent_type,
                    registration.capabilities,
                    success=True,
                    client_id=client_id
                )

                # Send acknowledgment
                await self._send_to_client(
                    client_id,
                    {
                        "type": "registration_confirmed",
                        "data": {"agent_id": registration.agent_id},
                    },
                )
            else:
                # Send error
                await self._send_to_client(
                    client_id,
                    {
                        "type": "registration_failed",
                        "data": {"agent_id": registration.agent_id},
                    },
                )

        except Exception as e:
            logger.error(f"Error handling agent registration: {e}")

    async def _handle_heartbeat(self, client_id: str, data: Dict[str, Any]):
        """Handle heartbeat from agent"""
        agent_id = data.get("agent_id")
        if agent_id:
            await self.agent_registry.update_heartbeat(agent_id)

    async def _handle_agent_heartbeat(self, client_id: str, data: Dict[str, Any]):
        """Handle agent heartbeat to maintain health status"""
        try:
            agent_id = data.get("agent_id")
            if agent_id:
                await self.agent_registry.update_heartbeat(agent_id)
                logger.debug(f"Updated heartbeat for agent {agent_id}")
        except Exception as e:
            logger.error(f"Error handling agent heartbeat: {e}")

    async def _handle_cancel_task(self, client_id: str, data: Dict[str, Any]):
        """Handle task cancellation request"""
        task_id = data.get("task_id")
        if task_id:
            success = await self.task_queue.cancel_task(task_id)

            await self._send_to_client(
                client_id,
                {
                    "type": "task_cancelled" if success else "cancel_failed",
                    "data": {"task_id": task_id},
                },
            )

    async def _handle_get_task_status(self, client_id: str, data: Dict[str, Any]):
        """Handle task status request"""
        task_id = data.get("task_id")
        response_id = data.get("response_id")

        if task_id and response_id:
            status = await self.task_queue.get_task_status(task_id)

            await self._send_to_client(
                client_id,
                {
                    "type": "task_status_response",
                    "data": {"response_id": response_id, "task_status": status},
                },
            )

    async def _handle_get_server_stats(self, client_id: str, data: Dict[str, Any]):
        """Handle server statistics request"""
        response_id = data.get("response_id")

        if response_id:
            # Get combined stats
            queue_stats = await self.task_queue.get_queue_stats()
            registry_stats = await self.agent_registry.get_stats()

            combined_stats = {
                **self.stats,
                "queue": queue_stats,
                "agents": registry_stats,
                "uptime_seconds": (
                    datetime.now()-self.stats["started_at"]
                ).total_seconds(),
            }

            await self._send_to_client(
                client_id,
                {
                    "type": "server_stats_response",
                    "data": {"response_id": response_id, "stats": combined_stats},
                },
            )

    async def _handle_get_active_tasks(self, client_id: str, data: Dict[str, Any]):
        """Handle request for active tasks"""
        response_id = data.get("response_id")

        if response_id:
            try:
                # Get active tasks from queue
                active_tasks = await self.task_queue.get_active_tasks()

                # Convert tasks to response format
                tasks_data = []
                for task in active_tasks:
                    task_info = {
                        "task_id": task.action.task_id,
                        "parent_id": task.action.parent_task_id,
                        "agent_type": task.action.agent_type,
                        "status": task.action.status,
                        "stage": "executing",  # Default stage
                        "created_at": task.action.created_at.isoformat(),
                        "updated_at": task.queued_at.isoformat(),
                        "content": task.action.payload,
                        "metadata": {
                            "assigned_agent": task.assigned_agent,
                            "retry_count": task.retry_count,
                            "priority": task.action.priority,
                            "action": task.action.action,
                        },
                        "dependencies": task.action.dependencies,
                        "children": [],  # Will be populated by client-side processing
                    }
                    tasks_data.append(task_info)

                await self._send_to_client(
                    client_id,
                    {
                        "type": "active_tasks_response",
                        "data": {"response_id": response_id, "tasks": tasks_data},
                    },
                )

            except Exception as e:
                logger.error(f"Error getting active tasks: {e}")
                await self._send_to_client(
                    client_id,
                    {
                        "type": "active_tasks_response",
                        "data": {
                            "response_id": response_id,
                            "tasks": [],
                            "error": str(e),
                        },
                    },
                )

    async def _handle_get_task_details(self, client_id: str, data: Dict[str, Any]):
        """Handle request for specific task details"""
        task_id = data.get("task_id")
        response_id = data.get("response_id")

        if task_id and response_id:
            try:
                # Get task details from queue
                task = await self.task_queue.get_task(task_id)

                if task:
                    task_info = {
                        "task_id": task.action.task_id,
                        "parent_id": task.action.parent_task_id,
                        "agent_type": task.action.agent_type,
                        "status": task.action.status,
                        "stage": "executing",  # Default stage
                        "created_at": task.action.created_at.isoformat(),
                        "updated_at": task.queued_at.isoformat(),
                        "content": task.action.payload,
                        "metadata": {
                            "assigned_agent": task.assigned_agent,
                            "retry_count": task.retry_count,
                            "priority": task.action.priority,
                            "action": task.action.action,
                            "context_id": task.action.context_id,
                            "max_retries": task.action.max_retries,
                            "timeout": task.action.timeout,
                        },
                        "dependencies": task.action.dependencies,
                        "children": [],  # Would need additional tracking for this
                    }

                    await self._send_to_client(
                        client_id,
                        {
                            "type": "task_details_response",
                            "data": {"response_id": response_id, "task": task_info},
                        },
                    )
                else:
                    await self._send_to_client(
                        client_id,
                        {
                            "type": "task_details_response",
                            "data": {
                                "response_id": response_id,
                                "task": None,
                                "error": "Task not found",
                            },
                        },
                    )

            except Exception as e:
                logger.error(f"Error getting task details for {task_id}: {e}")
                await self._send_to_client(
                    client_id,
                    {
                        "type": "task_details_response",
                        "data": {
                            "response_id": response_id,
                            "task": None,
                            "error": str(e),
                        },
                    },
                )

    # Background Task Methods

    async def _process_tasks(self):
        """Background task to process the task queue"""
        self.logger.log_event(
            LogLevel.INFO,
            LogEvent.SERVER_START,
            "Task processing loop started"
        )
        while self.is_running:
            try:
                # Get next task
                task = await self.task_queue.get_next_task()

                if task:
                    self.logger.log_event(
                        LogLevel.INFO,
                        LogEvent.TASK_DISPATCH,
                        f"Processing task {task.action.task_id} with action '{task.action.action}'",
                        task_id=task.action.task_id,
                        action=task.action.action
                    )

                    # Use enhanced load balancer to select best agent
                    agent_id = await self.load_balancer.select_agent(
                        task.action.action, task.action
                    )

                    if agent_id:
                        self.logger.log_event(
                            LogLevel.INFO,
                            LogEvent.TASK_DISPATCH,
                            f"Load balancer selected agent {agent_id}",
                            task_id=task.action.task_id,
                            agent_id=agent_id
                        )
                        
                        # Record request start for metrics
                        await self.load_balancer.record_request_start(
                            agent_id, task.action.task_id
                        )

                        # Assign task to agent
                        await self.agent_registry.assign_task(
                            agent_id, task.action.task_id
                        )
                        await self.task_queue.assign_agent(
                            task.action.task_id, agent_id
                        )

                        # Send task to agent
                        try:
                            await self._send_task_to_agent(agent_id, task.action)
                            self.logger.log_event(
                                LogLevel.INFO,
                                LogEvent.TASK_DISPATCH,
                                f"Successfully assigned task {task.action.task_id} to agent {agent_id}",
                                task_id=task.action.task_id,
                                agent_id=agent_id
                            )
                            
                            # Log task dispatch to task logger
                            self.task_logger.log_task_dispatch(
                                task.action.task_id,
                                task.action.context_id or "unknown",
                                task.action.agent_type,
                                task.action.action,
                                agent_id=agent_id
                            )
                            
                        except Exception as e:
                            # Record failure and retry or fail
                            await self.load_balancer.record_request_failure(
                                agent_id, task.action.task_id, e
                            )
                            logger.error(f"Failed to send task to agent {agent_id}: {e}")
                            
                            # Log dispatch failure to task logger
                            self.task_logger.log_error(
                                f"Failed to send task {task.action.task_id} to agent {agent_id}: {e}",
                                task_id=task.action.task_id,
                                agent_id=agent_id
                            )
                            # Task will be retried by queue mechanism
                            
                    else:
                        # Debug: Get all registered agents and capabilities
                        all_agents = await self.agent_registry.get_all_agents()
                        capabilities = await self.agent_registry.get_capabilities()

                        logger.warning(
                            f"No available agents for task {task.action.task_id} with action '{task.action.action}'"
                        )
                        logger.warning(f"Registered agents: {list(all_agents.keys())}")
                        logger.warning(
                            f"Available capabilities: {list(capabilities.keys())}"
                        )

                        # Check specific capability
                        if task.action.action in capabilities:
                            agent_ids = capabilities[task.action.action]
                            logger.warning(
                                f"Agents with capability '{task.action.action}': {list(agent_ids)}"
                            )
                            for agent_id in agent_ids:
                                if agent_id in all_agents:
                                    agent = all_agents[agent_id]
                                    logger.warning(
                                        f"Agent {agent_id}: available={agent.is_available}, "
                                        f"status={agent.registration.status}, "
                                        f"tasks={len(agent.current_tasks)}"
                                    )

                        # No available agents, put task back in queue
                        await self.task_queue.fail_task(
                            task.action.task_id, "No available agents", retry=True
                        )
                        logger.warning(
                            f"Failed task {task.action.task_id} due to no available agents"
                        )
                        
                        # Log no agent available to task logger
                        self.task_logger.log_event(
                            LogLevel.WARNING,
                            LogEvent.TASK_RETRY,
                            f"No available agents for task {task.action.task_id} with action '{task.action.action}'",
                            task_id=task.action.task_id,
                            agent_type=task.action.agent_type,
                            action=task.action.action
                        )

                # Small delay to prevent tight loop
                await asyncio.sleep(0.1)

            except Exception as e:
                self.logger.log_error(f"Error processing tasks: {e}")
                await asyncio.sleep(1)

        self.logger.log_event(
            LogLevel.INFO,
            LogEvent.SERVER_STOP,
            "Task processing loop stopped"
        )

    async def _send_task_to_agent(self, agent_id: str, action: ResearchAction):
        """Send task to specific agent"""
        # Find agent's client connection
        if agent_id in self.agent_to_client:
            client_id = self.agent_to_client[agent_id]

            if client_id in self.clients:
                try:
                    message = {
                        "type": "research_task",
                        "data": action.to_dict(),
                        "timestamp": datetime.now().isoformat(),
                    }

                    await self.clients[client_id].send(json.dumps(message, default=str))
                    self.stats["total_messages_sent"] += 1
                    self.logger.log_event(
                        LogLevel.DEBUG,
                        LogEvent.TASK_DISPATCH,
                        f"Sent task {action.task_id} to agent {agent_id}",
                        task_id=action.task_id,
                        agent_id=agent_id
                    )

                except Exception as e:
                    self.logger.log_error(f"Error sending task to agent {agent_id}: {e}", 
                                          task_id=action.task_id, agent_id=agent_id)
                    # Mark task as failed if we can't send it
                    await self.task_queue.fail_task(
                        action.task_id, f"Failed to send to agent: {e}"
                    )
                    # Log send failure to task logger
                    self.task_logger.log_error(
                        f"Failed to send task {action.task_id} to agent {agent_id}: {e}",
                        task_id=action.task_id,
                        agent_id=agent_id
                    )
            else:
                self.logger.log_error(f"Client {client_id} for agent {agent_id} not found", 
                                      agent_id=agent_id, client_id=client_id)
                await self.task_queue.fail_task(
                    action.task_id, "Agent client disconnected"
                )
                # Log client not found to task logger
                self.task_logger.log_error(
                    f"Client {client_id} for agent {agent_id} not found for task {action.task_id}",
                    task_id=action.task_id,
                    agent_id=agent_id,
                    client_id=client_id
                )
        else:
            self.logger.log_error(f"Agent {agent_id} not found in agent-to-client mapping", 
                                  agent_id=agent_id, task_id=action.task_id)
            await self.task_queue.fail_task(action.task_id, "Agent not registered")
            # Log agent not registered to task logger
            self.task_logger.log_error(
                f"Agent {agent_id} not found in mapping for task {action.task_id}",
                task_id=action.task_id,
                agent_id=agent_id
            )

    async def _send_to_client(self, client_id: str, message: Dict[str, Any]):
        """Send message to specific client"""
        if client_id in self.clients:
            try:
                message["timestamp"] = datetime.now().isoformat()
                await self.clients[client_id].send(json.dumps(message, default=str))
                self.stats["total_messages_sent"] += 1
            except Exception as e:
                logger.error(f"Error sending message to client {client_id}: {e}")

    async def _periodic_cleanup(self):
        """Periodic cleanup tasks"""
        while self.is_running:
            try:
                # Clean up old tasks
                await self.task_queue.cleanup_old_tasks(max_age_hours=24)

                # Sleep for 1 hour
                await asyncio.sleep(3600)

            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def get_server_stats(self) -> Dict[str, Any]:
        """Get comprehensive server statistics including load balancer metrics."""
        uptime = (datetime.now() - self.stats["started_at"]).total_seconds()
        
        # Get load balancer stats
        load_balancer_stats = await self.load_balancer.get_load_balancer_stats()
        
        # Get agent registry stats
        all_agents = await self.agent_registry.get_all_agents()
        capabilities = await self.agent_registry.get_capabilities()
        
        # Get agent metrics from load balancer
        agent_metrics = await self.load_balancer.get_all_metrics()
        
        return {
            "server": {
                "uptime_seconds": uptime,
                "started_at": self.stats["started_at"].isoformat(),
                "is_running": self.is_running,
                "total_tasks_processed": self.stats["total_tasks_processed"],
                "total_messages_sent": self.stats["total_messages_sent"],
                "total_messages_received": self.stats["total_messages_received"],
                "total_agents_registered": self.stats["total_agents_registered"],
                "active_connections": len(self.clients),
            },
            "load_balancer": load_balancer_stats,
            "agents": {
                "total_registered": len(all_agents),
                "available_capabilities": list(capabilities.keys()),
                "agent_details": {
                    agent_id: {
                        "agent_type": agent.registration.agent_type,
                        "capabilities": agent.registration.capabilities,
                        "status": agent.registration.status,
                        "current_tasks": len(agent.current_tasks),
                        "max_concurrent": agent.registration.max_concurrent,
                        "load_factor": agent.load_factor,
                        "is_available": agent.is_available,
                        "is_healthy": agent.is_healthy,
                        "last_heartbeat": agent.last_heartbeat.isoformat(),
                    }
                    for agent_id, agent in all_agents.items()
                },
                "performance_metrics": {
                    agent_id: {
                        "total_requests": metrics.total_requests,
                        "successful_requests": metrics.successful_requests,
                        "failed_requests": metrics.failed_requests,
                        "success_rate": metrics.success_rate,
                        "average_response_time": metrics.average_response_time,
                        "health_score": metrics.health_score,
                        "consecutive_failures": metrics.consecutive_failures,
                    }
                    for agent_id, metrics in agent_metrics.items()
                }
            },
            "task_queue": {
                "pending_tasks": len(self.task_queue._queue),
                "active_tasks": len(self.task_queue._active_tasks),
                "completed_tasks": len(self.task_queue._completed_tasks),
                "failed_tasks": len(self.task_queue._failed_tasks),
                "max_queue_size": self.task_queue.max_size,
            }
        }
    
    async def get_agent_health(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed health information for a specific agent."""
        agent_info = await self.agent_registry.get_agent_info(agent_id)
        if not agent_info:
            return None
            
        metrics = await self.load_balancer.get_agent_metrics(agent_id)
        circuit_breaker = self.load_balancer._get_circuit_breaker(agent_id)
        
        return {
            "agent_id": agent_id,
            "agent_type": agent_info.registration.agent_type,
            "status": agent_info.registration.status,
            "is_healthy": agent_info.is_healthy,
            "is_available": agent_info.is_available,
            "load_factor": agent_info.load_factor,
            "current_tasks": list(agent_info.current_tasks),
            "last_heartbeat": agent_info.last_heartbeat.isoformat(),
            "performance": {
                "total_requests": metrics.total_requests if metrics else 0,
                "success_rate": metrics.success_rate if metrics else 1.0,
                "average_response_time": metrics.average_response_time if metrics else 0.0,
                "health_score": metrics.health_score if metrics else 1.0,
                "consecutive_failures": metrics.consecutive_failures if metrics else 0,
            },
            "circuit_breaker": {
                "state": circuit_breaker.state,
                "failure_count": circuit_breaker.failure_count,
                "can_execute": circuit_breaker.can_execute(),
            }
        }
    
    async def set_load_balance_strategy(self, strategy: str) -> bool:
        """Change the load balancing strategy at runtime."""
        try:
            new_strategy = LoadBalanceStrategy(strategy)
            self.load_balancer.strategy = new_strategy
            self.logger.log_event(
                LogLevel.INFO,
                LogEvent.SERVER_START,
                f"Load balancing strategy changed to: {strategy}",
                strategy=strategy
            )
            return True
        except ValueError:
            self.logger.log_error(f"Invalid load balancing strategy: {strategy}", strategy=strategy)
            return False

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""

        def signal_handler(signum, frame):
            self.logger.log_event(
                LogLevel.INFO,
                LogEvent.SERVER_STOP,
                f"Received signal {signum}, shutting down gracefully...",
                signal=signum
            )
            asyncio.create_task(self.stop())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def run_forever(self):
        """Run the server forever"""
        try:
            await self.start()

            # Keep server running
            while self.is_running:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            self.logger.log_event(LogLevel.INFO, LogEvent.SERVER_STOP, "Received keyboard interrupt")
        except Exception as e:
            self.logger.log_error(f"Server error: {e}")
        finally:
            await self.stop()


async def main():
    """Main entry point for MCP server"""
    # Ensure logs directory exists
    from pathlib import Path

    Path("logs").mkdir(exist_ok=True)

    # Setup logging
    log_path = os.getenv("EUNICE_LOG_PATH", "logs")
    log_level = os.getenv("EUNICE_LOG_LEVEL", "INFO")

    # Ensure log directory exists
    Path(log_path).mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s-%(message)s",
        handlers=[
            logging.FileHandler(os.path.join(log_path, "mcp_server.log")),
            logging.StreamHandler(),
        ],
    )

    # Load configuration
    config_manager = ConfigManager()

    # Create and run server
    server = MCPServer(config_manager)
    await server.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
