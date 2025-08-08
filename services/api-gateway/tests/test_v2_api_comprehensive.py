"""
Comprehensive test suite for v2_hierarchical_api.py endpoints
Tests endpoints that are not covered in the simple test file to achieve >80% coverage
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from src.data_models.hierarchical_data_models import ProjectRequest, ResearchTopicRequest


class TestAdditionalProjectEndpoints:
    """Test additional project endpoints not covered in simple tests"""
    
    @pytest.mark.asyncio
    async def test_get_project_success(self):
        """Test successful project retrieval by ID."""
        # Import the function we need
        from v2_hierarchical_api import get_project
        
        # Mock dependencies
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        
        # Mock database to return a project
        mock_db.query.return_value = [{
            "id": "test-123",
            "name": "Test Project", 
            "description": "Test Description",
            "metadata": {}
        }]
        
        # Call the function
        result = await get_project("test-123", mock_db)
        
        # Verify result
        assert result.id == "test-123"
        assert result.name == "Test Project"
        mock_db.query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_project_not_found(self):
        """Test project retrieval when project doesn't exist."""
        from v2_hierarchical_api import get_project
        
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        
        # Mock database to return empty result
        mock_db.query.return_value = []
        
        # Should raise 404 HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await get_project("nonexistent-123", mock_db)
        
        assert exc_info.value.status_code == 404


class TestAdditionalTopicEndpoints:
    """Test additional topic endpoints not covered in simple tests"""
    
    @pytest.mark.asyncio 
    async def test_create_research_topic_success(self):
        """Test successful research topic creation."""
        from v2_hierarchical_api import create_research_topic
        
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
        assert result.project_id == "project-123"
        mock_mcp_client.send_research_action.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_research_topic_success(self):
        """Test successful research topic retrieval."""
        from v2_hierarchical_api import get_research_topic
        
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        
        # Mock database to return a topic
        mock_db.query.return_value = [{
            "id": "topic-123",
            "name": "Test Topic",
            "description": "Test Description", 
            "project_id": "project-123"
        }]
        
        result = await get_research_topic("topic-123", mock_db)
        
        assert result.id == "topic-123"
        assert result.name == "Test Topic"
        mock_db.query.assert_called_once()


class TestAdditionalPlanEndpoints:
    """Test additional plan endpoints not covered in simple tests"""
    
    @pytest.mark.asyncio
    async def test_create_research_plan_success(self):
        """Test successful research plan creation."""
        from v2_hierarchical_api import create_research_plan
        
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(return_value=True)
        
        result = await create_research_plan("topic-123", mock_db, mock_mcp_client)
        
        assert result.topic_id == "topic-123"
        mock_mcp_client.send_research_action.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_research_plan_success(self):
        """Test successful research plan retrieval."""
        from v2_hierarchical_api import get_research_plan
        
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        
        # Mock database to return a plan
        mock_db.query.return_value = [{
            "id": "plan-123",
            "name": "Test Plan",
            "description": "Test Description",
            "topic_id": "topic-123"
        }]
        
        result = await get_research_plan("plan-123", mock_db)
        
        assert result.id == "plan-123"
        assert result.name == "Test Plan"
        mock_db.query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_approve_research_plan_success(self):
        """Test successful research plan approval."""
        from v2_hierarchical_api import approve_research_plan
        
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(return_value=True)
        
        result = await approve_research_plan("plan-123", mock_db, mock_mcp_client)
        
        assert result.success is True
        mock_mcp_client.send_research_action.assert_called_once()


class TestAdditionalStatsEndpoints:
    """Test stats endpoints to increase coverage"""
    
    @pytest.mark.asyncio
    async def test_get_project_stats_success(self):
        """Test successful project stats retrieval."""
        from v2_hierarchical_api import get_project_stats
        
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        
        # Mock database to return stats
        mock_db.query.return_value = [{"count": 5}]
        
        result = await get_project_stats("project-123", mock_db)
        
        assert result.total_topics == 5
        mock_db.query.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_topic_stats_success(self):
        """Test successful topic stats retrieval."""
        from v2_hierarchical_api import get_topic_stats
        
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        
        # Mock database to return stats
        mock_db.query.return_value = [{"count": 3}]
        
        result = await get_topic_stats("topic-123", mock_db)
        
        assert result.total_plans == 3
        mock_db.query.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_plan_stats_success(self):
        """Test successful plan stats retrieval."""
        from v2_hierarchical_api import get_plan_stats
        
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        
        # Mock database to return stats
        mock_db.query.return_value = [{"count": 2}]
        
        result = await get_plan_stats("plan-123", mock_db)
        
        assert result.total_tasks == 2
        mock_db.query.assert_called()


class TestAdditionalErrorHandling:
    """Test additional error handling scenarios"""
    
    @pytest.mark.asyncio
    async def test_database_error_in_get_project(self):
        """Test database error handling in get_project."""
        from v2_hierarchical_api import get_project
        
        mock_db = AsyncMock()
        mock_db.query.side_effect = Exception("Database connection error")
        
        with pytest.raises(HTTPException) as exc_info:
            await get_project("test-123", mock_db)
        
        assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_mcp_client_error_in_create_topic(self):
        """Test MCP client error handling in create_research_topic."""
        from v2_hierarchical_api import create_research_topic
        
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(side_effect=Exception("MCP error"))
        
        topic_request = ResearchTopicRequest(
            name="Test Topic",
            description="Test Description"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await create_research_topic(topic_request, "project-123", mock_db, mock_mcp_client)
        
        assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_mcp_client_disconnected_error(self):
        """Test MCP client disconnected error."""
        from v2_hierarchical_api import create_project
        
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


class TestAdditionalValidation:
    """Test additional validation scenarios"""
    
    @pytest.mark.asyncio
    async def test_empty_project_name_validation(self):
        """Test validation for empty project name."""
        from v2_hierarchical_api import create_project
        
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        
        project_request = ProjectRequest(
            name="",  # Empty name should trigger validation error
            description="Test Description"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await create_project(project_request, mock_db, mock_mcp_client)
        
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_invalid_project_id_format(self):
        """Test validation for invalid project ID format."""
        from v2_hierarchical_api import get_project
        
        mock_db = AsyncMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await get_project("", mock_db)  # Empty ID should trigger validation error
        
        assert exc_info.value.status_code == 400


class TestAdditionalListEndpoints:
    """Test list endpoints to increase coverage"""
    
    @pytest.mark.asyncio
    async def test_list_research_topics_success(self):
        """Test successful research topics listing."""
        from v2_hierarchical_api import list_research_topics
        
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        
        # Mock database to return empty list
        mock_db.query.return_value = []
        
        result = await list_research_topics("project-123", mock_db)
        
        # Should return list of topics (empty in this case)
        assert isinstance(result, list)
        assert len(result) == 0
        mock_db.query.assert_called()
    
    @pytest.mark.asyncio
    async def test_list_research_plans_success(self):
        """Test successful research plans listing."""
        from v2_hierarchical_api import list_research_plans
        
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        
        # Mock database to return empty list
        mock_db.query.return_value = []
        
        result = await list_research_plans("topic-123", mock_db)
        
        # Should return list of plans (empty in this case)
        assert isinstance(result, list)
        assert len(result) == 0
        mock_db.query.assert_called()
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException

from v2_hierarchical_api import (
    create_project, list_projects, get_project, update_project, delete_project,
    create_research_topic, list_research_topics, get_research_topic, update_research_topic, delete_research_topic,
    create_research_plan, list_research_plans, get_research_plan, update_research_plan, delete_research_plan,
    approve_research_plan, get_project_stats, get_topic_stats, get_plan_stats
)
from src.data_models.hierarchical_data_models import (
    ProjectRequest, ResearchTopicRequest, ResearchPlanRequest, TaskRequest
)


class TestProjectCRUDOperations:
    """Test all project CRUD operations"""
    
    @pytest.mark.asyncio
    async def test_get_project_success(self):
        # Test successful project retrieval
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_db.query.return_value = [{"id": "test-123", "name": "Test Project"}]
        
        result = await get_project("test-123", mock_db, mock_mcp_client)
        
        assert result.id == "test-123"
        assert result.name == "Test Project"
    
    @pytest.mark.asyncio
    async def test_update_project_success(self):
        # Test successful project update
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(return_value=True)
        
        project_update = ProjectRequest(
            name="Updated Project",
            description="Updated Description"
        )
        
        result = await update_project("test-123", project_update, mock_db, mock_mcp_client)
        
        assert result.name == "Updated Project"
        mock_mcp_client.send_research_action.assert_called_once()
    
    @pytest.mark.asyncio  
    async def test_delete_project_success(self):
        # Test successful project deletion
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(return_value=True)
        
        result = await delete_project("test-123", mock_db, mock_mcp_client)
        
        assert result.success is True
        mock_mcp_client.send_research_action.assert_called_once()


class TestResearchTopicCRUDOperations:
    """Test all research topic CRUD operations"""
    
    @pytest.mark.asyncio
    async def test_create_research_topic_success(self):
        # Test successful research topic creation
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(return_value=True)
        
        topic_request = ResearchTopicRequest(
            name="Test Topic",
            description="Test Description"
        )
        
        result = await create_research_topic("project-123", topic_request, mock_db, mock_mcp_client)
        
        assert result.name == "Test Topic"
        assert result.description == "Test Description"
        mock_mcp_client.send_research_action.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_research_topic_success(self):
        # Test successful research topic retrieval
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_db.query.return_value = [{"id": "topic-123", "name": "Test Topic"}]
        
        result = await get_research_topic("topic-123", mock_db, mock_mcp_client)
        
        assert result.id == "topic-123"
        assert result.name == "Test Topic"
    
    @pytest.mark.asyncio
    async def test_update_research_topic_success(self):
        # Test successful research topic update
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(return_value=True)
        
        topic_update = ResearchTopicRequest(
            name="Updated Topic",
            description="Updated Description"
        )
        
        result = await update_research_topic("topic-123", topic_update, mock_db, mock_mcp_client)
        
        assert result.name == "Updated Topic"
        mock_mcp_client.send_research_action.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_research_topic_success(self):
        # Test successful research topic deletion
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(return_value=True)
        
        result = await delete_research_topic("topic-123", mock_db, mock_mcp_client)
        
        assert result.success is True
        mock_mcp_client.send_research_action.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_research_topics_success(self):
        # Test listing research topics
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_db.query.return_value = []
        
        result = await list_research_topics("project-123", mock_db, mock_mcp_client)
        
        assert result.topics == []
        assert result.total == 0


class TestResearchPlanCRUDOperations:
    """Test all research plan CRUD operations"""
    
    @pytest.mark.asyncio
    async def test_create_research_plan_success(self):
        # Test successful research plan creation
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(return_value=True)
        
        result = await create_research_plan("topic-123", mock_db, mock_mcp_client)
        
        assert result.topic_id == "topic-123"
        mock_mcp_client.send_research_action.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_research_plan_success(self):
        # Test successful research plan retrieval
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_db.query.return_value = [{"id": "plan-123", "name": "Test Plan"}]
        
        result = await get_research_plan("plan-123", mock_db, mock_mcp_client)
        
        assert result.id == "plan-123"
        assert result.name == "Test Plan"
    
    @pytest.mark.asyncio
    async def test_update_research_plan_success(self):
        # Test successful research plan update
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(return_value=True)
        
        plan_update = ResearchPlanRequest(
            name="Updated Plan",
            description="Updated Description"
        )
        
        result = await update_research_plan("plan-123", plan_update, mock_db, mock_mcp_client)
        
        assert result.name == "Updated Plan"
        mock_mcp_client.send_research_action.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_research_plan_success(self):
        # Test successful research plan deletion
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(return_value=True)
        
        result = await delete_research_plan("plan-123", mock_db, mock_mcp_client)
        
        assert result.success is True
        mock_mcp_client.send_research_action.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_approve_research_plan_success(self):
        # Test successful research plan approval
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(return_value=True)
        
        result = await approve_research_plan("plan-123", mock_db, mock_mcp_client)
        
        assert result.success is True
        mock_mcp_client.send_research_action.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_research_plans_success(self):
        # Test listing research plans
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_db.query.return_value = []
        
        result = await list_research_plans("topic-123", mock_db, mock_mcp_client)
        
        assert result.plans == []
        assert result.total == 0


class TestStatsOperations:
    """Test statistics operations"""
    
    @pytest.mark.asyncio
    async def test_get_project_stats_success(self):
        # Test successful project stats retrieval
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_db.query.return_value = [{"count": 5}]
        
        result = await get_project_stats("project-123", mock_db, mock_mcp_client)
        
        assert result.total_topics == 5
        mock_db.query.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_topic_stats_success(self):
        # Test successful topic stats retrieval
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_db.query.return_value = [{"count": 3}]
        
        result = await get_topic_stats("topic-123", mock_db, mock_mcp_client)
        
        assert result.total_plans == 3
        mock_db.query.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_plan_stats_success(self):
        # Test successful plan stats retrieval
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_db.query.return_value = [{"count": 2}]
        
        result = await get_plan_stats("plan-123", mock_db, mock_mcp_client)
        
        assert result.total_tasks == 2
        mock_db.query.assert_called()


class TestErrorHandlingComprehensive:
    """Test comprehensive error handling scenarios"""
    
    @pytest.mark.asyncio
    async def test_database_connection_error_project(self):
        # Test database connection error for project operations
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_db.query.side_effect = Exception("Database error")
        
        with pytest.raises(HTTPException) as exc_info:
            await get_project("test-123", mock_db, mock_mcp_client)
        
        assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_mcp_client_error_topic_creation(self):
        # Test MCP client error for topic creation
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(side_effect=Exception("MCP error"))
        
        topic_request = ResearchTopicRequest(
            name="Test Topic",
            description="Test Description"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await create_research_topic("project-123", topic_request, mock_db, mock_mcp_client)
        
        assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_mcp_client_disconnected(self):
        # Test MCP client disconnected scenario
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


class TestValidationAndEdgeCases:
    """Test validation and edge cases"""
    
    @pytest.mark.asyncio
    async def test_empty_project_name(self):
        # Test empty project name validation
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        
        project_request = ProjectRequest(
            name="",
            description="Test Description"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await create_project(project_request, mock_db, mock_mcp_client)
        
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_invalid_project_id(self):
        # Test invalid project ID format
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_db.query.return_value = []
        
        with pytest.raises(HTTPException) as exc_info:
            await get_project("", mock_db, mock_mcp_client)
        
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_nonexistent_resource(self):
        # Test accessing non-existent resource
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_db.query.return_value = []
        
        with pytest.raises(HTTPException) as exc_info:
            await get_project("nonexistent-123", mock_db, mock_mcp_client)
        
        assert exc_info.value.status_code == 404
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException

from v2_hierarchical_api import (
    create_project, list_projects, get_project, update_project, delete_project,
    create_research_topic, list_research_topics, get_research_topic, update_research_topic, delete_research_topic,
    create_research_plan, list_research_plans, get_research_plan, update_research_plan, delete_research_plan,
    approve_research_plan, get_project_stats, get_topic_stats, get_plan_stats
)
from src.data_models.hierarchical_data_models import (
    ProjectRequest, ResearchTopicRequest, ResearchPlanRequest, TaskRequest
)

class TestProjectCRUDOperations:
    """Test all project CRUD operations"""
    
    def test_create_project_success(self, test_config, mock_database, mock_mcp_client):
        # Test successful project creation
        request = ProjectCreateRequest(
            name="Test Project",
            description="Test Description",
            objectives=["Objective 1"]
        )
        
        # Mock MCP client call_tool to return success
        mock_mcp_client.call_tool.return_value = {"success": True, "project_id": "test-123"}
        
        result = create_project(request, mock_database, mock_mcp_client)
        
        assert result["success"] is True
        assert result["project_id"] == "test-123"
        mock_mcp_client.call_tool.assert_called_once()
    
    def test_update_project_success(self, test_config, mock_database, mock_mcp_client):
        # Test successful project update
        request = ProjectUpdateRequest(
            name="Updated Project",
            description="Updated Description"
        )
        
        mock_mcp_client.call_tool.return_value = {"success": True}
        
        result = update_project("test-123", request, mock_database, mock_mcp_client)
        
        assert result["success"] is True
        mock_mcp_client.call_tool.assert_called_once()
    
    def test_delete_project_success(self, test_config, mock_database, mock_mcp_client):
        # Test successful project deletion
        mock_mcp_client.call_tool.return_value = {"success": True}
        
        result = delete_project("test-123", mock_database, mock_mcp_client)
        
        assert result["success"] is True
        mock_mcp_client.call_tool.assert_called_once()
    
    def test_list_projects_empty(self, test_config, mock_database, mock_mcp_client):
        # Test listing projects when none exist
        mock_database.query.return_value = []
        
        result = list_projects(mock_database, limit=10, offset=0)
        
        assert result == {"projects": [], "total": 0, "limit": 10, "offset": 0}


class TestResearchTopicCRUDOperations:
    """Test all research topic CRUD operations"""
    
    def test_create_research_topic_success(self, test_config, mock_database, mock_mcp_client):
        # Test successful research topic creation
        request = ResearchTopicCreateRequest(
            name="Test Topic",
            description="Test Description",
            project_id="project-123"
        )
        
        mock_mcp_client.call_tool.return_value = {"success": True, "topic_id": "topic-123"}
        
        result = create_research_topic(request, mock_database, mock_mcp_client)
        
        assert result["success"] is True
        assert result["topic_id"] == "topic-123"
        mock_mcp_client.call_tool.assert_called_once()
    
    def test_update_research_topic_success(self, test_config, mock_database, mock_mcp_client):
        # Test successful research topic update
        request = ResearchTopicUpdateRequest(
            name="Updated Topic",
            description="Updated Description"
        )
        
        mock_mcp_client.call_tool.return_value = {"success": True}
        
        result = update_research_topic("topic-123", request, mock_database, mock_mcp_client)
        
        assert result["success"] is True
        mock_mcp_client.call_tool.assert_called_once()
    
    def test_delete_research_topic_success(self, test_config, mock_database, mock_mcp_client):
        # Test successful research topic deletion
        mock_mcp_client.call_tool.return_value = {"success": True}
        
        result = delete_research_topic("topic-123", mock_database, mock_mcp_client)
        
        assert result["success"] is True
        mock_mcp_client.call_tool.assert_called_once()
    
    def test_list_research_topics_empty(self, test_config, mock_database, mock_mcp_client):
        # Test listing research topics when none exist
        mock_database.query.return_value = []
        
        result = list_research_topics("project-123", mock_database, limit=10, offset=0)
        
        assert result == {"topics": [], "total": 0, "limit": 10, "offset": 0}


class TestResearchPlanCRUDOperations:
    """Test all research plan CRUD operations"""
    
    def test_update_research_plan_success(self, test_config, mock_database, mock_mcp_client):
        # Test successful research plan update
        request = ResearchPlanUpdateRequest(
            name="Updated Plan",
            description="Updated Description"
        )
        
        mock_mcp_client.call_tool.return_value = {"success": True}
        
        result = update_research_plan("plan-123", request, mock_database, mock_mcp_client)
        
        assert result["success"] is True
        mock_mcp_client.call_tool.assert_called_once()
    
    def test_delete_research_plan_success(self, test_config, mock_database, mock_mcp_client):
        # Test successful research plan deletion
        mock_mcp_client.call_tool.return_value = {"success": True}
        
        result = delete_research_plan("plan-123", mock_database, mock_mcp_client)
        
        assert result["success"] is True
        mock_mcp_client.call_tool.assert_called_once()
    
    def test_approve_research_plan_success(self, test_config, mock_database, mock_mcp_client):
        # Test successful research plan approval
        mock_mcp_client.call_tool.return_value = {"success": True}
        
        result = approve_research_plan("plan-123", mock_database, mock_mcp_client)
        
        assert result["success"] is True
        mock_mcp_client.call_tool.assert_called_once()
    
    def test_list_research_plans_empty(self, test_config, mock_database, mock_mcp_client):
        # Test listing research plans when none exist
        mock_database.query.return_value = []
        
        result = list_research_plans("topic-123", mock_database, limit=10, offset=0)
        
        assert result == {"plans": [], "total": 0, "limit": 10, "offset": 0}
    
    def test_create_research_plan_success(self, test_config, mock_database, mock_mcp_client):
        # Test successful research plan creation
        mock_mcp_client.call_tool.return_value = {"success": True, "plan_id": "plan-123"}
        
        result = create_research_plan("topic-123", mock_database, mock_mcp_client)
        
        assert result["success"] is True
        assert result["plan_id"] == "plan-123"
        mock_mcp_client.call_tool.assert_called_once()


class TestResearchTaskOperations:
    """Test research task operations"""
    
    def test_create_research_task_success(self, test_config, mock_database, mock_mcp_client):
        # Test successful research task creation
        request = ResearchTaskCreateRequest(
            name="Test Task",
            description="Test Description",
            task_type="data_collection"
        )
        
        mock_mcp_client.call_tool.return_value = {"success": True, "task_id": "task-123"}
        
        result = create_research_task("plan-123", request, mock_database, mock_mcp_client)
        
        assert result["success"] is True
        assert result["task_id"] == "task-123"
        mock_mcp_client.call_tool.assert_called_once()
    
    def test_list_research_tasks_empty(self, test_config, mock_database, mock_mcp_client):
        # Test listing research tasks when none exist
        mock_database.query.return_value = []
        
        result = list_research_tasks("plan-123", mock_database, limit=10, offset=0)
        
        assert result == {"tasks": [], "total": 0, "limit": 10, "offset": 0}


class TestQueryOperations:
    """Test query execution operations"""
    
    def test_execute_query_success(self, test_config, mock_database, mock_mcp_client):
        # Test successful query execution
        request = QueryRequest(
            query="SELECT * FROM projects",
            max_results=10
        )
        
        mock_database.query.return_value = [{"id": "1", "name": "Test Project"}]
        
        result = execute_query(request, mock_database)
        
        assert "results" in result
        assert len(result["results"]) == 1
        assert result["results"][0]["name"] == "Test Project"


class TestSearchOperations:
    """Test search operations"""
    
    def test_search_projects_success(self, test_config, mock_database, mock_mcp_client):
        # Test successful project search
        mock_database.query.return_value = [{"id": "1", "name": "Test Project"}]
        
        result = search_projects("test", mock_database, limit=10, offset=0)
        
        assert "projects" in result
        assert result["total"] == 1
        mock_database.query.assert_called_once()
    
    def test_search_research_topics_success(self, test_config, mock_database, mock_mcp_client):
        # Test successful research topic search
        mock_database.query.return_value = [{"id": "1", "name": "Test Topic"}]
        
        result = search_research_topics("test", mock_database, limit=10, offset=0)
        
        assert "topics" in result
        assert result["total"] == 1
        mock_database.query.assert_called_once()
    
    def test_search_research_plans_success(self, test_config, mock_database, mock_mcp_client):
        # Test successful research plan search
        mock_database.query.return_value = [{"id": "1", "name": "Test Plan"}]
        
        result = search_research_plans("test", mock_database, limit=10, offset=0)
        
        assert "plans" in result
        assert result["total"] == 1
        mock_database.query.assert_called_once()


class TestErrorHandlingComprehensive:
    """Test comprehensive error handling scenarios"""
    
    def test_mcp_client_connection_error(self, test_config, mock_database, mock_mcp_client):
        # Test MCP client connection error
        mock_mcp_client.call_tool.side_effect = Exception("Connection error")
        
        request = ProjectCreateRequest(
            name="Test Project",
            description="Test Description",
            objectives=["Objective 1"]
        )
        
        with pytest.raises(HTTPException) as exc_info:
            create_project(request, mock_database, mock_mcp_client)
        
        assert exc_info.value.status_code == 500
    
    def test_database_connection_error(self, test_config, mock_database, mock_mcp_client):
        # Test database connection error
        mock_database.query.side_effect = Exception("Database error")
        
        with pytest.raises(HTTPException) as exc_info:
            list_projects(mock_database, limit=10, offset=0)
        
        assert exc_info.value.status_code == 500
    
    def test_invalid_project_id_format(self, test_config, mock_database, mock_mcp_client):
        # Test invalid project ID format
        request = ProjectUpdateRequest(
            name="Updated Project",
            description="Updated Description"
        )
        
        # Test with empty string project ID
        with pytest.raises(HTTPException) as exc_info:
            update_project("", request, mock_database, mock_mcp_client)
        
        assert exc_info.value.status_code == 400


class TestValidationAndEdgeCases:
    """Test validation and edge cases"""
    
    def test_pagination_limits(self, test_config, mock_database, mock_mcp_client):
        # Test pagination with maximum limits
        mock_database.query.return_value = []
        
        result = list_projects(mock_database, limit=1000, offset=0)
        
        # Should cap limit at reasonable maximum
        assert result["limit"] <= 100
    
    def test_negative_pagination_values(self, test_config, mock_database, mock_mcp_client):
        # Test negative pagination values
        mock_database.query.return_value = []
        
        result = list_projects(mock_database, limit=-1, offset=-1)
        
        # Should handle negative values gracefully
        assert result["limit"] >= 0
        assert result["offset"] >= 0
    
    def test_empty_search_query(self, test_config, mock_database, mock_mcp_client):
        # Test empty search query
        mock_database.query.return_value = []
        
        result = search_projects("", mock_database, limit=10, offset=0)
        
        assert "projects" in result
        assert result["total"] == 0


class TestDataIntegrity:
    """Test data integrity and consistency"""
    
    def test_project_with_topics_deletion(self, test_config, mock_database, mock_mcp_client):
        # Test deleting project that has associated topics
        mock_mcp_client.call_tool.return_value = {"success": True}
        
        result = delete_project("project-with-topics", mock_database, mock_mcp_client)
        
        assert result["success"] is True
        mock_mcp_client.call_tool.assert_called_once()
    
    def test_topic_with_plans_deletion(self, test_config, mock_database, mock_mcp_client):
        # Test deleting topic that has associated plans
        mock_mcp_client.call_tool.return_value = {"success": True}
        
        result = delete_research_topic("topic-with-plans", mock_database, mock_mcp_client)
        
        assert result["success"] is True
        mock_mcp_client.call_tool.assert_called_once()
