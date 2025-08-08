#!/usr/bin/env python3
"""
JSON-RPC 2.0 Compliant MCP Client for Database Service

Enhanced for JSON-RPC 2.0 compliance with the MCP standard:
- Proper JSON-RPC 2.0 message format with "jsonrpc": "2.0"
- Request/response/notification handling
- Error handling with proper JSON-RPC error codes
- Enhanced connection management and retry logic
- Database service specific capabilities and message handlers
"""

import asyncio
import json
import logging
import uuid
import random
from datetime import datetime
from typing import Any, Callable, Dict, Optional

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

logger = logging.getLogger(__name__)


class MCPClient:
    """
    JSON-RPC 2.0 compliant MCP Client for Database Service communication.
    
    Features:
    - Full JSON-RPC 2.0 compliance for MCP protocol
    - Robust connection management with exponential backoff
    - Proper request/response/notification handling
    - Enhanced error handling with JSON-RPC error codes
    - Database service specific capabilities and message handlers
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
        self.max_reconnect_duration = self.config.get("max_reconnect_duration", 3600)  # 1 hour
        self.last_connection_attempt = None
        
        # Client identification
        self.client_id = f"database-{uuid.uuid4().hex[:8]}"  # Entity ID for routing
        
        # JSON-RPC management
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.request_counter = 0
        self.message_handlers: Dict[str, Callable] = {}
        self.request_timeout = self.config.get("request_timeout", 30.0)  # 30 seconds
        
        # Background tasks
        self._listen_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._should_reconnect = True
        
        # Heartbeat configuration
        self.heartbeat_interval = self.config.get("heartbeat_interval", 30)
        self.ping_timeout = self.config.get("ping_timeout", 10)
        
        # Setup message handlers for Database Service
        self._setup_message_handlers()

        logger.info(f"Initialized JSON-RPC 2.0 MCP Client for Database Service {host}:{port} with ID {self.client_id}")

    def _setup_message_handlers(self):
        """Setup message handlers for the Database Service."""
        self.message_handlers = {
            "agent_register_ack": self._handle_registration_confirmation,
            "task_request": self._handle_task_request,
            "database_update": self._handle_database_update,
            "heartbeat": self._handle_heartbeat,
            "ping": self._handle_ping
        }

    def _generate_request_id(self) -> str:
        """Generate a unique request ID."""
        self.request_counter += 1
        return f"{self.client_id}-req-{self.request_counter}"

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

    async def connect(self) -> bool:
        """Connect to MCP server."""
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
                self._cleanup_task = asyncio.create_task(self._cleanup_requests())
                
                # Register as Database Service
                await self._register_as_database_service()
                
                return True
                
            except Exception as e:
                logger.warning(f"Connection failed (attempt {self.connection_attempts}): {e}")
                if self.connection_attempts < max_retries:
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
        """Disconnect with proper cleanup."""
        try:
            logger.info("Disconnecting from MCP server...")
            self.running = False
            self._should_reconnect = False
            
            # Cancel background tasks
            tasks_to_cancel = [
                self._listen_task,
                self._reconnect_task,
                self._heartbeat_task,
                self._cleanup_task
            ]
            
            for task in tasks_to_cancel:
                if task and not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            # Send unregister notification if connected
            if self.websocket and not self.websocket.closed:
                try:
                    await self._send_jsonrpc_notification("agent_unregister", {
                        "agent_id": self.client_id,
                        "timestamp": datetime.now().isoformat()
                    })
                    await self.websocket.close()
                except Exception as e:
                    logger.error(f"Error sending unregister notification: {e}")

            self.is_connected = False
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
            result = await asyncio.wait_for(future, timeout=30.0)
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

    # Database Service specific methods
    async def _register_as_database_service(self):
        """Register this client as a Database Service."""
        try:
            await self._send_jsonrpc_notification("agent_register", {
                "agent_id": self.client_id,
                "agent_type": "database",
                "capabilities": [
                    "create_project",
                    "update_project",
                    "delete_project", 
                    "create_research_topic",
                    "update_research_topic",
                    "delete_research_topic",
                    "create_research_plan",
                    "update_research_plan",
                    "delete_research_plan",
                    "create_task",
                    "update_task",
                    "delete_task",
                    "create_research_task",
                    "update_research_task",
                    "delete_research_task",
                    "create_literature_record",
                    "update_literature_record",
                    "delete_literature_record",
                    "create_search_term_optimization",
                    "update_search_term_optimization",
                    "delete_search_term_optimization"
                ],
                "timestamp": datetime.now().isoformat()
            })
            logger.info("Registered as Database Service with MCP server")
            
        except Exception as e:
            logger.error(f"Failed to register as database service: {e}")

    async def send_status_update(self, status_data: Dict[str, Any]) -> bool:
        """Send a status update to the MCP server."""
        if not self.is_connected or not self.websocket:
            logger.warning("Not connected to MCP server, attempting reconnect...")
            success = await self._connect_with_retry()
            if not success:
                logger.error("Failed to reconnect for status update")
                return False

        try:
            await self._send_jsonrpc_notification("status_response", {
                **status_data,
                "agent_id": self.client_id,
                "timestamp": datetime.now().isoformat()
            })
            
            logger.info(f"Sent status update from database service")
            return True

        except Exception as e:
            logger.error(f"Failed to send status update: {e}")
            return False

    async def send_maintenance_report(self, maintenance_data: Dict[str, Any]) -> bool:
        """Send maintenance completion report to MCP server."""
        if not self.is_connected or not self.websocket:
            logger.warning("Not connected to MCP server, attempting reconnect...")
            success = await self._connect_with_retry()
            if not success:
                logger.error("Failed to reconnect for maintenance report")
                return False

        try:
            await self._send_jsonrpc_notification("maintenance_completed", {
                **maintenance_data,
                "agent_id": self.client_id,
                "timestamp": datetime.now().isoformat()
            })
            
            logger.info(f"Sent maintenance report from database service")
            return True

        except Exception as e:
            logger.error(f"Failed to send maintenance report: {e}")
            return False

    async def send_task_result(self, task_result: Dict[str, Any]) -> bool:
        """Send task result to MCP server."""
        if not self.is_connected or not self.websocket:
            logger.warning("Not connected to MCP server, attempting reconnect...")
            success = await self._connect_with_retry()
            if not success:
                logger.error("Failed to reconnect for task result")
                return False

        try:
            await self._send_jsonrpc_notification("task_result", {
                **task_result,
                "agent_id": self.client_id,
                "timestamp": datetime.now().isoformat()
            })
            
            logger.info(f"Sent task result for task {task_result.get('task_id')}")
            return True

        except Exception as e:
            logger.error(f"Failed to send task result: {e}")
            return False

    async def get_server_stats(self) -> Optional[Dict[str, Any]]:
        """Get server statistics with response handling."""
        if not self.is_connected or not self.websocket:
            logger.warning("Not connected to MCP server, attempting reconnect...")
            success = await self._connect_with_retry()
            if not success:
                logger.error("Failed to reconnect for server stats")
                return None

        try:
            result = await self._send_jsonrpc_request("status_request", {
                "agent_id": self.client_id,
                "timestamp": datetime.now().isoformat()
            })
            return result

        except Exception as e:
            logger.error(f"Failed to get server stats: {e}")
            return None

    # Connection and message handling
    async def _heartbeat_loop(self):
        """Send periodic heartbeat to MCP server."""
        while self.running and self._should_reconnect:
            try:
                if self.is_connected and self.websocket and not self.websocket.closed:
                    await self._send_jsonrpc_notification("heartbeat", {
                        "agent_id": self.client_id,
                        "status": "alive",
                        "timestamp": datetime.now().isoformat()
                    })
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                self.is_connected = False
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

    # Message handlers for Database Service
    async def _handle_registration_confirmation(self, params: Dict[str, Any]):
        """Handle registration confirmation from server."""
        server_id = params.get("server_id")
        logger.info(f"Database Service registration confirmed by server {server_id}")
        if "instructions" in params:
            logger.info(f"Received server instructions: {params['instructions']}")

    async def _handle_task_request(self, params: Dict[str, Any]):
        """Handle task request from MCP server."""
        # This would be handled by the database service main handler
        # For now, just log the request
        task_id = params.get("task_id")
        task_type = params.get("task_type") 
        logger.info(f"Received task request: {task_type} (task_id: {task_id})")

    async def _handle_database_update(self, params: Dict[str, Any]):
        """Handle database update request from MCP server."""
        # This would be handled by the database service main handler
        # For now, just log the request
        command = params.get("command")
        logger.info(f"Received database update request: {command}")

    async def _handle_heartbeat(self, params: Dict[str, Any]):
        """Handle heartbeat request."""
        await self._send_jsonrpc_notification("heartbeat_ack", {
            "agent_id": self.client_id,
            "status": "alive",
            "timestamp": datetime.now().isoformat()
        })

    async def _handle_ping(self, params: Dict[str, Any]):
        """Handle ping request."""
        await self._send_jsonrpc_notification("pong", {
            "agent_id": self.client_id,
            "timestamp": datetime.now().isoformat()
        })

    # Utility methods
    async def _reconnect(self):
        """Attempt to reconnect to MCP server with maximum duration."""
        start_time = datetime.now()
        reconnect_delay = self.base_retry_delay
        
        while (self._should_reconnect and not self.is_connected and self.running and
               (datetime.now() - start_time).total_seconds() < self.max_reconnect_duration):
            try:
                logger.info("Attempting to reconnect to MCP server...")
                success = await self._connect_with_retry()
                if success:
                    logger.info("Successfully reconnected to MCP server")
                    break
                else:
                    reconnect_delay = min(reconnect_delay * 1.5, 60) + (random.random() * 0.1)
                    logger.info(f"Retrying reconnect in {reconnect_delay:.2f} seconds...")
                    await asyncio.sleep(reconnect_delay)
            except Exception as e:
                logger.error(f"Reconnection attempt failed: {e}")
                await asyncio.sleep(reconnect_delay)
        
        if not self.is_connected:
            logger.error("Reconnection failed after maximum duration")

    async def _cleanup_requests(self):
        """Clean up expired requests."""
        while self.running:
            try:
                # Clean up expired pending requests
                current_time = datetime.now()
                expired_requests = []
                
                for request_id, future in list(self.pending_requests.items()):
                    if future.done():
                        expired_requests.append(request_id)
                
                for request_id in expired_requests:
                    self.pending_requests.pop(request_id, None)
                    logger.debug(f"Cleaned up completed request: {request_id}")
                
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in request cleanup loop: {e}")
                await asyncio.sleep(60)

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
            "host": self.host,
            "port": self.port,
            "client_id": self.client_id,
            "service_type": "database",
            "is_connected": self.is_connected,
            "running": self.running,
            "websocket_available": self.websocket is not None,
            "last_connection_attempt": self.last_connection_attempt.isoformat() if self.last_connection_attempt else None,
            "connection_attempts": self.connection_attempts,
            "pending_requests": len(self.pending_requests)
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check and return status."""
        health_status = {
            "status": "healthy" if self.is_connected else "unhealthy",
            "connected": self.is_connected,
            "running": self.running,
            "client_id": self.client_id,
            "service_type": "database",
            "server_url": f"ws://{self.host}:{self.port}",
            "pending_requests": len(self.pending_requests),
            "timestamp": datetime.now().isoformat()
        }
        
        if not self.is_connected:
            health_status["last_error"] = "WebSocket not connected"
            
        return health_status
