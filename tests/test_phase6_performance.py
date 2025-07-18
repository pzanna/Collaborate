"""
Performance tests for the multi-AI research collaboration system.

This module contains performance tests that verify the system performs
well under various load conditions and scales appropriately.
"""

import pytest
import asyncio
import time
import gc
from typing import Dict, List, Any
from unittest.mock import Mock, AsyncMock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.config.config_manager import ConfigManager
from src.storage.database import DatabaseManager
from src.core.ai_client_manager import AIClientManager
from src.core.research_manager import ResearchManager
from src.models.data_models import Project, Conversation, Message
from src.utils.performance import PerformanceMonitor


@pytest.mark.performance
class TestDatabasePerformance:
    """Test database performance under load."""
    
    def test_project_creation_performance(self, test_db_manager: DatabaseManager, 
                                        performance_monitor: PerformanceMonitor):
        """Test project creation performance."""
        num_projects = 1000
        
        # Start timing
        performance_monitor.start_timer("project_creation")
        
        for i in range(num_projects):
            project = Project(
                name=f"Performance Test Project {i}",
                description=f"Performance test project {i}"
            )
            test_db_manager.create_project(project)
        
        # End timing
        creation_time = performance_monitor.end_timer("project_creation")
        
        # Verify all projects were created
        all_projects = test_db_manager.list_projects()
        assert len(all_projects) >= num_projects
        
        # Check performance metrics
        stats = performance_monitor.get_stats("project_creation")
        assert stats["count"] >= 1
        
        # Project creation should be reasonably fast
        assert creation_time < 10.0  # Should complete within 10 seconds
    
    def test_conversation_creation_performance(self, test_db_manager: DatabaseManager,
                                             performance_monitor: PerformanceMonitor):
        """Test conversation creation performance."""
        # Create a project first
        project = Project(name="Performance Test", description="Performance test")
        test_db_manager.create_project(project)
        
        num_conversations = 1000
        
        # Start timing
        performance_monitor.start_timer("conversation_creation")
        
        for i in range(num_conversations):
            conversation = Conversation(
                project_id=project.id,
                title=f"Performance Test Conversation {i}"
            )
            test_db_manager.create_conversation(conversation)
        
        # End timing
        creation_time = performance_monitor.end_timer("conversation_creation")
        
        # Verify all conversations were created
        all_conversations = test_db_manager.list_conversations()
        assert len(all_conversations) >= num_conversations
        
        # Check performance metrics
        stats = performance_monitor.get_stats("conversation_creation")
        assert stats["count"] >= 1
        
        # Conversation creation should be reasonably fast
        assert creation_time < 10.0  # Should complete within 10 seconds
    
    def test_message_creation_performance(self, test_db_manager: DatabaseManager,
                                        performance_monitor: PerformanceMonitor):
        """Test message creation performance."""
        # Create test data
        project = Project(name="Performance Test", description="Performance test")
        test_db_manager.create_project(project)
        
        conversation = Conversation(
            project_id=project.id,
            title="Performance Test Conversation"
        )
        test_db_manager.create_conversation(conversation)
        
        num_messages = 10000
        
        # Start timing
        performance_monitor.start_timer("message_creation")
        
        for i in range(num_messages):
            message = Message(
                conversation_id=conversation.id,
                participant="user" if i % 2 == 0 else "openai",
                content=f"Performance test message {i}"
            )
            test_db_manager.create_message(message)
        
        # End timing
        creation_time = performance_monitor.end_timer("message_creation")
        
        # Verify all messages were created
        all_messages = test_db_manager.get_conversation_messages(conversation.id)
        assert len(all_messages) >= num_messages
        
        # Check performance metrics
        stats = performance_monitor.get_stats("message_creation")
        assert stats["count"] >= 1
        
        # Message creation should be reasonably fast
        assert creation_time < 30.0  # Should complete within 30 seconds
    
    def test_database_query_performance(self, test_db_manager: DatabaseManager,
                                       performance_monitor: PerformanceMonitor):
        """Test database query performance."""
        # Create test data
        project = Project(name="Query Performance Test", description="Query performance test")
        test_db_manager.create_project(project)
        
        conversations = []
        for i in range(100):
            conversation = Conversation(
                project_id=project.id,
                title=f"Query Test Conversation {i}"
            )
            created_conversation = test_db_manager.create_conversation(conversation)
            if created_conversation:
                conversations.append(created_conversation)
                
                # Add messages to each conversation
                for j in range(50):
                    message = Message(
                        conversation_id=created_conversation.id,
                        participant="user" if j % 2 == 0 else "openai",
                        content=f"Query test message {j} in conversation {i}"
                    )
                    test_db_manager.create_message(message)
        
        # Test query performance
        performance_monitor.start_timer("project_queries")
        for _ in range(100):
            test_db_manager.get_project(project.id)
        query_time = performance_monitor.end_timer("project_queries")
        
        # Queries should be fast
        assert query_time < 5.0


@pytest.mark.performance
@pytest.mark.asyncio
class TestAIClientPerformance:
    """Test AI client performance under load."""
    
    @patch('src.ai_clients.openai_client.OpenAIClient.get_response')
    async def test_concurrent_ai_requests(self, mock_get_response, 
                                         ai_client_manager: AIClientManager,
                                         performance_monitor: PerformanceMonitor):
        """Test concurrent AI request performance."""
        # Mock responses
        mock_get_response.return_value = "This is a test response"
        
        # Create test messages
        messages = [
            Message(
                conversation_id="test-conv",
                participant="user",
                content="Test message for performance testing"
            )
        ]
        
        # Get available providers
        providers = ai_client_manager.get_available_providers()
        if not providers:
            pytest.skip("No AI providers available")
        
        provider = providers[0]
        num_requests = 100
        
        # Start timing
        performance_monitor.start_timer("concurrent_ai_requests")
        
        # Use ThreadPoolExecutor to simulate concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(ai_client_manager.get_response, provider, messages)
                for _ in range(num_requests)
            ]
            
            responses = []
            for future in as_completed(futures):
                response = future.result()
                responses.append(response)
        
        # End timing
        total_time = performance_monitor.end_timer("concurrent_ai_requests")
        
        # Verify responses
        assert len(responses) == num_requests
        assert all(response == "This is a test response" for response in responses)
        
        # Concurrent requests should be reasonably fast
        assert total_time < 30.0  # Should complete within 30 seconds


@pytest.mark.performance
@pytest.mark.asyncio
class TestResearchManagerPerformance:
    """Test research manager performance under load."""
    
    async def test_concurrent_research_tasks(self, research_manager: ResearchManager,
                                           performance_monitor: PerformanceMonitor):
        """Test concurrent research task performance."""
        num_tasks = 20
        
        # Start timing
        performance_monitor.start_timer("concurrent_research_tasks")
        
        # Start multiple research tasks concurrently
        tasks = []
        for i in range(num_tasks):
            task = asyncio.create_task(
                research_manager.start_research_task(
                    query=f"Research query {i}",
                    user_id=f"user-{i}",
                    conversation_id=f"conv-{i}"
                )
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        task_ids = await asyncio.gather(*tasks)
        
        # End timing
        total_time = performance_monitor.end_timer("concurrent_research_tasks")
        
        # Verify all tasks were created
        assert len(task_ids) == num_tasks
        assert all(task_id is not None for task_id in task_ids)
        
        # Check active tasks
        active_tasks = research_manager.get_active_tasks()
        assert len(active_tasks) == num_tasks
        
        # Task creation should be reasonably fast
        assert total_time < 10.0  # Should complete within 10 seconds


@pytest.mark.performance
class TestMemoryPerformance:
    """Test memory performance and leak detection."""
    
    def test_memory_stability(self, test_db_manager: DatabaseManager,
                             performance_monitor: PerformanceMonitor):
        """Test memory stability under load."""
        # Force garbage collection before test
        gc.collect()
        
        # Create and delete objects repeatedly
        for iteration in range(10):
            projects = []
            conversations = []
            messages = []
            
            # Create objects
            for i in range(100):
                project = Project(
                    name=f"Memory Test Project {iteration}-{i}",
                    description=f"Memory test project {iteration}-{i}"
                )
                created_project = test_db_manager.create_project(project)
                if created_project:
                    projects.append(created_project)
                    
                    conversation = Conversation(
                        project_id=created_project.id,
                        title=f"Memory Test Conversation {iteration}-{i}"
                    )
                    created_conversation = test_db_manager.create_conversation(conversation)
                    if created_conversation:
                        conversations.append(created_conversation)
                        
                        for j in range(10):
                            message = Message(
                                conversation_id=created_conversation.id,
                                participant="user" if j % 2 == 0 else "openai",
                                content=f"Memory test message {j}"
                            )
                            created_message = test_db_manager.create_message(message)
                            if created_message:
                                messages.append(created_message)
            
            # Clear references
            projects.clear()
            conversations.clear()
            messages.clear()
            
            # Force garbage collection
            gc.collect()
        
        # Test should complete without memory errors
        stats = test_db_manager.get_database_stats()
        assert stats["projects"] >= 1000
        assert stats["conversations"] >= 1000
        assert stats["messages"] >= 10000
    
    def test_large_data_handling(self, test_db_manager: DatabaseManager,
                                performance_monitor: PerformanceMonitor):
        """Test handling of large data sets."""
        # Create a project
        project = Project(
            name="Large Data Test",
            description="Testing large data handling"
        )
        test_db_manager.create_project(project)
        
        # Create a conversation
        conversation = Conversation(
            project_id=project.id,
            title="Large Data Conversation"
        )
        test_db_manager.create_conversation(conversation)
        
        # Create many messages with large content
        large_content = "A" * 10000  # 10KB per message
        
        performance_monitor.start_timer("large_data_creation")
        for i in range(1000):  # 10MB total
            message = Message(
                conversation_id=conversation.id,
                participant="user",
                content=f"Message {i}: {large_content}"
            )
            test_db_manager.create_message(message)
        creation_time = performance_monitor.end_timer("large_data_creation")
        
        # Test retrieval performance
        performance_monitor.start_timer("large_data_retrieval")
        messages = test_db_manager.get_conversation_messages(conversation.id)
        retrieval_time = performance_monitor.end_timer("large_data_retrieval")
        
        assert len(messages) == 1000
        assert all(len(msg.content) > 10000 for msg in messages)
        
        # Large data operations should complete within reasonable time
        assert creation_time < 60.0
        assert retrieval_time < 30.0


@pytest.mark.performance
class TestConcurrencyPerformance:
    """Test concurrency performance."""
    
    def test_database_concurrency(self, test_db_manager: DatabaseManager,
                                 performance_monitor: PerformanceMonitor):
        """Test database concurrency performance."""
        num_threads = 10
        operations_per_thread = 100
        
        def database_operations(thread_id: int):
            """Perform database operations in a thread."""
            # Create project
            project = Project(
                name=f"Concurrent Test Project {thread_id}",
                description=f"Concurrent test project {thread_id}"
            )
            test_db_manager.create_project(project)
            
            # Create conversations
            for i in range(operations_per_thread):
                conversation = Conversation(
                    project_id=project.id,
                    title=f"Concurrent Test Conversation {thread_id}-{i}"
                )
                test_db_manager.create_conversation(conversation)
                
                # Create messages
                for j in range(5):
                    message = Message(
                        conversation_id=conversation.id,
                        participant="user" if j % 2 == 0 else "openai",
                        content=f"Concurrent test message {j}"
                    )
                    test_db_manager.create_message(message)
        
        performance_monitor.start_timer("database_concurrency")
        
        # Run concurrent database operations
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(database_operations, i)
                for i in range(num_threads)
            ]
            
            # Wait for all operations to complete
            for future in as_completed(futures):
                future.result()
        
        total_time = performance_monitor.end_timer("database_concurrency")
        
        # Verify all operations completed
        stats = test_db_manager.get_database_stats()
        assert stats["projects"] >= num_threads
        assert stats["conversations"] >= num_threads * operations_per_thread
        assert stats["messages"] >= num_threads * operations_per_thread * 5
        
        # Concurrent operations should be reasonably fast
        assert total_time < 120.0  # Should complete within 2 minutes


@pytest.mark.performance
class TestScalabilityPerformance:
    """Test scalability performance."""
    
    def test_scaling_with_data_size(self, test_db_manager: DatabaseManager,
                                   performance_monitor: PerformanceMonitor):
        """Test performance scaling with increasing data size."""
        data_sizes = [100, 500, 1000, 2000]
        times = []
        
        for size in data_sizes:
            # Create project
            project = Project(
                name=f"Scaling Test Project {size}",
                description=f"Scaling test project {size}"
            )
            test_db_manager.create_project(project)
            
            # Create conversations and messages
            performance_monitor.start_timer(f"scaling_test_{size}")
            
            conversation = Conversation(
                project_id=project.id,
                title=f"Scaling Test Conversation {size}"
            )
            test_db_manager.create_conversation(conversation)
            
            for i in range(size):
                message = Message(
                    conversation_id=conversation.id,
                    participant="user" if i % 2 == 0 else "openai",
                    content=f"Scaling test message {i}"
                )
                test_db_manager.create_message(message)
            
            test_time = performance_monitor.end_timer(f"scaling_test_{size}")
            times.append(test_time)
        
        # Verify scaling performance
        assert len(times) == len(data_sizes)
        
        # Performance should scale reasonably (not exponentially)
        assert times[1] > times[0]  # 500 should take longer than 100
        assert times[2] > times[1]  # 1000 should take longer than 500
        assert times[3] > times[2]  # 2000 should take longer than 1000
        
        # But not exponentially longer
        assert times[3] < times[0] * 100  # 2000 shouldn't take 100x longer than 100
