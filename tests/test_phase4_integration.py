#!/usr/bin/env python3
"""
Test script for Phase 4 FastAPI integration
Tests the new research endpoints and WebSocket functionality
"""

import asyncio
import json
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import the FastAPI app
from web_server import app

# Test client
client = TestClient(app)


class TestPhase4Integration:
    """Test Phase 4 FastAPI integration with Research Manager"""

    def test_health_endpoint_includes_research_system(self):
        """Test that health endpoint includes research system status"""
        response = client.get("/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "research_system" in data
        assert "status" in data["research_system"]
        assert "mcp_connected" in data["research_system"]

    def test_research_endpoints_available(self):
        """Test that research endpoints are available"""
        # Test research start endpoint (should return 503 when research system is not available)
        response = client.post("/api/research/start", json={
            "conversation_id": "test-conv-123",
            "query": "test query",
            "research_mode": "comprehensive"
        })
        # Should return 503 when research system is not available
        assert response.status_code == 503
        assert "Research system not available" in response.json()["detail"]
        
        # Test research task status endpoint
        response = client.get("/api/research/task/test-task-123")
        assert response.status_code == 503
        assert "Research system not available" in response.json()["detail"]
        
        # Test research cancel endpoint
        response = client.delete("/api/research/task/test-task-123")
        assert response.status_code == 503
        assert "Research system not available" in response.json()["detail"]

    def test_original_endpoints_still_work(self):
        """Test that original endpoints still function"""
        # Test projects endpoint
        response = client.get("/api/projects")
        assert response.status_code == 200
        
        # Test conversations endpoint
        response = client.get("/api/conversations")
        assert response.status_code == 200

    @patch('web_server.research_manager')
    @patch('web_server.mcp_client')
    def test_research_endpoints_with_mocked_system(self, mock_mcp_client, mock_research_manager):
        """Test research endpoints with mocked research system"""
        # Mock the research manager
        mock_research_manager.start_research_task = AsyncMock(return_value="test-task-123")
        mock_research_manager.get_task_context = Mock()
        mock_research_manager.get_task_context.return_value = Mock(
            task_id="test-task-123",
            conversation_id="test-conv-123",
            query="test query",
            stage=Mock(value="planning"),
            created_at=Mock(isoformat=Mock(return_value="2025-01-01T00:00:00")),
            updated_at=Mock(isoformat=Mock(return_value="2025-01-01T00:00:00"))
        )
        mock_research_manager.calculate_task_progress = Mock(return_value=0.2)
        
        # Mock MCP client
        mock_mcp_client.is_connected = True
        
        # Test research start endpoint
        response = client.post("/api/research/start", json={
            "conversation_id": "test-conv-123",
            "query": "test query",
            "research_mode": "comprehensive"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data["task_id"] == "test-task-123"
        assert data["conversation_id"] == "test-conv-123"
        assert data["query"] == "test query"

    def test_websocket_endpoints_exist(self):
        """Test that WebSocket endpoints are defined"""
        # The actual WebSocket testing would require more complex setup
        # This is just a basic check that the endpoints exist
        
        # Check that the routes are registered
        routes = [getattr(route, 'path', str(route)) for route in app.routes]
        # Check if any route contains the WebSocket paths
        has_chat_ws = any("/api/chat/stream/" in str(route) for route in routes)
        has_research_ws = any("/api/research/stream/" in str(route) for route in routes)
        
        assert has_chat_ws or has_research_ws  # At least one should exist

    def test_pydantic_models(self):
        """Test that new Pydantic models are properly defined"""
        from web_server import ResearchRequest, ResearchTaskResponse
        
        # Test ResearchRequest model
        request = ResearchRequest(
            conversation_id="test-conv-123",
            query="test query",
            research_mode="comprehensive",
            max_results=10
        )
        assert request.conversation_id == "test-conv-123"
        assert request.query == "test query"
        assert request.research_mode == "comprehensive"
        assert request.max_results == 10
        
        # Test ResearchTaskResponse model
        response = ResearchTaskResponse(
            task_id="test-task-123",
            conversation_id="test-conv-123",
            query="test query",
            status="planning",
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
            progress=0.2
        )
        assert response.task_id == "test-task-123"
        assert response.status == "planning"
        assert response.progress == 0.2

    def test_connection_manager_research_methods(self):
        """Test that ConnectionManager has research-related methods"""
        from web_server import ConnectionManager
        
        manager = ConnectionManager()
        
        # Check that research methods exist
        assert hasattr(manager, 'research_connections')
        assert hasattr(manager, 'connect_research')
        assert hasattr(manager, 'disconnect_research')
        assert hasattr(manager, 'send_to_research')
        
        # Check that research_connections is initialized
        assert isinstance(manager.research_connections, dict)

    def test_cors_middleware_configured(self):
        """Test that CORS middleware is properly configured"""
        # Test preflight request
        response = client.options("/api/health")
        # Should not fail with CORS errors
        assert response.status_code in [200, 405]  # 405 is OK for OPTIONS not implemented


def test_integration_smoke_test():
    """Smoke test to ensure basic integration works"""
    # Test that the app can be imported and basic endpoints work
    response = client.get("/api/health")
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "ai_providers" in data
    assert "research_system" in data
    assert "errors" in data
    
    print("✅ Phase 4 integration smoke test passed")


if __name__ == "__main__":
    # Run basic smoke test
    test_integration_smoke_test()
    
    # Run all tests if pytest is available
    try:
        pytest.main([__file__, "-v"])
    except ImportError:
        print("⚠️  pytest not available, run: pip install pytest")
        print("✅ Basic smoke test completed successfully")
