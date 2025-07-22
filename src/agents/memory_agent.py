"""
Memory Agent for context and memory management.

This module provides the MemoryAgent that handles context persistence,
knowledge graph maintenance, and learning from interactions.
"""

import asyncio
import logging
import json
import sqlite3
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path
import aiosqlite
from dataclasses import dataclass, field

from .base_agent import BaseAgent, AgentStatus
from ..mcp.protocols import ResearchAction, StoreMemoryRequest, QueryMemoryRequest
from ..config.config_manager import ConfigManager


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


class MemoryAgent(BaseAgent):
    """
    Memory Agent for context and memory management.
    
    This agent handles:
    - Context persistence across sessions
    - Knowledge graph maintenance
    - Previous conversation recall
    - Learning from interactions
    - Memory consolidation and pruning
    - Semantic search in memory
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the Memory Agent.
        
        Args:
            config_manager: Configuration manager instance
        """
        super().__init__("memory", config_manager)
        
        # Memory configuration
        self.memory_db_path = Path("data/memory.db")
        self.max_memory_size = 10000  # Maximum number of memory records
        self.importance_threshold = 0.3  # Minimum importance for long-term storage
        self.consolidation_interval = 3600  # 1 hour in seconds
        
        # Knowledge graph configuration
        self.max_graph_nodes = 5000
        self.max_graph_edges = 10000
        self.edge_decay_rate = 0.95  # Strength decay per consolidation cycle
        
        # Database connection
        self.db_connection: Optional[aiosqlite.Connection] = None
        
        # In-memory caches
        self.memory_cache: Dict[str, MemoryRecord] = {}
        self.knowledge_cache: Dict[str, KnowledgeNode] = {}
        self.edge_cache: Dict[str, KnowledgeEdge] = {}
        
        # Last consolidation time
        self.last_consolidation = datetime.now()
        
        self.logger.info("MemoryAgent initialized")
    
    def _get_capabilities(self) -> List[str]:
        """Get memory agent capabilities."""
        return [
            'store_memory',
            'retrieve_memory',
            'search_memory',
            'update_memory',
            'delete_memory',
            'add_knowledge',
            'query_knowledge',
            'find_connections',
            'consolidate_memory',
            'store_structured_memory',  # New enhanced capability
            'query_structured_memory'   # New enhanced capability
        ]
    
    async def _initialize_agent(self) -> None:
        """Initialize memory-specific resources."""
        # Ensure data directory exists
        self.memory_db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        await self._initialize_database()
        
        # Load recent memories into cache
        await self._load_memory_cache()
        
        # Load knowledge graph into cache
        await self._load_knowledge_cache()
        
        self.logger.info(f"MemoryAgent initialized with {len(self.memory_cache)} cached memories")
    
    async def _cleanup_agent(self) -> None:
        """Clean up memory-specific resources."""
        # Close database connection
        if self.db_connection:
            await self.db_connection.close()
        
        # Clear caches
        self.memory_cache.clear()
        self.knowledge_cache.clear()
        self.edge_cache.clear()
        
        self.logger.info("MemoryAgent cleanup completed")
    
    async def _process_task_impl(self, task: ResearchAction) -> Dict[str, Any]:
        """
        Process a memory task.
        
        Args:
            task: Research task to process
            
        Returns:
            Dict[str, Any]: Memory operation results
        """
        action = task.action
        payload = task.payload
        
        # Check if consolidation is needed
        await self._check_consolidation_needed()
        
        if action == 'store_memory':
            return await self._store_memory(payload)
        elif action == 'retrieve_memory':
            return await self._retrieve_memory(payload)
        elif action == 'search_memory':
            return await self._search_memory(payload)
        elif action == 'update_memory':
            return await self._update_memory(payload)
        elif action == 'delete_memory':
            return await self._delete_memory(payload)
        elif action == 'add_knowledge':
            return await self._add_knowledge(payload)
        elif action == 'query_knowledge':
            return await self._query_knowledge(payload)
        elif action == 'find_connections':
            return await self._find_connections(payload)
        elif action == 'consolidate_memory':
            return await self._consolidate_memory(payload)
        elif action == 'store_structured_memory':
            return await self._store_structured_memory(payload)
        elif action == 'query_structured_memory':
            return await self._query_structured_memory(payload)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _store_memory(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store a memory record.
        
        Args:
            payload: Memory storage parameters
            
        Returns:
            Dict[str, Any]: Storage results
        """
        context_id = payload.get('context_id', '')
        content = payload.get('content', '')
        metadata = payload.get('metadata', {})
        importance = payload.get('importance', 0.5)
        
        if not content:
            raise ValueError("Content is required for memory storage")
        
        # Generate memory ID
        memory_id = f"mem_{asyncio.get_event_loop().time()}_{hash(content) % 10000}"
        
        # Create memory record
        record = MemoryRecord(
            id=memory_id,
            context_id=context_id,
            content=content,
            metadata=metadata,
            importance=importance,
            timestamp=datetime.now()
        )
        
        try:
            # Store in database
            await self._insert_memory_record(record)
            
            # Add to cache if important enough
            if importance >= self.importance_threshold:
                self.memory_cache[memory_id] = record
            
            return {
                'success': True,
                'memory_id': memory_id,
                'importance': importance,
                'cached': importance >= self.importance_threshold
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'memory_id': memory_id
            }
    
    async def _retrieve_memory(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve specific memory records.
        
        Args:
            payload: Memory retrieval parameters
            
        Returns:
            Dict[str, Any]: Retrieved memories
        """
        memory_id = payload.get('memory_id', '')
        context_id = payload.get('context_id', '')
        limit = payload.get('limit', 10)
        
        try:
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
                'success': True,
                'memories': [self._memory_to_dict(m) for m in memories],
                'count': len(memories)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'memories': [],
                'count': 0
            }
    
    async def _search_memory(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search memories by content.
        
        Args:
            payload: Search parameters
            
        Returns:
            Dict[str, Any]: Search results
        """
        query = payload.get('query', '')
        limit = payload.get('limit', 10)
        min_importance = payload.get('min_importance', 0.0)
        
        if not query:
            raise ValueError("Query is required for memory search")
        
        try:
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
                'success': True,
                'results': [self._memory_to_dict(m) for m in sorted_results],
                'count': len(sorted_results),
                'query': query
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'results': [],
                'count': 0,
                'query': query
            }
    
    async def _update_memory(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Update memory record."""
        memory_id = payload.get('memory_id', '')
        updates = payload.get('updates', {})
        
        if not memory_id:
            raise ValueError("Memory ID is required for update")
        
        try:
            # Update in cache if present
            if memory_id in self.memory_cache:
                memory = self.memory_cache[memory_id]
                for key, value in updates.items():
                    if hasattr(memory, key):
                        setattr(memory, key, value)
            
            # Update in database
            await self._update_memory_db(memory_id, updates)
            
            return {
                'success': True,
                'memory_id': memory_id,
                'updates': updates
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'memory_id': memory_id
            }
    
    async def _delete_memory(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Delete memory record."""
        memory_id = payload.get('memory_id', '')
        
        if not memory_id:
            raise ValueError("Memory ID is required for deletion")
        
        try:
            # Remove from cache
            if memory_id in self.memory_cache:
                del self.memory_cache[memory_id]
            
            # Remove from database
            await self._delete_memory_db(memory_id)
            
            return {
                'success': True,
                'memory_id': memory_id
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'memory_id': memory_id
            }
    
    async def _add_knowledge(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Add knowledge to the graph."""
        content = payload.get('content', '')
        node_type = payload.get('node_type', 'concept')
        properties = payload.get('properties', {})
        connections = payload.get('connections', [])
        
        if not content:
            raise ValueError("Content is required for knowledge addition")
        
        try:
            # Generate node ID
            node_id = f"node_{asyncio.get_event_loop().time()}_{hash(content) % 10000}"
            
            # Create knowledge node
            node = KnowledgeNode(
                id=node_id,
                content=content,
                node_type=node_type,
                properties=properties
            )
            
            # Store node
            await self._insert_knowledge_node(node)
            self.knowledge_cache[node_id] = node
            
            # Create connections
            edges_created = []
            for connection in connections:
                edge = await self._create_knowledge_edge(
                    node_id,
                    connection.get('to_node', ''),
                    connection.get('relationship', 'related'),
                    connection.get('strength', 1.0)
                )
                if edge:
                    edges_created.append(edge.id)
            
            return {
                'success': True,
                'node_id': node_id,
                'edges_created': edges_created
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'node_id': None
            }
    
    async def _query_knowledge(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Query the knowledge graph."""
        query = payload.get('query', '')
        query_type = payload.get('type', 'search')  # search, neighbors, path
        limit = payload.get('limit', 10)
        
        try:
            if query_type == 'search':
                results = await self._search_knowledge_nodes(query, limit)
            elif query_type == 'neighbors':
                node_id = payload.get('node_id', '')
                results = await self._get_knowledge_neighbors(node_id, limit)
            elif query_type == 'path':
                from_node = payload.get('from_node', '')
                to_node = payload.get('to_node', '')
                results = await self._find_knowledge_path(from_node, to_node)
            else:
                raise ValueError(f"Unknown query type: {query_type}")
            
            return {
                'success': True,
                'results': results,
                'count': len(results) if isinstance(results, list) else 1,
                'query_type': query_type
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'results': [],
                'count': 0,
                'query_type': query_type
            }
    
    async def _find_connections(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Find connections between concepts."""
        concepts = payload.get('concepts', [])
        max_depth = payload.get('max_depth', 3)
        
        if len(concepts) < 2:
            raise ValueError("At least 2 concepts are required to find connections")
        
        try:
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
                                node1.get('id', ''),
                                node2.get('id', ''),
                                max_depth
                            )
                            if path:
                                connections.append({
                                    'from_concept': concept1,
                                    'to_concept': concept2,
                                    'path': path
                                })
            
            return {
                'success': True,
                'connections': connections,
                'count': len(connections)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'connections': [],
                'count': 0
            }
    
    async def _consolidate_memory(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Consolidate and prune memory."""
        force = payload.get('force', False)
        
        if not force and not self._consolidation_needed():
            return {
                'success': True,
                'message': 'Consolidation not needed',
                'memories_pruned': 0,
                'edges_decayed': 0
            }
        
        try:
            # Prune low-importance memories
            pruned_count = await self._prune_memories()
            
            # Decay edge strengths
            decayed_count = await self._decay_edge_strengths()
            
            # Update consolidation timestamp
            self.last_consolidation = datetime.now()
            
            return {
                'success': True,
                'message': 'Consolidation completed',
                'memories_pruned': pruned_count,
                'edges_decayed': decayed_count
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'memories_pruned': 0,
                'edges_decayed': 0
            }
    
    async def _store_structured_memory(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store structured memory with enhanced metadata and categorization.
        
        Args:
            payload: Enhanced memory storage parameters
            
        Returns:
            Dict[str, Any]: Storage results
        """
        try:
            # Parse payload - support both direct dict and StoreMemoryRequest
            if isinstance(payload, dict):
                context_id = payload.get('context_id', '')
                memory_type = payload.get('memory_type', 'general')
                content = payload.get('content', '')
                metadata = payload.get('metadata', {})
                importance = payload.get('importance', 0.5)
                tags = payload.get('tags', [])
                source_task_id = payload.get('source_task_id')
            else:
                # Assume it's a StoreMemoryRequest object
                context_id = payload.context_id
                memory_type = payload.memory_type
                content = payload.content
                metadata = payload.metadata
                importance = payload.importance
                tags = payload.tags
                source_task_id = payload.source_task_id
            
            if not content:
                raise ValueError("Content is required for memory storage")
            
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
            
            self.logger.info(f"Stored structured memory: {memory_type} - {memory_id}")
            
            return {
                'success': True,
                'memory_id': memory_id,
                'memory_type': memory_type,
                'importance': importance,
                'cached': importance >= self.importance_threshold,
                'tags': tags
            }
            
        except Exception as e:
            self.logger.error(f"Failed to store structured memory: {e}")
            return {
                'success': False,
                'error': str(e),
                'memory_id': None
            }
    
    async def _query_structured_memory(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Query memories with structured filters and enhanced search.
        
        Args:
            payload: Query parameters
            
        Returns:
            Dict[str, Any]: Query results
        """
        try:
            # Parse query parameters
            context_id = payload.get('context_id')
            memory_type = payload.get('memory_type')
            query = payload.get('query', '')
            tags = payload.get('tags', [])
            limit = payload.get('limit', 10)
            min_importance = payload.get('min_importance', 0.0)
            time_range = payload.get('time_range')
            
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
                params.extend([f'%{query}%', f'%{query}%'])
            
            if min_importance > 0:
                where_conditions.append("importance >= ?")
                params.append(min_importance)
            
            if time_range:
                if time_range.get('start'):
                    where_conditions.append("timestamp >= ?")
                    params.append(time_range['start'])
                if time_range.get('end'):
                    where_conditions.append("timestamp <= ?")
                    params.append(time_range['end'])
            
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
                return {
                    'success': False,
                    'error': 'Database not connected',
                    'results': [],
                    'count': 0
                }
            
            async with self.db_connection.execute(base_query, params) as cursor:
                async for row in cursor:
                    memory = self._row_to_memory(row)
                    results.append(memory)
                    
                    # Update access count
                    await self._update_access_count(memory.id)
            
            # Convert to dict format
            result_dicts = [self._memory_to_dict(m) for m in results]
            
            return {
                'success': True,
                'results': result_dicts,
                'count': len(result_dicts),
                'query_params': {
                    'context_id': context_id,
                    'memory_type': memory_type,
                    'query': query,
                    'tags': tags,
                    'limit': limit,
                    'min_importance': min_importance
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to query structured memory: {e}")
            return {
                'success': False,
                'error': str(e),
                'results': [],
                'count': 0
            }
    
    async def _initialize_database(self) -> None:
        """Initialize the enhanced memory database."""
        self.db_connection = await aiosqlite.connect(str(self.memory_db_path))
        
        # Create enhanced memories table
        await self.db_connection.execute('''
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
        ''')
        
        await self.db_connection.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_nodes (
                id TEXT PRIMARY KEY,
                content TEXT,
                node_type TEXT,
                properties TEXT,
                created_at DATETIME
            )
        ''')
        
        await self.db_connection.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_edges (
                id TEXT PRIMARY KEY,
                from_node TEXT,
                to_node TEXT,
                relationship TEXT,
                strength REAL,
                properties TEXT,
                created_at DATETIME
            )
        ''')
        
        # Create enhanced indexes for better query performance
        await self.db_connection.execute('''
            CREATE INDEX IF NOT EXISTS idx_memories_context 
            ON memories(context_id)
        ''')
        
        await self.db_connection.execute('''
            CREATE INDEX IF NOT EXISTS idx_memories_type 
            ON memories(memory_type)
        ''')
        
        await self.db_connection.execute('''
            CREATE INDEX IF NOT EXISTS idx_memories_importance 
            ON memories(importance)
        ''')
        
        await self.db_connection.execute('''
            CREATE INDEX IF NOT EXISTS idx_memories_timestamp 
            ON memories(timestamp)
        ''')
        
        await self.db_connection.execute('''
            CREATE INDEX IF NOT EXISTS idx_memories_tags 
            ON memories(tags)
        ''')
        
        await self.db_connection.execute('''
            CREATE INDEX IF NOT EXISTS idx_memories_source_task 
            ON memories(source_task_id)
        ''')
        
        await self.db_connection.execute('''
            CREATE INDEX IF NOT EXISTS idx_knowledge_nodes_content 
            ON knowledge_nodes(content)
        ''')
        
        await self.db_connection.commit()
    
    async def _load_memory_cache(self) -> None:
        """Load recent high-importance memories into cache."""
        if not self.db_connection:
            return
        
        async with self.db_connection.execute('''
            SELECT * FROM memories 
            WHERE importance >= ? 
            ORDER BY timestamp DESC 
            LIMIT 100
        ''', (self.importance_threshold,)) as cursor:
            async for row in cursor:
                memory = self._row_to_memory(row)
                self.memory_cache[memory.id] = memory
    
    async def _load_knowledge_cache(self) -> None:
        """Load knowledge graph into cache."""
        if not self.db_connection:
            return
        
        # Load nodes
        async with self.db_connection.execute('''
            SELECT * FROM knowledge_nodes 
            ORDER BY created_at DESC 
            LIMIT 1000
        ''') as cursor:
            async for row in cursor:
                node = self._row_to_knowledge_node(row)
                self.knowledge_cache[node.id] = node
        
        # Load edges
        async with self.db_connection.execute('''
            SELECT * FROM knowledge_edges 
            WHERE strength > 0.1 
            ORDER BY created_at DESC 
            LIMIT 2000
        ''') as cursor:
            async for row in cursor:
                edge = self._row_to_knowledge_edge(row)
                self.edge_cache[edge.id] = edge
    
    def _memory_to_dict(self, memory: MemoryRecord) -> Dict[str, Any]:
        """Convert memory record to dictionary."""
        return {
            'id': memory.id,
            'context_id': memory.context_id,
            'content': memory.content,
            'memory_type': memory.memory_type,
            'metadata': memory.metadata,
            'importance': memory.importance,
            'access_count': memory.access_count,
            'timestamp': memory.timestamp.isoformat(),
            'last_accessed': memory.last_accessed.isoformat() if memory.last_accessed else None,
            'tags': memory.tags,
            'source_task_id': memory.source_task_id
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
            # Fallback for malformed rows
            self.logger.warning(f"Error parsing memory row: {e}")
            return MemoryRecord(
                id=str(row[0]) if len(row) > 0 else "unknown",
                context_id=str(row[1]) if len(row) > 1 else "unknown",
                content=str(row[2]) if len(row) > 2 else "",
                memory_type="general",
                metadata={},
                importance=0.5,
                access_count=0,
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
    
    async def _insert_memory_record(self, record: MemoryRecord) -> None:
        """Insert memory record into database."""
        if not self.db_connection:
            return
        
        await self.db_connection.execute('''
            INSERT INTO memories 
            (id, context_id, content, memory_type, metadata, importance, access_count, timestamp, last_accessed, tags, source_task_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
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
            if (memory.importance >= min_importance and 
                query_lower in memory.content.lower()):
                results.append(memory)
        
        return results
    
    async def _search_memory_db(self, query: str, limit: int, min_importance: float) -> List[MemoryRecord]:
        """Search memory database."""
        if not self.db_connection:
            return []
        
        results = []
        
        async with self.db_connection.execute('''
            SELECT * FROM memories 
            WHERE content LIKE ? AND importance >= ?
            ORDER BY importance DESC, access_count DESC
            LIMIT ?
        ''', (f'%{query}%', min_importance, limit)) as cursor:
            async for row in cursor:
                results.append(self._row_to_memory(row))
        
        return results
    
    async def _check_consolidation_needed(self) -> None:
        """Check if memory consolidation is needed."""
        if self._consolidation_needed():
            await self._consolidate_memory({'force': True})
    
    def _consolidation_needed(self) -> bool:
        """Check if consolidation is needed."""
        time_since_last = (datetime.now() - self.last_consolidation).total_seconds()
        return time_since_last > self.consolidation_interval
    
    async def _prune_memories(self) -> int:
        """Prune low-importance memories."""
        # TODO: Implement memory pruning based on importance and access patterns
        return 0
    
    async def _decay_edge_strengths(self) -> int:
        """Decay knowledge graph edge strengths."""
        # TODO: Implement edge strength decay over time
        return 0
    
    async def _get_memory_from_db(self, memory_id: str) -> Optional[MemoryRecord]:
        """Get memory from database."""
        if not self.db_connection:
            return None
        
        try:
            async with self.db_connection.execute(
                'SELECT * FROM memories WHERE id = ?', (memory_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_memory(row)
        except Exception as e:
            self.logger.error(f"Failed to get memory {memory_id}: {e}")
        
        return None
    
    async def _get_memories_by_context(self, context_id: str, limit: int) -> List[MemoryRecord]:
        """Get memories by context."""
        if not self.db_connection:
            return []
        
        memories = []
        try:
            async with self.db_connection.execute('''
                SELECT * FROM memories 
                WHERE context_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (context_id, limit)) as cursor:
                async for row in cursor:
                    memories.append(self._row_to_memory(row))
        except Exception as e:
            self.logger.error(f"Failed to get memories by context {context_id}: {e}")
        
        return memories
    
    async def _get_recent_memories(self, limit: int) -> List[MemoryRecord]:
        """Get recent memories."""
        if not self.db_connection:
            return []
        
        memories = []
        try:
            async with self.db_connection.execute('''
                SELECT * FROM memories 
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,)) as cursor:
                async for row in cursor:
                    memories.append(self._row_to_memory(row))
        except Exception as e:
            self.logger.error(f"Failed to get recent memories: {e}")
        
        return memories
    
    async def _update_access_count(self, memory_id: str) -> None:
        """Update memory access count."""
        try:
            # Update in cache if present
            if memory_id in self.memory_cache:
                self.memory_cache[memory_id].access_count += 1
                self.memory_cache[memory_id].last_accessed = datetime.now()
            
            # Update in database
            if self.db_connection:
                await self.db_connection.execute('''
                    UPDATE memories 
                    SET access_count = access_count + 1, last_accessed = ?
                    WHERE id = ?
                ''', (datetime.now().isoformat(), memory_id))
                await self.db_connection.commit()
        except Exception as e:
            self.logger.warning(f"Failed to update access count for {memory_id}: {e}")
    
    async def _update_memory_db(self, memory_id: str, updates: Dict[str, Any]) -> None:
        """Update memory in database."""
        if not self.db_connection:
            return
        
        try:
            # Build dynamic update query
            set_clauses = []
            params = []
            
            for key, value in updates.items():
                if key in ['content', 'memory_type', 'importance', 'source_task_id']:
                    set_clauses.append(f"{key} = ?")
                    params.append(value)
                elif key == 'metadata':
                    set_clauses.append("metadata = ?")
                    params.append(json.dumps(value))
                elif key == 'tags':
                    set_clauses.append("tags = ?")
                    params.append(json.dumps(value))
            
            if set_clauses:
                query = f"UPDATE memories SET {', '.join(set_clauses)} WHERE id = ?"
                params.append(memory_id)
                await self.db_connection.execute(query, params)
                await self.db_connection.commit()
        except Exception as e:
            self.logger.error(f"Failed to update memory {memory_id}: {e}")
    
    async def _delete_memory_db(self, memory_id: str) -> None:
        """Delete memory from database."""
        if not self.db_connection:
            return
        
        try:
            await self.db_connection.execute('DELETE FROM memories WHERE id = ?', (memory_id,))
            await self.db_connection.commit()
        except Exception as e:
            self.logger.error(f"Failed to delete memory {memory_id}: {e}")
    
    async def _insert_knowledge_node(self, node: KnowledgeNode) -> None:
        """Insert knowledge node into database."""
        # Implementation would insert knowledge node
        pass
    
    async def _create_knowledge_edge(self, from_node: str, to_node: str, relationship: str, strength: float) -> Optional[KnowledgeEdge]:
        """Create knowledge edge."""
        # Implementation would create knowledge edge
        return None
    
    async def _search_knowledge_nodes(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search knowledge nodes."""
        # Implementation would search knowledge nodes
        return []
    
    async def _get_knowledge_neighbors(self, node_id: str, limit: int) -> List[Dict[str, Any]]:
        """Get knowledge neighbors."""
        # Implementation would get knowledge neighbors
        return []
    
    async def _find_knowledge_path(self, from_node: str, to_node: str, max_depth: int = 3) -> Optional[List[Dict[str, Any]]]:
        """Find path between knowledge nodes."""
        # Implementation would find path between nodes
        return None
