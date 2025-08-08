"""Test suite optimized for maximum coverage of v2_hierarchical_api.py functions."""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

# Import the API functions directly
from v2_hierarchical_api import (
    create_project, list_projects, get_project, update_project, delete_project,
    create_research_topic, list_research_topics, get_research_topic, 
    update_research_topic, delete_research_topic,
    create_research_plan, list_research_plans, get_research_plan,
    update_research_plan, delete_research_plan, approve_research_plan,
    get_project_stats, get_topic_stats, get_plan_stats,
    get_project_hierarchy, get_execution_progress
)

# Import data models
from src.data_models.hierarchical_data_models import (
    ProjectRequest, ProjectUpdate, ResearchTopicRequest, ResearchTopicUpdate, 
    ResearchPlanRequest, ProjectResponse, ResearchTopicResponse, ResearchPlanResponse
)


class TestAPIFunctionsCoverage:
    """Optimized test suite for maximum coverage."""

    @pytest.mark.asyncio
    async def test_create_project_success(self):
        """Test successful project creation."""
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(return_value=True)

        project_request = ProjectRequest(
            name="Test Project",
            description="Test Description"
        )

        result = await create_project(project_request, mock_db, mock_mcp_client)
        assert result.name == "Test Project"
        assert result.description == "Test Description"
        mock_mcp_client.send_research_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_project_mcp_disconnected(self):
        """Test project creation with MCP disconnected."""
        from fastapi import HTTPException

        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = False

        project_request = ProjectRequest(
            name="Test Project",
            description="Test Description"
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_project(project_request, mock_db, mock_mcp_client)
        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_get_project_with_complete_data(self):
        """Test get project with full data fields."""
        mock_db = AsyncMock()
        
        # Mock complete project data with all required fields
        mock_db.get_project.return_value = {
            "id": "test-123",
            "name": "Test Project",
            "description": "Test Description",
            "status": "active",
            "metadata": {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        mock_db.get_project_stats.return_value = {
            "topics_count": 2,
            "plans_count": 3,
            "tasks_count": 5,
            "total_cost": 100.0,
            "completion_rate": 0.6
        }

        result = await get_project("test-123", mock_db)
        assert result.id == "test-123"
        assert result.name == "Test Project"
        assert result.topics_count == 2
        assert result.plans_count == 3

    @pytest.mark.asyncio
    async def test_get_project_not_found(self):
        """Test get project when project doesn't exist."""
        from fastapi import HTTPException

        mock_db = AsyncMock()
        mock_db.get_project.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_project("nonexistent", mock_db)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_project_success(self):
        """Test successful project update."""
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(return_value=True)

        # Mock existing project with all required fields
        mock_db.get_project.return_value = {
            "id": "test-123",
            "name": "Old Name",
            "description": "Old Description",
            "status": "pending",
            "metadata": {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        project_update = ProjectUpdate(
            name="Updated Name",
            description="Updated Description",
            status="active"
        )

        result = await update_project(project_update, "test-123", mock_db, mock_mcp_client)
        assert result.name == "Updated Name"
        assert result.description == "Updated Description"
        assert result.status == "active"

    @pytest.mark.asyncio
    async def test_delete_project_success(self):
        """Test successful project deletion."""
        from fastapi import HTTPException

        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(return_value=True)

        # Mock existing project
        mock_db.get_project.return_value = {
            "id": "test-123",
            "name": "Test Project"
        }

        result = await delete_project("test-123", mock_db, mock_mcp_client)
        assert result["success"] == True
        assert "deleted" in result["message"]

    @pytest.mark.asyncio
    async def test_create_research_topic_success(self):
        """Test successful research topic creation."""
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(return_value=True)

        # Mock project exists
        mock_db.get_project.return_value = {"id": "project-123"}

        topic_request = ResearchTopicRequest(
            name="Test Topic",
            description="Test Description",
            project_id="project-123"
        )

        result = await create_research_topic(topic_request, mock_db, mock_mcp_client)
        assert result.name == "Test Topic"
        assert result.project_id == "project-123"

    @pytest.mark.asyncio
    async def test_get_research_topic_with_complete_data(self):
        """Test get research topic with complete data."""
        mock_db = AsyncMock()
        
        mock_db.get_research_topic.return_value = {
            "id": "topic-123",
            "name": "Test Topic", 
            "description": "Test Description",
            "project_id": "project-123",
            "status": "active",
            "metadata": {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "plans_count": 2,
            "tasks_count": 4
        }

        result = await get_research_topic("topic-123", mock_db)
        assert result.id == "topic-123"
        assert result.name == "Test Topic"
        assert result.project_id == "project-123"

    @pytest.mark.asyncio
    async def test_create_research_plan_success(self):
        """Test successful research plan creation."""
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(return_value=True)

        # Mock topic exists
        mock_db.get_research_topic.return_value = {"id": "topic-123"}

        plan_request = ResearchPlanRequest(
            name="Test Plan",
            description="Test Description",
            topic_id="topic-123"
        )

        result = await create_research_plan(plan_request, mock_db, mock_mcp_client)
        assert result.name == "Test Plan"
        assert result.topic_id == "topic-123"

    @pytest.mark.asyncio
    async def test_get_research_plan_with_complete_data(self):
        """Test get research plan with complete data."""
        mock_db = AsyncMock()
        
        mock_db.get_research_plan.return_value = {
            "id": "plan-123",
            "name": "Test Plan",
            "description": "Test Description", 
            "topic_id": "topic-123",
            "status": "pending",
            "plan_approved": False,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "tasks_count": 3,
            "completed_tasks": 1,
            "progress": 33.3
        }

        result = await get_research_plan("plan-123", mock_db)
        assert result.id == "plan-123"
        assert result.name == "Test Plan"
        assert result.tasks_count == 3

    @pytest.mark.asyncio
    async def test_approve_research_plan_success(self):
        """Test successful research plan approval."""
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(return_value=True)

        # Mock existing plan and related data
        mock_db.get_research_plan.return_value = {
            "id": "plan-123",
            "name": "Test Plan",
            "topic_id": "topic-123",
            "status": "pending",
            "plan_approved": False,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        mock_db.get_research_topic.return_value = {
            "id": "topic-123",
            "project_id": "project-123"
        }
        
        mock_db.get_project.return_value = {
            "id": "project-123",
            "status": "pending"
        }
        
        mock_db.get_tasks.return_value = [
            {"id": "task-1", "status": "pending"},
            {"id": "task-2", "status": "completed"}
        ]

        result = await approve_research_plan("plan-123", mock_db, mock_mcp_client)
        assert result.plan_approved == True
        assert result.status == "active"

    @pytest.mark.asyncio
    async def test_get_project_stats_success(self):
        """Test get project stats."""
        mock_db = AsyncMock()
        
        # Mock various database queries for project stats
        mock_db.query.side_effect = [
            [{"count": 5}],  # topics count
            [{"count": 8}],  # plans count
            [{"count": 12}], # tasks count
            [{"sum": 150.0}], # total cost
            [{"count": 4}]   # completed tasks for completion rate
        ]

        result = await get_project_stats("project-123", mock_db)
        assert result.topics_count == 5
        assert result.plans_count == 8
        assert result.tasks_count == 12
        assert result.total_cost == 150.0

    @pytest.mark.asyncio
    async def test_get_topic_stats_success(self):
        """Test get topic stats."""
        mock_db = AsyncMock()
        
        # Mock database queries for topic stats  
        mock_db.query.side_effect = [
            [{"count": 3}],   # plans count
            [{"count": 7}],   # tasks count
            [{"sum": 80.0}],  # total cost
            [{"count": 2}]    # completed tasks
        ]

        result = await get_topic_stats("topic-123", mock_db)
        assert result.plans_count == 3
        assert result.tasks_count == 7
        assert result.total_cost == 80.0

    @pytest.mark.asyncio 
    async def test_get_plan_stats_success(self):
        """Test get plan stats."""
        mock_db = AsyncMock()
        
        # Mock database queries for plan stats
        mock_db.query.side_effect = [
            [{"count": 6}],   # total tasks
            [{"count": 4}],   # completed tasks
            [{"sum": 50.0}]   # total cost
        ]

        result = await get_plan_stats("plan-123", mock_db)
        assert result.tasks_count == 6
        assert result.completed_tasks == 4
        assert result.total_cost == 50.0
        # Progress should be calculated as 4/6 = 66.67%
        assert abs(result.progress - 66.67) < 0.1

    @pytest.mark.asyncio
    async def test_get_execution_progress_success(self):
        """Test get execution progress."""
        mock_db = AsyncMock()
        
        # Mock tasks data for progress calculation
        mock_db.query.return_value = [
            {"task_id": "task-1", "status": "completed", "progress": 100},
            {"task_id": "task-2", "status": "in_progress", "progress": 50}
        ]

        result = await get_execution_progress("plan-123", mock_db)
        assert result["execution_id"] == "plan-123"
        assert "overall_progress" in result or "current_stage" in result

    @pytest.mark.asyncio
    async def test_list_projects_with_filters(self):
        """Test list projects with status filter."""
        mock_db = AsyncMock()
        
        # Mock database response
        mock_db.get_projects.return_value = [
            {
                "id": "1", 
                "name": "Project 1", 
                "description": "Test 1",
                "status": "active",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        ]
        mock_db.get_project_stats.return_value = {
            "topics_count": 1,
            "plans_count": 2, 
            "tasks_count": 3,
            "total_cost": 50.0,
            "completion_rate": 0.5
        }

        result = await list_projects("active", 10, mock_db)
        assert len(result) == 1
        assert result[0].name == "Project 1"
        assert result[0].status == "active"

    @pytest.mark.asyncio
    async def test_list_research_topics_success(self):
        """Test list research topics."""
        mock_db = AsyncMock()
        
        # Mock project exists
        mock_db.get_project.return_value = {"id": "project-123"}
        
        mock_db.get_research_topics.return_value = [
            {
                "id": "topic-1",
                "name": "Topic 1", 
                "project_id": "project-123",
                "status": "active",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        ]
        mock_db.get_research_plans.return_value = [{"id": "plan-1"}]

        result = await list_research_topics("project-123", None, mock_db)
        assert len(result) == 1
        assert result[0].name == "Topic 1"

    @pytest.mark.asyncio
    async def test_list_research_plans_success(self):
        """Test list research plans."""
        mock_db = AsyncMock()
        
        # Mock topic exists
        mock_db.get_research_topic.return_value = {"id": "topic-123"}
        
        mock_db.get_research_plans.return_value = [
            {
                "id": "plan-1",
                "name": "Plan 1",
                "topic_id": "topic-123", 
                "status": "pending",
                "plan_approved": False,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        ]
        mock_db.get_tasks.return_value = []

        result = await list_research_plans("topic-123", None, mock_db)
        assert len(result) == 1
        assert result[0].name == "Plan 1"

    @pytest.mark.asyncio
    async def test_get_project_hierarchy_success(self):
        """Test get project hierarchy."""
        mock_db = AsyncMock()
        
        # Mock hierarchy data as a regular dict (not async)
        hierarchy_data = {
            "id": "project-123",
            "name": "Test Project",
            "topics": [
                {
                    "id": "topic-123", 
                    "name": "Test Topic",
                    "plans": [
                        {"id": "plan-123", "name": "Test Plan"}
                    ]
                }
            ]
        }
        mock_db.get_project_hierarchy.return_value = hierarchy_data

        result = await get_project_hierarchy("project-123", mock_db)
        assert result.id == "project-123"
        assert result.name == "Test Project"

    @pytest.mark.asyncio
    async def test_error_handling_paths(self):
        """Test various error handling paths."""
        from fastapi import HTTPException
        
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        
        # Test project not found for update
        mock_db.get_project.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await update_project(ProjectUpdate(name="Test"), "nonexistent", mock_db, mock_mcp_client)
        assert exc_info.value.status_code == 404

        # Test topic not found for plan creation
        mock_db.get_research_topic.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            topic_request = ResearchTopicRequest(name="Test", description="Test", project_id="project-123")
            await create_research_topic(topic_request, mock_db, mock_mcp_client)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_validation_edge_cases(self):
        """Test validation edge cases."""
        from pydantic import ValidationError
        
        # Test empty name validation
        with pytest.raises(ValidationError):
            ProjectRequest(name="", description="Test")
            
        # Test empty topic name
        with pytest.raises(ValidationError):
            ResearchTopicRequest(name="", description="Test", project_id="project-123")
