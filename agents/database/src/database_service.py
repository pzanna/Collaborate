"""
Database Agent Service - Containerized MCP Client

This service acts as a containerized Database Agent that connects to the MCP server
via WebSocket and provides database write operations through direct database access.

Architecture:
- Connects to MCP Server as a client agent
- Receives database operation requests from MCP Server
- Connects directly to the database (no HTTP layer)
- Handles all database write operations (CREATE, UPDATE, DELETE)
- Read operations go directly from API Gateway to PostgreSQL for performance
"""

import asyncio
import json
import logging
import os
import signal
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import uvicorn
import websockets
from fastapi import FastAPI
from websockets.exceptions import ConnectionClosed, WebSocketException

# Import database libraries directly
sys.path.append('/app')
import asyncpg

# Configuration
SERVICE_HOST = os.getenv("SERVICE_HOST", "0.0.0.0")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8011"))
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "ws://mcp-server:9000")
AGENT_TYPE = os.getenv("AGENT_TYPE", "database")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/eunice")

# Setup logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("database_agent_direct")


class DatabaseAgentService:
    """Containerized Database Agent Service with Direct Database Access"""
    
    def __init__(self):
        self.websocket = None
        self.is_connected = False
        self.should_run = True
        self.start_time = asyncio.get_event_loop().time()
        self.agent_id = f"database-{os.getpid()}"
        self.database_url = DATABASE_URL
        
        # Database Agent capabilities
        self.capabilities = [
            "create_project", "update_project", "delete_project",
            "create_topic", "update_topic", "delete_topic", 
            "create_plan", "update_plan", "delete_plan",
            "create_task", "update_task", "delete_task",
            "database_operations"
        ]
        
        logger.info(f"Database Agent Service initialized with ID: {self.agent_id}")
        logger.info(f"Loaded capabilities: {self.capabilities}")

    async def test_database_connection(self):
        """Test direct database connection"""
        try:
            conn = await asyncpg.connect(self.database_url)
            await conn.fetchval("SELECT 1")
            await conn.close()
            logger.info("✅ Database Agent established direct database connection")
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            raise

    async def connect_to_mcp_server(self):
        """Connect to MCP server via WebSocket"""
        max_retries = 5
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to connect to MCP server at {MCP_SERVER_URL} (attempt {attempt + 1})")
                
                self.websocket = await websockets.connect(
                    MCP_SERVER_URL,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=10
                )
                
                self.is_connected = True
                logger.info("Successfully connected to MCP server")
                
                # Register agent with MCP server
                await self.register_agent()
                return
                
            except Exception as e:
                logger.error(f"Failed to connect to MCP server (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error("Max retries reached. Could not connect to MCP server")
                    raise

    async def register_agent(self):
        """Register this agent with the MCP server"""
        if not self.websocket:
            logger.error("Cannot register agent: no websocket connection")
            return
            
        registration_message = {
            "type": "agent_register",
            "agent_id": self.agent_id,
            "agent_type": AGENT_TYPE,
            "capabilities": self.capabilities,
            "service_info": {
                "port": SERVICE_PORT,
                "health_endpoint": f"http://localhost:{SERVICE_PORT}/health"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.websocket.send(json.dumps(registration_message))
        logger.info(f"Registered Database Agent {self.agent_id} with MCP server")

    async def listen_for_tasks(self):
        """Listen for tasks from MCP server"""
        if not self.websocket:
            logger.error("Cannot listen for tasks: no websocket connection")
            return
            
        logger.info("Starting to listen for tasks from MCP server")
        
        try:
            async for message in self.websocket:
                if not self.should_run:
                    break
                    
                try:
                    data = json.loads(message)
                    await self.handle_mcp_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse MCP message: {e}")
                except Exception as e:
                    logger.error(f"Error handling MCP message: {e}")
                    
        except ConnectionClosed:
            logger.warning("MCP server connection closed")
            self.is_connected = False
        except WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Unexpected error in message listener: {e}")
            self.is_connected = False

    async def handle_mcp_message(self, data: Dict[str, Any]):
        """Handle incoming MCP message"""
        if not self.websocket:
            logger.error("Cannot handle MCP message: no websocket connection")
            return
            
        message_type = data.get("type")
        logger.info(f"Received MCP message: {message_type}")
        
        if message_type == "task_request":
            # Execute database task
            task_id = data.get("task_id")
            task_type = data.get("task_type", "database_operation")
            task_data = data.get("data", {})
            context_id = data.get("context_id")
            
            try:
                result = await self.execute_database_task({
                    "action": task_type,
                    "payload": task_data
                })
                response = {
                    "type": "task_result",
                    "task_id": task_id,
                    "status": "completed",
                    "result": result,
                    "agent_id": self.agent_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            except Exception as e:
                logger.error(f"Error executing database task: {e}")
                response = {
                    "type": "task_result",
                    "task_id": task_id,
                    "status": "failed",
                    "error": str(e),
                    "agent_id": self.agent_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            await self.websocket.send(json.dumps(response))
            
        elif message_type == "registration_confirmed":
            logger.info("Database Agent registration confirmed by MCP server")
            
        elif message_type == "ping":
            # Respond to health check
            response = {
                "type": "pong",
                "agent_id": self.agent_id,
                "status": "healthy",
                "capabilities": self.capabilities,
                "timestamp": datetime.utcnow().isoformat()
            }
            await self.websocket.send(json.dumps(response))
            
        else:
            logger.warning(f"Unknown MCP message type: {message_type}")

    async def execute_database_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a database task by communicating with Database Service"""
        action = task_data.get("action")
        payload = task_data.get("payload", {})
        
        logger.info(f"Executing database task: {action}")
        
        if action == "create_project":
            return await self._create_project(payload)
        elif action == "update_project":
            return await self._update_project(payload)
        elif action == "delete_project":
            return await self._delete_project(payload)
        elif action == "create_topic":
            return await self._create_topic(payload)
        elif action == "update_topic":
            return await self._update_topic(payload)
        elif action == "delete_topic":
            return await self._delete_topic(payload)
        elif action == "create_plan":
            return await self._create_plan(payload)
        elif action == "update_plan":
            return await self._update_plan(payload)
        elif action == "delete_plan":
            return await self._delete_plan(payload)
        elif action == "create_task":
            return await self._create_task(payload)
        elif action == "update_task":
            return await self._update_task(payload)
        elif action == "delete_task":
            return await self._delete_task(payload)
        else:
            raise ValueError(f"Unknown database action: {action}")

    # Project Operations - Direct Database Access
    async def _create_project(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new project via direct database connection"""
        try:
            # Extract parameters from payload
            name = payload.get('name')
            description = payload.get('description', '')
            status = payload.get('status', 'active')
            metadata = payload.get('metadata', '{}')
            
            if not name:
                raise ValueError("Project name is required")
            
            # Connect directly to database
            conn = await asyncpg.connect(self.database_url)
            
            # Generate UUID and timestamps
            import uuid
            project_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            # Insert project
            await conn.execute("""
                INSERT INTO projects (id, name, description, status, created_at, updated_at, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, project_id, name, description, status, now, now, metadata)
            
            await conn.close()
            
            project_data = {
                "id": project_id,
                "name": name,
                "description": description,
                "status": status,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "metadata": metadata
            }
            
            logger.info(f"Successfully created project: {project_id}")
            return {
                "success": True,
                "project": project_data,
                "message": "Project created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error creating project: {e}")
            raise Exception(f"Database operation failed: {str(e)}")

    async def _update_project(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Update a project via direct database connection"""
        project_id = payload.get("id")
        if not project_id:
            raise ValueError("Project ID is required for update")
            
        try:
            conn = await asyncpg.connect(self.database_url)
            
            # Build update query dynamically
            update_fields = []
            params = []
            param_count = 1
            
            for field in ['name', 'description', 'status', 'metadata']:
                if field in payload and payload[field] is not None:
                    update_fields.append(f"{field} = ${param_count}")
                    params.append(payload[field])
                    param_count += 1
            
            # Always update the updated_at timestamp
            now = datetime.utcnow()
            update_fields.append(f"updated_at = ${param_count}")
            params.append(now)
            param_count += 1
            
            # Add project_id as the last parameter
            params.append(project_id)
            
            # Execute update
            query = f"""
                UPDATE projects 
                SET {', '.join(update_fields)}
                WHERE id = ${param_count}
                RETURNING id, name, description, status, created_at, updated_at, metadata
            """
            
            row = await conn.fetchrow(query, *params)
            await conn.close()
            
            if not row:
                raise Exception("Project not found")
            
            project_data = {
                "id": str(row['id']),
                "name": row['name'],
                "description": row['description'] or "",
                "status": row['status'] or "active",
                "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
                "metadata": row['metadata'] or "{}"
            }
            
            logger.info(f"Successfully updated project: {project_id}")
            return {
                "success": True,
                "project": project_data,
                "message": "Project updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Error updating project: {e}")
            raise Exception(f"Database operation failed: {str(e)}")

    async def _delete_project(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a project via direct database connection"""
        project_id = payload.get("id")
        if not project_id:
            raise ValueError("Project ID is required for deletion")
            
        try:
            conn = await asyncpg.connect(self.database_url)
            
            # Check if project exists and delete
            result = await conn.execute("DELETE FROM projects WHERE id = $1", project_id)
            await conn.close()
            
            # Check if any rows were affected
            rows_affected = int(result.split()[-1])  # Extract number from "DELETE 1"
            if rows_affected == 0:
                raise Exception("Project not found")
            
            logger.info(f"Successfully deleted project: {project_id}")
            return {
                "success": True,
                "message": "Project deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"Error deleting project: {e}")
            raise Exception(f"Database operation failed: {str(e)}")

    # NOTE: Research topic, plan, and task operations are placeholder implementations
    # These will be implemented when the Database Service adds corresponding endpoints
    
    async def _create_topic(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a research topic via Database Service"""
        # Research topic endpoints are not yet available in Database Service
        return {"success": True, "message": "Topic operations not yet implemented"}
    
    async def _update_topic(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Update a research topic via Database Service"""
        # Research topic endpoints are not yet available in Database Service
        return {"success": True, "message": "Topic operations not yet implemented"}
    
    async def _delete_topic(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a research topic via Database Service"""
        # Research topic endpoints are not yet available in Database Service
        return {"success": True, "message": "Topic operations not yet implemented"}
    
    async def _create_plan(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a research plan via Database Service"""
        # Research plan endpoints are not yet available in Database Service
        return {"success": True, "message": "Plan operations not yet implemented"}

    async def _update_plan(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Update a research plan via Database Service"""
        # Research plan endpoints are not yet available in Database Service
        return {"success": True, "message": "Plan operations not yet implemented"}

    async def _delete_plan(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a research plan via Database Service"""
        # Research plan endpoints are not yet available in Database Service
        return {"success": True, "message": "Plan operations not yet implemented"}

    async def _create_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a task via Database Service"""
        # Task endpoints are not yet available in Database Service
        return {"success": True, "message": "Task operations not yet implemented"}

    async def _update_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Update a task via Database Service"""
        # Task endpoints are not yet available in Database Service
        return {"success": True, "message": "Task operations not yet implemented"}

    async def _delete_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a task via Database Service"""
        # Task endpoints are not yet available in Database Service
        return {"success": True, "message": "Task operations not yet implemented"}


# FastAPI app for health checks
app = FastAPI(title="Database Agent Service", version="1.0.0")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "service": "database-agent",
        "status": "healthy",
        "agent_id": database_service.agent_id if database_service else "unknown",
        "mcp_connected": database_service.is_connected if database_service else False,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/status")
async def get_status():
    """Detailed status endpoint"""
    return {
        "service": "database-agent",
        "agent_id": database_service.agent_id if database_service else "unknown",
        "mcp_connected": database_service.is_connected if database_service else False,
        "capabilities": database_service.capabilities if database_service else [],
        "uptime_seconds": asyncio.get_event_loop().time() - database_service.start_time if database_service else 0,
        "timestamp": datetime.utcnow().isoformat()
    }


# Global service instance
database_service = None


async def run_database_agent():
    """Run the Database Agent service"""
    global database_service
    
    try:
        database_service = DatabaseAgentService()
        
        # Test database connection
        await database_service.test_database_connection()
        
        # Connect to MCP server
        await database_service.connect_to_mcp_server()
        
        # Start listening for tasks in background
        task_listener = asyncio.create_task(database_service.listen_for_tasks())
        
        # Start FastAPI server for health checks
        config = uvicorn.Config(
            app,
            host=SERVICE_HOST,
            port=SERVICE_PORT,
            log_level="info",
            access_log=False
        )
        server = uvicorn.Server(config)
        
        # Run both the MCP listener and HTTP server
        await asyncio.gather(
            task_listener,
            server.serve()
        )
        
    except Exception as e:
        logger.error(f"Database Agent service error: {e}")
        sys.exit(1)


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    if database_service:
        database_service.should_run = False
    sys.exit(0)


def main():
    """Main entry point"""
    # Setup signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("Starting Database Agent Service...")
    
    try:
        asyncio.run(run_database_agent())
    except KeyboardInterrupt:
        logger.info("Database Agent Service stopped by user")
    except Exception as e:
        logger.error(f"Failed to start Database Agent Service: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
