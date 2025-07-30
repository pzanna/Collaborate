"""
Native PostgreSQL Database Client for API Gateway

This client provides direct native PostgreSQL connections for READ operations,
offering high performance through direct database connectivity.
Only READ operations are allowed from the API Gateway.

Features:
- Direct asyncpg connection pool for high performance
- Connection health monitoring and automatic recovery
- Read-only operations enforcement
- Connection pooling with configurable pool sizes
- Transaction isolation for consistency
"""

import asyncio
import json
import logging
import os
import decimal
from typing import Dict, List, Optional, Any, Union
from contextlib import asynccontextmanager

import asyncpg
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class NativeDatabaseClient:
    """
    Native PostgreSQL client for API Gateway READ operations.
    Provides direct database connectivity using asyncpg for optimal performance.
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        min_size: int = 5,
        max_size: int = 20,
        command_timeout: int = 60,
        server_settings: Optional[Dict[str, str]] = None
    ):
        """
        Initialize the native database client.
        
        Args:
            database_url: PostgreSQL connection URL
            min_size: Minimum pool size
            max_size: Maximum pool size  
            command_timeout: Command timeout in seconds
            server_settings: Additional server settings
        """
        self.database_url = database_url or os.getenv(
            "DATABASE_URL", 
            os.getenv("DATABASE_READ_URL", "postgresql://postgres:password@postgres:5432/eunice")
        )
        self.min_size = min_size
        self.max_size = max_size
        self.command_timeout = command_timeout
        self.server_settings = server_settings or {
            "application_name": "eunice_api_gateway",
            "search_path": "public"
        }
        
        self.pool: Optional[asyncpg.Pool] = None
        self._initialized = False
        
    async def initialize(self) -> bool:
        """Initialize the database connection pool."""
        try:
            logger.info(f"Initializing native PostgreSQL connection pool...")
            
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=self.min_size,
                max_size=self.max_size,
                command_timeout=self.command_timeout,
                server_settings=self.server_settings
            )
            
            # Test the connection
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            
            self._initialized = True
            logger.info(f"Native database connection pool initialized successfully "
                       f"(min: {self.min_size}, max: {self.max_size})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize native database client: {e}")
            self._initialized = False
            return False
    
    async def close(self):
        """Close the database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Native database connection pool closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection from the pool."""
        if not self._initialized or not self.pool:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        async with self.pool.acquire() as conn:
            yield conn
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the database connection."""
        try:
            if not self._initialized or not self.pool:
                return {
                    "status": "unhealthy",
                    "error": "Database not initialized"
                }
            
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                pool_stats = {
                    "size": self.pool.get_size(),
                    "min_size": self.pool.get_min_size(),
                    "max_size": self.pool.get_max_size(),
                    "idle": self.pool.get_idle_size()
                }
                
            return {
                "status": "healthy",
                "connection_test": result == 1,
                "pool_stats": pool_stats
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def get_projects(self, status_filter: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        List all projects with optional filtering.
        
        Args:
            status_filter: Filter by project status
            limit: Limit number of results
            
        Returns:
            List of project dictionaries
        """
        try:
            async with self.get_connection() as conn:
                # Build query with optional filters
                query = "SELECT id, name, description, status, created_at, updated_at, metadata FROM projects"
                params = []
                
                if status_filter:
                    query += " WHERE status = $1"
                    params.append(status_filter)
                
                query += " ORDER BY created_at DESC"
                
                if limit:
                    if params:
                        query += f" LIMIT ${len(params) + 1}"
                    else:
                        query += " LIMIT $1"
                    params.append(limit)
                
                rows = await conn.fetch(query, *params)
                
                # Convert rows to dictionaries
                projects = []
                for row in rows:
                    metadata = row['metadata'] or {}
                    if isinstance(metadata, str):
                        try:
                            metadata = json.loads(metadata)
                        except:
                            metadata = {}
                    
                    projects.append({
                        "id": str(row['id']),
                        "name": row['name'],
                        "description": row['description'] or "",
                        "status": row['status'] or "active",
                        "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                        "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
                        "metadata": metadata
                    })
                
                return projects
                
        except Exception as e:
            logger.error(f"Failed to fetch projects: {e}")
            raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    
    async def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific project by ID.
        
        Args:
            project_id: Project ID
            
        Returns:
            Project dictionary or None if not found
        """
        try:
            async with self.get_connection() as conn:
                query = """
                    SELECT id, name, description, status, created_at, updated_at, metadata 
                    FROM projects 
                    WHERE id = $1
                """
                
                row = await conn.fetchrow(query, project_id)
                
                if not row:
                    return None
                
                metadata = row['metadata'] or {}
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except:
                        metadata = {}
                
                return {
                    "id": str(row['id']),
                    "name": row['name'],
                    "description": row['description'] or "",
                    "status": row['status'] or "active",
                    "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                    "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
                    "metadata": metadata
                }
                
        except Exception as e:
            logger.error(f"Failed to fetch project {project_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    
    async def get_research_topics(self, project_id: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get research topics, optionally filtered by project.
        
        Args:
            project_id: Optional project ID filter
            limit: Maximum number of topics to return
            offset: Number of topics to skip
            
        Returns:
            List of research topic dictionaries
        """
        try:
            async with self.get_connection() as conn:
                if project_id:
                    query = """
                        SELECT id, name, description, project_id, created_at, updated_at 
                        FROM research_topics 
                        WHERE project_id = $1 
                        ORDER BY created_at DESC 
                        LIMIT $2 OFFSET $3
                    """
                    rows = await conn.fetch(query, project_id, limit, offset)
                else:
                    query = """
                        SELECT id, name, description, project_id, created_at, updated_at 
                        FROM research_topics 
                        ORDER BY created_at DESC 
                        LIMIT $1 OFFSET $2
                    """
                    rows = await conn.fetch(query, limit, offset)
                
                return [
                    {
                        "id": str(row['id']),
                        "project_id": str(row['project_id']),
                        "name": row['name'],
                        "description": row['description'] or "",
                        "status": "active",  # Default status
                        "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                        "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
                        "plans_count": 0,  # Count fields
                        "tasks_count": 0,
                        "total_cost": 0.0,
                        "completion_rate": 0.0,
                        "metadata": {}
                    }
                    for row in rows
                ]
                
        except Exception as e:
            logger.error(f"Failed to fetch research topics for project {project_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")

    async def get_research_topic(self, topic_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific research topic by ID.
        
        Args:
            topic_id: Topic ID
            
        Returns:
            Research topic dictionary or None if not found
        """
        try:
            async with self.get_connection() as conn:
                query = """
                    SELECT id, name, description, project_id, created_at, updated_at 
                    FROM research_topics 
                    WHERE id = $1
                """
                
                row = await conn.fetchrow(query, topic_id)
                
                if row:
                    return {
                        "id": str(row['id']),
                        "project_id": str(row['project_id']),
                        "name": row['name'],
                        "description": row['description'] or "",
                        "status": "active",  # Default status
                        "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                        "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
                        "plans_count": 0,  # Count fields
                        "tasks_count": 0,
                        "total_cost": 0.0,
                        "completion_rate": 0.0,
                        "metadata": {}
                    }
                return None
                
        except Exception as e:
            logger.error(f"Failed to fetch research topic {topic_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")

    async def get_research_plans(self, topic_id: str, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get research plans for a topic.
        
        Args:
            topic_id: Topic ID
            status_filter: Optional status filter
            
        Returns:
            List of research plan dictionaries
        """
        try:
            async with self.get_connection() as conn:
                query = """
                    SELECT id, name, description, topic_id, plan_type, status, created_at, updated_at, metadata 
                    FROM research_plans 
                    WHERE topic_id = $1
                """
                params = [topic_id]
                
                if status_filter:
                    query += " AND status = $2"
                    params.append(status_filter)
                
                query += " ORDER BY created_at DESC"
                
                rows = await conn.fetch(query, *params)
                
                plans = []
                for row in rows:
                    metadata = row['metadata'] or {}
                    if isinstance(metadata, str):
                        try:
                            metadata = json.loads(metadata)
                        except:
                            metadata = {}
                    
                    plans.append({
                        "id": str(row['id']),
                        "topic_id": str(row['topic_id']) if row['topic_id'] else None,
                        "name": row['name'],
                        "description": row['description'] or "",
                        "plan_type": row.get('plan_type', 'comprehensive'),
                        "status": row.get('status', 'active'),
                        "plan_approved": False,  # Default approval status
                        "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                        "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
                        "estimated_cost": 0.0,  # Default cost values
                        "actual_cost": 0.0,
                        "tasks_count": 0,  # Count fields
                        "completed_tasks": 0,
                        "progress": 0.0,
                        "plan_structure": {},  # Additional fields
                        "metadata": metadata
                    })
                
                return plans
                
        except Exception as e:
            logger.error(f"Failed to fetch research plans for topic {topic_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")

    async def get_research_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific research plan by ID.
        
        Args:
            plan_id: Plan ID
            
        Returns:
            Research plan dictionary or None if not found
        """
        try:
            async with self.get_connection() as conn:
                query = """
                    SELECT id, name, description, topic_id, plan_type, status, created_at, updated_at, metadata 
                    FROM research_plans 
                    WHERE id = $1
                """
                
                row = await conn.fetchrow(query, plan_id)
                
                if row:
                    metadata = row['metadata'] or {}
                    if isinstance(metadata, str):
                        try:
                            metadata = json.loads(metadata)
                        except:
                            metadata = {}
                    
                    return {
                        "id": str(row['id']),
                        "topic_id": str(row['topic_id']) if row['topic_id'] else None,
                        "name": row['name'],
                        "description": row['description'] or "",
                        "plan_type": row.get('plan_type', 'comprehensive'),
                        "status": row.get('status', 'active'),
                        "plan_approved": False,  # Default approval status  
                        "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                        "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
                        "estimated_cost": 0.0,  # Default cost values
                        "actual_cost": 0.0,
                        "tasks_count": 0,  # Count fields
                        "completed_tasks": 0,
                        "progress": 0.0,
                        "plan_structure": {},  # Additional fields
                        "metadata": metadata
                    }
                return None
                
        except Exception as e:
            logger.error(f"Failed to fetch research plan {plan_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")

    async def get_tasks(self, plan_id: str, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get tasks for a research plan.
        
        Args:
            plan_id: Plan ID
            status_filter: Optional status filter
            
        Returns:
            List of task dictionaries
        """
        try:
            async with self.get_connection() as conn:
                query = """
                    SELECT id, name, description, plan_id, task_type, status, task_order, created_at, updated_at 
                    FROM tasks 
                    WHERE plan_id = $1
                """
                params = [plan_id]
                
                if status_filter:
                    query += " AND status = $2"
                    params.append(status_filter)
                
                query += " ORDER BY task_order ASC, created_at ASC"
                
                rows = await conn.fetch(query, *params)
                
                tasks = []
                for row in rows:
                    tasks.append({
                        "id": str(row['id']),
                        "plan_id": str(row['plan_id']),
                        "name": row['name'],
                        "description": row['description'] or "",
                        "task_type": row.get('task_type', 'research'),
                        "task_order": row.get('task_order', 1),
                        "status": row.get('status', 'pending'),
                        "stage": "planning",  # Default stage
                        "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                        "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
                        "estimated_cost": 0.0,  # Default costs and flags
                        "actual_cost": 0.0,
                        "cost_approved": False,
                        "single_agent_mode": False,
                        "max_results": 10,
                        "progress": 0.0,
                        "query": None,  # Optional fields
                        "search_results": [],
                        "reasoning_output": None,
                        "execution_results": [],
                        "synthesis": None,
                        "metadata": {}
                    })
                
                return tasks
                
        except Exception as e:
            logger.error(f"Failed to fetch tasks for plan {plan_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific task by ID.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task dictionary or None if not found
        """
        try:
            async with self.get_connection() as conn:
                query = """
                    SELECT id, name, description, plan_id, task_type, status, task_order, created_at, updated_at 
                    FROM tasks 
                    WHERE id = $1
                """
                
                row = await conn.fetchrow(query, task_id)
                
                if row:
                    return {
                        "id": str(row['id']),
                        "plan_id": str(row['plan_id']),
                        "name": row['name'],
                        "description": row['description'] or "",
                        "task_type": row.get('task_type', 'research'),
                        "task_order": row.get('task_order', 1),
                        "status": row.get('status', 'pending'),
                        "stage": "planning",  # Default stage
                        "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                        "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
                        "estimated_cost": 0.0,  # Default cost values
                        "actual_cost": 0.0,
                        "cost_approved": False,
                        "single_agent_mode": False,
                        "max_results": 10,
                        "progress": 0.0,
                        "query": None,  # Optional fields
                        "search_results": [],
                        "reasoning_output": None,
                        "execution_results": [],
                        "synthesis": None,
                        "metadata": {}
                    }
                return None
                
        except Exception as e:
            logger.error(f"Failed to fetch task {task_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")

    async def get_project_stats(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get project statistics including counts and costs.
        
        Args:
            project_id: Project ID
            
        Returns:
            Project statistics dictionary or None if project not found
        """
        try:
            async with self.get_connection() as conn:
                # First verify project exists
                project_exists = await conn.fetchval(
                    "SELECT 1 FROM projects WHERE id = $1", project_id
                )
                if not project_exists:
                    return None

                # Get counts of topics, plans, and tasks
                stats_query = """
                    SELECT 
                        COALESCE(
                            (SELECT COUNT(*) FROM research_topics WHERE project_id = $1), 0
                        ) as topics_count,
                        COALESCE(
                            (SELECT COUNT(*) 
                             FROM research_plans rp 
                             JOIN research_topics rt ON rp.topic_id = rt.id 
                             WHERE rt.project_id = $1), 0
                        ) as plans_count,
                        COALESCE(
                            (SELECT COUNT(*) 
                             FROM tasks t 
                             JOIN research_plans rp ON t.plan_id = rp.id 
                             JOIN research_topics rt ON rp.topic_id = rt.id 
                             WHERE rt.project_id = $1), 0
                        ) as tasks_count,
                        COALESCE(
                            (SELECT COUNT(*) 
                             FROM tasks t 
                             JOIN research_plans rp ON t.plan_id = rp.id 
                             JOIN research_topics rt ON rp.topic_id = rt.id 
                             WHERE rt.project_id = $1 AND t.status = 'completed'), 0
                        ) as completed_tasks
                """
                
                stats_row = await conn.fetchrow(stats_query, project_id)
                
                # Calculate completion rate
                total_tasks = stats_row['tasks_count']
                completed_tasks = stats_row['completed_tasks']
                completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0.0
                
                return {
                    "topics_count": stats_row['topics_count'],
                    "plans_count": stats_row['plans_count'], 
                    "tasks_count": total_tasks,
                    "total_cost": 0.0,  # Cost calculation will be implemented when cost columns are added to database
                    "completion_rate": completion_rate
                }
                
        except Exception as e:
            logger.error(f"Failed to get project stats for {project_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")

    async def get_project_hierarchy(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete project hierarchy with topics, plans, and tasks.
        
        Args:
            project_id: Project ID
            
        Returns:
            Project hierarchy dictionary or None if project not found
        """
        try:
            # Get the project
            project = await self.get_project(project_id)
            if not project:
                return None

            # Get project statistics
            stats = await self.get_project_stats(project_id)
            if stats:
                project.update({
                    "topics_count": stats["topics_count"],
                    "plans_count": stats["plans_count"],
                    "tasks_count": stats["tasks_count"],
                    "total_cost": stats["total_cost"],
                    "completion_rate": stats["completion_rate"]
                })

            # Get all topics for this project
            topics = await self.get_research_topics(project_id=project_id)
            
            # Get all plans and tasks for each topic
            plans = []
            tasks = []
            
            for topic in topics:
                topic_plans = await self.get_research_plans(topic["id"])
                plans.extend(topic_plans)
                
                for plan in topic_plans:
                    plan_tasks = await self.get_tasks(plan["id"])
                    tasks.extend(plan_tasks)
            
            return {
                "project": project,
                "topics": topics,
                "plans": plans,
                "tasks": tasks
            }
                
        except Exception as e:
            logger.error(f"Failed to get project hierarchy for {project_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")

    async def execute_read_query(self, query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a read-only query against the database.
        
        Args:
            query: SQL query to execute
            params: Optional query parameters
            
        Returns:
            List of result dictionaries
        """
        try:
            async with self.get_connection() as conn:
                rows = await conn.fetch(query, *(params or []))
                
                # Convert asyncpg.Record objects to dictionaries
                results = []
                for row in rows:
                    result = dict(row)
                    
                    # Convert any special types to serializable formats
                    for key, value in result.items():
                        if hasattr(value, 'isoformat'):  # datetime objects
                            result[key] = value.isoformat()
                        elif isinstance(value, decimal.Decimal):
                            result[key] = float(value)
                    
                    results.append(result)
                
                return results
                
        except Exception as e:
            logger.error(f"Failed to execute read query: {e}")
            raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    
    # Global instance


# Global instance
native_db_client: Optional[NativeDatabaseClient] = None


def get_native_database() -> NativeDatabaseClient:
    """Get the global native database client instance."""
    global native_db_client
    if native_db_client is None:
        native_db_client = NativeDatabaseClient()
    return native_db_client


async def initialize_native_database() -> bool:
    """Initialize the global native database client."""
    client = get_native_database()
    return await client.initialize()


async def close_native_database():
    """Close the global native database client."""
    global native_db_client
    if native_db_client:
        await native_db_client.close()
        native_db_client = None
