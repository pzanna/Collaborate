"""Test configuration for api_gateway service tests."""

import asyncio
import pytest
from unittest.mock import MagicMock

from config import Config


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_config():
    """Create test configuration."""
    return Config()


@pytest.fixture
def mock_database():
    """Mock database connection."""
    return MagicMock()


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client."""
    return MagicMock()
