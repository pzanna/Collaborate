"""
JSON-RPC 2.0 Compliant MCP Communication module for Research Manager.

This module handles all MCP protocol communication including:
- Connection management and registration
- Message parsing and routing  
- Task delegation to other agents
- Response handling and coordination
- Full JSON-RPC 2.0 compliance
"""

import asyncio
import json
import logging
import uuid
import random
from datetime import datetime
from typing import Any, Dict, Optional, Callable

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

logger = logging.getLogger(__name__)


class MCPCommunicator:
    """JSON-RPC 2.0 compliant MCP protocol communication handler for Research Manager."""
    
    def __init__(self, agent_id: str, agent_type: str, mcp_server_url: str, capabilities: list):
        """Initialize MCP communicator."""
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.mcp_server_url = mcp_server_url
        self.capabilities = capabilities
        
        # Connection state
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.mcp_connected = False
        self.should_run = True
        self.connection_attempts = 0
        
        # JSON-RPC management
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.request_counter = 0
        
        # Message handling
        self.task_queue = asyncio.Queue()
        self.message_handlers: Dict[str, Callable] = {}
        
        # Background tasks
        self._listen_task = None
        self._heartbeat_task = None
        
        # Configuration
        self.heartbeat_interval = 30
        self.request_timeout = 30.0
        self.max_retries = 10
        self.base_retry_delay = 5
        
        # Setup message handlers
        self._setup_message_handlers()
        
        logger.info(f"Initialized JSON-RPC 2.0 MCP Communicator for {agent_id}")
    
    def _setup_message_handlers(self):
        """Setup message handlers for research manager."""
        self.message_handlers = {
            "task_request": self._handle_task_request,
            "heartbeat": self._handle_heartbeat,
            "ping": self._handle_ping,
            "research_action": self._handle_research_action,
        }
    
    def _generate_request_id(self) -> str:
        """Generate a unique request ID."""
        self.request_counter += 1
        return f"{self.agent_id}-req-{self.request_counter}"

    def _validate_jsonrpc_message(self, message: Dict[str, Any]) -> bool:
        """Validate JSON-RPC 2.0 message format."""
        if not isinstance(message, dict):
            return False
        
        # Must have jsonrpc field with value "2.0"
        if message.get("jsonrpc") != "2.0":
            return False
        
        # Must be either request, response, or notification
        if "method" in message:
            # Request or notification
            return isinstance(message.get("method"), str)
        elif "result" in message or "error" in message:
            # Response
            return "id" in message
        
        return False

    async def connect_to_mcp_server(self):
        """Connect to MCP server with retry logic."""
        self.connection_attempts = 0
        
        while self.connection_attempts < self.max_retries and self.should_run:
            try:
                self.connection_attempts += 1
                logger.info(f"Connecting to MCP server at {self.mcp_server_url} (attempt {self.connection_attempts})")
                
                self.websocket = await websockets.connect(
                    self.mcp_server_url,
                    ping_interval=self.heartbeat_interval,
                    ping_timeout=10,
                    close_timeout=10,
                    max_size=1024*1024  # 1MB max message size
                )
                
                # Register with MCP server
                await self._register_with_mcp_server()
                
                self.mcp_connected = True
                self.connection_attempts = 0
                
                # Start background tasks
                self._listen_task = asyncio.create_task(self._listen_for_messages())
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                
                logger.info("Successfully connected to MCP server")
                return
                
            except Exception as e:
                logger.warning(f"Failed to connect to MCP server (attempt {self.connection_attempts}): {e}")
                if self.connection_attempts < self.max_retries:
                    delay = (self.base_retry_delay * (2 ** min(self.connection_attempts - 1, 5))) + (random.random() * 0.1)
                    await asyncio.sleep(delay)
                else:
                    logger.error("Failed to connect to MCP server after all retries")
                    raise
    
    async def disconnect(self):
        """Disconnect from MCP server with proper cleanup."""
        try:
            logger.info("Disconnecting from MCP server...")
            self.should_run = False
            
            # Cancel background tasks
            if self._listen_task and not self._listen_task.done():
                self._listen_task.cancel()
                try:
                    await self._listen_task
                except asyncio.CancelledError:
                    pass
            
            if self._heartbeat_task and not self._heartbeat_task.done():
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    pass
            
            # Send unregister notification if connected
            if self.websocket and not self.websocket.closed:
                try:
                    await self._send_jsonrpc_notification("agent_unregister", {
                        "agent_id": self.agent_id,
                        "timestamp": datetime.now().isoformat()
                    })
                    await self.websocket.close()
                except Exception as e:
                    logger.error(f"Error sending unregister notification: {e}")
            
            self.mcp_connected = False
            self.websocket = None
            logger.info("Disconnected from MCP server")
            
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
    
    # JSON-RPC 2.0 communication methods
    async def _send_jsonrpc_request(self, method: str, params: Dict[str, Any]) -> Any:
        """Send JSON-RPC request and wait for response."""
        if not self.websocket or self.websocket.closed:
            raise Exception("WebSocket not connected")
        
        request_id = self._generate_request_id()
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id
        }
        
        # Create future for response
        future = asyncio.Future()
        self.pending_requests[request_id] = future
        
        try:
            await self.websocket.send(json.dumps(request))
            logger.debug(f"Sent JSON-RPC request: {method} (id: {request_id})")
            
            # Wait for response with timeout
            result = await asyncio.wait_for(future, timeout=self.request_timeout)
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Request timeout for method: {method}")
            raise
        finally:
            self.pending_requests.pop(request_id, None)

    async def _send_jsonrpc_notification(self, method: str, params: Dict[str, Any]):
        """Send JSON-RPC notification (no response expected)."""
        if not self.websocket or self.websocket.closed:
            raise Exception("WebSocket not connected")
        
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        
        await self.websocket.send(json.dumps(notification))
        logger.debug(f"Sent JSON-RPC notification: {method}")

    async def _send_jsonrpc_response(self, result: Any, request_id: str):
        """Send JSON-RPC response."""
        if not self.websocket or self.websocket.closed:
            return
        
        response = {
            "jsonrpc": "2.0",
            "result": result,
            "id": request_id
        }
        
        await self.websocket.send(json.dumps(response))
        logger.debug(f"Sent JSON-RPC response (id: {request_id})")

    async def _send_jsonrpc_error(self, code: int, message: str, request_id: str, data: Any = None):
        """Send JSON-RPC error response."""
        if not self.websocket or self.websocket.closed:
            return
        
        error_response = {
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": message
            },
            "id": request_id
        }
        
        if data is not None:
            error_response["error"]["data"] = data
        
        await self.websocket.send(json.dumps(error_response))
        logger.debug(f"Sent JSON-RPC error: {code} - {message} (id: {request_id})")

    async def _register_with_mcp_server(self):
        """Register this agent with the MCP server."""
        if not self.websocket:
            raise Exception("WebSocket connection not available")
            
        await self._send_jsonrpc_notification("agent_register", {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": self.capabilities,
            "timestamp": datetime.now().isoformat(),
            "service_info": {
                "host": "0.0.0.0",
                "port": 8002,
                "health_endpoint": "http://0.0.0.0:8002/health"
            }
        })
        
        logger.info(f"Registered with MCP server: {len(self.capabilities)} capabilities")
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeat to MCP server."""
        while self.should_run and self.mcp_connected:
            try:
                if self.websocket and not self.websocket.closed:
                    await self._send_jsonrpc_notification("heartbeat", {
                        "agent_id": self.agent_id,
                        "status": "alive",
                        "timestamp": datetime.now().isoformat()
                    })
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                self.mcp_connected = False
                break
    
    async def _listen_for_messages(self):
        """Listen for incoming messages."""
        logger.info("Started listening for MCP server messages")
        
        try:
            if not self.websocket:
                logger.error("No WebSocket connection available")
                return
                
            async for message_str in self.websocket:
                try:
                    message = json.loads(message_str)
                    if self._validate_jsonrpc_message(message):
                        await self._process_jsonrpc_message(message)
                    else:
                        logger.warning(f"Invalid JSON-RPC message: {message}")
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode JSON: {message_str}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    
        except ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.mcp_connected = False
        except WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            self.mcp_connected = False
        except Exception as e:
            logger.error(f"Unexpected error in message listener: {e}")
            self.mcp_connected = False

    async def _process_jsonrpc_message(self, message: Dict[str, Any]):
        """Process incoming JSON-RPC message."""
        try:
            if "method" in message:
                # Request or notification
                await self._handle_jsonrpc_request(message)
            elif "result" in message or "error" in message:
                # Response
                await self._handle_jsonrpc_response(message)
            else:
                logger.warning(f"Unknown JSON-RPC message format: {message}")
                
        except Exception as e:
            logger.error(f"Error processing JSON-RPC message: {e}")

    async def _handle_jsonrpc_request(self, message: Dict[str, Any]):
        """Handle JSON-RPC request or notification."""
        try:
            method = message.get("method")
            params = message.get("params", {})
            request_id = message.get("id")  # None for notifications
            
            if not method or not isinstance(method, str):
                logger.warning("Received message with invalid method")
                return
            
            logger.debug(f"Handling JSON-RPC method: {method}")
            
            # Find handler
            handler = self.message_handlers.get(method)
            if handler:
                try:
                    if request_id is not None:
                        # Request - handler should return result
                        result = await handler(params)
                        await self._send_jsonrpc_response(result, request_id)
                    else:
                        # Notification - no response expected
                        await handler(params)
                except Exception as e:
                    logger.error(f"Error in handler for {method}: {e}")
                    if request_id is not None:
                        await self._send_jsonrpc_error(-32603, "Internal error", request_id, str(e))
            else:
                logger.warning(f"No handler for method: {method}")
                if request_id is not None:
                    await self._send_jsonrpc_error(-32601, "Method not found", request_id)
                
        except Exception as e:
            logger.error(f"Error processing JSON-RPC message: {e}")

    async def _handle_jsonrpc_response(self, message: Dict[str, Any]):
        """Handle JSON-RPC response or error."""
        request_id = message.get("id")
        if request_id is None:
            logger.warning("Received response without id")
            return
        
        future = self.pending_requests.get(request_id)
        if future and not future.done():
            if "error" in message:
                error = message["error"]
                future.set_exception(Exception(f"JSON-RPC Error {error.get('code')}: {error.get('message')}"))
            else:
                future.set_result(message.get("result"))
        
        self.pending_requests.pop(request_id, None)

    # Message handlers for research manager
    async def _handle_task_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task request from MCP server."""
        logger.info(f"Received task request: {params}")
        
        # Queue task for processing
        await self.task_queue.put(params)
        
        return {"status": "received", "message": "Task queued for processing"}

    async def _handle_research_action(self, params: Dict[str, Any]):
        """Handle research action notification."""
        logger.info(f"Received research action: {params}")
        
        # Queue research action for processing
        await self.task_queue.put({
            "type": "research_action",
            **params
        })

    async def _handle_heartbeat(self, params: Dict[str, Any]):
        """Handle heartbeat request."""
        # Respond with heartbeat_ack notification
        await self._send_jsonrpc_notification("heartbeat_ack", {
            "agent_id": self.agent_id,
            "status": "alive",
            "timestamp": datetime.now().isoformat()
        })

    async def _handle_ping(self, params: Dict[str, Any]):
        """Handle ping request."""
        # Respond with pong notification
        await self._send_jsonrpc_notification("pong", {
            "agent_id": self.agent_id,
            "timestamp": datetime.now().isoformat()
        })

    # Public API methods
    async def listen_for_tasks(self):
        """Listen for tasks from MCP server."""
        try:
            if not self.websocket:
                logger.error("Cannot listen for tasks: no websocket connection")
                return
                
            logger.info("Starting to listen for tasks from MCP server")
            
            while self.should_run and self.mcp_connected:
                try:
                    # Get task from queue with timeout
                    task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                    
                    # Process the task
                    await self._process_task(task)
                    
                except asyncio.TimeoutError:
                    # No task received, continue listening
                    continue
                except Exception as e:
                    logger.error(f"Error processing task: {e}")
                    
        except Exception as e:
            logger.error(f"Error in task listening loop: {e}")

    async def _process_task(self, task: Dict[str, Any]):
        """Process a task received from MCP server."""
        task_id = task.get("task_id", str(uuid.uuid4()))
        task_type = task.get("type", "unknown")
        
        logger.info(f"Processing task {task_id} of type {task_type}")
        
        try:
            # Send task status update
            await self._send_jsonrpc_notification("task_status", {
                "task_id": task_id,
                "status": "processing",
                "agent_id": self.agent_id,
                "timestamp": datetime.now().isoformat()
            })
            
            # TODO: Implement actual task processing logic here
            # This would delegate to appropriate handlers based on task type
            
            # Send task completion
            await self._send_jsonrpc_notification("task_result", {
                "task_id": task_id,
                "status": "completed",
                "result": {"message": f"Task {task_id} processed successfully"},
                "agent_id": self.agent_id,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}")
            
            # Send task error
            await self._send_jsonrpc_notification("task_result", {
                "task_id": task_id,
                "status": "error",
                "error": str(e),
                "agent_id": self.agent_id,
                "timestamp": datetime.now().isoformat()
            })

    async def send_task_result(self, task_id: str, result: Dict[str, Any], status: str = "completed"):
        """Send task result to MCP server."""
        try:
            await self._send_jsonrpc_notification("task_result", {
                "task_id": task_id,
                "status": status,
                "result": result,
                "agent_id": self.agent_id,
                "timestamp": datetime.now().isoformat()
            })
            logger.info(f"Sent task result for {task_id}: {status}")
            
        except Exception as e:
            logger.error(f"Failed to send task result for {task_id}: {e}")

    async def request_task_delegation(self, target_agent: str, task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Request task delegation to another agent."""
        try:
            result = await self._send_jsonrpc_request("delegate_task", {
                "target_agent": target_agent,
                "task_data": task_data,
                "source_agent": self.agent_id,
                "timestamp": datetime.now().isoformat()
            })
            return result
            
        except Exception as e:
            logger.error(f"Failed to delegate task to {target_agent}: {e}")
            return None

    def add_message_handler(self, method: str, handler: Callable):
        """Add a custom message handler."""
        self.message_handlers[method] = handler
        logger.debug(f"Added message handler for method: {method}")

    def remove_message_handler(self, method: str):
        """Remove a message handler."""
        if method in self.message_handlers:
            del self.message_handlers[method]
            logger.debug(f"Removed message handler for method: {method}")

    @property
    def connection_info(self) -> Dict[str, Any]:
        """Get connection information."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "mcp_server_url": self.mcp_server_url,
            "mcp_connected": self.mcp_connected,
            "should_run": self.should_run,
            "websocket_available": self.websocket is not None,
            "connection_attempts": self.connection_attempts,
            "pending_requests": len(self.pending_requests),
            "capabilities": self.capabilities
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check and return status."""
        health_status = {
            "status": "healthy" if self.mcp_connected else "unhealthy",
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "mcp_connected": self.mcp_connected,
            "should_run": self.should_run,
            "mcp_server_url": self.mcp_server_url,
            "pending_requests": len(self.pending_requests),
            "capabilities": len(self.capabilities),
            "timestamp": datetime.now().isoformat()
        }
        
        if not self.mcp_connected:
            health_status["last_error"] = "MCP server not connected"
            
        return health_status
