"""Enhanced data models for hierarchical research structure - V2 API."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, validator

# Status type definitions for consistency
ProjectStatus = Literal["active", "archived"]
TopicStatus = Literal["active", "paused", "completed", "archived"]
PlanStatus = Literal["draft", "active", "completed", "cancelled"]
TaskStatus = Literal["pending", "running", "completed", "failed", "cancelled"]
TaskStage = Literal["planning", "literature_review", "reasoning", "execution", "synthesis", "complete", "failed"]
TaskType = Literal["research", "analysis", "synthesis", "validation"]
PlanType = Literal["comprehensive", "quick", "deep", "custom"]


def generate_uuid() -> str:
    """Generate a unique ID."""
    return str(uuid4())


class Project(BaseModel):
    """Project model for organizing research initiatives."""

    id: str = Field(default_factory=generate_uuid)
    name: str
    description: str = ""
    status: ProjectStatus = "active"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator("name")
    def name_must_not_be_empty(cls, v):
        """TODO: Add docstring for name_must_not_be_empty."""
        if not v.strip():
            raise ValueError("Project name cannot be empty")
        return v.strip()

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now()


class ResearchTopic(BaseModel):
    """Research topic model for specific areas of investigation within a project."""

    id: str = Field(default_factory=generate_uuid)
    project_id: str
    name: str
    description: str = ""
    status: TopicStatus = "active"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator("name")
    def name_must_not_be_empty(cls, v):
        """TODO: Add docstring for name_must_not_be_empty."""
        if not v.strip():
            raise ValueError("Topic name cannot be empty")
        return v.strip()

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now()

    def update_status(self, new_status: TopicStatus) -> None:
        """Update topic status."""
        self.status = new_status
        self.update_timestamp()


class ResearchPlan(BaseModel):
    """Research plan model for structured approaches to investigate a topic."""

    id: str = Field(default_factory=generate_uuid)
    topic_id: str
    name: str
    description: str = ""
    plan_type: PlanType = "comprehensive"
    status: PlanStatus = "draft"
    plan_approved: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    estimated_cost: float = 0.0
    actual_cost: float = 0.0
    plan_structure: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator("name")
    def name_must_not_be_empty(cls, v):
        """TODO: Add docstring for name_must_not_be_empty."""
        if not v.strip():
            raise ValueError("Plan name cannot be empty")
        return v.strip()

    @validator("estimated_cost", "actual_cost")
    def cost_must_be_non_negative(cls, v):
        """TODO: Add docstring for cost_must_be_non_negative."""
        if v < 0:
            raise ValueError("Cost cannot be negative")
        return v

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now()

    def update_status(self, new_status: PlanStatus) -> None:
        """Update plan status."""
        self.status = new_status
        self.update_timestamp()

    def update_cost(self, cost: float, is_actual: bool = False) -> None:
        """Update cost information."""
        if cost < 0:
            raise ValueError("Cost cannot be negative")
        if is_actual:
            self.actual_cost = cost
        else:
            self.estimated_cost = cost
        self.update_timestamp()


class Task(BaseModel):
    """Task model for individual work units within a research plan."""

    id: str = Field(default_factory=generate_uuid)
    plan_id: str
    name: str
    description: str = ""
    task_type: TaskType = "research"
    task_order: int = 0
    status: TaskStatus = "pending"
    stage: TaskStage = "planning"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    estimated_cost: float = 0.0
    actual_cost: float = 0.0
    cost_approved: bool = False
    single_agent_mode: bool = False
    max_results: int = 10
    progress: float = 0.0

    # Task execution data
    query: Optional[str] = None
    search_results: List[Dict[str, Any]] = Field(default_factory=list)
    reasoning_output: Optional[str] = None
    execution_results: List[Dict[str, Any]] = Field(default_factory=list)
    synthesis: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator("name")
    def name_must_not_be_empty(cls, v):
        """TODO: Add docstring for name_must_not_be_empty."""
        if not v.strip():
            raise ValueError("Task name cannot be empty")
        return v.strip()

    @validator("estimated_cost", "actual_cost")
    def cost_must_be_non_negative(cls, v):
        """TODO: Add docstring for cost_must_be_non_negative."""
        if v < 0:
            raise ValueError("Cost cannot be negative")
        return v

    @validator("progress")
    def progress_must_be_valid(cls, v):
        """TODO: Add docstring for progress_must_be_valid."""
        if not 0 <= v <= 100:
            raise ValueError("Progress must be between 0 and 100")
        return v

    @validator("max_results")
    def max_results_must_be_positive(cls, v):
        """TODO: Add docstring for max_results_must_be_positive."""
        if v <= 0:
            raise ValueError("Max results must be positive")
        return v

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now()

    def update_progress(self, new_progress: float) -> None:
        """Update task progress."""
        if not 0 <= new_progress <= 100:
            raise ValueError("Progress must be between 0 and 100")
        self.progress = new_progress
        self.update_timestamp()

    def update_status(self, new_status: TaskStatus, new_stage: Optional[TaskStage] = None) -> None:
        """Update task status and optionally stage."""
        self.status = new_status
        if new_stage:
            self.stage = new_stage
        self.update_timestamp()


# Request models for API
class ProjectRequest(BaseModel):
    """Request model for creating projects."""

    name: str
    description: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator("name")
    def name_must_not_be_empty(cls, v):
        """TODO: Add docstring for name_must_not_be_empty."""
        if not v.strip():
            raise ValueError("Project name cannot be empty")
        return v.strip()


class ResearchTopicRequest(BaseModel):
    """Request model for creating research topics."""

    name: str
    description: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator("name")
    def name_must_not_be_empty(cls, v):
        """TODO: Add docstring for name_must_not_be_empty."""
        if not v.strip():
            raise ValueError("Topic name cannot be empty")
        return v.strip()


class ResearchPlanRequest(BaseModel):
    """Request model for creating research plans."""

    name: str
    description: str = ""
    plan_type: PlanType = "comprehensive"
    plan_structure: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator("name")
    def name_must_not_be_empty(cls, v):
        """TODO: Add docstring for name_must_not_be_empty."""
        if not v.strip():
            raise ValueError("Plan name cannot be empty")
        return v.strip()


class TaskRequest(BaseModel):
    """Request model for creating tasks."""

    name: str
    description: str = ""
    task_type: TaskType = "research"
    task_order: int = 0
    query: Optional[str] = None
    max_results: int = 10
    single_agent_mode: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator("name")
    def name_must_not_be_empty(cls, v):
        """TODO: Add docstring for name_must_not_be_empty."""
        if not v.strip():
            raise ValueError("Task name cannot be empty")
        return v.strip()

    @validator("max_results")
    def max_results_must_be_positive(cls, v):
        """TODO: Add docstring for max_results_must_be_positive."""
        if v <= 0:
            raise ValueError("Max results must be positive")
        return v


# Update request models (all fields optional for PATCH operations)
class ProjectUpdate(BaseModel):
    """Request model for updating projects."""

    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    metadata: Optional[Dict[str, Any]] = None

    @validator("name")
    def name_must_not_be_empty(cls, v):
        """TODO: Add docstring for name_must_not_be_empty."""
        if v is not None and not v.strip():
            raise ValueError("Project name cannot be empty")
        return v.strip() if v else v


class ResearchTopicUpdate(BaseModel):
    """Request model for updating research topics."""

    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TopicStatus] = None
    metadata: Optional[Dict[str, Any]] = None

    @validator("name")
    def name_must_not_be_empty(cls, v):
        """TODO: Add docstring for name_must_not_be_empty."""
        if v is not None and not v.strip():
            raise ValueError("Topic name cannot be empty")
        return v.strip() if v else v


class ResearchPlanUpdate(BaseModel):
    """Request model for updating research plans."""

    name: Optional[str] = None
    description: Optional[str] = None
    plan_type: Optional[PlanType] = None
    status: Optional[PlanStatus] = None
    plan_structure: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    @validator("name")
    def name_must_not_be_empty(cls, v):
        """TODO: Add docstring for name_must_not_be_empty."""
        if v is not None and not v.strip():
            raise ValueError("Plan name cannot be empty")
        return v.strip() if v else v


class TaskUpdate(BaseModel):
    """Request model for updating tasks."""

    name: Optional[str] = None
    description: Optional[str] = None
    task_type: Optional[TaskType] = None
    task_order: Optional[int] = None
    status: Optional[TaskStatus] = None
    stage: Optional[TaskStage] = None
    query: Optional[str] = None
    max_results: Optional[int] = None
    single_agent_mode: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None

    @validator("name")
    def name_must_not_be_empty(cls, v):
        """TODO: Add docstring for name_must_not_be_empty."""
        if v is not None and not v.strip():
            raise ValueError("Task name cannot be empty")
        return v.strip() if v else v

    @validator("max_results")
    def max_results_must_be_positive(cls, v):
        """TODO: Add docstring for max_results_must_be_positive."""
        if v is not None and v <= 0:
            raise ValueError("Max results must be positive")
        return v


# Response models for API with computed fields
class ProjectResponse(BaseModel):
    """Response model for projects."""

    id: str
    name: str
    description: str
    status: ProjectStatus
    created_at: str
    updated_at: str
    topics_count: int = 0
    plans_count: int = 0
    tasks_count: int = 0
    total_cost: float = 0.0
    completion_rate: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ResearchTopicResponse(BaseModel):
    """Response model for research topics."""

    id: str
    project_id: str
    name: str
    description: str
    status: TopicStatus
    created_at: str
    updated_at: str
    plans_count: int = 0
    tasks_count: int = 0
    total_cost: float = 0.0
    completion_rate: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ResearchPlanResponse(BaseModel):
    """Response model for research plans."""

    id: str
    topic_id: str
    name: str
    description: str
    plan_type: PlanType
    status: PlanStatus
    plan_approved: bool
    created_at: str
    updated_at: str
    estimated_cost: float
    actual_cost: float
    tasks_count: int = 0
    completed_tasks: int = 0
    progress: float = 0.0
    plan_structure: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskResponse(BaseModel):
    """Response model for tasks."""

    id: str
    plan_id: str
    name: str
    description: str
    task_type: TaskType
    task_order: int
    status: TaskStatus
    stage: TaskStage
    created_at: str
    updated_at: str
    estimated_cost: float
    actual_cost: float
    cost_approved: bool
    single_agent_mode: bool
    max_results: int
    progress: float
    query: Optional[str] = None
    search_results: List[Dict[str, Any]] = Field(default_factory=list)
    reasoning_output: Optional[str] = None
    execution_results: List[Dict[str, Any]] = Field(default_factory=list)
    synthesis: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Hierarchical navigation models
class ProjectHierarchy(BaseModel):
    """Complete project hierarchy with all topics, plans, and tasks."""

    project: ProjectResponse
    topics: List[ResearchTopicResponse] = Field(default_factory=list)
    plans: List[ResearchPlanResponse] = Field(default_factory=list)
    tasks: List[TaskResponse] = Field(default_factory=list)


# Bulk operation models
class BulkTaskRequest(BaseModel):
    """Request model for bulk task operations."""

    tasks: List[TaskRequest]


class BulkTaskStatusUpdate(BaseModel):
    """Request model for bulk task status updates."""

    task_ids: List[str]
    status: TaskStatus


# Statistics models
class ProjectStats(BaseModel):
    """Project statistics."""

    topics_count: int
    plans_count: int
    tasks_count: int
    total_cost: float
    completion_rate: float


class TopicStats(BaseModel):
    """Topic statistics."""

    plans_count: int
    tasks_count: int
    total_cost: float
    completion_rate: float


class PlanStats(BaseModel):
    """Plan statistics."""

    tasks_count: int
    completed_tasks: int
    total_cost: float
    progress: float


# Error response model
class ErrorResponse(BaseModel):
    """Standard error response model."""

    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# Success response model
class SuccessResponse(BaseModel):
    """Standard success response model."""

    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
