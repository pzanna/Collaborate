"""
Comprehensive test suite for API Gateway endpoints.

This module tests all REST API endpoints provided by the API Gateway service,
including project management, research topics, research plans, and execution endpoints.
"""

import asyncio
import json
import pytest
import httpx
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import uuid4

# Base URL for API Gateway (adjust based on environment)
BASE_URL = "http://localhost:8001"

# Test configuration
TEST_CONFIG = {
    "timeout": 30.0,
    "verify_ssl": False,
}


class APITestClient:
    """HTTP client wrapper for API testing."""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            timeout=TEST_CONFIG["timeout"],
            verify=TEST_CONFIG["verify_ssl"]
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def get(self, path: str, **kwargs) -> httpx.Response:
        """Make GET request."""
        return await self.client.get(f"{self.base_url}{path}", **kwargs)
    
    async def post(self, path: str, **kwargs) -> httpx.Response:
        """Make POST request."""
        return await self.client.post(f"{self.base_url}{path}", **kwargs)
    
    async def put(self, path: str, **kwargs) -> httpx.Response:
        """Make PUT request."""
        return await self.client.put(f"{self.base_url}{path}", **kwargs)
    
    async def delete(self, path: str, **kwargs) -> httpx.Response:
        """Make DELETE request."""
        return await self.client.delete(f"{self.base_url}{path}", **kwargs)


# Test fixtures for creating test data
class TestDataFactory:
    """Factory for creating test data."""
    
    @staticmethod
    def create_project_data(name: Optional[str] = None) -> Dict[str, Any]:
        """Create test project data."""
        return {
            "name": name or f"Test Project {uuid4().hex[:8]}",
            "description": "A test project for API testing",
            "metadata": {
                "test": True,
                "created_by": "api_test_suite",
                "purpose": "automated_testing"
            }
        }
    
    @staticmethod
    def create_topic_data(name: Optional[str] = None) -> Dict[str, Any]:
        """Create test research topic data."""
        return {
            "name": name or f"Test Topic {uuid4().hex[:8]}",
            "description": "A test research topic for API testing",
            "metadata": {
                "test": True,
                "domain": "artificial_intelligence",
                "complexity": "medium"
            }
        }
    
    @staticmethod
    def create_plan_data(name: Optional[str] = None, plan_type: str = "comprehensive") -> Dict[str, Any]:
        """Create test research plan data."""
        return {
            "name": name or f"Test Plan {uuid4().hex[:8]}",
            "description": "A test research plan for API testing",
            "plan_type": plan_type,
            "plan_structure": {
                "title": "Test Research Plan",
                "sections": [
                    {"title": "Introduction", "description": "Research background"},
                    {"title": "Literature Review", "description": "Existing work analysis"},
                    {"title": "Methodology", "description": "Research approach"},
                    {"title": "Results", "description": "Expected outcomes"}
                ],
                "questions": [
                    "What are the current trends in AI research?",
                    "How can machine learning improve efficiency?",
                    "What are the ethical implications?"
                ]
            },
            "metadata": {
                "test": True,
                "complexity": "medium",
                "estimated_weeks": 4
            }
        }
    
    @staticmethod
    def create_execution_data(task_type: str = "literature_review", depth: str = "undergraduate") -> Dict[str, Any]:
        """Create test research execution data."""
        return {
            "task_type": task_type,
            "depth": depth
        }


# =============================================================================
# HEALTH CHECK TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_health_check():
    """Test the health check endpoint."""
    async with APITestClient() as client:
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "api-gateway"
        assert "timestamp" in data
        assert "version" in data


# =============================================================================
# PROJECT CRUD TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_create_project():
    """Test creating a new project."""
    async with APITestClient() as client:
        project_data = TestDataFactory.create_project_data()
        
        response = await client.post("/v2/projects", json=project_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert data["name"] == project_data["name"]
        assert data["description"] == project_data["description"]
        assert data["status"] == "pending"
        assert data["topics_count"] == 0
        assert data["plans_count"] == 0
        assert data["tasks_count"] == 0
        assert data["total_cost"] == 0.0
        assert data["completion_rate"] == 0.0
        assert "created_at" in data
        assert "updated_at" in data


@pytest.mark.asyncio
async def test_list_projects():
    """Test listing all projects."""
    async with APITestClient() as client:
        # First create a test project
        project_data = TestDataFactory.create_project_data()
        create_response = await client.post("/v2/projects", json=project_data)
        assert create_response.status_code == 200
        
        # Then list projects
        response = await client.get("/v2/projects")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Check that our created project is in the list
        project_names = [p["name"] for p in data]
        assert project_data["name"] in project_names


@pytest.mark.asyncio
async def test_list_projects_with_status_filter():
    """Test listing projects with status filter."""
    async with APITestClient() as client:
        response = await client.get("/v2/projects?status=pending")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # All returned projects should have 'pending' status
        for project in data:
            assert project["status"] == "pending"


@pytest.mark.asyncio
async def test_list_projects_with_limit():
    """Test listing projects with limit."""
    async with APITestClient() as client:
        response = await client.get("/v2/projects?limit=5")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5


@pytest.mark.asyncio
async def test_get_project():
    """Test getting a specific project."""
    async with APITestClient() as client:
        # First create a test project
        project_data = TestDataFactory.create_project_data()
        create_response = await client.post("/v2/projects", json=project_data)
        assert create_response.status_code == 200
        created_project = create_response.json()
        project_id = created_project["id"]
        
        # Then get the project
        response = await client.get(f"/v2/projects/{project_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == project_id
        assert data["name"] == project_data["name"]
        assert data["description"] == project_data["description"]


@pytest.mark.asyncio
async def test_get_nonexistent_project():
    """Test getting a project that doesn't exist."""
    async with APITestClient() as client:
        fake_id = str(uuid4())
        response = await client.get(f"/v2/projects/{fake_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_update_project():
    """Test updating a project."""
    async with APITestClient() as client:
        # First create a test project
        project_data = TestDataFactory.create_project_data()
        create_response = await client.post("/v2/projects", json=project_data)
        assert create_response.status_code == 200
        created_project = create_response.json()
        project_id = created_project["id"]
        
        # Update the project
        update_data = {
            "name": "Updated Project Name",
            "description": "Updated description",
            "status": "active"
        }
        
        response = await client.put(f"/v2/projects/{project_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == project_id
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
        assert data["status"] == update_data["status"]


@pytest.mark.asyncio
async def test_update_nonexistent_project():
    """Test updating a project that doesn't exist."""
    async with APITestClient() as client:
        fake_id = str(uuid4())
        update_data = {"name": "Updated Name"}
        
        response = await client.put(f"/v2/projects/{fake_id}", json=update_data)
        
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_project():
    """Test deleting a project."""
    async with APITestClient() as client:
        # First create a test project
        project_data = TestDataFactory.create_project_data()
        create_response = await client.post("/v2/projects", json=project_data)
        assert create_response.status_code == 200
        created_project = create_response.json()
        project_id = created_project["id"]
        
        # Delete the project
        response = await client.delete(f"/v2/projects/{project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "deleted successfully" in data["message"]
        
        # Verify project is deleted
        get_response = await client.get(f"/v2/projects/{project_id}")
        assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_project():
    """Test deleting a project that doesn't exist."""
    async with APITestClient() as client:
        fake_id = str(uuid4())
        response = await client.delete(f"/v2/projects/{fake_id}")
        
        assert response.status_code == 404


# =============================================================================
# RESEARCH TOPIC CRUD TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_create_research_topic():
    """Test creating a new research topic."""
    async with APITestClient() as client:
        # First create a test project
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        # Create research topic
        topic_data = TestDataFactory.create_topic_data()
        
        response = await client.post(f"/v2/projects/{project_id}/topics", json=topic_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert data["project_id"] == project_id
        assert data["name"] == topic_data["name"]
        assert data["description"] == topic_data["description"]
        assert data["status"] == "active"
        assert data["plans_count"] == 0
        assert data["tasks_count"] == 0


@pytest.mark.asyncio
async def test_create_topic_for_nonexistent_project():
    """Test creating a topic for a project that doesn't exist."""
    async with APITestClient() as client:
        fake_project_id = str(uuid4())
        topic_data = TestDataFactory.create_topic_data()
        
        response = await client.post(f"/v2/projects/{fake_project_id}/topics", json=topic_data)
        
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_research_topics():
    """Test listing research topics for a project."""
    async with APITestClient() as client:
        # First create a test project
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        # Create a research topic
        topic_data = TestDataFactory.create_topic_data()
        topic_response = await client.post(f"/v2/projects/{project_id}/topics", json=topic_data)
        assert topic_response.status_code == 200
        
        # List topics
        response = await client.get(f"/v2/projects/{project_id}/topics")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Check that our created topic is in the list
        topic_names = [t["name"] for t in data]
        assert topic_data["name"] in topic_names


@pytest.mark.asyncio
async def test_list_topics_with_status_filter():
    """Test listing topics with status filter."""
    async with APITestClient() as client:
        # First create a test project
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        response = await client.get(f"/v2/projects/{project_id}/topics?status=active")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # All returned topics should have 'active' status
        for topic in data:
            assert topic["status"] == "active"


@pytest.mark.asyncio
async def test_get_research_topic():
    """Test getting a specific research topic."""
    async with APITestClient() as client:
        # First create a test project and topic
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        topic_data = TestDataFactory.create_topic_data()
        topic_response = await client.post(f"/v2/projects/{project_id}/topics", json=topic_data)
        assert topic_response.status_code == 200
        topic_id = topic_response.json()["id"]
        
        # Get the topic
        response = await client.get(f"/topics/{topic_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == topic_id
        assert data["project_id"] == project_id
        assert data["name"] == topic_data["name"]


@pytest.mark.asyncio
async def test_get_research_topic_by_project():
    """Test getting a research topic within a specific project."""
    async with APITestClient() as client:
        # First create a test project and topic
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        topic_data = TestDataFactory.create_topic_data()
        topic_response = await client.post(f"/v2/projects/{project_id}/topics", json=topic_data)
        assert topic_response.status_code == 200
        topic_id = topic_response.json()["id"]
        
        # Get the topic by project
        response = await client.get(f"/v2/projects/{project_id}/topics/{topic_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == topic_id
        assert data["project_id"] == project_id


@pytest.mark.asyncio
async def test_update_research_topic():
    """Test updating a research topic."""
    async with APITestClient() as client:
        # First create a test project and topic
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        topic_data = TestDataFactory.create_topic_data()
        topic_response = await client.post(f"/v2/projects/{project_id}/topics", json=topic_data)
        assert topic_response.status_code == 200
        topic_id = topic_response.json()["id"]
        
        # Update the topic
        update_data = {
            "name": "Updated Topic Name",
            "description": "Updated description"
        }
        
        response = await client.put(f"/topics/{topic_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == topic_id
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]


@pytest.mark.asyncio
async def test_update_research_topic_by_project():
    """Test updating a research topic within a specific project."""
    async with APITestClient() as client:
        # First create a test project and topic
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        topic_data = TestDataFactory.create_topic_data()
        topic_response = await client.post(f"/v2/projects/{project_id}/topics", json=topic_data)
        assert topic_response.status_code == 200
        topic_id = topic_response.json()["id"]
        
        # Update the topic by project
        update_data = {
            "name": "Updated Topic Name",
            "description": "Updated description"
        }
        
        response = await client.put(f"/v2/projects/{project_id}/topics/{topic_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == topic_id
        assert data["name"] == update_data["name"]


@pytest.mark.asyncio
async def test_delete_research_topic():
    """Test deleting a research topic."""
    async with APITestClient() as client:
        # First create a test project and topic
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        topic_data = TestDataFactory.create_topic_data()
        topic_response = await client.post(f"/v2/projects/{project_id}/topics", json=topic_data)
        assert topic_response.status_code == 200
        topic_id = topic_response.json()["id"]
        
        # Delete the topic
        response = await client.delete(f"/topics/{topic_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify topic is deleted
        get_response = await client.get(f"/topics/{topic_id}")
        assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_research_topic_by_project():
    """Test deleting a research topic within a specific project."""
    async with APITestClient() as client:
        # First create a test project and topic
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        topic_data = TestDataFactory.create_topic_data()
        topic_response = await client.post(f"/v2/projects/{project_id}/topics", json=topic_data)
        assert topic_response.status_code == 200
        topic_id = topic_response.json()["id"]
        
        # Delete the topic by project
        response = await client.delete(f"/v2/projects/{project_id}/topics/{topic_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


# =============================================================================
# RESEARCH PLAN CRUD TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_create_research_plan():
    """Test creating a new research plan."""
    async with APITestClient() as client:
        # First create a test project and topic
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        topic_data = TestDataFactory.create_topic_data()
        topic_response = await client.post(f"/v2/projects/{project_id}/topics", json=topic_data)
        assert topic_response.status_code == 200
        topic_id = topic_response.json()["id"]
        
        # Create research plan
        plan_data = TestDataFactory.create_plan_data()
        
        response = await client.post(f"/topics/{topic_id}/plans", json=plan_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert data["topic_id"] == topic_id
        assert data["name"] == plan_data["name"]
        assert data["description"] == plan_data["description"]
        assert data["plan_type"] == plan_data["plan_type"]
        assert data["status"] == "draft"
        assert data["plan_approved"] is False
        assert data["tasks_count"] == 0


@pytest.mark.asyncio
async def test_create_ai_research_plan():
    """Test creating an AI-generated research plan."""
    async with APITestClient() as client:
        # First create a test project and topic
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        topic_data = TestDataFactory.create_topic_data()
        topic_response = await client.post(f"/v2/projects/{project_id}/topics", json=topic_data)
        assert topic_response.status_code == 200
        topic_id = topic_response.json()["id"]
        
        # Create AI research plan
        plan_data = TestDataFactory.create_plan_data(name="AI Generated Plan")
        
        response = await client.post(f"/topics/{topic_id}/ai-plans", json=plan_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert data["topic_id"] == topic_id
        assert data["name"] == plan_data["name"]
        assert data["status"] == "draft"
        assert data["metadata"]["ai_generated"] is True
        assert "ai_model_used" in data["metadata"]
        assert "generation_cost" in data["metadata"]


@pytest.mark.asyncio
async def test_list_research_plans():
    """Test listing research plans for a topic."""
    async with APITestClient() as client:
        # First create a test project, topic, and plan
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        topic_data = TestDataFactory.create_topic_data()
        topic_response = await client.post(f"/v2/projects/{project_id}/topics", json=topic_data)
        assert topic_response.status_code == 200
        topic_id = topic_response.json()["id"]
        
        plan_data = TestDataFactory.create_plan_data()
        plan_response = await client.post(f"/topics/{topic_id}/plans", json=plan_data)
        assert plan_response.status_code == 200
        
        # List plans
        response = await client.get(f"/topics/{topic_id}/plans")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Check that our created plan is in the list
        plan_names = [p["name"] for p in data]
        assert plan_data["name"] in plan_names


@pytest.mark.asyncio
async def test_get_research_plan():
    """Test getting a specific research plan."""
    async with APITestClient() as client:
        # First create a test project, topic, and plan
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        topic_data = TestDataFactory.create_topic_data()
        topic_response = await client.post(f"/v2/projects/{project_id}/topics", json=topic_data)
        assert topic_response.status_code == 200
        topic_id = topic_response.json()["id"]
        
        plan_data = TestDataFactory.create_plan_data()
        plan_response = await client.post(f"/topics/{topic_id}/plans", json=plan_data)
        assert plan_response.status_code == 200
        plan_id = plan_response.json()["id"]
        
        # Get the plan
        response = await client.get(f"/plans/{plan_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == plan_id
        assert data["topic_id"] == topic_id
        assert data["name"] == plan_data["name"]


@pytest.mark.asyncio
async def test_update_research_plan():
    """Test updating a research plan."""
    async with APITestClient() as client:
        # First create a test project, topic, and plan
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        topic_data = TestDataFactory.create_topic_data()
        topic_response = await client.post(f"/v2/projects/{project_id}/topics", json=topic_data)
        assert topic_response.status_code == 200
        topic_id = topic_response.json()["id"]
        
        plan_data = TestDataFactory.create_plan_data()
        plan_response = await client.post(f"/topics/{topic_id}/plans", json=plan_data)
        assert plan_response.status_code == 200
        plan_id = plan_response.json()["id"]
        
        # Update the plan
        update_data = {
            "name": "Updated Plan Name",
            "description": "Updated description",
            "status": "active"
        }
        
        response = await client.put(f"/plans/{plan_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == plan_id
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
        assert data["status"] == update_data["status"]


@pytest.mark.asyncio
async def test_approve_research_plan():
    """Test approving a research plan."""
    async with APITestClient() as client:
        # First create a test project, topic, and plan
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        topic_data = TestDataFactory.create_topic_data()
        topic_response = await client.post(f"/v2/projects/{project_id}/topics", json=topic_data)
        assert topic_response.status_code == 200
        topic_id = topic_response.json()["id"]
        
        plan_data = TestDataFactory.create_plan_data()
        plan_response = await client.post(f"/topics/{topic_id}/plans", json=plan_data)
        assert plan_response.status_code == 200
        plan_id = plan_response.json()["id"]
        
        # Approve the plan
        response = await client.post(f"/plans/{plan_id}/approve")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == plan_id
        assert data["plan_approved"] is True
        assert data["status"] == "active"


@pytest.mark.asyncio
async def test_delete_research_plan():
    """Test deleting a research plan."""
    async with APITestClient() as client:
        # First create a test project, topic, and plan
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        topic_data = TestDataFactory.create_topic_data()
        topic_response = await client.post(f"/v2/projects/{project_id}/topics", json=topic_data)
        assert topic_response.status_code == 200
        topic_id = topic_response.json()["id"]
        
        plan_data = TestDataFactory.create_plan_data()
        plan_response = await client.post(f"/topics/{topic_id}/plans", json=plan_data)
        assert plan_response.status_code == 200
        plan_id = plan_response.json()["id"]
        
        # Delete the plan
        response = await client.delete(f"/plans/{plan_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify plan is deleted
        get_response = await client.get(f"/plans/{plan_id}")
        assert get_response.status_code == 404


# =============================================================================
# RESEARCH EXECUTION TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_execute_research_task():
    """Test executing a research task."""
    async with APITestClient() as client:
        # First create a test project, topic, and approved plan
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        topic_data = TestDataFactory.create_topic_data()
        topic_response = await client.post(f"/v2/projects/{project_id}/topics", json=topic_data)
        assert topic_response.status_code == 200
        topic_id = topic_response.json()["id"]
        
        plan_data = TestDataFactory.create_plan_data()
        plan_response = await client.post(f"/topics/{topic_id}/plans", json=plan_data)
        assert plan_response.status_code == 200
        plan_id = plan_response.json()["id"]
        
        # Approve the plan
        approve_response = await client.post(f"/plans/{plan_id}/approve")
        assert approve_response.status_code == 200
        
        # Execute research task
        execution_data = TestDataFactory.create_execution_data()
        
        response = await client.post(f"/v2/topics/{topic_id}/execute", json=execution_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "execution_id" in data
        assert data["topic_name"] == topic_data["name"]
        assert data["task_type"] == execution_data["task_type"]
        assert data["depth"] == execution_data["depth"]
        assert data["status"] == "initiated"
        assert "estimated_cost" in data
        assert "estimated_duration" in data
        assert "progress_url" in data


@pytest.mark.asyncio
async def test_execute_research_without_approved_plan():
    """Test executing research without an approved plan."""
    async with APITestClient() as client:
        # First create a test project and topic (no approved plan)
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        topic_data = TestDataFactory.create_topic_data()
        topic_response = await client.post(f"/v2/projects/{project_id}/topics", json=topic_data)
        assert topic_response.status_code == 200
        topic_id = topic_response.json()["id"]
        
        # Try to execute research task without approved plan
        execution_data = TestDataFactory.create_execution_data()
        
        response = await client.post(f"/v2/topics/{topic_id}/execute", json=execution_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "no approved research plan" in data["detail"].lower()


@pytest.mark.asyncio
async def test_execute_research_different_depths():
    """Test executing research with different depth levels."""
    depths = ["undergraduate", "masters", "phd"]
    
    async with APITestClient() as client:
        for depth in depths:
            # Create project, topic, and approved plan
            project_data = TestDataFactory.create_project_data(name=f"Test Project - {depth}")
            project_response = await client.post("/v2/projects", json=project_data)
            assert project_response.status_code == 200
            project_id = project_response.json()["id"]
            
            topic_data = TestDataFactory.create_topic_data(name=f"Test Topic - {depth}")
            topic_response = await client.post(f"/v2/projects/{project_id}/topics", json=topic_data)
            assert topic_response.status_code == 200
            topic_id = topic_response.json()["id"]
            
            plan_data = TestDataFactory.create_plan_data(name=f"Test Plan - {depth}")
            plan_response = await client.post(f"/topics/{topic_id}/plans", json=plan_data)
            assert plan_response.status_code == 200
            plan_id = plan_response.json()["id"]
            
            # Approve the plan
            approve_response = await client.post(f"/plans/{plan_id}/approve")
            assert approve_response.status_code == 200
            
            # Execute research task with this depth
            execution_data = TestDataFactory.create_execution_data(depth=depth)
            
            response = await client.post(f"/v2/topics/{topic_id}/execute", json=execution_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["depth"] == depth


@pytest.mark.asyncio
async def test_execute_research_different_task_types():
    """Test executing research with different task types."""
    task_types = ["literature_review", "systematic_review", "meta_analysis"]
    
    async with APITestClient() as client:
        for task_type in task_types:
            # Create project, topic, and approved plan
            project_data = TestDataFactory.create_project_data(name=f"Test Project - {task_type}")
            project_response = await client.post("/v2/projects", json=project_data)
            assert project_response.status_code == 200
            project_id = project_response.json()["id"]
            
            topic_data = TestDataFactory.create_topic_data(name=f"Test Topic - {task_type}")
            topic_response = await client.post(f"/v2/projects/{project_id}/topics", json=topic_data)
            assert topic_response.status_code == 200
            topic_id = topic_response.json()["id"]
            
            plan_data = TestDataFactory.create_plan_data(name=f"Test Plan - {task_type}")
            plan_response = await client.post(f"/topics/{topic_id}/plans", json=plan_data)
            assert plan_response.status_code == 200
            plan_id = plan_response.json()["id"]
            
            # Approve the plan
            approve_response = await client.post(f"/plans/{plan_id}/approve")
            assert approve_response.status_code == 200
            
            # Execute research task with this type
            execution_data = TestDataFactory.create_execution_data(task_type=task_type)
            
            response = await client.post(f"/v2/topics/{topic_id}/execute", json=execution_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["task_type"] == task_type


@pytest.mark.asyncio
async def test_get_execution_progress():
    """Test getting execution progress."""
    async with APITestClient() as client:
        # Create project, topic, approved plan, and execute research
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        topic_data = TestDataFactory.create_topic_data()
        topic_response = await client.post(f"/v2/projects/{project_id}/topics", json=topic_data)
        assert topic_response.status_code == 200
        topic_id = topic_response.json()["id"]
        
        plan_data = TestDataFactory.create_plan_data()
        plan_response = await client.post(f"/topics/{topic_id}/plans", json=plan_data)
        assert plan_response.status_code == 200
        plan_id = plan_response.json()["id"]
        
        # Approve the plan
        approve_response = await client.post(f"/plans/{plan_id}/approve")
        assert approve_response.status_code == 200
        
        # Execute research task
        execution_data = TestDataFactory.create_execution_data()
        execution_response = await client.post(f"/v2/topics/{topic_id}/execute", json=execution_data)
        assert execution_response.status_code == 200
        execution_id = execution_response.json()["execution_id"]
        
        # Get execution progress
        response = await client.get(f"/v2/executions/{execution_id}/progress")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["execution_id"] == execution_id
        assert "status" in data
        assert "progress_percentage" in data
        assert "current_stage" in data
        assert "stages" in data
        assert "last_updated" in data


# =============================================================================
# STATISTICS TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_get_project_stats():
    """Test getting project statistics."""
    async with APITestClient() as client:
        # Create project with topics and plans
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        # Get project stats
        response = await client.get(f"/v2/projects/{project_id}/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "topics_count" in data
        assert "plans_count" in data
        assert "tasks_count" in data
        assert "total_cost" in data
        assert "completion_rate" in data


@pytest.mark.asyncio
async def test_get_topic_stats():
    """Test getting topic statistics."""
    async with APITestClient() as client:
        # Create project and topic
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        topic_data = TestDataFactory.create_topic_data()
        topic_response = await client.post(f"/v2/projects/{project_id}/topics", json=topic_data)
        assert topic_response.status_code == 200
        topic_id = topic_response.json()["id"]
        
        # Get topic stats
        response = await client.get(f"/v2/topics/{topic_id}/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "plans_count" in data
        assert "tasks_count" in data
        assert "total_cost" in data
        assert "completion_rate" in data


@pytest.mark.asyncio
async def test_get_plan_stats():
    """Test getting plan statistics."""
    async with APITestClient() as client:
        # Create project, topic, and plan
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        topic_data = TestDataFactory.create_topic_data()
        topic_response = await client.post(f"/v2/projects/{project_id}/topics", json=topic_data)
        assert topic_response.status_code == 200
        topic_id = topic_response.json()["id"]
        
        plan_data = TestDataFactory.create_plan_data()
        plan_response = await client.post(f"/topics/{topic_id}/plans", json=plan_data)
        assert plan_response.status_code == 200
        plan_id = plan_response.json()["id"]
        
        # Get plan stats
        response = await client.get(f"/v2/plans/{plan_id}/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "tasks_count" in data
        assert "completed_tasks" in data
        assert "total_cost" in data
        assert "progress" in data


@pytest.mark.asyncio
async def test_get_project_hierarchy():
    """Test getting complete project hierarchy."""
    async with APITestClient() as client:
        # Create project with topics and plans
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        topic_data = TestDataFactory.create_topic_data()
        topic_response = await client.post(f"/v2/projects/{project_id}/topics", json=topic_data)
        assert topic_response.status_code == 200
        topic_id = topic_response.json()["id"]
        
        plan_data = TestDataFactory.create_plan_data()
        plan_response = await client.post(f"/topics/{topic_id}/plans", json=plan_data)
        assert plan_response.status_code == 200
        
        # Get project hierarchy
        response = await client.get(f"/v2/projects/{project_id}/hierarchy")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "project" in data
        assert "topics" in data
        assert "plans" in data
        assert "tasks" in data
        
        assert data["project"]["id"] == project_id
        assert len(data["topics"]) >= 1
        assert len(data["plans"]) >= 1


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_invalid_project_data():
    """Test creating project with invalid data."""
    async with APITestClient() as client:
        # Test empty name
        invalid_data = {"name": "", "description": "Test"}
        response = await client.post("/v2/projects", json=invalid_data)
        assert response.status_code == 422
        
        # Test missing name
        invalid_data = {"description": "Test"}
        response = await client.post("/v2/projects", json=invalid_data)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_topic_data():
    """Test creating topic with invalid data."""
    async with APITestClient() as client:
        # First create a valid project
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        # Test empty name
        invalid_data = {"name": "", "description": "Test"}
        response = await client.post(f"/v2/projects/{project_id}/topics", json=invalid_data)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_plan_data():
    """Test creating plan with invalid data."""
    async with APITestClient() as client:
        # First create a valid project and topic
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        topic_data = TestDataFactory.create_topic_data()
        topic_response = await client.post(f"/v2/projects/{project_id}/topics", json=topic_data)
        assert topic_response.status_code == 200
        topic_id = topic_response.json()["id"]
        
        # Test empty name
        invalid_data = {"name": "", "description": "Test"}
        response = await client.post(f"/topics/{topic_id}/plans", json=invalid_data)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_execution_data():
    """Test research execution with invalid data."""
    async with APITestClient() as client:
        # First create a valid project, topic, and approved plan
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        topic_data = TestDataFactory.create_topic_data()
        topic_response = await client.post(f"/v2/projects/{project_id}/topics", json=topic_data)
        assert topic_response.status_code == 200
        topic_id = topic_response.json()["id"]
        
        plan_data = TestDataFactory.create_plan_data()
        plan_response = await client.post(f"/topics/{topic_id}/plans", json=plan_data)
        assert plan_response.status_code == 200
        plan_id = plan_response.json()["id"]
        
        # Approve the plan
        approve_response = await client.post(f"/plans/{plan_id}/approve")
        assert approve_response.status_code == 200
        
        # Test invalid depth
        invalid_data = {"task_type": "literature_review", "depth": "invalid_depth"}
        response = await client.post(f"/v2/topics/{topic_id}/execute", json=invalid_data)
        assert response.status_code == 400
        
        # Test invalid task type
        invalid_data = {"task_type": "invalid_task", "depth": "undergraduate"}
        response = await client.post(f"/v2/topics/{topic_id}/execute", json=invalid_data)
        assert response.status_code == 422


# =============================================================================
# DATA VALIDATION TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_project_name_validation():
    """Test project name validation."""
    async with APITestClient() as client:
        # Test whitespace-only name
        invalid_data = {"name": "   ", "description": "Test"}
        response = await client.post("/v2/projects", json=invalid_data)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_topic_name_validation():
    """Test topic name validation."""
    async with APITestClient() as client:
        # First create a valid project
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        # Test whitespace-only name
        invalid_data = {"name": "   ", "description": "Test"}
        response = await client.post(f"/v2/projects/{project_id}/topics", json=invalid_data)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_plan_name_validation():
    """Test plan name validation."""
    async with APITestClient() as client:
        # First create a valid project and topic
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        topic_data = TestDataFactory.create_topic_data()
        topic_response = await client.post(f"/v2/projects/{project_id}/topics", json=topic_data)
        assert topic_response.status_code == 200
        topic_id = topic_response.json()["id"]
        
        # Test whitespace-only name
        invalid_data = {"name": "   ", "description": "Test"}
        response = await client.post(f"/topics/{topic_id}/plans", json=invalid_data)
        assert response.status_code == 422


# =============================================================================
# UTILITY FUNCTIONS FOR RUNNING TESTS
# =============================================================================

def run_single_test(test_function_name: str):
    """Run a single test function."""
    import sys
    import importlib
    
    # Get the current module
    current_module = sys.modules[__name__]
    
    # Get the test function
    test_function = getattr(current_module, test_function_name)
    
    # Run the test
    try:
        asyncio.run(test_function())
        print(f"✅ {test_function_name} passed")
    except Exception as e:
        print(f"❌ {test_function_name} failed: {e}")


def run_all_tests():
    """Run all test functions."""
    import sys
    
    # Get all test functions
    current_module = sys.modules[__name__]
    test_functions = [name for name in dir(current_module) if name.startswith('test_')]
    
    passed = 0
    failed = 0
    
    print(f"Running {len(test_functions)} tests...\n")
    
    for test_name in test_functions:
        try:
            test_function = getattr(current_module, test_name)
            asyncio.run(test_function())
            print(f"✅ {test_name}")
            passed += 1
        except Exception as e:
            print(f"❌ {test_name}: {e}")
            failed += 1
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    """Run tests when script is executed directly."""
    import sys
    
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        if not test_name.startswith('test_'):
            test_name = f"test_{test_name}"
        run_single_test(test_name)
    else:
        # Run all tests
        run_all_tests()

