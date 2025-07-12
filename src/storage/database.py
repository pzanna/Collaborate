"""Database operations for the Collaborate application."""

import sqlite3
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

# Import models
try:
    from ..models.data_models import Project, Conversation, Message, ConversationSession
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models.data_models import Project, Conversation, Message, ConversationSession


class DatabaseManager:
    """Manages database operations for the Collaborate application."""
    
    def __init__(self, db_path: str = "data/collaborate.db"):
        self.db_path = db_path
        self._persistent_conn = None
        
        # For in-memory databases, we need to keep a persistent connection
        if db_path == ":memory:":
            self._persistent_conn = sqlite3.connect(db_path)
            self._persistent_conn.row_factory = sqlite3.Row
        
        self.init_database()
    
    def __del__(self):
        """Clean up persistent connection."""
        if self._persistent_conn:
            self._persistent_conn.close()
    
    def init_database(self) -> None:
        """Initialize the database with required tables."""
        # Ensure the directory exists (unless it's in-memory)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with self.get_connection() as conn:
            self._create_tables(conn)
    
    @contextmanager
    def get_connection(self):
        """Get a database connection context manager."""
        if self._persistent_conn:
            # Use persistent connection for in-memory databases
            try:
                yield self._persistent_conn
                self._persistent_conn.commit()
            except Exception:
                self._persistent_conn.rollback()
                raise
        else:
            # Use regular connection for file databases
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
    
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
    
    # Project operations
    def create_project(self, project: Project) -> None:
        """Create a new project."""
        with self.get_connection() as conn:
            conn.execute(
                """INSERT INTO projects (id, name, description, created_at, updated_at, metadata)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (project.id, project.name, project.description, 
                 project.created_at, project.updated_at, json.dumps(project.metadata))
            )
            conn.commit()
    
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
                    metadata=json.loads(row['metadata'])
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
                    metadata=json.loads(row['metadata'])
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
    def create_conversation(self, conversation: Conversation) -> None:
        """Create a new conversation."""
        with self.get_connection() as conn:
            conn.execute(
                """INSERT INTO conversations 
                   (id, project_id, title, created_at, updated_at, participants, status, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (conversation.id, conversation.project_id, conversation.title,
                 conversation.created_at, conversation.updated_at,
                 json.dumps(conversation.participants), conversation.status,
                 json.dumps(conversation.metadata))
            )
            conn.commit()
    
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
                    participants=json.loads(row['participants']),
                    status=row['status'],
                    metadata=json.loads(row['metadata'])
                )
            return None
    
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
                    participants=json.loads(row['participants']),
                    status=row['status'],
                    metadata=json.loads(row['metadata'])
                )
                for row in rows
            ]
    
    # Message operations
    def create_message(self, message: Message) -> None:
        """Create a new message."""
        with self.get_connection() as conn:
            conn.execute(
                """INSERT INTO messages 
                   (id, conversation_id, participant, content, timestamp, message_type, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (message.id, message.conversation_id, message.participant,
                 message.content, message.timestamp, message.message_type,
                 json.dumps(message.metadata))
            )
            conn.commit()
    
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
                    metadata=json.loads(row['metadata'])
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
