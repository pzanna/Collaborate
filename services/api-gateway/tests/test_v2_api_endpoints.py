"""
Unit tests for API Gateway v2 hierarchical endpoints.

Tests for the CRUD operations on projects, topics, and plans.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

# We'll need to test the actual endpoints, so let's create a FastAPI test client
import json
from httpx import AsyncClient
from fastapi import FastAPI

# Import the router and dependencies
from v2_hierarchical_api import v2_router, set_mcp_client
from src.data_models.hierarchical_data_models import (
    ProjectRequest, ResearchTopicRequest, ResearchPlanRequest,
    ProjectResponse, ResearchTopicResponse, ResearchPlanResponse
)


# Create a test FastAPI app for endpoint testing
@pytest.fixture
def test_app():
    """Create a test FastAPI app with our v2 router."""
    app = FastAPI()
    app.include_router(v2_router)
    return app


@pytest.fixture
def mock_database():
    """Mock database client."""
    mock_db = AsyncMock()
    
    # Mock project operations
    mock_db.get_projects = AsyncMock(return_value=[
        {
            "id": "test-project-123",
            "name": "Test Project",
            "description": "A test project",
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "topics_count": 2,
            "plans_count": 3,
            "tasks_count": 5,
            "total_cost": 150.0,
            "completion_rate": 60.0,
            "metadata": {}
        }
    ])
    
    mock_db.get_project_by_id = AsyncMock(return_value={
        "id": "test-project-123",
        "name": "Test Project",
        "description": "A test project",
        "status": "active",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "metadata": {}
    })
    
    mock_db.get_project_stats = AsyncMock(return_value={
        "topics_count": 2,
        "plans_count": 3,
        "tasks_count": 5,
        "total_cost": 150.0,
        "completion_rate": 60.0
    })
    
    # Mock topic operations
    mock_db.get_research_topics = AsyncMock(return_value=[
        {
            "id": "test-topic-456",
            "project_id": "test-project-123",
            "name": "Test Topic",
            "description": "A test research topic",
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
    ])
    
    # Mock plan operations
    mock_db.get_research_plans = AsyncMock(return_value=[
        {
            "id": "test-plan-789",
            "topic_id": "test-topic-456",
            "name": "Test Plan",
            "description": "A test research plan",
            "status": "draft",
            "cost_estimate": 100.0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
    ])
    
    return mock_db


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client."""
    mock_client = AsyncMock()
    mock_client.is_connected = True
    mock_client.send_research_action = AsyncMock(return_value=True)
    return mock_client


@pytest.fixture
async def test_client(test_app, mock_database, mock_mcp_client):
    """Create test client with mocked dependencies."""
    # Set the MCP client for the router
    set_mcp_client(mock_mcp_client)
    
    # Mock the database dependency
    def get_test_database():
        return mock_database
    
    def get_test_mcp_client():
        return mock_mcp_client
    
    # Override dependencies in the app
    from v2_hierarchical_api import get_database, get_mcp_client
    test_app.dependency_overrides[get_database] = get_test_database
    test_app.dependency_overrides[get_mcp_client] = get_test_mcp_client
    
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        return client


class TestProjectEndpoints:
    """Test cases for project CRUD endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_project(self, test_client, mock_mcp_client):
        """Test project creation endpoint."""
        project_data = {
            "name": "New Test Project",
            "description": "A new test project for testing",
            "metadata": {"test": True}
        }
        
        response = await test_client.post("/v2/projects", json=project_data)
        
        assert response.status_code == 200
        result = response.json()
        
        assert result["name"] == project_data["name"]
        assert result["description"] == project_data["description"]
        assert result["status"] == "pending"
        assert result["metadata"] == project_data["metadata"]
        assert "id" in result
        assert "created_at" in result
        
        # Verify MCP client was called
        mock_mcp_client.send_research_action.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_list_projects(self, test_client, mock_database):
        """Test project listing endpoint."""
        response = await test_client.get("/v2/projects")
        
        assert response.status_code == 200
        result = response.json()
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["name"] == "Test Project"
        
        # Verify database was called
        mock_database.get_projects.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_get_project_by_id(self, test_client, mock_database):
        """Test get project by ID endpoint."""
        project_id = "test-project-123"
        
        response = await test_client.get(f"/v2/projects/{project_id}")
        
        assert response.status_code == 200
        result = response.json()
        
        assert result["id"] == project_id
        assert result["name"] == "Test Project"
        
        # Verify database was called
        mock_database.get_project_by_id.assert_called_once_with(project_id)
        
    @pytest.mark.asyncio
    async def test_update_project(self, test_client, mock_mcp_client):
        """Test project update endpoint."""
        project_id = "test-project-123"
        update_data = {
            "name": "Updated Project Name",
            "description": "Updated description"
        }
        
        response = await test_client.put(f"/v2/projects/{project_id}", json=update_data)
        
        assert response.status_code == 200
        result = response.json()
        
        assert result["name"] == update_data["name"]
        assert result["description"] == update_data["description"]
        
        # Verify MCP client was called
        mock_mcp_client.send_research_action.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_delete_project(self, test_client, mock_mcp_client):
        """Test project deletion endpoint."""
        project_id = "test-project-123"
        
        response = await test_client.delete(f"/v2/projects/{project_id}")
        
        assert response.status_code == 200
        result = response.json()
        
        assert result["success"] is True
        assert "Project deleted successfully" in result["message"]
        
        # Verify MCP client was called
        mock_mcp_client.send_research_action.assert_called_once()


class TestResearchTopicEndpoints:
    """Test cases for research topic CRUD endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_research_topic(self, test_client, mock_mcp_client):
        """Test research topic creation endpoint."""
        project_id = "test-project-123"
        topic_data = {
            "name": "New Research Topic",
            "description": "A new research topic for testing",
            "research_depth": "comprehensive"
        }
        
        response = await test_client.post(f"/v2/projects/{project_id}/topics", json=topic_data)
        
        assert response.status_code == 200
        result = response.json()
        
        assert result["name"] == topic_data["name"]
        assert result["description"] == topic_data["description"]
        assert result["project_id"] == project_id
        assert result["status"] == "pending"
        assert "id" in result
        
        # Verify MCP client was called
        mock_mcp_client.send_research_action.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_list_research_topics(self, test_client, mock_database):
        """Test research topic listing endpoint."""
        project_id = "test-project-123"
        
        response = await test_client.get(f"/v2/projects/{project_id}/topics")
        
        assert response.status_code == 200
        result = response.json()
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["name"] == "Test Topic"
        
        # Verify database was called
        mock_database.get_research_topics.assert_called_once_with(project_id=project_id)
        
    @pytest.mark.asyncio
    async def test_update_research_topic(self, test_client, mock_mcp_client):
        """Test research topic update endpoint."""
        topic_id = "test-topic-456"
        update_data = {
            "name": "Updated Topic Name",
            "description": "Updated description"
        }
        
        response = await test_client.put(f"/v2/topics/{topic_id}", json=update_data)
        
        assert response.status_code == 200
        result = response.json()
        
        assert result["name"] == update_data["name"]
        assert result["description"] == update_data["description"]
        
        # Verify MCP client was called
        mock_mcp_client.send_research_action.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_delete_research_topic(self, test_client, mock_mcp_client):
        """Test research topic deletion endpoint."""
        topic_id = "test-topic-456"
        
        response = await test_client.delete(f"/v2/topics/{topic_id}")
        
        assert response.status_code == 200
        result = response.json()
        
        assert result["success"] is True
        assert "Research topic deleted successfully" in result["message"]
        
        # Verify MCP client was called
        mock_mcp_client.send_research_action.assert_called_once()


class TestResearchPlanEndpoints:
    """Test cases for research plan CRUD endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_research_plan(self, test_client, mock_mcp_client):
        """Test research plan creation endpoint."""
        topic_id = "test-topic-456"
        plan_data = {
            "name": "New Research Plan",
            "description": "A new research plan for testing",
            "research_steps": ["Step 1", "Step 2", "Step 3"],
            "cost_estimate": 200.0
        }
        
        response = await test_client.post(f"/v2/topics/{topic_id}/plans", json=plan_data)
        
        assert response.status_code == 200
        result = response.json()
        
        assert result["name"] == plan_data["name"]
        assert result["description"] == plan_data["description"]
        assert result["topic_id"] == topic_id
        assert result["status"] == "draft"
        assert "id" in result
        
        # Verify MCP client was called
        mock_mcp_client.send_research_action.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_update_research_plan(self, test_client, mock_mcp_client):
        """Test research plan update endpoint."""
        plan_id = "test-plan-789"
        update_data = {
            "name": "Updated Plan Name",
            "description": "Updated description",
            "cost_estimate": 250.0
        }
        
        response = await test_client.put(f"/v2/plans/{plan_id}", json=update_data)
        
        assert response.status_code == 200
        result = response.json()
        
        assert result["name"] == update_data["name"]
        assert result["description"] == update_data["description"]
        
        # Verify MCP client was called
        mock_mcp_client.send_research_action.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_delete_research_plan(self, test_client, mock_mcp_client):
        """Test research plan deletion endpoint."""
        plan_id = "test-plan-789"
        
        response = await test_client.delete(f"/v2/plans/{plan_id}")
        
        assert response.status_code == 200
        result = response.json()
        
        assert result["success"] is True
        assert "Research plan deleted successfully" in result["message"]
        
        # Verify MCP client was called
        mock_mcp_client.send_research_action.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_approve_research_plan(self, test_client, mock_mcp_client):
        """Test research plan approval endpoint."""
        plan_id = "test-plan-789"
        
        response = await test_client.post(f"/v2/plans/{plan_id}/approve")
        
        assert response.status_code == 200
        result = response.json()
        
        assert result["status"] == "approved"
        
        # Verify MCP client was called
        mock_mcp_client.send_research_action.assert_called_once()


class TestAPIErrorHandling:
    """Test cases for API error handling."""
    
    @pytest.mark.asyncio
    async def test_mcp_client_unavailable(self, test_client):
        """Test behavior when MCP client is unavailable."""
        # Override MCP client to return None
        def get_unavailable_mcp_client():
            return None
        
        from v2_hierarchical_api import get_mcp_client
        test_client.app.dependency_overrides[get_mcp_client] = get_unavailable_mcp_client
        
        project_data = {
            "name": "Test Project",
            "description": "Test description"
        }
        
        response = await test_client.post("/v2/projects", json=project_data)
        
        # Should still work but might return different status
        assert response.status_code in [200, 503]  # Either success or service unavailable
        
    @pytest.mark.asyncio
    async def test_invalid_project_data(self, test_client):
        """Test behavior with invalid project data."""
        invalid_data = {
            "name": "",  # Empty name should be invalid
            "description": "Test description"
        }
        
        response = await test_client.post("/v2/projects", json=invalid_data)
        
        # Should return validation error
        assert response.status_code in [400, 422]  # Bad request or validation error
        
    @pytest.mark.asyncio
    async def test_nonexistent_resource(self, test_client, mock_database):
        """Test behavior when requesting nonexistent resources."""
        # Mock database to return None for nonexistent project
        mock_database.get_project_by_id.return_value = None
        
        response = await test_client.get("/v2/projects/nonexistent-id")
        
        assert response.status_code == 404  # Not found
