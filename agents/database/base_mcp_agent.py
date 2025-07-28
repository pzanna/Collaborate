"""
Base MCP Agent - Pure WebSocket Client Implementation

This base class provides the foundation for all research agents to communicate
exclusively through the MCP (Model Context Protocol) server via WebSocket.

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
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path
from abc import ABC, abstractmethod

import websockets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class BaseMCPAgent(ABC):
    """
    Base class for all MCP agents.
    
    Provides:
    - WebSocket connection management
    - MCP protocol handling
    - Agent registration
    - Task routing
    - Error handling
    - Graceful shutdown
    """
    
    def __init__(self, agent_type: str, config: Dict[str, Any]):
        """Initialize base MCP agent."""
        self.agent_type = agent_type
        self.agent_id = f"{agent_type}-{uuid.uuid4().hex[:8]}"
        self.config = config
        
        # Connection configuration
        self.mcp_server_url = config.get("mcp_server_url", "ws://mcp-server:9000")
        self.websocket = None
        self.connected = False
        self.running = False
        
        # Heartbeat configuration
        self.heartbeat_interval = config.get("heartbeat_interval", 30)
        self.ping_timeout = config.get("ping_timeout", 10)
        
        # Task handling
        self.task_handlers = {}
        self.message_handlers = {
            "task/execute": self._handle_task_execution,
            "agent/ping": self._handle_ping,
            "agent/status": self._handle_status_request,
            "agent/shutdown": self._handle_shutdown
        }
        
        # Setup logging
        self.logger = logging.getLogger(f"{agent_type}-agent")
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
        
        # Connect to MCP server with retry logic
        await self._connect_with_retry()
        
        # Start heartbeat
        asyncio.create_task(self._heartbeat_loop())
        
        # Keep agent running
        try:
            while self.running:
                if not self.connected:
                    self.logger.warning("Connection lost, attempting to reconnect...")
                    await self._connect_with_retry()
                
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("Shutdown signal received")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the MCP agent."""
        self.running = False
        
        if self.websocket and not self.websocket.closed:
            try:
                # Send unregister message
                await self._send_message({
                    "jsonrpc": "2.0",
                    "method": "agent/unregister",
                    "params": {
                        "agent_id": self.agent_id
                    }
                })
                
                await self.websocket.close()
            except Exception as e:
                self.logger.error(f"Error closing websocket: {e}")
        
        self.logger.info(f"MCP Agent {self.agent_id} stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, initiating shutdown...")
        self.running = False
    
    async def _connect_with_retry(self):
        """Connect to MCP server with retry logic."""
        max_retries = 15
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Connecting to MCP server at {self.mcp_server_url} (attempt {attempt + 1})")
                
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
                self.logger.info("Successfully connected to MCP server")
                return
                
            except Exception as e:
                self.logger.warning(f"Failed to connect (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (2 ** min(attempt, 3)))  # Exponential backoff
                else:
                    self.logger.error("Failed to connect after all retries")
                    raise
    
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
        self.logger.info(f"Registered agent {self.agent_id} with capabilities: {self.get_capabilities()}")
    
    async def _send_message(self, message: Dict[str, Any]):
        """Send message to MCP server."""
        if self.websocket and not self.websocket.closed:
            try:
                message_str = json.dumps(message)
                await self.websocket.send(message_str)
                self.logger.debug(f"Sent message: {message.get('method', message.get('type', 'unknown'))}")
            except Exception as e:
                self.logger.error(f"Error sending message: {e}")
                self.connected = False
        else:
            self.logger.warning("Cannot send message: WebSocket not connected")
    
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
                    
        except websockets.exceptions.ConnectionClosed:
            self.logger.warning("MCP server connection closed")
            self.connected = False
        except Exception as e:
            self.logger.error(f"Error in message handler: {e}")
            self.connected = False
    
    async def _process_mcp_message(self, data: Dict[str, Any]):
        """Process incoming MCP message."""
        try:
            # Handle JSON-RPC requests
            if "method" in data:
                method = data["method"]
                params = data.get("params", {})
                request_id = data.get("id")
                
                if method in self.message_handlers:
                    handler = self.message_handlers[method]
                    await handler(params, request_id)
                else:
                    self.logger.warning(f"Unknown method: {method}")
                    
                    # Send error response for unknown methods
                    if request_id:
                        error_response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32601,
                                "message": f"Method not found: {method}"
                            }
                        }
                        await self._send_message(error_response)
                        
            # Handle notifications
            elif data.get("jsonrpc") == "2.0" and "result" in data:
                # Response to our request
                self.logger.debug(f"Received response: {data.get('id')}")
                
            elif "type" in data:
                # Handle legacy message types
                await self._handle_legacy_message(data)
                
        except Exception as e:
            self.logger.error(f"Error processing MCP message: {e}")
    
    async def _handle_legacy_message(self, data: Dict[str, Any]):
        """Handle legacy message formats."""
        message_type = data.get("type")
        if message_type == "notification":
            self.logger.info(f"Received notification: {data.get('message', 'No message')}")
        else:
            self.logger.warning(f"Unknown legacy message type: {message_type}")
    
    async def _handle_task_execution(self, params: Dict[str, Any], request_id: Optional[str]):
        """Handle task execution request."""
        try:
            task_type = params.get("task_type")
            task_data = params.get("data", {})
            task_id = params.get("task_id", str(uuid.uuid4()))
            
            self.logger.info(f"Executing task: {task_type} (ID: {task_id})")
            
            # Route to appropriate handler
            if task_type in self.task_handlers:
                handler = self.task_handlers[task_type]
                result = await handler(task_data)
                
                # Send success response
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "status": "completed",
                        "task_id": task_id,
                        "data": result,
                        "agent_id": self.agent_id,
                        "timestamp": datetime.now().isoformat()
                    }
                }
            else:
                # Unknown task type
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown task type: {task_type}",
                        "data": {
                            "available_tasks": list(self.task_handlers.keys())
                        }
                    }
                }
            
            await self._send_message(response)
            
        except Exception as e:
            self.logger.error(f"Error handling task execution: {e}")
            
            # Send error response
            error_response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": "Internal error during task execution",
                    "data": {
                        "error": str(e),
                        "task_type": params.get("task_type", "unknown")
                    }
                }
            }
            await self._send_message(error_response)
    
    async def _handle_ping(self, params: Dict[str, Any], request_id: Optional[str]):
        """Handle ping request."""
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "status": "alive",
                "agent_id": self.agent_id,
                "timestamp": datetime.now().isoformat(),
                "uptime": "running"  # Could calculate actual uptime
            }
        }
        await self._send_message(response)
    
    async def _handle_status_request(self, params: Dict[str, Any], request_id: Optional[str]):
        """Handle status request."""
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "status": "ready" if self.connected else "disconnected",
                "capabilities": self.get_capabilities(),
                "connection": {
                    "connected": self.connected,
                    "server_url": self.mcp_server_url
                },
                "tasks": {
                    "available_handlers": list(self.task_handlers.keys()),
                    "total_handlers": len(self.task_handlers)
                },
                "timestamp": datetime.now().isoformat()
            }
        }
        await self._send_message(response)
    
    async def _handle_shutdown(self, params: Dict[str, Any], request_id: Optional[str]):
        """Handle shutdown request."""
        self.logger.info("Shutdown requested via MCP")
        
        # Send acknowledgment
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "status": "shutting_down",
                "agent_id": self.agent_id,
                "timestamp": datetime.now().isoformat()
            }
        }
        await self._send_message(response)
        
        # Initiate shutdown
        self.running = False
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeat to MCP server."""
        while self.running:
            try:
                if self.connected and self.websocket and not self.websocket.closed:
                    heartbeat = {
                        "type": "heartbeat",
                        "agent_id": self.agent_id,
                        "timestamp": datetime.now().isoformat()
                    }
                    await self._send_message(heartbeat)
                
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
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading config from {config_path}: {e}")
        
        # Return default config
        return {
            "mcp_server_url": "ws://mcp-server:9000",
            "heartbeat_interval": 30,
            "ping_timeout": 10
        }


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
