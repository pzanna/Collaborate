"""
MCP Server Implementation

The core Message Control Protocol server that coordinates communication
between the Research Manager and specialized agents.
"""

import asyncio
import websockets
import json
import logging
from typing import Dict, Any, Set, Optional, List
from datetime import datetime
import uuid
import signal
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from config.config_manager import ConfigManager
except ImportError:
    # Fallback for test environment
    from src.config.config_manager import ConfigManager
from .protocols import (
    ResearchAction, AgentResponse, AgentRegistration, TaskUpdate,
    serialize_message, deserialize_message, MESSAGE_TYPES
)
from .registry import AgentRegistry
from .queue import TaskQueue

logger = logging.getLogger(__name__)


class MCPServer:
    """Message Control Protocol Server"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        # Load config with fallback
        try:
            self.config = config_manager.config.mcp_server
        except AttributeError:
            # Fallback configuration
            class FallbackConfig:
                def __init__(self):
                    self.host = '127.0.0.1'
                    self.port = 9000
                    self.max_concurrent_tasks = 10
                    self.task_timeout = 300
                    self.retry_attempts = 3
                    self.log_level = 'INFO'
            
            self.config = FallbackConfig()
        
        # Core components
        self.agent_registry = AgentRegistry(heartbeat_timeout=30)
        
        # Get queue size with fallback
        try:
            max_queue_size = config_manager.config.research_tasks.max_task_queue_size
        except AttributeError:
            max_queue_size = 50
        
        self.task_queue = TaskQueue(
            max_size=max_queue_size,
            retry_attempts=self.config.retry_attempts
        )
        
        # Connection management
        self.clients: Dict[str, Any] = {}
        self.research_manager_client: Optional[str] = None
        
        # Server state
        self.is_running = False
        self.server: Optional[Any] = None
        self._background_tasks: List[asyncio.Task] = []
        
        # Statistics
        self.stats = {
            'started_at': datetime.now(),
            'total_tasks_processed': 0,
            'total_messages_sent': 0,
            'total_messages_received': 0,
            'total_agents_registered': 0
        }
    
    async def start(self):
        """Start the MCP server"""
        try:
            # Start background tasks
            await self._start_background_tasks()
            
            # Start WebSocket server
            self.server = await websockets.serve(
                self._handle_client,
                self.config.host,
                self.config.port,
                ping_interval=20,
                ping_timeout=10
            )
            
            self.is_running = True
            logger.info(f"MCP Server started on {self.config.host}:{self.config.port}")
            
            # Set up signal handlers
            self._setup_signal_handlers()
            
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise
    
    async def stop(self):
        """Stop the MCP server"""
        logger.info("Stopping MCP server...")
        
        self.is_running = False
        
        # Stop background tasks
        for task in self._background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        # Close all client connections
        if self.clients:
            await asyncio.gather(
                *[client.close() for client in self.clients.values()],
                return_exceptions=True
            )
        
        # Stop WebSocket server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        # Stop registry cleanup
        await self.agent_registry.stop_cleanup_task()
        
        logger.info("MCP server stopped")
    
    async def _start_background_tasks(self):
        """Start background tasks"""
        # Start agent registry cleanup
        await self.agent_registry.start_cleanup_task()
        
        # Start task processing
        self._background_tasks.append(
            asyncio.create_task(self._process_tasks())
        )
        
        # Start periodic cleanup
        self._background_tasks.append(
            asyncio.create_task(self._periodic_cleanup())
        )
    
    async def _handle_client(self, websocket):
        """Handle new client connection"""
        client_id = str(uuid.uuid4())
        self.clients[client_id] = websocket
        
        logger.info(f"New client connected: {client_id}")
        
        try:
            await websocket.send(json.dumps({
                'type': 'connection_established',
                'data': {'client_id': client_id},
                'timestamp': datetime.now().isoformat()
            }))
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(client_id, data)
                    self.stats['total_messages_received'] += 1
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from client {client_id}")
                except Exception as e:
                    logger.error(f"Error handling message from {client_id}: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} disconnected")
        except Exception as e:
            logger.error(f"Error with client {client_id}: {e}")
        finally:
            # Clean up client
            if client_id in self.clients:
                del self.clients[client_id]
            
            # If this was the research manager, clear reference
            if client_id == self.research_manager_client:
                self.research_manager_client = None
    
    async def _handle_message(self, client_id: str, message: Dict[str, Any]):
        """Handle incoming message from client"""
        message_type = message.get('type')
        message_data = message.get('data', {})
        
        if message_type == 'research_action':
            await self._handle_research_action(client_id, message_data)
        elif message_type == 'agent_response':
            await self._handle_agent_response(client_id, message_data)
        elif message_type == 'agent_registration':
            await self._handle_agent_registration(client_id, message_data)
        elif message_type == 'heartbeat':
            await self._handle_heartbeat(client_id, message_data)
        elif message_type == 'cancel_task':
            await self._handle_cancel_task(client_id, message_data)
        elif message_type == 'get_task_status':
            await self._handle_get_task_status(client_id, message_data)
        elif message_type == 'get_server_stats':
            await self._handle_get_server_stats(client_id, message_data)
        elif message_type == 'identify_research_manager':
            await self._handle_identify_research_manager(client_id, message_data)
        else:
            logger.warning(f"Unknown message type from {client_id}: {message_type}")
    
    async def _handle_research_action(self, client_id: str, data: Dict[str, Any]):
        """Handle research action from Research Manager"""
        try:
            action = ResearchAction.from_dict(data)
            
            # Add to task queue
            success = await self.task_queue.add_task(action)
            
            if success:
                logger.info(f"Added task {action.task_id} to queue")
                self.stats['total_tasks_processed'] += 1
                
                # Send acknowledgment
                await self._send_to_client(client_id, {
                    'type': 'task_queued',
                    'data': {
                        'task_id': action.task_id,
                        'status': 'queued'
                    }
                })
            else:
                # Send error
                await self._send_to_client(client_id, {
                    'type': 'task_rejected',
                    'data': {
                        'task_id': action.task_id,
                        'error': 'Task queue full'
                    }
                })
        
        except Exception as e:
            logger.error(f"Error handling research action: {e}")
    
    async def _handle_agent_response(self, client_id: str, data: Dict[str, Any]):
        """Handle response from agent"""
        try:
            response = AgentResponse.from_dict(data)
            
            # Mark task as completed or failed
            if response.status == 'completed':
                await self.task_queue.complete_task(response.task_id, response.result)
            elif response.status == 'failed':
                await self.task_queue.fail_task(response.task_id, response.error or "Unknown error")
            
            # Forward response to Research Manager
            if self.research_manager_client:
                await self._send_to_client(self.research_manager_client, {
                    'type': 'agent_response',
                    'data': response.to_dict()
                })
            
            logger.debug(f"Processed response for task {response.task_id}")
        
        except Exception as e:
            logger.error(f"Error handling agent response: {e}")
    
    async def _handle_agent_registration(self, client_id: str, data: Dict[str, Any]):
        """Handle agent registration"""
        try:
            registration = AgentRegistration.from_dict(data)
            
            # Register agent
            success = await self.agent_registry.register_agent(registration)
            
            if success:
                self.stats['total_agents_registered'] += 1
                
                # Send acknowledgment
                await self._send_to_client(client_id, {
                    'type': 'registration_confirmed',
                    'data': {'agent_id': registration.agent_id}
                })
            else:
                # Send error
                await self._send_to_client(client_id, {
                    'type': 'registration_failed',
                    'data': {'agent_id': registration.agent_id}
                })
        
        except Exception as e:
            logger.error(f"Error handling agent registration: {e}")
    
    async def _handle_heartbeat(self, client_id: str, data: Dict[str, Any]):
        """Handle heartbeat from agent"""
        agent_id = data.get('agent_id')
        if agent_id:
            await self.agent_registry.update_heartbeat(agent_id)
    
    async def _handle_cancel_task(self, client_id: str, data: Dict[str, Any]):
        """Handle task cancellation request"""
        task_id = data.get('task_id')
        if task_id:
            success = await self.task_queue.cancel_task(task_id)
            
            await self._send_to_client(client_id, {
                'type': 'task_cancelled' if success else 'cancel_failed',
                'data': {'task_id': task_id}
            })
    
    async def _handle_get_task_status(self, client_id: str, data: Dict[str, Any]):
        """Handle task status request"""
        task_id = data.get('task_id')
        response_id = data.get('response_id')
        
        if task_id and response_id:
            status = await self.task_queue.get_task_status(task_id)
            
            await self._send_to_client(client_id, {
                'type': 'task_status_response',
                'data': {
                    'response_id': response_id,
                    'task_status': status
                }
            })
    
    async def _handle_get_server_stats(self, client_id: str, data: Dict[str, Any]):
        """Handle server statistics request"""
        response_id = data.get('response_id')
        
        if response_id:
            # Get combined stats
            queue_stats = await self.task_queue.get_queue_stats()
            registry_stats = await self.agent_registry.get_stats()
            
            combined_stats = {
                **self.stats,
                'queue': queue_stats,
                'agents': registry_stats,
                'uptime_seconds': (datetime.now() - self.stats['started_at']).total_seconds()
            }
            
            await self._send_to_client(client_id, {
                'type': 'server_stats_response',
                'data': {
                    'response_id': response_id,
                    'stats': combined_stats
                }
            })
    
    async def _handle_identify_research_manager(self, client_id: str, data: Dict[str, Any]):
        """Handle Research Manager identification"""
        self.research_manager_client = client_id
        logger.info(f"Research Manager identified: {client_id}")
        
        await self._send_to_client(client_id, {
            'type': 'research_manager_confirmed',
            'data': {'client_id': client_id}
        })
    
    async def _process_tasks(self):
        """Background task to process the task queue"""
        while self.is_running:
            try:
                # Get next task
                task = await self.task_queue.get_next_task()
                
                if task:
                    # Find available agent
                    agents = await self.agent_registry.get_available_agents(task.action.action)
                    
                    if agents:
                        agent_id = agents[0]  # Use least loaded agent
                        
                        # Assign task to agent
                        await self.agent_registry.assign_task(agent_id, task.action.task_id)
                        await self.task_queue.assign_agent(task.action.task_id, agent_id)
                        
                        # Send task to agent
                        await self._send_task_to_agent(agent_id, task.action)
                        
                        logger.info(f"Assigned task {task.action.task_id} to agent {agent_id}")
                    else:
                        # No available agents, put task back in queue
                        await self.task_queue.fail_task(
                            task.action.task_id, 
                            "No available agents", 
                            retry=True
                        )
                        logger.warning(f"No available agents for task {task.action.task_id}")
                
                # Small delay to prevent tight loop
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error processing tasks: {e}")
                await asyncio.sleep(1)
    
    async def _send_task_to_agent(self, agent_id: str, action: ResearchAction):
        """Send task to specific agent"""
        # Find agent's client connection
        # This is a simplified approach - in practice, you'd maintain agent->client mapping
        message = serialize_message('research_action', action)
        
        # Broadcast to all clients (agents will filter by their capabilities)
        for client_id, websocket in self.clients.items():
            try:
                await websocket.send(json.dumps(message))
                self.stats['total_messages_sent'] += 1
            except Exception as e:
                logger.error(f"Error sending task to client {client_id}: {e}")
    
    async def _send_to_client(self, client_id: str, message: Dict[str, Any]):
        """Send message to specific client"""
        if client_id in self.clients:
            try:
                message['timestamp'] = datetime.now().isoformat()
                await self.clients[client_id].send(json.dumps(message))
                self.stats['total_messages_sent'] += 1
            except Exception as e:
                logger.error(f"Error sending message to client {client_id}: {e}")
    
    async def _periodic_cleanup(self):
        """Periodic cleanup tasks"""
        while self.is_running:
            try:
                # Clean up old tasks
                await self.task_queue.cleanup_old_tasks(max_age_hours=24)
                
                # Sleep for 1 hour
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down gracefully...")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run_forever(self):
        """Run the server forever"""
        try:
            await self.start()
            
            # Keep server running
            while self.is_running:
                await asyncio.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            await self.stop()


async def main():
    """Main entry point for MCP server"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load configuration
    config_manager = ConfigManager()
    
    # Create and run server
    server = MCPServer(config_manager)
    await server.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
