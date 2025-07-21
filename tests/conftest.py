"""
Shared test fixtures and configuration for the Eunice test suite.

This module provides common fixtures, test data, and configuration
used across multiple test modules.
"""

import asyncio
import pytest
import tempfile
import os
import uuid
from pathlib import Path
from typing import Dict, Any, AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.config.config_manager import ConfigManager
from src.storage.database import DatabaseManager
from src.mcp.server import MCPServer
from src.mcp.protocols import ResearchAction, Priority
from src.core.context_manager import ContextManager


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Provide test configuration data."""
    return {
        "ai_providers": {
            "openai": {
                "model": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 2000,
                "timeout": 30
            },
            "xai": {
                "model": "grok-beta",
                "temperature": 0.7,
                "max_tokens": 2000,
                "timeout": 30
            }
        },
        "storage": {
            "database_path": ":memory:",
            "export_path": "/tmp/test_exports"
        },
        "mcp_server": {
            "host": "127.0.0.1",
            "port": 9001,
            "task_timeout": 60,
            "retry_attempts": 2,
            "max_concurrent_tasks": 5
        },
        "research": {
            "max_concurrent_tasks": 10,
            "default_priority": "normal",
            "task_timeout": 300
        },
        "logging": {
            "level": "INFO",
            "file": "/tmp/test_eunice.log"
        }
    }


@pytest.fixture
def config_manager(test_config: Dict[str, Any], temp_dir: Path) -> ConfigManager:
    """Create a ConfigManager instance for testing."""
    # Create temporary config file
    config_file = temp_dir / "test_config.json"
    
    import json
    with open(config_file, 'w') as f:
        json.dump(test_config, f)
    
    # Override config path
    original_config_path = os.environ.get('CONFIG_PATH')
    os.environ['CONFIG_PATH'] = str(config_file)
    
    manager = ConfigManager()
    
    # Note: ConfigManager doesn't need explicit cleanup for tests
    return manager


@pytest.fixture
def database_manager(temp_dir: Path) -> DatabaseManager:
    """Create a DatabaseManager instance for testing."""
    db_path = ":memory:"  # Use in-memory database for testing
    manager = DatabaseManager(db_path)
    return manager


@pytest.fixture
async def context_manager(config_manager: ConfigManager) -> AsyncGenerator[ContextManager, None]:
    """Create a ContextManager instance for testing."""
    manager = ContextManager(config_manager)
    await manager.initialize()
    yield manager
    # Context manager doesn't have explicit close method, relies on garbage collection


@pytest.fixture
async def mcp_server(config_manager: ConfigManager) -> AsyncGenerator[MCPServer, None]:
    """Create an MCP server instance for testing."""
    server = MCPServer(config_manager)
    await server.start()
    yield server
    await server.stop()


@pytest.fixture
def sample_research_action() -> ResearchAction:
    """Create a sample research action for testing."""
    return ResearchAction(
        task_id=str(uuid.uuid4()),
        context_id=str(uuid.uuid4()),
        agent_type="retriever",
        action="search",
        payload={"query": "test search query", "max_results": 5},
        priority="normal"
    )


@pytest.fixture
def mock_ai_client():
    """Create a mock AI client for testing."""
    client = AsyncMock()
    client.chat = AsyncMock()
    client.stream_chat = AsyncMock()
    client.get_models = AsyncMock(return_value=["gpt-4o-mini", "gpt-4"])
    client.health_check = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_openai_client(mock_ai_client):
    """Create a mock OpenAI client for testing."""
    mock_ai_client.name = "openai"
    mock_ai_client.model = "gpt-4o-mini"
    return mock_ai_client


@pytest.fixture
def mock_xai_client(mock_ai_client):
    """Create a mock xAI client for testing."""
    mock_ai_client.name = "xai"
    mock_ai_client.model = "grok-beta"
    return mock_ai_client


@pytest.fixture
def sample_conversation_data():
    """Provide sample conversation data for testing."""
    return {
        "conversation_id": str(uuid.uuid4()),
        "project_id": str(uuid.uuid4()),
        "messages": [
            {
                "id": str(uuid.uuid4()),
                "role": "user",
                "content": "What is machine learning?",
                "timestamp": "2025-07-19T10:00:00Z"
            },
            {
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "content": "Machine learning is a subset of artificial intelligence...",
                "timestamp": "2025-07-19T10:00:30Z",
                "provider": "openai"
            }
        ],
        "metadata": {
            "created_at": "2025-07-19T10:00:00Z",
            "updated_at": "2025-07-19T10:00:30Z",
            "status": "active"
        }
    }


@pytest.fixture
def sample_export_data():
    """Provide sample export data for testing."""
    return {
        "conversation_id": str(uuid.uuid4()),
        "title": "Test Conversation",
        "participants": ["user", "openai", "xai"],
        "messages": [
            {
                "role": "user",
                "content": "Hello",
                "timestamp": "2025-07-19T10:00:00Z"
            },
            {
                "role": "assistant",
                "content": "Hello! How can I help you?",
                "timestamp": "2025-07-19T10:00:01Z",
                "provider": "openai"
            }
        ],
        "metadata": {
            "export_date": "2025-07-19T10:05:00Z",
            "version": "1.0"
        }
    }


@pytest.fixture
def sample_project(database_manager: DatabaseManager):
    """Create a sample project for testing."""
    from src.models.data_models import Project
    from datetime import datetime
    
    project = Project(
        id=str(uuid.uuid4()),
        name="Test Project",
        description="A test project for integration testing",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # Create the project in the database
    created_project = database_manager.create_project(project)
    return created_project or project


@pytest.fixture
def sample_conversation(database_manager: DatabaseManager, sample_project):
    """Create a sample conversation for testing."""
    from src.models.data_models import Conversation
    from datetime import datetime
    
    conversation = Conversation(
        id=str(uuid.uuid4()),
        project_id=sample_project.id,
        title="Test Conversation",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # Create the conversation in the database
    created_conversation = database_manager.create_conversation(conversation)
    return created_conversation or conversation


@pytest.fixture
def environment_variables(temp_dir: Path):
    """Set up test environment variables."""
    test_env = {
        'OPENAI_API_KEY': 'test-openai-key',
        'XAI_API_KEY': 'test-xai-key',
        'DATABASE_PATH': str(temp_dir / "test.db"),
        'LOG_LEVEL': 'DEBUG',
        'HOST': '127.0.0.1',
        'PORT': '8001',
        'MCP_HOST': '127.0.0.1',
        'MCP_PORT': '9001'
    }
    
    # Store original values
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield test_env
    
    # Restore original environment
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


# Test data constants
TEST_USER_MESSAGES = [
    "What is artificial intelligence?",
    "Explain machine learning concepts",
    "How does neural network training work?",
    "What are the applications of AI in healthcare?",
    "Describe the differences between supervised and unsupervised learning"
]

TEST_RESEARCH_QUERIES = [
    "Latest developments in quantum computing",
    "Impact of climate change on marine ecosystems",
    "Advances in renewable energy technology",
    "Applications of blockchain in supply chain management",
    "Ethical considerations in AI development"
]

TEST_AGENT_CAPABILITIES = {
    "retriever": ["search", "gather", "collect"],
    "planning": ["analyze", "synthesize", "conclude"],
    "executor": ["execute", "implement", "perform"],
    "memory": ["store", "retrieve", "remember"]
}


class TestDataFactory:
    """Factory class for generating test data."""
    
    @staticmethod
    def create_research_action(
        agent_type: str = "retriever",
        action: str = "search",
        priority: str = "normal",
        **kwargs
    ) -> ResearchAction:
        """Create a research action with sensible defaults."""
        return ResearchAction(
            task_id=kwargs.get("task_id", str(uuid.uuid4())),
            context_id=kwargs.get("context_id", str(uuid.uuid4())),
            agent_type=agent_type,
            action=action,
            payload=kwargs.get("payload", {"query": "test query"}),
            priority=priority,
            timeout=kwargs.get("timeout", 60),
            retry_count=kwargs.get("retry_count", 0)
        )
    
    @staticmethod
    def create_session_context(**kwargs):
        """Create a session context with sensible defaults."""
        from src.core.context_manager import SessionContext
        from datetime import datetime
        
        return SessionContext(
            context_id=kwargs.get("context_id", str(uuid.uuid4())),
            conversation_id=kwargs.get("conversation_id", str(uuid.uuid4())),
            created_at=kwargs.get("created_at", datetime.now()),
            updated_at=kwargs.get("updated_at", datetime.now()),
            status=kwargs.get("status", "active"),
            current_stage=kwargs.get("current_stage"),
            messages=kwargs.get("messages", []),
            research_tasks=kwargs.get("research_tasks", []),
            context_traces=kwargs.get("context_traces", []),
            active_agents=kwargs.get("active_agents", []),
            memory_references=kwargs.get("memory_references", []),
            metadata=kwargs.get("metadata", {}),
            settings=kwargs.get("settings", {})
        )


# Performance testing constants
PERFORMANCE_TEST_ITERATIONS = 100
LOAD_TEST_CONCURRENT_REQUESTS = 10
STRESS_TEST_DURATION_SECONDS = 30
