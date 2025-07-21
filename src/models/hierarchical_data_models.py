"""Enhanced data models for hierarchical research structure."""

from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from uuid import uuid4


def generate_uuid() -> str:
    """Generate a unique ID."""
    return str(uuid4())


class Project(BaseModel):
    """Project model for organizing research initiatives."""
    id: str = Field(default_factory=generate_uuid)
    name: str
    description: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now()


class ResearchTopic(BaseModel):
    """Research topic model for specific areas of investigation within a project."""
    id: str = Field(default_factory=generate_uuid)
    project_id: str
    name: str
    description: str = ""
    status: str = "active"  # active, paused, completed, archived
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now()

    def update_status(self, new_status: str) -> None:
        """Update topic status."""
        self.status = new_status
        self.update_timestamp()


class ResearchPlan(BaseModel):
    """Research plan model for structured approaches to investigate a topic."""
    id: str = Field(default_factory=generate_uuid)
    topic_id: str
    name: str
    description: str = ""
    plan_type: str = "comprehensive"  # comprehensive, quick, deep, custom
    status: str = "draft"  # draft, active, completed, cancelled
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    estimated_cost: float = 0.0
    actual_cost: float = 0.0
    plan_structure: Dict[str, Any] = Field(default_factory=dict)  # JSON structure defining the approach
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now()

    def update_status(self, new_status: str) -> None:
        """Update plan status."""
        self.status = new_status
        self.update_timestamp()

    def update_cost(self, cost: float, is_actual: bool = False) -> None:
        """Update cost information."""
        if is_actual:
            self.actual_cost = cost
        else:
            self.estimated_cost = cost
        self.update_timestamp()


class Task(BaseModel):
    """Task model for individual work units within a research plan."""
    id: str = Field(default_factory=generate_uuid)
    plan_id: str
    name: str
    description: str = ""
    task_type: str = "research"  # research, analysis, synthesis, validation
    task_order: int = 0
    status: str = "pending"  # pending, running, completed, failed, cancelled
    stage: str = "planning"  # planning, retrieval, reasoning, execution, synthesis, complete, failed
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    estimated_cost: float = 0.0
    actual_cost: float = 0.0
    cost_approved: bool = False
    single_agent_mode: bool = False
    max_results: int = 10
    progress: float = 0.0
    
    # Task execution data
    query: Optional[str] = None  # For research tasks
    search_results: List[Dict[str, Any]] = Field(default_factory=list)
    reasoning_output: Optional[str] = None
    execution_results: List[Dict[str, Any]] = Field(default_factory=list)
    synthesis: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now()

    def update_progress(self, new_progress: float) -> None:
        """Update task progress."""
        self.progress = max(0.0, min(100.0, new_progress))
        self.update_timestamp()

    def update_status(self, new_status: str, new_stage: Optional[str] = None) -> None:
        """Update task status and optionally stage."""
        self.status = new_status
        if new_stage:
            self.stage = new_stage
        self.update_timestamp()


# Legacy models for backward compatibility
class Conversation(BaseModel):
    """Conversation model for managing chat sessions."""
    id: str = Field(default_factory=generate_uuid)
    project_id: str
    title: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    participants: List[str] = Field(default_factory=lambda: ['user', 'openai', 'xai'])
    status: str = "active"  # active, paused, archived
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now()


class Message(BaseModel):
    """Message model for individual chat messages."""
    id: str = Field(default_factory=generate_uuid)
    conversation_id: str
    participant: str  # user, openai, xai
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    message_type: str = "text"  # text, system, command, error
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the message."""
        self.metadata[key] = value


class AIConfig(BaseModel):
    """AI configuration model."""
    provider: str  # openai, xai
    model: str
    temperature: float = 0.7
    max_tokens: int = 2000
    system_prompt: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Alias for backward compatibility
AIProviderConfig = AIConfig


class ConversationSession(BaseModel):
    """Complete conversation session with all related data."""
    conversation: Conversation
    messages: List[Message] = Field(default_factory=list)
    project: Optional[Project] = None
    ai_configs: Dict[str, AIConfig] = Field(default_factory=dict)

    def add_message(self, message: Message) -> None:
        """Add a message to the session."""
        self.messages.append(message)
        self.conversation.update_timestamp()

    def get_messages_by_participant(self, participant: str) -> List[Message]:
        """Get all messages from a specific participant."""
        return [msg for msg in self.messages if msg.participant == participant]

    def get_recent_messages(self, limit: int = 10) -> List[Message]:
        """Get the most recent messages."""
        return sorted(self.messages, key=lambda x: x.timestamp, reverse=True)[:limit]

    def get_context_messages(self, max_tokens: int = 8000) -> List[Message]:
        """Get messages that fit within the token limit for context."""
        # Simple approximation: ~4 characters per token
        char_limit = max_tokens * 4
        total_chars = 0
        context_messages = []
        
        for message in reversed(self.messages):
            message_chars = len(message.content)
            if total_chars + message_chars > char_limit:
                break
            context_messages.append(message)
            total_chars += message_chars
        
        return list(reversed(context_messages))


# Legacy alias for backward compatibility during migration
ResearchTask = Task


# Response models for API
class ResearchTopicResponse(BaseModel):
    """Response model for research topics."""
    id: str
    project_id: str
    name: str
    description: str
    status: str
    created_at: str
    updated_at: str
    plan_count: int = 0
    task_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ResearchPlanResponse(BaseModel):
    """Response model for research plans."""
    id: str
    topic_id: str
    name: str
    description: str
    plan_type: str
    status: str
    created_at: str
    updated_at: str
    estimated_cost: float
    actual_cost: float
    task_count: int = 0
    completed_tasks: int = 0
    progress: float = 0.0
    plan_structure: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskResponse(BaseModel):
    """Response model for tasks."""
    id: str
    plan_id: str
    name: str
    description: str
    task_type: str
    task_order: int
    status: str
    stage: str
    created_at: str
    updated_at: str
    estimated_cost: float
    actual_cost: float
    cost_approved: bool
    single_agent_mode: bool
    max_results: int
    progress: float
    query: Optional[str] = None
    search_results: List[Dict[str, Any]] = Field(default_factory=list)
    reasoning_output: Optional[str] = None
    execution_results: List[Dict[str, Any]] = Field(default_factory=list)
    synthesis: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Request models for API
class ResearchTopicRequest(BaseModel):
    """Request model for creating research topics."""
    project_id: str
    name: str
    description: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ResearchPlanRequest(BaseModel):
    """Request model for creating research plans."""
    topic_id: str
    name: str
    description: str = ""
    plan_type: str = "comprehensive"
    plan_structure: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskRequest(BaseModel):
    """Request model for creating tasks."""
    plan_id: str
    name: str
    description: str = ""
    task_type: str = "research"
    task_order: int = 0
    query: Optional[str] = None  # For research tasks
    max_results: int = 10
    single_agent_mode: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
