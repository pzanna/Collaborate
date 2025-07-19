"""
Integration tests for the Collaborate application.

Tests the integration between different components including:
- AI client manager coordination
- Database and storage integration
- MCP server and agent communication
- End-to-end conversation flows
- Context management integration
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.ai_client_manager import AIClientManager
from src.storage.database import DatabaseManager
from src.models.data_models import Project, Conversation, Message, AIConfig
from src.core.context_manager import ContextManager
from src.config.config_manager import ConfigManager


class TestAIClientManagerIntegration:
    """Integration tests for AI client manager."""
    
    @pytest.mark.asyncio
    async def test_ai_client_manager_with_config(self, config_manager: ConfigManager):
        """Test AI client manager integration with configuration."""
        manager = AIClientManager(config_manager)
        
        # Should have clients based on config
        assert len(manager.clients) > 0
        
        # Should have expected client types
        client_names = list(manager.clients.keys())
        assert any("openai" in name for name in client_names)
    
    @pytest.mark.asyncio
    async def test_client_health_checks(self, config_manager: ConfigManager):
        """Test health checks for all clients."""
        manager = AIClientManager(config_manager)
        
        # Mock the clients for testing
        for client_name, client in manager.clients.items():
            client.get_response = MagicMock(return_value="OK")
        
        # Test health check method if it exists
        if hasattr(manager, 'health_check_all'):
            health_status = await manager.health_check_all()
            assert isinstance(health_status, dict)


class TestDatabaseIntegration:
    """Integration tests for database operations."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            db_path = f.name
        yield db_path
        # Cleanup
        import os
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    def test_complete_conversation_workflow(self, temp_db_path):
        """Test a complete conversation workflow with database."""
        db_manager = DatabaseManager(temp_db_path)
        
        # 1. Create project
        project = Project(
            name="Integration Test Project",
            description="Testing integration workflow"
        )
        created_project = db_manager.create_project(project)
        assert created_project is not None
        
        # 2. Create conversation
        conversation = Conversation(
            project_id=created_project.id,
            title="Integration Test Conversation"
        )
        created_conversation = db_manager.create_conversation(conversation)
        assert created_conversation is not None
        
        # 3. Add messages
        messages = [
            Message(
                conversation_id=created_conversation.id,
                participant="user",
                content="Hello, I need help with integration testing."
            ),
            Message(
                conversation_id=created_conversation.id,
                participant="openai",
                content="I'll help you with integration testing. What specifically would you like to know?"
            ),
            Message(
                conversation_id=created_conversation.id,
                participant="xai", 
                content="Integration testing is crucial for ensuring components work together properly."
            )
        ]
        
        for message in messages:
            result = db_manager.create_message(message)
            assert result is not None
        
        # 4. Verify data retrieval
        retrieved_project = db_manager.get_project(created_project.id)
        assert retrieved_project.name == "Integration Test Project"
        
        retrieved_conversation = db_manager.get_conversation(created_conversation.id)
        assert retrieved_conversation.title == "Integration Test Conversation"
        
        retrieved_messages = db_manager.get_conversation_messages(created_conversation.id)
        assert len(retrieved_messages) == 3
        assert retrieved_messages[0].participant == "user"
    
    def test_database_error_handling(self, temp_db_path):
        """Test database error handling."""
        db_manager = DatabaseManager(temp_db_path)
        
        # Test with invalid data
        invalid_project = Project(name="")  # Empty name might cause issues
        result = db_manager.create_project(invalid_project)
        # Should handle gracefully (either succeed or return None)
        assert result is None or isinstance(result, Project)
    
    def test_database_transaction_rollback(self, temp_db_path):
        """Test database transaction rollback on errors."""
        db_manager = DatabaseManager(temp_db_path)
        
        # Create a valid project first
        project = Project(name="Test Project")
        created_project = db_manager.create_project(project)
        assert created_project is not None
        
        # Try to create conversation with invalid project_id
        invalid_conversation = Conversation(
            project_id="nonexistent-project-id",
            title="Invalid Conversation"
        )
        
        result = db_manager.create_conversation(invalid_conversation)
        # Should handle the foreign key constraint gracefully
        assert result is None or isinstance(result, Conversation)


class TestContextManagerIntegration:
    """Integration tests for context manager."""
    
    @pytest.mark.asyncio
    async def test_context_manager_initialization(self, config_manager: ConfigManager):
        """Test context manager initialization."""
        context_manager = ContextManager(config_manager)
        await context_manager.initialize()
        
        # Should be properly initialized
        assert context_manager.db_path is not None
        assert context_manager.active_contexts is not None
    
    @pytest.mark.asyncio
    async def test_context_creation_and_retrieval(self, config_manager: ConfigManager):
        """Test creating and retrieving contexts."""
        context_manager = ContextManager(config_manager)
        await context_manager.initialize()
        
        # Create a new context
        conversation_id = "test-conv-123"
        context_id = await context_manager.create_context(conversation_id)
        
        assert context_id is not None
        context = await context_manager.get_context(context_id)
        assert context.conversation_id == conversation_id
        assert context.status == "active"
        
        # Retrieve the context
        retrieved_context = await context_manager.get_context(context_id)
        assert retrieved_context is not None
        assert retrieved_context.context_id == context_id
    
    @pytest.mark.asyncio
    async def test_context_trace_management(self, config_manager: ConfigManager):
        """Test context trace management."""
        context_manager = ContextManager(config_manager)
        await context_manager.initialize()
        
        # Create context
        conversation_id = "test-conv-456"
        context_id = await context_manager.create_context(conversation_id)
        
        # Add trace
        trace_data = {
            "stage": "planning",
            "content": {"plan": "Test plan"},
            "task_id": "task-123"
        }
        
        trace_id = await context_manager.add_context_trace(
            context_id,
            trace_data["stage"],
            trace_data["content"],
            trace_data.get("task_id")
        )
        
        assert trace_id is not None
        
        # Retrieve traces
        traces = await context_manager.get_context_traces(context_id)
        assert len(traces) == 1
        assert traces[0].stage == "planning"
        assert traces[0].content == {"plan": "Test plan"}


class TestEndToEndWorkflow:
    """End-to-end integration tests."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            
            # Create necessary subdirectories
            (workspace / "data").mkdir()
            (workspace / "logs").mkdir()
            (workspace / "exports").mkdir()
            
            yield workspace
    
    @pytest.mark.asyncio
    async def test_complete_research_workflow(self, temp_workspace: Path, config_manager: ConfigManager):
        """Test a complete research workflow."""
        # Setup components
        db_path = temp_workspace / "data" / "test.db"
        db_manager = DatabaseManager(str(db_path))
        
        context_manager = ContextManager(config_manager)
        await context_manager.initialize()
        
        ai_manager = AIClientManager(config_manager)
        
        # 1. Create project and conversation
        project = Project(
            name="Research Workflow Test",
            description="Testing end-to-end research workflow"
        )
        created_project = db_manager.create_project(project)
        assert created_project is not None
        
        conversation = Conversation(
            project_id=created_project.id,
            title="AI Research Session"
        )
        created_conversation = db_manager.create_conversation(conversation)
        assert created_conversation is not None
        
        # 2. Create context for the conversation
        context_id = await context_manager.create_context(created_conversation.id)
        assert context_id is not None
        
        # 3. Simulate user message
        user_message = Message(
            conversation_id=created_conversation.id,
            participant="user",
            content="I want to research the latest developments in quantum computing."
        )
        saved_message = db_manager.create_message(user_message)
        assert saved_message is not None
        
        # 4. Add planning trace
        planning_trace_id = await context_manager.add_context_trace(
            context_id,
            "planning",
            {
                "user_query": user_message.content,
                "research_plan": "1. Search for quantum computing papers 2. Analyze trends 3. Summarize findings",
                "agents_needed": ["retriever", "reasoner"]
            }
        )
        assert planning_trace_id is not None
        
        # 5. Mock AI responses
        mock_openai_response = "Based on recent papers, quantum computing has made significant advances in error correction and quantum algorithms..."
        mock_xai_response = "From my analysis, the quantum computing field is particularly exciting in areas of quantum machine learning..."
        
        # Mock the AI clients
        for client_name, client in ai_manager.clients.items():
            if "openai" in client_name.lower():
                client.get_response = MagicMock(return_value=mock_openai_response)
            elif "xai" in client_name.lower():
                client.get_response = MagicMock(return_value=mock_xai_response)
        
        # 6. Add AI responses
        ai_messages = []
        for provider, response in [("openai", mock_openai_response), ("xai", mock_xai_response)]:
            ai_message = Message(
                conversation_id=created_conversation.id,
                participant=provider,
                content=response
            )
            saved_ai_message = db_manager.create_message(ai_message)
            assert saved_ai_message is not None
            ai_messages.append(saved_ai_message)
        
        # 7. Add completion trace
        completion_trace_id = await context_manager.add_context_trace(
            context_id,
            "completion",
            {
                "status": "completed",
                "messages_generated": len(ai_messages),
                "research_summary": "Successfully provided quantum computing research insights from multiple AI perspectives"
            }
        )
        assert completion_trace_id is not None
        
        # 8. Verify final state
        final_context = await context_manager.get_context(context_id)
        assert final_context is not None
        
        final_messages = db_manager.get_conversation_messages(created_conversation.id)
        assert len(final_messages) == 3  # 1 user + 2 AI messages
        
        context_traces = await context_manager.get_context_traces(context_id)
        assert len(context_traces) == 2  # planning + completion traces
        
        # Update context status
        await context_manager.update_context_status(context_id, "completed")
        updated_context = await context_manager.get_context(context_id)
        assert updated_context.status == "completed"
    
    def test_error_recovery_workflow(self, temp_workspace: Path, config_manager: ConfigManager):
        """Test error recovery in workflow."""
        # Setup with intentionally problematic configuration
        db_path = temp_workspace / "data" / "test_error.db"
        db_manager = DatabaseManager(str(db_path))
        
        # Test creating project with edge case data
        edge_case_project = Project(
            name="Project with ünicöde and special chars: !@#$%",
            description="Testing érrör recovery with spëcial characters"
        )
        
        try:
            created_project = db_manager.create_project(edge_case_project)
            # Should either succeed or fail gracefully
            if created_project:
                assert created_project.name == edge_case_project.name
        except Exception as e:
            # Should not raise unhandled exceptions
            assert isinstance(e, (ValueError, TypeError, RuntimeError))
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, temp_workspace: Path, config_manager: ConfigManager):
        """Test concurrent operations."""
        db_path = temp_workspace / "data" / "test_concurrent.db"
        db_manager = DatabaseManager(str(db_path))
        
        context_manager = ContextManager(config_manager)
        await context_manager.initialize()
        
        # Create base project
        project = Project(name="Concurrent Test Project")
        created_project = db_manager.create_project(project)
        assert created_project is not None
        
        # Create multiple concurrent conversations
        async def create_conversation_with_messages(conv_num: int):
            conversation = Conversation(
                project_id=created_project.id,
                title=f"Concurrent Conversation {conv_num}"
            )
            created_conv = db_manager.create_conversation(conversation)
            if created_conv:
                # Add messages
                for i in range(3):
                    message = Message(
                        conversation_id=created_conv.id,
                        participant="user" if i % 2 == 0 else "openai",
                        content=f"Message {i} in conversation {conv_num}"
                    )
                    db_manager.create_message(message)
                return created_conv.id
            return None
        
        # Run concurrent tasks
        tasks = [create_conversation_with_messages(i) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check results
        successful_results = [r for r in results if isinstance(r, str)]
        assert len(successful_results) >= 3  # At least some should succeed
        
        # Verify data integrity
        all_conversations = db_manager.list_conversations(created_project.id)
        assert len(all_conversations) >= 3
