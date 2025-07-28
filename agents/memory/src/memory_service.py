"""
Memory Agent Service for Eunice Research Platform.

This module provides a containerized Memory Agent that handles:
- Knowledge base management
- Document storage and retrieval  
- Research artifact organization
- Semantic search capabilities
- Memory consolidation and pruning
"""

import asyncio
import json
import logging
import sqlite3
import tempfile
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite
import uvicorn
import websockets
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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


class MemoryAgentService:
    """
    Memory Agent Service for knowledge base management.
    
    Handles memory operations, knowledge graph management,
    and semantic search via MCP protocol.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Memory Agent Service."""
        self.config = config
        self.agent_id = "memory_agent"
        self.agent_type = "memory"
        
        # Service configuration
        self.service_host = config.get("service_host", "0.0.0.0")
        self.service_port = config.get("service_port", 8009)
        self.mcp_server_url = config.get("mcp_server_url", "ws://mcp-server:9000")
        
        # Memory configuration
        self.memory_db_path = Path("/tmp/memory_agent_data/memory.db")
        self.max_memory_size = config.get("max_memory_size", 10000)
        self.importance_threshold = config.get("importance_threshold", 0.3)
        self.consolidation_interval = config.get("consolidation_interval", 3600)
        
        # Knowledge graph configuration
        self.max_graph_nodes = config.get("max_graph_nodes", 5000)
        self.max_graph_edges = config.get("max_graph_edges", 10000)
        self.edge_decay_rate = config.get("edge_decay_rate", 0.95)
        
        # MCP connection
        self.websocket = None
        self.mcp_connected = False
        
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
        
        logger.info(f"Memory Agent Service initialized on port {self.service_port}")
    
    async def start(self):
        """Start the Memory Agent Service."""
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
            
            # Start task processing
            asyncio.create_task(self._process_task_queue())
            
            logger.info("Memory Agent Service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Memory Agent Service: {e}")
            raise
    
    async def stop(self):
        """Stop the Memory Agent Service."""
        try:
            # Close MCP connection
            if self.websocket:
                await self.websocket.close()
            
            # Close database connection
            if self.db_connection:
                await self.db_connection.close()
            
            # Clear caches
            self.memory_cache.clear()
            self.knowledge_cache.clear()
            self.edge_cache.clear()
            
            logger.info("Memory Agent Service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping Memory Agent Service: {e}")
    
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
                
                # Start message handler
                asyncio.create_task(self._handle_mcp_messages())
                
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
        """Register this agent with the MCP server."""
        capabilities = [
            "store_memory",
            "retrieve_memory", 
            "search_memory",
            "update_memory",
            "delete_memory",
            "add_knowledge",
            "query_knowledge",
            "find_connections",
            "consolidate_memory",
            "store_structured_memory",
            "query_structured_memory"
        ]
        
        registration_message = {
            "type": "register",
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": capabilities,
            "service_info": {
                "host": self.service_host,
                "port": self.service_port,
                "health_endpoint": f"http://{self.service_host}:{self.service_port}/health"
            }
        }
        
        await self.websocket.send(json.dumps(registration_message))
        logger.info(f"Registered with MCP server: {len(capabilities)} capabilities")
    
    async def _handle_mcp_messages(self):
        """Handle incoming MCP messages."""
        try:
            while self.websocket:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                if data.get("type") == "task":
                    await self.task_queue.put(data)
                elif data.get("type") == "ping":
                    await self.websocket.send(json.dumps({"type": "pong"}))
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("MCP server connection closed")
            self.mcp_connected = False
        except Exception as e:
            logger.error(f"Error handling MCP messages: {e}")
            self.mcp_connected = False
    
    async def _process_task_queue(self):
        """Process tasks from the MCP queue."""
        while True:
            try:
                # Get task from queue
                task_data = await self.task_queue.get()
                
                # Process the task
                result = await self._process_memory_task(task_data)
                
                # Send result back to MCP server
                if self.websocket and self.mcp_connected:
                    response = {
                        "type": "task_result",
                        "task_id": task_data.get("task_id"),
                        "agent_id": self.agent_id,
                        "result": result
                    }
                    await self.websocket.send(json.dumps(response))
                
                # Mark task as done
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing task: {e}")
                await asyncio.sleep(1)
    
    async def _process_memory_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a memory task."""
        try:
            action = task_data.get("action", "")
            payload = task_data.get("payload", {})
            
            # Check if consolidation is needed
            await self._check_consolidation_needed()
            
            # Route to appropriate handler
            if action == "store_memory":
                return await self._store_memory(payload)
            elif action == "retrieve_memory":
                return await self._retrieve_memory(payload)
            elif action == "search_memory":
                return await self._search_memory(payload)
            elif action == "update_memory":
                return await self._update_memory(payload)
            elif action == "delete_memory":
                return await self._delete_memory(payload)
            elif action == "add_knowledge":
                return await self._add_knowledge(payload)
            elif action == "query_knowledge":
                return await self._query_knowledge(payload)
            elif action == "find_connections":
                return await self._find_connections(payload)
            elif action == "consolidate_memory":
                return await self._consolidate_memory(payload)
            elif action == "store_structured_memory":
                return await self._store_structured_memory(payload)
            elif action == "query_structured_memory":
                return await self._query_structured_memory(payload)
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            logger.error(f"Error processing memory task: {e}")
            return {"success": False, "error": str(e)}
    
    async def _store_memory(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Store a memory record."""
        try:
            context_id = payload.get("context_id", "")
            content = payload.get("content", "")
            metadata = payload.get("metadata", {})
            importance = payload.get("importance", 0.5)
            
            if not content:
                return {"success": False, "error": "Content is required for memory storage"}
            
            # Generate memory ID
            timestamp = datetime.now()
            memory_id = f"mem_{int(timestamp.timestamp())}_{hash(content) % 10000}"
            
            # Create memory record
            record = MemoryRecord(
                id=memory_id,
                context_id=context_id,
                content=content,
                metadata=metadata,
                importance=importance,
                timestamp=timestamp
            )
            
            # Store in database
            await self._insert_memory_record(record)
            
            # Add to cache if important enough
            if importance >= self.importance_threshold:
                self.memory_cache[memory_id] = record
            
            logger.info(f"Stored memory: {memory_id}")
            
            return {
                "success": True,
                "memory_id": memory_id,
                "importance": importance,
                "cached": importance >= self.importance_threshold
            }
            
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            return {"success": False, "error": str(e)}
    
    async def _retrieve_memory(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve specific memory records."""
        try:
            memory_id = payload.get("memory_id", "")
            context_id = payload.get("context_id", "")
            limit = payload.get("limit", 10)
            
            memories = []
            
            if memory_id:
                # Retrieve specific memory
                if memory_id in self.memory_cache:
                    memory = self.memory_cache[memory_id]
                    await self._update_access_count(memory_id)
                    memories.append(memory)
                else:
                    memory = await self._get_memory_from_db(memory_id)
                    if memory:
                        await self._update_access_count(memory_id)
                        memories.append(memory)
            
            elif context_id:
                # Retrieve memories for context
                memories = await self._get_memories_by_context(context_id, limit)
            
            else:
                # Retrieve recent memories
                memories = await self._get_recent_memories(limit)
            
            return {
                "success": True,
                "memories": [self._memory_to_dict(m) for m in memories],
                "count": len(memories)
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve memory: {e}")
            return {"success": False, "error": str(e), "memories": [], "count": 0}
    
    async def _search_memory(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Search memories by content."""
        try:
            query = payload.get("query", "")
            limit = payload.get("limit", 10)
            min_importance = payload.get("min_importance", 0.0)
            
            if not query:
                return {"success": False, "error": "Query is required for memory search"}
            
            # Search in cache first
            cache_results = self._search_memory_cache(query, min_importance)
            
            # Search in database
            db_results = await self._search_memory_db(query, limit, min_importance)
            
            # Combine and deduplicate results
            all_results = {}
            for memory in cache_results + db_results:
                all_results[memory.id] = memory
            
            # Sort by relevance and importance
            sorted_results = sorted(
                all_results.values(),
                key=lambda m: (m.importance, m.access_count),
                reverse=True
            )[:limit]
            
            return {
                "success": True,
                "results": [self._memory_to_dict(m) for m in sorted_results],
                "count": len(sorted_results),
                "query": query
            }
            
        except Exception as e:
            logger.error(f"Failed to search memory: {e}")
            return {"success": False, "error": str(e), "results": [], "count": 0}
    
    async def _update_memory(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Update memory record."""
        try:
            memory_id = payload.get("memory_id", "")
            updates = payload.get("updates", {})
            
            if not memory_id:
                return {"success": False, "error": "Memory ID is required for update"}
            
            # Update in cache if present
            if memory_id in self.memory_cache:
                memory = self.memory_cache[memory_id]
                for key, value in updates.items():
                    if hasattr(memory, key):
                        setattr(memory, key, value)
            
            # Update in database
            await self._update_memory_db(memory_id, updates)
            
            return {"success": True, "memory_id": memory_id, "updates": updates}
            
        except Exception as e:
            logger.error(f"Failed to update memory: {e}")
            return {"success": False, "error": str(e)}
    
    async def _delete_memory(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Delete memory record."""
        try:
            memory_id = payload.get("memory_id", "")
            
            if not memory_id:
                return {"success": False, "error": "Memory ID is required for deletion"}
            
            # Remove from cache
            if memory_id in self.memory_cache:
                del self.memory_cache[memory_id]
            
            # Remove from database
            await self._delete_memory_db(memory_id)
            
            return {"success": True, "memory_id": memory_id}
            
        except Exception as e:
            logger.error(f"Failed to delete memory: {e}")
            return {"success": False, "error": str(e)}
    
    async def _add_knowledge(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Add knowledge to the graph."""
        try:
            content = payload.get("content", "")
            node_type = payload.get("node_type", "concept")
            properties = payload.get("properties", {})
            connections = payload.get("connections", [])
            
            if not content:
                return {"success": False, "error": "Content is required for knowledge addition"}
            
            # Generate node ID
            timestamp = datetime.now()
            node_id = f"node_{int(timestamp.timestamp())}_{hash(content) % 10000}"
            
            # Create knowledge node
            node = KnowledgeNode(
                id=node_id,
                content=content,
                node_type=node_type,
                properties=properties,
                created_at=timestamp
            )
            
            # Store node
            await self._insert_knowledge_node(node)
            self.knowledge_cache[node_id] = node
            
            # Create connections
            edges_created = []
            for connection in connections:
                edge = await self._create_knowledge_edge(
                    node_id,
                    connection.get("to_node", ""),
                    connection.get("relationship", "related"),
                    connection.get("strength", 1.0)
                )
                if edge:
                    edges_created.append(edge.id)
            
            return {"success": True, "node_id": node_id, "edges_created": edges_created}
            
        except Exception as e:
            logger.error(f"Failed to add knowledge: {e}")
            return {"success": False, "error": str(e), "node_id": None}
    
    async def _query_knowledge(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Query the knowledge graph."""
        try:
            query = payload.get("query", "")
            query_type = payload.get("type", "search")  # search, neighbors, path
            limit = payload.get("limit", 10)
            
            if query_type == "search":
                results = await self._search_knowledge_nodes(query, limit)
            elif query_type == "neighbors":
                node_id = payload.get("node_id", "")
                results = await self._get_knowledge_neighbors(node_id, limit)
            elif query_type == "path":
                from_node = payload.get("from_node", "")
                to_node = payload.get("to_node", "")
                results = await self._find_knowledge_path(from_node, to_node)
            else:
                return {"success": False, "error": f"Unknown query type: {query_type}"}
            
            return {
                "success": True,
                "results": results,
                "count": len(results) if isinstance(results, list) else 1,
                "query_type": query_type
            }
            
        except Exception as e:
            logger.error(f"Failed to query knowledge: {e}")
            return {"success": False, "error": str(e), "results": [], "count": 0}
    
    async def _find_connections(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Find connections between concepts."""
        try:
            concepts = payload.get("concepts", [])
            max_depth = payload.get("max_depth", 3)
            
            if len(concepts) < 2:
                return {"success": False, "error": "At least 2 concepts are required to find connections"}
            
            connections = []
            
            for i in range(len(concepts)):
                for j in range(i + 1, len(concepts)):
                    concept1 = concepts[i]
                    concept2 = concepts[j]
                    
                    # Find nodes for concepts
                    nodes1 = await self._search_knowledge_nodes(concept1, 5)
                    nodes2 = await self._search_knowledge_nodes(concept2, 5)
                    
                    # Find paths between nodes
                    for node1 in nodes1:
                        for node2 in nodes2:
                            path = await self._find_knowledge_path(
                                node1.get("id", ""), 
                                node2.get("id", ""), 
                                max_depth
                            )
                            if path:
                                connections.append({
                                    "from_concept": concept1,
                                    "to_concept": concept2,
                                    "path": path
                                })
            
            return {
                "success": True,
                "connections": connections,
                "count": len(connections)
            }
            
        except Exception as e:
            logger.error(f"Failed to find connections: {e}")
            return {"success": False, "error": str(e), "connections": [], "count": 0}
    
    async def _consolidate_memory(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Consolidate and prune memory."""
        try:
            force = payload.get("force", False)
            
            if not force and not self._consolidation_needed():
                return {
                    "success": True,
                    "message": "Consolidation not needed",
                    "memories_pruned": 0,
                    "edges_decayed": 0
                }
            
            # Prune low-importance memories
            pruned_count = await self._prune_memories()
            
            # Decay edge strengths  
            decayed_count = await self._decay_edge_strengths()
            
            # Update consolidation timestamp
            self.last_consolidation = datetime.now()
            
            return {
                "success": True,
                "message": "Consolidation completed",
                "memories_pruned": pruned_count,
                "edges_decayed": decayed_count
            }
            
        except Exception as e:
            logger.error(f"Failed to consolidate memory: {e}")
            return {"success": False, "error": str(e), "memories_pruned": 0, "edges_decayed": 0}
    
    async def _store_structured_memory(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Store structured memory with enhanced metadata."""
        try:
            context_id = payload.get("context_id", "")
            memory_type = payload.get("memory_type", "general")
            content = payload.get("content", "")
            metadata = payload.get("metadata", {})
            importance = payload.get("importance", 0.5)
            tags = payload.get("tags", [])
            source_task_id = payload.get("source_task_id")
            
            if not content:
                return {"success": False, "error": "Content is required for memory storage"}
            
            # Generate memory ID with type prefix
            timestamp = datetime.now()
            memory_id = f"{memory_type}_{int(timestamp.timestamp())}_{hash(content) % 10000}"
            
            # Create enhanced memory record
            record = MemoryRecord(
                id=memory_id,
                context_id=context_id,
                content=content,
                memory_type=memory_type,
                metadata=metadata,
                importance=importance,
                timestamp=timestamp,
                tags=tags,
                source_task_id=source_task_id
            )
            
            # Store in database
            await self._insert_memory_record(record)
            
            # Add to cache if important enough
            if importance >= self.importance_threshold:
                self.memory_cache[memory_id] = record
            
            logger.info(f"Stored structured memory: {memory_type}-{memory_id}")
            
            return {
                "success": True,
                "memory_id": memory_id,
                "memory_type": memory_type,
                "importance": importance,
                "cached": importance >= self.importance_threshold,
                "tags": tags
            }
            
        except Exception as e:
            logger.error(f"Failed to store structured memory: {e}")
            return {"success": False, "error": str(e), "memory_id": None}
    
    async def _query_structured_memory(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Query memories with structured filters."""
        try:
            context_id = payload.get("context_id")
            memory_type = payload.get("memory_type")
            query = payload.get("query", "")
            tags = payload.get("tags", [])
            limit = payload.get("limit", 10)
            min_importance = payload.get("min_importance", 0.0)
            time_range = payload.get("time_range")
            
            # Build SQL query dynamically
            where_conditions = []
            params = []
            
            if context_id:
                where_conditions.append("context_id = ?")
                params.append(context_id)
            
            if memory_type:
                where_conditions.append("memory_type = ?")
                params.append(memory_type)
            
            if query:
                where_conditions.append("(content LIKE ? OR metadata LIKE ?)")
                params.extend([f"%{query}%", f"%{query}%"])
            
            if min_importance > 0:
                where_conditions.append("importance >= ?")
                params.append(min_importance)
            
            if time_range:
                if time_range.get("start"):
                    where_conditions.append("timestamp >= ?")
                    params.append(time_range["start"])
                if time_range.get("end"):
                    where_conditions.append("timestamp <= ?")
                    params.append(time_range["end"])
            
            # Handle tags search
            if tags:
                tag_conditions = []
                for tag in tags:
                    tag_conditions.append("tags LIKE ?")
                    params.append(f'%"{tag}"%')
                if tag_conditions:
                    where_conditions.append(f"({' OR '.join(tag_conditions)})")
            
            # Build full query
            base_query = "SELECT * FROM memories"
            if where_conditions:
                base_query += " WHERE " + " AND ".join(where_conditions)
            base_query += " ORDER BY importance DESC, timestamp DESC LIMIT ?"
            params.append(limit)
            
            # Execute query
            results = []
            if not self.db_connection:
                return {"success": False, "error": "Database not connected", "results": [], "count": 0}
            
            async with self.db_connection.execute(base_query, params) as cursor:
                async for row in cursor:
                    memory = self._row_to_memory(row)
                    results.append(memory)
                    
                    # Update access count
                    await self._update_access_count(memory.id)
            
            # Convert to dict format
            result_dicts = [self._memory_to_dict(m) for m in results]
            
            return {
                "success": True,
                "results": result_dicts,
                "count": len(result_dicts),
                "query_params": {
                    "context_id": context_id,
                    "memory_type": memory_type,
                    "query": query,
                    "tags": tags,
                    "limit": limit,
                    "min_importance": min_importance
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to query structured memory: {e}")
            return {"success": False, "error": str(e), "results": [], "count": 0}
    
    # Database helper methods
    async def _initialize_database(self):
        """Initialize the memory database."""
        self.db_connection = await aiosqlite.connect(str(self.memory_db_path))
        
        # Create enhanced memories table
        await self.db_connection.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                context_id TEXT,
                content TEXT,
                memory_type TEXT DEFAULT 'general',
                metadata TEXT,
                importance REAL,
                access_count INTEGER DEFAULT 0,
                timestamp DATETIME,
                last_accessed DATETIME,
                tags TEXT,
                source_task_id TEXT
            )
        """)
        
        await self.db_connection.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_nodes (
                id TEXT PRIMARY KEY,
                content TEXT,
                node_type TEXT,
                properties TEXT,
                created_at DATETIME
            )
        """)
        
        await self.db_connection.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_edges (
                id TEXT PRIMARY KEY,
                from_node TEXT,
                to_node TEXT,
                relationship TEXT,
                strength REAL,
                properties TEXT,
                created_at DATETIME
            )
        """)
        
        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_memories_context ON memories(context_id)",
            "CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type)",
            "CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance)",
            "CREATE INDEX IF NOT EXISTS idx_memories_timestamp ON memories(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_memories_tags ON memories(tags)",
            "CREATE INDEX IF NOT EXISTS idx_memories_source_task ON memories(source_task_id)",
            "CREATE INDEX IF NOT EXISTS idx_knowledge_nodes_content ON knowledge_nodes(content)"
        ]
        
        for index_query in indexes:
            await self.db_connection.execute(index_query)
        
        await self.db_connection.commit()
        logger.info("Memory database initialized")
    
    async def _load_memory_cache(self):
        """Load recent high-importance memories into cache."""
        if not self.db_connection:
            return
        
        async with self.db_connection.execute("""
            SELECT * FROM memories 
            WHERE importance >= ?
            ORDER BY timestamp DESC 
            LIMIT 100
        """, (self.importance_threshold,)) as cursor:
            async for row in cursor:
                memory = self._row_to_memory(row)
                self.memory_cache[memory.id] = memory
        
        logger.info(f"Loaded {len(self.memory_cache)} memories into cache")
    
    async def _load_knowledge_cache(self):
        """Load knowledge graph into cache."""
        if not self.db_connection:
            return
        
        # Load nodes
        async with self.db_connection.execute("""
            SELECT * FROM knowledge_nodes 
            ORDER BY created_at DESC 
            LIMIT 1000
        """) as cursor:
            async for row in cursor:
                node = self._row_to_knowledge_node(row)
                self.knowledge_cache[node.id] = node
        
        # Load edges
        async with self.db_connection.execute("""
            SELECT * FROM knowledge_edges 
            WHERE strength > 0.1
            ORDER BY created_at DESC 
            LIMIT 2000
        """) as cursor:
            async for row in cursor:
                edge = self._row_to_knowledge_edge(row)
                self.edge_cache[edge.id] = edge
        
        logger.info(f"Loaded {len(self.knowledge_cache)} nodes and {len(self.edge_cache)} edges into cache")
    
    def _memory_to_dict(self, memory: MemoryRecord) -> Dict[str, Any]:
        """Convert memory record to dictionary."""
        return {
            "id": memory.id,
            "context_id": memory.context_id,
            "content": memory.content,
            "memory_type": memory.memory_type,
            "metadata": memory.metadata,
            "importance": memory.importance,
            "access_count": memory.access_count,
            "timestamp": memory.timestamp.isoformat(),
            "last_accessed": memory.last_accessed.isoformat() if memory.last_accessed else None,
            "tags": memory.tags,
            "source_task_id": memory.source_task_id
        }
    
    def _row_to_memory(self, row: Any) -> MemoryRecord:
        """Convert database row to memory record."""
        try:
            return MemoryRecord(
                id=row[0],
                context_id=row[1],
                content=row[2],
                memory_type=row[3] or "general",
                metadata=json.loads(row[4]) if row[4] else {},
                importance=row[5],
                access_count=row[6],
                timestamp=datetime.fromisoformat(row[7]),
                last_accessed=datetime.fromisoformat(row[8]) if row[8] else None,
                tags=json.loads(row[9]) if row[9] else [],
                source_task_id=row[10]
            )
        except (IndexError, ValueError, TypeError) as e:
            logger.warning(f"Error parsing memory row: {e}")
            return MemoryRecord(
                id=str(row[0]) if len(row) > 0 else "unknown",
                context_id=str(row[1]) if len(row) > 1 else "unknown",
                content=str(row[2]) if len(row) > 2 else "",
                memory_type="general",
                metadata={},
                importance=0.5,
                timestamp=datetime.now(),
                tags=[],
                source_task_id=None
            )
    
    def _row_to_knowledge_node(self, row: Any) -> KnowledgeNode:
        """Convert database row to knowledge node."""
        return KnowledgeNode(
            id=row[0],
            content=row[1],
            node_type=row[2],
            properties=json.loads(row[3]) if row[3] else {},
            created_at=datetime.fromisoformat(row[4])
        )
    
    def _row_to_knowledge_edge(self, row: Any) -> KnowledgeEdge:
        """Convert database row to knowledge edge."""
        return KnowledgeEdge(
            id=row[0],
            from_node=row[1],
            to_node=row[2],
            relationship=row[3],
            strength=row[4],
            properties=json.loads(row[5]) if row[5] else {},
            created_at=datetime.fromisoformat(row[6])
        )
    
    async def _insert_memory_record(self, record: MemoryRecord):
        """Insert memory record into database."""
        if not self.db_connection:
            return
        
        await self.db_connection.execute("""
            INSERT INTO memories 
            (id, context_id, content, memory_type, metadata, importance, 
             access_count, timestamp, last_accessed, tags, source_task_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.id,
            record.context_id,
            record.content,
            record.memory_type,
            json.dumps(record.metadata),
            record.importance,
            record.access_count,
            record.timestamp.isoformat(),
            record.last_accessed.isoformat() if record.last_accessed else None,
            json.dumps(record.tags),
            record.source_task_id
        ))
        
        await self.db_connection.commit()
    
    def _search_memory_cache(self, query: str, min_importance: float) -> List[MemoryRecord]:
        """Search memory cache."""
        results = []
        query_lower = query.lower()
        
        for memory in self.memory_cache.values():
            if memory.importance >= min_importance and query_lower in memory.content.lower():
                results.append(memory)
        
        return results
    
    async def _search_memory_db(self, query: str, limit: int, min_importance: float) -> List[MemoryRecord]:
        """Search memory database."""
        if not self.db_connection:
            return []
        
        results = []
        
        async with self.db_connection.execute("""
            SELECT * FROM memories 
            WHERE content LIKE ? AND importance >= ?
            ORDER BY importance DESC, access_count DESC 
            LIMIT ?
        """, (f"%{query}%", min_importance, limit)) as cursor:
            async for row in cursor:
                results.append(self._row_to_memory(row))
        
        return results
    
    async def _check_consolidation_needed(self):
        """Check if memory consolidation is needed."""
        if self._consolidation_needed():
            await self._consolidate_memory({"force": True})
    
    def _consolidation_needed(self) -> bool:
        """Check if consolidation is needed."""
        time_since_last = (datetime.now() - self.last_consolidation).total_seconds()
        return time_since_last > self.consolidation_interval
    
    async def _prune_memories(self) -> int:
        """Prune low-importance memories."""
        # Simple implementation - remove memories below threshold
        if not self.db_connection:
            return 0
        
        cursor = await self.db_connection.execute("""
            DELETE FROM memories 
            WHERE importance < ? AND access_count < 3
        """, (self.importance_threshold * 0.5,))
        
        deleted = cursor.rowcount
        await self.db_connection.commit()
        
        return deleted
    
    async def _decay_edge_strengths(self) -> int:
        """Decay knowledge graph edge strengths."""
        if not self.db_connection:
            return 0
        
        cursor = await self.db_connection.execute("""
            UPDATE knowledge_edges 
            SET strength = strength * ?
            WHERE strength > 0.1
        """, (self.edge_decay_rate,))
        
        updated = cursor.rowcount
        await self.db_connection.commit()
        
        return updated
    
    # Additional helper methods for database operations
    async def _get_memory_from_db(self, memory_id: str) -> Optional[MemoryRecord]:
        """Get memory from database."""
        if not self.db_connection:
            return None
        
        async with self.db_connection.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return self._row_to_memory(row)
        
        return None
    
    async def _get_memories_by_context(self, context_id: str, limit: int) -> List[MemoryRecord]:
        """Get memories by context."""
        if not self.db_connection:
            return []
        
        memories = []
        async with self.db_connection.execute("""
            SELECT * FROM memories 
            WHERE context_id = ?
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (context_id, limit)) as cursor:
            async for row in cursor:
                memories.append(self._row_to_memory(row))
        
        return memories
    
    async def _get_recent_memories(self, limit: int) -> List[MemoryRecord]:
        """Get recent memories."""
        if not self.db_connection:
            return []
        
        memories = []
        async with self.db_connection.execute("""
            SELECT * FROM memories 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,)) as cursor:
            async for row in cursor:
                memories.append(self._row_to_memory(row))
        
        return memories
    
    async def _update_access_count(self, memory_id: str):
        """Update memory access count."""
        try:
            # Update in cache if present
            if memory_id in self.memory_cache:
                self.memory_cache[memory_id].access_count += 1
                self.memory_cache[memory_id].last_accessed = datetime.now()
            
            # Update in database
            if self.db_connection:
                await self.db_connection.execute("""
                    UPDATE memories 
                    SET access_count = access_count + 1, last_accessed = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), memory_id))
                await self.db_connection.commit()
        except Exception as e:
            logger.warning(f"Failed to update access count for {memory_id}: {e}")
    
    async def _update_memory_db(self, memory_id: str, updates: Dict[str, Any]):
        """Update memory in database."""
        if not self.db_connection:
            return
        
        # Build dynamic update query
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            if key in ["content", "memory_type", "importance", "source_task_id"]:
                set_clauses.append(f"{key} = ?")
                params.append(value)
            elif key == "metadata":
                set_clauses.append("metadata = ?")
                params.append(json.dumps(value))
            elif key == "tags":
                set_clauses.append("tags = ?")
                params.append(json.dumps(value))
        
        if set_clauses:
            query = f"UPDATE memories SET {', '.join(set_clauses)} WHERE id = ?"
            params.append(memory_id)
            await self.db_connection.execute(query, params)
            await self.db_connection.commit()
    
    async def _delete_memory_db(self, memory_id: str):
        """Delete memory from database."""
        if not self.db_connection:
            return
        
        await self.db_connection.execute(
            "DELETE FROM memories WHERE id = ?", (memory_id,)
        )
        await self.db_connection.commit()
    
    async def _insert_knowledge_node(self, node: KnowledgeNode):
        """Insert knowledge node into database."""
        if not self.db_connection:
            return
        
        await self.db_connection.execute("""
            INSERT INTO knowledge_nodes 
            (id, content, node_type, properties, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            node.id,
            node.content,
            node.node_type,
            json.dumps(node.properties),
            node.created_at.isoformat()
        ))
        
        await self.db_connection.commit()
    
    async def _create_knowledge_edge(self, from_node: str, to_node: str, relationship: str, strength: float) -> Optional[KnowledgeEdge]:
        """Create knowledge edge."""
        if not self.db_connection or not to_node:
            return None
        
        timestamp = datetime.now()
        edge_id = f"edge_{int(timestamp.timestamp())}_{hash(f'{from_node}-{to_node}') % 10000}"
        
        edge = KnowledgeEdge(
            id=edge_id,
            from_node=from_node,
            to_node=to_node,
            relationship=relationship,
            strength=strength,
            created_at=timestamp
        )
        
        await self.db_connection.execute("""
            INSERT INTO knowledge_edges 
            (id, from_node, to_node, relationship, strength, properties, created_at)
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
        self.edge_cache[edge.id] = edge
        
        return edge
    
    async def _search_knowledge_nodes(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search knowledge nodes."""
        if not self.db_connection:
            return []
        
        results = []
        async with self.db_connection.execute("""
            SELECT * FROM knowledge_nodes 
            WHERE content LIKE ?
            ORDER BY created_at DESC 
            LIMIT ?
        """, (f"%{query}%", limit)) as cursor:
            async for row in cursor:
                node = self._row_to_knowledge_node(row)
                results.append({
                    "id": node.id,
                    "content": node.content,
                    "node_type": node.node_type,
                    "properties": node.properties,
                    "created_at": node.created_at.isoformat()
                })
        
        return results
    
    async def _get_knowledge_neighbors(self, node_id: str, limit: int) -> List[Dict[str, Any]]:
        """Get knowledge neighbors."""
        if not self.db_connection:
            return []
        
        results = []
        async with self.db_connection.execute("""
            SELECT n.*, e.relationship, e.strength 
            FROM knowledge_nodes n 
            JOIN knowledge_edges e ON (n.id = e.to_node OR n.id = e.from_node)
            WHERE (e.from_node = ? OR e.to_node = ?) AND n.id != ?
            ORDER BY e.strength DESC 
            LIMIT ?
        """, (node_id, node_id, node_id, limit)) as cursor:
            async for row in cursor:
                results.append({
                    "id": row[0],
                    "content": row[1],
                    "node_type": row[2],
                    "properties": json.loads(row[3]) if row[3] else {},
                    "created_at": row[4],
                    "relationship": row[5],
                    "strength": row[6]
                })
        
        return results
    
    async def _find_knowledge_path(self, from_node: str, to_node: str, max_depth: int = 3) -> Optional[List[Dict[str, Any]]]:
        """Find path between knowledge nodes."""
        # Simple breadth-first search implementation
        if not self.db_connection or from_node == to_node:
            return None
        
        visited = set()
        queue = [(from_node, [from_node])]
        
        while queue and len(queue[0][1]) <= max_depth:
            current_node, path = queue.pop(0)
            
            if current_node in visited:
                continue
            
            visited.add(current_node)
            
            if current_node == to_node:
                # Found path - convert to dict format
                path_details = []
                for node_id in path:
                    async with self.db_connection.execute(
                        "SELECT * FROM knowledge_nodes WHERE id = ?", (node_id,)
                    ) as cursor:
                        row = await cursor.fetchone()
                        if row:
                            path_details.append({
                                "id": row[0],
                                "content": row[1],
                                "node_type": row[2]
                            })
                return path_details
            
            # Get neighbors
            async with self.db_connection.execute("""
                SELECT CASE 
                    WHEN from_node = ? THEN to_node 
                    ELSE from_node 
                END as neighbor
                FROM knowledge_edges 
                WHERE (from_node = ? OR to_node = ?) AND strength > 0.1
            """, (current_node, current_node, current_node)) as cursor:
                async for row in cursor:
                    neighbor = row[0]
                    if neighbor not in visited:
                        queue.append((neighbor, path + [neighbor]))
        
        return None


# Request/Response models for FastAPI
class TaskRequest(BaseModel):
    action: str
    payload: Dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    agent_type: str
    mcp_connected: bool
    capabilities: List[str]
    memory_cache_size: int
    knowledge_cache_size: int
    database_path: str


# Global service instance
memory_service: Optional[MemoryAgentService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global memory_service
    
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
            "consolidation_interval": 3600,
            "max_graph_nodes": 5000,
            "max_graph_edges": 10000,
            "edge_decay_rate": 0.95
        }
    
    # Start service
    memory_service = MemoryAgentService(config)
    await memory_service.start()
    
    try:
        yield
    finally:
        # Cleanup
        if memory_service:
            await memory_service.stop()


# FastAPI application
app = FastAPI(
    title="Memory Agent Service",
    description="Memory Agent for knowledge base management and semantic search",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    if not memory_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    capabilities = [
        "store_memory",
        "retrieve_memory", 
        "search_memory",
        "update_memory",
        "delete_memory",
        "add_knowledge",
        "query_knowledge",
        "find_connections",
        "consolidate_memory",
        "store_structured_memory",
        "query_structured_memory"
    ]
    
    return HealthResponse(
        status="healthy",
        agent_type="memory",
        mcp_connected=memory_service.mcp_connected,
        capabilities=capabilities,
        memory_cache_size=len(memory_service.memory_cache),
        knowledge_cache_size=len(memory_service.knowledge_cache),
        database_path=str(memory_service.memory_db_path)
    )


@app.post("/task")
async def process_task(request: TaskRequest):
    """Process a memory task directly (for testing)."""
    if not memory_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        result = await memory_service._process_memory_task({
            "action": request.action,
            "payload": request.payload
        })
        return result
    except Exception as e:
        logger.error(f"Error processing task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "memory_service:app",
        host="0.0.0.0",
        port=8009,
        log_level="info"
    )
