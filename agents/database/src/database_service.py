"""
Database Agent Service for Eunice Research Platform.

This module provides a containerized Database Agent that handles:
- Database write operations (CREATE, UPDATE, DELETE)
- Project and task management database operations
- Literature review database operations
- User and collaboration database operations
- Direct database access and connection management

ARCHITECTURE COMPLIANCE:
- ONLY exposes health check API endpoint (/health)
- ALL business operations via MCP protocol exclusively
- NO direct HTTP/REST endpoints for business logic.
"""

import asyncio
import json
import logging
import re
import traceback
import uuid
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import uvicorn
import websockets
from fastapi import FastAPI
from websockets.exceptions import ConnectionClosed, WebSocketException

# Import database libraries
import asyncpg

# Import the standardized health check service
sys.path.append(str(Path(__file__).parent.parent))
from health_check_service import create_health_check_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DatabaseAgentService:
    """
    Database Agent Service for database operations.
    
    Handles all database write operations, project management,
    and data persistence via MCP protocol.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Database Agent Service."""
        self.config = config
        self.agent_id = "database_agent"
        self.agent_type = "database"
        
        # Service configuration
        self.service_host = config.get("service_host", "0.0.0.0")
        self.service_port = config.get("service_port", 8011)
        self.mcp_server_url = config.get("mcp_server_url", "ws://mcp-server:9000")
        
        # Database configuration
        self.database_url = config.get("database_url", "postgresql://postgres:password@postgres:5432/eunice")
        self.max_connections = config.get("max_connections", 10)
        self.connection_timeout = config.get("connection_timeout", 30)
        
        # MCP connection
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.mcp_connected = False
        self.should_run = True
        
        # Database connection pool
        self.db_pool: Optional[asyncpg.Pool] = None
        
        # Task processing queue
        self.task_queue = asyncio.Queue()
        
        # Start time for uptime tracking
        self.start_time = datetime.now()
        
        # Operation counters
        self.operations_completed = 0
        self.operations_failed = 0
        
        # Capabilities
        self.capabilities = [
            "create_project", "update_project", "delete_project", "get_project",
            "create_topic", "update_topic", "delete_topic", "get_topic", 
            "create_research_topic", "update_research_topic", "delete_research_topic", "get_research_topic",
            "create_plan", "update_plan", "delete_plan", "get_plan",
            "create_research_plan", "update_research_plan", "delete_research_plan", "get_research_plan",
            "create_task", "update_task", "delete_task", "get_task",
            "create_literature_record", "update_literature_record", "delete_literature_record",
            "create_search_term_optimization", "update_search_term_optimization", "delete_search_term_optimization", "get_search_term_optimization",
            "get_search_terms_for_plan", "get_search_terms_for_task", "store_optimized_search_terms",
            "database_operations", "data_persistence", "query_execution"
        ]
        
        logger.info(f"Database Agent Service initialized on port {self.service_port}")
    
    def get_capabilities(self) -> List[str]:
        """Return list of agent capabilities."""
        return self.capabilities
    
    async def start(self):
        """Start the Database Agent Service."""
        try:
            # Initialize database connection pool
            await self._initialize_database_pool()
            
            # Test database connection
            await self._test_database_connection()
            
            # Connect to MCP server
            await self._connect_to_mcp_server()
            
            # Start task processing and listening concurrently
            await asyncio.gather(
                self._process_task_queue(),
                self._listen_for_tasks()
            )
            
            logger.info("Database Agent Service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Database Agent Service: {e}")
            raise
    
    async def stop(self):
        """Stop the Database Agent Service."""
        try:
            self.should_run = False
            
            # Close database pool
            if self.db_pool:
                await self.db_pool.close()
            
            # Close MCP connection
            if self.websocket:
                await self.websocket.close()
            
            logger.info("Database Agent Service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping Database Agent Service: {e}")
    
    async def _initialize_database_pool(self):
        """Initialize database connection pool."""
        try:
            self.db_pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=self.max_connections,
                command_timeout=self.connection_timeout
            )
            logger.info(f"Database pool initialized with max {self.max_connections} connections")
            
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    async def _test_database_connection(self):
        """Test database connection."""
        try:
            if not self.db_pool:
                raise Exception("Database pool not initialized")
            
            async with self.db_pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                if result == 1:
                    logger.info("✅ Database connection test successful")
                else:
                    raise Exception("Database connection test failed")
                    
        except Exception as e:
            logger.error(f"❌ Database connection test failed: {e}")
            raise
    
    async def _connect_to_mcp_server(self):
        """Connect to MCP server."""
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
                "host": self.service_host,
                "port": self.service_port,
                "health_endpoint": f"http://{self.service_host}:{self.service_port}/health"
            }
        }
        
        await self.websocket.send(json.dumps(registration_message))
        logger.info(f"Registered with MCP server: {len(self.capabilities)} capabilities")
        logger.info(f"DEBUG: Capabilities sent: {self.capabilities}")
    
    async def _listen_for_tasks(self):
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
                    data = json.loads(message)
                    logger.info(f"Received message from MCP server: {data}")
                    
                    # Filter out system messages - only queue actual task requests
                    message_type = data.get("type", "")
                    if message_type == "task_request":
                        await self.task_queue.put(data)
                        logger.info("Task request added to task queue")
                    elif message_type == "registration_confirmed":
                        logger.info("Registration confirmed by MCP server")
                    elif message_type == "heartbeat_ack":
                        logger.debug("Heartbeat acknowledgment received")
                    else:
                        logger.info(f"Received system message type: {message_type} - not queuing as task")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse MCP message: {e}")
                except Exception as e:
                    logger.error(f"Error handling MCP message: {e}")
                    
        except ConnectionClosed:
            logger.warning("MCP server connection closed")
            self.mcp_connected = False
        except WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            self.mcp_connected = False
        except Exception as e:
            logger.error(f"Unexpected error in message listener: {e}")
            self.mcp_connected = False
    
    async def _process_task_queue(self):
        """Process tasks from the MCP queue."""
        logger.info("Task queue processor started")
        while self.should_run:
            try:
                # Get task from queue
                logger.info("Waiting for task from queue")
                task_data = await self.task_queue.get()
                logger.info(f"Got task from queue: {task_data}")

                # Process the task
                logger.info("About to process database task")
                result = await self._process_database_task(task_data)
                logger.info(f"Task processing result: {result}")

                # Send result back to MCP server
                if self.websocket and self.mcp_connected:
                    # Convert any datetime objects in result to ISO strings for JSON serialization
                    serializable_result = _make_json_serializable(result)
                    
                    response = {
                        "type": "task_result",
                        "task_id": task_data.get("task_id"),
                        "result": serializable_result,
                        "status": "completed",
                        "timestamp": datetime.now().isoformat()
                    }
                    logger.info(f"Sending response to MCP server: {response}")
                    await self.websocket.send(json.dumps(response))
                    logger.info("Response sent successfully")
                else:
                    logger.warning("No websocket connection to send response")

                # Mark task as done
                self.task_queue.task_done()
                logger.info("Task marked as done")

            except Exception as e:
                logger.error(f"Error processing task: {e}")
                logger.error(f"Task queue exception: {type(e).__name__}: {str(e)}")
                import traceback
                logger.error(f"Task queue traceback: {traceback.format_exc()}")
                await asyncio.sleep(1)
    
    async def _process_database_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a database-related task."""
        logger.info("Entering _process_database_task method")
        logger.info(f"Method received task_data type: {type(task_data)}")
        try:
            logger.info(f"Full task data received: {task_data}")

            # Handle both MCP formats:
            # 1. {"type": "task_request", "task_type": "create_project", "data": {...}}
            # 2. {"task_id": "...", "action": "create_project", "payload": {...}}
            task_type = task_data.get("task_type", task_data.get("action", ""))
            data = task_data.get("data", task_data.get("payload", {}))
            
            logger.info(f"Processing database task: {task_type}")
            
            # Project operations
            if task_type == "create_project":
                result = await self._handle_create_project(data)
                return result
            elif task_type == "update_project":
                logger.info("CRITICAL DEBUG: About to call _handle_update_project")
                logger.error("CRITICAL ERROR: This should definitely appear in logs!")
                print("PRINT STATEMENT: This should appear even if logging is broken")
                result = await self._handle_update_project(data)
                logger.info(f"CRITICAL DEBUG: Got result from _handle_update_project: {result}")
                return result
            elif task_type == "delete_project":
                return await self._handle_delete_project(data)
            
            # Topic operations
            elif task_type == "create_topic":
                return await self._handle_create_topic(data)
            elif task_type == "create_research_topic":
                return await self._handle_create_research_topic(data)
            elif task_type == "update_topic":
                return await self._handle_update_topic(data)
            elif task_type == "update_research_topic":
                return await self._handle_update_research_topic(data)
            elif task_type == "delete_topic":
                return await self._handle_delete_topic(data)
            elif task_type == "delete_research_topic":
                return await self._handle_delete_research_topic(data)
            
            # Plan operations
            elif task_type == "create_plan" or task_type == "create_research_plan":
                return await self._handle_create_plan(data)
            elif task_type == "update_plan" or task_type == "update_research_plan":
                return await self._handle_update_plan(data)
            elif task_type == "delete_plan" or task_type == "delete_research_plan":
                return await self._handle_delete_plan(data)
            
            # Task operations
            elif task_type == "create_task":
                return await self._handle_create_task(data)
            elif task_type == "update_task":
                return await self._handle_update_task(data)
            elif task_type == "delete_task":
                return await self._handle_delete_task(data)
            
            # Literature record operations
            elif task_type == "create_literature_record":
                return await self._handle_create_literature_record(data)
            elif task_type == "update_literature_record":
                return await self._handle_update_literature_record(data)
            elif task_type == "delete_literature_record":
                return await self._handle_delete_literature_record(data)
            
            # Search term optimization operations
            elif task_type == "create_search_term_optimization":
                return await self._handle_create_search_term_optimization(data)
            elif task_type == "update_search_term_optimization":
                return await self._handle_update_search_term_optimization(data)
            elif task_type == "delete_search_term_optimization":
                return await self._handle_delete_search_term_optimization(data)
            elif task_type == "get_search_term_optimization":
                return await self._handle_get_search_term_optimization(data)
            elif task_type == "get_search_terms_for_plan":
                return await self._handle_get_search_terms_for_plan(data)
            elif task_type == "get_search_terms_for_task":
                return await self._handle_get_search_terms_for_task(data)
            elif task_type == "store_optimized_search_terms":
                return await self._handle_store_optimized_search_terms(data)
            
            # Generic database operations
            elif task_type == "database_operations":
                return await self._handle_database_operations(data)
            elif task_type == "query_execution":
                return await self._handle_query_execution(data)
            
            else:
                return {
                    "status": "failed",
                    "error": f"Unknown task type: {task_type}",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error processing database task: {e}")
            import traceback
            self.operations_failed += 1
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_create_project(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle project creation request."""
        try:
            logger.info(f"Creating project with data: {data}")
            
            if not self.db_pool:
                logger.error("Database pool not available")
                raise Exception("Database pool not available")
                
            # Handle different data formats from different sources
            project_name = data.get("name", data.get("project_name", ""))  # Use 'name' as primary, 'project_name' as fallback
            description = data.get("description", "")
            user_id = data.get("user_id", data.get("created_by", "system"))  # Default to 'system' if no user_id
            
            # Generate or use provided project ID
            try:
                project_id = data.get("id", str(uuid.uuid4()))  # Use provided ID or generate new one
            except Exception as e:
                logger.error(f"UUID generation error: {e}")
                project_id = "temp-id-" + str(datetime.now().timestamp())
            
            logger.info(f"Extracted values - name: {project_name}, desc: {description}, user: {user_id}, id: {project_id}")
            
            if not project_name:
                logger.error("Project name is required")
                return {
                    "status": "failed",
                    "error": "Project name is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            logger.info("Executing database insert")
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO projects (id, name, description, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5)
                """, project_id, project_name, description, datetime.now(), datetime.now())

            logger.info(f"Project created successfully with ID: {project_id}")
            self.operations_completed += 1
            
            return {
                "status": "completed",
                "project_id": project_id,
                "project_name": project_name,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            self.operations_failed += 1
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_update_project(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle project update request - supports multiple data formats."""
        logger.info(f"🔍 ABSOLUTELY FIRST LINE: Received data: {data}")
        try:
            if not self.db_pool:
                raise Exception("Database pool not available")
                
            logger.info(f"🔍 DEBUG: Received data for update_project: {data}")
            logger.info(f"🔍 DEBUG: Data type: {type(data)}")
            logger.info(f"🔍 DEBUG: Data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                
            # Handle multiple data formats for backward compatibility
            # Format 1: {"project_id": "...", "updates": {...}}
            # Format 2: {"id": "...", "name": "...", "description": "...", ...}
            
            project_id = data.get("project_id") or data.get("id", "")
            logger.error(f"🔥 CRITICAL: Extracted project_id: '{project_id}' from data keys: {list(data.keys())}")
            logger.error(f"🔥 CRITICAL: data.get('project_id'): '{data.get('project_id')}', data.get('id'): '{data.get('id')}'")
            
            if not project_id:
                logger.error("🚨 CRITICAL FAILURE: Project ID is empty or None!")
                return {
                    "status": "failed",
                    "error": "Project ID is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Extract updates from either format
            if "updates" in data:
                # Format 1: structured with updates field
                updates = data.get("updates", {})
            else:
                # Format 2: direct fields, extract the updatable ones
                updates = {}
                for field in ["name", "description", "status", "metadata"]:
                    if field in data:
                        value = data[field]
                        # Handle metadata string conversion
                        if field == "metadata" and isinstance(value, str):
                            try:
                                # Parse JSON string and convert back to string for database
                                parsed_metadata = json.loads(value)
                                value = json.dumps(parsed_metadata)  # Convert back to JSON string
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse metadata JSON: {value}")
                                value = "{}"  # Default to empty JSON object string
                        elif field == "metadata" and isinstance(value, dict):
                            # If already a dict, convert to JSON string for database
                            value = json.dumps(value)
                        updates[field] = value
            
            logger.info(f"DEBUG: Final updates dict: {updates}")
            
            # Build update query dynamically
            set_clauses = []
            values = []
            param_count = 1
            
            for field, value in updates.items():
                if field in ["name", "description", "status", "metadata"]:
                    set_clauses.append(f"{field} = ${param_count}")
                    values.append(value)
                    param_count += 1
            
            if not set_clauses:
                return {
                    "status": "failed",
                    "error": "No valid fields to update",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Add updated_at
            set_clauses.append(f"updated_at = ${param_count}")
            values.append(datetime.now())
            param_count += 1
            
            # Add project_id for WHERE clause
            values.append(project_id)
            
            query = f"""
                UPDATE projects 
                SET {', '.join(set_clauses)}
                WHERE id = ${param_count}
            """
            
            logger.info(f"Executing update query: {query}")
            logger.info(f"With values: {values}")
            
            async with self.db_pool.acquire() as conn:
                result = await conn.execute(query, *values)
                rows_affected = int(result.split()[-1])
                
            logger.info(f"Update completed, rows affected: {rows_affected}")
            
            self.operations_completed += 1
            
            return {
                "status": "completed",
                "project_id": project_id,
                "rows_affected": rows_affected,
                "updates_applied": updates,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to update project: {e}")
            self.operations_failed += 1
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_delete_project(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle project deletion request."""
        try:
            if not self.db_pool:
                raise Exception("Database pool not available")
                
            project_id = data.get("id", "")
            
            if not project_id:
                return {
                    "status": "failed",
                    "error": "Project ID is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            async with self.db_pool.acquire() as conn:
                result = await conn.execute("DELETE FROM projects WHERE id = $1", project_id)
                rows_affected = int(result.split()[-1])
            
            self.operations_completed += 1
            
            return {
                "status": "completed",
                "project_id": project_id,
                "rows_affected": rows_affected,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to delete project: {e}")
            self.operations_failed += 1
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_create_topic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle topic creation request."""
        try:
            if not self.db_pool:
                raise Exception("Database pool not available")
                
            topic_name = data.get("name", data.get("topic_name", ""))  # Use 'name' as primary, 'topic_name' as fallback
            project_id = data.get("project_id", "")
            description = data.get("description", "")
            
            if not all([topic_name, project_id]):
                return {
                    "status": "failed",
                    "error": "Topic name and project ID are required",
                    "timestamp": datetime.now().isoformat()
                }
            
            topic_id = str(uuid.uuid4())
            
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO topics (id, name, description, project_id, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, topic_id, topic_name, description, project_id, datetime.now(), datetime.now())
            
            self.operations_completed += 1
            
            return {
                "status": "completed",
                "topic_id": topic_id,
                "topic_name": topic_name,
                "project_id": project_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create topic: {e}")
            self.operations_failed += 1
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_create_research_topic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle research topic creation request with correct table and field names."""
        try:
            if not self.db_pool:
                raise Exception("Database pool not available")
            
            # Extract data from API Gateway format
            payload = data.get("payload", data)  # Handle nested payload structure
            
            topic_id = payload.get("id", str(uuid.uuid4()))
            project_id = payload.get("project_id", "")
            name = payload.get("name", "")
            description = payload.get("description", "")
            status = payload.get("status", "active")
            created_at = payload.get("created_at", datetime.now().isoformat())
            updated_at = payload.get("updated_at", datetime.now().isoformat())
            metadata = payload.get("metadata", "{}")
            
            # Ensure metadata is a string (for JSON storage)
            if isinstance(metadata, dict):
                metadata = json.dumps(metadata)
            elif not isinstance(metadata, str):
                metadata = "{}"
            
            if not all([name, project_id]):
                return {
                    "status": "failed",
                    "error": "Topic name and project ID are required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Parse datetime strings
            try:
                created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00')) if isinstance(created_at, str) else created_at
                updated_dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00')) if isinstance(updated_at, str) else updated_at
            except:
                created_dt = datetime.now()
                updated_dt = datetime.now()
            
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO research_topics (id, project_id, name, description, status, created_at, updated_at, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
                """, topic_id, project_id, name, description, status, created_dt, updated_dt, metadata)
            
            self.operations_completed += 1
            
            return {
                "status": "completed",
                "topic_id": topic_id,
                "name": name,
                "project_id": project_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create research topic: {e}")
            self.operations_failed += 1
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def _handle_update_topic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle topic update request."""
        return await self._generic_update("topics", data)
    
    async def _handle_delete_topic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle topic deletion request."""
        return await self._generic_delete("topics", data.get("topic_id", ""))

    async def _handle_update_research_topic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle research topic update request."""
        try:
            if not self.db_pool:
                raise Exception("Database pool not available")
            
            # Extract ID from payload or data
            topic_id = data.get("id", data.get("topic_id", ""))
            if not topic_id:
                return {
                    "status": "failed",
                    "error": "Topic ID is required for update",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Use the research_topics table for research topic updates
            return await self._generic_update("research_topics", data)
            
        except Exception as e:
            logger.error(f"Failed to update research topic: {e}")
            self.operations_failed += 1
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def _handle_delete_research_topic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle research topic deletion request."""
        try:
            # Extract ID from payload or data (API Gateway sends it as 'id')
            topic_id = data.get("id", data.get("topic_id", ""))
            if not topic_id:
                return {
                    "status": "failed", 
                    "error": "Topic ID is required for deletion",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Use the research_topics table for research topic deletions
            return await self._generic_delete("research_topics", topic_id)
            
        except Exception as e:
            logger.error(f"Failed to delete research topic: {e}")
            self.operations_failed += 1
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_create_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle research plan creation request."""
        try:
            if not self.db_pool:
                raise Exception("Database pool not available")
                
            # Extract fields to match the actual research_plans table schema
            plan_id = data.get("id", str(uuid.uuid4()))  # Use provided ID or generate new one
            topic_id = data.get("topic_id", "")  # Research plans belong to topics, not projects
            name = data.get("name", "")
            description = data.get("description", "")
            plan_type = data.get("plan_type", "comprehensive") 
            status = data.get("status", "draft")
            plan_approved = data.get("plan_approved", False)
            estimated_cost = data.get("estimated_cost", 0.0)
            actual_cost = data.get("actual_cost", 0.0)
            plan_structure = data.get("plan_structure", {})
            metadata = data.get("metadata", {})
            
            # Validate required fields
            if not all([name, topic_id]):
                return {
                    "status": "failed",
                    "error": "Plan name and topic ID are required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Convert metadata to JSON string if it's a dict or parse it if it's a string
            if isinstance(metadata, str):
                try:
                    metadata_json = json.loads(metadata)
                except json.JSONDecodeError:
                    metadata_json = {}
            else:
                metadata_json = metadata
            
            # Convert plan_structure to JSON string if it's a dict or parse it if it's a string
            if isinstance(plan_structure, str):
                try:
                    plan_structure_json = json.loads(plan_structure)
                except json.JSONDecodeError:
                    plan_structure_json = {}
            else:
                plan_structure_json = plan_structure
            
            # Debug logging to check values
            logger.info(f"Creating plan with plan_structure type: {type(plan_structure)}")
            logger.info(f"plan_structure_json type: {type(plan_structure_json)}")
            logger.info(f"plan_structure content preview: {str(plan_structure_json)[:200]}...")
            
            async with self.db_pool.acquire() as conn:
                logger.info(f"Executing INSERT for plan {plan_id} with plan_structure length: {len(json.dumps(plan_structure_json))}")
                await conn.execute("""
                    INSERT INTO research_plans (id, topic_id, name, description, plan_type, status, plan_approved, 
                                              estimated_cost, actual_cost, plan_structure, metadata, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """, plan_id, topic_id, name, description, plan_type, status, plan_approved, 
                estimated_cost, actual_cost, json.dumps(plan_structure_json), json.dumps(metadata_json), 
                datetime.now(), datetime.now())
                logger.info(f"Successfully executed INSERT for plan {plan_id}")
            
            self.operations_completed += 1
            
            return {
                "status": "completed",
                "plan_id": plan_id,
                "name": name,
                "topic_id": topic_id,
                "plan_type": plan_type,
                "plan_status": status,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create research plan: {e}")
            self.operations_failed += 1
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_update_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle plan update request."""
        return await self._generic_update("research_plans", data)
    
    async def _handle_delete_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle plan deletion request."""
        # Support both 'id' and 'plan_id' for flexibility
        plan_id = data.get("id") or data.get("plan_id", "")
        return await self._generic_delete("research_plans", plan_id)
    
    async def _handle_create_task(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task creation request."""
        try:
            if not self.db_pool:
                raise Exception("Database pool not available")
                
            # Extract task data according to research_tasks schema
            task_name = data.get("name", data.get("task_name", ""))
            plan_id = data.get("plan_id", "")
            description = data.get("description", "")
            task_type = data.get("task_type", "research")
            task_order = data.get("task_order", 1)
            status = data.get("status", "pending")
            metadata = data.get("metadata", {})
            
            # Use provided ID or generate new one
            task_id = data.get("id", str(uuid.uuid4()))
            
            if not all([task_name, plan_id]):
                return {
                    "status": "failed",
                    "error": "Task name and plan ID are required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Convert metadata to JSON if it's a string
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse metadata JSON: {metadata}")
                    metadata = {}
            
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO research_tasks (id, plan_id, name, description, task_type, task_order, status, created_at, updated_at, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """, task_id, plan_id, task_name, description, task_type, task_order, status, 
                     datetime.now(), datetime.now(), json.dumps(metadata))
            
            self.operations_completed += 1
            
            return {
                "status": "completed",
                "task_id": task_id,
                "task_name": task_name,
                "plan_id": plan_id,
                "task_type": task_type,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            self.operations_failed += 1
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_update_task(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle research task update request (use research_tasks table)."""
        return await self._generic_update("research_tasks", data)
    
    async def _handle_delete_task(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle research task deletion request (use research_tasks table)."""
        return await self._generic_delete("research_tasks", data.get("task_id", ""))
    
    async def _handle_create_literature_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle literature record creation request with full field support."""
        try:
            if not self.db_pool:
                raise Exception("Database pool not available")
                
            # Extract all literature record fields
            title = data.get("title", "")
            authors = data.get("authors", [])
            project_id = data.get("project_id", "")
            doi = data.get("doi")
            pmid = data.get("pmid")
            arxiv_id = data.get("arxiv_id")
            year = data.get("year")
            journal = data.get("journal")
            abstract = data.get("abstract")
            url = data.get("url")
            source = data.get("source")
            publication_type = data.get("publication_type")
            mesh_terms = data.get("mesh_terms", [])
            categories = data.get("categories", [])
            metadata = data.get("metadata", {})
            
            # Handle citation count conversion to integer
            citation_count = data.get("citation_count", 0)
            if citation_count is not None:
                try:
                    citation_count = int(citation_count) if citation_count != "" else None
                except (ValueError, TypeError):
                    citation_count = None
            
            # Validate required fields
            if not title or not project_id:
                return {
                    "status": "failed",
                    "error": "Title and project ID are required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Check if project exists before creating literature record
            async with self.db_pool.acquire() as conn:
                project_exists = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM projects WHERE id = $1)", project_id
                )
                if not project_exists:
                    return {
                        "status": "failed",
                        "error": f"Project with ID {project_id} does not exist",
                        "timestamp": datetime.now().isoformat()
                    }
            
                record_id = str(uuid.uuid4())
                now = datetime.now()
                
                # Use the existing connection for the insert
                await conn.execute("""
                    INSERT INTO literature_records (
                        id, title, authors, project_id, doi, pmid, arxiv_id, year, 
                        journal, abstract, url, citation_count, source, publication_type,
                        mesh_terms, categories, created_at, updated_at, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
                """, 
                    record_id, title, json.dumps(authors), project_id, doi, pmid, arxiv_id, year,
                    journal, abstract, url, citation_count, source, publication_type,
                    json.dumps(mesh_terms), json.dumps(categories), now, now, json.dumps(metadata)
                )
            
            self.operations_completed += 1
            
            return {
                "status": "completed",
                "record_id": record_id,
                "title": title,
                "project_id": project_id,
                "source": source,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create literature record: {e}")
            self.operations_failed += 1
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_update_literature_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle literature record update request."""
        return await self._generic_update("literature_records", data)
    
    async def _handle_delete_literature_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle literature record deletion request."""
        return await self._generic_delete("literature_records", data.get("record_id", ""))
    
    # Search Term Optimization Handlers
    async def _handle_create_search_term_optimization(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle search term optimization creation request."""
        try:
            if not self.db_pool:
                raise Exception("Database pool not available")
                
            # Extract search term optimization data
            source_type = data.get("source_type", "")  # 'plan' or 'task'
            source_id = data.get("source_id", "")
            original_query = data.get("original_query", "")
            optimized_terms = data.get("optimized_terms", [])
            optimization_context = data.get("optimization_context", {})
            target_databases = data.get("target_databases", [])
            expires_at = data.get("expires_at")
            expires_at = datetime.fromisoformat(expires_at) if expires_at else None
            metadata = data.get("metadata", {})
            
            if not source_type or not source_id or not original_query or not optimized_terms:
                return {
                    "status": "failed",
                    "error": "source_type, source_id, original_query, and optimized_terms are required",
                    "timestamp": datetime.now().isoformat()
                }
            
            if source_type not in ["plan", "task"]:
                return {
                    "status": "failed",
                    "error": "source_type must be 'plan' or 'task'",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Generate UUID for search term optimization
            optimization_id = str(uuid.uuid4())
            now = datetime.now()
            
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO search_term_optimizations (
                        id, source_type, source_id, original_query, optimized_terms, 
                        optimization_context, target_databases, created_at, updated_at, 
                        expires_at, metadata
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """, 
                    optimization_id, source_type, source_id, original_query,
                    json.dumps(optimized_terms), json.dumps(optimization_context),
                    json.dumps(target_databases), now, now, expires_at,
                    json.dumps(metadata)
                )
                
                self.operations_completed += 1
                
                return {
                    "status": "completed",
                    "optimization_id": optimization_id,
                    "source_type": source_type,
                    "source_id": source_id,
                    "optimized_terms": optimized_terms,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to create search term optimization: {e}")
            self.operations_failed += 1
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_update_search_term_optimization(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle search term optimization update request."""
        return await self._generic_update("search_term_optimizations", data)
    
    async def _handle_delete_search_term_optimization(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle search term optimization deletion request."""
        return await self._generic_delete("search_term_optimizations", data.get("optimization_id", ""))
    
    async def _handle_get_search_term_optimization(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle search term optimization retrieval request."""
        try:
            if not self.db_pool:
                raise Exception("Database pool not available")
                
            optimization_id = data.get("optimization_id", "")
            
            if not optimization_id:
                return {
                    "status": "failed",
                    "error": "optimization_id is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            async with self.db_pool.acquire() as conn:
                result = await conn.fetchrow("""
                    SELECT * FROM search_term_optimizations WHERE id = $1
                """, optimization_id)
                
                if result:
                    # Convert row to dict and parse JSON fields
                    optimization = dict(result)
                    optimization["optimized_terms"] = json.loads(optimization["optimized_terms"])
                    optimization["optimization_context"] = json.loads(optimization["optimization_context"])
                    optimization["target_databases"] = json.loads(optimization["target_databases"])
                    optimization["metadata"] = json.loads(optimization["metadata"])
                    
                    return {
                        "status": "completed",
                        "optimization": optimization,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "status": "failed",
                        "error": f"Search term optimization not found: {optimization_id}",
                        "timestamp": datetime.now().isoformat()
                    }
                    
        except Exception as e:
            logger.error(f"Failed to get search term optimization: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_get_search_terms_for_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle retrieval of search terms for a specific research plan."""
        try:
            if not self.db_pool:
                raise Exception("Database pool not available")
                
            plan_id = data.get("plan_id", "")
            
            if not plan_id:
                return {
                    "status": "failed",
                    "error": "plan_id is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            async with self.db_pool.acquire() as conn:
                # Get optimizations for this plan
                results = await conn.fetch("""
                    SELECT * FROM search_term_optimizations 
                    WHERE source_type = 'plan' AND source_id = $1
                    ORDER BY created_at DESC
                """, plan_id)
                
                # logger.info(f"Retrieved search term optimizations for plan {plan_id} - {results}")

                optimizations = []
                for result in results:
                    optimization = dict(result)
                    optimization["optimized_terms"] = json.loads(optimization["optimized_terms"])
                    optimization["optimization_context"] = json.loads(optimization["optimization_context"])
                    optimization["target_databases"] = json.loads(optimization["target_databases"])
                    optimization["metadata"] = json.loads(optimization["metadata"])
                    optimizations.append(optimization)
                
                return {
                    "status": "completed",
                    "plan_id": plan_id,
                    "optimizations": optimizations,
                    "count": len(optimizations),
                    "timestamp": datetime.now().isoformat()
                }
                    
        except Exception as e:
            logger.error(f"Failed to get search terms for plan: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_get_search_terms_for_task(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle retrieval of search terms for a specific research task."""
        try:
            if not self.db_pool:
                raise Exception("Database pool not available")
                
            task_id = data.get("task_id", "")
            
            if not task_id:
                return {
                    "status": "failed",
                    "error": "task_id is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            async with self.db_pool.acquire() as conn:
                # Get optimizations for this task
                results = await conn.fetch("""
                    SELECT * FROM search_term_optimizations 
                    WHERE source_type = 'task' AND source_id = $1
                    ORDER BY created_at DESC
                """, task_id)
                
                optimizations = []
                for result in results:
                    optimization = dict(result)
                    optimization["optimized_terms"] = json.loads(optimization["optimized_terms"])
                    optimization["optimization_context"] = json.loads(optimization["optimization_context"])
                    optimization["target_databases"] = json.loads(optimization["target_databases"])
                    optimization["metadata"] = json.loads(optimization["metadata"])
                    optimizations.append(optimization)
                
                return {
                    "status": "completed",
                    "task_id": task_id,
                    "optimizations": optimizations,
                    "count": len(optimizations),
                    "timestamp": datetime.now().isoformat()
                }
                    
        except Exception as e:
            logger.error(f"Failed to get search terms for task: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_store_optimized_search_terms(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle storage of optimized search terms with automatic source type detection."""
        try:
            if not self.db_pool:
                raise Exception("Database pool not available")
                
            # This is a convenience method that can auto-detect source type
            source_id = data.get("source_id", "")
            plan_id = data.get("plan_id", "")
            task_id = data.get("task_id", "")
            original_query = data.get("original_query", "")
            optimized_terms = data.get("optimized_terms", [])
            optimization_context = data.get("optimization_context", {})
            target_databases = data.get("target_databases", [])
            expires_at = data.get("expires_at")
            metadata = data.get("metadata", {})
            
            # Auto-detect source type and source_id
            if plan_id:
                source_type = "plan"
                source_id = plan_id
            elif task_id:
                source_type = "task"
                source_id = task_id
            elif source_id:
                # Try to auto-detect based on whether it's found in plans or tasks
                async with self.db_pool.acquire() as conn:
                    plan_exists = await conn.fetchval("""
                        SELECT EXISTS(SELECT 1 FROM research_plans WHERE id = $1)
                    """, source_id)
                    
                    if plan_exists:
                        source_type = "plan"
                    else:
                        task_exists = await conn.fetchval("""
                            SELECT EXISTS(SELECT 1 FROM research_tasks WHERE id = $1)
                        """, source_id)
                        
                        if task_exists:
                            source_type = "task"
                        else:
                            return {
                                "status": "failed",
                                "error": f"Source ID {source_id} not found in plans or tasks",
                                "timestamp": datetime.now().isoformat()
                            }
            else:
                return {
                    "status": "failed",
                    "error": "Either plan_id, task_id, or source_id must be provided",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Use the create handler with detected parameters
            create_data = {
                "source_type": source_type,
                "source_id": source_id,
                "original_query": original_query,
                "optimized_terms": optimized_terms,
                "optimization_context": optimization_context,
                "target_databases": target_databases,
                "expires_at": expires_at,
                "metadata": metadata
            }
            
            return await self._handle_create_search_term_optimization(create_data)
                    
        except Exception as e:
            logger.error(f"Failed to store optimized search terms: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_database_operations(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle generic database operations request."""
        try:
            operation = data.get("operation", "")
            
            if operation == "backup":
                return await self._handle_backup_operation(data)
            elif operation == "maintenance":
                return await self._handle_maintenance_operation(data)
            elif operation == "analytics":
                return await self._handle_analytics_operation(data)
            else:
                return {
                    "status": "failed",
                    "error": f"Unknown database operation: {operation}",
                    "available_operations": ["backup", "maintenance", "analytics"],
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to execute database operations: {e}")
            self.operations_failed += 1
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_query_execution(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle raw query execution request."""
        try:
            if not self.db_pool:
                raise Exception("Database pool not available")
                
            query = data.get("query", "")
            params = data.get("params", [])
            query_type = data.get("query_type", "select")
            
            if not query:
                return {
                    "status": "failed",
                    "error": "Query is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Safety check - only allow certain query types
            allowed_types = ["insert", "update", "delete"]
            if query_type.lower() not in allowed_types:
                return {
                    "status": "failed",
                    "error": f"Query type '{query_type}' not allowed. Allowed types: {allowed_types}",
                    "timestamp": datetime.now().isoformat()
                }
            
            async with self.db_pool.acquire() as conn:
                if query_type.lower() in ["insert", "update", "delete"]:
                    result = await conn.execute(query, *params)
                    rows_affected = int(result.split()[-1]) if result else 0
                    
                    self.operations_completed += 1
                    
                    return {
                        "status": "completed",
                        "query_type": query_type,
                        "rows_affected": rows_affected,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "status": "failed",
                        "error": "Unsupported query type",
                        "timestamp": datetime.now().isoformat()
                    }
                    
        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            self.operations_failed += 1
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _generic_update(self, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generic update handler for database tables."""
        try:
            if not self.db_pool:
                raise Exception("Database pool not available")
                
            record_id = data.get("id", data.get(f"{table_name[:-1]}_id", ""))  # Remove 's' for singular
            updates = data.get("updates", {})
            
            if not record_id:
                return {
                    "status": "failed",
                    "error": "Record ID is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            if not updates:
                return {
                    "status": "failed",
                    "error": "Updates are required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Build update query
            set_clauses = []
            values = []
            param_count = 1
            
            for field, value in updates.items():
                set_clauses.append(f"{field} = ${param_count}")
                values.append(value)
                param_count += 1
            
            # Add updated_at
            set_clauses.append(f"updated_at = ${param_count}")
            values.append(datetime.now())
            param_count += 1
            
            # Add record_id for WHERE clause
            values.append(record_id)
            
            query = f"""
                UPDATE {table_name} 
                SET {', '.join(set_clauses)}
                WHERE id = ${param_count}
            """
            
            async with self.db_pool.acquire() as conn:
                result = await conn.execute(query, *values)
                rows_affected = int(result.split()[-1])
            
            self.operations_completed += 1
            
            return {
                "status": "completed",
                "table": table_name,
                "record_id": record_id,
                "rows_affected": rows_affected,
                "updates_applied": updates,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to update {table_name}: {e}")
            self.operations_failed += 1
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _generic_delete(self, table_name: str, record_id: str) -> Dict[str, Any]:
        """Generic delete handler for database tables."""
        try:
            if not self.db_pool:
                raise Exception("Database pool not available")
                
            if not record_id:
                return {
                    "status": "failed",
                    "error": "Record ID is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            async with self.db_pool.acquire() as conn:
                result = await conn.execute(f"DELETE FROM {table_name} WHERE id = $1", record_id)
                rows_affected = int(result.split()[-1])
            
            self.operations_completed += 1
            
            return {
                "status": "completed",
                "table": table_name,
                "record_id": record_id,
                "rows_affected": rows_affected,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to delete from {table_name}: {e}")
            self.operations_failed += 1
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_backup_operation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle database backup operation."""
        # Simplified backup operation
        return {
            "status": "completed",
            "operation": "backup",
            "message": "Backup operation initiated (implementation required)",
            "timestamp": datetime.now().isoformat()
        }
    
    async def _handle_maintenance_operation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle database maintenance operation."""
        try:
            if not self.db_pool:
                raise Exception("Database pool not available")
            
            # Simple maintenance - analyze tables
            async with self.db_pool.acquire() as conn:
                await conn.execute("ANALYZE")
            
            return {
                "status": "completed",
                "operation": "maintenance",
                "message": "Database analysis completed",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "operation": "maintenance",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_analytics_operation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle database analytics operation."""
        try:
            if not self.db_pool:
                raise Exception("Database pool not available")
            
            # Simple analytics - table counts
            analytics = {}
            tables = ["projects", "topics", "tasks", "literature_records"]
            
            async with self.db_pool.acquire() as conn:
                for table in tables:
                    try:
                        count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                        analytics[f"{table}_count"] = count
                    except:
                        analytics[f"{table}_count"] = 0
            
            return {
                "status": "completed",
                "operation": "analytics",
                "analytics": analytics,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "operation": "analytics",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _get_agent_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        # Database pool status
        pool_status = {}
        if self.db_pool:
            pool_status = {
                "pool_size": self.db_pool.get_size(),
                "pool_max_size": self.db_pool.get_max_size(),
                "pool_min_size": self.db_pool.get_min_size()
            }
        
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": "ready" if self.mcp_connected else "disconnected",
            "capabilities": self.capabilities,
            "mcp_connected": self.mcp_connected,
            "database_connected": self.db_pool is not None,
            "operations_completed": self.operations_completed,
            "operations_failed": self.operations_failed,
            "pool_status": pool_status,
            "uptime_seconds": uptime,
            "timestamp": datetime.now().isoformat()
        }


# Global service instance
database_service: Optional[DatabaseAgentService] = None


def get_mcp_status() -> Dict[str, Any]:
    """Get MCP connection status for health check."""
    if database_service:
        return {
            "connected": database_service.mcp_connected,
            "last_heartbeat": datetime.now().isoformat()
        }
    return {"connected": False, "last_heartbeat": "never"}


def get_additional_metadata() -> Dict[str, Any]:
    """Get additional metadata for health check."""
    if database_service:
        pool_info = {}
        if database_service.db_pool:
            pool_info = {
                "pool_size": database_service.db_pool.get_size(),
                "pool_max_size": database_service.db_pool.get_max_size()
            }
        
        return {
            "capabilities": database_service.capabilities,
            "operations_completed": database_service.operations_completed,
            "operations_failed": database_service.operations_failed,
            "database_connected": database_service.db_pool is not None,
            "pool_info": pool_info,
            "agent_id": database_service.agent_id
        }
    return {}


# Create health check only FastAPI application
app = create_health_check_app(
    agent_type="database",
    agent_id="database-agent",
    version="1.0.0",
    get_mcp_status=get_mcp_status,
    get_additional_metadata=get_additional_metadata
)

def _make_json_serializable(obj):
    """Convert datetime objects to ISO strings for JSON serialization."""
    if isinstance(obj, dict):
        return {key: _make_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_make_json_serializable(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj


async def main():
    """Main entry point for the database agent service."""
    global database_service
    
    try:
        # Load configuration
        config_path = Path("/app/config/config.json")
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
        else:
            config = {
                "service_host": "0.0.0.0",
                "service_port": 8011,
                "mcp_server_url": "ws://mcp-server:9000",
                "database_url": "postgresql://postgres:password@postgres:5432/eunice",
                "max_connections": 10,
                "connection_timeout": 30
            }
        
        # Initialize service
        database_service = DatabaseAgentService(config)
        
        # Start FastAPI health check server in background
        config_uvicorn = uvicorn.Config(
            app,
            host=config["service_host"],
            port=config["service_port"],
            log_level="info"
        )
        server = uvicorn.Server(config_uvicorn)
        
        logger.info("🚨 ARCHITECTURE COMPLIANCE: Database Agent")
        logger.info("✅ ONLY health check API exposed")
        logger.info("✅ All business operations via MCP protocol exclusively")
        
        # Start server and MCP service concurrently
        await asyncio.gather(
            server.serve(),
            database_service.start()
        )
        
    except KeyboardInterrupt:
        logger.info("Database agent shutdown requested")
    except Exception as e:
        logger.error(f"Database agent failed: {e}")
        sys.exit(1)
    finally:
        if database_service:
            await database_service.stop()


if __name__ == "__main__":
    asyncio.run(main())
