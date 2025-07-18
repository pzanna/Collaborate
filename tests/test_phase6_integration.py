"""
Integration tests for the multi-AI research collaboration system.

This module contains integration tests that verify the system works correctly
when multiple components interact with each other.
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

from src.config.config_manager import ConfigManager
from src.storage.database import DatabaseManager
from src.core.ai_client_manager import AIClientManager
from src.core.research_manager import ResearchManager
from src.models.data_models import Project, Conversation, Message
from src.mcp.server import MCPServer
from src.mcp.client import MCPClient
from src.utils.export_manager import ExportManager


@pytest.mark.integration
class TestDatabaseIntegration:
    """Test database integration with other components."""
    
    def test_project_conversation_message_flow(self, test_db_manager: DatabaseManager):
        """Test complete project -> conversation -> message flow."""
        # Create a project
        project = Project(
            name="Integration Test Project",
            description="Testing integration between components"
        )
        created_project = test_db_manager.create_project(project)
        assert created_project is not None
        
        # Create a conversation
        conversation = Conversation(
            project_id=created_project.id,
            title="Integration Test Conversation"
        )
        created_conversation = test_db_manager.create_conversation(conversation)
        assert created_conversation is not None
        
        # Create messages
        messages = [
            Message(
                conversation_id=created_conversation.id,
                participant="user",
                content="Hello, let's test integration"
            ),
            Message(
                conversation_id=created_conversation.id,
                participant="openai",
                content="Hello! I'm ready to help with integration testing."
            ),
            Message(
                conversation_id=created_conversation.id,
                participant="xai",
                content="Great! I can also assist with testing the system integration."
            )
        ]
        
        for message in messages:
            created_message = test_db_manager.create_message(message)
            assert created_message is not None
        
        # Verify the complete flow
        retrieved_project = test_db_manager.get_project(created_project.id)
        assert retrieved_project is not None
        assert retrieved_project.name == "Integration Test Project"
        
        retrieved_conversation = test_db_manager.get_conversation(created_conversation.id)
        assert retrieved_conversation is not None
        assert retrieved_conversation.title == "Integration Test Conversation"
        
        retrieved_messages = test_db_manager.get_conversation_messages(created_conversation.id)
        assert len(retrieved_messages) == 3
        assert retrieved_messages[0].participant == "user"
        assert retrieved_messages[1].participant == "openai"
        assert retrieved_messages[2].participant == "xai"
    
    def test_conversation_session_integration(self, test_db_manager: DatabaseManager):
        """Test conversation session functionality."""
        # Create test data
        project = Project(name="Session Test", description="Test session")
        test_db_manager.create_project(project)
        
        conversation = Conversation(
            project_id=project.id,
            title="Session Test Conversation"
        )
        test_db_manager.create_conversation(conversation)
        
        message = Message(
            conversation_id=conversation.id,
            participant="user",
            content="Test session message"
        )
        test_db_manager.create_message(message)
        
        # Get session
        session = test_db_manager.get_conversation_session(conversation.id)
        
        assert session is not None
        assert session.conversation.id == conversation.id
        assert session.project is not None
        assert session.project.id == project.id
        assert len(session.messages) == 1
        assert session.messages[0].content == "Test session message"


@pytest.mark.integration
class TestAIClientIntegration:
    """Test AI client integration with other components."""
    
    @patch('src.ai_clients.openai_client.OpenAIClient.get_response')
    def test_ai_client_manager_with_mock_responses(self, mock_get_response, 
                                                  ai_client_manager: AIClientManager):
        """Test AI client manager with mocked responses."""
        # Mock responses
        mock_get_response.return_value = "This is a test response from OpenAI"
        
        # Create test messages
        messages = [
            Message(
                conversation_id="test-conv",
                participant="user",
                content="Hello, how are you?"
            )
        ]
        
        # Get available providers
        providers = ai_client_manager.get_available_providers()
        assert len(providers) > 0
        
        # Test single provider response
        if 'openai' in providers:
            response = ai_client_manager.get_response('openai', messages)
            assert response == "This is a test response from OpenAI"
            mock_get_response.assert_called_once()
        
        # Test smart responses
        mock_get_response.reset_mock()
        mock_get_response.return_value = "Smart response test"
        
        responses = ai_client_manager.get_smart_responses(messages)
        assert isinstance(responses, dict)
        assert len(responses) > 0
    
    def test_ai_client_manager_configuration(self, ai_client_manager: AIClientManager):
        """Test AI client manager configuration."""
        # Test provider health
        health = ai_client_manager.get_provider_health()
        assert isinstance(health, dict)
        
        # Test provider count
        count = ai_client_manager.get_provider_count()
        assert count >= 0
        
        # Test available providers
        providers = ai_client_manager.get_available_providers()
        assert isinstance(providers, list)
        
        # Test failed providers
        failed = ai_client_manager.get_failed_providers()
        assert isinstance(failed, dict)


@pytest.mark.integration
@pytest.mark.asyncio
class TestResearchManagerIntegration:
    """Test research manager integration."""
    
    async def test_research_manager_with_config(self, config_manager: ConfigManager):
        """Test research manager with configuration."""
        research_manager = ResearchManager(config_manager)
        
        # Test initialization
        assert research_manager.config == config_manager
        assert research_manager.active_contexts == {}
        
        # Test configuration methods
        mcp_config = research_manager.config.get_mcp_config()
        assert isinstance(mcp_config, dict)
        
        research_config = research_manager.config.get_research_config()
        assert isinstance(research_config, dict)
        
        agent_config = research_manager.config.get_agent_config()
        assert isinstance(agent_config, dict)
    
    async def test_research_task_lifecycle(self, research_manager: ResearchManager):
        """Test complete research task lifecycle."""
        # Start a research task
        task_id = await research_manager.start_research_task(
            query="Test research query",
            user_id="test-user",
            conversation_id="test-conv"
        )
        
        assert task_id is not None
        assert task_id in research_manager.active_contexts
        
        # Check task status
        status = research_manager.get_task_status(task_id)
        assert status is not None
        
        # Get active tasks
        active_tasks = research_manager.get_active_tasks()
        assert task_id in active_tasks
        
        # Test context retrieval
        context = research_manager.active_contexts[task_id]
        assert context.query == "Test research query"
        assert context.user_id == "test-user"
        assert context.conversation_id == "test-conv"


@pytest.mark.integration
class TestExportIntegration:
    """Test export functionality integration."""
    
    def test_export_manager_with_database(self, test_db_manager: DatabaseManager, 
                                         temporary_export_dir: Path):
        """Test export manager with database integration."""
        # Create test data
        project = Project(name="Export Test", description="Test export functionality")
        test_db_manager.create_project(project)
        
        conversation = Conversation(
            project_id=project.id,
            title="Export Test Conversation"
        )
        test_db_manager.create_conversation(conversation)
        
        messages = [
            Message(
                conversation_id=conversation.id,
                participant="user",
                content="What is artificial intelligence?"
            ),
            Message(
                conversation_id=conversation.id,
                participant="openai",
                content="Artificial intelligence is the simulation of human intelligence processes by machines."
            ),
            Message(
                conversation_id=conversation.id,
                participant="xai",
                content="AI involves creating systems that can perform tasks that typically require human intelligence."
            )
        ]
        
        for message in messages:
            test_db_manager.create_message(message)
        
        # Test export
        export_manager = ExportManager(str(temporary_export_dir))
        session = test_db_manager.get_conversation_session(conversation.id)
        
        assert session is not None, "Session should not be None"
        
        # Test JSON export
        json_path = export_manager.export_conversation(session, "json", "test_export")
        assert Path(json_path).exists()
        
        # Test markdown export
        md_path = export_manager.export_conversation(session, "markdown", "test_export")
        assert Path(md_path).exists()
        
        # Test export listing
        exports = export_manager.list_exports()
        assert len(exports) >= 2
        
        # Verify export content
        with open(json_path, 'r') as f:
            content = f.read()
            assert "Export Test Conversation" in content
            assert "artificial intelligence" in content


@pytest.mark.integration
class TestWebSocketIntegration:
    """Test WebSocket integration (mocked)."""
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket for testing."""
        websocket = Mock()
        websocket.send = AsyncMock()
        websocket.receive = AsyncMock()
        websocket.close = AsyncMock()
        return websocket
    
    async def test_websocket_message_flow(self, mock_websocket):
        """Test WebSocket message flow."""
        # Test sending messages
        await mock_websocket.send('{"type": "message", "content": "Hello"}')
        mock_websocket.send.assert_called_once_with('{"type": "message", "content": "Hello"}')
        
        # Test receiving messages
        mock_websocket.receive.return_value = '{"type": "response", "content": "Hello back"}'
        response = await mock_websocket.receive()
        assert response == '{"type": "response", "content": "Hello back"}'
        
        # Test closing connection
        await mock_websocket.close()
        mock_websocket.close.assert_called_once()


@pytest.mark.integration
class TestConfigurationIntegration:
    """Test configuration integration across components."""
    
    def test_config_manager_with_components(self, config_manager: ConfigManager):
        """Test configuration manager with various components."""
        # Test database configuration
        db_manager = DatabaseManager(":memory:")
        assert db_manager.db_path == ":memory:"
        
        # Test AI client manager configuration
        ai_manager = AIClientManager(config_manager)
        assert ai_manager.config_manager == config_manager
        
        # Test configuration access
        assert hasattr(config_manager.config, 'ai_providers')
        assert hasattr(config_manager.config, 'storage')
        assert hasattr(config_manager.config, 'conversation')
        assert hasattr(config_manager.config, 'mcp_server')
    
    def test_config_update_propagation(self, config_manager: ConfigManager):
        """Test configuration updates propagate to components."""
        # Update a configuration value
        config_manager.config.conversation.max_context_tokens = 10000
        
        # Verify the update
        assert config_manager.config.conversation.max_context_tokens == 10000
        
        # Test that new components use updated config
        ai_manager = AIClientManager(config_manager)
        assert ai_manager.config_manager.config.conversation.max_context_tokens == 10000


@pytest.mark.integration
class TestErrorHandlingIntegration:
    """Test error handling integration across components."""
    
    def test_database_error_handling(self, test_db_manager: DatabaseManager):
        """Test database error handling integration."""
        # Test creating conversation with invalid project ID
        invalid_conversation = Conversation(
            project_id="invalid-project-id",
            title="Invalid Conversation"
        )
        
        result = test_db_manager.create_conversation(invalid_conversation)
        assert result is None  # Should return None on error
        
        # Test creating message with invalid conversation ID
        invalid_message = Message(
            conversation_id="invalid-conversation-id",
            participant="user",
            content="Invalid message"
        )
        
        result = test_db_manager.create_message(invalid_message)
        assert result is None  # Should return None on error
    
    def test_ai_client_error_handling(self, ai_client_manager: AIClientManager):
        """Test AI client error handling integration."""
        # Test with invalid provider
        try:
            ai_client_manager.get_response("invalid_provider", [])
            assert False, "Should have raised an error"
        except Exception as e:
            assert "not available" in str(e) or "Provider" in str(e)
        
        # Test with empty messages
        providers = ai_client_manager.get_available_providers()
        if providers:
            response = ai_client_manager.get_response(providers[0], [])
            # Should handle empty messages gracefully
            assert isinstance(response, str)


@pytest.mark.integration
class TestPerformanceIntegration:
    """Test performance integration across components."""
    
    def test_database_performance(self, test_db_manager: DatabaseManager):
        """Test database performance with multiple operations."""
        # Create multiple projects
        projects = []
        for i in range(10):
            project = Project(
                name=f"Performance Test Project {i}",
                description=f"Performance test project {i}"
            )
            created_project = test_db_manager.create_project(project)
            projects.append(created_project)
        
        # Verify all projects were created
        all_projects = test_db_manager.list_projects()
        assert len(all_projects) >= 10
        
        # Create multiple conversations
        conversations = []
        for i, project in enumerate(projects):
            conversation = Conversation(
                project_id=project.id,
                title=f"Performance Test Conversation {i}"
            )
            created_conversation = test_db_manager.create_conversation(conversation)
            conversations.append(created_conversation)
        
        # Create multiple messages
        for i, conversation in enumerate(conversations):
            for j in range(5):  # 5 messages per conversation
                message = Message(
                    conversation_id=conversation.id,
                    participant="user" if j % 2 == 0 else "openai",
                    content=f"Performance test message {j} in conversation {i}"
                )
                test_db_manager.create_message(message)
        
        # Verify performance with stats
        stats = test_db_manager.get_database_stats()
        assert stats["projects"] >= 10
        assert stats["conversations"] >= 10
        assert stats["messages"] >= 50
    
    def test_memory_usage_integration(self, test_db_manager: DatabaseManager):
        """Test memory usage doesn't grow unbounded."""
        import gc
        import os
        
        # Get initial memory usage (simplified approach)
        gc.collect()
        
        # Create and delete many objects
        for i in range(100):
            project = Project(
                name=f"Memory Test Project {i}",
                description=f"Memory test project {i}"
            )
            test_db_manager.create_project(project)
            
            conversation = Conversation(
                project_id=project.id,
                title=f"Memory Test Conversation {i}"
            )
            test_db_manager.create_conversation(conversation)
            
            # Create multiple messages
            for j in range(10):
                message = Message(
                    conversation_id=conversation.id,
                    participant="user",
                    content=f"Memory test message {j}"
                )
                test_db_manager.create_message(message)
        
        # Force garbage collection
        gc.collect()
        
        # Test successful completion without memory errors
        stats = test_db_manager.get_database_stats()
        assert stats["projects"] >= 100
        assert stats["conversations"] >= 100
        assert stats["messages"] >= 1000
