#!/usr/bin/env python3
"""
Improved Base MCP Agent - WebSocket Client Implementation

Enhanced to leverage the improved MCP server's features:
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
    Base class for all MCP agents.

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
        
        # Heartbeat configuration
        self.heartbeat_interval = config.get("heartbeat_interval", 30)
        self.ping_timeout = config.get("ping_timeout", 10)
        
        # Task handling
        self.task_handlers: Dict[str, Callable] = {}
        self.message_handlers = {
            "agent/ping": self._handle_ping,
            "agent/status": self._handle_status_request,
            "agent/shutdown": self._handle_shutdown,
            "task_request": self._handle_task_execution,
            "registration_confirmed": self._handle_registration_confirmation,
            "error": self._handle_error_message
        }
        
        # Task tracking
        self.active_tasks: Dict[str, Dict[str, Any]] = {}  # task_id -> task_info
        self.task_timeout = config.get("task_timeout", 3600)  # 1 hour
        
        self.logger.info(f"MCP Agent {self.agent_id} initialized")

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Return list of agent capabilities."""
        pass

    @abstractmethod
    def setup_task_handlers(self) -> Dict[str, Callable]:
        """Setup task handlers for this agent."""
        pass

    async def start(self):
        """Start the MCP agent."""
        self.running = True
        
        # Setup signal handlers for graceful shutdown
        for sig in [signal.SIGTERM, signal.SIGINT]:
            signal.signal(sig, self._signal_handler)
        
        # Setup task handlers
        self.task_handlers = self.setup_task_handlers()
        
        # Start connection and heartbeat
        try:
            await self._connect_with_retry()
            asyncio.create_task(self._heartbeat_loop())
            asyncio.create_task(self._task_cleanup_loop())
            
            while self.running:
                if not self.connected:
                    self.logger.warning("Connection lost, attempting to reconnect...")
                    await self._connect_with_retry()
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("Shutdown signal received")
        except Exception as e:
            self.logger.error(f"Fatal error in agent: {e}")
            raise
        finally:
            await self.stop()

    async def stop(self):
        """Stop the MCP agent."""
        self.running = False
        
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
                    # Send unregister message
                    await self._send_message({
                        "type": "agent_unregister",
                        "agent_id": self.agent_id,
                        "timestamp": datetime.now().isoformat()
                    })
                
                await self.websocket.close()
            except Exception as e:
                self.logger.error(f"Error closing WebSocket: {e}")
        
        self.connected = False
        self.websocket = None
        self.logger.info(f"MCP Agent {self.agent_id} stopped")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, initiating shutdown...")
        self.running = False

    async def _connect_with_retry(self):
        """Connect to MCP server with exponential backoff and jitter."""
        self.connection_attempts = 0
        max_retries = self.max_retries
        base_delay = self.base_retry_delay
        
        while self.connection_attempts < max_retries and self.running:
            try:
                self.connection_attempts += 1
                self.logger.info(f"Connecting to MCP server at {self.mcp_server_url} (attempt {self.connection_attempts})")
                
                self.websocket = await websockets.connect(
                    self.mcp_server_url,
                    ping_interval=self.heartbeat_interval,
                    ping_timeout=self.ping_timeout,
                    close_timeout=10,
                    max_size=1024*1024  # 1MB max message size
                )
                
                # Register with MCP server
                await self._register_agent()
                
                # Start message handler
                asyncio.create_task(self._handle_messages())
                
                self.connected = True
                self.connection_attempts = 0
                self.last_connection_attempt = datetime.now()
                self.logger.info("Successfully connected to MCP server")
                return
                
            except Exception as e:
                self.logger.warning(f"Connection failed (attempt {self.connection_attempts}): {e}")
                if self.connection_attempts < max_retries:
                    # Exponential backoff with jitter: delay = base_delay * 2^attempt + random(0, 100ms)
                    delay = (base_delay * (2 ** min(self.connection_attempts - 1, 5))) + (random.random() * 0.1)
                    self.logger.info(f"Retrying in {delay:.2f} seconds...")
                    await asyncio.sleep(delay)
                else:
                    self.logger.error("Failed to connect after all retries")
                    raise ConnectionError(f"Failed to connect to MCP server after {max_retries} attempts")

    async def _register_agent(self):
        """Register this agent with MCP server."""
        registration = {
            "type": "agent_register",
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": self.get_capabilities(),
            "timestamp": datetime.now().isoformat()
        }
        
        await self._send_message(registration)
        self.logger.info(f"Sent registration for agent {self.agent_id} with capabilities: {self.get_capabilities()}")

    async def _send_message(self, message: Dict[str, Any]):
        """Send message to MCP server."""
        if not self.websocket:
            self.logger.warning("Cannot send message: WebSocket not connected")
            self.connected = False
            return
        
        # Check if websocket is closed using compatible method
        try:
            if hasattr(self.websocket, 'closed') and self.websocket.closed:
                self.logger.warning("Cannot send message: WebSocket is closed")
                self.connected = False
                return
            elif hasattr(self.websocket, 'state') and self.websocket.state.name != 'OPEN':
                self.logger.warning("Cannot send message: WebSocket is not open")
                self.connected = False
                return
        except AttributeError:
            # Fallback if neither attribute exists
            pass
        
        try:
            message_str = json.dumps(message)
            await self.websocket.send(message_str)
            self.logger.debug(f"Sent message: {message.get('type', 'unknown')}")
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            self.connected = False

    async def _handle_messages(self):
        """Handle incoming MCP messages."""
        try:
            if not self.websocket:
                return
                
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._process_mcp_message(data)
                except json.JSONDecodeError as e:
                    self.logger.error(f"Invalid JSON received: {e}")
                except Exception as e:
                    self.logger.error(f"Error processing message: {e}")
                    
        except ConnectionClosed:
            self.logger.warning("MCP server connection closed")
            self.connected = False
        except Exception as e:
            self.logger.error(f"Error in message handler: {e}")
            self.connected = False

    async def _process_mcp_message(self, data: Dict[str, Any]):
        """Process incoming MCP message."""
        try:
            message_type = data.get("type")
            if not message_type:
                self.logger.warning("Received message with no type")
                return
                
            handler = self.message_handlers.get(message_type)
            if handler:
                await handler(data)
            else:
                self.logger.warning(f"Unknown message type: {message_type}")
                
        except Exception as e:
            self.logger.error(f"Error processing MCP message: {e}")

    async def _handle_task_execution(self, data: Dict[str, Any]):
        """Handle task execution request."""
        task_id = None
        try:
            task_id = data.get("task_id")
            task_type = data.get("task_type")
            task_data = data.get("data", {})
            context_id = data.get("context_id")
            
            if not task_id or not task_type:
                self.logger.error(f"Invalid task request: missing task_id or task_type")
                await self._send_message({
                    "type": "task_result",
                    "task_id": task_id or "unknown",
                    "status": "error",
                    "error": "Missing task_id or task_type"
                })
                return
            
            self.logger.info(f"Executing task: {task_type} (ID: {task_id})")
            
            # Track task
            self.active_tasks[task_id] = {
                "task_type": task_type,
                "context_id": context_id,
                "data": task_data,
                "created_at": datetime.now()
            }
            
            # Route to appropriate handler
            if task_type in self.task_handlers:
                try:
                    handler = self.task_handlers[task_type]
                    result = await handler(task_data)
                    
                    # Send success response
                    await self._send_message({
                        "type": "task_result",
                        "task_id": task_id,
                        "status": "completed",
                        "result": result,
                        "agent_id": self.agent_id,
                        "timestamp": datetime.now().isoformat()
                    })
                except Exception as e:
                    self.logger.error(f"Task execution failed: {e}")
                    await self._send_message({
                        "type": "task_result",
                        "task_id": task_id,
                        "status": "error",
                        "error": str(e),
                        "agent_id": self.agent_id,
                        "timestamp": datetime.now().isoformat()
                    })
            else:
                self.logger.error(f"Unknown task type: {task_type}")
                await self._send_message({
                    "type": "task_result",
                    "task_id": task_id,
                    "status": "error",
                    "error": f"Unknown task type: {task_type}",
                    "data": {"available_tasks": list(self.task_handlers.keys())},
                    "agent_id": self.agent_id,
                    "timestamp": datetime.now().isoformat()
                })
            
            # Clean up task
            self.active_tasks.pop(task_id, None)
            
        except Exception as e:
            self.logger.error(f"Error handling task execution: {e}")
            if task_id:
                await self._send_message({
                    "type": "task_result",
                    "task_id": task_id,
                    "status": "error",
                    "error": str(e),
                    "agent_id": self.agent_id,
                    "timestamp": datetime.now().isoformat()
                })

    async def _handle_ping(self, data: Dict[str, Any]):
        """Handle ping request."""
        await self._send_message({
            "type": "heartbeat_ack",
            "agent_id": self.agent_id,
            "status": "alive",
            "timestamp": datetime.now().isoformat()
        })

    async def _handle_status_request(self, data: Dict[str, Any]):
        """Handle status request."""
        await self._send_message({
            "type": "status_response",
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": "ready" if self.connected else "disconnected",
            "capabilities": self.get_capabilities(),
            "connection": {
                "connected": self.connected,
                "server_url": self.mcp_server_url,
                "last_connection": self.last_connection_attempt.isoformat() if self.last_connection_attempt else None
            },
            "tasks": {
                "active_tasks": len(self.active_tasks),
                "available_handlers": list(self.task_handlers.keys())
            },
            "timestamp": datetime.now().isoformat()
        })

    async def _handle_registration_confirmation(self, data: Dict[str, Any]):
        """Handle registration confirmation from server."""
        server_id = data.get("server_id")
        self.logger.info(f"Registration confirmed by server {server_id}")
        # Process any additional server instructions if present
        if "instructions" in data:
            self.logger.info(f"Received server instructions: {data['instructions']}")

    async def _handle_error_message(self, data: Dict[str, Any]):
        """Handle error messages from server."""
        message = data.get("message", "Unknown error")
        task_id = data.get("task_id")
        self.logger.error(f"Received error from server: {message}" + (f" for task {task_id}" if task_id else ""))
        if task_id and task_id in self.active_tasks:
            self.active_tasks.pop(task_id)

    async def _handle_shutdown(self, data: Dict[str, Any]):
        """Handle shutdown request."""
        self.logger.info("Shutdown requested via MCP")
        await self._send_message({
            "type": "shutdown_ack",
            "agent_id": self.agent_id,
            "status": "shutting_down",
            "timestamp": datetime.now().isoformat()
        })
        self.running = False

    async def _task_cleanup_loop(self):
        """Clean up expired tasks."""
        while self.running:
            try:
                current_time = datetime.now()
                expired_tasks = [
                    task_id for task_id, task in self.active_tasks.items()
                    if (current_time - task["created_at"]).total_seconds() > self.task_timeout
                ]
                
                for task_id in expired_tasks:
                    self.logger.warning(f"Task {task_id} timed out")
                    await self._send_message({
                        "type": "task_result",
                        "task_id": task_id,
                        "status": "timeout",
                        "error": "Task execution timeout",
                        "agent_id": self.agent_id,
                        "timestamp": datetime.now().isoformat()
                    })
                    self.active_tasks.pop(task_id)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error in task cleanup loop: {e}")
                await asyncio.sleep(60)

    async def _heartbeat_loop(self):
        """Send periodic heartbeat to MCP server."""
        while self.running:
            try:
                if (self.connected and self.websocket and 
                    hasattr(self.websocket, 'closed') and not self.websocket.closed):
                    await self._send_message({
                        "type": "heartbeat",
                        "agent_id": self.agent_id,
                        "status": "alive",
                        "timestamp": datetime.now().isoformat()
                    })
                elif (self.connected and self.websocket and 
                      hasattr(self.websocket, 'state') and 
                      self.websocket.state.name == 'OPEN'):
                    await self._send_message({
                        "type": "heartbeat",
                        "agent_id": self.agent_id,
                        "status": "alive",
                        "timestamp": datetime.now().isoformat()
                    })
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                self.logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(self.heartbeat_interval)

    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from file."""
        config_file = Path(config_path)
        if config_file.exists():
            try:
                with open(config_file) as f:
                    config = json.load(f)
                self.logger.info(f"Loaded config from {config_path}")
                return config
            except Exception as e:
                self.logger.error(f"Error loading config from {config_path}: {e}")
        
        # Return default config
        default_config = {
            "mcp_server_url": "ws://mcp-server:9000",
            "heartbeat_interval": 30,
            "ping_timeout": 10,
            "max_retries": 15,
            "base_retry_delay": 5,
            "task_timeout": 3600
        }
        self.logger.info("Using default configuration")
        return default_config

    async def update_config(self, new_config: Dict[str, Any]):
        """Update configuration dynamically."""
        self.logger.info("Updating agent configuration")
        self.config.update(new_config)
        
        # Update relevant attributes
        self.mcp_server_url = self.config.get("mcp_server_url", self.mcp_server_url)
        self.heartbeat_interval = self.config.get("heartbeat_interval", self.heartbeat_interval)
        self.ping_timeout = self.config.get("ping_timeout", self.ping_timeout)
        self.max_retries = self.config.get("max_retries", self.max_retries)
        self.base_retry_delay = self.config.get("base_retry_delay", self.base_retry_delay)
        self.task_timeout = self.config.get("task_timeout", self.task_timeout)
        
        self.logger.info("Configuration updated successfully")
        
        # Reconnect if server URL changed
        if new_config.get("mcp_server_url") and new_config["mcp_server_url"] != self.mcp_server_url:
            self.logger.info("Server URL changed, reconnecting...")
            self.connected = False
            if self.websocket:
                try:
                    await self.websocket.close()
                except:
                    pass
            await self._connect_with_retry()


def create_agent_main(agent_class, agent_type: str, config_path: str = "/app/config/config.json"):
    """
    Create main entry point for an agent.
    
    Args:
        agent_class: The agent class that inherits from BaseMCPAgent
        agent_type: The type identifier for the agent
        config_path: Path to configuration file
    """
    async def main():
        """Main entry point for MCP agent."""
        # Load configuration
        try:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file) as f:
                    config = json.load(f)
            else:
                config = {
                    "mcp_server_url": "ws://mcp-server:9000",
                    "heartbeat_interval": 30,
                    "ping_timeout": 10
                }
        except Exception as e:
            print(f"Error loading config: {e}")
            sys.exit(1)
        
        # Create and start agent
        agent = agent_class(agent_type, config)
        
        try:
            await agent.start()
        except KeyboardInterrupt:
            print(f"\n{agent_type} agent shutdown requested")
        except Exception as e:
            print(f"{agent_type} agent failed: {e}")
            sys.exit(1)
    
    return main
