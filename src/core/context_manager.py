"""Context Tracking System for maintaining session context across interactions."""

import asyncio
import logging
import json
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field

try:
    import aiosqlite
except ImportError:
    aiosqlite = None

from ..config.config_manager import ConfigManager


@dataclass
class ContextTrace:
    """Represents a context trace entry for tracking task execution."""
    trace_id: str
    context_id: str
    stage: str
    content: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    task_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SessionContext:
    """Represents a complete session context."""
    context_id: str
    conversation_id: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    status: str = "active"
    current_stage: Optional[str] = None
    messages: List[Any] = field(default_factory=list)
    research_tasks: List[Dict[str, Any]] = field(default_factory=list)
    context_traces: List[ContextTrace] = field(default_factory=list)
    active_agents: List[str] = field(default_factory=list)
    memory_references: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    settings: Dict[str, Any] = field(default_factory=dict)


class ContextManager:
    """Manages session contexts with persistence and tracking capabilities."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        self.db_connection: Optional[aiosqlite.Connection] = None
        self.db_path = Path(config_manager.get('storage.database_path', 'data/collaborate.db'))
        self.active_contexts: Dict[str, SessionContext] = {}
        
    async def initialize(self) -> None:
        """Initialize the context manager and database."""
        try:
            if aiosqlite is None:
                self.logger.warning("aiosqlite not available, context tracking disabled")
                return
                
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.db_connection = await aiosqlite.connect(str(self.db_path))
            await self._create_database_schema()
            await self._load_active_contexts()
            self.logger.info(f"ContextManager initialized with {len(self.active_contexts)} active contexts")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ContextManager: {e}")
            raise
    
    async def cleanup(self) -> None:
        """Clean up context manager resources."""
        try:
            await self._save_active_contexts()
            if self.db_connection:
                await self.db_connection.close()
                self.db_connection = None
            self.logger.info("ContextManager cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during ContextManager cleanup: {e}")
    
    async def _ensure_db_connection(self) -> aiosqlite.Connection:
        """Ensure database connection is available."""
        if self.db_connection is None:
            await self.initialize()
        if self.db_connection is None:
            raise RuntimeError("Database connection could not be established")
        return self.db_connection
    
    async def _create_database_schema(self) -> None:
        """Create the database schema for context tracking."""
        if not self.db_connection:
            return
            
        await self.db_connection.execute('''
            CREATE TABLE IF NOT EXISTS contexts (
                context_id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                current_stage TEXT,
                active_agents TEXT,
                memory_references TEXT,
                metadata TEXT,
                settings TEXT
            )
        ''')
        
        await self.db_connection.execute('''
            CREATE TABLE IF NOT EXISTS context_traces (
                trace_id TEXT PRIMARY KEY,
                context_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                task_id TEXT,
                metadata TEXT,
                FOREIGN KEY (context_id) REFERENCES contexts (context_id) ON DELETE CASCADE
            )
        ''')
        
        await self.db_connection.commit()
        self.logger.info("Database schema created successfully")
    
    async def _load_active_contexts(self) -> None:
        """Load active contexts from database."""
        if not self.db_connection:
            return
            
        try:
            async with self.db_connection.execute('''
                SELECT context_id, conversation_id, created_at, updated_at, status, 
                       current_stage, active_agents, memory_references, metadata, settings
                FROM contexts 
                WHERE status IN ('active', 'paused')
                ORDER BY updated_at DESC
            ''') as cursor:
                async for row in cursor:
                    context = SessionContext(
                        context_id=row[0],
                        conversation_id=row[1],
                        created_at=datetime.fromisoformat(row[2]),
                        updated_at=datetime.fromisoformat(row[3]),
                        status=row[4],
                        current_stage=row[5],
                        active_agents=json.loads(row[6]) if row[6] else [],
                        memory_references=json.loads(row[7]) if row[7] else [],
                        metadata=json.loads(row[8]) if row[8] else {},
                        settings=json.loads(row[9]) if row[9] else {}
                    )
                    self.active_contexts[row[0]] = context
                    
            self.logger.info(f"Loaded {len(self.active_contexts)} active contexts")
        except Exception as e:
            self.logger.error(f"Failed to load active contexts: {e}")
    
    async def _save_active_contexts(self) -> None:
        """Save all active contexts to database."""
        if not self.db_connection:
            return
            
        try:
            for context in self.active_contexts.values():
                await self._save_context(context)
        except Exception as e:
            self.logger.error(f"Failed to save active contexts: {e}")
    
    async def _save_context(self, context: SessionContext) -> None:
        """Save a single context to database."""
        if not self.db_connection:
            return
            
        try:
            context.updated_at = datetime.now()
            await self.db_connection.execute('''
                INSERT OR REPLACE INTO contexts 
                (context_id, conversation_id, created_at, updated_at, status, current_stage,
                 active_agents, memory_references, metadata, settings)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                context.context_id, context.conversation_id,
                context.created_at.isoformat(), context.updated_at.isoformat(),
                context.status, context.current_stage,
                json.dumps(context.active_agents), json.dumps(context.memory_references),
                json.dumps(context.metadata), json.dumps(context.settings)
            ))
            await self.db_connection.commit()
        except Exception as e:
            self.logger.error(f"Failed to save context {context.context_id}: {e}")
    
    # Public API Methods
    
    async def create_context(self, conversation_id: str, context_id: Optional[str] = None) -> str:
        """Create a new session context."""
        try:
            if context_id is None:
                context_id = str(uuid.uuid4())
            
            if context_id in self.active_contexts:
                self.logger.warning(f"Context {context_id} already exists")
                return context_id
            
            context = SessionContext(context_id=context_id, conversation_id=conversation_id)
            self.active_contexts[context_id] = context
            await self._save_context(context)
            
            self.logger.info(f"Created new context: {context_id} for conversation: {conversation_id}")
            return context_id
            
        except Exception as e:
            self.logger.error(f"Failed to create context: {e}")
            raise
    
    async def get_context(self, context_id: str) -> Optional[SessionContext]:
        """Get a context by ID."""
        try:
            if context_id in self.active_contexts:
                return self.active_contexts[context_id]
            
            if not self.db_connection:
                return None
                
            async with self.db_connection.execute('''
                SELECT context_id, conversation_id, created_at, updated_at, status, 
                       current_stage, active_agents, memory_references, metadata, settings
                FROM contexts 
                WHERE context_id = ?
            ''', (context_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    context = SessionContext(
                        context_id=row[0], conversation_id=row[1],
                        created_at=datetime.fromisoformat(row[2]),
                        updated_at=datetime.fromisoformat(row[3]),
                        status=row[4], current_stage=row[5],
                        active_agents=json.loads(row[6]) if row[6] else [],
                        memory_references=json.loads(row[7]) if row[7] else [],
                        metadata=json.loads(row[8]) if row[8] else {},
                        settings=json.loads(row[9]) if row[9] else {}
                    )
                    if context.status in ['active', 'paused']:
                        self.active_contexts[context_id] = context
                    return context
            return None
        except Exception as e:
            self.logger.error(f"Failed to get context {context_id}: {e}")
            return None
    
    async def resume_context(self, context_id: str) -> Optional[SessionContext]:
        """Resume a context with full data restoration."""
        try:
            context = await self.get_context(context_id)
            if not context:
                return None
            
            if context.status == 'paused':
                context.status = 'active'
                await self._save_context(context)
            
            self.active_contexts[context_id] = context
            self.logger.info(f"Resumed context: {context_id}")
            return context
        except Exception as e:
            self.logger.error(f"Failed to resume context {context_id}: {e}")
            return None
    
    async def add_context_trace(self, context_id: str, stage: str, content: Dict[str, Any], 
                              task_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add a context trace entry."""
        try:
            trace_id = str(uuid.uuid4())
            trace = ContextTrace(
                trace_id=trace_id, context_id=context_id, stage=stage, 
                content=content, task_id=task_id, metadata=metadata
            )
            
            if context_id in self.active_contexts:
                self.active_contexts[context_id].context_traces.append(trace)
            
            if self.db_connection:
                await self.db_connection.execute('''
                    INSERT INTO context_traces 
                    (trace_id, context_id, stage, content, timestamp, task_id, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    trace_id, context_id, stage, json.dumps(content),
                    trace.timestamp.isoformat(), task_id,
                    json.dumps(metadata) if metadata else None
                ))
                await self.db_connection.commit()
            
            self.logger.debug(f"Added context trace {trace_id} for context {context_id}")
            return trace_id
        except Exception as e:
            self.logger.error(f"Failed to add context trace: {e}")
            raise
    
    async def get_context_traces(self, context_id: str, limit: int = 100) -> List[ContextTrace]:
        """Get context traces for a context."""
        try:
            if context_id in self.active_contexts:
                traces = self.active_contexts[context_id].context_traces
                return traces[-limit:] if len(traces) > limit else traces
            
            if not self.db_connection:
                return []
                
            traces = []
            async with self.db_connection.execute('''
                SELECT trace_id, stage, content, timestamp, task_id, metadata
                FROM context_traces 
                WHERE context_id = ? 
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (context_id, limit)) as cursor:
                async for row in cursor:
                    trace = ContextTrace(
                        trace_id=row[0], context_id=context_id, stage=row[1],
                        content=json.loads(row[2]), 
                        timestamp=datetime.fromisoformat(row[3]),
                        task_id=row[4],
                        metadata=json.loads(row[5]) if row[5] else None
                    )
                    traces.append(trace)
            
            return list(reversed(traces))
        except Exception as e:
            self.logger.error(f"Failed to get context traces for {context_id}: {e}")
            return []
    
    async def list_contexts(self, conversation_id: Optional[str] = None, 
                          status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """List contexts with optional filtering."""
        try:
            if not self.db_connection:
                return []
                
            conditions = []
            params = []
            
            if conversation_id:
                conditions.append("conversation_id = ?")
                params.append(conversation_id)
            
            if status:
                conditions.append("status = ?")
                params.append(status)
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            query = f'''
                SELECT context_id, conversation_id, created_at, updated_at, 
                       status, current_stage, metadata
                FROM contexts 
                {where_clause}
                ORDER BY updated_at DESC 
                LIMIT ?
            '''
            params.append(limit)
            
            contexts = []
            async with self.db_connection.execute(query, params) as cursor:
                async for row in cursor:
                    contexts.append({
                        'context_id': row[0], 'conversation_id': row[1],
                        'created_at': row[2], 'updated_at': row[3],
                        'status': row[4], 'current_stage': row[5],
                        'metadata': json.loads(row[6]) if row[6] else {}
                    })
            return contexts
        except Exception as e:
            self.logger.error(f"Failed to list contexts: {e}")
            return []
    
    async def update_context_status(self, context_id: str, status: str, current_stage: Optional[str] = None) -> bool:
        """Update context status and current stage."""
        try:
            if context_id in self.active_contexts:
                self.active_contexts[context_id].status = status
                self.active_contexts[context_id].updated_at = datetime.now()
                if current_stage is not None:
                    self.active_contexts[context_id].current_stage = current_stage
                await self._save_context(self.active_contexts[context_id])
            elif self.db_connection:
                await self.db_connection.execute('''
                    UPDATE contexts 
                    SET status = ?, current_stage = COALESCE(?, current_stage), updated_at = ?
                    WHERE context_id = ?
                ''', (status, current_stage, datetime.now().isoformat(), context_id))
                await self.db_connection.commit()
            
            self.logger.info(f"Updated context {context_id} status to {status}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update context {context_id} status: {e}")
            return False
