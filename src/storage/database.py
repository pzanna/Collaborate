"""Database operations for the Eunice application."""

import sqlite3
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

# Import models and error handling
try:
    from ..models.data_models import Project, Conversation, Message, ConversationSession, ResearchTask
    from ..utils.error_handler import handle_errors, DatabaseError, ValidationError, safe_execute
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models.data_models import Project, Conversation, Message, ConversationSession, ResearchTask
    from utils.error_handler import handle_errors, DatabaseError, ValidationError, safe_execute


class DatabaseManager:
    """Manages database operations for the Eunice application with enhanced error handling."""
    
    def __init__(self, db_path: Optional[str] = None):
        # Use environment variable for default path if none provided
        if db_path is None:
            data_path = os.getenv("EUNICE_DATA_PATH", "data")
            db_path = os.path.join(data_path, "eunice.db")
        
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
    
    @handle_errors(context="database_initialization")
    def init_database(self) -> None:
        """Initialize the database with required tables."""
        try:
            # Ensure the directory exists (unless it's in-memory)
            if self.db_path != ":memory:":
                Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            with self.get_connection() as conn:
                self._create_tables(conn)
                self._migrate_database(conn)  # Run migrations after creating tables
        except Exception as e:
            raise DatabaseError(f"Failed to initialize database: {str(e)}", "initialization", original_error=e)
    
    @contextmanager
    def get_connection(self):
        """Get a database connection context manager with error handling."""
        conn = None
        try:
            if self._persistent_conn:
                conn = self._persistent_conn
            else:
                conn = sqlite3.connect(self.db_path, timeout=30.0)  # 30 second timeout
                conn.row_factory = sqlite3.Row
            
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys = ON")
            
            yield conn
            
            # Commit if not using persistent connection
            if not self._persistent_conn:
                conn.commit()
                
        except sqlite3.Error as e:
            if conn and not self._persistent_conn:
                try:
                    conn.rollback()
                except sqlite3.Error:
                    pass  # Ignore rollback errors
            raise DatabaseError(f"Database connection error: {str(e)}", "connection", original_error=e)
        except Exception as e:
            if conn and not self._persistent_conn:
                try:
                    conn.rollback()
                except sqlite3.Error:
                    pass  # Ignore rollback errors
            raise DatabaseError(f"Unexpected database error: {str(e)}", "connection", original_error=e)
        finally:
            if conn and not self._persistent_conn:
                try:
                    conn.close()
                except sqlite3.Error:
                    pass  # Ignore close errors

    def _create_tables(self, conn: sqlite3.Connection) -> None:
        """Create database tables."""
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
                project_id TEXT NOT NULL,
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
    
    @handle_errors(context="database_migration")
    def _migrate_database(self, conn: sqlite3.Connection) -> None:
        """Apply database migrations for schema changes."""
        cursor = conn.cursor()
        
        # Check if conversations table has description column
        cursor.execute("PRAGMA table_info(conversations)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'description' not in columns:
            # Add description column if it doesn't exist
            cursor.execute("ALTER TABLE conversations ADD COLUMN description TEXT")
            print("✓ Added description column to conversations table")
        
        # Check if research_tasks table has research_plan and plan_approved columns
        cursor.execute("PRAGMA table_info(research_tasks)")
        research_columns = [col[1] for col in cursor.fetchall()]
        
        if 'research_plan' not in research_columns:
            # Add research_plan column if it doesn't exist
            cursor.execute("ALTER TABLE research_tasks ADD COLUMN research_plan TEXT")
            print("✓ Added research_plan column to research_tasks table")
        
        if 'plan_approved' not in research_columns:
            # Add plan_approved column if it doesn't exist
            cursor.execute("ALTER TABLE research_tasks ADD COLUMN plan_approved BOOLEAN DEFAULT 0")
            print("✓ Added plan_approved column to research_tasks table")
    
    # Project operations
    @handle_errors(context="create_project", reraise=False, fallback_return=None)
    def create_project(self, project: Project) -> Optional[Project]:
        """Create a new project with error handling."""
        try:
            # Validate project data
            if not project.name or not project.name.strip():
                raise ValidationError("Project name cannot be empty", "name", project.name)
            
            if len(project.name) > 255:
                raise ValidationError("Project name too long (max 255 characters)", "name", project.name)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check for duplicate names
                cursor.execute("SELECT COUNT(*) FROM projects WHERE name = ?", (project.name,))
                if cursor.fetchone()[0] > 0:
                    raise ValidationError(f"Project with name '{project.name}' already exists", "name", project.name)
                
                # Insert project
                cursor.execute("""
                    INSERT INTO projects (id, name, description, created_at, updated_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    project.id,
                    project.name,
                    project.description,
                    project.created_at,
                    project.updated_at,
                    json.dumps(project.metadata)
                ))
                
                return project
                
        except ValidationError:
            raise  # Re-raise validation errors
        except Exception as e:
            raise DatabaseError(f"Failed to create project: {str(e)}", "create_project", 
                              {"project_name": project.name}, e)
    
    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
            
            if row:
                return Project(
                    id=row['id'],
                    name=row['name'],
                    description=row['description'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                )
            return None
    
    def list_projects(self) -> List[Project]:
        """List all projects."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM projects ORDER BY updated_at DESC"
            ).fetchall()
            
            return [
                Project(
                    id=row['id'],
                    name=row['name'],
                    description=row['description'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                )
                for row in rows
            ]
    
    def update_project(self, project: Project) -> None:
        """Update a project."""
        project.update_timestamp()
        with self.get_connection() as conn:
            conn.execute(
                """UPDATE projects 
                   SET name = ?, description = ?, updated_at = ?, metadata = ?
                   WHERE id = ?""",
                (project.name, project.description, project.updated_at, 
                 json.dumps(project.metadata), project.id)
            )
            conn.commit()

    @handle_errors(context="delete_project", reraise=False, fallback_return=False)
    def delete_project(self, project_id: str) -> bool:
        """Delete a project and all its conversations and messages."""
        try:
            if not project_id or not project_id.strip():
                raise ValidationError("Project ID cannot be empty", "project_id", project_id)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if project exists
                cursor.execute("SELECT COUNT(*) FROM projects WHERE id = ?", (project_id,))
                if cursor.fetchone()[0] == 0:
                    raise ValidationError(f"Project with ID '{project_id}' not found", 
                                        "project_id", project_id)
                
                # Get all conversations for this project
                cursor.execute("SELECT id FROM conversations WHERE project_id = ?", (project_id,))
                conversation_ids = [row[0] for row in cursor.fetchall()]
                
                # Delete all messages in conversations for this project
                for conversation_id in conversation_ids:
                    cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
                
                # Delete all conversations for this project
                cursor.execute("DELETE FROM conversations WHERE project_id = ?", (project_id,))
                
                # Delete the project
                cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
                
                conn.commit()
                return True
                
        except ValidationError:
            raise  # Re-raise validation errors
        except Exception as e:
            raise DatabaseError(f"Failed to delete project: {str(e)}", "delete_project", 
                              {"project_id": project_id}, e)
    # Conversation operations
    @handle_errors(context="create_conversation", reraise=False, fallback_return=None)
    def create_conversation(self, conversation: Conversation) -> Optional[Conversation]:
        """Create a new conversation with error handling."""
        try:
            # Validate conversation data
            if not conversation.title or not conversation.title.strip():
                raise ValidationError("Conversation title cannot be empty", "title", conversation.title)
            
            if not conversation.project_id:
                raise ValidationError("Conversation must have a project ID", "project_id", conversation.project_id)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if project exists
                cursor.execute("SELECT COUNT(*) FROM projects WHERE id = ?", (conversation.project_id,))
                if cursor.fetchone()[0] == 0:
                    raise ValidationError(f"Project with ID '{conversation.project_id}' not found", 
                                        "project_id", conversation.project_id)
                
                # Insert conversation
                cursor.execute("""
                    INSERT INTO conversations (id, project_id, title, description, status, created_at, updated_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    conversation.id,
                    conversation.project_id,
                    conversation.title,
                    "",  # Default empty description since model doesn't have it
                    conversation.status,
                    conversation.created_at,
                    conversation.updated_at,
                    json.dumps(conversation.metadata)
                ))
                
                return conversation
                
        except ValidationError:
            raise  # Re-raise validation errors
        except Exception as e:
            raise DatabaseError(f"Failed to create conversation: {str(e)}", "create_conversation", 
                              {"conversation_title": conversation.title}, e)
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
            
            if row:
                return Conversation(
                    id=row['id'],
                    project_id=row['project_id'],
                    title=row['title'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    participants=json.loads(row['participants']) if row['participants'] else [],
                    status=row['status'],
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                )
            return None
    
    @handle_errors(context="delete_conversation", reraise=False, fallback_return=False)
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all its messages."""
        try:
            if not conversation_id or not conversation_id.strip():
                raise ValidationError("Conversation ID cannot be empty", "conversation_id", conversation_id)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if conversation exists
                cursor.execute("SELECT COUNT(*) FROM conversations WHERE id = ?", (conversation_id,))
                if cursor.fetchone()[0] == 0:
                    raise ValidationError(f"Conversation with ID '{conversation_id}' not found", 
                                        "conversation_id", conversation_id)
                
                # Delete all messages in the conversation first (due to foreign key constraints)
                cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
                
                # Delete the conversation
                cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
                
                conn.commit()
                return True
                
        except ValidationError:
            raise  # Re-raise validation errors
        except Exception as e:
            raise DatabaseError(f"Failed to delete conversation: {str(e)}", "delete_conversation", 
                              {"conversation_id": conversation_id}, e)
    
    def list_conversations(self, project_id: Optional[str] = None) -> List[Conversation]:
        """List conversations, optionally filtered by project."""
        with self.get_connection() as conn:
            if project_id:
                rows = conn.execute(
                    "SELECT * FROM conversations WHERE project_id = ? ORDER BY updated_at DESC",
                    (project_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM conversations ORDER BY updated_at DESC"
                ).fetchall()
            
            return [
                Conversation(
                    id=row['id'],
                    project_id=row['project_id'],
                    title=row['title'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    participants=json.loads(row['participants']) if row['participants'] else [],
                    status=row['status'],
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                )
                for row in rows
            ]
    
    # Message operations
    @handle_errors(context="create_message", reraise=False, fallback_return=None)
    def create_message(self, message: Message) -> Optional[Message]:
        """Create a new message with error handling."""
        try:
            # Validate message data
            if not message.conversation_id:
                raise ValidationError("Message must have a conversation ID", "conversation_id", message.conversation_id)
            
            if not message.participant:
                raise ValidationError("Message must have a participant", "participant", message.participant)
            
            if not message.content or not message.content.strip():
                raise ValidationError("Message content cannot be empty", "content", message.content)
            
            if len(message.content) > 50000:  # 50KB limit
                raise ValidationError("Message content too long (max 50KB)", "content", len(message.content))
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if conversation exists
                cursor.execute("SELECT COUNT(*) FROM conversations WHERE id = ?", (message.conversation_id,))
                if cursor.fetchone()[0] == 0:
                    raise ValidationError(f"Conversation with ID '{message.conversation_id}' not found", 
                                        "conversation_id", message.conversation_id)
                
                # Insert message
                cursor.execute("""
                    INSERT INTO messages (id, conversation_id, participant, content, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    message.id,
                    message.conversation_id,
                    message.participant,
                    message.content,
                    message.timestamp,
                    json.dumps(message.metadata)
                ))
                
                # Update conversation timestamp
                cursor.execute("""
                    UPDATE conversations SET updated_at = ? WHERE id = ?
                """, (datetime.now(), message.conversation_id))
                
                return message
                
        except ValidationError:
            raise  # Re-raise validation errors
        except Exception as e:
            raise DatabaseError(f"Failed to create message: {str(e)}", "create_message", 
                              {"conversation_id": message.conversation_id}, e)
    
    def get_conversation_messages(self, conversation_id: str) -> List[Message]:
        """Get all messages for a conversation."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC",
                (conversation_id,)
            ).fetchall()
            
            return [
                Message(
                    id=row['id'],
                    conversation_id=row['conversation_id'],
                    participant=row['participant'],
                    content=row['content'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    message_type=row['message_type'],
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                )
                for row in rows
            ]
    
    def get_conversation_session(self, conversation_id: str) -> Optional[ConversationSession]:
        """Get a complete conversation session with all messages."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return None
        
        messages = self.get_conversation_messages(conversation_id)
        project = self.get_project(conversation.project_id)
        
        return ConversationSession(
            conversation=conversation,
            messages=messages,
            project=project
        )
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics and health information."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get table counts
                cursor.execute("SELECT COUNT(*) FROM projects")
                project_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM conversations")
                conversation_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM messages")
                message_count = cursor.fetchone()[0]
                
                # Get database file size (if not in-memory)
                db_size = 0
                if self.db_path != ":memory:" and os.path.exists(self.db_path):
                    db_size = os.path.getsize(self.db_path)
                
                return {
                    "projects": project_count,
                    "conversations": conversation_count,
                    "messages": message_count,
                    "database_size_bytes": db_size,
                    "database_path": self.db_path,
                    "status": "healthy"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "database_path": self.db_path
            }
    
    def backup_database(self, backup_path: str) -> bool:
        """Create a backup of the database."""
        try:
            if self.db_path == ":memory:":
                print("⚠️ Cannot backup in-memory database")
                return False
            
            import shutil
            shutil.copy2(self.db_path, backup_path)
            print(f"✓ Database backed up to {backup_path}")
            return True
            
        except Exception as e:
            print(f"❌ Database backup failed: {e}")
            return False
    
    def verify_database_integrity(self) -> bool:
        """Verify database integrity."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Run integrity check
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()
                
                if result and result[0] == "ok":
                    print("✓ Database integrity check passed")
                    return True
                else:
                    print(f"❌ Database integrity check failed: {result}")
                    return False
                    
        except Exception as e:
            print(f"❌ Database integrity check error: {e}")
            return False

    # ===== Research Task Management Methods =====

    @handle_errors(context="create_research_task", reraise=False, fallback_return=None)
    def create_research_task(self, research_task: ResearchTask) -> Optional[ResearchTask]:
        """Create a new research task with error handling."""
        try:
            # Validate research task data
            if not research_task.query or not research_task.query.strip():
                raise ValidationError("Research task query cannot be empty", "query", research_task.query)
            
            if not research_task.name or not research_task.name.strip():
                raise ValidationError("Research task name cannot be empty", "name", research_task.name)
            
            if not research_task.project_id:
                raise ValidationError("Research task must be assigned to a project", "project_id", research_task.project_id)

            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if project exists
                cursor.execute("SELECT COUNT(*) FROM projects WHERE id = ?", (research_task.project_id,))
                if cursor.fetchone()[0] == 0:
                    raise ValidationError(f"Project with ID '{research_task.project_id}' does not exist", "project_id", research_task.project_id)
                
                # Check if conversation exists (if provided)
                if research_task.conversation_id:
                    cursor.execute("SELECT COUNT(*) FROM conversations WHERE id = ?", (research_task.conversation_id,))
                    if cursor.fetchone()[0] == 0:
                        raise ValidationError(f"Conversation with ID '{research_task.conversation_id}' does not exist", "conversation_id", research_task.conversation_id)
                
                # Insert research task
                cursor.execute("""
                    INSERT INTO research_tasks (
                        id, project_id, conversation_id, query, name, status, stage,
                        created_at, updated_at, estimated_cost, actual_cost, cost_approved,
                        single_agent_mode, research_mode, max_results, progress,
                        search_results, reasoning_output, execution_results, synthesis, 
                        research_plan, plan_approved, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    research_task.id,
                    research_task.project_id,
                    research_task.conversation_id,
                    research_task.query,
                    research_task.name,
                    research_task.status,
                    research_task.stage,
                    research_task.created_at,
                    research_task.updated_at,
                    research_task.estimated_cost,
                    research_task.actual_cost,
                    research_task.cost_approved,
                    research_task.single_agent_mode,
                    research_task.research_mode,
                    research_task.max_results,
                    research_task.progress,
                    json.dumps(research_task.search_results),
                    research_task.reasoning_output,
                    json.dumps(research_task.execution_results),
                    research_task.synthesis,
                    json.dumps(research_task.research_plan) if research_task.research_plan else None,
                    research_task.plan_approved,
                    json.dumps(research_task.metadata)
                ))
                
                return research_task
                
        except ValidationError:
            raise  # Re-raise validation errors
        except Exception as e:
            raise DatabaseError(f"Failed to create research task: {str(e)}", "create_research_task", 
                              {"task_name": research_task.name}, e)

    def get_research_task(self, task_id: str) -> Optional[ResearchTask]:
        """Get a research task by ID."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM research_tasks WHERE id = ?", (task_id,)
            ).fetchone()
            
            if row:
                return ResearchTask(
                    id=row['id'],
                    project_id=row['project_id'],
                    conversation_id=row['conversation_id'],
                    query=row['query'],
                    name=row['name'],
                    status=row['status'],
                    stage=row['stage'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    estimated_cost=row['estimated_cost'],
                    actual_cost=row['actual_cost'],
                    cost_approved=bool(row['cost_approved']),
                    single_agent_mode=bool(row['single_agent_mode']),
                    research_mode=row['research_mode'],
                    max_results=row['max_results'],
                    progress=row['progress'],
                    search_results=json.loads(row['search_results']) if row['search_results'] else [],
                    reasoning_output=row['reasoning_output'],
                    execution_results=json.loads(row['execution_results']) if row['execution_results'] else [],
                    synthesis=row['synthesis'],
                    research_plan=json.loads(row['research_plan']) if row.get('research_plan') else None,
                    plan_approved=bool(row.get('plan_approved', False)),
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                )
            return None

    def update_research_task(self, research_task: ResearchTask) -> None:
        """Update a research task."""
        research_task.update_timestamp()
        with self.get_connection() as conn:
            conn.execute(
                """UPDATE research_tasks 
                   SET query = ?, name = ?, status = ?, stage = ?, updated_at = ?,
                       estimated_cost = ?, actual_cost = ?, cost_approved = ?,
                       single_agent_mode = ?, research_mode = ?, max_results = ?,
                       progress = ?, search_results = ?, reasoning_output = ?,
                       execution_results = ?, synthesis = ?, research_plan = ?, 
                       plan_approved = ?, metadata = ?
                   WHERE id = ?""",
                (research_task.query, research_task.name, research_task.status,
                 research_task.stage, research_task.updated_at, research_task.estimated_cost,
                 research_task.actual_cost, research_task.cost_approved,
                 research_task.single_agent_mode, research_task.research_mode,
                 research_task.max_results, research_task.progress,
                 json.dumps(research_task.search_results), research_task.reasoning_output,
                 json.dumps(research_task.execution_results), research_task.synthesis,
                 json.dumps(research_task.research_plan) if research_task.research_plan else None,
                 research_task.plan_approved, json.dumps(research_task.metadata), 
                 research_task.id)
            )
            conn.commit()

    def delete_research_task(self, task_id: str) -> bool:
        """Delete a research task."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM research_tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0

    def list_research_tasks(self, project_id: Optional[str] = None, conversation_id: Optional[str] = None, 
                           status_filter: Optional[str] = None, limit: int = 100) -> List[ResearchTask]:
        """List research tasks with optional filters."""
        with self.get_connection() as conn:
            query = "SELECT * FROM research_tasks WHERE 1=1"
            params = []
            
            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)
            
            if conversation_id:
                query += " AND conversation_id = ?"
                params.append(conversation_id)
            
            if status_filter:
                query += " AND status = ?"
                params.append(status_filter)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            
            return [
                ResearchTask(
                    id=row['id'],
                    project_id=row['project_id'],
                    conversation_id=row['conversation_id'],
                    query=row['query'],
                    name=row['name'],
                    status=row['status'],
                    stage=row['stage'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    estimated_cost=row['estimated_cost'],
                    actual_cost=row['actual_cost'],
                    cost_approved=bool(row['cost_approved']),
                    single_agent_mode=bool(row['single_agent_mode']),
                    research_mode=row['research_mode'],
                    max_results=row['max_results'],
                    progress=row['progress'],
                    search_results=json.loads(row['search_results']) if row['search_results'] else [],
                    reasoning_output=row['reasoning_output'],
                    execution_results=json.loads(row['execution_results']) if row['execution_results'] else [],
                    synthesis=row['synthesis'],
                    research_plan=json.loads(row['research_plan']) if row.get('research_plan') else None,
                    plan_approved=bool(row.get('plan_approved', False)),
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                )
                for row in rows
            ]
    
    def update_research_plan(self, task_id: str, research_plan: Dict[str, Any]) -> bool:
        """Update the research plan for a task."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE research_tasks 
                   SET research_plan = ?, updated_at = ?
                   WHERE id = ?""",
                (json.dumps(research_plan), datetime.now(), task_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def approve_research_plan(self, task_id: str, approved: bool = True) -> bool:
        """Approve or reject a research plan."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE research_tasks 
                   SET plan_approved = ?, updated_at = ?
                   WHERE id = ?""",
                (approved, datetime.now(), task_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def get_research_plan_for_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the research plan for a specific task."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT research_plan FROM research_tasks WHERE id = ?", 
                (task_id,)
            ).fetchone()
            
            if row and row['research_plan']:
                return json.loads(row['research_plan'])
            return None

    def get_research_tasks_by_project(self, project_id: str) -> List[ResearchTask]:
        """Get all research tasks for a specific project."""
        return self.list_research_tasks(project_id=project_id)

    def get_research_task_count_by_project(self, project_id: str) -> int:
        """Get the count of research tasks for a project."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM research_tasks WHERE project_id = ?", (project_id,))
            return cursor.fetchone()[0]

    # Hierarchical Database Methods
    def delete_research_topic(self, topic_id: str) -> bool:
        """Delete a research topic and all its plans and tasks."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if hierarchical tables exist
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name IN ('research_topics', 'research_plans')
                """)
                tables = cursor.fetchall()
                if len(tables) < 2:
                    # Hierarchical tables don't exist, return False
                    return False
                
                # Check if topic exists
                cursor.execute("SELECT id FROM research_topics WHERE id = ?", (topic_id,))
                if not cursor.fetchone():
                    return False
                
                # Delete all tasks for plans in this topic
                cursor.execute("""
                    DELETE FROM research_tasks 
                    WHERE plan_id IN (
                        SELECT id FROM research_plans WHERE topic_id = ?
                    )
                """, (topic_id,))
                
                # Delete all plans for this topic
                cursor.execute("DELETE FROM research_plans WHERE topic_id = ?", (topic_id,))
                
                # Delete the topic
                cursor.execute("DELETE FROM research_topics WHERE id = ?", (topic_id,))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error deleting research topic: {e}")
            return False
    
    def get_research_topic(self, topic_id: str) -> Optional[Dict[str, Any]]:
        """Get a research topic by ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if hierarchical tables exist
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='research_topics'
                """)
                if not cursor.fetchone():
                    return None
                
                cursor.execute("SELECT * FROM research_topics WHERE id = ?", (topic_id,))
                row = cursor.fetchone()
                if row:
                    topic = dict(row)
                    # Parse JSON fields
                    if topic.get('metadata'):
                        try:
                            topic['metadata'] = json.loads(topic['metadata'])
                        except (json.JSONDecodeError, TypeError):
                            topic['metadata'] = {}
                    return topic
                return None
        except Exception as e:
            print(f"Error getting research topic: {e}")
            return None
    
    def get_research_topics_by_project(self, project_id: str, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all research topics for a project."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if hierarchical tables exist
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='research_topics'
                """)
                if not cursor.fetchone():
                    return []
                
                query = "SELECT * FROM research_topics WHERE project_id = ?"
                params = [project_id]
                
                if status_filter:
                    query += " AND status = ?"
                    params.append(status_filter)
                
                query += " ORDER BY created_at DESC"
                
                cursor.execute(query, params)
                topics = []
                for row in cursor.fetchall():
                    topic = dict(row)
                    # Parse JSON fields
                    if topic.get('metadata'):
                        try:
                            topic['metadata'] = json.loads(topic['metadata'])
                        except (json.JSONDecodeError, TypeError):
                            topic['metadata'] = {}
                    topics.append(topic)
                
                return topics
        except Exception as e:
            print(f"Error getting research topics: {e}")
            return []
    
    def create_research_topic(self, topic_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new research topic."""
        # For now, return None to indicate this method isn't fully implemented
        return None
    
    def get_research_plans_by_topic(self, topic_id: str, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all research plans for a topic."""
        # For now, return empty list
        return []
    
    def create_research_plan(self, plan_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new research plan."""
        # For now, return None
        return None
    
    def delete_research_plan(self, plan_id: str) -> bool:
        """Delete a research plan and all its tasks."""
        # For now, return False
        return False
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task by ID."""
        # For now, return None
        return None
    
    def get_tasks_by_plan(self, plan_id: str, status_filter: Optional[str] = None, type_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all tasks for a plan."""
        # For now, return empty list
        return []
    
    def create_task(self, task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new task."""
        # For now, return None
        return None
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        # For now, return False
        return False
    
    def get_project_hierarchy(self, project_id: str) -> Dict[str, Any]:
        """Get complete hierarchy for a project."""
        # For now, return empty dict
        return {}
