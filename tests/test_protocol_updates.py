"""
Unit tests for Protocol Updates (Phase 1)

Tests for the enhanced protocol definitions including timeout, retry, 
and capability registration fields.
"""

import pytest
from datetime import datetime
from src.mcp.protocols import (
    ResearchAction, AgentResponse, RegisterCapabilities, TimeoutEvent,
    serialize_message, deserialize_message
)


class TestResearchActionEnhancements:
    """Test ResearchAction protocol enhancements"""
    
    def test_research_action_with_new_fields(self):
        """Test ResearchAction with timeout, retry, and dependency fields"""
        action = ResearchAction(
            task_id="test-task-1",
            context_id="test-context-1",
            agent_type="Retriever",
            action="search",
            payload={"query": "test"},
            timeout=30,
            retry_count=1,
            max_retries=3,
            parent_task_id="parent-task-1",
            dependencies=["dep-1", "dep-2"]
        )
        
        assert action.task_id == "test-task-1"
        assert action.timeout == 30
        assert action.retry_count == 1
        assert action.max_retries == 3
        assert action.parent_task_id == "parent-task-1"
        assert action.dependencies == ["dep-1", "dep-2"]
    
    def test_research_action_serialization(self):
        """Test serialization/deserialization with new fields"""
        action = ResearchAction(
            task_id="test-task-1",
            context_id="test-context-1",
            agent_type="Retriever",
            action="search",
            payload={"query": "test"},
            timeout=30,
            max_retries=5,
            dependencies=["dep-1"]
        )
        
        # Serialize
        data_dict = action.to_dict()
        assert data_dict['timeout'] == 30
        assert data_dict['max_retries'] == 5
        assert data_dict['dependencies'] == ["dep-1"]
        
        # Deserialize
        restored_action = ResearchAction.from_dict(data_dict)
        assert restored_action.timeout == 30
        assert restored_action.max_retries == 5
        assert restored_action.dependencies == ["dep-1"]
        assert restored_action.task_id == "test-task-1"
    
    def test_research_action_defaults(self):
        """Test default values for new fields"""
        action = ResearchAction(
            task_id="test-task-1",
            context_id="test-context-1",
            agent_type="Retriever",
            action="search",
            payload={"query": "test"}
        )
        
        assert action.timeout is None
        assert action.retry_count == 0
        assert action.max_retries == 3
        assert action.parent_task_id is None
        assert action.dependencies == []


class TestRegisterCapabilities:
    """Test RegisterCapabilities message class"""
    
    def test_register_capabilities_creation(self):
        """Test RegisterCapabilities message creation"""
        reg = RegisterCapabilities(
            agent_id="agent-123",
            agent_type="Retriever",
            capabilities=["search", "summarize"],
            max_concurrent=2,
            timeout=60
        )
        
        assert reg.agent_id == "agent-123"
        assert reg.agent_type == "Retriever"
        assert reg.capabilities == ["search", "summarize"]
        assert reg.max_concurrent == 2
        assert reg.timeout == 60
        assert reg.version == "1.0"
    
    def test_register_capabilities_serialization(self):
        """Test RegisterCapabilities serialization"""
        reg = RegisterCapabilities(
            agent_id="agent-123",
            agent_type="Retriever",
            capabilities=["search", "summarize"]
        )
        
        data_dict = reg.to_dict()
        assert data_dict['agent_id'] == "agent-123"
        assert data_dict['capabilities'] == ["search", "summarize"]
        
        restored_reg = RegisterCapabilities.from_dict(data_dict)
        assert restored_reg.agent_id == "agent-123"
        assert restored_reg.capabilities == ["search", "summarize"]


class TestTimeoutEvent:
    """Test TimeoutEvent message class"""
    
    def test_timeout_event_creation(self):
        """Test TimeoutEvent message creation"""
        event = TimeoutEvent(
            task_id="task-123",
            context_id="context-123",
            agent_type="Executor",
            timeout_duration=30,
            message="Task exceeded timeout limit"
        )
        
        assert event.task_id == "task-123"
        assert event.context_id == "context-123"
        assert event.agent_type == "Executor"
        assert event.timeout_duration == 30
        assert event.message == "Task exceeded timeout limit"
    
    def test_timeout_event_serialization(self):
        """Test TimeoutEvent serialization"""
        event = TimeoutEvent(
            task_id="task-123",
            context_id="context-123",
            agent_type="Executor",
            timeout_duration=30,
            message="Task exceeded timeout limit"
        )
        
        data_dict = event.to_dict()
        assert data_dict['task_id'] == "task-123"
        assert data_dict['timeout_duration'] == 30
        
        restored_event = TimeoutEvent.from_dict(data_dict)
        assert restored_event.task_id == "task-123"
        assert restored_event.timeout_duration == 30


class TestMessageSerialization:
    """Test message serialization with new message types"""
    
    def test_serialize_register_capabilities(self):
        """Test serializing RegisterCapabilities message"""
        reg = RegisterCapabilities(
            agent_id="agent-123",
            agent_type="Retriever",
            capabilities=["search"]
        )
        
        serialized = serialize_message("register_capabilities", reg)
        assert serialized['type'] == "register_capabilities"
        assert 'data' in serialized
        assert 'timestamp' in serialized
        
        # Test deserialization
        deserialized = deserialize_message(serialized)
        assert isinstance(deserialized, RegisterCapabilities)
        assert deserialized.agent_id == "agent-123"
    
    def test_serialize_timeout_event(self):
        """Test serializing TimeoutEvent message"""
        event = TimeoutEvent(
            task_id="task-123",
            context_id="context-123",
            agent_type="Executor",
            timeout_duration=30,
            message="Timeout occurred"
        )
        
        serialized = serialize_message("timeout_event", event)
        assert serialized['type'] == "timeout_event"
        
        # Test deserialization
        deserialized = deserialize_message(serialized)
        assert isinstance(deserialized, TimeoutEvent)
        assert deserialized.task_id == "task-123"
        assert deserialized.timeout_duration == 30


if __name__ == "__main__":
    pytest.main([__file__])
