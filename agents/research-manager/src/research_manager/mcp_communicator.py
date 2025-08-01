"""
MCP (Model Context Protocol) communication module for Research Manager.

This module handles all MCP protocol communication including:
- Connection management and registration
- Message parsing and routing
- Task delegation to other agents
- Response handling and coordination
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

logger = logging.getLogger(__name__)


class MCPCommunicator:
    """Handles MCP protocol communication for Research Manager."""
    
    def __init__(self, agent_id: str, agent_type: str, mcp_server_url: str, capabilities: list):
        """Initialize MCP communicator."""
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.mcp_server_url = mcp_server_url
        self.capabilities = capabilities
        
        # Connection state
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.mcp_connected = False
        self.should_run = True
        
        # Message handling
        self.task_queue = asyncio.Queue()
        self.pending_responses: Dict[str, asyncio.Future] = {}
    
    async def connect_to_mcp_server(self):
        """Connect to MCP server with retry logic."""
        max_retries = 10
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Connecting to MCP server at {self.mcp_server_url} (attempt {attempt + 1})")
                
                self.websocket = await websockets.connect(
                    self.mcp_server_url,
                    ping_interval=30,
                    ping_timeout=10
                )
                
                # Register with MCP server
                await self._register_with_mcp_server()
                
                self.mcp_connected = True
                logger.info("Successfully connected to MCP server")
                return
                
            except Exception as e:
                logger.warning(f"Failed to connect to MCP server (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("Failed to connect to MCP server after all retries")
                    raise
    
    async def _register_with_mcp_server(self):
        """Register this agent with the MCP server."""
        if not self.websocket:
            raise Exception("WebSocket connection not available")
            
        registration_message = {
            "type": "agent_register",
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": self.capabilities,
            "timestamp": datetime.now().isoformat(),
            "service_info": {
                "host": "0.0.0.0",
                "port": 8002,
                "health_endpoint": "http://0.0.0.0:8002/health"
            }
        }
        
        await self.websocket.send(json.dumps(registration_message))
        logger.info(f"Registered with MCP server: {len(self.capabilities)} capabilities")
    
    async def listen_for_tasks(self):
        """Listen for tasks from MCP server."""
        try:
            if not self.websocket:
                logger.error("Cannot listen for tasks: no websocket connection")
                return
                
            logger.info("Starting to listen for tasks from MCP server")
            
            async for message in self.websocket:
                if not self.should_run:
                    break
                    
                try:
                    logger.info(f"Received raw WebSocket message: {message}")
                    data = json.loads(message)
                    logger.info(f"Parsed message data: {data}")
                    await self.task_queue.put(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse MCP message: {e}, raw message: {message}")
                except Exception as e:
                    logger.error(f"Error handling MCP message: {e}, message: {message}")
                    
        except ConnectionClosed:
            logger.warning("MCP server connection closed")
            self.mcp_connected = False
        except WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            self.mcp_connected = False
        except Exception as e:
            logger.error(f"Unexpected error in message listener: {e}")
            self.mcp_connected = False
    
    async def send_response(self, task_data: Dict[str, Any], result: Dict[str, Any]):
        """Send response back to MCP server."""
        if not self.websocket or not self.mcp_connected:
            logger.warning("Cannot send response: MCP connection not available")
            return
        
        message_type = task_data.get("type", "")
        
        # Skip responses for control messages
        if message_type in ["registration_confirmed", "heartbeat", "ping", "pong"]:
            logger.info(f"Skipping response for control message: {message_type}")
            return
        
        response = {
            "type": "task_result",
            "task_id": task_data.get("task_id"),
            "agent_id": self.agent_id,
            "result": result,
            "status": result.get("status", "completed") if isinstance(result, dict) else "completed"
        }
        
        logger.info(f"Sending response to MCP server: {response}")
        await self.websocket.send(json.dumps(response))
    
    async def delegate_to_agent(self, task_id: str, agent_type: str, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate a task to a specific agent via MCP."""
        try:
            if not self.websocket or not self.mcp_connected:
                raise Exception("MCP connection not available")
            
            # Create research_action message for delegation
            delegation_message = {
                "type": "research_action",
                "data": {
                    "task_id": str(uuid.uuid4()),
                    "context_id": f"delegation-{task_id}",
                    "agent_type": agent_type,
                    "action": action_data.get("action", "search_literature"),
                    "payload": {
                        **action_data,
                        "delegated_from": self.agent_id,
                        "original_task_id": task_id
                    }
                },
                "client_id": self.agent_id,
                "timestamp": datetime.now().isoformat()
            }
            
            # Send delegation
            await self.websocket.send(json.dumps(delegation_message))
            
            logger.info(f"Delegated task {task_id} to {agent_type} with action {action_data.get('action', 'search_literature')}")
            
            return {
                "delegated": True,
                "target_agent": agent_type,
                "delegation_id": delegation_message["data"]["task_id"]
            }
            
        except Exception as e:
            logger.error(f"Failed to delegate to agent {agent_type}: {e}")
            return {
                "delegated": False,
                "error": str(e)
            }
    
    async def fetch_from_database(self, topic_id: str) -> Dict[str, Any]:
        """Fetch research plan from database using topic_id."""
        try:
            if not self.websocket or not self.mcp_connected:
                logger.warning("Cannot fetch research plan: MCP connection not available")
                return {}
            
            # Request database agent to fetch research plan for topic
            db_request = {
                "type": "task",
                "task_id": f"fetch_plan_{uuid.uuid4().hex[:8]}",
                "target_agent": "database_agent",
                "action": "get_approved_plan_for_topic",
                "payload": {
                    "topic_id": topic_id
                },
                "timestamp": datetime.now().isoformat()
            }
            
            await self.websocket.send(json.dumps(db_request))
            logger.info(f"Sent request to fetch research plan for topic {topic_id}")
            
            # Wait for response with timeout
            response_timeout = 10.0  # 10 seconds for database query
            start_time = datetime.now()
            
            while (datetime.now() - start_time).total_seconds() < response_timeout:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    
                    if (data.get("type") == "task_result" and 
                        data.get("task_id") == db_request["task_id"]):
                        
                        result = data.get("result", {})
                        if result.get("status") == "completed":
                            plan_data = result.get("plan_data", {})
                            plan_structure = plan_data.get("plan_structure", {})
                            logger.info(f"Successfully fetched research plan from database: {plan_structure}")
                            return plan_structure
                        else:
                            logger.warning(f"Database agent failed to fetch plan: {result.get('error', 'Unknown error')}")
                            return {}
                        
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Error receiving database response: {e}")
                    break
            
            logger.warning("Timeout waiting for database response")
            return {}
            
        except Exception as e:
            logger.error(f"Error fetching research plan from database: {e}")
            return {}
    
    async def generate_research_plan(self, topic_name: str, topic_description: str) -> Dict[str, Any]:
        """Generate a research plan using the planning agent."""
        try:
            if not self.websocket or not self.mcp_connected:
                logger.warning("Cannot generate research plan: MCP connection not available")
                return {}
            
            # Request planning agent to generate research plan
            planning_request = {
                "type": "task",
                "task_id": f"generate_plan_{uuid.uuid4().hex[:8]}",
                "target_agent": "planning_agent",
                "action": "generate_research_plan",
                "payload": {
                    "topic_name": topic_name,
                    "topic_description": topic_description,
                    "plan_type": "literature_review",
                    "depth": "standard"
                },
                "timestamp": datetime.now().isoformat()
            }
            
            await self.websocket.send(json.dumps(planning_request))
            logger.info(f"Sent request to generate research plan for topic: {topic_name}")
            
            # Wait for response with timeout
            response_timeout = 30.0  # 30 seconds for AI planning
            start_time = datetime.now()
            
            while (datetime.now() - start_time).total_seconds() < response_timeout:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    
                    if (data.get("type") == "task_result" and 
                        data.get("task_id") == planning_request["task_id"]):
                        
                        result = data.get("result", {})
                        if result.get("status") == "completed":
                            generated_plan = result.get("research_plan", {})
                            logger.info(f"Successfully generated research plan: {generated_plan}")
                            return generated_plan
                        else:
                            logger.warning(f"Planning agent failed to generate plan: {result.get('error', 'Unknown error')}")
                            return {}
                        
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Error receiving planning agent response: {e}")
                    break
            
            logger.warning("Timeout waiting for planning agent response")
            return {}
            
        except Exception as e:
            logger.error(f"Error generating research plan: {e}")
            return {}
    
    async def close(self):
        """Close MCP connection."""
        self.should_run = False
        if self.websocket:
            await self.websocket.close()
        self.mcp_connected = False
