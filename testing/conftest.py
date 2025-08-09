"""
pytest configuration and fixtures for API Gateway tests.

This module provides common fixtures and configuration for testing
the API Gateway service endpoints.
"""

import asyncio
import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator

# Test environment configuration
TEST_ENV = {
    "API_GATEWAY_URL": os.getenv("API_GATEWAY_URL", "http://localhost:8001"),
    "DATABASE_URL": os.getenv("TEST_DATABASE_URL", "postgresql://eunice:eunice@localhost:5432/eunice_test"),
    "SERVICE_HOST": "localhost",
    "SERVICE_PORT": "8001",
    "LOG_LEVEL": "DEBUG",
}


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def api_gateway_url() -> str:
    """Get the API Gateway URL for testing."""
    return TEST_ENV["API_GATEWAY_URL"]


@pytest.fixture(scope="function")
async def test_cleanup():
    """Fixture to ensure test cleanup after each test."""
    # Setup
    test_resources = []
    
    yield test_resources
    
    # Cleanup - this would ideally clean up any test data
    # For now, we'll just log the cleanup
    if test_resources:
        print(f"Cleaning up {len(test_resources)} test resources")


# Mark all tests as asyncio by default
def pytest_collection_modifyitems(config, items):
    """Add asyncio marker to all test items."""
    for item in items:
        if "asyncio" not in [marker.name for marker in item.iter_markers()]:
            item.add_marker(pytest.mark.asyncio)


# Configure pytest-asyncio
pytest_plugins = ["pytest_asyncio"]


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    for key, value in TEST_ENV.items():
        os.environ[key] = value
    
    yield
    
    # Cleanup environment if needed
    pass


@pytest.fixture
def timeout():
    """Test timeout configuration."""
    return 30.0


@pytest.fixture
def max_retries():
    """Maximum number of retries for flaky tests."""
    return 3


# Test data constants
TEST_DATA_CONSTANTS = {
    "PROJECT_STATUSES": ["pending", "active", "complete", "archived"],
    "TOPIC_STATUSES": ["active", "paused", "completed", "archived"],
    "PLAN_STATUSES": ["draft", "active", "completed", "cancelled"],
    "PLAN_TYPES": ["comprehensive", "quick", "deep", "custom"],
    "TASK_TYPES": ["research", "analysis", "synthesis", "validation", "literature_review", "systematic_review", "meta_analysis"],
    "RESEARCH_DEPTHS": ["undergraduate", "masters", "phd"],
}


@pytest.fixture
def test_constants():
    """Provide test constants."""
    return TEST_DATA_CONSTANTS
