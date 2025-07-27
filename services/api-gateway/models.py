"""
API Models for Containerized API Gateway

Data models for request/response handling in the Version 0.3 containerized API Gateway.
These models ensure type safety and proper serialization for REST API operations.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class APIRequest(BaseModel):
    """Base API request model with common fields."""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class APIResponse(BaseModel):
    """Base API response model with common fields."""
    success: bool
    request_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    warnings: Optional[List[str]] = None

    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ResearchRequest(APIRequest):
    """Research task request model."""
    agent_type: str = Field(..., description="Type of agent to handle the request")
    action: str = Field(..., description="Specific action to perform")
    payload: Dict[str, Any] = Field(..., description="Request payload")
    priority: str = Field(default="normal", description="Task priority")
    timeout: Optional[int] = Field(default=300, description="Task timeout in seconds")

    class Config:
        """Pydantic configuration"""
        schema_extra = {
            "example": {
                "agent_type": "literature",
                "action": "search_literature",
                "payload": {
                    "query": "neural networks attention mechanisms",
                    "max_results": 50
                },
                "priority": "normal",
                "timeout": 300
            }
        }


class LiteratureSearchRequest(APIRequest):
    """Literature search request model."""
    query: str = Field(..., description="Search query for literature")
    max_results: int = Field(default=50, ge=1, le=200, description="Maximum number of results")
    include_abstracts: bool = Field(default=True, description="Include paper abstracts")
    date_range: Optional[Dict[str, str]] = Field(default=None, description="Date range filter")
    databases: Optional[List[str]] = Field(default=None, description="Specific databases to search")
    
    class Config:
        """Pydantic configuration"""
        schema_extra = {
            "example": {
                "query": "neural networks attention mechanisms",
                "max_results": 50,
                "include_abstracts": True,
                "date_range": {
                    "start": "2020-01-01",
                    "end": "2024-12-31"
                },
                "databases": ["arxiv", "pubmed", "semantic_scholar"]
            }
        }


class DataAnalysisRequest(APIRequest):
    """Data analysis request model."""
    dataset: str = Field(..., description="Dataset to analyze (JSON string or file path)")
    analysis_type: str = Field(..., description="Type of analysis to perform")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Analysis parameters")
    output_format: str = Field(default="json", description="Output format")
    
    class Config:
        """Pydantic configuration"""
        schema_extra = {
            "example": {
                "dataset": '{"data": [1, 2, 3, 4, 5]}',
                "analysis_type": "descriptive_statistics",
                "parameters": {
                    "include_correlation": True,
                    "confidence_level": 0.95
                },
                "output_format": "json"
            }
        }


class TaskStatusResponse(APIResponse):
    """Task status response model."""
    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Current task status")
    progress: Optional[float] = Field(default=None, ge=0, le=100, description="Progress percentage")
    estimated_completion: Optional[str] = Field(default=None, description="Estimated completion time")
    
    def __init__(self, success: bool, request_id: str, task_id: str, status: str, **kwargs):
        super().__init__(success=success, request_id=request_id, **kwargs)
        self.task_id = task_id
        self.status = status
    
    class Config:
        """Pydantic configuration"""
        schema_extra = {
            "example": {
                "success": True,
                "request_id": "task-123",
                "task_id": "task-123",
                "status": "in_progress",
                "progress": 75.5,
                "estimated_completion": "2024-01-15T14:30:00Z",
                "data": {
                    "intermediate_results": "Processing literature search..."
                }
            }
        }


class AgentStatusResponse(APIResponse):
    """Agent status response model."""
    agents: Dict[str, Dict[str, Any]] = Field(..., description="Status of all agents")
    total_agents: int = Field(..., description="Total number of registered agents")
    active_agents: int = Field(..., description="Number of active agents")
    
    class Config:
        """Pydantic configuration"""
        schema_extra = {
            "example": {
                "success": True,
                "request_id": "status-request-123",
                "agents": {
                    "literature": {
                        "status": "active",
                        "last_seen": "2024-01-15T14:25:00Z",
                        "capabilities": ["search", "retrieve", "summarize"]
                    },
                    "planning": {
                        "status": "active",
                        "last_seen": "2024-01-15T14:24:00Z",
                        "capabilities": ["plan", "coordinate", "optimize"]
                    }
                },
                "total_agents": 8,
                "active_agents": 6
            }
        }


class HealthCheckResponse(BaseModel):
    """Health check response model."""
    service: str = Field(..., description="Service name")
    status: str = Field(..., description="Service health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(..., description="Service version")
    dependencies: Dict[str, str] = Field(..., description="Status of dependencies")
    uptime: Optional[float] = Field(default=None, description="Service uptime in seconds")
    
    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "service": "api-gateway",
                "status": "healthy",
                "timestamp": "2024-01-15T14:25:00Z",
                "version": "3.0.0",
                "dependencies": {
                    "mcp_server": "connected",
                    "database": "healthy",
                    "redis": "connected"
                },
                "uptime": 3600.5
            }
        }


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(default=None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = Field(default=None, description="Request identifier")
    
    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "error": "Task submission failed",
                "error_code": "MCP_CONNECTION_ERROR",
                "details": {
                    "mcp_server_status": "disconnected",
                    "retry_after": 30
                },
                "timestamp": "2024-01-15T14:25:00Z",
                "request_id": "req-123"
            }
        }


# Response Models for specific endpoints
class LiteratureSearchResponse(APIResponse):
    """Literature search response model."""
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Search results")
    total_found: int = Field(default=0, description="Total results found")
    query_processed: str = Field(..., description="Processed search query")
    search_time: Optional[float] = Field(default=None, description="Search execution time")
    

class ResearchTaskResponse(APIResponse):
    """Research task response model."""
    task_id: str = Field(..., description="Task identifier")
    agent_assigned: str = Field(..., description="Agent assigned to task")
    estimated_completion: Optional[str] = Field(default=None, description="Estimated completion time")


class MetricsResponse(BaseModel):
    """Service metrics response model."""
    active_requests: int = Field(..., description="Number of active requests")
    mcp_connected: bool = Field(..., description="MCP server connection status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    uptime: Optional[float] = Field(default=None, description="Service uptime in seconds")
    total_requests: Optional[int] = Field(default=None, description="Total requests handled")
    
    class Config:
        """Pydantic configuration"""
        schema_extra = {
            "example": {
                "active_requests": 5,
                "mcp_connected": True,
                "service": "api-gateway",
                "version": "3.0.0",
                "uptime": 3600.5,
                "total_requests": 1250
            }
        }


# Validation helpers
def validate_agent_type(agent_type: str) -> bool:
    """Validate agent type."""
    valid_agents = [
        "literature", "planning", "executor", "memory", 
        "screening", "synthesis", "writer", "research_manager"
    ]
    return agent_type in valid_agents


def validate_priority(priority: str) -> bool:
    """Validate task priority."""
    valid_priorities = ["low", "normal", "high", "urgent"]
    return priority in valid_priorities


def validate_task_status(status: str) -> bool:
    """Validate task status."""
    valid_statuses = [
        "queued", "in_progress", "completed", "failed", 
        "cancelled", "timeout", "unknown"
    ]
    return status in valid_statuses


# Academic Search Models (from existing codebase)
class AcademicPaper(BaseModel):
    """Academic paper model."""
    title: str = Field(..., description="Paper title")
    url: str = Field(..., description="Paper URL")
    content: str = Field(default="", description="Paper content/abstract")
    source: str = Field(..., description="Source database")
    type: str = Field(default="academic_paper", description="Paper type")
    link_type: str = Field(default="", description="Link type")
    relevance_score: float = Field(default=0.0, description="Relevance score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class AcademicSearchRequest(APIRequest):
    """Academic search request model."""
    query: str = Field(..., description="Search query", min_length=1, max_length=500)
    max_results_per_source: int = Field(default=10, ge=1, le=50, description="Max results per source")
    include_pubmed: bool = Field(default=True, description="Include PubMed search")
    include_arxiv: bool = Field(default=True, description="Include arXiv search")
    include_semantic_scholar: bool = Field(default=True, description="Include Semantic Scholar search")
    use_cache: bool = Field(default=True, description="Use cached results if available")


class AcademicSearchResponse(BaseModel):
    """Response model for academic search results."""
    papers: List[AcademicPaper]
    total_results: int
    query: str
    execution_time: Optional[float] = None
    sources: Optional[List[str]] = None


# Duplicate removed - DataAnalysisRequest already defined above


class DataAnalysisResponse(BaseModel):
    """Response model for data analysis operations."""
    success: bool
    analysis_id: str
    status: str
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# Project Management Models
class ProjectCreateRequest(APIRequest):
    """Request model for creating a new project."""
    name: str = Field(..., description="Project name")
    description: str = Field(..., description="Project description")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional project metadata")


class ProjectResponse(BaseModel):
    """Response model for project operations."""
    id: str
    name: str
    description: str
    status: str
    created_at: str
    updated_at: str
    metadata: Optional[Dict[str, Any]] = None
