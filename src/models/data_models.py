"""Core data models for the Collaborate application."""

from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from uuid import uuid4


def generate_uuid() -> str:
    """Generate a unique ID."""
    return str(uuid4())


class Project(BaseModel):
    """Project model for organizing conversations."""
    id: str = Field(default_factory=generate_uuid)
    name: str
    description: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now()


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


class ResearchTask(BaseModel):
    """Research task model for tracking research requests."""
    id: str = Field(default_factory=generate_uuid)
    project_id: str
    conversation_id: Optional[str] = None
    query: str
    name: str  # Human-readable task name
    status: str = "pending"  # pending, running, completed, failed, cancelled
    stage: str = "planning"  # planning, retrieval, reasoning, execution, synthesis, complete, failed
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    estimated_cost: float = 0.0
    actual_cost: float = 0.0
    cost_approved: bool = False
    single_agent_mode: bool = False
    research_mode: str = "comprehensive"  # comprehensive, quick, deep
    max_results: int = 10
    progress: float = 0.0
    
    # Research results
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
