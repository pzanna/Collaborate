"""
Database Agent - Centralized data access and persistence service.

This agent encapsulates all database write operations and provides an API
that shields other components from schema changes, following the Architecture.md
North Star design.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ...config.config_manager import ConfigManager
from ...database.core.manager import HierarchicalDatabaseManager
from ...mcp.protocols import AgentResponse, ResearchAction, TaskStatus
from ...utils.error_handler import DatabaseError, handle_errors
from ..base_agent import BaseAgent

logger = logging.getLogger(__name__)


class DatabaseAgent(BaseAgent):
    """
    Database Agent Service - Centralized data access layer.
    
    Provides:
    - Schema abstraction and migration management
    - Centralized write operations
    - Caching and performance optimization
    - Transaction management and consistency
    """

    def __init__(self, config_manager: ConfigManager, db_path: Optional[str] = None):
        super().__init__("database_agent", config_manager)
        self.db_manager = HierarchicalDatabaseManager(db_path)
        self.cache = {}  # Simple in-memory cache for read operations
        self.cache_ttl = 300  # 5 minutes cache TTL
        self.cache_timestamps = {}
        
        logger.info("Database Agent initialized with centralized data access")

    # Abstract method implementations from BaseAgent

    async def _process_task_impl(self, task: ResearchAction) -> Dict[str, Any]:
        """Process a task implementation - delegates to process_action."""
        response = await self.process_action(task)
        return {
            "status": response.status,
            "result": response.result,
            "error": response.error
        }

    def _get_capabilities(self) -> List[str]:
        """Get Database Agent capabilities."""
        return [
            "create_project", "create_topic", "create_plan", "create_task",
            "update_project", "update_topic", "update_plan", "update_task", 
            "get_project", "get_topic", "get_plan", "get_task",
            "list_projects", "list_topics", "list_plans", "list_tasks",
            "delete_project", "delete_topic", "delete_plan", "delete_task",
            "health_check"
        ]

    async def _initialize_agent(self) -> None:
        """Initialize Database Agent resources."""
        # Database manager is already initialized in __init__
        # Test database connection
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
            logger.info("Database Agent initialization completed successfully")
        except Exception as e:
            logger.error(f"Database Agent initialization failed: {str(e)}")
            raise

    async def _cleanup_agent(self) -> None:
        """Clean up Database Agent resources."""
        # Clear cache
        self.cache.clear()
        self.cache_timestamps.clear()
        logger.info("Database Agent cleanup completed")

    async def process_action(self, action: ResearchAction) -> AgentResponse:
        """
        Process database actions through the MCP protocol.
        
        Supported actions:
        - create_project, create_topic, create_plan, create_task
        - update_project, update_topic, update_plan, update_task
        - get_project, get_topic, get_plan, get_task
        - list_projects, list_topics, list_plans, list_tasks
        - delete_project, delete_topic, delete_plan, delete_task
        """
        try:
            action_type = action.action
            params = action.payload or {}

            # Route to appropriate handler
            if action_type.startswith("create_"):
                result = await self._handle_create_operation(action_type, params)
            elif action_type.startswith("update_"):
                result = await self._handle_update_operation(action_type, params)
            elif action_type.startswith("get_"):
                result = await self._handle_get_operation(action_type, params)
            elif action_type.startswith("list_"):
                result = await self._handle_list_operation(action_type, params)
            elif action_type.startswith("delete_"):
                result = await self._handle_delete_operation(action_type, params)
            else:
                raise DatabaseError(f"Unsupported database action: {action_type}", "database_agent")

            return AgentResponse(
                task_id=action.task_id,
                context_id=action.context_id,
                agent_type=self.agent_type,
                status=TaskStatus.COMPLETED.value,
                result=result
            )

        except Exception as e:
            logger.error(f"Database Agent error processing {action.action}: {str(e)}")
            return AgentResponse(
                task_id=action.task_id,
                context_id=action.context_id,
                agent_type=self.agent_type,
                status=TaskStatus.FAILED.value,
                error=str(e)
            )

    # CREATE Operations
    async def _handle_create_operation(self, action_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle all create operations with transaction support."""
        
        if action_type == "create_project":
            return await self._create_project(params)
        elif action_type == "create_topic" or action_type == "create_research_topic":
            return await self._create_topic(params)
        elif action_type == "create_plan" or action_type == "create_research_plan":
            return await self._create_plan(params)
        elif action_type == "create_task":
            return await self._create_task(params)
        else:
            raise DatabaseError(f"Unsupported create operation: {action_type}", "database_agent_create")

    @handle_errors("database_agent_create_project")
    async def _create_project(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new research project."""
        project_data = {
            "name": params.get("name"),
            "description": params.get("description", ""),
            "status": params.get("status", "active"),
            "metadata": json.dumps(params.get("metadata", {}))  # Serialize metadata as JSON
        }
        
        result = self.db_manager.create_project(project_data)
        self._invalidate_cache("projects")
        
        if result:
            return {
                "project_id": result.get("id"),
                "created_at": result.get("created_at"),
                "status": "created"
            }
        else:
            raise DatabaseError("Failed to create project", "create_project")
        

    @handle_errors("database_agent_create_topic")
    async def _create_topic(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new research topic."""
        topic_data = {
            "project_id": params.get("project_id"),
            "name": params.get("name") or params.get("title"),  # Handle both 'name' and 'title'
            "description": params.get("description", ""),
            "status": params.get("status", "active"),
            "metadata": json.dumps(params.get("metadata", {}))  # Serialize metadata as JSON
        }
        
        result = self.db_manager.create_research_topic(topic_data)
        self._invalidate_cache(f"topics_{params.get('project_id')}")
        
        if result:
            return {
                "topic_id": result.get("id"),
                "project_id": result.get("project_id"),
                "created_at": result.get("created_at"),
                "status": "created"
            }
        else:
            raise DatabaseError("Failed to create research topic", "create_research_topic")

    @handle_errors("database_agent_create_plan")
    async def _create_plan(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new research plan."""
        plan_data = {
            "topic_id": params.get("topic_id"),
            "name": params.get("name"),
            "description": params.get("description", ""),
            "steps": params.get("steps", []),
            "estimated_cost": params.get("estimated_cost", 0.0),
            "metadata": params.get("metadata", {})
        }
        
        plan_id = self.db_manager.create_research_plan(plan_data)
        self._invalidate_cache(f"plans_{params.get('topic_id')}")
        
        return {
            "plan_id": plan_id,
            "topic_id": params.get("topic_id"),
            "created_at": datetime.utcnow().isoformat(),
            "status": "created"
        }

    @handle_errors("database_agent_create_task")
    async def _create_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new task."""
        task_data = {
            "plan_id": params.get("plan_id"),
            "name": params.get("name"),
            "description": params.get("description", ""),
            "agent_type": params.get("agent_type"),
            "parameters": params.get("parameters", {}),
            "status": params.get("status", "pending"),
            "metadata": params.get("metadata", {})
        }
        
        task_id = self.db_manager.create_task(task_data)
        self._invalidate_cache(f"tasks_{params.get('plan_id')}")
        
        return {
            "task_id": task_id,
            "plan_id": params.get("plan_id"),
            "created_at": datetime.utcnow().isoformat(),
            "status": "created"
        }

    # READ Operations (with caching)
    async def _handle_get_operation(self, action_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle all get operations with caching support."""
        
        entity_id = params.get("id") or params.get("project_id") or params.get("topic_id") or params.get("plan_id") or params.get("task_id")
        if not entity_id:
            raise DatabaseError("Missing 'id' parameter for get operation", "database_agent_get")
            
        cache_key = f"{action_type}_{entity_id}"
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            logger.debug(f"Cache hit for {cache_key}")
            return self.cache[cache_key]
        
        # Fetch from database
        result = None
        if action_type == "get_project":
            result = self.db_manager.get_project(entity_id)
        elif action_type == "get_topic" or action_type == "get_research_topic":
            result = self.db_manager.get_research_topic(entity_id)
        elif action_type == "get_plan" or action_type == "get_research_plan":
            result = self.db_manager.get_research_plan(entity_id)
        elif action_type == "get_task":
            result = self.db_manager.get_task(entity_id)
        else:
            raise DatabaseError(f"Unsupported get operation: {action_type}", "database_agent_get")
        
        if result is None:
            raise DatabaseError(f"Entity not found: {entity_id}", "database_agent_get")
            
        # Cache the result
        self._cache_result(cache_key, result)
        return result

    # UPDATE Operations
    async def _handle_update_operation(self, action_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle all update operations with cache invalidation."""
        
        entity_id = params.get("id") or params.get("project_id") or params.get("topic_id") or params.get("plan_id") or params.get("task_id")
        if not entity_id:
            raise DatabaseError("Missing 'id' parameter for update operation", "database_agent_update")
        
        # Extract update data - either from 'data' parameter or from individual fields
        update_data = params.get("data", {})
        if not update_data:
            # If no 'data' parameter, extract update fields from the params directly
            excluded_keys = {"id", "project_id", "topic_id", "plan_id", "task_id"}
            update_data = {k: v for k, v in params.items() if k not in excluded_keys}
            
        if not update_data:
            raise DatabaseError("No update data provided", "database_agent_update")
        
        if action_type == "update_project":
            self.db_manager.update_project(entity_id, update_data)
            self._invalidate_cache(f"get_project_{entity_id}")
            self._invalidate_cache("projects")
        elif action_type == "update_topic" or action_type == "update_research_topic":
            self.db_manager.update_research_topic(entity_id, update_data)
            self._invalidate_cache(f"get_topic_{entity_id}")
        elif action_type == "update_plan" or action_type == "update_research_plan":
            self.db_manager.update_research_plan(entity_id, update_data)
            self._invalidate_cache(f"get_plan_{entity_id}")
        elif action_type == "update_task":
            self.db_manager.update_task(entity_id, update_data)
            self._invalidate_cache(f"get_task_{entity_id}")
        else:
            raise DatabaseError(f"Unsupported update operation: {action_type}", "database_agent_update")
        
        return {
            "id": entity_id,
            "updated_at": datetime.utcnow().isoformat(),
            "status": "updated"
        }

    # LIST Operations
    async def _handle_list_operation(self, action_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle all list operations with caching."""
        
        if action_type == "list_projects":
            cache_key = "projects"
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]
            
            results = self.db_manager.list_projects()
            response = {"projects": results}
            self._cache_result(cache_key, response)
            return response
        
        # Add other list operations as needed
        else:
            raise DatabaseError(f"Unsupported list operation: {action_type}", "database_agent_list")

    # DELETE Operations
    async def _handle_delete_operation(self, action_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle all delete operations with cache cleanup."""
        
        entity_id = params.get("id") or params.get("project_id") or params.get("topic_id") or params.get("plan_id") or params.get("task_id")
        if not entity_id:
            raise DatabaseError("Missing 'id' parameter for delete operation", "database_agent_delete")
        
        if action_type == "delete_project":
            self.db_manager.delete_project(entity_id)
            self._invalidate_cache(f"get_project_{entity_id}")
            self._invalidate_cache("projects")
        elif action_type == "delete_topic" or action_type == "delete_research_topic":
            self.db_manager.delete_research_topic(entity_id)
            self._invalidate_cache(f"get_topic_{entity_id}")
        elif action_type == "delete_plan" or action_type == "delete_research_plan":
            self.db_manager.delete_research_plan(entity_id)
            self._invalidate_cache(f"get_plan_{entity_id}")
        elif action_type == "delete_task":
            self.db_manager.delete_task(entity_id)
            self._invalidate_cache(f"get_task_{entity_id}")
        else:
            raise DatabaseError(f"Unsupported delete operation: {action_type}", "database_agent_delete")
        
        return {
            "id": entity_id,
            "deleted_at": datetime.utcnow().isoformat(),
            "status": "deleted"
        }

    # Cache Management
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is valid (not expired)."""
        if key not in self.cache:
            return False
        
        if key not in self.cache_timestamps:
            return False
        
        age = datetime.utcnow().timestamp() - self.cache_timestamps[key]
        return age < self.cache_ttl

    def _cache_result(self, key: str, result: Any):
        """Cache a result with timestamp."""
        self.cache[key] = result
        self.cache_timestamps[key] = datetime.utcnow().timestamp()

    def _invalidate_cache(self, pattern: Optional[str] = None):
        """Invalidate cache entries matching pattern."""
        if pattern is None:
            self.cache.clear()
            self.cache_timestamps.clear()
        else:
            keys_to_remove = [k for k in self.cache.keys() if pattern in k]
            for key in keys_to_remove:
                self.cache.pop(key, None)
                self.cache_timestamps.pop(key, None)

    # Health Check
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on database connections."""
        try:
            # Test database connectivity
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
            
            return {
                "status": "healthy",
                "database": "connected",
                "cache_size": len(self.cache),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
