#!/usr/bin/env python3
"""
Improved MCP Server with enhanced connection management and routing
Addresses routing and connection issues by:
- Implementing pending messages queue per entity_id for handling temporary disconnects
- Using entity_id consistently for sending messages
- Preserving tasks until successful send or buffer
- Improved late result delivery for AI services
- Added task timeout cleanup
- More robust logging and error handling
"""

import asyncio
import json
import logging
import os
import signal
import sys
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_server")


class MCPServer:
    """Improved MCP Server with better connectivity handling"""

    def __init__(self, host: str = "0.0.0.0", port: int = 9000):
        self.host = host
        self.port = port
        self.is_running = False
        self.server_id = str(uuid.uuid4())
        
        # Connection management
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}  # client_id -> ws
        self.agent_registry: Dict[str, Dict[str, Any]] = {}  # entity_id -> info
        self.agent_connections: Dict[str, str] = {}  # entity_id -> client_id
        self.connection_to_entity: Dict[str, str] = {}  # client_id -> entity_id
        
        # Pending messages for disconnected entities
        self.pending_messages: Dict[str, List[Dict[str, Any]]] = {}  # entity_id -> list of messages
        
        # Task management
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        
        # Task result buffer for late-arriving responses
        self.task_result_buffer: Dict[str, Dict[str, Any]] = {}
        self.max_buffer_age = 300  # Keep buffered results for 5 minutes
        self.task_timeout = 3600  # 1 hour timeout for active tasks
        
        logger.info(f"Improved MCP Server initialized: {self.server_id}")
    
    async def start(self):
        """Start the MCP server"""
        try:
            logger.info(f"Starting Improved MCP Server on {self.host}:{self.port}")
            
            # Start WebSocket server
            self.websocket_server = await websockets.serve(
                self._handle_connection,
                self.host,
                self.port,
                ping_interval=30,
                ping_timeout=60,
            )
            
            # Start background cleanup task
            asyncio.create_task(self._background_cleanup())
            
            self.is_running = True
            logger.info("Improved MCP Server started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Improved MCP Server: {e}")
            raise
    
    async def stop(self):
        """Stop the MCP server"""
        logger.info("Stopping Improved MCP Server")
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
        
        logger.info("Improved MCP Server stopped")
    
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
            elif message_type == "task_request":
                await self._handle_task_request_from_ai(client_id, data)
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
        self.connection_to_entity[client_id] = agent_id
        
        # Send registration confirmation
        await self._send_to_entity(agent_id, {
            "type": "registration_confirmed",
            "agent_id": agent_id,
            "server_id": self.server_id,
            "timestamp": datetime.now().isoformat()
        })
        
        # Deliver any pending messages
        await self._deliver_pending_messages(agent_id)
        
        logger.info(f"Agent registered: {agent_id} ({agent_type}) with capabilities: {capabilities}")
    
    async def _handle_gateway_registration(self, client_id: str, data: Dict[str, Any]):
        """Handle gateway registration"""
        gateway_id = data.get("client_id")  # Note: This is the gateway's own ID
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
        self.connection_to_entity[client_id] = gateway_id
        
        # Send registration confirmation
        await self._send_to_entity(gateway_id, {
            "type": "registration_confirmed",
            "client_id": gateway_id,
            "server_id": self.server_id,
            "timestamp": datetime.now().isoformat()
        })
        
        # Deliver any pending messages
        await self._deliver_pending_messages(gateway_id)
        
        logger.info(f"Gateway registered: {gateway_id} ({gateway_type})")
    
    async def _deliver_pending_messages(self, entity_id: str):
        """Deliver buffered messages to newly connected entity"""
        if entity_id not in self.pending_messages:
            return
        
        pending = self.pending_messages[entity_id].copy()
        self.pending_messages.pop(entity_id, None)
        
        for msg in pending:
            success = await self._send_to_entity(entity_id, msg)
            if not success:
                # If fails, it will be appended back in _send_to_entity
                pass
        
        logger.info(f"Delivered {len(pending)} pending messages to {entity_id}")
    
    async def _handle_research_action(self, client_id: str, data: Dict[str, Any]):
        """Handle research action from API Gateway"""
        try:
            requester_entity_id = self.connection_to_entity.get(client_id)
            if not requester_entity_id:
                await self._send_error(client_id, "Unregistered client")
                return
            
            task_data = data.get("data", {})
            
            task_id = task_data.get("task_id", str(uuid.uuid4()))
            agent_type = task_data.get("agent_type")
            action = task_data.get("action")
            payload = task_data.get("payload", {})
            context_id = task_data.get("context_id")
            
            logger.info(f"Processing research action: {action} for agent type: {agent_type} from {requester_entity_id}")
            
            if not agent_type or not action:
                await self._send_to_entity(requester_entity_id, {"type": "error", "message": "Missing agent_type or action"})
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
                await self._send_to_entity(requester_entity_id, {
                    "type": "task_rejected",
                    "data": {
                        "task_id": task_id,
                        "error": error_msg
                    }
                })
                logger.warning(error_msg)
                return
            
            # Select first available agent (can be improved to round-robin or load-based)
            selected_agent = suitable_agents[0]
            agent_client_id = self.agent_registry[selected_agent]["client_id"]
            
            # Store task
            self.active_tasks[task_id] = {
                "id": task_id,
                "type": action,
                "agent_type": agent_type,
                "data": payload,
                "context_id": context_id,
                "requester_id": requester_entity_id,
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
            await self._send_to_entity(requester_entity_id, {
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
            if requester_entity_id:
                await self._send_to_entity(requester_entity_id, {"type": "error", "message": error_msg})
            logger.error(error_msg)
    
    async def _handle_task_request_from_ai(self, client_id: str, data: Dict[str, Any]):
        """Handle task request from AI service"""
        try:
            requester_entity_id = self.connection_to_entity.get(client_id)
            if not requester_entity_id:
                await self._send_error(client_id, "Unregistered client")
                return
            
            task_data = data.get("data", {})
            
            task_id = task_data.get("task_id", str(uuid.uuid4()))
            agent_type = task_data.get("agent_type")
            action = task_data.get("action")
            payload = task_data.get("payload", {})
            context_id = task_data.get("context_id")
            
            logger.info(f"Processing AI task request: {action} for agent type: {agent_type} from {requester_entity_id}")
            
            if not agent_type or not action:
                await self._send_to_entity(requester_entity_id, {
                    "type": "task_result",
                    "task_id": task_id,
                    "status": "error",
                    "error": "Missing agent_type or action"
                })
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
                await self._send_to_entity(requester_entity_id, {
                    "type": "task_result",
                    "task_id": task_id,
                    "status": "error",
                    "error": error_msg
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
                "requester_id": requester_entity_id,
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
            
            logger.info(f"AI task routed: {task_id} -> {selected_agent}")
            
        except Exception as e:
            error_msg = f"Error processing AI task request: {str(e)}"
            if requester_entity_id:
                await self._send_to_entity(requester_entity_id, {"type": "error", "message": error_msg})
            logger.error(error_msg)
    
    async def _handle_task_result(self, client_id: str, data: Dict[str, Any]):
        """Handle task result from agent"""
        task_id = data.get("task_id")
        result = data.get("result")
        status = data.get("status", "completed")
        error = data.get("error")
        
        if not task_id:
            logger.error("Received task result with no task_id")
            return
        
        logger.info(f"Received task result for {task_id}: {status}")
        
        message = {
            "type": "task_result",
            "task_id": task_id,
            "result": result,
            "status": status,
            "error": error
        }
        
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            requester_id = task["requester_id"]
            
            success = await self._send_to_entity(requester_id, message)
            
            if success:
                logger.info(f"Task result delivered successfully for {task_id}")
                del self.active_tasks[task_id]
            else:
                logger.warning(f"Buffering task result for {task_id} due to delivery failure")
                # Since buffered in pending_messages, task can be removed or kept; here remove
                del self.active_tasks[task_id]
        else:
            # Late-arriving result
            logger.warning(f"Late task result for {task_id}, attempting delivery")
            self.task_result_buffer[task_id] = {
                "message": message,
                "received_at": datetime.now(),
                "attempts": 0
            }
            await self._attempt_late_delivery(task_id)
    
    async def _attempt_late_delivery(self, task_id: str):
        """Attempt to deliver a buffered task result"""
        if task_id not in self.task_result_buffer:
            return
        
        buffered = self.task_result_buffer[task_id]
        buffered["attempts"] += 1
        
        # Find all AI service entities
        ai_services = [
            agent_id for agent_id, info in self.agent_registry.items()
            if info["agent_type"] == "ai_service" and agent_id in self.agent_connections
        ]
        
        delivered = False
        for ai_id in ai_services:
            success = await self._send_to_entity(ai_id, buffered["message"])
            if success:
                delivered = True
                logger.info(f"Late delivery successful to {ai_id} for {task_id}")
                break
        
        if delivered:
            del self.task_result_buffer[task_id]
        else:
            logger.warning(f"Late delivery failed for {task_id} after {buffered['attempts']} attempts")
    
    async def _cleanup_task_buffer(self):
        """Clean up old entries from the task result buffer"""
        current_time = datetime.now()
        expired = [
            tid for tid, buf in self.task_result_buffer.items()
            if (current_time - buf["received_at"]).total_seconds() > self.max_buffer_age
        ]
        for tid in expired:
            logger.info(f"Cleaning up expired buffered result for {tid}")
            del self.task_result_buffer[tid]
    
    async def _cleanup_expired_tasks(self):
        """Clean up expired active tasks"""
        current_time = datetime.now()
        expired = []
        for tid, task in self.active_tasks.items():
            age = (current_time - task["created_at"]).total_seconds()
            if age > self.task_timeout:
                expired.append(tid)
                message = {
                    "type": "task_result",
                    "task_id": tid,
                    "status": "timeout",
                    "error": "Task timed out"
                }
                await self._send_to_entity(task["requester_id"], message)
        
        for tid in expired:
            del self.active_tasks[tid]
    
    async def _background_cleanup(self):
        """Background task for cleanups"""
        while self.is_running:
            try:
                await self._cleanup_task_buffer()
                await self._cleanup_expired_tasks()
            except Exception as e:
                logger.error(f"Background cleanup error: {e}")
            await asyncio.sleep(60)
    
    async def _handle_heartbeat(self, client_id: str, data: Dict[str, Any]):
        """Handle heartbeat"""
        entity_id = self.connection_to_entity.get(client_id)
        if entity_id:
            await self._send_to_entity(entity_id, {
                "type": "heartbeat_ack",
                "agent_id": entity_id,
                "timestamp": datetime.now().isoformat()
            })
    
    async def _send_to_entity(self, entity_id: str, message: Dict[str, Any]) -> bool:
        """Send message to entity, buffer if disconnected"""
        current_client_id = self.agent_connections.get(entity_id)
        if not current_client_id or current_client_id not in self.clients:
            logger.warning(f"No active connection for {entity_id}, buffering message")
            self.pending_messages.setdefault(entity_id, []).append(message)
            return False
        
        try:
            ws = self.clients[current_client_id]
            await ws.send(json.dumps(message))
            logger.info(f"Message sent to {entity_id} ({current_client_id}): {message.get('type')}")
            return True
        except Exception as e:
            logger.error(f"Send failed to {entity_id} ({current_client_id}): {e}")
            await self._cleanup_client(current_client_id)
            self.pending_messages.setdefault(entity_id, []).append(message)
            return False
    
    async def _send_error(self, client_id: str, error_message: str):
        """Send error message to client (fallback to old method for unregistered)"""
        await self._send_message(client_id, {
            "type": "error",
            "message": error_message,
            "timestamp": datetime.now().isoformat()
        })
    
    async def _send_message(self, client_id: str, message: Dict[str, Any]) -> bool:
        """Legacy direct send to client_id (used for task requests to agents)"""
        if client_id not in self.clients:
            logger.error(f"Client {client_id} not found")
            return False
        
        try:
            ws = self.clients[client_id]
            await ws.send(json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"Direct send failed to {client_id}: {e}")
            await self._cleanup_client(client_id)
            return False
    
    async def _cleanup_client(self, client_id: str):
        """Clean up client connection"""
        entity_id = self.connection_to_entity.pop(client_id, None)
        self.clients.pop(client_id, None)
        
        if entity_id:
            if entity_id in self.agent_connections and self.agent_connections[entity_id] == client_id:
                del self.agent_connections[entity_id]
            if entity_id in self.agent_registry:
                self.agent_registry[entity_id]["status"] = "disconnected"
            logger.info(f"Entity disconnected: {entity_id}")
    
    def get_status(self):
        """Get server status"""
        return {
            "server_id": self.server_id,
            "is_running": self.is_running,
            "active_agents": len(self.agent_registry),
            "active_tasks": len(self.active_tasks),
            "pending_messages": {k: len(v) for k, v in self.pending_messages.items()},
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
    server = MCPServer(
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