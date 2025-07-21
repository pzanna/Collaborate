"""API endpoints for hierarchical research structure."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from src.models.hierarchical_data_models import (
    ResearchTopicRequest,
    ResearchTopicResponse,
    ResearchPlanRequest,
    ResearchPlanResponse,
    TaskRequest,
    TaskResponse
)
from src.storage.hierarchical_database import HierarchicalDatabaseManager

# Create router for hierarchical research endpoints
hierarchical_router = APIRouter(prefix="/api/v2", tags=["hierarchical-research"])

# Global database instance
_hierarchical_db: Optional[HierarchicalDatabaseManager] = None


def get_database() -> Optional[HierarchicalDatabaseManager]:
    """Dependency to get database manager."""
    global _hierarchical_db
    if _hierarchical_db is None:
        # Initialize the database only once
        try:
            _hierarchical_db = HierarchicalDatabaseManager()
        except Exception as e:
            # If database initialization fails, return None to disable hierarchical features
            return None
    return _hierarchical_db


def check_database_available(db: Optional[HierarchicalDatabaseManager]) -> HierarchicalDatabaseManager:
    """Check if database is available and raise HTTPException if not."""
    if db is None:
        raise HTTPException(status_code=503, detail="Hierarchical database not available")
    return db


# Research Topics Endpoints
@hierarchical_router.post("/projects/{project_id}/topics", response_model=ResearchTopicResponse)
async def create_research_topic(
    project_id: str,
    topic_request: ResearchTopicRequest,
    db: Optional[HierarchicalDatabaseManager] = Depends(get_database)
):
    """Create a new research topic within a project."""
    db = check_database_available(db)
    
    try:
        # Verify project exists
        project = db.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Validate request
        if topic_request.project_id != project_id:
            topic_request.project_id = project_id
        
        # Create topic data
        topic_data = {
            'project_id': project_id,
            'name': topic_request.name,
            'description': topic_request.description,
            'status': 'active',  # Default status for new topics
            'metadata': topic_request.metadata or {}
        }
        
        # Create topic in database
        topic = db.create_research_topic(topic_data)
        if not topic:
            raise HTTPException(status_code=500, detail="Failed to create research topic")
        
        return ResearchTopicResponse(**topic)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@hierarchical_router.get("/projects/{project_id}/topics", response_model=List[ResearchTopicResponse])
async def list_research_topics(
    project_id: str,
    status: Optional[str] = None,
    db: Optional[HierarchicalDatabaseManager] = Depends(get_database)
):
    """List all research topics for a project."""
    db = check_database_available(db)
    
    try:
        # Verify project exists
        project = db.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get topics from database
        topics = db.get_research_topics_by_project(project_id, status_filter=status)
        
        return [ResearchTopicResponse(**topic) for topic in topics]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@hierarchical_router.get("/topics/{topic_id}", response_model=ResearchTopicResponse)
async def get_research_topic(
    topic_id: str,
    db: Optional[HierarchicalDatabaseManager] = Depends(get_database)
):
    """Get a specific research topic."""
    db = check_database_available(db)
    
    try:
        # Get topic from database
        topic = db.get_research_topic(topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Research topic not found")
        
        return ResearchTopicResponse(**topic)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@hierarchical_router.put("/topics/{topic_id}", response_model=ResearchTopicResponse)
async def update_research_topic(
    topic_id: str,
    topic_update: ResearchTopicRequest,
    db: Optional[HierarchicalDatabaseManager] = Depends(get_database)
):
    """Update a research topic."""
    try:
        # Prepare update data
        update_data = {}
        if topic_update.name:
            update_data['name'] = topic_update.name
        if topic_update.description:
            update_data['description'] = topic_update.description
        if topic_update.status:
            update_data['status'] = topic_update.status
        if topic_update.metadata:
            update_data['metadata'] = topic_update.metadata
        
        # Update topic in database
        topic = db.update_research_topic(topic_id, update_data)
        if not topic:
            raise HTTPException(status_code=404, detail="Research topic not found")
        
        return ResearchTopicResponse(**topic)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@hierarchical_router.delete("/topics/{topic_id}")
async def delete_research_topic(
    topic_id: str,
    db: Optional[HierarchicalDatabaseManager] = Depends(get_database)
):
    """Delete a research topic and all its plans and tasks."""
    try:
        # Delete topic from database
        success = db.delete_research_topic(topic_id)
        if not success:
            raise HTTPException(status_code=404, detail="Research topic not found")
        
        return {"success": True, "message": "Research topic deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Research Plans Endpoints
@hierarchical_router.post("/topics/{topic_id}/plans", response_model=ResearchPlanResponse)
async def create_research_plan(
    topic_id: str,
    plan_request: ResearchPlanRequest,
    db: Optional[HierarchicalDatabaseManager] = Depends(get_database)
):
    """Create a new research plan within a topic."""
    try:
        # Verify topic exists
        topic = db.get_research_topic(topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Research topic not found")
        
        # Validate request
        if plan_request.topic_id != topic_id:
            plan_request.topic_id = topic_id
        
        # Create plan data
        plan_data = {
            'topic_id': topic_id,
            'name': plan_request.name,
            'description': plan_request.description,
            'plan_type': plan_request.plan_type,
            'status': 'draft',  # Default status for new plans
            'plan_structure': plan_request.plan_structure or {},
            'metadata': plan_request.metadata or {}
        }
        
        # Create plan in database
        plan = db.create_research_plan(plan_data)
        if not plan:
            raise HTTPException(status_code=500, detail="Failed to create research plan")
        
        return ResearchPlanResponse(**plan)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@hierarchical_router.get("/topics/{topic_id}/plans", response_model=List[ResearchPlanResponse])
async def list_research_plans(
    topic_id: str,
    status: Optional[str] = None,
    db: Optional[HierarchicalDatabaseManager] = Depends(get_database)
):
    """List all research plans for a topic."""
    try:
        # Get plans from database
        plans = db.get_research_plans_by_topic(topic_id, status_filter=status)
        
        return [ResearchPlanResponse(**plan) for plan in plans]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@hierarchical_router.get("/plans/{plan_id}", response_model=ResearchPlanResponse)
async def get_research_plan(
    plan_id: str,
    db: Optional[HierarchicalDatabaseManager] = Depends(get_database)
):
    """Get a specific research plan."""
    try:
        # Get plan from database
        plan = db.get_research_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Research plan not found")
        
        return ResearchPlanResponse(**plan)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@hierarchical_router.put("/plans/{plan_id}", response_model=ResearchPlanResponse)
async def update_research_plan(
    plan_id: str,
    plan_update: ResearchPlanRequest,
    db: Optional[HierarchicalDatabaseManager] = Depends(get_database)
):
    """Update a research plan."""
    try:
        # Prepare update data
        update_data = {}
        if plan_update.name:
            update_data['name'] = plan_update.name
        if plan_update.description:
            update_data['description'] = plan_update.description
        if plan_update.plan_type:
            update_data['plan_type'] = plan_update.plan_type
        if plan_update.status:
            update_data['status'] = plan_update.status
        if plan_update.plan_structure:
            update_data['plan_structure'] = plan_update.plan_structure
        if plan_update.metadata:
            update_data['metadata'] = plan_update.metadata
        
        # Update plan in database
        plan = db.update_research_plan(plan_id, update_data)
        if not plan:
            raise HTTPException(status_code=404, detail="Research plan not found")
        
        return ResearchPlanResponse(**plan)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@hierarchical_router.delete("/plans/{plan_id}")
async def delete_research_plan(
    plan_id: str,
    db: Optional[HierarchicalDatabaseManager] = Depends(get_database)
):
    """Delete a research plan and all its tasks."""
    try:
        # Delete plan from database
        success = db.delete_research_plan(plan_id)
        if not success:
            raise HTTPException(status_code=404, detail="Research plan not found")
        
        return {"success": True, "message": "Research plan deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Tasks Endpoints
@hierarchical_router.post("/plans/{plan_id}/tasks", response_model=TaskResponse)
async def create_task(
    plan_id: str,
    task_request: TaskRequest,
    db: Optional[HierarchicalDatabaseManager] = Depends(get_database)
):
    """Create a new task within a plan."""
    try:
        # Verify plan exists
        plan = db.get_research_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Research plan not found")
        
        # Validate request
        if task_request.plan_id != plan_id:
            task_request.plan_id = plan_id
        
        # Create task data
        task_data = {
            'plan_id': plan_id,
            'name': task_request.name,
            'description': task_request.description,
            'task_type': task_request.task_type,
            'task_order': task_request.task_order or 1,
            'status': 'pending',  # Default status for new tasks
            'stage': 'planning',  # Default stage for new tasks
            'single_agent_mode': getattr(task_request, 'single_agent_mode', False),
            'max_results': getattr(task_request, 'max_results', 10),
            'query': getattr(task_request, 'query', None),
            'metadata': getattr(task_request, 'metadata', {})
        }
        
        # Create task in database
        task = db.create_task(task_data)
        if not task:
            raise HTTPException(status_code=500, detail="Failed to create task")
        
        return TaskResponse(**task)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@hierarchical_router.get("/plans/{plan_id}/tasks", response_model=List[TaskResponse])
async def list_tasks(
    plan_id: str,
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    db: Optional[HierarchicalDatabaseManager] = Depends(get_database)
):
    """List all tasks for a plan."""
    try:
        # Get tasks from database
        tasks = db.get_tasks_by_plan(plan_id, status_filter=status, type_filter=task_type)
        
        return [TaskResponse(**task) for task in tasks]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@hierarchical_router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    db: Optional[HierarchicalDatabaseManager] = Depends(get_database)
):
    """Get a specific task."""
    try:
        # Get task from database
        task = db.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return TaskResponse(**task)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@hierarchical_router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_update: TaskRequest,
    db: Optional[HierarchicalDatabaseManager] = Depends(get_database)
):
    """Update a task."""
    try:
        # Prepare update data
        update_data = {}
        if task_update.name:
            update_data['name'] = task_update.name
        if task_update.description:
            update_data['description'] = task_update.description
        if task_update.task_type:
            update_data['task_type'] = task_update.task_type
        if task_update.task_order:
            update_data['task_order'] = task_update.task_order
        if task_update.status:
            update_data['status'] = task_update.status
        if task_update.stage:
            update_data['stage'] = task_update.stage
        if task_update.single_agent_mode is not None:
            update_data['single_agent_mode'] = task_update.single_agent_mode
        if task_update.max_results:
            update_data['max_results'] = task_update.max_results
        if task_update.query:
            update_data['query'] = task_update.query
        if task_update.metadata:
            update_data['metadata'] = task_update.metadata
        
        # Update task in database
        task = db.update_task(task_id, update_data)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return TaskResponse(**task)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@hierarchical_router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    db: Optional[HierarchicalDatabaseManager] = Depends(get_database)
):
    """Delete a task."""
    try:
        # Delete task from database
        success = db.delete_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return {"success": True, "message": "Task deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Hierarchical navigation endpoints
@hierarchical_router.get("/projects/{project_id}/hierarchy")
async def get_project_hierarchy(
    project_id: str,
    db: Optional[HierarchicalDatabaseManager] = Depends(get_database)
):
    """Get complete hierarchy for a project (topics -> plans -> tasks)."""
    try:
        # Get project hierarchy from database
        hierarchy = db.get_project_hierarchy(project_id)
        if not hierarchy:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return hierarchy
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
