"""
Simplified unit tests for API Gateway v2 hierarchical endpoints.

Tests for the CRUD operations on projects, topics, and plans.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

# Import the functions we want to test directly
from v2_hierarchical_api import create_project, list_projects
from src.data_models.hierarchical_data_models import ProjectRequest


class TestProjectEndpointsUnit:
    """Unit tests for project endpoint functions."""
    
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
        # Mock database
        mock_db = AsyncMock()
        mock_db.get_projects = AsyncMock(return_value=[
            {
                "id": "test-project-123",
                "name": "Test Project",
                "description": "A test project",
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "metadata": {}
            }
        ])
        mock_db.get_project_stats = AsyncMock(return_value={
            "topics_count": 2,
            "plans_count": 3,
            "tasks_count": 5,
            "total_cost": 150.0,
            "completion_rate": 60.0
        })
        
        # Call the function
        result = await list_projects(db=mock_db)
        
        # Verify result
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].name == "Test Project"
        assert result[0].topics_count == 2
        assert result[0].plans_count == 3
        
        # Verify database was called
        mock_db.get_projects.assert_called_once()
        mock_db.get_project_stats.assert_called_once()


class TestEndpointValidation:
    """Test input validation for endpoints."""
    
    def test_project_request_validation(self):
        """Test ProjectRequest validation."""
        # Valid request
        valid_request = ProjectRequest(
            name="Valid Project",
            description="A valid project description"
        )
        assert valid_request.name == "Valid Project"
        
        # Test with metadata
        request_with_metadata = ProjectRequest(
            name="Project with metadata",
            description="Description",
            metadata={"key": "value"}
        )
        assert request_with_metadata.metadata == {"key": "value"}
        
    def test_project_request_invalid_name(self):
        """Test ProjectRequest with invalid name."""
        with pytest.raises(ValueError):
            ProjectRequest(
                name="",  # Empty name should be invalid
                description="Valid description"
            )


class TestMCPIntegration:
    """Test MCP client integration."""
    
    @pytest.mark.asyncio
    async def test_mcp_client_disconnected(self):
        """Test behavior when MCP client is disconnected."""
        # Mock dependencies
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = False  # Disconnected
        
        # Create test request
        project_request = ProjectRequest(
            name="Test Project",
            description="A test project"
        )
        
        # Call the function
        result = await create_project(project_request, mock_db, mock_mcp_client)
        
        # Should still work but MCP client shouldn't be called
        assert result.name == "Test Project"
        mock_mcp_client.send_research_action.assert_not_called()
        
    @pytest.mark.asyncio
    async def test_mcp_client_none(self):
        """Test behavior when MCP client is None."""
        # Mock dependencies
        mock_db = AsyncMock()
        mock_mcp_client = None
        
        # Create test request
        project_request = ProjectRequest(
            name="Test Project",
            description="A test project"
        )
        
        # Call the function
        result = await create_project(project_request, mock_db, mock_mcp_client)
        
        # Should still work
        assert result.name == "Test Project"


class TestErrorHandling:
    """Test error handling in endpoints."""
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self):
        """Test handling of database errors."""
        # Mock database to raise exception
        mock_db = AsyncMock()
        mock_db.get_projects = AsyncMock(side_effect=Exception("Database error"))
        
        # Call the function and expect it to handle the error gracefully
        with pytest.raises(Exception):
            await list_projects(db=mock_db)
            
    @pytest.mark.asyncio
    async def test_mcp_client_error_handling(self):
        """Test handling of MCP client errors."""
        # Mock dependencies
        mock_db = AsyncMock()
        mock_mcp_client = AsyncMock()
        mock_mcp_client.is_connected = True
        mock_mcp_client.send_research_action = AsyncMock(side_effect=Exception("MCP error"))
        
        # Create test request
        project_request = ProjectRequest(
            name="Test Project",
            description="A test project"
        )
        
        # Should raise HTTPException when MCP fails
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await create_project(project_request, mock_db, mock_mcp_client)
        
        assert exc_info.value.status_code == 500


if __name__ == "__main__":
    # Run tests with: python -m pytest tests/test_v2_api_simple.py -v
    pass
