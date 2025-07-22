"""
Message Control Protocol (MCP) Data Structures

Defines the core message types and protocols used for communication
between the Research Manager and specialized agents.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum


class TaskStatus(Enum):
    """Task execution status enumeration"""
    PENDING = "pending"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Priority(Enum):
    """Task priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class AgentType(Enum):
    """Available agent types"""
    RETRIEVER = "Retriever"
    PLANNING = "Planning"
    EXECUTOR = "Executor"
    MEMORY = "Memory"


@dataclass
class ResearchAction:
    """Core MCP message structure for research tasks"""
    task_id: str
    context_id: str
    agent_type: str
    action: str
    payload: Dict[str, Any]
    priority: str = "normal"
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)
    timeout: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    parent_task_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    parallelism: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'task_id': self.task_id,
            'context_id': self.context_id,
            'agent_type': self.agent_type,
            'action': self.action,
            'payload': self.payload,
            'priority': self.priority,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'timeout': self.timeout,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'parent_task_id': self.parent_task_id,
            'dependencies': self.dependencies,
            'parallelism': self.parallelism
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResearchAction':
        """Create from dictionary"""
        data = data.copy()
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


@dataclass
class AgentResponse:
    """Response message from agents back to Research Manager"""
    task_id: str
    context_id: str
    agent_type: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    partial_result: Optional[Dict[str, Any]] = None
    completed_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'task_id': self.task_id,
            'context_id': self.context_id,
            'agent_type': self.agent_type,
            'status': self.status,
            'result': self.result,
            'error': self.error,
            'partial_result': self.partial_result,
            'completed_at': self.completed_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentResponse':
        """Create from dictionary"""
        data = data.copy()
        if 'completed_at' in data and isinstance(data['completed_at'], str):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        return cls(**data)


@dataclass
class AgentRegistration:
    """Agent registration message"""
    agent_type: str
    capabilities: List[str]
    max_concurrent: int
    timeout: int
    agent_id: str
    status: str = "available"
    registered_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'agent_type': self.agent_type,
            'capabilities': self.capabilities,
            'max_concurrent': self.max_concurrent,
            'timeout': self.timeout,
            'agent_id': self.agent_id,
            'status': self.status,
            'registered_at': self.registered_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentRegistration':
        """Create from dictionary"""
        data = data.copy()
        if 'registered_at' in data and isinstance(data['registered_at'], str):
            data['registered_at'] = datetime.fromisoformat(data['registered_at'])
        return cls(**data)


@dataclass
class TaskUpdate:
    """Task status update message"""
    task_id: str
    status: str
    progress: Optional[float] = None
    message: Optional[str] = None
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'task_id': self.task_id,
            'status': self.status,
            'progress': self.progress,
            'message': self.message,
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskUpdate':
        """Create from dictionary"""
        data = data.copy()
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)


@dataclass
class RegisterCapabilities:
    """Message for registering agent capabilities"""
    agent_id: str
    agent_type: str
    capabilities: List[str]
    max_concurrent: int = 1
    timeout: int = 300
    version: str = "1.0"
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'agent_id': self.agent_id,
            'agent_type': self.agent_type,
            'capabilities': self.capabilities,
            'max_concurrent': self.max_concurrent,
            'timeout': self.timeout,
            'version': self.version,
            'timestamp': self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RegisterCapabilities':
        """Create from dictionary"""
        data = data.copy()
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class TimeoutEvent:
    """Event message for task timeouts"""
    task_id: str
    context_id: str
    agent_type: str
    timeout_duration: int
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'task_id': self.task_id,
            'context_id': self.context_id,
            'agent_type': self.agent_type,
            'timeout_duration': self.timeout_duration,
            'message': self.message,
            'timestamp': self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TimeoutEvent':
        """Create from dictionary"""
        data = data.copy()
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class StoreMemoryRequest:
    """Request to store memory data with structured metadata"""
    context_id: str
    memory_type: str  # "task_result", "finding", "insight", "context"
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5
    tags: List[str] = field(default_factory=list)
    source_task_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'context_id': self.context_id,
            'memory_type': self.memory_type,
            'content': self.content,
            'metadata': self.metadata,
            'importance': self.importance,
            'tags': self.tags,
            'source_task_id': self.source_task_id,
            'timestamp': self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StoreMemoryRequest':
        """Create from dictionary"""
        data = data.copy()
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class QueryMemoryRequest:
    """Request to query stored memories"""
    context_id: Optional[str] = None
    memory_type: Optional[str] = None
    query: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    limit: int = 10
    min_importance: float = 0.0
    time_range: Optional[Dict[str, str]] = None  # {"start": "2024-01-01", "end": "2024-01-02"}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'context_id': self.context_id,
            'memory_type': self.memory_type,
            'query': self.query,
            'tags': self.tags,
            'limit': self.limit,
            'min_importance': self.min_importance,
            'time_range': self.time_range
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueryMemoryRequest':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class PersonaConsultationRequest:
    """Request for expert consultation from persona agents"""
    request_id: str
    expertise_area: str
    query: str
    context: Dict[str, Any] = field(default_factory=dict)
    preferred_persona: Optional[str] = None
    priority: str = "normal"
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'request_id': self.request_id,
            'expertise_area': self.expertise_area,
            'query': self.query,
            'context': self.context,
            'preferred_persona': self.preferred_persona,
            'priority': self.priority,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PersonaConsultationRequest':
        """Create from dictionary"""
        data = data.copy()
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


@dataclass
class PersonaConsultationResponse:
    """Response from persona consultation"""
    request_id: str
    persona_type: str
    status: str
    expert_response: Optional[str] = None
    confidence: Optional[float] = None
    error: Optional[str] = None
    completed_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'request_id': self.request_id,
            'persona_type': self.persona_type,
            'status': self.status,
            'expert_response': self.expert_response,
            'confidence': self.confidence,
            'error': self.error,
            'completed_at': self.completed_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PersonaConsultationResponse':
        """Create from dictionary"""
        data = data.copy()
        if 'completed_at' in data and isinstance(data['completed_at'], str):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        return cls(**data)


# Message type mapping for serialization
MESSAGE_TYPES = {
    'research_action': ResearchAction,
    'agent_response': AgentResponse,
    'agent_registration': AgentRegistration,
    'task_update': TaskUpdate,
    'register_capabilities': RegisterCapabilities,
    'timeout_event': TimeoutEvent,
    'store_memory_request': StoreMemoryRequest,
    'query_memory_request': QueryMemoryRequest,
    'persona_consultation_request': PersonaConsultationRequest,
    'persona_consultation_response': PersonaConsultationResponse
}


def serialize_message(message_type: str, message_data: Any) -> Dict[str, Any]:
    """Serialize message for transmission"""
    if hasattr(message_data, 'to_dict'):
        return {
            'type': message_type,
            'data': message_data.to_dict(),
            'timestamp': datetime.now().isoformat()
        }
    else:
        return {
            'type': message_type,
            'data': message_data,
            'timestamp': datetime.now().isoformat()
        }


def deserialize_message(message: Dict[str, Any]) -> Any:
    """Deserialize message from transmission"""
    message_type = message.get('type')
    message_data = message.get('data')
    
    if message_type in MESSAGE_TYPES:
        return MESSAGE_TYPES[message_type].from_dict(message_data)
    else:
        return message_data
