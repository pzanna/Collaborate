"""
Memory Service for Eunice Research Platform.

This module provides a containerized Memory  that handles:
- Knowledge base management
- Document storage and retrieval  
- Research artifact organization
- Semantic search capabilities
- Memory consolidation and pruning

ARCHITECTURE COMPLIANCE:
- ONLY exposes health check API endpoint (/health)
- ALL business operations via MCP protocol exclusively
- NO direct HTTP/REST endpoints for business logic
"""

import asyncio
import json
import logging
import sqlite3
import sys
import tempfile
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiosqlite
import uvicorn
import websockets
from fastapi import FastAPI
from websockets.exceptions import ConnectionClosed, WebSocketException

# Import the standardized health check service
from health_check import create_health_check_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import watchfiles with fallback after logger is configured
try:
    from watchfiles import awatch
    WATCHFILES_AVAILABLE = True
    logger.info("watchfiles imported successfully")
except ImportError as e:
    logger.warning(f"watchfiles not available: {e}")
    awatch = None  # type: ignore
    WATCHFILES_AVAILABLE = False


@dataclass
class MemoryRecord:
    """Enhanced memory record structure."""
    
    id: str
    context_id: str
    content: str
    memory_type: str = "general"  # "task_result", "finding", "insight", "context"
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    importance: float = 0.5
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    source_task_id: Optional[str] = None


@dataclass
class KnowledgeNode:
    """Knowledge graph node."""
    
    id: str
    content: str
    node_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class KnowledgeEdge:
    """Knowledge graph edge."""
    
    id: str
    from_node: str
    to_node: str
    relationship: str
    strength: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


class MemoryService:
    """
    Memory Service for knowledge base management.
    
    Handles memory operations, knowledge graph management,
    and semantic search via MCP protocol.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Memory Service."""
        self.config = config
        self._id = "memory_"
        self._type = "memory"
        
        # Service configuration
        self.service_host = config.get("service_host", "0.0.0.0")
        self.service_port = config.get("service_port", 8009)
        self.mcp_server_url = config.get("mcp_server_url", "ws://mcp-server:9000")
        
        # Memory configuration - Use /app/data for writable storage in secure containers
        self.memory_db_path = Path("/app/data/memory.db")
        self.max_memory_size = config.get("max_memory_size", 10000)
        self.importance_threshold = config.get("importance_threshold", 0.3)
        self.consolidation_interval = config.get("consolidation_interval", 3600)
        
        # Knowledge graph configuration
        self.max_graph_nodes = config.get("max_graph_nodes", 5000)
        self.max_graph_edges = config.get("max_graph_edges", 10000)
        self.edge_decay_rate = config.get("edge_decay_rate", 0.95)
        
        # MCP connection
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.mcp_connected = False
        self.should_run = True
        
        # Database connection
        self.db_connection: Optional[aiosqlite.Connection] = None
        
        # In-memory caches
        self.memory_cache: Dict[str, MemoryRecord] = {}
        self.knowledge_cache: Dict[str, KnowledgeNode] = {}
        self.edge_cache: Dict[str, KnowledgeEdge] = {}
        
        # Last consolidation time
        self.last_consolidation = datetime.now()
        
        # Task processing queue
        self.task_queue = asyncio.Queue()
        
        # File watching
        self.watch_paths = [
            "/app/config",  # Watch config directory for changes
            "/app/data"     # Watch data directory for external changes
        ]
        self.file_watcher_task: Optional[asyncio.Task] = None
        
        # Capabilities
        capabilities_list = [
            "store_memory",
            "retrieve_memory", 
            "search_knowledge",
            "manage_knowledge_graph",
            "consolidate_memory",
            "semantic_search"
        ]
        
        # Add file watching capability if available
        if WATCHFILES_AVAILABLE:
            capabilities_list.append("file_watching")
        
        self.capabilities = capabilities_list
        
        logger.info(f"Memory Service initialized on port {self.service_port}")
    
    async def start(self):
        """Start the Memory Service."""
        try:
            # Ensure data directory exists
            self.memory_db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Initialize database
            await self._initialize_database()
            
            # Load memory cache
            await self._load_memory_cache()
            
            # Load knowledge cache
            await self._load_knowledge_cache()
            
            # Connect to MCP server
            await self._connect_to_mcp_server()
            
            # Prepare tasks to run concurrently
            tasks_to_run = []
            
            # Always start these core tasks
            tasks_to_run.extend([
                asyncio.create_task(self._process_task_queue()),
                asyncio.create_task(self._periodic_consolidation()),
                asyncio.create_task(self._listen_for_tasks())
            ])
            
            # Start file watcher if available
            if WATCHFILES_AVAILABLE:
                self.file_watcher_task = asyncio.create_task(self._watch_files())
                tasks_to_run.append(self.file_watcher_task)
                logger.info("File watching enabled")
            else:
                logger.info("File watching disabled - watchfiles not available")
            
            # Start all tasks concurrently
            await asyncio.gather(*tasks_to_run)
            
            logger.info("Memory Service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Memory Service: {e}")
            raise
    
    async def stop(self):
        """Stop the Memory Service."""
        try:
            self.should_run = False
            
            # Cancel file watcher task if it exists
            if self.file_watcher_task and not self.file_watcher_task.done():
                self.file_watcher_task.cancel()
                try:
                    await self.file_watcher_task
                except asyncio.CancelledError:
                    pass
            
            # Close database connection
            if self.db_connection:
                await self.db_connection.close()
            
            # Close MCP connection
            if self.websocket:
                await self.websocket.close()
            
            logger.info("Memory Service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping Memory Service: {e}")
    
    async def _watch_files(self):
        """Watch files and directories for changes."""
        try:
            if not WATCHFILES_AVAILABLE:
                logger.warning("File watching not available - watchfiles not installed")
                return
            
            logger.info(f"Starting file watcher for paths: {self.watch_paths}")
            
            # Filter paths that actually exist
            existing_paths = []
            for path in self.watch_paths:
                path_obj = Path(path)
                if path_obj.exists():
                    existing_paths.append(str(path_obj))
                else:
                    logger.warning(f"Watch path does not exist: {path}")
            
            if not existing_paths:
                logger.warning("No valid paths to watch")
                return
            
            if awatch is None:
                logger.error("awatch function not available")
                return
            
            async for changes in awatch(*existing_paths, watch_filter=None):
                if not self.should_run:
                    break
                    
                await self._handle_file_changes(changes)
                
        except Exception as e:
            logger.error(f"Error in file watcher: {e}")
    
    async def _handle_file_changes(self, changes):
        """Handle detected file changes."""
        try:
            for change_type, path in changes:
                path_str = str(path)
                logger.info(f"File change detected: {change_type.name} - {path_str}")
                
                # Handle config file changes
                if "/config/" in path_str and path_str.endswith(".json"):
                    await self._handle_config_change(path_str)
                
                # Handle database file changes (external modifications)
                elif path_str.endswith(".db"):
                    await self._handle_database_change(path_str)
                
                # Handle other data file changes
                else:
                    await self._handle_data_file_change(path_str, change_type.name)
                    
        except Exception as e:
            logger.error(f"Error handling file changes: {e}")
    
    async def _handle_config_change(self, config_path: str):
        """Handle configuration file changes."""
        try:
            logger.info(f"Configuration file changed: {config_path}")
            
            # If it's the main config file, we might want to reload some settings
            if "config.json" in config_path:
                logger.info("Main configuration file changed - considering reload")
                # Note: Full reload would require service restart
                # For now, just log the change
                
        except Exception as e:
            logger.error(f"Error handling config change: {e}")
    
    async def _handle_database_change(self, db_path: str):
        """Handle database file changes."""
        try:
            logger.info(f"Database file changed externally: {db_path}")
            
            # If our main database was modified externally, reload cache
            if str(self.memory_db_path) in db_path:
                logger.info("Memory database changed externally - reloading cache")
                await self._load_memory_cache()
                await self._load_knowledge_cache()
                
        except Exception as e:
            logger.error(f"Error handling database change: {e}")
    
    async def _handle_data_file_change(self, file_path: str, change_type: str):
        """Handle other data file changes."""
        try:
            logger.info(f"Data file {change_type.lower()}: {file_path}")
            
            # Could implement specific handling for different file types
            # For example, watching for import files, backup files, etc.
            
        except Exception as e:
            logger.error(f"Error handling data file change: {e}")
    
    async def _initialize_database(self):
        """Initialize SQLite database for memory storage."""
        try:
            self.db_connection = await aiosqlite.connect(str(self.memory_db_path))
            
            # Create memory records table
            await self.db_connection.execute("""
                CREATE TABLE IF NOT EXISTS memory_records (
                    id TEXT PRIMARY KEY,
                    context_id TEXT,
                    content TEXT,
                    memory_type TEXT,
                    metadata TEXT,
                    timestamp TEXT,
                    importance REAL,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TEXT,
                    tags TEXT,
                    source_task_id TEXT
                )
            """)
            
            # Create knowledge nodes table
            await self.db_connection.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_nodes (
                    id TEXT PRIMARY KEY,
                    content TEXT,
                    node_type TEXT,
                    properties TEXT,
                    created_at TEXT
                )
            """)
            
            # Create knowledge edges table
            await self.db_connection.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_edges (
                    id TEXT PRIMARY KEY,
                    from_node TEXT,
                    to_node TEXT,
                    relationship TEXT,
                    strength REAL,
                    properties TEXT,
                    created_at TEXT
                )
            """)
            
            await self.db_connection.commit()
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    async def _load_memory_cache(self):
        """Load recent memory records into cache."""
        try:
            if not self.db_connection:
                return
            
            # Load recent important memories
            async with self.db_connection.execute("""
                SELECT * FROM memory_records 
                WHERE importance > ? 
                ORDER BY timestamp DESC 
                LIMIT 1000
            """, (self.importance_threshold,)) as cursor:
                
                async for row in cursor:
                    record = MemoryRecord(
                        id=row[0],
                        context_id=row[1],
                        content=row[2],
                        memory_type=row[3],
                        metadata=json.loads(row[4]) if row[4] else {},
                        timestamp=datetime.fromisoformat(row[5]),
                        importance=row[6],
                        access_count=row[7],
                        last_accessed=datetime.fromisoformat(row[8]) if row[8] else None,
                        tags=json.loads(row[9]) if row[9] else [],
                        source_task_id=row[10]
                    )
                    self.memory_cache[record.id] = record
            
            logger.info(f"Loaded {len(self.memory_cache)} memory records into cache")
            
        except Exception as e:
            logger.error(f"Error loading memory cache: {e}")
    
    async def _load_knowledge_cache(self):
        """Load knowledge graph nodes and edges into cache."""
        try:
            if not self.db_connection:
                return
            
            # Load knowledge nodes
            async with self.db_connection.execute("SELECT * FROM knowledge_nodes LIMIT 1000") as cursor:
                async for row in cursor:
                    node = KnowledgeNode(
                        id=row[0],
                        content=row[1],
                        node_type=row[2],
                        properties=json.loads(row[3]) if row[3] else {},
                        created_at=datetime.fromisoformat(row[4])
                    )
                    self.knowledge_cache[node.id] = node
            
            # Load knowledge edges
            async with self.db_connection.execute("SELECT * FROM knowledge_edges LIMIT 2000") as cursor:
                async for row in cursor:
                    edge = KnowledgeEdge(
                        id=row[0],
                        from_node=row[1],
                        to_node=row[2],
                        relationship=row[3],
                        strength=row[4],
                        properties=json.loads(row[5]) if row[5] else {},
                        created_at=datetime.fromisoformat(row[6])
                    )
                    self.edge_cache[edge.id] = edge
            
            logger.info(f"Loaded {len(self.knowledge_cache)} nodes and {len(self.edge_cache)} edges into cache")
            
        except Exception as e:
            logger.error(f"Error loading knowledge cache: {e}")
    
    async def _connect_to_mcp_server(self):
        """Connect to MCP server."""
        max_retries = 10
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Connecting to MCP server at {self.mcp_server_url} (attempt {attempt + 1})")
                
                self.websocket = await websockets.connect(
                    self.mcp_server_url,
                    ping_interval=30,
                    ping_timeout=10
                )
                
                # Register with MCP server
                await self._register_with_mcp_server()
                
                self.mcp_connected = True
                logger.info("Successfully connected to MCP server")
                return
                
            except Exception as e:
                logger.warning(f"Failed to connect to MCP server (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("Failed to connect to MCP server after all retries")
                    raise
    
    async def _register_with_mcp_server(self):
        """Register this  with the MCP server."""
        if not self.websocket:
            raise Exception("WebSocket connection not available")
            
        registration_message = {
            "type": "_register",
            "_id": self._id,
            "_type": self._type,
            "capabilities": self.capabilities,
            "timestamp": datetime.now().isoformat(),
            "service_info": {
                    "host": self.service_host,
                    "port": self.service_port,
                    "health_endpoint": f"http://{self.service_host}:{self.service_port}/health"
                }
            
        }
        
        await self.websocket.send(json.dumps(registration_message))
        logger.info(f"Registered with MCP server: {len(self.capabilities)} capabilities")
    
    async def _listen_for_tasks(self):
        """Listen for tasks from MCP server."""
        try:
            if not self.websocket:
                logger.error("Cannot listen for tasks: no websocket connection")
                return
                
            logger.info("Starting to listen for tasks from MCP server")
            
            async for message in self.websocket:
                if not self.should_run:
                    break
                    
                try:
                    data = json.loads(message)
                    await self.task_queue.put(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse MCP message: {e}")
                except Exception as e:
                    logger.error(f"Error handling MCP message: {e}")
                    
        except ConnectionClosed:
            logger.warning("MCP server connection closed")
            self.mcp_connected = False
        except WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            self.mcp_connected = False
        except Exception as e:
            logger.error(f"Unexpected error in message listener: {e}")
            self.mcp_connected = False
    
    async def _process_task_queue(self):
        """Process tasks from the MCP queue."""
        while self.should_run:
            try:
                # Get task from queue
                task_data = await self.task_queue.get()
                
                # Process the task
                result = await self._process_memory_task(task_data)
                
                # Send result back to MCP server
                if self.websocket and self.mcp_connected:
                    response = {
                        "jsonrpc": "2.0",
                        "id": task_data.get("id"),
                        "result": result
                    }
                    await self.websocket.send(json.dumps(response))
                
                # Mark task as done
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing task: {e}")
                await asyncio.sleep(1)
    
    async def _process_memory_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a memory-related task."""
        try:
            method = task_data.get("method", "")
            params = task_data.get("params", {})
            
            # Route to appropriate handler
            if method == "task/execute":
                task_type = params.get("task_type", "")
                data = params.get("data", {})
                
                if task_type == "store_memory":
                    return await self._handle_store_memory(data)
                elif task_type == "retrieve_memory":
                    return await self._handle_retrieve_memory(data)
                elif task_type == "search_knowledge":
                    return await self._handle_search_knowledge(data)
                elif task_type == "manage_knowledge_graph":
                    return await self._handle_manage_knowledge_graph(data)
                elif task_type == "consolidate_memory":
                    return await self._handle_consolidate_memory(data)
                elif task_type == "file_watching":
                    return await self._handle_file_watching(data)
                else:
                    return {
                        "status": "failed",
                        "error": f"Unknown task type: {task_type}",
                        "timestamp": datetime.now().isoformat()
                    }
            elif method == "/ping":
                return {"status": "alive", "timestamp": datetime.now().isoformat()}
            elif method == "/status":
                return await self._get__status()
            else:
                return {
                    "status": "failed",
                    "error": f"Unknown method: {method}",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error processing memory task: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_store_memory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle store memory request."""
        try:
            content = data.get("content", "")
            context_id = data.get("context_id", str(uuid.uuid4()))
            memory_type = data.get("memory_type", "general")
            importance = data.get("importance", 0.5)
            tags = data.get("tags", [])
            
            if not content:
                return {
                    "status": "failed",
                    "error": "Content is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Create memory record
            record = MemoryRecord(
                id=str(uuid.uuid4()),
                context_id=context_id,
                content=content,
                memory_type=memory_type,
                importance=importance,
                tags=tags,
                metadata=data.get("metadata", {})
            )
            
            # Store in database
            await self._store_memory_record(record)
            
            # Add to cache if important
            if importance > self.importance_threshold:
                self.memory_cache[record.id] = record
            
            return {
                "status": "completed",
                "memory_id": record.id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_retrieve_memory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle retrieve memory request."""
        try:
            query = data.get("query", "")
            context_id = data.get("context_id")
            memory_type = data.get("memory_type")
            limit = data.get("limit", 10)
            
            # Search memories
            memories = await self._search_memories(
                query=query,
                context_id=context_id,
                memory_type=memory_type,
                limit=limit
            )
            
            return {
                "status": "completed",
                "memories": [self._memory_to_dict(m) for m in memories],
                "count": len(memories),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve memory: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_search_knowledge(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle knowledge search request."""
        try:
            query = data.get("query", "")
            node_types = data.get("node_types", [])
            limit = data.get("limit", 20)
            
            # Search knowledge graph
            nodes = await self._search_knowledge_nodes(
                query=query,
                node_types=node_types,
                limit=limit
            )
            
            return {
                "status": "completed",
                "nodes": [self._node_to_dict(n) for n in nodes],
                "count": len(nodes),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to search knowledge: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_manage_knowledge_graph(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle knowledge graph management request."""
        try:
            operation = data.get("operation", "")
            
            if operation == "add_node":
                node_data = data.get("node", {})
                node = await self._add_knowledge_node(node_data)
                return {
                    "status": "completed",
                    "node_id": node.id,
                    "timestamp": datetime.now().isoformat()
                }
            elif operation == "add_edge":
                edge_data = data.get("edge", {})
                edge = await self._add_knowledge_edge(edge_data)
                return {
                    "status": "completed",
                    "edge_id": edge.id,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "failed",
                    "error": f"Unknown operation: {operation}",
                    "available_operations": ["add_node", "add_edge"],
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to manage knowledge graph: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_consolidate_memory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle memory consolidation request."""
        try:
            force = data.get("force", False)
            
            # Perform consolidation
            result = await self._consolidate_memory(force)
            
            return {
                "status": "completed",
                "consolidation_result": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to consolidate memory: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_file_watching(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file watching request."""
        try:
            operation = data.get("operation", "")
            
            if operation == "add_watch_path":
                path = data.get("path", "")
                if path and Path(path).exists():
                    if path not in self.watch_paths:
                        self.watch_paths.append(path)
                        logger.info(f"Added watch path: {path}")
                    return {
                        "status": "completed",
                        "operation": "add_watch_path",
                        "path": path,
                        "watch_paths": self.watch_paths,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "status": "failed",
                        "error": f"Path does not exist: {path}",
                        "timestamp": datetime.now().isoformat()
                    }
            elif operation == "remove_watch_path":
                path = data.get("path", "")
                if path in self.watch_paths:
                    self.watch_paths.remove(path)
                    logger.info(f"Removed watch path: {path}")
                return {
                    "status": "completed",
                    "operation": "remove_watch_path",
                    "path": path,
                    "watch_paths": self.watch_paths,
                    "timestamp": datetime.now().isoformat()
                }
            elif operation == "list_watch_paths":
                return {
                    "status": "completed",
                    "operation": "list_watch_paths",
                    "watch_paths": self.watch_paths,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "failed",
                    "error": f"Unknown file watching operation: {operation}",
                    "available_operations": ["add_watch_path", "remove_watch_path", "list_watch_paths"],
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to handle file watching: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _store_memory_record(self, record: MemoryRecord):
        """Store memory record in database."""
        if not self.db_connection:
            raise Exception("Database connection not available")
        
        await self.db_connection.execute("""
            INSERT INTO memory_records 
            (id, context_id, content, memory_type, metadata, timestamp, 
             importance, access_count, last_accessed, tags, source_task_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.id,
            record.context_id,
            record.content,
            record.memory_type,
            json.dumps(record.metadata),
            record.timestamp.isoformat(),
            record.importance,
            record.access_count,
            record.last_accessed.isoformat() if record.last_accessed else None,
            json.dumps(record.tags),
            record.source_task_id
        ))
        
        await self.db_connection.commit()
    
    async def _search_memories(self, query: str = "", context_id: Optional[str] = None, 
                             memory_type: Optional[str] = None, limit: int = 10) -> List[MemoryRecord]:
        """Search memories in cache and database."""
        memories = []
        
        # Search in cache first
        for record in self.memory_cache.values():
            if self._matches_memory_criteria(record, query, context_id, memory_type):
                memories.append(record)
        
        # If we need more results, search database
        if len(memories) < limit and self.db_connection:
            # Build SQL query
            sql = "SELECT * FROM memory_records WHERE 1=1"
            params = []
            
            if query:
                sql += " AND content LIKE ?"
                params.append(f"%{query}%")
            
            if context_id:
                sql += " AND context_id = ?"
                params.append(context_id)
            
            if memory_type:
                sql += " AND memory_type = ?"
                params.append(memory_type)
            
            sql += " ORDER BY importance DESC, timestamp DESC LIMIT ?"
            params.append(limit)
            
            async with self.db_connection.execute(sql, params) as cursor:
                async for row in cursor:
                    if len(memories) >= limit:
                        break
                    
                    record = MemoryRecord(
                        id=row[0],
                        context_id=row[1],
                        content=row[2],
                        memory_type=row[3],
                        metadata=json.loads(row[4]) if row[4] else {},
                        timestamp=datetime.fromisoformat(row[5]),
                        importance=row[6],
                        access_count=row[7],
                        last_accessed=datetime.fromisoformat(row[8]) if row[8] else None,
                        tags=json.loads(row[9]) if row[9] else [],
                        source_task_id=row[10]
                    )
                    
                    # Avoid duplicates
                    if record.id not in [m.id for m in memories]:
                        memories.append(record)
        
        return memories[:limit]
    
    def _matches_memory_criteria(self, record: MemoryRecord, query: str = "", 
                                context_id: Optional[str] = None, memory_type: Optional[str] = None) -> bool:
        """Check if memory record matches search criteria."""
        if query and query.lower() not in record.content.lower():
            return False
        
        if context_id and record.context_id != context_id:
            return False
        
        if memory_type and record.memory_type != memory_type:
            return False
        
        return True
    
    async def _search_knowledge_nodes(self, query: str = "", node_types: Optional[List[str]] = None, 
                                    limit: int = 20) -> List[KnowledgeNode]:
        """Search knowledge nodes."""
        nodes = []
        
        # Search in cache
        for node in self.knowledge_cache.values():
            if self._matches_node_criteria(node, query, node_types):
                nodes.append(node)
        
        return nodes[:limit]
    
    def _matches_node_criteria(self, node: KnowledgeNode, query: str = "", 
                              node_types: Optional[List[str]] = None) -> bool:
        """Check if knowledge node matches search criteria."""
        if query and query.lower() not in node.content.lower():
            return False
        
        if node_types and node.node_type not in node_types:
            return False
        
        return True
    
    async def _add_knowledge_node(self, node_data: Dict[str, Any]) -> KnowledgeNode:
        """Add a knowledge node."""
        node = KnowledgeNode(
            id=str(uuid.uuid4()),
            content=node_data.get("content", ""),
            node_type=node_data.get("node_type", "general"),
            properties=node_data.get("properties", {})
        )
        
        # Store in database
        if self.db_connection:
            await self.db_connection.execute("""
                INSERT INTO knowledge_nodes (id, content, node_type, properties, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                node.id,
                node.content,
                node.node_type,
                json.dumps(node.properties),
                node.created_at.isoformat()
            ))
            await self.db_connection.commit()
        
        # Add to cache
        self.knowledge_cache[node.id] = node
        
        return node
    
    async def _add_knowledge_edge(self, edge_data: Dict[str, Any]) -> KnowledgeEdge:
        """Add a knowledge edge."""
        edge = KnowledgeEdge(
            id=str(uuid.uuid4()),
            from_node=edge_data.get("from_node", ""),
            to_node=edge_data.get("to_node", ""),
            relationship=edge_data.get("relationship", "related"),
            strength=edge_data.get("strength", 1.0),
            properties=edge_data.get("properties", {})
        )
        
        # Store in database
        if self.db_connection:
            await self.db_connection.execute("""
                INSERT INTO knowledge_edges (id, from_node, to_node, relationship, strength, properties, created_at)  
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                edge.id,
                edge.from_node,
                edge.to_node,
                edge.relationship,
                edge.strength,
                json.dumps(edge.properties),
                edge.created_at.isoformat()
            ))
            await self.db_connection.commit()
        
        # Add to cache
        self.edge_cache[edge.id] = edge
        
        return edge
    
    async def _consolidate_memory(self, force: bool = False) -> Dict[str, Any]:
        """Perform memory consolidation."""
        now = datetime.now()
        time_since_last = (now - self.last_consolidation).total_seconds()
        
        if not force and time_since_last < self.consolidation_interval:
            return {
                "performed": False,
                "reason": f"Too soon since last consolidation ({time_since_last:.0f}s ago)",
                "next_consolidation_in": self.consolidation_interval - time_since_last
            }
        
        # Simple consolidation: remove low-importance, rarely accessed memories
        removed_count = 0
        if self.db_connection:
            # Remove old, low-importance memories
            result = await self.db_connection.execute("""
                DELETE FROM memory_records 
                WHERE importance < ? 
                AND access_count < 2 
                AND datetime(timestamp) < datetime('now', '-30 days')
            """, (self.importance_threshold,))
            
            removed_count = result.rowcount
            await self.db_connection.commit()
        
        # Update last consolidation time
        self.last_consolidation = now
        
        return {
            "performed": True,
            "removed_memories": removed_count,
            "timestamp": now.isoformat()
        }
    
    async def _periodic_consolidation(self):
        """Perform periodic memory consolidation."""
        while self.should_run:
            try:
                await asyncio.sleep(self.consolidation_interval)
                if self.should_run:
                    await self._consolidate_memory()
            except Exception as e:
                logger.error(f"Error in periodic consolidation: {e}")
    
    def _memory_to_dict(self, record: MemoryRecord) -> Dict[str, Any]:
        """Convert memory record to dictionary."""
        return {
            "id": record.id,
            "context_id": record.context_id,
            "content": record.content,
            "memory_type": record.memory_type,
            "metadata": record.metadata,
            "timestamp": record.timestamp.isoformat(),
            "importance": record.importance,
            "access_count": record.access_count,
            "last_accessed": record.last_accessed.isoformat() if record.last_accessed else None,
            "tags": record.tags,
            "source_task_id": record.source_task_id
        }
    
    def _node_to_dict(self, node: KnowledgeNode) -> Dict[str, Any]:
        """Convert knowledge node to dictionary."""
        return {
            "id": node.id,
            "content": node.content,
            "node_type": node.node_type,
            "properties": node.properties,
            "created_at": node.created_at.isoformat()
        }
    
    async def _get__status(self) -> Dict[str, Any]:
        """Get current  status."""
        return {
            "_id": self._id,
            "_type": self._type,
            "status": "ready" if self.mcp_connected else "disconnected",
            "capabilities": self.capabilities,
            "timestamp": datetime.now().isoformat(),
            "mcp_connected": self.mcp_connected,
            "memory_cache_size": len(self.memory_cache),
            "knowledge_nodes": len(self.knowledge_cache),
            "knowledge_edges": len(self.edge_cache),
            "last_consolidation": self.last_consolidation.isoformat(),
            "file_watcher_active": self.file_watcher_task is not None and not self.file_watcher_task.done() if self.file_watcher_task else False,
            "watch_paths": self.watch_paths,
            "timestamp": datetime.now().isoformat()
        }


# Global service instance
memory_service: Optional[MemoryService] = None


def get_mcp_status() -> Dict[str, Any]:
    """Get MCP connection status for health check."""
    if memory_service:
        return {
            "connected": memory_service.mcp_connected,
            "last_heartbeat": datetime.now().isoformat()
        }
    return {"connected": False, "last_heartbeat": "never"}


def get_additional_metadata() -> Dict[str, Any]:
    """Get additional metadata for health check."""
    if memory_service:
        return {
            "capabilities": memory_service.capabilities,
            "memory_cache_size": len(memory_service.memory_cache),
            "knowledge_nodes": len(memory_service.knowledge_cache),
            "knowledge_edges": len(memory_service.edge_cache),
            "file_watcher_active": memory_service.file_watcher_task is not None and not memory_service.file_watcher_task.done() if memory_service.file_watcher_task else False,
            "watch_paths_count": len(memory_service.watch_paths),
            "_id": memory_service._id
        }
    return {}


# Create health check only FastAPI application
app = create_health_check_app(
    agent_type="memory",
    agent_id="memory-service",
    version="1.0.0",
    get_mcp_status=get_mcp_status,
    get_additional_metadata=get_additional_metadata
)


async def main():
    """Main entry point for the memory service."""
    global memory_service
    
    try:
        # Load configuration
        config_path = Path("/app/config/config.json")
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
        else:
            config = {
                "service_host": "0.0.0.0",
                "service_port": 8009,
                "mcp_server_url": "ws://mcp-server:9000",
                "max_memory_size": 10000,
                "importance_threshold": 0.3,
                "consolidation_interval": 3600
            }
        
        # Initialize service
        memory_service = MemoryService(config)
        
        # Start FastAPI health check server in background
        config_uvicorn = uvicorn.Config(
            app,
            host=config["service_host"],
            port=config["service_port"],
            log_level="info"
        )
        server = uvicorn.Server(config_uvicorn)
        
        logger.info("🚨 ARCHITECTURE COMPLIANCE: Memory ")
        logger.info("✅ ONLY health check API exposed")
        logger.info("✅ All business operations via MCP protocol exclusively")
        
        # Start server and MCP service concurrently
        await asyncio.gather(
            server.serve(),
            memory_service.start()
        )
        
    except KeyboardInterrupt:
        logger.info("Memory  shutdown requested")
    except Exception as e:
        logger.error(f"Memory  failed: {e}")
        sys.exit(1)
    finally:
        if memory_service:
            await memory_service.stop()


if __name__ == "__main__":
    asyncio.run(main())
