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
    REASONER = "Reasoner"
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
    timeout: Optional[int] = None
    retry_count: int = 0
    
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
            'retry_count': self.retry_count
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


# Message type mapping for serialization
MESSAGE_TYPES = {
    'research_action': ResearchAction,
    'agent_response': AgentResponse,
    'agent_registration': AgentRegistration,
    'task_update': TaskUpdate
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
