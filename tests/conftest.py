"""
Pytest configuration and shared fixtures for Phase 6 testing suite.

This module provides shared fixtures and configuration for comprehensive
testing of the multi-AI research collaboration system.
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any, AsyncGenerator, Generator
from unittest.mock import MagicMock, AsyncMock

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.config.config_manager import ConfigManager
from src.storage.database import DatabaseManager
from src.core.ai_client_manager import AIClientManager
from src.core.research_manager import ResearchManager
from src.models.data_models import Project, Conversation, Message


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def config_manager() -> ConfigManager:
    """Provide a test configuration manager."""
    return ConfigManager()


@pytest.fixture
def test_db_manager(config_manager: ConfigManager) -> DatabaseManager:
    """Provide a test database manager with in-memory database."""
    return DatabaseManager(":memory:")


@pytest.fixture
def ai_client_manager(config_manager: ConfigManager) -> AIClientManager:
    """Provide a test AI client manager."""
    return AIClientManager(config_manager)


@pytest.fixture
async def research_manager(config_manager: ConfigManager) -> AsyncGenerator[ResearchManager, None]:
    """Provide a test research manager."""
    manager = ResearchManager(config_manager)
    yield manager
    # Cleanup any active tasks
    if hasattr(manager, 'active_contexts'):
        manager.active_contexts.clear()


@pytest.fixture
def sample_project(test_db_manager: DatabaseManager) -> Project:
    """Create a sample project for testing."""
    project = Project(
        name="Test Project",
        description="A sample project for testing"
    )
    test_db_manager.create_project(project)
    return project


@pytest.fixture
def sample_conversation(test_db_manager: DatabaseManager, sample_project: Project) -> Conversation:
    """Create a sample conversation for testing."""
    conversation = Conversation(
        project_id=sample_project.id,
        title="Test Conversation"
    )
    test_db_manager.create_conversation(conversation)
    return conversation


@pytest.fixture
def sample_messages(test_db_manager: DatabaseManager, sample_conversation: Conversation) -> list[Message]:
    """Create sample messages for testing."""
    messages = [
        Message(
            conversation_id=sample_conversation.id,
            participant="user",
            content="What are the benefits of AI collaboration?"
        ),
        Message(
            conversation_id=sample_conversation.id,
            participant="openai",
            content="AI collaboration offers several benefits including diverse perspectives, enhanced problem-solving capabilities, and improved accuracy through cross-validation."
        ),
        Message(
            conversation_id=sample_conversation.id,
            participant="xai",
            content="Additionally, AI collaboration can help reduce bias by incorporating multiple AI systems with different training approaches and strengths."
        )
    ]
    
    for message in messages:
        test_db_manager.create_message(message)
    
    return messages


@pytest.fixture
def mock_websocket():
    """Provide a mock WebSocket for testing."""
    websocket = MagicMock()
    websocket.send = AsyncMock()
    websocket.receive = AsyncMock()
    websocket.close = AsyncMock()
    return websocket


@pytest.fixture
def mock_ai_response() -> Dict[str, Any]:
    """Provide mock AI response data for testing."""
    return {
        "id": "test-response-123",
        "choices": [
            {
                "message": {
                    "content": "This is a test AI response for unit testing purposes.",
                    "role": "assistant"
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 15,
            "total_tokens": 25
        }
    }


@pytest.fixture
def mock_research_context():
    """Provide mock research context for testing."""
    from src.core.research_manager import ResearchContext
    
    return ResearchContext(
        task_id="test-task-123",
        query="What are the applications of quantum computing?",
        user_id="test-user-456",
        conversation_id="test-conv-789",
        context_data={"priority": "high", "deadline": "2024-01-31"}
    )


@pytest.fixture
def temporary_export_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Provide a temporary directory for export testing."""
    export_dir = tmp_path / "test_exports"
    export_dir.mkdir()
    yield export_dir
    # Cleanup is handled by pytest's tmp_path fixture


@pytest.fixture
def performance_test_config() -> Dict[str, Any]:
    """Provide configuration for performance testing."""
    return {
        "max_response_time": 1.0,  # seconds
        "max_memory_usage": 100 * 1024 * 1024,  # 100MB
        "max_concurrent_requests": 10,
        "test_duration": 30,  # seconds
        "warmup_duration": 5,  # seconds
    }


@pytest.fixture
def test_environment_variables() -> Generator[None, None, None]:
    """Set up test environment variables."""
    original_env = os.environ.copy()
    
    # Set test environment variables
    os.environ["TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"
    os.environ["DATABASE_URL"] = ":memory:"
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_agent_response():
    """Provide mock agent response for testing."""
    from src.mcp.protocols import AgentResponse
    
    return AgentResponse(
        task_id="test-task-123",
        context_id="test-context-456",
        agent_type="Retriever",
        status="completed",
        result={
            "success": True,
            "data": ["result1", "result2", "result3"],
            "metadata": {"source": "test", "timestamp": "2024-01-15T10:00:00Z"}
        }
    )


# Define custom pytest markers for test organization
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "performance: mark test as performance test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow-running test")
