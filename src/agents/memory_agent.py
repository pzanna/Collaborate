"""
Memory Agent for context and memory management.

This module provides the MemoryAgent that handles context persistence,
knowledge graph maintenance, and learning from interactions.
"""

import asyncio
import logging
import json
import sqlite3
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import aiosqlite
from dataclasses import dataclass, field

from .base_agent import BaseAgent, AgentStatus
from ..mcp.protocols import ResearchAction
from ..config.config_manager import ConfigManager


@dataclass
class MemoryRecord:
    """Memory record structure."""
    id: str
    context_id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    importance: float = 0.5
    access_count: int = 0
    last_accessed: Optional[datetime] = None


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
            'consolidate_memory'
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
    
    async def _initialize_database(self) -> None:
        """Initialize the memory database."""
        self.db_connection = await aiosqlite.connect(str(self.memory_db_path))
        
        # Create tables
        await self.db_connection.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                context_id TEXT,
                content TEXT,
                metadata TEXT,
                importance REAL,
                access_count INTEGER DEFAULT 0,
                timestamp DATETIME,
                last_accessed DATETIME
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
        
        # Create indexes
        await self.db_connection.execute('''
            CREATE INDEX IF NOT EXISTS idx_memories_context 
            ON memories(context_id)
        ''')
        
        await self.db_connection.execute('''
            CREATE INDEX IF NOT EXISTS idx_memories_importance 
            ON memories(importance)
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
            'metadata': memory.metadata,
            'importance': memory.importance,
            'access_count': memory.access_count,
            'timestamp': memory.timestamp.isoformat(),
            'last_accessed': memory.last_accessed.isoformat() if memory.last_accessed else None
        }
    
    def _row_to_memory(self, row: Tuple) -> MemoryRecord:
        """Convert database row to memory record."""
        return MemoryRecord(
            id=row[0],
            context_id=row[1],
            content=row[2],
            metadata=json.loads(row[3]) if row[3] else {},
            importance=row[4],
            access_count=row[5],
            timestamp=datetime.fromisoformat(row[6]),
            last_accessed=datetime.fromisoformat(row[7]) if row[7] else None
        )
    
    def _row_to_knowledge_node(self, row: Tuple) -> KnowledgeNode:
        """Convert database row to knowledge node."""
        return KnowledgeNode(
            id=row[0],
            content=row[1],
            node_type=row[2],
            properties=json.loads(row[3]) if row[3] else {},
            created_at=datetime.fromisoformat(row[4])
        )
    
    def _row_to_knowledge_edge(self, row: Tuple) -> KnowledgeEdge:
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
            (id, context_id, content, metadata, importance, access_count, timestamp, last_accessed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record.id,
            record.context_id,
            record.content,
            json.dumps(record.metadata),
            record.importance,
            record.access_count,
            record.timestamp.isoformat(),
            record.last_accessed.isoformat() if record.last_accessed else None
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
        # Implementation would fetch specific memory from database
        return None
    
    async def _get_memories_by_context(self, context_id: str, limit: int) -> List[MemoryRecord]:
        """Get memories by context."""
        # Implementation would fetch memories by context
        return []
    
    async def _get_recent_memories(self, limit: int) -> List[MemoryRecord]:
        """Get recent memories."""
        # Implementation would fetch recent memories
        return []
    
    async def _update_access_count(self, memory_id: str) -> None:
        """Update memory access count."""
        # Implementation would update access count
        pass
    
    async def _update_memory_db(self, memory_id: str, updates: Dict[str, Any]) -> None:
        """Update memory in database."""
        # Implementation would update memory in database
        pass
    
    async def _delete_memory_db(self, memory_id: str) -> None:
        """Delete memory from database."""
        # Implementation would delete memory from database
        pass
    
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
