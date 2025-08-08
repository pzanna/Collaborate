"""
Data models and schemas for the SERVICE_NAME_PLACEHOLDER service.

This module defines the standard data models used across the service,
including request/response schemas, database models, and internal data structures.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


# Standard service information models
class ServiceInfo(BaseModel):
    """Service information model."""
    name: str
    version: str
    description: str
    status: str = "running"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthStatus(BaseModel):
    """Health check status model."""
    status: str = Field(..., description="Overall health status: healthy, degraded, unhealthy")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    checks: Dict[str, Any] = Field(default_factory=dict, description="Individual health check results")
    metrics: Dict[str, Union[int, float, str]] = Field(default_factory=dict, description="Service metrics")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = Field(None, description="Request ID for tracking")


class SuccessResponse(BaseModel):
    """Standard success response model."""
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# MCP-related models
class MCPMessage(BaseModel):
    """MCP message model."""
    id: str = Field(..., description="Message ID")
    method: str = Field(..., description="MCP method")
    params: Dict[str, Any] = Field(default_factory=dict, description="Method parameters")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MCPResponse(BaseModel):
    """MCP response model."""
    id: str = Field(..., description="Message ID")
    result: Optional[Dict[str, Any]] = Field(None, description="Response result")
    error: Optional[Dict[str, Any]] = Field(None, description="Error information")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TaskRequest(BaseModel):
    """Generic task request model."""
    task_id: str = Field(..., description="Unique task identifier")
    task_type: str = Field(..., description="Type of task to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    priority: int = Field(default=5, description="Task priority (1-10, 10 is highest)")
    timeout: Optional[int] = Field(None, description="Task timeout in seconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class TaskResponse(BaseModel):
    """Generic task response model."""
    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Task status: pending, running, completed, failed")
    result: Optional[Dict[str, Any]] = Field(None, description="Task result")
    error: Optional[str] = Field(None, description="Error message if failed")
    started_at: Optional[datetime] = Field(None, description="Task start time")
    completed_at: Optional[datetime] = Field(None, description="Task completion time")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")


# Configuration models
class ServiceConfigModel(BaseModel):
    """Service configuration model for API responses."""
    name: str
    version: str
    host: str
    port: int
    debug: bool
    capabilities: List[str]


class MetricsModel(BaseModel):
    """Service metrics model."""
    uptime: float = Field(..., description="Service uptime in seconds")
    requests_total: int = Field(default=0, description="Total number of requests")
    requests_per_second: float = Field(default=0.0, description="Current requests per second")
    active_connections: int = Field(default=0, description="Active connections count")
    memory_usage: Dict[str, Union[int, float]] = Field(default_factory=dict, description="Memory usage statistics")
    cpu_usage: float = Field(default=0.0, description="CPU usage percentage")
    custom_metrics: Dict[str, Union[int, float, str]] = Field(default_factory=dict, description="Service-specific metrics")


# Database models (if applicable)
class BaseEntity(BaseModel):
    """Base entity model with common fields."""
    id: Optional[str] = Field(None, description="Entity ID")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    version: int = Field(default=1, description="Entity version for optimistic locking")


# Service-specific models
# Add your service-specific models here
class ServiceSpecificModel(BaseModel):
    """Example service-specific model - replace with actual models."""
    name: str = Field(..., description="Model name")
    data: Dict[str, Any] = Field(default_factory=dict, description="Model data")
    tags: List[str] = Field(default_factory=list, description="Model tags")


# Validation models
class ValidationResult(BaseModel):
    """Validation result model."""
    is_valid: bool = Field(..., description="Whether validation passed")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")


# Pagination models
class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    page_size: int = Field(default=20, ge=1, le=100, description="Number of items per page")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: str = Field(default="asc", regex="^(asc|desc)$", description="Sort order")


class PaginatedResponse(BaseModel):
    """Paginated response model."""
    items: List[Any] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")


# Export all models
__all__ = [
    "ServiceInfo",
    "HealthStatus",
    "ErrorResponse",
    "SuccessResponse",
    "MCPMessage",
    "MCPResponse",
    "TaskRequest",
    "TaskResponse",
    "ServiceConfigModel",
    "MetricsModel",
    "BaseEntity",
    "ServiceSpecificModel",
    "ValidationResult",
    "PaginationParams",
    "PaginatedResponse"
]
