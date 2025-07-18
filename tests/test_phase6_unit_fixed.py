"""
Phase 6 Unit Tests

Comprehensive unit tests for all core components 
of the multi-AI research collaboration system.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

# Import the modules we're testing
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config.config_manager import ConfigManager
from storage.database import DatabaseManager
from core.ai_client_manager import AIClientManager
from core.research_manager import ResearchManager
from models.data_models import Project, Conversation, Message, AgentResponse
from mcp.protocols import ResearchAction, TaskStatus
from utils.error_handler import ErrorHandler
from utils.performance import PerformanceMonitor


@pytest.mark.unit
class TestConfigManager:
    """Test configuration management."""
    
    def test_config_manager_initialization(self, config_manager):
        """Test ConfigManager initialization."""
        assert config_manager is not None
        assert hasattr(config_manager, 'config')
    
    def test_get_ai_provider_config(self, config_manager):
        """Test AI provider configuration retrieval."""
        config = config_manager.get_ai_provider_config('openai')
        assert isinstance(config, dict)
        assert 'provider' in config
        assert 'model' in config
    
    def test_get_invalid_provider_config(self, config_manager):
        """Test getting configuration for invalid provider."""
        with pytest.raises(ValueError):
            config_manager.get_ai_provider_config('invalid_provider')
    
    def test_get_mcp_config(self, config_manager):
        """Test MCP configuration retrieval."""
        mcp_config = config_manager.get_mcp_config()
        assert isinstance(mcp_config, dict)
        assert 'host' in mcp_config
        assert 'port' in mcp_config
    
    def test_get_research_config(self, config_manager):
        """Test research configuration retrieval."""
        research_config = config_manager.get_research_config()
        assert isinstance(research_config, dict)
        assert 'max_concurrent_tasks' in research_config or 'task_timeout' in research_config


@pytest.mark.unit
class TestDatabaseManager:
    """Test database operations."""
    
    def test_database_initialization(self, db_manager):
        """Test DatabaseManager initialization."""
        assert db_manager is not None
        assert hasattr(db_manager, 'db_path')
    
    def test_create_project(self, db_manager):
        """Test project creation."""
        project = db_manager.create_project("Test Project", "This is a test project")
        assert project is not None
        assert project.name == "Test Project"
        assert project.description == "This is a test project"
    
    def test_get_project(self, db_manager):
        """Test project retrieval."""
        # Create a project first
        created_project = db_manager.create_project("Test Project", "Test description")
        
        # Retrieve the project
        retrieved_project = db_manager.get_project(created_project.id)
        assert retrieved_project is not None
        assert retrieved_project.name == created_project.name
    
    def test_get_nonexistent_project(self, db_manager):
        """Test retrieving non-existent project."""
        project = db_manager.get_project("nonexistent_id")
        assert project is None
    
    def test_list_projects(self, db_manager):
        """Test listing projects."""
        # Create a few projects
        db_manager.create_project("Project 1", "Description 1")
        db_manager.create_project("Project 2", "Description 2")
        
        projects = db_manager.list_projects()
        assert len(projects) >= 2
    
    def test_create_conversation(self, db_manager):
        """Test conversation creation."""
        project = db_manager.create_project("Test Project", "Test description")
        conversation = db_manager.create_conversation(project.id, "Test Conversation")
        
        assert conversation is not None
        assert conversation.project_id == project.id
        assert conversation.title == "Test Conversation"
    
    def test_get_conversation(self, db_manager):
        """Test conversation retrieval."""
        project = db_manager.create_project("Test Project", "Test description")
        created_conv = db_manager.create_conversation(project.id, "Test Conversation")
        
        retrieved_conv = db_manager.get_conversation(created_conv.id)
        assert retrieved_conv is not None
        assert retrieved_conv.title == created_conv.title
    
    def test_create_message(self, db_manager):
        """Test message creation."""
        project = db_manager.create_project("Test Project", "Test description")
        conversation = db_manager.create_conversation(project.id, "Test Conversation")
        
        message = db_manager.create_message(
            conversation.id, 
            "user", 
            "Hello, world!", 
            {"test": "metadata"}
        )
        
        assert message is not None
        assert message.conversation_id == conversation.id
        assert message.role == "user"
        assert message.content == "Hello, world!"
    
    def test_get_conversation_messages(self, db_manager):
        """Test retrieving conversation messages."""
        project = db_manager.create_project("Test Project", "Test description")
        conversation = db_manager.create_conversation(project.id, "Test Conversation")
        
        # Create some messages
        db_manager.create_message(conversation.id, "user", "Message 1", {})
        db_manager.create_message(conversation.id, "assistant", "Message 2", {})
        
        messages = db_manager.get_conversation_messages(conversation.id)
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"
    
    def test_get_database_stats(self, db_manager):
        """Test database statistics retrieval."""
        stats = db_manager.get_database_stats()
        assert isinstance(stats, dict)
        assert 'projects' in stats
        assert 'conversations' in stats
        assert 'messages' in stats
        assert 'status' in stats


@pytest.mark.unit
class TestAIClientManager:
    """Test AI client management."""
    
    def test_ai_client_manager_initialization(self, ai_client_manager):
        """Test AIClientManager initialization."""
        assert ai_client_manager is not None
        assert hasattr(ai_client_manager, 'clients')
    
    def test_get_available_providers(self, ai_client_manager):
        """Test getting available providers."""
        providers = ai_client_manager.get_available_providers()
        assert isinstance(providers, list)
        assert len(providers) > 0
    
    def test_get_provider_health(self, ai_client_manager):
        """Test provider health check."""
        health = ai_client_manager.get_provider_health()
        assert isinstance(health, dict)
        
        # Check that health info is returned for each provider
        for provider_name, status in health.items():
            assert 'status' in status
            assert 'failure_count' in status
            assert 'available' in status
    
    def test_adapt_system_prompt(self, ai_client_manager):
        """Test system prompt adaptation."""
        providers = ai_client_manager.get_available_providers()
        if providers:
            provider = providers[0]
            prompt = ai_client_manager.adapt_system_prompt(provider, "Test message", [])
            assert isinstance(prompt, str)
    
    def test_get_response_mock(self, ai_client_manager):
        """Test getting response with mock."""
        providers = ai_client_manager.get_available_providers()
        if providers:
            provider = providers[0]
            
            # Mock the response
            with patch.object(ai_client_manager, 'get_response', return_value=AsyncMock()):
                response = ai_client_manager.get_response(provider, "Test message")
                assert response is not None


@pytest.mark.unit
@pytest.mark.asyncio
class TestResearchManager:
    """Test research management."""
    
    def test_research_manager_initialization(self, research_manager):
        """Test ResearchManager initialization."""
        assert research_manager is not None
        assert hasattr(research_manager, 'active_contexts')
    
    async def test_start_research_task(self, research_manager):
        """Test starting a research task."""
        task_id = await research_manager.start_research_task("What is machine learning?")
        assert task_id is not None
        assert isinstance(task_id, str)
    
    async def test_get_task_status(self, research_manager):
        """Test getting task status."""
        task_id = await research_manager.start_research_task("What is AI?")
        status = await research_manager.get_task_status(task_id)
        assert status is not None
        assert 'task_id' in status
        assert 'stage' in status
    
    async def test_get_active_tasks(self, research_manager):
        """Test getting active tasks."""
        task_id = await research_manager.start_research_task("Test query")
        active_tasks = await research_manager.get_active_tasks()
        assert isinstance(active_tasks, list)
        assert len(active_tasks) > 0
    
    def test_research_context_creation(self, research_manager):
        """Test research context creation."""
        context = research_manager.create_research_context("test_query", "test_context_id")
        assert context is not None
        assert context.query == "test_query"
        assert context.context_id == "test_context_id"
    
    def test_callback_registration(self, research_manager):
        """Test callback registration."""
        def dummy_callback(data):
            pass
        
        research_manager.register_callback("test_callback", dummy_callback)
        assert "test_callback" in research_manager.callbacks


@pytest.mark.unit
class TestDataModels:
    """Test data models."""
    
    def test_project_creation(self):
        """Test Project model creation."""
        project = Project(
            id="test_id",
            name="Test Project",
            description="A test project",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        assert project.name == "Test Project"
        assert project.description == "A test project"
    
    def test_conversation_creation(self):
        """Test Conversation model creation."""
        conversation = Conversation(
            id="conv_id",
            project_id="project_id",
            title="Test Conversation",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        assert conversation.title == "Test Conversation"
        assert conversation.project_id == "project_id"
    
    def test_message_creation(self):
        """Test Message model creation."""
        message = Message(
            id="msg_id",
            conversation_id="conv_id",
            role="user",
            content="Hello",
            metadata={"test": "data"},
            created_at=datetime.now()
        )
        assert message.role == "user"
        assert message.content == "Hello"
        assert message.metadata == {"test": "data"}
    
    def test_message_metadata(self):
        """Test Message metadata handling."""
        message = Message(
            id="msg_id",
            conversation_id="conv_id",
            role="assistant",
            content="Response",
            metadata={"provider": "openai", "tokens": 100},
            created_at=datetime.now()
        )
        assert message.metadata["provider"] == "openai"
        assert message.metadata["tokens"] == 100


@pytest.mark.unit
class TestMCPProtocols:
    """Test MCP protocol classes."""
    
    def test_research_action_creation(self):
        """Test ResearchAction creation."""
        action = ResearchAction(
            task_id="task_123",
            context_id="context_456",
            agent_type="retriever",
            action="search",
            payload={"query": "test query"},
            priority=1,
            status="pending"
        )
        assert action.task_id == "task_123"
        assert action.agent_type == "retriever"
        assert action.action == "search"
    
    def test_agent_response_creation(self):
        """Test AgentResponse creation."""
        response = AgentResponse(
            task_id="task_123",
            agent_id="agent_456",
            agent_type="retriever",
            status="completed",
            result={"data": "test result"},
            error=None
        )
        assert response.task_id == "task_123"
        assert response.status == "completed"
        assert response.result == {"data": "test result"}
    
    def test_research_action_serialization(self):
        """Test ResearchAction serialization."""
        action = ResearchAction(
            task_id="task_123",
            context_id="context_456",
            agent_type="retriever",
            action="search",
            payload={"query": "test query"},
            priority=1,
            status="pending"
        )
        
        # Test that we can convert to dict
        action_dict = action.to_dict()
        assert isinstance(action_dict, dict)
        assert action_dict["task_id"] == "task_123"


@pytest.mark.unit
class TestErrorHandler:
    """Test error handling."""
    
    def test_error_handler_initialization(self):
        """Test ErrorHandler initialization."""
        handler = ErrorHandler()
        assert handler is not None
        assert hasattr(handler, 'error_counts')
    
    def test_handle_error(self):
        """Test error handling."""
        handler = ErrorHandler()
        test_error = Exception("Test error")
        
        handler.handle_error(test_error, "test_context")
        
        # Check that error was logged
        assert len(handler.error_counts) > 0
    
    def test_get_error_stats(self):
        """Test getting error statistics."""
        handler = ErrorHandler()
        
        # Generate some errors
        handler.handle_error(Exception("Error 1"), "context1")
        handler.handle_error(Exception("Error 2"), "context2")
        handler.handle_error(Exception("Error 3"), "context1")
        
        stats = handler.get_error_stats()
        assert isinstance(stats, dict)
        assert len(stats) > 0
    
    def test_reset_stats(self):
        """Test resetting error statistics."""
        handler = ErrorHandler()
        
        # Generate an error
        handler.handle_error(Exception("Test error"), "test_context")
        
        # Reset stats
        handler.reset_stats()
        
        # Check that stats are cleared
        stats = handler.get_error_stats()
        assert len(stats) == 0


@pytest.mark.unit
class TestPerformanceMonitor:
    """Test performance monitoring."""
    
    def test_performance_monitor_initialization(self):
        """Test PerformanceMonitor initialization."""
        monitor = PerformanceMonitor()
        assert monitor is not None
        assert hasattr(monitor, 'timers')
    
    def test_timer_functionality(self):
        """Test timer start/stop functionality."""
        monitor = PerformanceMonitor()
        
        # Start a timer
        monitor.start_timer("test_operation")
        
        # Simulate some work
        import time
        time.sleep(0.1)
        
        # Stop the timer
        duration = monitor.end_timer("test_operation")
        
        assert duration > 0
        assert duration >= 0.1
    
    def test_performance_stats(self):
        """Test getting performance statistics."""
        monitor = PerformanceMonitor()
        
        # Run a few operations
        monitor.start_timer("operation1")
        import time
        time.sleep(0.05)
        monitor.end_timer("operation1")
        
        monitor.start_timer("operation2")
        time.sleep(0.03)
        monitor.end_timer("operation2")
        
        stats = monitor.get_stats()
        assert isinstance(stats, dict)
        assert len(stats) > 0
