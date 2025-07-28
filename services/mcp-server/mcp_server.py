#!/usr/bin/env python3
"""
Simple MCP Server for testing connectivity issues
Focuses on basic message routing without advanced features
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
from websockets.exceptions import ConnectionClosed, WebSocketException

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("simple_mcp_server")


class SimpleMCPServer:
    """Simple MCP Server for testing connectivity"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 9000):
        self.host = host
        self.port = port
        self.is_running = False
        self.server_id = str(uuid.uuid4())
        
        # Connection management
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.agent_registry: Dict[str, Dict[str, Any]] = {}
        self.agent_connections: Dict[str, str] = {}  # agent_id -> client_id
        
        # Task management
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"Simple MCP Server initialized: {self.server_id}")
    
    async def start(self):
        """Start the MCP server"""
        try:
            logger.info(f"Starting Simple MCP Server on {self.host}:{self.port}")
            
            # Start WebSocket server
            self.websocket_server = await websockets.serve(
                self._handle_connection,
                self.host,
                self.port,
                ping_interval=30,
                ping_timeout=60,
            )
            
            self.is_running = True
            logger.info("Simple MCP Server started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Simple MCP Server: {e}")
            raise
    
    async def stop(self):
        """Stop the MCP server"""
        logger.info("Stopping Simple MCP Server")
        self.is_running = False
        
        # Close all client connections
        if self.clients:
            await asyncio.gather(
                *[client.close() for client in self.clients.values()],
                return_exceptions=True
            )
        
        # Close WebSocket server
        if hasattr(self, 'websocket_server'):
            self.websocket_server.close()
            await self.websocket_server.wait_closed()
        
        logger.info("Simple MCP Server stopped")
    
    async def _handle_connection(self, websocket, path):
        """Handle new WebSocket connection"""
        client_id = str(uuid.uuid4())
        self.clients[client_id] = websocket
        
        logger.info(f"New client connected: {client_id}")
        
        try:
            async for message in websocket:
                await self._handle_message(client_id, message)
                
        except ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"Connection error for {client_id}: {e}")
        finally:
            await self._cleanup_client(client_id)
    
    async def _handle_message(self, client_id: str, message: str):
        """Handle incoming message from client"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            logger.info(f"Received message from {client_id}: {message_type}")
            
            if message_type == "agent_register":
                await self._handle_agent_registration(client_id, data)
            elif message_type == "gateway_register":
                await self._handle_gateway_registration(client_id, data)
            elif message_type == "research_action":
                await self._handle_research_action(client_id, data)
            elif message_type == "task_result":
                await self._handle_task_result(client_id, data)
            elif message_type == "heartbeat":
                await self._handle_heartbeat(client_id, data)
            else:
                logger.warning(f"Unknown message type from {client_id}: {message_type}")
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from {client_id}")
        except Exception as e:
            logger.error(f"Message handling error for {client_id}: {e}")
    
    async def _handle_agent_registration(self, client_id: str, data: Dict[str, Any]):
        """Handle agent registration"""
        agent_id = data.get("agent_id")
        agent_type = data.get("agent_type")
        capabilities = data.get("capabilities", [])
        
        if not agent_id or not agent_type:
            await self._send_error(client_id, "Missing agent_id or agent_type")
            return
        
        # Register agent
        self.agent_registry[agent_id] = {
            "client_id": client_id,
            "agent_type": agent_type,
            "capabilities": capabilities,
            "status": "active",
            "registered_at": datetime.now(),
        }
        
        self.agent_connections[agent_id] = client_id
        
        # Send registration confirmation
        await self._send_message(client_id, {
            "type": "registration_confirmed",
            "agent_id": agent_id,
            "server_id": self.server_id,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"Agent registered: {agent_id} ({agent_type}) with capabilities: {capabilities}")
    
    async def _handle_gateway_registration(self, client_id: str, data: Dict[str, Any]):
        """Handle gateway registration"""
        gateway_id = data.get("client_id")
        gateway_type = data.get("client_type")
        capabilities = data.get("capabilities", [])
        
        if not gateway_id or not gateway_type:
            await self._send_error(client_id, "Missing client_id or client_type")
            return
        
        # Register gateway
        self.agent_registry[gateway_id] = {
            "client_id": client_id,
            "agent_type": gateway_type,
            "capabilities": capabilities,
            "status": "active",
            "registered_at": datetime.now(),
        }
        
        self.agent_connections[gateway_id] = client_id
        
        # Send registration confirmation
        await self._send_message(client_id, {
            "type": "registration_confirmed",
            "client_id": gateway_id,
            "server_id": self.server_id,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"Gateway registered: {gateway_id} ({gateway_type})")
    
    async def _handle_research_action(self, client_id: str, data: Dict[str, Any]):
        """Handle research action from API Gateway"""
        try:
            task_data = data.get("data", {})
            
            # Debug: Log the complete data structure
            logger.info(f"Raw research action data: {data}")
            logger.info(f"Task data: {task_data}")
            
            # Extract task information
            task_id = task_data.get("task_id", str(uuid.uuid4()))
            agent_type = task_data.get("agent_type")
            action = task_data.get("action")
            payload = task_data.get("payload", {})
            context_id = task_data.get("context_id")
            
            logger.info(f"Processing research action: {action} for agent type: {agent_type}")
            
            if not agent_type or not action:
                await self._send_error(client_id, "Missing agent_type or action")
                return
            
            # Find suitable agents
            suitable_agents = [
                agent_id for agent_id, info in self.agent_registry.items()
                if (info["agent_type"] == agent_type and 
                    info["status"] == "active" and 
                    action in info.get("capabilities", []))
            ]
            
            if not suitable_agents:
                error_msg = f"No active {agent_type} agents found with capability: {action}"
                await self._send_message(client_id, {
                    "type": "task_rejected",
                    "data": {
                        "task_id": task_id,
                        "error": error_msg
                    }
                })
                logger.warning(error_msg)
                return
            
            # Select first available agent
            selected_agent = suitable_agents[0]
            agent_client_id = self.agent_registry[selected_agent]["client_id"]
            
            # Store task
            self.active_tasks[task_id] = {
                "id": task_id,
                "type": action,
                "agent_type": agent_type,
                "data": payload,
                "context_id": context_id,
                "client_id": client_id,
                "assigned_agent": selected_agent,
                "status": "processing",
                "created_at": datetime.now(),
            }
            
            # Send task to agent
            await self._send_message(agent_client_id, {
                "type": "task_request",
                "task_id": task_id,
                "task_type": action,
                "data": payload,
                "context_id": context_id
            })
            
            # Confirm to gateway
            await self._send_message(client_id, {
                "type": "task_queued",
                "data": {
                    "task_id": task_id,
                    "assigned_agent": selected_agent,
                    "agent_type": agent_type,
                    "status": "processing"
                }
            })
            
            logger.info(f"Research action routed: {task_id} -> {selected_agent}")
            
        except Exception as e:
            error_msg = f"Error processing research action: {str(e)}"
            await self._send_error(client_id, error_msg)
            logger.error(error_msg)
    
    async def _handle_task_result(self, client_id: str, data: Dict[str, Any]):
        """Handle task result from agent"""
        task_id = data.get("task_id")
        result = data.get("result")
        status = data.get("status", "completed")
        error = data.get("error")
        
        logger.info(f"Received task result for {task_id}: {status}")
        
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task["status"] = status
            task["result"] = result
            task["completed_at"] = datetime.now()
            
            # Send result to original client
            original_client_id = task["client_id"]
            if original_client_id in self.clients:
                await self._send_message(original_client_id, {
                    "type": "task_result",
                    "task_id": task_id,
                    "result": result,
                    "status": status,
                    "error": error
                })
            
            # Clean up
            self.active_tasks.pop(task_id, None)
    
    async def _handle_heartbeat(self, client_id: str, data: Dict[str, Any]):
        """Handle heartbeat"""
        agent_id = data.get("agent_id")
        if agent_id and agent_id in self.agent_registry:
            await self._send_message(client_id, {
                "type": "heartbeat_ack",
                "agent_id": agent_id,
                "timestamp": datetime.now().isoformat()
            })
    
    async def _send_message(self, client_id: str, message: Dict[str, Any]):
        """Send message to client"""
        if client_id not in self.clients:
            return
        
        try:
            websocket = self.clients[client_id]
            await websocket.send(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send message to {client_id}: {e}")
    
    async def _send_error(self, client_id: str, error_message: str):
        """Send error message to client"""
        await self._send_message(client_id, {
            "type": "error",
            "message": error_message,
            "timestamp": datetime.now().isoformat()
        })
    
    async def _cleanup_client(self, client_id: str):
        """Clean up client connection"""
        # Remove from clients
        self.clients.pop(client_id, None)
        
        # Find and remove agent registration
        agent_to_remove = None
        for agent_id, info in self.agent_registry.items():
            if info["client_id"] == client_id:
                agent_to_remove = agent_id
                break
        
        if agent_to_remove:
            agent_info = self.agent_registry.pop(agent_to_remove)
            self.agent_connections.pop(agent_to_remove, None)
            logger.info(f"Agent unregistered: {agent_to_remove}")
    
    def get_status(self):
        """Get server status"""
        return {
            "server_id": self.server_id,
            "is_running": self.is_running,
            "active_agents": len(self.agent_registry),
            "active_tasks": len(self.active_tasks),
            "registered_agents": {
                agent_id: {
                    "type": info["agent_type"],
                    "capabilities": info["capabilities"],
                    "status": info["status"]
                }
                for agent_id, info in self.agent_registry.items()
            }
        }


async def main():
    """Main entry point"""
    server = SimpleMCPServer(
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "9000"))
    )
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(server.stop())
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        await server.start()
        # Keep server running
        while server.is_running:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
