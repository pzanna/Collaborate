"""
MCP Client for Containerized API Gateway

Adapted from the main codebase MCP client to work in the containerized 
microservices environment. Handles WebSocket communication with the MCP server.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Union

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

logger = logging.getLogger(__name__)


class MCPClient:
    """
    Client for communicating with MCP server from the containerized API Gateway.
    
    This client is specifically adapted for Version 0.3 microservices architecture
    where the API Gateway runs as a separate container from the MCP server.
    """

    def __init__(self, host: str = "mcp-server", port: int = 9000):
        self.host = host
        self.port = port
        self.websocket: Optional[Any] = None
        self.is_connected = False
        self.response_callbacks: Dict[str, Union[Callable, asyncio.Future]] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.client_id = f"api-gateway-{uuid.uuid4().hex[:8]}"
        self._listen_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None
        self._should_reconnect = True
        self.reconnect_delay = 5  # seconds

        logger.info(f"Initialized MCP Client for {host}:{port} with ID {self.client_id}")

    async def connect(self) -> bool:
        """Connect to MCP server"""
        try:
            uri = f"ws://{self.host}:{self.port}"
            logger.info(f"Connecting to MCP server at {uri}")
            
            self.websocket = await websockets.connect(
                uri,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            
            self.is_connected = True
            logger.info(f"Successfully connected to MCP server at {uri}")

            # Start listening for messages
            self._listen_task = asyncio.create_task(self._listen_for_messages())
            
            # Register as API Gateway
            await self._register_as_gateway()
            
            return True

        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            self.is_connected = False
            return False

    async def disconnect(self):
        """Disconnect from MCP server"""
        try:
            logger.info("Disconnecting from MCP server...")
            self._should_reconnect = False
            
            # Cancel listening task
            if self._listen_task and not self._listen_task.done():
                self._listen_task.cancel()
                try:
                    await self._listen_task
                except asyncio.CancelledError:
                    pass

            # Cancel reconnect task
            if self._reconnect_task and not self._reconnect_task.done():
                self._reconnect_task.cancel()
                try:
                    await self._reconnect_task
                except asyncio.CancelledError:
                    pass

            # Close WebSocket connection
            if self.websocket:
                await self.websocket.close()

            self.is_connected = False
            logger.info("Disconnected from MCP server")

        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

    async def _register_as_gateway(self):
        """Register this client as an API Gateway with the MCP server"""
        try:
            registration_message = {
                "type": "gateway_register",
                "client_id": self.client_id,
                "client_type": "api_gateway",
                "capabilities": ["request_routing", "task_submission", "status_queries"],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self._send_message(registration_message)
            logger.info("Registered as API Gateway with MCP server")
            
        except Exception as e:
            logger.error(f"Failed to register as gateway: {e}")

    async def send_research_action(self, task_data: Dict[str, Any]) -> bool:
        """Send a research action to the MCP server"""
        if not self.is_connected or not self.websocket:
            logger.error("Not connected to MCP server")
            return False

        try:
            message = {
                "type": "research_action",
                "data": task_data,
                "client_id": self.client_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self._send_message(message)
            logger.debug(f"Sent research action for task {task_data.get('task_id')}")
            return True

        except Exception as e:
            logger.error(f"Failed to send research action: {e}")
            return False

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a task from MCP server"""
        if not self.is_connected or not self.websocket:
            logger.error("Not connected to MCP server")
            return None

        try:
            message = {
                "type": "task_status_request",
                "task_id": task_id,
                "client_id": self.client_id,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Create a future to wait for the response
            response_future = asyncio.Future()
            self.response_callbacks[task_id] = response_future

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
                self.response_callbacks.pop(task_id, None)

        except Exception as e:
            logger.error(f"Failed to get task status for {task_id}: {e}")
            return None

    async def wait_for_task_result(self, task_id: str, timeout: float = 60.0) -> Optional[Dict[str, Any]]:
        """Wait for a task result from the MCP server"""
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
        """Cancel a task"""
        if not self.is_connected or not self.websocket:
            logger.error("Not connected to MCP server")
            return False

        try:
            message = {
                "type": "task_cancel_request",
                "task_id": task_id,
                "client_id": self.client_id,
                "timestamp": datetime.utcnow().isoformat()
            }

            await self._send_message(message)
            logger.debug(f"Sent cancel request for task {task_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return False

    async def get_server_stats(self) -> Optional[Dict[str, Any]]:
        """Get server statistics"""
        if not self.is_connected or not self.websocket:
            logger.error("Not connected to MCP server")
            return None

        try:
            message = {
                "type": "server_stats_request",
                "client_id": self.client_id,
                "timestamp": datetime.utcnow().isoformat()
            }

            await self._send_message(message)
            # For now, return basic info - can be enhanced later
            return {"status": "requested", "client_id": self.client_id}

        except Exception as e:
            logger.error(f"Failed to get server stats: {e}")
            return None

    async def _send_message(self, message: Dict[str, Any]):
        """Send a message to the MCP server"""
        if not self.websocket:
            raise Exception("Not connected to MCP server")
        
        message_str = json.dumps(message)
        await self.websocket.send(message_str)
        logger.debug(f"Sent message: {message.get('type', 'unknown')}")

    async def _listen_for_messages(self):
        """Listen for incoming messages from MCP server"""
        logger.info("Started listening for MCP server messages")
        
        try:
            async for message_str in self.websocket:
                try:
                    message = json.loads(message_str)
                    await self._handle_message(message)
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode message: {message_str}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    
        except ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.is_connected = False
            if self._should_reconnect:
                self._reconnect_task = asyncio.create_task(self._reconnect())
        except WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            self.is_connected = False
            if self._should_reconnect:
                self._reconnect_task = asyncio.create_task(self._reconnect())
        except Exception as e:
            logger.error(f"Unexpected error in message listener: {e}")
            self.is_connected = False

    async def _handle_message(self, message: Dict[str, Any]):
        """Handle incoming message from MCP server"""
        message_type = message.get("type", "unknown")
        
        try:
            if message_type == "task_status_response":
                # Handle task status response
                task_id = message.get("task_id")
                if task_id and task_id in self.response_callbacks:
                    callback = self.response_callbacks[task_id]
                    if isinstance(callback, asyncio.Future) and not callback.done():
                        callback.set_result(message.get("data", {}))
            
            elif message_type == "task_result":
                # Handle task result (actual completion from agent)
                task_id = message.get("task_id")
                result_key = f"result_{task_id}"
                
                if result_key in self.response_callbacks:
                    callback = self.response_callbacks[result_key]
                    if isinstance(callback, asyncio.Future) and not callback.done():
                        # Pass the complete message as the result
                        callback.set_result(message)
                        logger.info(f"Delivered task result for {task_id}")
                
                # Also log for debugging
                logger.info(f"Received task result for {task_id}: {message.get('status', 'unknown')}")
            
            elif message_type == "registration_confirmed":
                logger.info("API Gateway registration confirmed by MCP server")
            
            elif message_type == "task_queued":
                task_id = message.get("data", {}).get("task_id")
                logger.info(f"Task {task_id} queued successfully")
            
            elif message_type == "task_rejected":
                task_id = message.get("data", {}).get("task_id")
                error = message.get("data", {}).get("error", "Unknown error")
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
            
            else:
                logger.debug(f"Received unhandled message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling message type {message_type}: {e}")

    async def _reconnect(self):
        """Attempt to reconnect to MCP server"""
        while self._should_reconnect and not self.is_connected:
            try:
                logger.info("Attempting to reconnect to MCP server...")
                await asyncio.sleep(self.reconnect_delay)

                success = await self.connect()
                if success:
                    logger.info("Successfully reconnected to MCP server")
                    break
                else:
                    # Exponential backoff (up to 60 seconds)
                    self.reconnect_delay = min(self.reconnect_delay * 1.5, 60)

            except Exception as e:
                logger.error(f"Reconnection attempt failed: {e}")
                await asyncio.sleep(self.reconnect_delay)

    def add_message_handler(self, message_type: str, handler: Callable):
        """Add a custom message handler"""
        self.message_handlers[message_type] = handler
        logger.debug(f"Added message handler for type: {message_type}")

    def remove_message_handler(self, message_type: str):
        """Remove a message handler"""
        if message_type in self.message_handlers:
            del self.message_handlers[message_type]
            logger.debug(f"Removed message handler for type: {message_type}")

    @property
    def connection_info(self) -> Dict[str, Any]:
        """Get connection information"""
        return {
            "host": self.host,
            "port": self.port,
            "client_id": self.client_id,
            "is_connected": self.is_connected,
            "websocket_available": self.websocket is not None
        }
