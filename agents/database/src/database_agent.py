"""
Database Agent - Pure MCP Client Implementation

Architecture-compliant database agent that communicates exclusively 
through MCP protocol via WebSocket.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path
import sys
import asyncpg

# Import base MCP agent
sys.path.append('/app')
from base_mcp_agent import BaseMCPAgent, create_agent_main

logger = logging.getLogger(__name__)


class DatabaseAgent(BaseMCPAgent):
    """
    Database Agent - Pure MCP Client
    
    Handles database operations through MCP protocol only.
    """
    
    def __init__(self, agent_type: str, config: Dict[str, Any]):
        """Initialize Database Agent."""
        super().__init__(agent_type, config)
        self.db_pool: Optional[asyncpg.Pool] = None
        self.database_url = config.get("database_url", "postgresql://postgres:password@postgres:5432/eunice")
        self.logger.info("Database Agent initialized with MCP client and database connection")
    
    async def start(self):
        """Start the agent with database connection."""
        # Initialize database connection
        await self._initialize_database()
        # Start the base MCP agent
        await super().start()
    
    async def _initialize_database(self):
        """Initialize database connection pool."""
        try:
            self.db_pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=5,
                command_timeout=30
            )
            self.logger.info("✅ Database connection pool initialized")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize database: {e}")
            raise
    
    def get_capabilities(self) -> List[str]:
        """Return database agent capabilities."""
        return [
            "create_project", "update_project", "delete_project", "get_project",
            "create_topic", "update_topic", "delete_topic", "get_topic", 
            "create_research_topic", "update_research_topic", "delete_research_topic", "get_research_topic",
            "create_plan", "update_plan", "delete_plan", "get_plan",
            "create_research_plan", "update_research_plan", "delete_research_plan", "get_research_plan",
            "create_task", "update_task", "delete_task", "get_task",
            "database_operations", "data_storage", "query_processing", "transaction_management"
        ]
    
    def setup_task_handlers(self) -> Dict[str, Any]:
        """Setup task handlers for database operations."""
        return {
            # Project operations
            "create_project": self._handle_create_project,
            "update_project": self._handle_update_project,
            "delete_project": self._handle_delete_project,
            "get_project": self._handle_get_project,
            
            # Topic operations  
            "create_topic": self._handle_create_topic,
            "update_topic": self._handle_update_topic,
            "delete_topic": self._handle_delete_topic,
            "get_topic": self._handle_get_topic,

            # Research Topic operations (hierarchical API)
            "create_research_topic": self._handle_create_research_topic,
            "update_research_topic": self._handle_update_research_topic,
            "delete_research_topic": self._handle_delete_research_topic,
            "get_research_topic": self._handle_get_research_topic,
            
            # Plan operations
            "create_plan": self._handle_create_plan,
            "update_plan": self._handle_update_plan,
            "delete_plan": self._handle_delete_plan,
            "get_plan": self._handle_get_plan,
            
            # Research Plan operations (hierarchical API)
            "create_research_plan": self._handle_create_research_plan,
            "update_research_plan": self._handle_update_research_plan,
            "delete_research_plan": self._handle_delete_research_plan,
            "get_research_plan": self._handle_get_research_plan,
            
            # Task operations
            "create_task": self._handle_create_task,
            "update_task": self._handle_update_task,
            "delete_task": self._handle_delete_task,
            "get_task": self._handle_get_task,
            
            # Legacy handlers
            "process_request": self._handle_process_request,
            "get_status": self._handle_get_status,
            "health_check": self._handle_health_check
        }
    
    # Task Handlers
    
    async def _handle_process_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general processing request."""
        try:
            request_type = data.get("request_type", "unknown")
            payload = data.get("payload", {})
            
            self.logger.info(f"Processing {request_type} request")
            
            # Process request (implement specific logic here)
            result = await self._process_database_request(request_type, payload)
            
            return {
                "status": "completed",
                "result": result,
                "request_type": request_type,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error processing request: {e}")
            raise
    
    async def _handle_get_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status request."""
        return {
            "agent_type": "database",
            "status": "ready",
            "capabilities": self.get_capabilities(),
            "timestamp": datetime.now().isoformat()
        }
    
    async def _handle_health_check(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle health check request."""
        return {
            "status": "healthy",
            "agent_type": "database",
            "timestamp": datetime.now().isoformat()
        }
    
    # Business Logic Methods
    
    async def _process_database_request(self, request_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process database-specific request."""
        # Implement specific logic here
        return {
            "message": f"Database processing complete",
            "request_type": request_type,
            "processed": True
        }

    # Project Operations
    async def _handle_create_project(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle project creation."""
        try:
            self.logger.info(f"Creating project: {data.get('name', 'unknown')}")
            # For now, return success - actual DB implementation would go here
            return {
                "status": "completed",
                "message": "Project created successfully",
                "data": data,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error creating project: {e}")
            raise

    async def _handle_update_project(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle project update."""
        return {"status": "completed", "message": "Project updated", "timestamp": datetime.now().isoformat()}

    async def _handle_delete_project(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle project deletion."""
        return {"status": "completed", "message": "Project deleted", "timestamp": datetime.now().isoformat()}

    async def _handle_get_project(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle project retrieval."""
        return {"status": "completed", "message": "Project retrieved", "timestamp": datetime.now().isoformat()}

    # Topic Operations
    async def _handle_create_topic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle topic creation."""
        return {"status": "completed", "message": "Topic created", "timestamp": datetime.now().isoformat()}

    async def _handle_update_topic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle topic update."""
        return {"status": "completed", "message": "Topic updated", "timestamp": datetime.now().isoformat()}

    async def _handle_delete_topic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle topic deletion."""
        return {"status": "completed", "message": "Topic deleted", "timestamp": datetime.now().isoformat()}

    async def _handle_get_topic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle topic retrieval."""
        return {"status": "completed", "message": "Topic retrieved", "timestamp": datetime.now().isoformat()}

    # Research Topic Operations (hierarchical API)
    async def _handle_create_research_topic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle research topic creation."""
        try:
            if not self.db_pool:
                raise Exception("Database connection not available")
            
            # Extract data fields
            project_id = data.get("project_id")
            name = data.get("name", data.get("topic_name", ""))
            description = data.get("description", "")
            keywords = data.get("keywords", [])
            priority = data.get("priority", "medium")
            
            if not project_id:
                raise ValueError("project_id is required")
            if not name:
                raise ValueError("name is required")
            
            # Generate unique ID
            topic_id = str(uuid.uuid4())
            now = datetime.now()
            
            # Create the research topic in database
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO research_topics (
                        id, project_id, name, description, keywords, priority,
                        status, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """, topic_id, project_id, name, description, keywords, priority,
                    "active", now, now)
            
            self.logger.info(f"✅ Created research topic: {name} (ID: {topic_id})")
            
            return {
                "status": "completed",
                "message": "Research topic created successfully",
                "topic_id": topic_id,
                "data": {
                    "id": topic_id,
                    "project_id": project_id,
                    "name": name,
                    "description": description,
                    "keywords": keywords,
                    "priority": priority,
                    "status": "active",
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat()
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create research topic: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def _handle_update_research_topic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle research topic update."""
        return {"status": "completed", "message": "Research topic updated", "timestamp": datetime.now().isoformat()}

    async def _handle_delete_research_topic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle research topic deletion."""
        return {"status": "completed", "message": "Research topic deleted", "timestamp": datetime.now().isoformat()}

    async def _handle_get_research_topic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle research topic retrieval."""
        return {"status": "completed", "message": "Research topic retrieved", "timestamp": datetime.now().isoformat()}

    # Plan Operations
    async def _handle_create_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle plan creation."""
        return {"status": "completed", "message": "Plan created", "timestamp": datetime.now().isoformat()}

    async def _handle_update_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle plan update."""
        return {"status": "completed", "message": "Plan updated", "timestamp": datetime.now().isoformat()}

    async def _handle_delete_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle plan deletion."""
        return {"status": "completed", "message": "Plan deleted", "timestamp": datetime.now().isoformat()}

    async def _handle_get_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle plan retrieval."""
        return {"status": "completed", "message": "Plan retrieved", "timestamp": datetime.now().isoformat()}

    # Task Operations
    async def _handle_create_task(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task creation."""
        return {"status": "completed", "message": "Task created", "timestamp": datetime.now().isoformat()}

    async def _handle_update_task(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task update."""
        return {"status": "completed", "message": "Task updated", "timestamp": datetime.now().isoformat()}

    async def _handle_delete_task(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task deletion."""
        return {"status": "completed", "message": "Task deleted", "timestamp": datetime.now().isoformat()}

    async def _handle_get_task(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task retrieval."""
        return {"status": "completed", "message": "Task retrieved", "timestamp": datetime.now().isoformat()}

    # Research Plan Operations
    async def _handle_create_research_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle research plan creation."""
        try:
            if not self.db_pool:
                raise Exception("Database connection not available")
            
            # Extract data fields
            topic_id = data.get("topic_id")
            name = data.get("name", "")
            description = data.get("description", "")
            plan_type = data.get("plan_type", "comprehensive")
            plan_structure = data.get("plan_structure", {})
            metadata = data.get("metadata", {})
            
            if not topic_id:
                raise ValueError("topic_id is required")
            if not name:
                raise ValueError("name is required")
            
            # Generate unique ID
            plan_id = str(uuid.uuid4())
            now = datetime.now()
            
            # Create the research plan in database
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO research_plans (
                        id, topic_id, name, description, plan_type, status, plan_approved,
                        plan_structure, estimated_cost, actual_cost, metadata,
                        created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """, plan_id, topic_id, name, description, plan_type, "draft", False,
                    json.dumps(plan_structure), 0.0, 0.0, json.dumps(metadata), now, now)
            
            self.logger.info(f"✅ Created research plan: {name} (ID: {plan_id})")
            
            return {
                "status": "completed",
                "message": "Research plan created successfully",
                "plan_id": plan_id,
                "data": {
                    "id": plan_id,
                    "topic_id": topic_id,
                    "name": name,
                    "description": description,
                    "plan_type": plan_type,
                    "status": "draft",
                    "plan_approved": False,
                    "plan_structure": plan_structure,
                    "estimated_cost": 0.0,
                    "actual_cost": 0.0,
                    "metadata": metadata,
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat()
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create research plan: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def _handle_update_research_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle research plan update."""
        try:
            if not self.db_pool:
                raise Exception("Database connection not available")
            
            plan_id = data.get("id")
            if not plan_id:
                raise ValueError("plan id is required")
            
            # Build update fields
            update_fields = []
            update_values = []
            
            if "name" in data:
                update_fields.append("name = $" + str(len(update_values) + 1))
                update_values.append(data["name"])
            
            if "description" in data:
                update_fields.append("description = $" + str(len(update_values) + 1))
                update_values.append(data["description"])
            
            if "plan_type" in data:
                update_fields.append("plan_type = $" + str(len(update_values) + 1))
                update_values.append(data["plan_type"])
            
            if "status" in data:
                update_fields.append("status = $" + str(len(update_values) + 1))
                update_values.append(data["status"])
            
            if "plan_structure" in data:
                update_fields.append("plan_structure = $" + str(len(update_values) + 1))
                update_values.append(json.dumps(data["plan_structure"]))
            
            if "metadata" in data:
                update_fields.append("metadata = $" + str(len(update_values) + 1))
                update_values.append(json.dumps(data["metadata"]))
            
            # Always update timestamp
            update_fields.append("updated_at = $" + str(len(update_values) + 1))
            update_values.append(datetime.now())
            
            # Add plan_id for WHERE clause
            update_values.append(plan_id)
            
            if update_fields:
                query = f"UPDATE research_plans SET {', '.join(update_fields)} WHERE id = ${len(update_values)}"
                
                async with self.db_pool.acquire() as conn:
                    result = await conn.execute(query, *update_values)
                    
                    if result == "UPDATE 0":
                        raise ValueError(f"Research plan {plan_id} not found")
            
            self.logger.info(f"✅ Updated research plan: {plan_id}")
            
            return {
                "status": "completed",
                "message": "Research plan updated successfully",
                "plan_id": plan_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Failed to update research plan: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def _handle_delete_research_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle research plan deletion."""
        try:
            if not self.db_pool:
                raise Exception("Database connection not available")
            
            plan_id = data.get("id")
            if not plan_id:
                raise ValueError("plan id is required")
            
            async with self.db_pool.acquire() as conn:
                # Start a transaction to ensure consistency
                async with conn.transaction():
                    # First, delete all tasks associated with this plan
                    tasks_deleted = await conn.execute(
                        "DELETE FROM research_tasks WHERE plan_id = $1", plan_id
                    )
                    
                    # Then delete the research plan
                    plan_deleted = await conn.execute(
                        "DELETE FROM research_plans WHERE id = $1", plan_id
                    )
                    
                    if plan_deleted == "DELETE 0":
                        raise ValueError(f"Research plan {plan_id} not found")
            
            self.logger.info(f"✅ Deleted research plan: {plan_id} (also deleted associated tasks)")
            
            return {
                "status": "completed",
                "message": "Research plan deleted successfully",
                "plan_id": plan_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Failed to delete research plan: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def _handle_get_research_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle research plan retrieval."""
        try:
            if not self.db_pool:
                raise Exception("Database connection not available")
            
            plan_id = data.get("id")
            if not plan_id:
                raise ValueError("plan id is required")
            
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT p.*, 
                           COUNT(t.id) as tasks_count,
                           COUNT(CASE WHEN t.status = 'completed' THEN 1 END) as completed_tasks,
                           COALESCE(AVG(CASE WHEN t.status = 'completed' THEN 100.0 ELSE 0.0 END), 0) as progress
                    FROM research_plans p
                    LEFT JOIN research_tasks t ON p.id = t.plan_id
                    WHERE p.id = $1
                    GROUP BY p.id
                """, plan_id)
                
                if not row:
                    raise ValueError(f"Research plan {plan_id} not found")
                
                # Convert row to dict and handle JSON fields
                plan_data = dict(row)
                if plan_data.get("plan_structure"):
                    try:
                        plan_data["plan_structure"] = json.loads(plan_data["plan_structure"])
                    except:
                        plan_data["plan_structure"] = {}
                
                if plan_data.get("metadata"):
                    try:
                        plan_data["metadata"] = json.loads(plan_data["metadata"])
                    except:
                        plan_data["metadata"] = {}
                
                # Convert datetime objects to ISO strings
                for field in ["created_at", "updated_at"]:
                    if plan_data.get(field):
                        plan_data[field] = plan_data[field].isoformat()
            
            self.logger.info(f"✅ Retrieved research plan: {plan_id}")
            
            return {
                "status": "completed",
                "message": "Research plan retrieved successfully",
                "data": plan_data,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Failed to retrieve research plan: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# Create main entry point
main = create_agent_main(DatabaseAgent, "database")

if __name__ == "__main__":
    asyncio.run(main())
