"""Enhanced database operations with hierarchical research support."""

import json
import os
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import existing models
try:
    from ..utils.error_handler import DatabaseError, handle_errors
    from ..utils.id_utils import generate_timestamped_id, generate_uuid_id
except ImportError:
    # For direct execution or testing
    # Add the parent directory to the path
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    from src.utils.error_handler import DatabaseError, handle_errors
    from src.utils.id_utils import generate_timestamped_id, generate_uuid_id

# Import new hierarchical models
try:
    from ..models.hierarchical_data_models import (ResearchPlan, ResearchTopic,
                                                   Task)
except ImportError:
    try:
        from models.hierarchical_data_models import (ResearchPlan,
                                                     ResearchTopic, Task)
    except ImportError:
        # Fallback for development - these will be implemented
        ResearchTopic = None
        ResearchPlan = None
        Task = None


class HierarchicalDatabaseManager:
    """Enhanced database manager with hierarchical research support."""

    def __init__(self, db_path: Optional[str] = None):
        # Use environment variable for default path if none provided
        if db_path is None:
            data_path = os.getenv("EUNICE_DATA_PATH", "data")
            db_path = os.path.join(data_path, "eunice.db")

        self.db_path = db_path
        self._persistent_conn = None
        self.max_retries = 3

        # For in - memory databases, we need to keep a persistent connection
        if db_path == ":memory:":
            self._persistent_conn = sqlite3.connect(db_path)
            self._persistent_conn.row_factory = sqlite3.Row

        self.init_database()

    def __del__(self):
        """Clean up persistent connection."""
        if self._persistent_conn:
            try:
                self._persistent_conn.close()
            except Exception:
                pass  # Ignore errors during cleanup

    @contextmanager
    def get_connection(self):
        """Get a database connection with proper cleanup."""
        if self._persistent_conn:
            yield self._persistent_conn
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

    @handle_errors(context="database_initialization")
    def init_database(self) -> None:
        """Initialize the database with all required tables."""
        try:
            # Ensure the directory exists (unless it's in - memory)
            if self.db_path != ":memory:":
                db_dir = Path(self.db_path).parent
                db_dir.mkdir(parents=True, exist_ok=True)

            with self.get_connection() as conn:
                # Enable foreign key constraints
                conn.execute("PRAGMA foreign_keys = ON")

                # Create all tables with final schema
                self._create_all_tables(conn)

                conn.commit()

        except Exception as e:
            raise DatabaseError(
                "Failed to initialize database", f"Database initialization failed: {e}"
            )

    def _create_all_tables(self, conn: sqlite3.Connection) -> None:
        """Create all database tables with final schema - no migrations needed."""
        conn.executescript(
            """
            -- Projects table with all final columns
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                metadata TEXT,
                status TEXT DEFAULT 'active'
            );

            -- Research topics table
            CREATE TABLE IF NOT EXISTS research_topics (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
            );

            -- Research plans table
            CREATE TABLE IF NOT EXISTS research_plans (
                id TEXT PRIMARY KEY,
                topic_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                plan_type TEXT DEFAULT 'comprehensive',
                status TEXT DEFAULT 'draft',
                plan_approved BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                estimated_cost REAL DEFAULT 0.0,
                actual_cost REAL DEFAULT 0.0,
                plan_structure TEXT DEFAULT '{}',
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (topic_id) REFERENCES research_topics (id) ON DELETE CASCADE
            );

            -- Research tasks table with all final columns
            CREATE TABLE IF NOT EXISTS research_tasks (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                query TEXT NOT NULL,
                name TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                stage TEXT DEFAULT 'planning',
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                estimated_cost REAL DEFAULT 0.0,
                actual_cost REAL DEFAULT 0.0,
                cost_approved BOOLEAN DEFAULT 0,
                single_agent_mode BOOLEAN DEFAULT 0,
                research_mode TEXT DEFAULT 'comprehensive',
                max_results INTEGER DEFAULT 10,
                progress REAL DEFAULT 0.0,
                search_results TEXT,
                reasoning_output TEXT,
                execution_results TEXT,
                synthesis TEXT,
                metadata TEXT,
                plan_id TEXT,
                task_type TEXT DEFAULT 'research',
                task_order INTEGER DEFAULT 0,
                description TEXT DEFAULT '',
                FOREIGN KEY (project_id) REFERENCES projects (id),
                FOREIGN KEY (plan_id) REFERENCES research_plans (id)
            );

            -- Create all indexes
            CREATE INDEX IF NOT EXISTS idx_research_tasks_project_id ON research_tasks(project_id);
            CREATE INDEX IF NOT EXISTS idx_research_tasks_status ON research_tasks(status);
            CREATE INDEX IF NOT EXISTS idx_research_tasks_created_at ON research_tasks(created_at);
            CREATE INDEX IF NOT EXISTS idx_research_tasks_plan_id ON research_tasks(plan_id);
            CREATE INDEX IF NOT EXISTS idx_topics_project_id ON research_topics(project_id);
            CREATE INDEX IF NOT EXISTS idx_topics_status ON research_topics(status);
            CREATE INDEX IF NOT EXISTS idx_plans_topic_id ON research_plans(topic_id);
            CREATE INDEX IF NOT EXISTS idx_plans_status ON research_plans(status);
            CREATE INDEX IF NOT EXISTS idx_plans_plan_type ON research_plans(plan_type);
            CREATE INDEX IF NOT EXISTS idx_tasks_task_type ON research_tasks(task_type);
            CREATE INDEX IF NOT EXISTS idx_tasks_task_order ON research_tasks(task_order);
        """
        )

    # Research Topics Methods
    @handle_errors(context="create_research_topic")
    def create_research_topic(
        self, topic_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create a new research topic."""
        try:
            topic_id = topic_data.get("id", generate_timestamped_id("topic"))

            with self.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO research_topics
                    (id, project_id, name, description, status, created_at, updated_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        topic_id,
                        topic_data["project_id"],
                        topic_data["name"],
                        topic_data.get("description", ""),
                        topic_data.get("status", "active"),
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                        topic_data.get("metadata", "{}"),
                    ),
                )
                conn.commit()

                return self.get_research_topic(topic_id)

        except Exception as e:
            raise DatabaseError(
                "Failed to create research topic", f"Topic creation failed: {e}"
            )

    @handle_errors(context="get_research_topic")
    def get_research_topic(self, topic_id: str) -> Optional[Dict[str, Any]]:
        """Get a research topic by ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT t.*,
                           COUNT(DISTINCT p.id) as plans_count,
                           COUNT(DISTINCT rt.id) as tasks_count,
                           COALESCE(SUM(p.actual_cost), 0.0) as total_cost,
                           CASE
                               WHEN COUNT(DISTINCT p.id) = 0 THEN 0.0
                               ELSE CAST(COUNT(DISTINCT CASE WHEN p.status = 'completed'
                               THEN p.id END) AS FLOAT) / COUNT(DISTINCT p.id) * 100
                           END as completion_rate
                    FROM research_topics t
                    LEFT JOIN research_plans p ON t.id = p.topic_id
                    LEFT JOIN research_tasks rt ON p.id = rt.plan_id
                    WHERE t.id = ?
                    GROUP BY t.id
                """,
                    (topic_id,),
                )

                row = cursor.fetchone()
                if row:
                    topic = dict(row)
                    # Handle metadata parsing with double - encoded JSON
                    metadata_raw = topic.get("metadata", "{}")
                    try:
                        metadata = json.loads(metadata_raw)
                        # If metadata is a string (double - encoded JSON), parse it again
                        if isinstance(metadata, str):
                            metadata = json.loads(metadata)
                        topic["metadata"] = metadata
                    except (json.JSONDecodeError, TypeError):
                        topic["metadata"] = {}
                    return topic
                return None

        except Exception as e:
            raise DatabaseError(
                "Failed to get research topic", f"Topic retrieval failed: {e}"
            )

    @handle_errors(context="get_research_topics_by_project")
    def get_research_topics_by_project(
        self, project_id: str, status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all research topics for a project."""
        try:
            with self.get_connection() as conn:
                query = """
                    SELECT t.*,
                           COUNT(DISTINCT p.id) as plan_count,
                           COUNT(DISTINCT rt.id) as task_count
                    FROM research_topics t
                    LEFT JOIN research_plans p ON t.id = p.topic_id
                    LEFT JOIN research_tasks rt ON p.id = rt.plan_id
                    WHERE t.project_id = ?
                """
                params = [project_id]

                if status_filter:
                    query += " AND t.status = ?"
                    params.append(status_filter)

                query += " GROUP BY t.id ORDER BY t.created_at DESC"

                cursor = conn.execute(query, params)
                topics = []
                for row in cursor.fetchall():
                    topic = dict(row)
                    # Handle metadata parsing with double - encoded JSON
                    metadata_raw = topic.get("metadata", "{}")
                    try:
                        metadata = json.loads(metadata_raw)
                        # If metadata is a string (double - encoded JSON), parse it again
                        if isinstance(metadata, str):
                            metadata = json.loads(metadata)
                        topic["metadata"] = metadata
                    except (json.JSONDecodeError, TypeError):
                        topic["metadata"] = {}
                    topics.append(topic)

                return topics

        except Exception as e:
            raise DatabaseError(
                "Failed to get research topics", f"Topics retrieval failed: {e}"
            )

    # Research Plans Methods
    @handle_errors(context="create_research_plan")
    def create_research_plan(
        self, plan_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create a new research plan."""
        try:
            plan_id = plan_data.get("id", generate_timestamped_id("plan"))

            with self.get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO research_plans
                    (id, topic_id, name, description, plan_type, status, plan_approved, created_at, updated_at,
                     estimated_cost, actual_cost, plan_structure, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        plan_id,
                        plan_data["topic_id"],
                        plan_data["name"],
                        plan_data.get("description", ""),
                        plan_data.get("plan_type", "comprehensive"),
                        plan_data.get("status", "draft"),
                        plan_data.get("plan_approved", False),
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                        plan_data.get("estimated_cost", 0.0),
                        plan_data.get("actual_cost", 0.0),
                        plan_data.get("plan_structure", "{}"),
                        plan_data.get("metadata", "{}"),
                    ),
                )
                conn.commit()

                return self.get_research_plan(plan_id)

        except Exception as e:
            raise DatabaseError(
                "Failed to create research plan", f"Plan creation failed: {e}"
            )

    @handle_errors(context="get_research_plan")
    def get_research_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get a research plan by ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT p.*,
                           COUNT(DISTINCT rt.id) as tasks_count,
                           COUNT(CASE WHEN rt.status = 'completed' THEN 1 END) as completed_tasks,
                           AVG(CASE WHEN rt.progress IS NOT NULL THEN rt.progress ELSE 0 END) as progress
                    FROM research_plans p
                    LEFT JOIN research_tasks rt ON p.id = rt.plan_id
                    WHERE p.id = ?
                    GROUP BY p.id
                """,
                    (plan_id,),
                )

                row = cursor.fetchone()
                if row:
                    plan = dict(row)

                    # Handle plan_structure parsing
                    try:
                        plan_structure_raw = plan.get("plan_structure", "{}")
                        if isinstance(plan_structure_raw, str):
                            plan["plan_structure"] = json.loads(plan_structure_raw)
                        else:
                            plan["plan_structure"] = plan_structure_raw
                    except (json.JSONDecodeError, TypeError):
                        plan["plan_structure"] = {}

                    # Handle metadata parsing with double - encoded JSON
                    metadata_raw = plan.get("metadata", "{}")
                    try:
                        metadata = json.loads(metadata_raw)
                        # If metadata is a string (double - encoded JSON), parse it again
                        if isinstance(metadata, str):
                            metadata = json.loads(metadata)
                        plan["metadata"] = metadata
                    except (json.JSONDecodeError, TypeError):
                        plan["metadata"] = {}
                    return plan
                return None

        except Exception as e:
            raise DatabaseError(
                "Failed to get research plan", f"Plan retrieval failed: {e}"
            )

    @handle_errors(context="get_research_plans_by_topic")
    def get_research_plans_by_topic(
        self, topic_id: str, status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all research plans for a topic."""
        try:
            with self.get_connection() as conn:
                query = """
                    SELECT p.*,
                           COUNT(DISTINCT rt.id) as tasks_count,
                           COUNT(CASE WHEN rt.status = 'completed' THEN 1 END) as completed_tasks,
                           AVG(CASE WHEN rt.progress IS NOT NULL THEN rt.progress ELSE 0 END) as progress
                    FROM research_plans p
                    LEFT JOIN research_tasks rt ON p.id = rt.plan_id
                    WHERE p.topic_id = ?
                """
                params = [topic_id]

                if status_filter:
                    query += " AND p.status = ?"
                    params.append(status_filter)

                query += " GROUP BY p.id ORDER BY p.created_at DESC"

                cursor = conn.execute(query, params)
                plans = []
                for row in cursor.fetchall():
                    plan = dict(row)
                    plan["plan_structure"] = json.loads(
                        plan.get("plan_structure", "{}")
                    )
                    # Handle metadata parsing with double - encoded JSON
                    metadata_raw = plan.get("metadata", "{}")
                    try:
                        metadata = json.loads(metadata_raw)
                        # If metadata is a string (double - encoded JSON), parse it again
                        if isinstance(metadata, str):
                            metadata = json.loads(metadata)
                        plan["metadata"] = metadata
                    except (json.JSONDecodeError, TypeError):
                        plan["metadata"] = {}
                    plans.append(plan)

                return plans

        except Exception as e:
            raise DatabaseError(
                "Failed to get research plans", f"Plans retrieval failed: {e}"
            )

    # Enhanced Task Methods (renamed from research_tasks)
    @handle_errors(context="create_task")
    def create_task(self, task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new task."""
        try:
            task_id = task_data.get("id", generate_timestamped_id("task"))

            # Plan ID is optional - tasks can be created without plans initially
            plan_id = task_data.get("plan_id")
            project_id = task_data.get("project_id")

            if plan_id and not project_id:
                # Get project_id from the plan if not provided directly
                plan = self.get_research_plan(plan_id)
                if not plan:
                    raise Exception(f"Plan {plan_id} not found")

                # Get project_id through topic
                topic = self.get_research_topic(plan["topic_id"])
                if not topic:
                    raise Exception(f"Topic {plan['topic_id']} not found")

                project_id = topic["project_id"]

            if not project_id:
                raise Exception("project_id is required")

            with self.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO research_tasks
                    (id, project_id, plan_id, name, query, status, stage, created_at, updated_at,
                     task_type, task_order, estimated_cost, actual_cost, cost_approved,
                     single_agent_mode, research_mode, max_results, progress, search_results,
                     reasoning_output, execution_results, synthesis, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        task_id,
                        project_id,
                        plan_id,  # Can be None
                        task_data.get("name", ""),
                        task_data.get("query", ""),
                        task_data.get("status", "pending"),
                        task_data.get("stage", "planning"),
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                        task_data.get("task_type", "research"),
                        task_data.get("task_order", 0),
                        task_data.get("estimated_cost", 0.0),
                        task_data.get("actual_cost", 0.0),
                        task_data.get("cost_approved", False),
                        task_data.get("single_agent_mode", False),
                        task_data.get("research_mode", "comprehensive"),
                        task_data.get("max_results", 10),
                        task_data.get("progress", 0.0),
                        json.dumps(task_data.get("search_results", [])),
                        task_data.get("reasoning_output"),
                        json.dumps(task_data.get("execution_results", [])),
                        task_data.get("synthesis"),
                        task_data.get("metadata", "{}"),
                    ),
                )
                conn.commit()

                return self.get_task(task_id)

        except Exception as e:
            raise DatabaseError("Failed to create task", f"Task creation failed: {e}")

    @handle_errors(context="get_task")
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task by ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM research_tasks WHERE id = ?
                """,
                    (task_id,),
                )

                row = cursor.fetchone()
                if row:
                    task = dict(row)
                    # Parse JSON fields and ensure proper defaults
                    for field in ["search_results", "execution_results", "metadata"]:
                        if task.get(field):
                            try:
                                task[field] = json.loads(task[field])
                            except (json.JSONDecodeError, TypeError):
                                task[field] = (
                                    []
                                    if field in ["search_results", "execution_results"]
                                    else {}
                                )
                        else:
                            task[field] = (
                                []
                                if field in ["search_results", "execution_results"]
                                else {}
                            )

                    # Ensure required fields have proper defaults
                    task.setdefault("description", "")
                    task.setdefault("search_results", [])
                    task.setdefault("execution_results", [])
                    task.setdefault("reasoning_output", None)
                    task.setdefault("synthesis", None)

                    return task
                return None

        except Exception as e:
            raise DatabaseError("Failed to get task", f"Task retrieval failed: {e}")

    @handle_errors(context="get_tasks_by_plan")
    def get_tasks_by_plan(
        self,
        plan_id: str,
        status_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get all tasks for a plan."""
        try:
            with self.get_connection() as conn:
                query = "SELECT * FROM research_tasks WHERE plan_id = ?"
                params = [plan_id]

                if status_filter:
                    query += " AND status = ?"
                    params.append(status_filter)

                if type_filter:
                    query += " AND task_type = ?"
                    params.append(type_filter)

                query += " ORDER BY task_order ASC, created_at ASC"

                cursor = conn.execute(query, params)
                tasks = []
                for row in cursor.fetchall():
                    task = dict(row)
                    # Parse JSON fields
                    for field in ["search_results", "execution_results", "metadata"]:
                        if task.get(field):
                            try:
                                task[field] = json.loads(task[field])
                            except (json.JSONDecodeError, TypeError):
                                task[field] = []
                    tasks.append(task)

                return tasks

        except Exception as e:
            raise DatabaseError("Failed to get tasks", f"Tasks retrieval failed: {e}")

    # Hierarchical navigation methods
    @handle_errors(context="get_project_hierarchy")
    def get_project_hierarchy(self, project_id: str) -> Dict[str, Any]:
        """Get complete hierarchy for a project."""
        try:
            project = self.get_project(project_id)
            if not project:
                return {}

            topics = self.get_research_topics_by_project(project_id)

            for topic in topics:
                topic["plans"] = self.get_research_plans_by_topic(topic["id"])

                for plan in topic["plans"]:
                    plan["tasks"] = self.get_tasks_by_plan(plan["id"])

            return {"project": project, "topics": topics}

        except Exception as e:
            raise DatabaseError(
                "Failed to get project hierarchy", f"Hierarchy retrieval failed: {e}"
            )

    # Delete methods
    @handle_errors(context="delete_research_topic")
    def delete_research_topic(self, topic_id: str) -> bool:
        """Delete a research topic and all its plans and tasks."""
        try:
            with self.get_connection() as conn:
                # Check if topic exists
                cursor = conn.execute(
                    "SELECT id FROM research_topics WHERE id = ?", (topic_id,)
                )
                if not cursor.fetchone():
                    return False

                # Delete all tasks for plans in this topic
                conn.execute(
                    """
                    DELETE FROM research_tasks
                    WHERE plan_id IN (
                        SELECT id FROM research_plans WHERE topic_id = ?
                    )
                """,
                    (topic_id,),
                )

                # Delete all plans for this topic
                conn.execute(
                    "DELETE FROM research_plans WHERE topic_id = ?", (topic_id,)
                )

                # Delete the topic
                conn.execute("DELETE FROM research_topics WHERE id = ?", (topic_id,))

                conn.commit()
                return True

        except Exception as e:
            raise DatabaseError(
                "Failed to delete research topic", f"Topic deletion failed: {e}"
            )

    @handle_errors(context="update_research_plan")
    def update_research_plan(
        self, plan_id: str, update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a research plan."""
        try:
            # Check if plan exists
            plan = self.get_research_plan(plan_id)
            if not plan:
                return None

            # Build update query dynamically
            update_fields = []
            update_values = []

            for field, value in update_data.items():
                if field in [
                    "name",
                    "description",
                    "plan_type",
                    "status",
                    "plan_approved",
                ]:
                    update_fields.append(f"{field} = ?")
                    update_values.append(value)
                elif field in ["plan_structure", "metadata"]:
                    update_fields.append(f"{field} = ?")
                    update_values.append(json.dumps(value))

            if not update_fields:
                return plan  # No updates to apply

            update_values.append(datetime.now().isoformat())  # updated_at
            update_values.append(plan_id)  # WHERE clause

            update_query = f"""
                UPDATE research_plans
                SET {', '.join(update_fields)}, updated_at = ?
                WHERE id = ?
            """

            with self.get_connection() as conn:
                conn.execute(update_query, update_values)
                conn.commit()

            # Return updated plan
            return self.get_research_plan(plan_id)

        except Exception as e:
            raise DatabaseError(
                "Failed to update research plan", f"Plan update failed: {e}"
            )

    @handle_errors(context="delete_research_plan")
    def delete_research_plan(self, plan_id: str) -> bool:
        """Delete a research plan and all its tasks."""
        try:
            with self.get_connection() as conn:
                # Check if plan exists
                cursor = conn.execute(
                    "SELECT id FROM research_plans WHERE id = ?", (plan_id,)
                )
                if not cursor.fetchone():
                    return False

                # Delete all tasks for this plan
                conn.execute("DELETE FROM research_tasks WHERE plan_id = ?", (plan_id,))

                # Delete the plan
                conn.execute("DELETE FROM research_plans WHERE id = ?", (plan_id,))

                conn.commit()
                return True

        except Exception as e:
            raise DatabaseError(
                "Failed to delete research plan", f"Plan deletion failed: {e}"
            )

    @handle_errors(context="delete_task")
    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        try:
            with self.get_connection() as conn:
                # Check if task exists
                cursor = conn.execute(
                    "SELECT id FROM research_tasks WHERE id = ?", (task_id,)
                )
                if not cursor.fetchone():
                    return False

                # Delete the task
                conn.execute("DELETE FROM research_tasks WHERE id = ?", (task_id,))

                conn.commit()
                return True

        except Exception as e:
            raise DatabaseError("Failed to delete task", f"Task deletion failed: {e}")

    # Research task compatibility methods
    def get_research_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a research task by ID."""
        return self.get_task(task_id)

    def update_research_task(
        self, task_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a research task."""
        # Extract task ID from the data
        task_id = task_data.get("id")
        if not task_id:
            return None

        try:
            with self.get_connection() as conn:
                # Build update query dynamically based on available fields
                update_fields = []
                update_values = []

                # Map common fields that might be updated
                field_mapping = {
                    "status": "status",
                    "stage": "stage",
                    "progress": "progress",
                    "actual_cost": "actual_cost",
                    "search_results": "search_results",
                    "reasoning_output": "reasoning_output",
                    "execution_results": "execution_results",
                    "synthesis": "synthesis",
                    "metadata": "metadata",
                }

                for field, column in field_mapping.items():
                    if field in task_data:
                        update_fields.append(f"{column} = ?")
                        value = task_data[field]
                        # Convert lists / dicts to JSON strings
                        if isinstance(value, (list, dict)):
                            value = json.dumps(value)
                        update_values.append(value)

                if not update_fields:
                    return task_data  # No updates to apply

                # Add updated_at timestamp
                update_fields.append("updated_at = ?")
                update_values.append(datetime.now().isoformat())
                update_values.append(task_id)  # WHERE clause

                update_query = f"""
                    UPDATE research_tasks
                    SET {', '.join(update_fields)}
                    WHERE id = ?
                """

                conn.execute(update_query, update_values)
                conn.commit()

                # Return updated task
                return self.get_task(task_id)

        except Exception as e:
            print(f"Failed to update research task: {e}")
            return None

    @handle_errors(context="create_research_task_with_hierarchy")
    def create_research_task_with_hierarchy(
        self, task_data: Dict[str, Any], auto_create_topic: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Create a research task with proper hierarchical structure (topic → plan → task).

        Args:
            task_data: Task data including project_id, query, name, etc.
            auto_create_topic: Whether to automatically create a topic if none exists

        Returns:
            Created task data with hierarchy in place
        """
        try:
            project_id = task_data.get("project_id")
            if not project_id:
                raise Exception("project_id is required for hierarchical task creation")

            # Step 1: Find or create a research topic
            topic_id = None

            # Look for existing topics in this project
            existing_topics = self.get_research_topics_by_project(project_id)

            if existing_topics:
                # Use the first active topic, or create a new one if all are inactive
                active_topics = [
                    t for t in existing_topics if t.get("status") == "active"
                ]
                if active_topics:
                    topic_id = active_topics[0]["id"]
                else:
                    topic_id = existing_topics[0]["id"]  # Use any existing topic

            if not topic_id and auto_create_topic:
                # Create a new topic based on the research query
                query = task_data.get("query", "")
                topic_name = self._generate_topic_name_from_query(query)

                topic_data = {
                    "project_id": project_id,
                    "name": topic_name,
                    "description": (
                        f"Research topic for: {query[:100]}..."
                        if len(query) > 100
                        else f"Research topic for: {query}"
                    ),
                    "status": "active",
                }

                created_topic = self.create_research_topic(topic_data)
                if not created_topic:
                    raise Exception("Failed to create research topic")
                topic_id = created_topic["id"]

            if not topic_id:
                raise Exception("No topic available and auto_create_topic is disabled")

            # Step 2: Create a research plan
            plan_id = generate_uuid_id("plan")  # Use UUID for better uniqueness
            plan_data = {
                "id": plan_id,
                "topic_id": topic_id,
                "name": f"Plan: {task_data.get('name', task_data.get('query', 'Research Task'))}",
                "description": f"Research plan for: {task_data.get('query', 'N / A')}",
                "plan_type": "comprehensive",
                "status": "active",
                "plan_structure": {
                    "query": task_data.get("query"),
                    "research_mode": task_data.get("research_mode", "comprehensive"),
                    "max_results": task_data.get("max_results", 10),
                },
                "metadata": {
                    "created_from_task": True,
                    "task_name": task_data.get("name"),
                },
            }

            created_plan = self.create_research_plan(plan_data)
            if not created_plan:
                raise Exception("Failed to create research plan")

            # Step 3: Create the research task linked to the plan
            enhanced_task_data = task_data.copy()
            enhanced_task_data["plan_id"] = created_plan["id"]

            created_task = self.create_task(enhanced_task_data)
            if not created_task:
                raise Exception("Failed to create research task")

            return created_task

        except Exception as e:
            raise DatabaseError(
                "Failed to create research task with hierarchy",
                f"Hierarchical task creation failed: {e}",
            )

    def _generate_topic_name_from_query(self, query: str) -> str:
        """Generate a meaningful topic name from a research query."""
        if not query:
            return "General Research"

        # Extract key terms from the query
        words = query.split()
        if len(words) <= 3:
            return query.title()

        # Take the first few significant words
        significant_words = []
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "how",
            "what",
            "why",
            "when",
            "where",
            "who",
        }

        for word in words[:6]:  # Look at first 6 words
            clean_word = word.strip('.,!?;:"()[]').lower()
            if clean_word not in stop_words and len(clean_word) > 2:
                significant_words.append(word.capitalize())
            if len(significant_words) >= 3:
                break

        if significant_words:
            topic_name = " ".join(significant_words)
            return topic_name if len(topic_name) <= 50 else topic_name[:47] + "..."

        return "Research Topic"

    # Project management methods
    def list_projects(self) -> List[Dict[str, Any]]:
        """List all projects."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM projects ORDER BY created_at DESC
                """
                )
                projects = []
                for row in cursor.fetchall():
                    project = dict(row)
                    projects.append(project)
                return projects
        except Exception as e:
            print(f"Failed to list projects: {e}")
            return []

    def create_project(self, project_data) -> Optional[Dict[str, Any]]:
        """Create a new project."""
        try:
            # Handle both dict and object input
            if hasattr(project_data, "__dict__"):
                # Convert object to dict
                data = {
                    "id": getattr(project_data, "id", generate_timestamped_id("proj")),
                    "name": project_data.name,
                    "description": getattr(project_data, "description", ""),
                    "created_at": (
                        project_data.created_at.isoformat()
                        if hasattr(project_data, "created_at")
                        and hasattr(project_data.created_at, "isoformat")
                        else datetime.now().isoformat()
                    ),
                    "updated_at": (
                        project_data.updated_at.isoformat()
                        if hasattr(project_data, "updated_at")
                        and hasattr(project_data.updated_at, "isoformat")
                        else datetime.now().isoformat()
                    ),
                }
            else:
                # Handle dict input - generate missing fields
                data = project_data.copy()
                if "id" not in data:
                    data["id"] = generate_timestamped_id("proj")
                if "created_at" not in data:
                    data["created_at"] = datetime.now().isoformat()
                if "updated_at" not in data:
                    data["updated_at"] = datetime.now().isoformat()
                if "description" not in data:
                    data["description"] = ""

            with self.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO projects (id, name, description, status, created_at, updated_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        data["id"],
                        data["name"],
                        data["description"],
                        data.get("status", "active"),
                        data["created_at"],
                        data["updated_at"],
                        data.get("metadata", "{}"),
                    ),
                )
                conn.commit()

                # Return the created project by fetching it back (this will handle JSON conversion)
                return self.get_project(data["id"])
        except Exception as e:
            print(f"Failed to create project: {e}")
            return None

    def delete_project(self, project_id: str) -> bool:
        """Delete a project."""
        try:
            with self.get_connection() as conn:
                conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
                conn.commit()
                return True
        except Exception as e:
            print(f"Failed to delete project: {e}")
            return False

    def get_research_tasks_by_project(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all research tasks for a project."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM research_tasks
                    WHERE project_id = ?
                    ORDER BY created_at DESC
                """,
                    (project_id,),
                )
                tasks = []
                for row in cursor.fetchall():
                    task = dict(row)
                    # Parse JSON fields
                    for field in ["search_results", "execution_results", "metadata"]:
                        if task.get(field):
                            try:
                                task[field] = json.loads(task[field])
                            except (json.JSONDecodeError, TypeError):
                                task[field] = (
                                    []
                                    if field in ["search_results", "execution_results"]
                                    else {}
                                )
                        else:
                            task[field] = (
                                []
                                if field in ["search_results", "execution_results"]
                                else {}
                            )
                    tasks.append(task)
                return tasks
        except Exception as e:
            print(f"Failed to get research tasks by project: {e}")
            return []

    def get_research_task_count_by_project(self, project_id: str) -> int:
        """Get count of research tasks for a project."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) FROM research_tasks WHERE project_id = ?
                """,
                    (project_id,),
                )
                return cursor.fetchone()[0]
        except Exception as e:
            print(f"Failed to get research task count: {e}")
            return 0

    def list_research_tasks(
        self,
        project_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List research tasks with filters."""
        try:
            query = "SELECT * FROM research_tasks WHERE 1=1"
            params = []

            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)

            if status_filter:
                query += " AND status = ?"
                params.append(status_filter)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                tasks = []
                for row in cursor.fetchall():
                    task = dict(row)
                    # Parse JSON fields
                    for field in ["search_results", "execution_results", "metadata"]:
                        if task.get(field):
                            try:
                                task[field] = json.loads(task[field])
                            except (json.JSONDecodeError, TypeError):
                                task[field] = (
                                    []
                                    if field in ["search_results", "execution_results"]
                                    else {}
                                )
                        else:
                            task[field] = (
                                []
                                if field in ["search_results", "execution_results"]
                                else {}
                            )
                    tasks.append(task)
                return tasks
        except Exception as e:
            print(f"Failed to list research tasks: {e}")
            return []

    def create_research_task(self, task_data) -> Optional[Dict[str, Any]]:
        """Create a research task."""
        try:
            # Handle both dict and object input
            if hasattr(task_data, "__dict__"):
                # Convert ResearchTask object to dict
                data = {
                    "id": task_data.id,
                    "project_id": task_data.project_id,
                    "query": task_data.query,
                    "name": task_data.name,
                    "status": task_data.status,
                    "stage": task_data.stage,
                    "created_at": (
                        task_data.created_at.isoformat()
                        if hasattr(task_data.created_at, "isoformat")
                        else str(task_data.created_at)
                    ),
                    "updated_at": (
                        task_data.updated_at.isoformat()
                        if hasattr(task_data.updated_at, "isoformat")
                        else str(task_data.updated_at)
                    ),
                    "estimated_cost": task_data.estimated_cost,
                    "actual_cost": task_data.actual_cost,
                    "cost_approved": task_data.cost_approved,
                    "single_agent_mode": task_data.single_agent_mode,
                    "research_mode": task_data.research_mode,
                    "max_results": task_data.max_results,
                    "progress": task_data.progress,
                    "search_results": json.dumps(task_data.search_results),
                    "reasoning_output": task_data.reasoning_output,
                    "execution_results": json.dumps(task_data.execution_results),
                    "synthesis": task_data.synthesis,
                    "metadata": json.dumps(task_data.metadata),
                }
            else:
                data = task_data.copy()
                # Ensure JSON fields are strings
                for field in ["search_results", "execution_results", "metadata"]:
                    if field in data and not isinstance(data[field], str):
                        data[field] = json.dumps(data[field])

            with self.get_connection() as conn:
                # Use INSERT OR IGNORE to prevent duplicate creation
                conn.execute(
                    """
                    INSERT OR IGNORE INTO research_tasks
                    (id, project_id, query, name, status, stage,
                     created_at, updated_at, estimated_cost, actual_cost, cost_approved,
                     single_agent_mode, research_mode, max_results, progress,
                     search_results, reasoning_output, execution_results, synthesis, metadata,
                     plan_id, task_type, task_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        data["id"],
                        data["project_id"],
                        data["query"],
                        data["name"],
                        data["status"],
                        data["stage"],
                        data["created_at"],
                        data["updated_at"],
                        data["estimated_cost"],
                        data["actual_cost"],
                        data["cost_approved"],
                        data["single_agent_mode"],
                        data["research_mode"],
                        data["max_results"],
                        data["progress"],
                        data.get("search_results", "[]"),
                        data.get("reasoning_output"),
                        data.get("execution_results", "[]"),
                        data.get("synthesis"),
                        data.get("metadata", "{}"),
                        data.get("plan_id"),
                        data.get("task_type", "research"),
                        data.get("task_order", 0),
                    ),
                )
                conn.commit()
                return data
        except Exception as e:
            print(f"Failed to create research task: {e}")
            return None

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get a project by ID."""
        try:
            with self.get_connection() as conn:
                result = conn.execute(
                    "SELECT * FROM projects WHERE id = ?", (project_id,)
                ).fetchone()

                if result:
                    data = dict(result)
                    data["metadata"] = json.loads(data.get("metadata", "{}"))

                    # Add computed fields
                    stats = self.get_project_stats(project_id)
                    if stats:
                        data.update(stats)

                    return data
                return None

        except Exception as e:
            print(f"Failed to get project: {e}")
            return None

    def get_projects(
        self, status_filter: Optional[str] = None, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all projects with optional filters."""
        try:
            with self.get_connection() as conn:
                query = "SELECT * FROM projects"
                params = []

                if status_filter:
                    query += " WHERE status = ?"
                    params.append(status_filter)

                query += " ORDER BY updated_at DESC"

                if limit:
                    query += " LIMIT ?"
                    params.append(limit)

                results = conn.execute(query, params).fetchall()

                projects = []
                for result in results:
                    data = dict(result)
                    data["metadata"] = json.loads(data.get("metadata", "{}"))

                    # Add computed fields
                    stats = self.get_project_stats(data["id"])
                    if stats:
                        data.update(stats)

                    projects.append(data)

                return projects

        except Exception as e:
            print(f"Failed to get projects: {e}")
            return []

    def update_project(
        self, project_id: str, update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a project."""
        try:
            with self.get_connection() as conn:
                # Build SET clause dynamically
                set_clauses = []
                params = []

                for key, value in update_data.items():
                    if key == "metadata":
                        set_clauses.append("metadata = ?")
                        params.append(json.dumps(value))
                    else:
                        set_clauses.append(f"{key} = ?")
                        params.append(value)

                # Always update the timestamp
                set_clauses.append("updated_at = ?")
                params.append(datetime.now().isoformat())

                params.append(project_id)

                query = f"UPDATE projects SET {', '.join(set_clauses)} WHERE id = ?"
                conn.execute(query, params)
                conn.commit()

                return self.get_project(project_id)

        except Exception as e:
            print(f"Failed to update project: {e}")
            return None

    def update_research_topic(
        self, topic_id: str, update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a research topic."""
        try:
            with self.get_connection() as conn:
                # Build SET clause dynamically
                set_clauses = []
                params = []

                for key, value in update_data.items():
                    if key == "metadata":
                        set_clauses.append("metadata = ?")
                        params.append(json.dumps(value))
                    else:
                        set_clauses.append(f"{key} = ?")
                        params.append(value)

                # Always update the timestamp
                set_clauses.append("updated_at = ?")
                params.append(datetime.now().isoformat())

                params.append(topic_id)

                query = (
                    f"UPDATE research_topics SET {', '.join(set_clauses)} WHERE id = ?"
                )
                conn.execute(query, params)
                conn.commit()

                return self.get_research_topic(topic_id)

        except Exception as e:
            print(f"Failed to update research topic: {e}")
            return None

    def update_task(
        self, task_id: str, update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a task."""
        try:
            with self.get_connection() as conn:
                # Build SET clause dynamically
                set_clauses = []
                params = []

                for key, value in update_data.items():
                    if key in ["metadata", "search_results", "execution_results"]:
                        set_clauses.append(f"{key} = ?")
                        params.append(json.dumps(value) if value else "[]")
                    else:
                        set_clauses.append(f"{key} = ?")
                        params.append(value)

                # Always update the timestamp
                set_clauses.append("updated_at = ?")
                params.append(datetime.now().isoformat())

                params.append(task_id)

                query = (
                    f"UPDATE research_tasks SET {', '.join(set_clauses)} WHERE id = ?"
                )
                conn.execute(query, params)
                conn.commit()

                return self.get_task(task_id)

        except Exception as e:
            print(f"Failed to update task: {e}")
            return None

    def get_project_stats(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project statistics."""
        try:
            with self.get_connection() as conn:
                # Count topics
                topics_count = conn.execute(
                    "SELECT COUNT(*) FROM research_topics WHERE project_id = ?",
                    (project_id,),
                ).fetchone()[0]

                # Count plans
                plans_count = conn.execute(
                    """SELECT COUNT(*) FROM research_plans rp
                       JOIN research_topics rt ON rp.topic_id = rt.id
                       WHERE rt.project_id = ?""",
                    (project_id,),
                ).fetchone()[0]

                # Count tasks
                tasks_count = conn.execute(
                    """SELECT COUNT(*) FROM research_tasks rt2
                       JOIN research_plans rp ON rt2.plan_id = rp.id
                       JOIN research_topics rt ON rp.topic_id = rt.id
                       WHERE rt.project_id = ?""",
                    (project_id,),
                ).fetchone()[0]

                # Calculate total cost
                total_cost_result = conn.execute(
                    """SELECT SUM(rt2.actual_cost) FROM research_tasks rt2
                       JOIN research_plans rp ON rt2.plan_id = rp.id
                       JOIN research_topics rt ON rp.topic_id = rt.id
                       WHERE rt.project_id = ?""",
                    (project_id,),
                ).fetchone()

                total_cost = total_cost_result[0] if total_cost_result[0] else 0.0

                # Calculate completion rate
                completed_tasks = conn.execute(
                    """SELECT COUNT(*) FROM research_tasks rt2
                       JOIN research_plans rp ON rt2.plan_id = rp.id
                       JOIN research_topics rt ON rp.topic_id = rt.id
                       WHERE rt.project_id = ? AND rt2.status = 'completed'""",
                    (project_id,),
                ).fetchone()[0]

                completion_rate = (
                    (completed_tasks / tasks_count * 100) if tasks_count > 0 else 0.0
                )

                return {
                    "topics_count": topics_count,
                    "plans_count": plans_count,
                    "tasks_count": tasks_count,
                    "total_cost": total_cost,
                    "completion_rate": completion_rate,
                }

        except Exception as e:
            print(f"Failed to get project stats: {e}")
            return None

    def get_topic_stats(self, topic_id: str) -> Optional[Dict[str, Any]]:
        """Get topic statistics."""
        try:
            with self.get_connection() as conn:
                # Count plans
                plans_count = conn.execute(
                    "SELECT COUNT(*) FROM research_plans WHERE topic_id = ?",
                    (topic_id,),
                ).fetchone()[0]

                # Count tasks
                tasks_count = conn.execute(
                    """SELECT COUNT(*) FROM research_tasks rt
                       JOIN research_plans rp ON rt.plan_id = rp.id
                       WHERE rp.topic_id = ?""",
                    (topic_id,),
                ).fetchone()[0]

                # Calculate total cost
                total_cost_result = conn.execute(
                    """SELECT SUM(actual_cost) FROM research_tasks rt
                       JOIN research_plans rp ON rt.plan_id = rp.id
                       WHERE rp.topic_id = ?""",
                    (topic_id,),
                ).fetchone()

                total_cost = total_cost_result[0] if total_cost_result[0] else 0.0

                # Calculate completion rate
                completed_tasks = conn.execute(
                    """SELECT COUNT(*) FROM research_tasks rt
                       JOIN research_plans rp ON rt.plan_id = rp.id
                       WHERE rp.topic_id = ? AND rt.status = 'completed'""",
                    (topic_id,),
                ).fetchone()[0]

                completion_rate = (
                    (completed_tasks / tasks_count * 100) if tasks_count > 0 else 0.0
                )

                return {
                    "plans_count": plans_count,
                    "tasks_count": tasks_count,
                    "total_cost": total_cost,
                    "completion_rate": completion_rate,
                }

        except Exception as e:
            print(f"Failed to get topic stats: {e}")
            return None

    def get_plan_stats(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get plan statistics."""
        try:
            with self.get_connection() as conn:
                # Count tasks
                tasks_count = conn.execute(
                    "SELECT COUNT(*) FROM research_tasks WHERE plan_id = ?", (plan_id,)
                ).fetchone()[0]

                # Count completed tasks
                completed_tasks = conn.execute(
                    "SELECT COUNT(*) FROM research_tasks WHERE plan_id = ? AND status = 'completed'",
                    (plan_id,),
                ).fetchone()[0]

                # Calculate total cost
                total_cost_result = conn.execute(
                    "SELECT SUM(actual_cost) FROM research_tasks WHERE plan_id = ?",
                    (plan_id,),
                ).fetchone()

                total_cost = total_cost_result[0] if total_cost_result[0] else 0.0

                # Calculate progress
                progress = (
                    (completed_tasks / tasks_count * 100) if tasks_count > 0 else 0.0
                )

                return {
                    "tasks_count": tasks_count,
                    "completed_tasks": completed_tasks,
                    "total_cost": total_cost,
                    "progress": progress,
                }

        except Exception as e:
            print(f"Failed to get plan stats: {e}")
            return None

    def search_project_hierarchy(
        self,
        project_id: str,
        query: str,
        entity_types: Optional[List[str]] = None,
        status_filters: Optional[List[str]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Search across project hierarchy."""
        results = {"topics": [], "plans": [], "tasks": []}

        try:
            with self.get_connection() as conn:
                # Search topics
                if not entity_types or "topic" in entity_types:
                    topic_query = """
                        SELECT * FROM research_topics
                        WHERE project_id = ? AND (name LIKE ? OR description LIKE ?)
                    """
                    params = [project_id, f"%{query}%", f"%{query}%"]

                    if status_filters:
                        topic_query += (
                            f" AND status IN ({','.join(['?'] * len(status_filters))})"
                        )
                        params.extend(status_filters)

                    topic_results = conn.execute(topic_query, params).fetchall()
                    for result in topic_results:
                        data = dict(result)
                        data["metadata"] = json.loads(data.get("metadata", "{}"))
                        results["topics"].append(data)

                # Search plans
                if not entity_types or "plan" in entity_types:
                    plan_query = """
                        SELECT rp.* FROM research_plans rp
                        JOIN research_topics rt ON rp.topic_id = rt.id
                        WHERE rt.project_id = ? AND (rp.name LIKE ? OR rp.description LIKE ?)
                    """
                    params = [project_id, f"%{query}%", f"%{query}%"]

                    if status_filters:
                        plan_query += f" AND rp.status IN ({','.join(['?'] * len(status_filters))})"
                        params.extend(status_filters)

                    plan_results = conn.execute(plan_query, params).fetchall()
                    for result in plan_results:
                        data = dict(result)
                        data["metadata"] = json.loads(data.get("metadata", "{}"))
                        data["plan_structure"] = json.loads(
                            data.get("plan_structure", "{}")
                        )
                        results["plans"].append(data)

                # Search tasks
                if not entity_types or "task" in entity_types:
                    task_query = """
                        SELECT rt2.* FROM research_tasks rt2
                        JOIN research_plans rp ON rt2.plan_id = rp.id
                        JOIN research_topics rt ON rp.topic_id = rt.id
                        WHERE rt.project_id = ? AND (rt2.name LIKE ? OR rt2.description LIKE ? OR rt2.query LIKE ?)
                    """
                    params = [project_id, f"%{query}%", f"%{query}%", f"%{query}%"]

                    if status_filters:
                        task_query += f" AND rt2.status IN ({','.join(['?'] * len(status_filters))})"
                        params.extend(status_filters)

                    task_results = conn.execute(task_query, params).fetchall()
                    for result in task_results:
                        data = dict(result)
                        data["metadata"] = json.loads(data.get("metadata", "{}"))
                        data["search_results"] = json.loads(
                            data.get("search_results", "[]")
                        )
                        data["execution_results"] = json.loads(
                            data.get("execution_results", "[]")
                        )
                        results["tasks"].append(data)

                return results

        except Exception as e:
            print(f"Failed to search project hierarchy: {e}")
            return results
