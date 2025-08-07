"""
MCP Client for Containerized API Gateway

Enhanced client adapted for the new MCP server architecture.
Handles WebSocket communication with improved MCP server featuring:
- Robust reconnection with exponential backoff and jitter
- Enhanced message routing and task handling
- Better error handling and logging
- Graceful shutdown with resource cleanup
"""

import asyncio
import json
import logging
import uuid
import random
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Union

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

logger = logging.getLogger(__name__)


class MCPClient:
    """
    Enhanced MCP Client for API Gateway communication with improved MCP server.
    
    Features:
    - Robust connection management with exponential backoff
    - Enhanced task submission and result handling
    - Improved error handling and recovery
    - Better logging and monitoring capabilities
    """

    def __init__(self, host: str = "mcp-server", port: int = 9000, config: Optional[Dict[str, Any]] = None):
        self.host = host
        self.port = port
        self.config = config or {}
        
        # WebSocket connection
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        self.running = False
        
        # Connection management
        self.connection_attempts = 0
        self.max_retries = self.config.get("max_retries", 15)
        self.base_retry_delay = self.config.get("base_retry_delay", 5)
        self.last_connection_attempt = None
        
        # Client identification
        self.client_id = f"api-gateway-{uuid.uuid4().hex[:8]}"  # Entity ID for routing
        
        # Task and response management
        self.response_callbacks: Dict[str, Union[Callable, asyncio.Future]] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.active_requests: Dict[str, Dict[str, Any]] = {}  # Track ongoing requests
        
        # Background tasks
        self._listen_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._should_reconnect = True
        
        # Heartbeat configuration
        self.heartbeat_interval = self.config.get("heartbeat_interval", 30)
        self.ping_timeout = self.config.get("ping_timeout", 10)
        
        # Setup message handlers
        self._setup_message_handlers()

        logger.info(f"Initialized enhanced MCP Client for {host}:{port} with ID {self.client_id}")

    def _setup_message_handlers(self):
        """Setup default message handlers for the API Gateway."""
        self.message_handlers = {
            "registration_confirmed": self._handle_registration_confirmation,
            "task_result": self._handle_task_result,
            "task_status_response": self._handle_task_status_response,
            "task_queued": self._handle_task_queued,
            "task_rejected": self._handle_task_rejected,
            "error": self._handle_error_message,
            "heartbeat_request": self._handle_heartbeat_request
        }

    async def connect(self) -> bool:
        """Connect to MCP server with enhanced retry logic."""
        return await self._connect_with_retry()

    async def _connect_with_retry(self) -> bool:
        """Connect to MCP server with exponential backoff and jitter."""
        self.connection_attempts = 0
        max_retries = self.max_retries
        base_delay = self.base_retry_delay
        
        while self.connection_attempts < max_retries and self._should_reconnect:
            try:
                self.connection_attempts += 1
                uri = f"ws://{self.host}:{self.port}"
                logger.info(f"Connecting to MCP server at {uri} (attempt {self.connection_attempts})")
                
                self.websocket = await websockets.connect(
                    uri,
                    ping_interval=self.heartbeat_interval,
                    ping_timeout=self.ping_timeout,
                    close_timeout=10,
                    max_size=1024*1024  # 1MB max message size
                )
                
                self.is_connected = True
                self.running = True
                self.connection_attempts = 0
                self.last_connection_attempt = datetime.now()
                
                logger.info(f"Successfully connected to MCP server at {uri}")

                # Start background tasks
                self._listen_task = asyncio.create_task(self._listen_for_messages())
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                
                # Register as API Gateway
                await self._register_as_gateway()
                
                return True
                
            except Exception as e:
                logger.warning(f"Connection failed (attempt {self.connection_attempts}): {e}")
                if self.connection_attempts < max_retries:
                    # Exponential backoff with jitter: delay = base_delay * 2^attempt + random(0, 100ms)
                    delay = (base_delay * (2 ** min(self.connection_attempts - 1, 5))) + (random.random() * 0.1)
                    logger.info(f"Retrying in {delay:.2f} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error("Failed to connect after all retries")
                    self.is_connected = False
                    return False
        
        self.is_connected = False
        return False

    async def disconnect(self):
        """Enhanced disconnect with proper cleanup."""
        try:
            logger.info("Disconnecting from MCP server...")
            self.running = False
            self._should_reconnect = False
            
            # Cancel background tasks
            tasks_to_cancel = [
                self._listen_task,
                self._reconnect_task,
                self._heartbeat_task
            ]
            
            for task in tasks_to_cancel:
                if task and not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            # Send unregister message if connected
            if self.websocket:
                try:
                    # Check if websocket is still open before sending
                    can_send = False
                    if hasattr(self.websocket, 'closed'):
                        can_send = not self.websocket.closed
                    elif hasattr(self.websocket, 'state'):
                        can_send = self.websocket.state.name == 'OPEN'
                    else:
                        can_send = True  # Fallback, try to send
                    
                    if can_send:
                        await self._send_message({
                            "type": "gateway_unregister",
                            "client_id": self.client_id,
                            "timestamp": datetime.now().isoformat()
                        })
                    
                    await self.websocket.close()
                except Exception as e:
                    logger.error(f"Error sending unregister message: {e}")

            self.is_connected = False
            self.websocket = None
            logger.info("Disconnected from MCP server")

        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

    async def _register_as_gateway(self):
        """Register this client as an API Gateway with enhanced capabilities."""
        try:
            registration_message = {
                "type": "gateway_register",
                "client_id": self.client_id,  # Entity ID for routing
                "client_type": "api_gateway",
                "capabilities": [
                    "request_routing", 
                    "task_submission", 
                    "status_queries",
                    "result_delivery",
                    "error_handling"
                ],
                "timestamp": datetime.now().isoformat()
            }
            
            await self._send_message(registration_message)
            logger.info("Registered as API Gateway with enhanced MCP server")
            
        except Exception as e:
            logger.error(f"Failed to register as gateway: {e}")

    async def _heartbeat_loop(self):
        """Send periodic heartbeat to MCP server."""
        while self.running and self._should_reconnect:
            try:
                if (self.is_connected and self.websocket and 
                    hasattr(self.websocket, 'closed') and not self.websocket.closed):
                    await self._send_message({
                        "type": "heartbeat",
                        "client_id": self.client_id,
                        "status": "alive",
                        "timestamp": datetime.now().isoformat()
                    })
                elif (self.is_connected and self.websocket and 
                      hasattr(self.websocket, 'state') and 
                      self.websocket.state.name == 'OPEN'):
                    await self._send_message({
                        "type": "heartbeat",
                        "client_id": self.client_id,
                        "status": "alive",
                        "timestamp": datetime.now().isoformat()
                    })
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                self.is_connected = False
                break

    async def send_research_action(self, task_data: Dict[str, Any]) -> bool:
        """Send a research action to the MCP server with enhanced tracking."""
        if not self.is_connected or not self.websocket:
            logger.error("Not connected to MCP server")
            return False

        try:
            task_id = task_data.get("task_id")
            if not task_id:
                task_id = str(uuid.uuid4())
                task_data["task_id"] = task_id

            message = {
                "type": "task_request",  # Aligned with new MCP server
                "task_id": task_id,
                "task_type": task_data.get("task_type", "research_action"),
                "data": task_data,
                "client_id": self.client_id,  # Entity ID for routing
                "context_id": task_data.get("context_id"),
                "timestamp": datetime.now().isoformat()
            }
            
            # Track the request
            self.active_requests[task_id] = {
                "type": "research_action",
                "data": task_data,
                "submitted_at": datetime.now()
            }
            
            await self._send_message(message)
            logger.debug(f"Sent research action for task {task_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send research action: {e}")
            return False

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a task from MCP server with enhanced handling."""
        if not self.is_connected or not self.websocket:
            logger.error("Not connected to MCP server")
            return None

        try:
            message = {
                "type": "task_status_request",
                "task_id": task_id,
                "client_id": self.client_id,
                "timestamp": datetime.now().isoformat()
            }

            # Create a future to wait for the response
            response_future = asyncio.Future()
            callback_key = f"status_{task_id}"
            self.response_callbacks[callback_key] = response_future

            await self._send_message(message)

            # Wait for response with timeout
            try:
                response = await asyncio.wait_for(response_future, timeout=10.0)
                return response
            except asyncio.TimeoutError:
                logger.warning(f"Timeout waiting for task status: {task_id}")
                return None
            finally:
                # Clean up callback
                self.response_callbacks.pop(callback_key, None)

        except Exception as e:
            logger.error(f"Failed to get task status for {task_id}: {e}")
            return None

    async def wait_for_task_result(self, task_id: str, timeout: float = 60.0) -> Optional[Dict[str, Any]]:
        """Wait for a task result with enhanced error handling."""
        if not self.is_connected or not self.websocket:
            logger.error("Not connected to MCP server")
            return None

        try:
            # Create a future to wait for the task result
            result_future = asyncio.Future()
            callback_key = f"result_{task_id}"
            self.response_callbacks[callback_key] = result_future

            logger.info(f"Waiting for task result: {task_id} (timeout: {timeout}s)")

            # Wait for task result with timeout
            try:
                result = await asyncio.wait_for(result_future, timeout=timeout)
                logger.info(f"Received task result for {task_id}")
                
                # Clean up active request tracking
                self.active_requests.pop(task_id, None)
                
                return result
            except asyncio.TimeoutError:
                logger.warning(f"Timeout waiting for task result: {task_id}")
                return None
            finally:
                # Clean up callback
                self.response_callbacks.pop(callback_key, None)

        except Exception as e:
            logger.error(f"Failed to wait for task result {task_id}: {e}")
            return None

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task with enhanced tracking."""
        if not self.is_connected or not self.websocket:
            logger.error("Not connected to MCP server")
            return False

        try:
            message = {
                "type": "task_cancel_request",
                "task_id": task_id,
                "client_id": self.client_id,
                "timestamp": datetime.now().isoformat()
            }

            await self._send_message(message)
            logger.debug(f"Sent cancel request for task {task_id}")
            
            # Clean up tracking
            self.active_requests.pop(task_id, None)
            self.response_callbacks.pop(f"result_{task_id}", None)
            self.response_callbacks.pop(f"status_{task_id}", None)
            
            return True

        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return False

    async def get_server_stats(self) -> Optional[Dict[str, Any]]:
        """Get server statistics with enhanced information."""
        if not self.is_connected or not self.websocket:
            logger.error("Not connected to MCP server")
            return None

        try:
            message = {
                "type": "server_stats_request",
                "client_id": self.client_id,
                "timestamp": datetime.now().isoformat()
            }

            await self._send_message(message)
            
            # Return enhanced client info
            return {
                "status": "requested", 
                "client_id": self.client_id,
                "active_requests": len(self.active_requests),
                "pending_callbacks": len(self.response_callbacks),
                "connection_info": self.connection_info
            }

        except Exception as e:
            logger.error(f"Failed to get server stats: {e}")
            return None

    async def _send_message(self, message: Dict[str, Any]):
        """Send a message to the MCP server with enhanced error handling."""
        if not self.websocket:
            logger.warning("Cannot send message: WebSocket not connected")
            self.is_connected = False
            return
        
        # Check if websocket is closed using compatible method
        try:
            if hasattr(self.websocket, 'closed') and self.websocket.closed:
                logger.warning("Cannot send message: WebSocket is closed")
                self.is_connected = False
                return
            elif hasattr(self.websocket, 'state') and self.websocket.state.name != 'OPEN':
                logger.warning("Cannot send message: WebSocket is not open")
                self.is_connected = False
                return
        except AttributeError:
            # Fallback if neither attribute exists
            pass
        
        try:
            message_str = json.dumps(message)
            await self.websocket.send(message_str)
            logger.debug(f"Sent message: {message.get('type', 'unknown')}")
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.is_connected = False

    async def _listen_for_messages(self):
        """Listen for incoming messages with enhanced error handling."""
        logger.info("Started listening for MCP server messages")
        
        try:
            if not self.websocket:
                logger.error("No websocket connection available")
                return
                
            async for message_str in self.websocket:
                try:
                    message = json.loads(message_str)
                    await self._process_mcp_message(message)
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode message: {message_str}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    
        except ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.is_connected = False
            if self._should_reconnect and self.running:
                self._reconnect_task = asyncio.create_task(self._reconnect())
        except WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            self.is_connected = False
            if self._should_reconnect and self.running:
                self._reconnect_task = asyncio.create_task(self._reconnect())
        except Exception as e:
            logger.error(f"Unexpected error in message listener: {e}")
            self.is_connected = False

    async def _process_mcp_message(self, data: Dict[str, Any]):
        """Process incoming MCP message with enhanced routing."""
        try:
            message_type = data.get("type")
            if not message_type:
                logger.warning("Received message with no type")
                return
                
            handler = self.message_handlers.get(message_type)
            if handler:
                await handler(data)
            else:
                logger.debug(f"No handler for message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error processing MCP message: {e}")

    # Enhanced message handlers
    async def _handle_registration_confirmation(self, data: Dict[str, Any]):
        """Handle registration confirmation from server."""
        server_id = data.get("server_id")
        logger.info(f"API Gateway registration confirmed by server {server_id}")
        
        # Process any additional server instructions if present
        if "instructions" in data:
            logger.info(f"Received server instructions: {data['instructions']}")

    async def _handle_task_result(self, data: Dict[str, Any]):
        """Handle task result with enhanced processing."""
        task_id = data.get("task_id")
        status = data.get("status", "unknown")
        
        if not task_id:
            logger.warning("Received task result without task_id")
            return
        
        result_key = f"result_{task_id}"
        
        if result_key in self.response_callbacks:
            callback = self.response_callbacks[result_key]
            if isinstance(callback, asyncio.Future) and not callback.done():
                # Pass the complete message as the result
                callback.set_result(data)
                logger.info(f"Delivered task result for {task_id}: {status}")
        
        # Clean up tracking
        if task_id:
            self.active_requests.pop(task_id, None)
        
        logger.debug(f"Processed task result for {task_id}: {status}")

    async def _handle_task_status_response(self, data: Dict[str, Any]):
        """Handle task status response."""
        task_id = data.get("task_id")
        
        if not task_id:
            logger.warning("Received task status response without task_id")
            return
        
        callback_key = f"status_{task_id}"
        if callback_key in self.response_callbacks:
            callback = self.response_callbacks[callback_key]
            if isinstance(callback, asyncio.Future) and not callback.done():
                callback.set_result(data.get("data", {}))
                logger.debug(f"Delivered task status for {task_id}")

    async def _handle_task_queued(self, data: Dict[str, Any]):
        """Handle task queued confirmation."""
        task_id = data.get("data", {}).get("task_id") or data.get("task_id")
        logger.info(f"Task {task_id} queued successfully")

    async def _handle_task_rejected(self, data: Dict[str, Any]):
        """Handle task rejection with enhanced error reporting."""
        task_id = data.get("data", {}).get("task_id") or data.get("task_id")
        error = data.get("data", {}).get("error") or data.get("error", "Unknown error")
        
        logger.error(f"Task {task_id} rejected: {error}")
        
        # Also notify any waiting callbacks about the rejection
        result_key = f"result_{task_id}"
        if result_key in self.response_callbacks:
            callback = self.response_callbacks[result_key]
            if isinstance(callback, asyncio.Future) and not callback.done():
                callback.set_result({
                    "status": "rejected", 
                    "error": error,
                    "task_id": task_id
                })
        
        # Clean up tracking
        if task_id:
            self.active_requests.pop(task_id, None)

    async def _handle_error_message(self, data: Dict[str, Any]):
        """Handle error messages from server."""
        message = data.get("message", "Unknown error")
        task_id = data.get("task_id")
        
        logger.error(f"Received error from server: {message}" + 
                    (f" for task {task_id}" if task_id else ""))
        
        if task_id:
            # Notify waiting callbacks
            result_key = f"result_{task_id}"
            if result_key in self.response_callbacks:
                callback = self.response_callbacks[result_key]
                if isinstance(callback, asyncio.Future) and not callback.done():
                    callback.set_result({
                        "status": "error",
                        "error": message,
                        "task_id": task_id
                    })
            
            # Clean up tracking
            if task_id:
                self.active_requests.pop(task_id, None)

    async def _handle_heartbeat_request(self, data: Dict[str, Any]):
        """Handle heartbeat request from server."""
        await self._send_message({
            "type": "heartbeat_response",
            "client_id": self.client_id,
            "status": "alive",
            "timestamp": datetime.now().isoformat()
        })

    async def _reconnect(self):
        """Attempt to reconnect to MCP server with enhanced logic."""
        reconnect_delay = self.base_retry_delay
        
        while self._should_reconnect and not self.is_connected and self.running:
            try:
                logger.info("Attempting to reconnect to MCP server...")
                await asyncio.sleep(reconnect_delay)

                success = await self._connect_with_retry()
                if success:
                    logger.info("Successfully reconnected to MCP server")
                    break
                else:
                    # Exponential backoff with jitter (up to 60 seconds)
                    reconnect_delay = min(reconnect_delay * 1.5, 60) + (random.random() * 0.1)

            except Exception as e:
                logger.error(f"Reconnection attempt failed: {e}")
                await asyncio.sleep(reconnect_delay)

    def add_message_handler(self, message_type: str, handler: Callable):
        """Add a custom message handler."""
        self.message_handlers[message_type] = handler
        logger.debug(f"Added message handler for type: {message_type}")

    def remove_message_handler(self, message_type: str):
        """Remove a message handler."""
        if message_type in self.message_handlers:
            del self.message_handlers[message_type]
            logger.debug(f"Removed message handler for type: {message_type}")

    async def update_config(self, new_config: Dict[str, Any]):
        """Update configuration dynamically."""
        logger.info("Updating MCP client configuration")
        self.config.update(new_config)
        
        # Update relevant attributes
        old_server_url = f"ws://{self.host}:{self.port}"
        
        self.host = self.config.get("host", self.host)
        self.port = self.config.get("port", self.port)
        self.max_retries = self.config.get("max_retries", self.max_retries)
        self.base_retry_delay = self.config.get("base_retry_delay", self.base_retry_delay)
        self.heartbeat_interval = self.config.get("heartbeat_interval", self.heartbeat_interval)
        self.ping_timeout = self.config.get("ping_timeout", self.ping_timeout)
        
        new_server_url = f"ws://{self.host}:{self.port}"
        
        logger.info("Configuration updated successfully")
        
        # Reconnect if server URL changed
        if new_server_url != old_server_url:
            logger.info("Server URL changed, reconnecting...")
            self.is_connected = False
            if self.websocket and not self.websocket.closed:
                await self.websocket.close()
            await self._connect_with_retry()

    @property
    def connection_info(self) -> Dict[str, Any]:
        """Get enhanced connection information."""
        return {
            "host": self.host,
            "port": self.port,
            "client_id": self.client_id,
            "is_connected": self.is_connected,
            "running": self.running,
            "websocket_available": self.websocket is not None,
            "last_connection_attempt": self.last_connection_attempt.isoformat() if self.last_connection_attempt else None,
            "connection_attempts": self.connection_attempts,
            "active_requests": len(self.active_requests),
            "pending_callbacks": len(self.response_callbacks)
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check and return status."""
        health_status = {
            "status": "healthy" if self.is_connected else "unhealthy",
            "connected": self.is_connected,
            "running": self.running,
            "client_id": self.client_id,
            "server_url": f"ws://{self.host}:{self.port}",
            "active_requests": len(self.active_requests),
            "pending_callbacks": len(self.response_callbacks),
            "timestamp": datetime.now().isoformat()
        }
        
        if not self.is_connected:
            health_status["last_error"] = "WebSocket not connected"
            
        return health_status
