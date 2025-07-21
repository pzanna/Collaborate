"""Enhanced database operations with hierarchical research support."""

import sqlite3
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

# Import existing models
try:
    from ..models.data_models import Project, Conversation, Message, ConversationSession, ResearchTask
    from ..utils.error_handler import handle_errors, DatabaseError, ValidationError, safe_execute
    from ..utils.id_utils import generate_timestamped_id
except ImportError:
    # For direct execution or testing
    import sys
    from pathlib import Path
    
    # Add the parent directory to the path
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    from src.models.data_models import Project, Conversation, Message, ConversationSession, ResearchTask
    from src.utils.error_handler import handle_errors, DatabaseError, ValidationError, safe_execute
    from src.utils.id_utils import generate_timestamped_id

# Import new hierarchical models
try:
    from ..models.hierarchical_data_models import (
        ResearchTopic, ResearchPlan, Task,
        ResearchTopicRequest, ResearchPlanRequest, TaskRequest
    )
except ImportError:
    try:
        from models.hierarchical_data_models import (
            ResearchTopic, ResearchPlan, Task,
            ResearchTopicRequest, ResearchPlanRequest, TaskRequest
        )
    except ImportError:
        # Fallback for development - these will be implemented
        ResearchTopic = None
        ResearchPlan = None
        Task = None


class HierarchicalDatabaseManager:
    """Enhanced database manager with hierarchical research support."""
    
    def __init__(self, db_path: str = "data/eunice.db"):
        self.db_path = db_path
        self._persistent_conn = None
        self.max_retries = 3
        
        # For in-memory databases, we need to keep a persistent connection
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
            # Ensure the directory exists (unless it's in-memory)
            if self.db_path != ":memory:":
                db_dir = Path(self.db_path).parent
                db_dir.mkdir(parents=True, exist_ok=True)
            
            with self.get_connection() as conn:
                # Enable foreign key constraints
                conn.execute("PRAGMA foreign_keys = ON")
                
                # Create original tables
                self._create_original_tables(conn)
                
                # Create hierarchical tables
                self._create_hierarchical_tables(conn)
                
                conn.commit()
                
        except Exception as e:
            raise DatabaseError("Failed to initialize database", f"Database initialization failed: {e}")
    
    def _create_original_tables(self, conn: sqlite3.Connection) -> None:
        """Create the original database tables."""
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                metadata TEXT
            );
            
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                title TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                participants TEXT,
                status TEXT DEFAULT 'active',
                metadata TEXT,
                FOREIGN KEY (project_id) REFERENCES projects (id)
            );
            
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                participant TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP,
                message_type TEXT DEFAULT 'text',
                metadata TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id)
            );
            
            CREATE TABLE IF NOT EXISTS research_tasks (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                conversation_id TEXT,
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
                FOREIGN KEY (project_id) REFERENCES projects (id),
                FOREIGN KEY (conversation_id) REFERENCES conversations (id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_conversations_project_id ON conversations(project_id);
            CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
            CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
            CREATE INDEX IF NOT EXISTS idx_research_tasks_project_id ON research_tasks(project_id);
            CREATE INDEX IF NOT EXISTS idx_research_tasks_conversation_id ON research_tasks(conversation_id);
            CREATE INDEX IF NOT EXISTS idx_research_tasks_status ON research_tasks(status);
            CREATE INDEX IF NOT EXISTS idx_research_tasks_created_at ON research_tasks(created_at);
        """)
    
    def _create_hierarchical_tables(self, conn: sqlite3.Connection) -> None:
        """Create the new hierarchical research tables."""
        conn.executescript("""
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
            
            CREATE TABLE IF NOT EXISTS research_plans (
                id TEXT PRIMARY KEY,
                topic_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                plan_type TEXT DEFAULT 'comprehensive',
                status TEXT DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                estimated_cost REAL DEFAULT 0.0,
                actual_cost REAL DEFAULT 0.0,
                plan_structure TEXT DEFAULT '{}',
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (topic_id) REFERENCES research_topics (id) ON DELETE CASCADE
            );
            
            CREATE INDEX IF NOT EXISTS idx_topics_project_id ON research_topics(project_id);
            CREATE INDEX IF NOT EXISTS idx_topics_status ON research_topics(status);
            CREATE INDEX IF NOT EXISTS idx_plans_topic_id ON research_plans(topic_id);
            CREATE INDEX IF NOT EXISTS idx_plans_status ON research_plans(status);
            CREATE INDEX IF NOT EXISTS idx_plans_plan_type ON research_plans(plan_type);
            CREATE INDEX IF NOT EXISTS idx_tasks_plan_id ON research_tasks(plan_id);
            CREATE INDEX IF NOT EXISTS idx_tasks_task_type ON research_tasks(task_type);
            CREATE INDEX IF NOT EXISTS idx_tasks_task_order ON research_tasks(task_order);
        """)
    
    # Research Topics Methods
    @handle_errors(context="create_research_topic")
    def create_research_topic(self, topic_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new research topic."""
        try:
            topic_id = topic_data.get('id', generate_timestamped_id('topic'))
            
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO research_topics 
                    (id, project_id, name, description, status, created_at, updated_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    topic_id,
                    topic_data['project_id'],
                    topic_data['name'],
                    topic_data.get('description', ''),
                    topic_data.get('status', 'active'),
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    json.dumps(topic_data.get('metadata', {}))
                ))
                conn.commit()
                
                return self.get_research_topic(topic_id)
                
        except Exception as e:
            raise DatabaseError("Failed to create research topic", f"Topic creation failed: {e}")
    
    @handle_errors(context="get_research_topic")
    def get_research_topic(self, topic_id: str) -> Optional[Dict[str, Any]]:
        """Get a research topic by ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT t.*, 
                           COUNT(DISTINCT p.id) as plan_count,
                           COUNT(DISTINCT rt.id) as task_count
                    FROM research_topics t
                    LEFT JOIN research_plans p ON t.id = p.topic_id
                    LEFT JOIN research_tasks rt ON p.id = rt.plan_id
                    WHERE t.id = ?
                    GROUP BY t.id
                """, (topic_id,))
                
                row = cursor.fetchone()
                if row:
                    topic = dict(row)
                    topic['metadata'] = json.loads(topic.get('metadata', '{}'))
                    return topic
                return None
                
        except Exception as e:
            raise DatabaseError("Failed to get research topic", f"Topic retrieval failed: {e}")
    
    @handle_errors(context="get_research_topics_by_project")
    def get_research_topics_by_project(self, project_id: str, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
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
                    topic['metadata'] = json.loads(topic.get('metadata', '{}'))
                    topics.append(topic)
                
                return topics
                
        except Exception as e:
            raise DatabaseError("Failed to get research topics", f"Topics retrieval failed: {e}")
    
    # Research Plans Methods
    @handle_errors(context="create_research_plan")
    def create_research_plan(self, plan_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new research plan."""
        try:
            plan_id = plan_data.get('id', generate_timestamped_id('plan'))
            
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO research_plans 
                    (id, topic_id, name, description, plan_type, status, created_at, updated_at, 
                     estimated_cost, actual_cost, plan_structure, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    plan_id,
                    plan_data['topic_id'],
                    plan_data['name'],
                    plan_data.get('description', ''),
                    plan_data.get('plan_type', 'comprehensive'),
                    plan_data.get('status', 'draft'),
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    plan_data.get('estimated_cost', 0.0),
                    plan_data.get('actual_cost', 0.0),
                    json.dumps(plan_data.get('plan_structure', {})),
                    json.dumps(plan_data.get('metadata', {}))
                ))
                conn.commit()
                
                return self.get_research_plan(plan_id)
                
        except Exception as e:
            raise DatabaseError("Failed to create research plan", f"Plan creation failed: {e}")
    
    @handle_errors(context="get_research_plan")
    def get_research_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get a research plan by ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT p.*, 
                           COUNT(DISTINCT rt.id) as task_count,
                           COUNT(CASE WHEN rt.status = 'completed' THEN 1 END) as completed_tasks,
                           AVG(CASE WHEN rt.progress IS NOT NULL THEN rt.progress ELSE 0 END) as progress
                    FROM research_plans p
                    LEFT JOIN research_tasks rt ON p.id = rt.plan_id
                    WHERE p.id = ?
                    GROUP BY p.id
                """, (plan_id,))
                
                row = cursor.fetchone()
                if row:
                    plan = dict(row)
                    plan['plan_structure'] = json.loads(plan.get('plan_structure', '{}'))
                    plan['metadata'] = json.loads(plan.get('metadata', '{}'))
                    return plan
                return None
                
        except Exception as e:
            raise DatabaseError("Failed to get research plan", f"Plan retrieval failed: {e}")
    
    @handle_errors(context="get_research_plans_by_topic")
    def get_research_plans_by_topic(self, topic_id: str, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all research plans for a topic."""
        try:
            with self.get_connection() as conn:
                query = """
                    SELECT p.*, 
                           COUNT(DISTINCT rt.id) as task_count,
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
                    plan['plan_structure'] = json.loads(plan.get('plan_structure', '{}'))
                    plan['metadata'] = json.loads(plan.get('metadata', '{}'))
                    plans.append(plan)
                
                return plans
                
        except Exception as e:
            raise DatabaseError("Failed to get research plans", f"Plans retrieval failed: {e}")
    
    # Enhanced Task Methods (renamed from research_tasks)
    @handle_errors(context="create_task")
    def create_task(self, task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new task."""
        try:
            task_id = task_data.get('id', f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            
            # Get project_id from the plan
            plan = self.get_research_plan(task_data['plan_id'])
            if not plan:
                raise Exception(f"Plan {task_data['plan_id']} not found")
            
            # Get project_id through topic
            topic = self.get_research_topic(plan['topic_id'])
            if not topic:
                raise Exception(f"Topic {plan['topic_id']} not found")
            
            project_id = topic['project_id']
            
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO research_tasks 
                    (id, project_id, plan_id, name, query, status, stage, created_at, updated_at, 
                     estimated_cost, actual_cost, cost_approved, single_agent_mode, 
                     research_mode, max_results, progress, task_type, task_order, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task_id,
                    project_id,
                    task_data['plan_id'],
                    task_data['name'],
                    task_data.get('query', ''),
                    task_data.get('status', 'pending'),
                    task_data.get('stage', 'planning'),
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    task_data.get('estimated_cost', 0.0),
                    task_data.get('actual_cost', 0.0),
                    task_data.get('cost_approved', False),
                    task_data.get('single_agent_mode', False),
                    task_data.get('research_mode', 'comprehensive'),
                    task_data.get('max_results', 10),
                    task_data.get('progress', 0.0),
                    task_data.get('task_type', 'research'),
                    task_data.get('task_order', 0),
                    json.dumps(task_data.get('metadata', {}))
                ))
                conn.commit()
                
                return self.get_task(task_id)
                
        except Exception as e:
            raise DatabaseError("Failed to create task", f"Task creation failed: {e}")
    
    @handle_errors(context="get_task")
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task by ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM research_tasks WHERE id = ?
                """, (task_id,))
                
                row = cursor.fetchone()
                if row:
                    task = dict(row)
                    # Parse JSON fields
                    for field in ['search_results', 'execution_results', 'metadata']:
                        if task.get(field):
                            try:
                                task[field] = json.loads(task[field])
                            except (json.JSONDecodeError, TypeError):
                                task[field] = []
                    return task
                return None
                
        except Exception as e:
            raise DatabaseError("Failed to get task", f"Task retrieval failed: {e}")
    
    @handle_errors(context="get_tasks_by_plan")
    def get_tasks_by_plan(self, plan_id: str, status_filter: Optional[str] = None, 
                         type_filter: Optional[str] = None) -> List[Dict[str, Any]]:
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
                    for field in ['search_results', 'execution_results', 'metadata']:
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
                topic['plans'] = self.get_research_plans_by_topic(topic['id'])
                
                for plan in topic['plans']:
                    plan['tasks'] = self.get_tasks_by_plan(plan['id'])
            
            return {
                'project': project,
                'topics': topics
            }
            
        except Exception as e:
            raise DatabaseError("Failed to get project hierarchy", f"Hierarchy retrieval failed: {e}")
    
    # Legacy methods for backward compatibility
    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get a project by ID (legacy method)."""
        # This would call the original implementation
        # For now, return a mock
        return {
            'id': project_id,
            'name': 'Sample Project',
            'description': 'A sample project for testing',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
