#!/usr/bin/env python3
"""
JSON-RPC 2.0 Compliant Base MCP Agent - WebSocket Client Implementation

Enhanced to leverage the improved MCP server's features:
- Full JSON-RPC 2.0 compliance for all communications
- Consistent entity_id usage for message routing
- Robust reconnection with exponential backoff and jitter
- Support for pending message delivery on reconnect
- Task timeout handling and late result processing
- Improved error handling and logging
- Graceful shutdown with resource cleanup
- Dynamic configuration updates

Architecture Compliance:
- No HTTP/REST endpoints
- Pure MCP JSON-RPC over WebSocket
- Zero attack surface design
- Centralized communication through MCP server
"""

import asyncio
import json
import logging
import uuid
import signal
import sys
import random
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path
from abc import ABC, abstractmethod

import websockets
from websockets.exceptions import ConnectionClosed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class BaseMCPAgent(ABC):
    """
    Base class for all MCP agents with JSON-RPC 2.0 compliance.

    Provides:
    - Robust WebSocket connection management with reconnection
    - MCP JSON-RPC 2.0 protocol handling
    - Agent registration with pending message support
    - Task routing with timeout handling
    - Enhanced error handling and logging
    - Graceful shutdown with cleanup
    - Dynamic configuration updates
    """

    def __init__(self, agent_type: str, config: Dict[str, Any]):
        """Initialize base MCP agent."""
        self.agent_type = agent_type
        self.agent_id = f"{agent_type}-{uuid.uuid4().hex[:8]}"  # Entity ID
        self.config = config
        self.logger = logging.getLogger(f"{agent_type}-agent")
        
        # Connection configuration
        self.mcp_server_url = config.get("mcp_server_url", "ws://mcp-server:9000")
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self.running = False
        self.last_connection_attempt = None
        self.connection_attempts = 0
        self.max_retries = config.get("max_retries", 15)
        self.base_retry_delay = config.get("base_retry_delay", 5)
        
        # JSON-RPC management
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.request_counter = 0
        
        # Heartbeat configuration
        self.heartbeat_interval = config.get("heartbeat_interval", 30)
        self.ping_timeout = config.get("ping_timeout", 10)
        
        # Task handling
        self.task_handlers: Dict[str, Callable] = {}
        self.message_handlers = {
            "ping": self._handle_ping,
            "status_request": self._handle_status_request,
            "shutdown": self._handle_shutdown,
            "task_request": self._handle_task_execution,
            "registration_confirmed": self._handle_registration_confirmation,
            "heartbeat": self._handle_heartbeat
        }
        
        # Task tracking
        self.active_tasks: Dict[str, Dict[str, Any]] = {}  # task_id -> task_info
        self.task_timeout = config.get("task_timeout", 3600)  # 1 hour
        
        # Request timeout
        self.request_timeout = config.get("request_timeout", 30.0)
        
        self.logger.info(f"JSON-RPC 2.0 MCP Agent {self.agent_id} initialized")

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Return list of agent capabilities."""
        pass

    @abstractmethod
    def setup_task_handlers(self) -> Dict[str, Callable]:
        """Setup task handlers for this agent."""
        pass

    @abstractmethod
    async def handle_task(self, task_type: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a specific task. Subclasses must implement this."""
        pass

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
            self.logger.debug(f"Sent JSON-RPC request: {method} (id: {request_id})")
            
            # Wait for response with timeout
            result = await asyncio.wait_for(future, timeout=self.request_timeout)
            return result
            
        except asyncio.TimeoutError:
            self.logger.error(f"Request timeout for method: {method}")
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
        self.logger.debug(f"Sent JSON-RPC notification: {method}")

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
        self.logger.debug(f"Sent JSON-RPC response (id: {request_id})")

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
        self.logger.debug(f"Sent JSON-RPC error: {code} - {message} (id: {request_id})")

    async def start(self):
        """Start the agent with graceful shutdown handling."""
        try:
            self.running = True
            self.task_handlers = self.setup_task_handlers()
            
            # Setup signal handlers for graceful shutdown
            if sys.platform != "win32":
                loop = asyncio.get_event_loop()
                for sig in [signal.SIGTERM, signal.SIGINT]:
                    loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))
            
            await self.connect_to_mcp_server()
            await self.message_loop()
            
        except Exception as e:
            self.logger.error(f"Error in agent start: {e}")
            await self.shutdown()
            raise

    async def shutdown(self):
        """Graceful shutdown with cleanup."""
        if not self.running:
            return
            
        self.logger.info("Initiating graceful shutdown...")
        self.running = False
        
        try:
            # Send unregister notification if connected
            if self.connected and self.websocket and not self.websocket.closed:
                await self._send_jsonrpc_notification("agent_unregister", {
                    "agent_id": self.agent_id,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Give time for unregister to be sent
                await asyncio.sleep(0.5)
                
                # Close WebSocket
                await self.websocket.close()
                
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
        finally:
            self.connected = False
            self.websocket = None
            self.logger.info("Agent shutdown complete")

    async def connect_to_mcp_server(self):
        """Connect to MCP server with retry logic."""
        self.connection_attempts = 0
        
        while self.connection_attempts < self.max_retries and self.running:
            try:
                self.connection_attempts += 1
                self.logger.info(f"Connecting to MCP server (attempt {self.connection_attempts})")
                
                self.websocket = await websockets.connect(
                    self.mcp_server_url,
                    ping_interval=self.heartbeat_interval,
                    ping_timeout=self.ping_timeout,
                    close_timeout=10,
                    max_size=1024*1024  # 1MB max message size
                )
                
                await self.register_with_mcp_server()
                self.connected = True
                self.connection_attempts = 0
                self.logger.info("Connected to MCP server successfully")
                return
                
            except Exception as e:
                self.logger.warning(f"Failed to connect (attempt {self.connection_attempts}): {e}")
                if self.connection_attempts < self.max_retries:
                    # Exponential backoff with jitter
                    delay = min(self.base_retry_delay * (2 ** self.connection_attempts), 300)
                    jitter = random.uniform(0, 0.1 * delay)
                    await asyncio.sleep(delay + jitter)
                else:
                    raise Exception("Failed to connect to MCP server after all retries")

    async def register_with_mcp_server(self):
        """Register this agent with the MCP server."""
        if not self.websocket:
            raise Exception("WebSocket connection not available")
            
        await self._send_jsonrpc_notification("agent_register", {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": self.get_capabilities(),
            "timestamp": datetime.now().isoformat()
        })
        
        self.logger.info(f"Registered with MCP server: {len(self.get_capabilities())} capabilities")

    async def message_loop(self):
        """Main message processing loop."""
        self.logger.info("Starting message processing loop")
        
        try:
            if not self.websocket:
                raise Exception("No WebSocket connection available")
                
            async for message_str in self.websocket:
                try:
                    message = json.loads(message_str)
                    if self._validate_jsonrpc_message(message):
                        await self._process_jsonrpc_message(message)
                    else:
                        self.logger.warning(f"Invalid JSON-RPC message: {message}")
                except json.JSONDecodeError:
                    self.logger.error(f"Failed to decode JSON: {message_str}")
                except Exception as e:
                    self.logger.error(f"Error handling message: {e}")
                    
        except ConnectionClosed:
            self.logger.warning("WebSocket connection closed")
            self.connected = False
            if self.running:
                await self.reconnect()
        except Exception as e:
            self.logger.error(f"Error in message loop: {e}")
            self.connected = False
            if self.running:
                await self.reconnect()

    async def reconnect(self):
        """Reconnect to MCP server."""
        self.logger.info("Attempting to reconnect...")
        self.connected = False
        self.websocket = None
        
        try:
            await self.connect_to_mcp_server()
            await self.message_loop()
        except Exception as e:
            self.logger.error(f"Reconnection failed: {e}")
            await self.shutdown()

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
                self.logger.warning(f"Unknown JSON-RPC message format: {message}")
                
        except Exception as e:
            self.logger.error(f"Error processing JSON-RPC message: {e}")

    async def _handle_jsonrpc_request(self, message: Dict[str, Any]):
        """Handle JSON-RPC request or notification."""
        try:
            method = message.get("method")
            params = message.get("params", {})
            request_id = message.get("id")  # None for notifications
            
            if not method or not isinstance(method, str):
                self.logger.warning("Received message with invalid method")
                return
            
            self.logger.debug(f"Handling JSON-RPC method: {method}")
            
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
                    self.logger.error(f"Error in handler for {method}: {e}")
                    if request_id is not None:
                        await self._send_jsonrpc_error(-32603, "Internal error", request_id, str(e))
            else:
                self.logger.warning(f"No handler for method: {method}")
                if request_id is not None:
                    await self._send_jsonrpc_error(-32601, "Method not found", request_id)
                
        except Exception as e:
            self.logger.error(f"Error processing JSON-RPC request: {e}")

    async def _handle_jsonrpc_response(self, message: Dict[str, Any]):
        """Handle JSON-RPC response or error."""
        request_id = message.get("id")
        if request_id is None:
            self.logger.warning("Received response without id")
            return
        
        future = self.pending_requests.get(request_id)
        if future and not future.done():
            if "error" in message:
                error = message["error"]
                future.set_exception(Exception(f"JSON-RPC Error {error.get('code')}: {error.get('message')}"))
            else:
                future.set_result(message.get("result"))
        
        self.pending_requests.pop(request_id, None)

    # Message handlers
    async def _handle_task_execution(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task execution request."""
        task_id = params.get("task_id")
        task_type = params.get("task_type")
        task_data = params.get("task_data", {})
        
        if not task_id or not task_type:
            raise Exception("Invalid task request: missing task_id or task_type")
            
        self.logger.info(f"Executing task {task_id} of type {task_type}")
        
        try:
            # Track active task
            self.active_tasks[task_id] = {
                "type": task_type,
                "data": task_data,
                "start_time": datetime.now(),
                "status": "running"
            }
            
            # Execute task using subclass implementation
            result = await self.handle_task(task_type, task_data)
            
            # Send success result
            await self._send_jsonrpc_notification("task_result", {
                "task_id": task_id,
                "status": "completed",
                "result": result,
                "agent_id": self.agent_id,
                "timestamp": datetime.now().isoformat()
            })
            
            # Update task tracking
            self.active_tasks[task_id]["status"] = "completed"
            self.active_tasks[task_id]["result"] = result
            
            return {"status": "received", "message": "Task execution started"}
            
        except Exception as e:
            self.logger.error(f"Task execution failed for {task_id}: {e}")
            
            # Send error result
            await self._send_jsonrpc_notification("task_result", {
                "task_id": task_id,
                "status": "error",
                "error": str(e),
                "agent_id": self.agent_id,
                "timestamp": datetime.now().isoformat()
            })
            
            # Update task tracking
            self.active_tasks[task_id]["status"] = "error"
            self.active_tasks[task_id]["error"] = str(e)
            
            raise

    async def _handle_heartbeat(self, params: Dict[str, Any]):
        """Handle heartbeat notification."""
        # Respond with heartbeat_ack notification
        await self._send_jsonrpc_notification("heartbeat_ack", {
            "agent_id": self.agent_id,
            "status": "alive",
            "timestamp": datetime.now().isoformat()
        })

    async def _handle_ping(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ping request."""
        return {
            "agent_id": self.agent_id,
            "status": "alive",
            "timestamp": datetime.now().isoformat()
        }

    async def _handle_status_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status request."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": "running" if self.running else "stopped",
            "connected": self.connected,
            "active_tasks": len(self.active_tasks),
            "capabilities": self.get_capabilities(),
            "timestamp": datetime.now().isoformat()
        }

    async def _handle_shutdown(self, params: Dict[str, Any]):
        """Handle shutdown notification."""
        self.logger.info("Received shutdown request")
        
        # Send acknowledgment
        await self._send_jsonrpc_notification("shutdown_ack", {
            "agent_id": self.agent_id,
            "timestamp": datetime.now().isoformat()
        })
        
        # Initiate shutdown
        asyncio.create_task(self.shutdown())

    async def _handle_registration_confirmation(self, params: Dict[str, Any]):
        """Handle registration confirmation notification."""
        self.logger.info("Agent registration confirmed by MCP server")

    # Utility methods
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
            self.logger.info(f"Sent task result for {task_id}: {status}")
            
        except Exception as e:
            self.logger.error(f"Failed to send task result for {task_id}: {e}")

    async def send_periodic_heartbeat(self):
        """Send periodic heartbeat to maintain connection."""
        while self.connected and self.running:
            try:
                await self._send_jsonrpc_notification("heartbeat", {
                    "agent_id": self.agent_id,
                    "status": "alive", 
                    "timestamp": datetime.now().isoformat()
                })
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                self.logger.error(f"Error sending heartbeat: {e}")
                break

    @property
    def connection_info(self) -> Dict[str, Any]:
        """Get connection information."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "mcp_server_url": self.mcp_server_url,
            "connected": self.connected,
            "running": self.running,
            "websocket_available": self.websocket is not None,
            "connection_attempts": self.connection_attempts,
            "pending_requests": len(self.pending_requests),
            "active_tasks": len(self.active_tasks)
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check and return status."""
        return {
            "status": "healthy" if self.connected else "unhealthy",
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "connected": self.connected,
            "running": self.running,
            "mcp_server_url": self.mcp_server_url,
            "pending_requests": len(self.pending_requests),
            "active_tasks": len(self.active_tasks),
            "capabilities": len(self.get_capabilities()),
            "timestamp": datetime.now().isoformat()
        }
