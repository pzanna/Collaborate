#!/usr/bin/env python3
"""
Enhanced MCP Server - Version 0.3.1
Containerized MCP Server with clustering, enhanced monitoring, and agent coordination
"""

import asyncio
import logging
import os
import signal
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
import json

import websockets
import redis.asyncio as redis
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import structlog

from config import EnhancedMCPServerConfig, get_enhanced_config, validate_config


# Prometheus metrics
CONNECTED_AGENTS = Gauge('mcp_connected_agents_total', 'Total connected agents', ['agent_type'])
TASK_DURATION = Histogram('mcp_task_duration_seconds', 'Task processing duration', ['task_type'])
MESSAGE_COUNTER = Counter('mcp_messages_total', 'Total messages processed', ['direction', 'type'])
ERROR_COUNTER = Counter('mcp_errors_total', 'Total errors', ['error_type'])


class EnhancedMCPServer:
    """Enhanced MCP Server for Version 0.3.1 with clustering and monitoring"""
    
    def __init__(self, config: EnhancedMCPServerConfig):
        self.config = config
        
        # Validate configuration
        if not validate_config(config):
            raise ValueError("Invalid server configuration")
        
        # Setup structured logging
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer() if config.log_format == "json" else structlog.dev.ConsoleRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        self.logger = structlog.get_logger("enhanced_mcp_server")
        
        # Server state
        self.server_id = config.cluster_node_id or str(uuid.uuid4())
        self.is_running = False
        self.start_time = datetime.now()
        
        # Connection management
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.agent_registry: Dict[str, Dict[str, Any]] = {}
        self.agent_connections: Dict[str, str] = {}  # agent_id -> client_id
        
        # Task management
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue(maxsize=config.max_concurrent_tasks)
        
        # Clustering components
        self.redis_client: Optional[redis.Redis] = None
        self.cluster_peers: Set[str] = set()
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        
        # WebSocket server
        self.websocket_server: Optional[Any] = None
        
        # Statistics
        self.stats = {
            "server_id": self.server_id,
            "started_at": self.start_time,
            "total_connections": 0,
            "total_tasks_processed": 0,
            "total_messages": 0,
            "active_agents": 0,
        }
    
    async def start(self):
        """Start the enhanced MCP server"""
        try:
            self.logger.info("Starting Enhanced MCP Server", 
                           server_id=self.server_id, 
                           config=self.config.__dict__)
            
            # Initialize Redis connection
            await self._init_redis()
            
            # Start metrics server
            if self.config.enable_metrics:
                start_http_server(self.config.metrics_port)
                self.logger.info("Metrics server started", port=self.config.metrics_port)
            
            # Start background tasks
            await self._start_background_tasks()
            
            # Register in cluster if enabled
            if self.config.cluster_enabled:
                await self._register_in_cluster()
            
            # Start WebSocket server
            self.websocket_server = await websockets.serve(
                self._handle_connection,
                self.config.host,
                self.config.port,
                ping_interval=self.config.websocket_ping_interval,
                ping_timeout=self.config.websocket_ping_timeout,
                max_size=self.config.websocket_max_size,
            )
            
            self.is_running = True
            self.logger.info("Enhanced MCP Server started successfully",
                           host=self.config.host,
                           port=self.config.port,
                           max_connections=self.config.max_connections)
            
            # Setup signal handlers
            self._setup_signal_handlers()
            
        except Exception as e:
            self.logger.error("Failed to start Enhanced MCP Server", error=str(e))
            await self.stop()
            raise
    
    async def stop(self):
        """Stop the enhanced MCP server gracefully"""
        self.logger.info("Stopping Enhanced MCP Server", server_id=self.server_id)
        
        self.is_running = False
        
        # Deregister from cluster
        if self.config.cluster_enabled and self.redis_client:
            await self._deregister_from_cluster()
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        # Close all client connections
        if self.clients:
            await asyncio.gather(
                *[client.close() for client in self.clients.values()],
                return_exceptions=True
            )
        
        # Close WebSocket server
        if self.websocket_server:
            self.websocket_server.close()
            await self.websocket_server.wait_closed()
        
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()
        
        self.logger.info("Enhanced MCP Server stopped gracefully")
    
    async def _init_redis(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(
                self.config.redis_url,
                max_connections=self.config.redis_max_connections,
                retry_on_timeout=True
            )
            
            # Test connection
            await self.redis_client.ping()
            self.logger.info("Redis connection established", url=self.config.redis_url)
            
        except Exception as e:
            self.logger.error("Failed to connect to Redis", error=str(e))
            raise
    
    async def _start_background_tasks(self):
        """Start background maintenance tasks"""
        self.background_tasks.extend([
            asyncio.create_task(self._heartbeat_monitor()),
            asyncio.create_task(self._task_processor()),
            asyncio.create_task(self._metrics_collector()),
            asyncio.create_task(self._health_check_server()),
        ])
        
        if self.config.cluster_enabled:
            self.background_tasks.append(
                asyncio.create_task(self._cluster_discovery())
            )
    
    async def _handle_connection(self, websocket, path):
        """Handle new WebSocket connection"""
        client_id = str(uuid.uuid4())
        self.clients[client_id] = websocket
        self.stats["total_connections"] += 1
        
        self.logger.info("New client connected", 
                        client_id=client_id, 
                        remote_address=websocket.remote_address)
        
        try:
            async for message in websocket:
                await self._handle_message(client_id, message)
                
        except websockets.exceptions.ConnectionClosed:
            self.logger.info("Client disconnected", client_id=client_id)
        except Exception as e:
            self.logger.error("Connection error", client_id=client_id, error=str(e))
            ERROR_COUNTER.labels(error_type="connection_error").inc()
        finally:
            await self._cleanup_client(client_id)
    
    async def _handle_message(self, client_id: str, message: str):
        """Handle incoming message from client"""
        try:
            data = json.loads(message)
            MESSAGE_COUNTER.labels(direction="inbound", type=data.get("type", "unknown")).inc()
            
            message_type = data.get("type")
            
            if message_type == "agent_register":
                await self._handle_agent_registration(client_id, data)
            elif message_type == "task_submit":
                await self._handle_task_submission(client_id, data)
            elif message_type == "task_result":
                await self._handle_task_result(client_id, data)
            elif message_type == "heartbeat":
                await self._handle_heartbeat(client_id, data)
            elif message_type == "agent_status":
                await self._handle_agent_status(client_id, data)
            elif message_type == "ai_request":
                await self._handle_ai_request(client_id, data)
            else:
                self.logger.warning("Unknown message type", 
                                  client_id=client_id, 
                                  message_type=message_type)
                
        except json.JSONDecodeError:
            self.logger.error("Invalid JSON message", client_id=client_id)
            ERROR_COUNTER.labels(error_type="json_decode").inc()
        except Exception as e:
            self.logger.error("Message handling error", 
                            client_id=client_id, 
                            error=str(e))
            ERROR_COUNTER.labels(error_type="message_handling").inc()
    
    async def _handle_agent_registration(self, client_id: str, data: Dict[str, Any]):
        """Handle agent registration"""
        agent_id = data.get("agent_id")
        agent_type = data.get("agent_type")
        capabilities = data.get("capabilities", [])
        
        if not agent_id or not agent_type:
            await self._send_error(client_id, "Missing agent_id or agent_type")
            return
        
        if agent_type not in self.config.allowed_agent_types:
            await self._send_error(client_id, f"Agent type '{agent_type}' not allowed")
            return
        
        # Register agent
        self.agent_registry[agent_id] = {
            "client_id": client_id,
            "agent_type": agent_type,
            "capabilities": capabilities,
            "status": "active",
            "registered_at": datetime.now(),
            "last_heartbeat": datetime.now(),
        }
        
        self.agent_connections[agent_id] = client_id
        self.stats["active_agents"] = len(self.agent_registry)
        
        # Update metrics
        CONNECTED_AGENTS.labels(agent_type=agent_type).inc()
        
        # Send registration confirmation
        await self._send_message(client_id, {
            "type": "registration_confirmed",
            "agent_id": agent_id,
            "server_id": self.server_id,
            "timestamp": datetime.now().isoformat()
        })
        
        self.logger.info("Agent registered", 
                        agent_id=agent_id, 
                        agent_type=agent_type,
                        capabilities=capabilities)
    
    async def _send_message(self, client_id: str, message: Dict[str, Any]):
        """Send message to client"""
        if client_id not in self.clients:
            return
        
        try:
            websocket = self.clients[client_id]
            await websocket.send(json.dumps(message))
            MESSAGE_COUNTER.labels(direction="outbound", type=message.get("type", "unknown")).inc()
            self.stats["total_messages"] += 1
            
        except Exception as e:
            self.logger.error("Failed to send message", 
                            client_id=client_id, 
                            error=str(e))
            ERROR_COUNTER.labels(error_type="send_message").inc()
    
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
            CONNECTED_AGENTS.labels(agent_type=agent_info["agent_type"]).dec()
            
            self.logger.info("Agent unregistered", 
                           agent_id=agent_to_remove,
                           agent_type=agent_info["agent_type"])
        
        self.stats["active_agents"] = len(self.agent_registry)
    
    async def _heartbeat_monitor(self):
        """Monitor agent heartbeats"""
        while self.is_running:
            try:
                current_time = datetime.now()
                expired_agents = []
                
                for agent_id, info in self.agent_registry.items():
                    time_since_heartbeat = (current_time - info["last_heartbeat"]).total_seconds()
                    if time_since_heartbeat > self.config.agent_registry_ttl:
                        expired_agents.append(agent_id)
                
                # Remove expired agents
                for agent_id in expired_agents:
                    agent_info = self.agent_registry.pop(agent_id, None)
                    if agent_info:
                        client_id = agent_info["client_id"]
                        self.agent_connections.pop(agent_id, None)
                        
                        # Close connection if still exists
                        if client_id in self.clients:
                            await self.clients[client_id].close()
                            self.clients.pop(client_id, None)
                        
                        CONNECTED_AGENTS.labels(agent_type=agent_info["agent_type"]).dec()
                        
                        self.logger.warning("Agent expired due to heartbeat timeout",
                                          agent_id=agent_id,
                                          agent_type=agent_info["agent_type"])
                
                await asyncio.sleep(self.config.heartbeat_interval)
                
            except Exception as e:
                self.logger.error("Heartbeat monitor error", error=str(e))
                await asyncio.sleep(5)
    
    async def _handle_heartbeat(self, client_id: str, data: Dict[str, Any]):
        """Handle agent heartbeat"""
        agent_id = data.get("agent_id")
        if agent_id and agent_id in self.agent_registry:
            self.agent_registry[agent_id]["last_heartbeat"] = datetime.now()
            await self._send_message(client_id, {
                "type": "heartbeat_ack",
                "agent_id": agent_id,
                "timestamp": datetime.now().isoformat()
            })
    
    async def _handle_task_submission(self, client_id: str, data: Dict[str, Any]):
        """Handle task submission from client"""
        task_id = data.get("task_id", str(uuid.uuid4()))
        task_type = data.get("task_type")
        task_data = data.get("task_data", {})
        
        # Store task
        self.active_tasks[task_id] = {
            "id": task_id,
            "type": task_type,
            "data": task_data,
            "client_id": client_id,
            "status": "queued",
            "created_at": datetime.now(),
        }
        
        # Add to task queue
        try:
            await self.task_queue.put({
                "task_id": task_id,
                "type": task_type,
                "data": task_data,
                "client_id": client_id
            })
            
            await self._send_message(client_id, {
                "type": "task_accepted",
                "task_id": task_id,
                "status": "queued"
            })
            
        except asyncio.QueueFull:
            await self._send_error(client_id, "Task queue is full")
    
    async def _handle_task_result(self, client_id: str, data: Dict[str, Any]):
        """Handle task result from agent"""
        task_id = data.get("task_id")
        result = data.get("result")
        status = data.get("status", "completed")
        error = data.get("error")
        
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task["status"] = status
            task["result"] = result
            task["completed_at"] = datetime.now()
            
            # Get original client info
            original_client_id = task["client_id"]
            original_request_id = task.get("original_request_id")
            
            if original_client_id in self.clients:
                # Check if this is an AI service response
                if task.get("type") == "ai_chat_completion" and original_request_id:
                    # Send AI response format
                    response_message = {
                        "type": "ai_response",
                        "request_id": original_request_id,
                        "status": "success" if status == "completed" else "error"
                    }
                    
                    if status == "completed":
                        response_message["result"] = result
                    else:
                        response_message["error"] = error or "Unknown error"
                    
                    await self._send_message(original_client_id, response_message)
                else:
                    # Send regular task result
                    await self._send_message(original_client_id, {
                        "type": "task_result",
                        "task_id": task_id,
                        "result": result,
                        "status": status,
                        "error": error
                    })
            
            # Clean up completed task
            self.active_tasks.pop(task_id, None)
            self.stats["total_tasks_processed"] += 1
    
    async def _handle_agent_status(self, client_id: str, data: Dict[str, Any]):
        """Handle agent status update"""
        agent_id = data.get("agent_id")
        status = data.get("status")
        metrics = data.get("metrics", {})
        
        if agent_id in self.agent_registry:
            self.agent_registry[agent_id]["status"] = status
            self.agent_registry[agent_id]["metrics"] = metrics
            self.agent_registry[agent_id]["last_status_update"] = datetime.now()
    
    async def _handle_ai_request(self, client_id: str, data: Dict[str, Any]):
        """Handle AI request from agent - route to AI service via MCP protocol"""
        request_id = data.get("request_id", str(uuid.uuid4()))
        provider = data.get("provider", "openai")
        messages = data.get("messages", [])
        
        try:
            # Find AI service agent
            ai_service_agent = None
            for agent_id, info in self.agent_registry.items():
                if info["agent_type"] == "ai_service" and info["status"] == "active":
                    ai_service_agent = agent_id
                    break
            
            if not ai_service_agent:
                raise Exception("AI service not available")
            
            # Create task for AI service
            task_id = str(uuid.uuid4())
            task_data = {
                "provider": provider,
                "messages": messages,
                **{k: v for k, v in data.items() 
                   if k not in ["request_id", "type"]}
            }
            
            # Store task with original client info
            self.active_tasks[task_id] = {
                "id": task_id,
                "type": "ai_chat_completion",
                "data": task_data,
                "client_id": client_id,
                "original_request_id": request_id,
                "status": "processing",
                "created_at": datetime.now(),
                "assigned_agent": ai_service_agent
            }
            
            # Send task to AI service
            ai_client_id = self.agent_registry[ai_service_agent]["client_id"]
            await self._send_message(ai_client_id, {
                "type": "task_request",
                "task_id": task_id,
                "task_type": "ai_chat_completion",
                "data": task_data
            })
            
            self.logger.info("AI request forwarded to AI service", 
                           client_id=client_id,
                           request_id=request_id,
                           task_id=task_id,
                           provider=provider)
                
        except Exception as e:
            # Send error response back to agent
            await self._send_message(client_id, {
                "type": "ai_response", 
                "request_id": request_id,
                "error": str(e),
                "status": "error"
            })
            
            self.logger.error("AI request failed",
                            client_id=client_id,
                            request_id=request_id,
                            error=str(e))
            
            ERROR_COUNTER.labels(error_type="ai_request_failed").inc()
    
    async def _task_processor(self):
        """Process tasks from the queue"""
        while self.is_running:
            try:
                # Get task from queue with timeout
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                
                # Find suitable agent for task
                suitable_agents = [
                    agent_id for agent_id, info in self.agent_registry.items()
                    if info["status"] == "active" and task["type"] in info.get("capabilities", [])
                ]
                
                if suitable_agents:
                    # Select agent (simple round-robin for now)
                    selected_agent = suitable_agents[0]
                    agent_client_id = self.agent_registry[selected_agent]["client_id"]
                    
                    # Send task to agent
                    await self._send_message(agent_client_id, {
                        "type": "task_request",
                        "task_id": task["task_id"],
                        "task_type": task["type"],
                        "data": task["data"]
                    })
                    
                    # Update task status
                    if task["task_id"] in self.active_tasks:
                        self.active_tasks[task["task_id"]]["status"] = "processing"
                        self.active_tasks[task["task_id"]]["assigned_agent"] = selected_agent
                else:
                    # No suitable agents, put task back in queue
                    await asyncio.sleep(5)  # Wait before retrying
                    await self.task_queue.put(task)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error("Task processor error", error=str(e))
                await asyncio.sleep(1)
    
    async def _metrics_collector(self):
        """Collect and update metrics"""
        while self.is_running:
            try:
                # Update agent metrics
                for agent_type in self.config.allowed_agent_types:
                    count = sum(1 for info in self.agent_registry.values() 
                               if info["agent_type"] == agent_type)
                    CONNECTED_AGENTS.labels(agent_type=agent_type).set(count)
                
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                self.logger.error("Metrics collector error", error=str(e))
                await asyncio.sleep(5)
    
    async def _health_check_server(self):
        """Simple health check endpoint"""
        from aiohttp import web
        
        async def health_check(request):
            health_status = {
                "status": "healthy" if self.is_running else "unhealthy",
                "server_id": self.server_id,
                "uptime": (datetime.now() - self.start_time).total_seconds(),
                "active_agents": len(self.agent_registry),
                "active_tasks": len(self.active_tasks),
                "total_connections": self.stats["total_connections"],
                "total_tasks_processed": self.stats["total_tasks_processed"],
            }
            return web.json_response(health_status)
        
        app = web.Application()
        app.router.add_get('/health', health_check)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.config.host, 8080)  # Health check on separate port
        await site.start()
        
        self.logger.info("Health check server started", port=8080)
    
    async def _register_in_cluster(self):
        """Register this server instance in the cluster"""
        if not self.redis_client:
            return
        
        try:
            cluster_key = "mcp_cluster:servers"
            server_info = {
                "server_id": self.server_id,
                "host": self.config.host,
                "port": self.config.port,
                "registered_at": datetime.now().isoformat(),
            }
            
            await self.redis_client.hset(cluster_key, self.server_id, json.dumps(server_info))
            await self.redis_client.expire(cluster_key, self.config.agent_registry_ttl)
            
            self.logger.info("Registered in cluster", server_id=self.server_id)
            
        except Exception as e:
            self.logger.error("Failed to register in cluster", error=str(e))
    
    async def _deregister_from_cluster(self):
        """Deregister this server instance from the cluster"""
        if not self.redis_client:
            return
        
        try:
            cluster_key = "mcp_cluster:servers"
            await self.redis_client.hdel(cluster_key, self.server_id)
            
            self.logger.info("Deregistered from cluster", server_id=self.server_id)
            
        except Exception as e:
            self.logger.error("Failed to deregister from cluster", error=str(e))
    
    async def _cluster_discovery(self):
        """Discover other servers in the cluster"""
        while self.is_running:
            try:
                if self.redis_client:
                    cluster_key = "mcp_cluster:servers"
                    servers = await self.redis_client.hgetall(cluster_key)
                    
                    current_peers = set()
                    for server_id, server_data in servers.items():
                        if server_id.decode() != self.server_id:
                            current_peers.add(server_id.decode())
                    
                    # Update peer list
                    if current_peers != self.cluster_peers:
                        self.cluster_peers = current_peers
                        self.logger.info("Cluster peers updated", peers=list(self.cluster_peers))
                
                await asyncio.sleep(60)  # Discovery every minute
                
            except Exception as e:
                self.logger.error("Cluster discovery error", error=str(e))
                await asyncio.sleep(30)
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        if sys.platform != "win32":
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))


async def main():
    """Main entry point for Enhanced MCP Server"""
    config = get_enhanced_config()
    server = EnhancedMCPServer(config)
    
    try:
        await server.start()
        # Keep server running
        while server.is_running:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Received shutdown signal")
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
