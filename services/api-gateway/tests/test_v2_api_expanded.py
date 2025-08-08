"""
Expanded unit tests for API Gateway v2 hierarchical endpoints.
Goal: Achieve >80% test coverage across v2_hierarchical_api.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime

# Import the functions we want to test directly
from v2_hierarchical_api import (
    create_project, list_projects, get_project, update_project, delete_project,
    create_research_topic, list_research_topics, get_research_topic, 
    update_research_topic, delete_research_topic,
    create_research_plan, list_research_plans, get_research_plan,
    update_research_plan, delete_research_plan, approve_research_plan,
    get_project_stats, get_topic_stats, get_plan_stats,
    get_project_hierarchy, get_execution_progress
)
from src.data_models.hierarchical_data_models import (
    ProjectRequest, ResearchTopicRequest, ResearchPlanRequest
)


class TestProjectEndpointsExpanded:
    """Expanded unit tests for project endpoint functions."""
    
    @pytest.mark.asyncio
    async def test_create_project_function(self):
        """Test create project function directly."""
        # Mock dependencies
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(return_value=True)
        
        # Create test request
        project_request = ProjectRequest(
            name="Test Project",
            description="A test project",
            metadata={"test": True}
        )
        
        # Call the function directly
        result = await create_project(project_request, mock_db, mock_mcp_client)
        
        # Verify result
        assert result.name == "Test Project"
        assert result.description == "A test project"
        assert result.status == "pending"
        assert result.metadata == {"test": True}
        assert result.id is not None
        
        # Verify MCP client was called
        mock_mcp_client.send_research_action.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_list_projects_function(self):
        """Test list projects function directly."""
        # Mock dependencies
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        
        # Mock database response
        mock_db.query.return_value = [
            {"id": "1", "name": "Project 1", "description": "Test 1"},
            {"id": "2", "name": "Project 2", "description": "Test 2"}
        ]
        
        # Call the function
        result = await list_projects(mock_db)
        
        # Verify results
        assert len(result) == 2
        assert result[0].name == "Project 1"
        assert result[1].name == "Project 2"
        mock_db.query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_project_function(self):
        """Test get project by ID function."""
        # Mock dependencies
        mock_db = AsyncMock()
        
        # Mock database response
        mock_db.get_project.return_value = {
            "id": "test-123",
            "name": "Test Project",
            "description": "Test Description",
            "metadata": {},
            "topics_count": 0,
            "plans_count": 0,
            "tasks_count": 0,
            "total_cost": 0.0,
            "completion_rate": 0.0
        }
        mock_db.get_project_stats.return_value = {}
        
        # Call the function
        result = await get_project("test-123", mock_db)
        
        # Verify result
        assert result.id == "test-123"
        assert result.name == "Test Project"
        mock_db.get_project.assert_called_once_with("test-123")
    
    @pytest.mark.asyncio
    async def test_update_project_function(self):
        """Test update project function."""
        # Mock dependencies
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(return_value=True)
        
        # Mock existing project check
        mock_db.get_project.return_value = {
            "id": "test-123",
            "name": "Old Name",
            "description": "Old Description"
        }
        
        # Create update request
        project_update = ProjectRequest(
            name="Updated Name",
            description="Updated Description"
        )
        
        # Call the function
        result = await update_project(project_update, "test-123", mock_db, mock_mcp_client)
        
        # Verify result
        assert result.name == "Updated Name"
        assert result.description == "Updated Description"
        mock_mcp_client.send_research_action.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_project_function(self):
        """Test delete project function."""
        # Mock dependencies
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(return_value=True)
        
        # Mock existing project check
        mock_db.get_project.return_value = {
            "id": "test-123",
            "name": "Test Project"
        }
        
        # Call the function
        result = await delete_project("test-123", mock_db, mock_mcp_client)
        
        # Verify result
        assert result.success is True
        mock_mcp_client.send_research_action.assert_called_once()


class TestResearchTopicEndpointsExpanded:
    """Expanded unit tests for research topic endpoint functions."""
    
    @pytest.mark.asyncio
    async def test_create_research_topic_function(self):
        """Test create research topic function."""
        # Mock dependencies
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(return_value=True)
        
        # Create test request
        topic_request = ResearchTopicRequest(
            name="Test Topic",
            description="Test Description"
        )
        
        # Call the function
        result = await create_research_topic(topic_request, "project-123", mock_db, mock_mcp_client)
        
        # Verify result
        assert result.name == "Test Topic"
        assert result.description == "Test Description"
        assert result.project_id == "project-123"
        mock_mcp_client.send_research_action.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_research_topics_function(self):
        """Test list research topics function."""
        # Mock dependencies
        mock_db = AsyncMock()
        
        # Mock database response
        mock_db.query.return_value = [
            {"id": "1", "name": "Topic 1", "project_id": "project-123"},
            {"id": "2", "name": "Topic 2", "project_id": "project-123"}
        ]
        
        # Call the function
        result = await list_research_topics("project-123", mock_db)
        
        # Verify results
        assert len(result) == 2
        assert result[0].name == "Topic 1"
        assert result[1].name == "Topic 2"
        mock_db.query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_research_topic_function(self):
        """Test get research topic by ID function."""
        # Mock dependencies
        mock_db = AsyncMock()
        
        # Mock database response
        mock_db.get_research_topic.return_value = {
            "id": "topic-123",
            "name": "Test Topic",
            "description": "Test Description",
            "project_id": "project-123"
        }
        
        # Call the function
        result = await get_research_topic("topic-123", mock_db)
        
        # Verify result
        assert result.id == "topic-123"
        assert result.name == "Test Topic"
        mock_db.get_research_topic.assert_called_once_with("topic-123")
    
    @pytest.mark.asyncio
    async def test_update_research_topic_function(self):
        """Test update research topic function."""
        # Mock dependencies
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(return_value=True)
        
        # Mock existing topic check
        mock_db.get_research_topic.return_value = {
            "id": "topic-123",
            "name": "Old Name"
        }
        
        # Create update request
        topic_update = ResearchTopicRequest(
            name="Updated Topic",
            description="Updated Description"
        )
        
        # Call the function (note parameter order from function signature)
        result = await update_research_topic(topic_update, "topic-123", mock_db, mock_mcp_client)
        
        # Verify result
        assert result.name == "Updated Topic"
        mock_mcp_client.send_research_action.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_research_topic_function(self):
        """Test delete research topic function."""
        # Mock dependencies
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(return_value=True)
        
        # Mock existing topic check
        mock_db.get_research_topic.return_value = {
            "id": "topic-123",
            "name": "Test Topic"
        }
        
        # Call the function
        result = await delete_research_topic("topic-123", mock_db, mock_mcp_client)
        
        # Verify result
        assert result.success is True
        mock_mcp_client.send_research_action.assert_called_once()


class TestResearchPlanEndpointsExpanded:
    """Expanded unit tests for research plan endpoint functions."""
    
    @pytest.mark.asyncio
    async def test_create_research_plan_function(self):
        """Test create research plan function."""
        # Mock dependencies
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(return_value=True)
        
        # Create a minimal plan request
        plan_request = ResearchPlanRequest(
            name="Test Plan",
            description="Test Description"
        )
        
        # Call the function
        result = await create_research_plan(plan_request, "topic-123", mock_db, mock_mcp_client)
        
        # Verify result
        assert result.topic_id == "topic-123"
        mock_mcp_client.send_research_action.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_research_plans_function(self):
        """Test list research plans function."""
        # Mock dependencies
        mock_db = AsyncMock()
        
        # Mock database response
        mock_db.query.return_value = [
            {"id": "1", "name": "Plan 1", "topic_id": "topic-123"},
            {"id": "2", "name": "Plan 2", "topic_id": "topic-123"}
        ]
        
        # Call the function
        result = await list_research_plans("topic-123", mock_db)
        
        # Verify results
        assert len(result) == 2
        assert result[0].name == "Plan 1"
        assert result[1].name == "Plan 2"
        mock_db.query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_research_plan_function(self):
        """Test get research plan by ID function."""
        # Mock dependencies
        mock_db = AsyncMock()
        
        # Mock database response
        mock_db.get_research_plan.return_value = {
            "id": "plan-123",
            "name": "Test Plan",
            "description": "Test Description",
            "topic_id": "topic-123"
        }
        
        # Call the function
        result = await get_research_plan("plan-123", mock_db)
        
        # Verify result
        assert result.id == "plan-123"
        assert result.name == "Test Plan"
        mock_db.get_research_plan.assert_called_once_with("plan-123")
    
    @pytest.mark.asyncio
    async def test_update_research_plan_function(self):
        """Test update research plan function."""
        # Mock dependencies
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(return_value=True)
        
        # Mock existing plan check
        mock_db.get_research_plan.return_value = {
            "id": "plan-123",
            "name": "Old Plan"
        }
        
        # Create update request
        plan_update = ResearchPlanRequest(
            name="Updated Plan",
            description="Updated Description"
        )
        
        # Call the function (note parameter order from function signature)
        result = await update_research_plan(plan_update, "plan-123", mock_db, mock_mcp_client)
        
        # Verify result
        assert result.name == "Updated Plan"
        mock_mcp_client.send_research_action.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_research_plan_function(self):
        """Test delete research plan function."""
        # Mock dependencies
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(return_value=True)
        
        # Mock existing plan check
        mock_db.get_research_plan.return_value = {
            "id": "plan-123",
            "name": "Test Plan"
        }
        
        # Call the function
        result = await delete_research_plan("plan-123", mock_db, mock_mcp_client)
        
        # Verify result
        assert result.success is True
        mock_mcp_client.send_research_action.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_approve_research_plan_function(self):
        """Test approve research plan function."""
        # Mock dependencies
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(return_value=True)
        
        # Mock existing plan check
        mock_db.get_research_plan.return_value = {
            "id": "plan-123",
            "name": "Test Plan",
            "status": "pending"
        }
        
        # Call the function
        result = await approve_research_plan("plan-123", mock_db, mock_mcp_client)
        
        # Verify result
        assert result.success is True
        mock_mcp_client.send_research_action.assert_called_once()


class TestStatsEndpointsExpanded:
    """Expanded unit tests for statistics endpoint functions."""
    
    @pytest.mark.asyncio
    async def test_get_project_stats_function(self):
        """Test get project stats function."""
        # Mock dependencies
        mock_db = AsyncMock()
        
        # Mock database responses
        mock_db.query.return_value = [{"count": 5}]
        
        # Call the function
        result = await get_project_stats("project-123", mock_db)
        
        # Verify result
        assert result.total_topics == 5
        mock_db.query.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_topic_stats_function(self):
        """Test get topic stats function."""
        # Mock dependencies
        mock_db = AsyncMock()
        
        # Mock database responses
        mock_db.query.return_value = [{"count": 3}]
        
        # Call the function
        result = await get_topic_stats("topic-123", mock_db)
        
        # Verify result
        assert result.total_plans == 3
        mock_db.query.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_plan_stats_function(self):
        """Test get plan stats function."""
        # Mock dependencies
        mock_db = AsyncMock()
        
        # Mock database responses
        mock_db.query.return_value = [{"count": 2}]
        
        # Call the function
        result = await get_plan_stats("plan-123", mock_db)
        
        # Verify result
        assert result.total_tasks == 2
        mock_db.query.assert_called()


class TestUtilityEndpointsExpanded:
    """Expanded unit tests for utility endpoint functions."""
    
    @pytest.mark.asyncio
    async def test_get_project_hierarchy_function(self):
        """Test get project hierarchy function."""
        # Mock dependencies
        mock_db = AsyncMock()
        
        # Mock database responses for hierarchy data
        mock_db.query.return_value = [
            {
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
        ]
        
        # Call the function
        result = await get_project_hierarchy("project-123", mock_db)
        
        # Verify result structure
        assert result.id == "project-123"
        assert result.name == "Test Project"
        mock_db.query.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_execution_progress_function(self):
        """Test get execution progress function."""
        # Mock dependencies
        mock_db = AsyncMock()
        
        # Mock database responses for progress data
        mock_db.query.return_value = [
            {
                "task_id": "task-123",
                "status": "completed",
                "progress": 100,
                "estimated_completion": "2024-01-15"
            }
        ]
        
        # Call the function
        result = await get_execution_progress("plan-123", mock_db)
        
        # Verify result
        assert "progress" in result or "overall_progress" in result
        mock_db.query.assert_called()


class TestErrorHandlingExpanded:
    """Expanded unit tests for error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_project_creation_mcp_disconnected(self):
        """Test project creation when MCP client is disconnected."""
        from fastapi import HTTPException
        
        # Mock dependencies
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = False
        
        # Create test request
        project_request = ProjectRequest(
            name="Test Project",
            description="Test Description"
        )
        
        # Should raise HTTPException with 503 status
        with pytest.raises(HTTPException) as exc_info:
            await create_project(project_request, mock_db, mock_mcp_client)
        
        assert exc_info.value.status_code == 503
    
    @pytest.mark.asyncio
    async def test_project_creation_mcp_error(self):
        """Test project creation when MCP client raises an error."""
        from fastapi import HTTPException
        
        # Mock dependencies
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(side_effect=Exception("MCP Error"))
        
        # Create test request
        project_request = ProjectRequest(
            name="Test Project",
            description="Test Description"
        )
        
        # Should raise HTTPException with 500 status
        with pytest.raises(HTTPException) as exc_info:
            await create_project(project_request, mock_db, mock_mcp_client)
        
        assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_get_project_not_found(self):
        """Test get project when project doesn't exist."""
        from fastapi import HTTPException
        
        # Mock dependencies
        mock_db = AsyncMock()
        mock_db.get_project.return_value = None
        
        # Should raise HTTPException with 404 status
        with pytest.raises(HTTPException) as exc_info:
            await get_project("nonexistent-123", mock_db)
        
        assert exc_info.value.status_code == 404
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self):
        """Test database error handling."""
        from fastapi import HTTPException
        
        # Mock dependencies
        mock_db = AsyncMock()
        mock_db.query.side_effect = Exception("Database error")
        
        # Should raise HTTPException with 500 status
        with pytest.raises(HTTPException) as exc_info:
            await list_projects(mock_db)
        
        assert exc_info.value.status_code == 500


class TestValidationExpanded:
    """Expanded unit tests for input validation scenarios."""
    
    @pytest.mark.asyncio
    async def test_empty_project_name_validation(self):
        """Test validation for empty project name."""
        from fastapi import HTTPException
        
        # Mock dependencies
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        
        # Create request with empty name
        project_request = ProjectRequest(
            name="",  # Empty name should trigger validation
            description="Test Description"
        )
        
        # Should raise HTTPException with 400 status
        with pytest.raises(HTTPException) as exc_info:
            await create_project(project_request, mock_db, mock_mcp_client)
        
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_invalid_id_format_validation(self):
        """Test validation for invalid ID format."""
        from fastapi import HTTPException
        
        # Mock dependencies
        mock_db = AsyncMock()
        
        # Should raise HTTPException with 400 status for empty ID
        with pytest.raises(HTTPException) as exc_info:
            await get_project("", mock_db)
        
        assert exc_info.value.status_code == 400
