"""Database operations for the Collaborate application."""

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
    from ..models.data_models import Project, Conversation, Message, ConversationSession
    from ..utils.error_handler import handle_errors, DatabaseError, ValidationError, safe_execute
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models.data_models import Project, Conversation, Message, ConversationSession
    from utils.error_handler import handle_errors, DatabaseError, ValidationError, safe_execute


class DatabaseManager:
    """Manages database operations for the Collaborate application with enhanced error handling."""
    
    def __init__(self, db_path: str = "data/collaborate.db"):
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
            
            CREATE INDEX IF NOT EXISTS idx_conversations_project_id ON conversations(project_id);
            CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
            CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
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
