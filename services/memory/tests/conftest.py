"""
Test configuration for memory service tests.

This module provides test configuration and fixtures used across all tests.
"""

import asyncio
import os
import pytest
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

# Import the service modules
from src.config import Config, get_config
from src.health_check import HealthCheck
from src.main import create_app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_config() -> Config:
    """Create test configuration."""
    # Create a temporary directory for test files
    temp_dir = tempfile.mkdtemp()
    
    # Override environment variables for testing
    test_env = {
        "SERVICE_NAME": "test-service",
        "SERVICE_VERSION": "test-1.0.0",
        "SERVICE_ENVIRONMENT": "test",
        "SERVICE_HOST": "localhost",
        "SERVICE_PORT": "8080",
        "SERVICE_DEBUG": "true",
        "LOG_LEVEL": "DEBUG",
        "LOG_FILE": f"{temp_dir}/test.log",
        "DATABASE_URL": "sqlite:///:memory:",
        "MCP_SERVER_URL": "ws://localhost:8081",
        "CONFIG_FILE": f"{temp_dir}/test_config.json"
    }
    
    # Set environment variables
    for key, value in test_env.items():
        os.environ[key] = value
    
    # Create test config file
    test_config_data = {
        "service": {
            "name": "test-service",
            "version": "test-1.0.0",
            "description": "Test service",
            "environment": "test"
        },
        "server": {
            "host": "localhost",
            "port": 8080,
            "debug": True
        },
        "database": {
            "url": "sqlite:///:memory:",
            "echo": True
        },
        "mcp": {
            "server_url": "ws://localhost:8081",
            "timeout": 30
        },
        "logging": {
            "level": "DEBUG",
            "file": f"{temp_dir}/test.log"
        }
    }
    
    import json
    config_file = Path(temp_dir) / "test_config.json"
    with open(config_file, 'w') as f:
        json.dump(test_config_data, f)
    
    return get_config()


@pytest.fixture
def mock_database():
    """Mock database connection."""
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()
    mock_db.fetch = AsyncMock()
    mock_db.fetchrow = AsyncMock()
    mock_db.fetchval = AsyncMock()
    return mock_db


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client."""
    mock_client = AsyncMock()
    mock_client.connect = AsyncMock()
    mock_client.disconnect = AsyncMock()
    mock_client.send_request = AsyncMock()
    mock_client.list_tools = AsyncMock(return_value=[])
    mock_client.call_tool = AsyncMock()
    return mock_client


@pytest.fixture
async def health_check(test_config: Config) -> HealthCheck:
    """Create health check instance for testing."""
    return HealthCheck(test_config)


@pytest.fixture
async def test_app(test_config: Config):
    """Create test FastAPI application."""
    app = create_app(test_config)
    return app


@pytest.fixture
async def test_client(test_app):
    """Create test client for FastAPI application."""
    from httpx import AsyncClient
    
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_task_request():
    """Create sample task request for testing."""
    return {
        "task_id": "test-task-123",
        "task_type": "test_task",
        "parameters": {
            "input": "test input",
            "options": {
                "timeout": 30,
                "retries": 3
            }
        },
        "priority": "normal",
        "metadata": {
            "user_id": "test-user",
            "created_at": "2025-01-11T12:00:00Z"
        }
    }


@pytest.fixture
def sample_task_response():
    """Create sample task response for testing."""
    return {
        "task_id": "test-task-123",
        "status": "completed",
        "result": {
            "output": "test output",
            "processed_at": "2025-01-11T12:00:30Z"
        },
        "execution_time": 30.5,
        "metadata": {
            "worker_id": "worker-1",
            "version": "1.0.0"
        }
    }


@pytest.fixture
def mock_external_api():
    """Mock external API responses."""
    mock_api = MagicMock()
    mock_api.get = AsyncMock()
    mock_api.post = AsyncMock()
    mock_api.put = AsyncMock()
    mock_api.delete = AsyncMock()
    return mock_api


class TestDatabase:
    """Test database helper class."""
    
    def __init__(self, db_url: str = "sqlite:///:memory:"):
        self.db_url = db_url
        self.connection = None
    
    async def setup(self):
        """Set up test database."""
        # Implement database setup for testing
        pass
    
    async def teardown(self):
        """Clean up test database."""
        # Implement database cleanup
        pass
    
    async def reset(self):
        """Reset database to clean state."""
        # Implement database reset
        pass


@pytest.fixture
async def test_database():
    """Create test database instance."""
    db = TestDatabase()
    await db.setup()
    yield db
    await db.teardown()


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "external: mark test as requiring external services"
    )


@pytest.fixture(autouse=True)
def cleanup_environment():
    """Clean up environment variables after each test."""
    original_env = os.environ.copy()
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def temp_directory():
    """Create temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


# Mock data fixtures
@pytest.fixture
def mock_service_info():
    """Mock service information."""
    return {
        "name": "test-service",
        "version": "1.0.0",
        "description": "Test service for unit testing",
        "environment": "test",
        "uptime": 123.45,
        "status": "healthy"
    }


@pytest.fixture
def mock_health_status():
    """Mock health status."""
    return {
        "status": "healthy",
        "timestamp": "2025-01-11T12:00:00Z",
        "service": "test-service",
        "version": "1.0.0",
        "checks": {
            "uptime": {"status": "healthy", "uptime_seconds": 123.45},
            "memory": {"status": "healthy", "usage_percent": 45.2},
            "cpu": {"status": "healthy", "usage_percent": 12.8}
        },
        "metrics": {
            "uptime": 123.45,
            "request_count": 42,
            "requests_per_second": 0.34
        }
    }


# Async test helpers
class AsyncContextManager:
    """Helper for testing async context managers."""
    
    def __init__(self, return_value=None):
        self.return_value = return_value
    
    async def __aenter__(self):
        return self.return_value
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


def async_mock_context(return_value=None):
    """Create async context manager mock."""
    return AsyncContextManager(return_value)
