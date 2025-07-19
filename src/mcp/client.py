"""
MCP Client for Communication with MCP Server

Provides client interface for Research Manager and other components
to communicate with the MCP server.
"""

import asyncio
import websockets
import json
import logging
from typing import Dict, Any, Optional, Callable, List, Union
from datetime import datetime
import uuid

from .protocols import ResearchAction, AgentResponse, serialize_message, deserialize_message
from .structured_logger import get_mcp_logger

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for communicating with MCP server"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 9000):
        self.host = host
        self.port = port
        self.websocket: Optional[Any] = None
        self.is_connected = False
        self.response_callbacks: Dict[str, Union[Callable, asyncio.Future]] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.client_id = str(uuid.uuid4())
        self._listen_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None
        self._should_reconnect = True
        self.reconnect_delay = 5  # seconds
        
        # Initialize structured logger
        self.logger = get_mcp_logger("client")
        
    async def connect(self) -> bool:
        """Connect to MCP server"""
        try:
            uri = f"ws://{self.host}:{self.port}/ws"
            self.websocket = await websockets.connect(uri)
            self.is_connected = True
            
            # Start listening for messages
            self._listen_task = asyncio.create_task(self._listen_for_messages())
            
            logger.info(f"Connected to MCP server at {uri}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from MCP server"""
        self._should_reconnect = False
        
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
        
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        self.is_connected = False
        logger.info("Disconnected from MCP server")
    
    async def send_task(self, action: ResearchAction) -> bool:
        """Send a research task to the MCP server"""
        if not self.is_connected or not self.websocket:
            logger.error("Not connected to MCP server")
            return False
        
        try:
            message = serialize_message('research_action', action)
            await self.websocket.send(json.dumps(message))
            logger.debug(f"Sent task {action.task_id} to MCP server")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send task {action.task_id}: {e}")
            return False
    
    async def send_response(self, response: AgentResponse) -> bool:
        """Send agent response to MCP server"""
        if not self.is_connected or not self.websocket:
            logger.error("Not connected to MCP server")
            return False
        
        try:
            message = serialize_message('agent_response', response)
            await self.websocket.send(json.dumps(message))
            logger.debug(f"Sent response for task {response.task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send response for task {response.task_id}: {e}")
            return False
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        if not self.is_connected or not self.websocket:
            logger.error("Not connected to MCP server")
            return False
        
        try:
            message = {
                'type': 'cancel_task',
                'data': {'task_id': task_id},
                'timestamp': datetime.now().isoformat()
            }
            await self.websocket.send(json.dumps(message))
            logger.debug(f"Sent cancel request for task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return False
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a task"""
        if not self.is_connected or not self.websocket:
            logger.error("Not connected to MCP server")
            return None
        
        try:
            response_id = str(uuid.uuid4())
            message = {
                'type': 'get_task_status',
                'data': {'task_id': task_id, 'response_id': response_id},
                'timestamp': datetime.now().isoformat()
            }
            
            # Set up response callback
            response_future = asyncio.Future()
            self.response_callbacks[response_id] = response_future
            
            await self.websocket.send(json.dumps(message))
            
            # Wait for response (with timeout)
            try:
                result = await asyncio.wait_for(response_future, timeout=10.0)
                return result
            except asyncio.TimeoutError:
                logger.error(f"Timeout waiting for status of task {task_id}")
                return None
            finally:
                # Clean up callback
                if response_id in self.response_callbacks:
                    del self.response_callbacks[response_id]
            
        except Exception as e:
            logger.error(f"Failed to get status for task {task_id}: {e}")
            return None
    
    async def get_server_stats(self) -> Optional[Dict[str, Any]]:
        """Get server statistics"""
        if not self.is_connected or not self.websocket:
            logger.error("Not connected to MCP server")
            return None
        
        try:
            response_id = str(uuid.uuid4())
            message = {
                'type': 'get_server_stats',
                'data': {'response_id': response_id},
                'timestamp': datetime.now().isoformat()
            }
            
            # Set up response callback
            response_future = asyncio.Future()
            self.response_callbacks[response_id] = response_future
            
            await self.websocket.send(json.dumps(message))
            
            # Wait for response (with timeout)
            try:
                result = await asyncio.wait_for(response_future, timeout=10.0)
                return result
            except asyncio.TimeoutError:
                logger.error("Timeout waiting for server stats")
                return None
            finally:
                # Clean up callback
                if response_id in self.response_callbacks:
                    del self.response_callbacks[response_id]
            
        except Exception as e:
            logger.error(f"Failed to get server stats: {e}")
            return None
    
    def add_message_handler(self, message_type: str, handler: Callable[[Dict[str, Any]], None]):
        """Add a message handler for specific message types"""
        self.message_handlers[message_type] = handler
    
    def remove_message_handler(self, message_type: str):
        """Remove a message handler"""
        if message_type in self.message_handlers:
            del self.message_handlers[message_type]
    
    async def _listen_for_messages(self):
        """Listen for messages from MCP server"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Connection to MCP server closed")
        except Exception as e:
            logger.error(f"Error listening for messages: {e}")
        finally:
            self.is_connected = False
            if self._should_reconnect:
                self._reconnect_task = asyncio.create_task(self._reconnect())
    
    async def _handle_message(self, data: Dict[str, Any]):
        """Handle incoming message from server"""
        message_type = data.get('type')
        message_data = data.get('data', {})
        
        # Handle response callbacks
        if 'response_id' in message_data:
            response_id = message_data['response_id']
            if response_id in self.response_callbacks:
                future = self.response_callbacks[response_id]
                if not future.done():
                    future.set_result(message_data)
                return
        
        # Handle message type handlers
        if message_type in self.message_handlers:
            handler = self.message_handlers[message_type]
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message_data)
                else:
                    handler(message_data)
            except Exception as e:
                logger.error(f"Error in message handler for {message_type}: {e}")
        else:
            logger.debug(f"No handler for message type: {message_type}")
    
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
    
    async def wait_for_connection(self, timeout: float = 30.0) -> bool:
        """Wait for connection to be established"""
        start_time = asyncio.get_event_loop().time()
        
        while not self.is_connected:
            if asyncio.get_event_loop().time() - start_time > timeout:
                return False
            await asyncio.sleep(0.1)
        
        return True
    
    @property
    def connection_status(self) -> Dict[str, Any]:
        """Get current connection status"""
        return {
            'connected': self.is_connected,
            'host': self.host,
            'port': self.port,
            'client_id': self.client_id,
            'should_reconnect': self._should_reconnect
        }
