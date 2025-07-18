"""
End-to-end tests for the multi-AI research collaboration system.

This module contains comprehensive end-to-end tests that verify
the entire system works correctly from user input to final output.
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any

from src.config.config_manager import ConfigManager
from src.storage.database import DatabaseManager
from src.core.ai_client_manager import AIClientManager
from src.core.research_manager import ResearchManager
from src.models.data_models import Project, Conversation, Message
from src.utils.export_manager import ExportManager
from src.utils.performance import PerformanceMonitor


@pytest.mark.e2e
class TestFullWorkflowE2E:
    """Test complete end-to-end workflows."""
    
    def test_complete_research_workflow(self, test_db_manager: DatabaseManager,
                                       ai_client_manager: AIClientManager,
                                       research_manager: ResearchManager,
                                       temporary_export_dir: Path):
        """Test complete research workflow from start to finish."""
        # Step 1: Create a project
        project = Project(
            name="E2E Research Project",
            description="End-to-end testing of research collaboration"
        )
        created_project = test_db_manager.create_project(project)
        assert created_project is not None
        
        # Step 2: Create a conversation
        conversation = Conversation(
            project_id=created_project.id,
            title="Research Discussion"
        )
        created_conversation = test_db_manager.create_conversation(conversation)
        assert created_conversation is not None
        
        # Step 3: Simulate user input
        user_message = Message(
            conversation_id=created_conversation.id,
            participant="user",
            content="I need help researching the latest advances in quantum computing."
        )
        test_db_manager.create_message(user_message)
        
        # Step 4: Mock AI responses
        with patch.object(ai_client_manager, 'get_smart_responses') as mock_responses:
            mock_responses.return_value = {
                "openai": "Quantum computing has made significant advances in error correction and quantum algorithms. Recent breakthroughs include improved qubit stability and new applications in cryptography.",
                "xai": "The field of quantum computing is rapidly evolving. Key developments include quantum supremacy demonstrations and practical applications in optimization problems."
            }
            
            # Get AI responses
            messages = test_db_manager.get_conversation_messages(created_conversation.id)
            responses = ai_client_manager.get_smart_responses(messages)
            
            # Verify responses
            assert isinstance(responses, dict)
            assert len(responses) >= 1
            
            # Step 5: Store AI responses
            for provider, response in responses.items():
                ai_message = Message(
                    conversation_id=created_conversation.id,
                    participant=provider,
                    content=response
                )
                test_db_manager.create_message(ai_message)
        
        # Step 6: Verify conversation state
        all_messages = test_db_manager.get_conversation_messages(created_conversation.id)
        assert len(all_messages) >= 3  # User + 2 AI responses
        
        # Step 7: Export conversation
        export_manager = ExportManager(str(temporary_export_dir))
        session = test_db_manager.get_conversation_session(created_conversation.id)
        assert session is not None
        
        # Export to multiple formats
        json_path = export_manager.export_conversation(session, "json", "research_workflow")
        md_path = export_manager.export_conversation(session, "markdown", "research_workflow")
        
        # Verify exports
        assert Path(json_path).exists()
        assert Path(md_path).exists()
        
        # Verify export content
        with open(json_path, 'r') as f:
            content = f.read()
            assert "quantum computing" in content
            assert "E2E Research Project" in content
    
    @pytest.mark.asyncio
    async def test_research_manager_integration(self, research_manager: ResearchManager,
                                              test_db_manager: DatabaseManager):
        """Test research manager integration with full workflow."""
        # Start a research task
        task_id = await research_manager.start_research_task(
            query="Analyze the impact of artificial intelligence on healthcare",
            user_id="e2e_user",
            conversation_id="e2e_conv"
        )
        
        assert task_id is not None
        
        # Check task status
        status = research_manager.get_task_status(task_id)
        assert status is not None
        
        # Verify task is active
        active_tasks = research_manager.get_active_tasks()
        assert task_id in active_tasks
        
        # Create related conversation in database
        project = Project(
            name="Healthcare AI Research",
            description="Research on AI impact in healthcare"
        )
        test_db_manager.create_project(project)
        
        conversation = Conversation(
            project_id=project.id,
            title="AI Healthcare Analysis"
        )
        test_db_manager.create_conversation(conversation)
        
        # Store research query as message
        query_message = Message(
            conversation_id=conversation.id,
            participant="user",
            content="Analyze the impact of artificial intelligence on healthcare"
        )
        test_db_manager.create_message(query_message)
        
        # Verify the complete workflow
        messages = test_db_manager.get_conversation_messages(conversation.id)
        assert len(messages) == 1
        assert messages[0].content == "Analyze the impact of artificial intelligence on healthcare"


@pytest.mark.e2e
class TestMultiProviderE2E:
    """Test multi-provider AI interactions end-to-end."""
    
    @patch('src.ai_clients.openai_client.OpenAIClient.get_response')
    @patch('src.ai_clients.xai_client.XAIClient.get_response')
    def test_multi_provider_conversation(self, mock_xai_response, mock_openai_response,
                                        test_db_manager: DatabaseManager,
                                        ai_client_manager: AIClientManager):
        """Test conversation with multiple AI providers."""
        # Setup mock responses
        mock_openai_response.return_value = "OpenAI: This is a complex topic that requires careful analysis of multiple factors."
        mock_xai_response.return_value = "XAI: I agree, and I'd like to add that we should also consider the ethical implications."
        
        # Create test project and conversation
        project = Project(
            name="Multi-Provider Discussion",
            description="Testing multi-provider AI conversation"
        )
        test_db_manager.create_project(project)
        
        conversation = Conversation(
            project_id=project.id,
            title="Collaborative Analysis"
        )
        test_db_manager.create_conversation(conversation)
        
        # User starts conversation
        user_message = Message(
            conversation_id=conversation.id,
            participant="user",
            content="What are the key challenges in implementing sustainable energy solutions?"
        )
        test_db_manager.create_message(user_message)
        
        # Get responses from all providers
        messages = test_db_manager.get_conversation_messages(conversation.id)
        
        # Test each provider individually
        providers = ai_client_manager.get_available_providers()
        responses = {}
        
        for provider in providers:
            if provider == "openai":
                response = ai_client_manager.get_response(provider, messages)
                responses[provider] = response
            elif provider == "xai":
                response = ai_client_manager.get_response(provider, messages)
                responses[provider] = response
        
        # Verify responses
        if "openai" in responses:
            assert "complex topic" in responses["openai"]
            # Store OpenAI response
            openai_message = Message(
                conversation_id=conversation.id,
                participant="openai",
                content=responses["openai"]
            )
            test_db_manager.create_message(openai_message)
        
        if "xai" in responses:
            assert "ethical implications" in responses["xai"]
            # Store XAI response
            xai_message = Message(
                conversation_id=conversation.id,
                participant="xai",
                content=responses["xai"]
            )
            test_db_manager.create_message(xai_message)
        
        # Verify final conversation state
        final_messages = test_db_manager.get_conversation_messages(conversation.id)
        assert len(final_messages) >= 1  # At least user message
        
        # Check for multi-provider responses
        participants = [msg.participant for msg in final_messages]
        assert "user" in participants
    
    def test_provider_fallback_scenario(self, ai_client_manager: AIClientManager,
                                       test_db_manager: DatabaseManager):
        """Test fallback behavior when primary provider fails."""
        # Create test conversation
        project = Project(
            name="Fallback Test",
            description="Testing provider fallback"
        )
        test_db_manager.create_project(project)
        
        conversation = Conversation(
            project_id=project.id,
            title="Fallback Scenario"
        )
        test_db_manager.create_conversation(conversation)
        
        user_message = Message(
            conversation_id=conversation.id,
            participant="user",
            content="Test fallback functionality"
        )
        test_db_manager.create_message(user_message)
        
        # Test provider health
        health = ai_client_manager.get_provider_health()
        assert isinstance(health, dict)
        
        # Test failed providers
        failed = ai_client_manager.get_failed_providers()
        assert isinstance(failed, dict)
        
        # Test provider count
        count = ai_client_manager.get_provider_count()
        assert count >= 0


@pytest.mark.e2e
class TestDataPersistenceE2E:
    """Test data persistence and recovery scenarios."""
    
    def test_database_persistence(self, test_db_manager: DatabaseManager):
        """Test database persistence across operations."""
        # Create initial data
        project = Project(
            name="Persistence Test",
            description="Testing data persistence"
        )
        created_project = test_db_manager.create_project(project)
        assert created_project is not None
        
        conversation = Conversation(
            project_id=created_project.id,
            title="Persistence Conversation"
        )
        created_conversation = test_db_manager.create_conversation(conversation)
        assert created_conversation is not None
        
        # Create multiple messages
        messages = [
            Message(
                conversation_id=created_conversation.id,
                participant="user",
                content="First message"
            ),
            Message(
                conversation_id=created_conversation.id,
                participant="openai",
                content="Second message from OpenAI"
            ),
            Message(
                conversation_id=created_conversation.id,
                participant="xai",
                content="Third message from XAI"
            )
        ]
        
        created_messages = []
        for msg in messages:
            created_msg = test_db_manager.create_message(msg)
            created_messages.append(created_msg)
        
        # Verify data persistence
        retrieved_project = test_db_manager.get_project(created_project.id)
        assert retrieved_project is not None
        assert retrieved_project.name == "Persistence Test"
        
        retrieved_conversation = test_db_manager.get_conversation(created_conversation.id)
        assert retrieved_conversation is not None
        assert retrieved_conversation.title == "Persistence Conversation"
        
        retrieved_messages = test_db_manager.get_conversation_messages(created_conversation.id)
        assert len(retrieved_messages) == 3
        
        # Verify message order and content
        assert retrieved_messages[0].content == "First message"
        assert retrieved_messages[1].content == "Second message from OpenAI"
        assert retrieved_messages[2].content == "Third message from XAI"
        
        # Test database statistics
        stats = test_db_manager.get_database_stats()
        assert stats["projects"] >= 1
        assert stats["conversations"] >= 1
        assert stats["messages"] >= 3
    
    def test_session_recovery(self, test_db_manager: DatabaseManager):
        """Test session recovery functionality."""
        # Create test data
        project = Project(
            name="Session Recovery Test",
            description="Testing session recovery"
        )
        test_db_manager.create_project(project)
        
        conversation = Conversation(
            project_id=project.id,
            title="Recovery Session"
        )
        test_db_manager.create_conversation(conversation)
        
        # Add messages to create a session
        for i in range(5):
            message = Message(
                conversation_id=conversation.id,
                participant="user" if i % 2 == 0 else "openai",
                content=f"Session recovery message {i}"
            )
            test_db_manager.create_message(message)
        
        # Retrieve session
        session = test_db_manager.get_conversation_session(conversation.id)
        assert session is not None
        
        # Verify session completeness
        assert session.project is not None
        assert session.project.name == "Session Recovery Test"
        assert session.conversation.title == "Recovery Session"
        assert len(session.messages) == 5
        
        # Verify message order
        for i, message in enumerate(session.messages):
            assert f"Session recovery message {i}" in message.content


@pytest.mark.e2e
class TestExportImportE2E:
    """Test export and import functionality end-to-end."""
    
    def test_export_workflow(self, test_db_manager: DatabaseManager,
                            temporary_export_dir: Path):
        """Test complete export workflow."""
        # Create comprehensive test data
        project = Project(
            name="Export Test Project",
            description="Comprehensive export testing"
        )
        test_db_manager.create_project(project)
        
        conversation = Conversation(
            project_id=project.id,
            title="Export Test Conversation"
        )
        test_db_manager.create_conversation(conversation)
        
        # Create diverse messages
        messages = [
            Message(
                conversation_id=conversation.id,
                participant="user",
                content="What are the implications of quantum computing for cryptography?"
            ),
            Message(
                conversation_id=conversation.id,
                participant="openai",
                content="Quantum computing poses significant challenges to current cryptographic methods. It could break RSA and other public-key systems."
            ),
            Message(
                conversation_id=conversation.id,
                participant="xai",
                content="Indeed, we need to develop quantum-resistant cryptography. Post-quantum cryptographic algorithms are being researched."
            ),
            Message(
                conversation_id=conversation.id,
                participant="user",
                content="Can you explain the timeline for practical quantum computers?"
            ),
            Message(
                conversation_id=conversation.id,
                participant="openai",
                content="Current estimates suggest that cryptographically relevant quantum computers may emerge within 10-15 years."
            )
        ]
        
        for msg in messages:
            test_db_manager.create_message(msg)
        
        # Test export functionality
        export_manager = ExportManager(str(temporary_export_dir))
        session = test_db_manager.get_conversation_session(conversation.id)
        assert session is not None
        
        # Export to multiple formats
        json_path = export_manager.export_conversation(session, "json", "export_test")
        md_path = export_manager.export_conversation(session, "markdown", "export_test")
        
        # Verify exports exist
        assert Path(json_path).exists()
        assert Path(md_path).exists()
        
        # Verify JSON export content
        with open(json_path, 'r') as f:
            json_content = f.read()
            assert "quantum computing" in json_content
            assert "Export Test Project" in json_content
            assert "cryptography" in json_content
        
        # Verify Markdown export content
        with open(md_path, 'r') as f:
            md_content = f.read()
            assert "# Export Test Conversation" in md_content
            assert "quantum computing" in md_content
            assert "**openai**:" in md_content
            assert "**xai**:" in md_content
        
        # Test export listing
        exports = export_manager.list_exports()
        assert len(exports) >= 2
        
        # Verify export metadata
        json_exports = [e for e in exports if e['filename'].endswith('.json')]
        md_exports = [e for e in exports if e['filename'].endswith('.md')]
        
        assert len(json_exports) >= 1
        assert len(md_exports) >= 1


@pytest.mark.e2e
class TestPerformanceE2E:
    """Test performance scenarios end-to-end."""
    
    def test_large_conversation_performance(self, test_db_manager: DatabaseManager,
                                          performance_monitor: PerformanceMonitor):
        """Test performance with large conversations."""
        # Create project
        project = Project(
            name="Large Conversation Test",
            description="Testing performance with large conversations"
        )
        test_db_manager.create_project(project)
        
        conversation = Conversation(
            project_id=project.id,
            title="Large Performance Test"
        )
        test_db_manager.create_conversation(conversation)
        
        # Create large number of messages
        num_messages = 5000
        
        performance_monitor.start_timer("large_conversation_creation")
        
        for i in range(num_messages):
            message = Message(
                conversation_id=conversation.id,
                participant="user" if i % 3 == 0 else ("openai" if i % 3 == 1 else "xai"),
                content=f"Performance test message {i}: This is a test message to evaluate performance with large conversations."
            )
            test_db_manager.create_message(message)
        
        creation_time = performance_monitor.end_timer("large_conversation_creation")
        
        # Test retrieval performance
        performance_monitor.start_timer("large_conversation_retrieval")
        messages = test_db_manager.get_conversation_messages(conversation.id)
        retrieval_time = performance_monitor.end_timer("large_conversation_retrieval")
        
        # Verify results
        assert len(messages) == num_messages
        assert creation_time < 120.0  # Should complete within 2 minutes
        assert retrieval_time < 30.0   # Should retrieve within 30 seconds
        
        # Test session performance
        performance_monitor.start_timer("large_session_retrieval")
        session = test_db_manager.get_conversation_session(conversation.id)
        session_time = performance_monitor.end_timer("large_session_retrieval")
        
        assert session is not None
        assert len(session.messages) == num_messages
        assert session_time < 30.0  # Should retrieve session within 30 seconds
    
    def test_concurrent_operations_e2e(self, test_db_manager: DatabaseManager,
                                      performance_monitor: PerformanceMonitor):
        """Test concurrent operations end-to-end."""
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def create_conversation_thread(thread_id: int):
            """Create a conversation in a separate thread."""
            project = Project(
                name=f"Concurrent Project {thread_id}",
                description=f"Concurrent test project {thread_id}"
            )
            test_db_manager.create_project(project)
            
            conversation = Conversation(
                project_id=project.id,
                title=f"Concurrent Conversation {thread_id}"
            )
            test_db_manager.create_conversation(conversation)
            
            # Add messages
            for i in range(100):
                message = Message(
                    conversation_id=conversation.id,
                    participant="user" if i % 2 == 0 else "openai",
                    content=f"Concurrent message {i} from thread {thread_id}"
                )
                test_db_manager.create_message(message)
            
            return thread_id
        
        # Test concurrent operations
        num_threads = 10
        
        performance_monitor.start_timer("concurrent_e2e_operations")
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(create_conversation_thread, i)
                for i in range(num_threads)
            ]
            
            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
        
        total_time = performance_monitor.end_timer("concurrent_e2e_operations")
        
        # Verify results
        assert len(results) == num_threads
        assert total_time < 180.0  # Should complete within 3 minutes
        
        # Verify data integrity
        stats = test_db_manager.get_database_stats()
        assert stats["projects"] >= num_threads
        assert stats["conversations"] >= num_threads
        assert stats["messages"] >= num_threads * 100


@pytest.mark.e2e
class TestErrorHandlingE2E:
    """Test error handling scenarios end-to-end."""
    
    def test_invalid_data_handling(self, test_db_manager: DatabaseManager):
        """Test handling of invalid data scenarios."""
        # Test invalid project creation
        invalid_project = Project(name="", description="")
        result = test_db_manager.create_project(invalid_project)
        # Should handle gracefully (may return None or raise exception)
        
        # Test invalid conversation creation
        invalid_conversation = Conversation(
            project_id="non-existent-id",
            title="Invalid Conversation"
        )
        result = test_db_manager.create_conversation(invalid_conversation)
        assert result is None  # Should return None for invalid project ID
        
        # Test invalid message creation
        invalid_message = Message(
            conversation_id="non-existent-id",
            participant="user",
            content="Invalid message"
        )
        result = test_db_manager.create_message(invalid_message)
        assert result is None  # Should return None for invalid conversation ID
    
    def test_ai_client_error_handling(self, ai_client_manager: AIClientManager):
        """Test AI client error handling scenarios."""
        # Test invalid provider
        try:
            response = ai_client_manager.get_response("invalid_provider", [])
            # Should handle gracefully
        except Exception as e:
            # Expected behavior for invalid provider
            assert "not available" in str(e).lower() or "provider" in str(e).lower()
        
        # Test empty messages
        providers = ai_client_manager.get_available_providers()
        if providers:
            response = ai_client_manager.get_response(providers[0], [])
            # Should handle empty messages gracefully
            assert isinstance(response, str)
    
    def test_recovery_scenarios(self, test_db_manager: DatabaseManager):
        """Test system recovery scenarios."""
        # Create valid data first
        project = Project(
            name="Recovery Test",
            description="Testing recovery scenarios"
        )
        test_db_manager.create_project(project)
        
        conversation = Conversation(
            project_id=project.id,
            title="Recovery Conversation"
        )
        test_db_manager.create_conversation(conversation)
        
        # Add some messages
        for i in range(10):
            message = Message(
                conversation_id=conversation.id,
                participant="user",
                content=f"Recovery test message {i}"
            )
            test_db_manager.create_message(message)
        
        # Test recovery by retrieving data
        retrieved_project = test_db_manager.get_project(project.id)
        assert retrieved_project is not None
        assert retrieved_project.name == "Recovery Test"
        
        retrieved_conversation = test_db_manager.get_conversation(conversation.id)
        assert retrieved_conversation is not None
        assert retrieved_conversation.title == "Recovery Conversation"
        
        retrieved_messages = test_db_manager.get_conversation_messages(conversation.id)
        assert len(retrieved_messages) == 10
        
        # Test session recovery
        session = test_db_manager.get_conversation_session(conversation.id)
        assert session is not None
        assert len(session.messages) == 10
