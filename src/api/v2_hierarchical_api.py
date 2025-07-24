"""V2 API endpoints for hierarchical research structure-Clean Implementation."""

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from src.core.research_manager import ResearchManager
from src.models.hierarchical_data_models import (  # Request models; Update models; Response models; Utility models
    PlanStats, ProjectHierarchy, ProjectRequest, ProjectResponse, ProjectStats,
    ProjectUpdate, ResearchPlanRequest, ResearchPlanResponse,
    ResearchPlanUpdate, ResearchTopicRequest, ResearchTopicResponse,
    ResearchTopicUpdate, SuccessResponse, TaskRequest, TaskResponse,
    TaskUpdate, TopicStats)
from src.storage.hierarchical_database import HierarchicalDatabaseManager

# Create router for V2 hierarchical research endpoints
v2_router = APIRouter(tags=["v2-hierarchical"])

# Global instances
_hierarchical_db: Optional[HierarchicalDatabaseManager] = None
_research_manager: Optional[ResearchManager] = None


def set_database_manager(db_manager: HierarchicalDatabaseManager):
    """Set the database manager instance for the V2 API."""
    global _hierarchical_db
    _hierarchical_db = db_manager


def set_research_manager(research_manager: ResearchManager):
    """Set the research manager instance for the V2 API."""
    global _research_manager
    _research_manager = research_manager


def get_database() -> HierarchicalDatabaseManager:
    """Dependency to get database manager."""
    global _hierarchical_db
    if _hierarchical_db is None:
        try:
            # Fall back to creating a new instance if not set
            _hierarchical_db = HierarchicalDatabaseManager()
        except Exception as e:
            raise HTTPException(
                status_code=503, detail=f"Database initialization failed: {str(e)}"
            )
    return _hierarchical_db


def get_research_manager() -> Optional[ResearchManager]:
    """Dependency to get research manager."""
    return _research_manager


# =============================================================================
# PROJECT ENDPOINTS
# =============================================================================


@v2_router.post("/projects", response_model=ProjectResponse)
async def create_project(
    project_request: ProjectRequest,
    db: HierarchicalDatabaseManager = Depends(get_database),
):
    """Create a new project."""
    try:
        import json
        from datetime import datetime
        from uuid import uuid4

        # Generate ID and timestamps
        project_id = str(uuid4())
        now = datetime.utcnow()

        project_data = {
            "id": project_id,
            "name": project_request.name,
            "description": project_request.description,
            "status": "active",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "metadata": json.dumps(project_request.metadata or {}),
        }

        project = db.create_project(project_data)
        if not project:
            raise HTTPException(status_code=500, detail="Failed to create project")

        return ProjectResponse(**project)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(
    status: Optional[str] = Query(None, description="Filter by project status"),
    limit: Optional[int] = Query(None, description="Limit number of results"),
    db: HierarchicalDatabaseManager = Depends(get_database),
):
    """List all projects."""
    try:
        projects = db.get_projects(status_filter=status, limit=limit)
        return [ProjectResponse(**project) for project in projects]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str = Path(..., description="Project ID"),
    db: HierarchicalDatabaseManager = Depends(get_database),
):
    """Get a specific project."""
    try:
        project = db.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        return ProjectResponse(**project)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_update: ProjectUpdate,
    project_id: str = Path(..., description="Project ID"),
    db: HierarchicalDatabaseManager = Depends(get_database),
):
    """Update a project."""
    try:
        # Build update data from non-None fields
        update_data = {}
        if project_update.name is not None:
            update_data["name"] = project_update.name
        if project_update.description is not None:
            update_data["description"] = project_update.description
        if project_update.status is not None:
            update_data["status"] = project_update.status
        if project_update.metadata is not None:
            update_data["metadata"] = project_update.metadata

        project = db.update_project(project_id, update_data)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        return ProjectResponse(**project)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.delete("/projects/{project_id}", response_model=SuccessResponse)
async def delete_project(
    project_id: str = Path(..., description="Project ID"),
    db: HierarchicalDatabaseManager = Depends(get_database),
):
    """Delete a project and all its related data."""
    try:
        success = db.delete_project(project_id)
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")

        return SuccessResponse(message="Project deleted successfully")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# RESEARCH TOPIC ENDPOINTS
# =============================================================================


@v2_router.post("/projects/{project_id}/topics", response_model=ResearchTopicResponse)
async def create_research_topic(
    topic_request: ResearchTopicRequest,
    project_id: str = Path(..., description="Project ID"),
    db: HierarchicalDatabaseManager = Depends(get_database),
):
    """Create a new research topic within a project."""
    try:
        import json
        from datetime import datetime
        from uuid import uuid4

        # Verify project exists
        project = db.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Generate ID and timestamps
        topic_id = str(uuid4())
        now = datetime.utcnow()

        topic_data = {
            "id": topic_id,
            "project_id": project_id,
            "name": topic_request.name,
            "description": topic_request.description,
            "status": "active",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "metadata": json.dumps(topic_request.metadata or {}),
        }

        topic = db.create_research_topic(topic_data)
        if not topic:
            raise HTTPException(
                status_code=500, detail="Failed to create research topic"
            )

        return ResearchTopicResponse(**topic)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.get(
    "/projects/{project_id}/topics", response_model=List[ResearchTopicResponse]
)
async def list_research_topics(
    project_id: str = Path(..., description="Project ID"),
    status: Optional[str] = Query(None, description="Filter by topic status"),
    db: HierarchicalDatabaseManager = Depends(get_database),
):
    """List all research topics for a project."""
    try:
        # Verify project exists
        project = db.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        topics = db.get_research_topics_by_project(project_id, status_filter=status)
        return [ResearchTopicResponse(**topic) for topic in topics]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.get("/topics/{topic_id}", response_model=ResearchTopicResponse)
async def get_research_topic(
    topic_id: str = Path(..., description="Topic ID"),
    db: HierarchicalDatabaseManager = Depends(get_database),
):
    """Get a specific research topic."""
    try:
        topic = db.get_research_topic(topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Research topic not found")

        return ResearchTopicResponse(**topic)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.put("/topics/{topic_id}", response_model=ResearchTopicResponse)
async def update_research_topic(
    topic_update: ResearchTopicUpdate,
    topic_id: str = Path(..., description="Topic ID"),
    db: HierarchicalDatabaseManager = Depends(get_database),
):
    """Update a research topic."""
    try:
        # Build update data from non-None fields
        update_data = {}
        if topic_update.name is not None:
            update_data["name"] = topic_update.name
        if topic_update.description is not None:
            update_data["description"] = topic_update.description
        if topic_update.status is not None:
            update_data["status"] = topic_update.status
        if topic_update.metadata is not None:
            update_data["metadata"] = topic_update.metadata

        topic = db.update_research_topic(topic_id, update_data)
        if not topic:
            raise HTTPException(status_code=404, detail="Research topic not found")

        return ResearchTopicResponse(**topic)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.delete("/topics/{topic_id}", response_model=SuccessResponse)
async def delete_research_topic(
    topic_id: str = Path(..., description="Topic ID"),
    db: HierarchicalDatabaseManager = Depends(get_database),
):
    """Delete a research topic and all its related data."""
    try:
        success = db.delete_research_topic(topic_id)
        if not success:
            raise HTTPException(status_code=404, detail="Research topic not found")

        return SuccessResponse(message="Research topic deleted successfully")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# RESEARCH PLAN ENDPOINTS
# =============================================================================


@v2_router.post("/topics/{topic_id}/plans", response_model=ResearchPlanResponse)
async def create_research_plan(
    plan_request: ResearchPlanRequest,
    topic_id: str = Path(..., description="Topic ID"),
    db: HierarchicalDatabaseManager = Depends(get_database),
):
    """Create a new research plan within a topic."""
    try:
        import json
        from datetime import datetime
        from uuid import uuid4

        # Verify topic exists
        topic = db.get_research_topic(topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Research topic not found")

        # Generate ID and timestamps
        plan_id = str(uuid4())
        now = datetime.utcnow()

        plan_data = {
            "id": plan_id,
            "topic_id": topic_id,
            "name": plan_request.name,
            "description": plan_request.description,
            "plan_type": plan_request.plan_type,
            "status": "draft",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "estimated_cost": 0.0,
            "actual_cost": 0.0,
            "plan_structure": json.dumps(plan_request.plan_structure or {}),
            "metadata": json.dumps(plan_request.metadata or {}),
        }

        plan = db.create_research_plan(plan_data)
        if not plan:
            raise HTTPException(
                status_code=500, detail="Failed to create research plan"
            )

        return ResearchPlanResponse(**plan)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.get("/topics/{topic_id}/plans", response_model=List[ResearchPlanResponse])
async def list_research_plans(
    topic_id: str = Path(..., description="Topic ID"),
    status: Optional[str] = Query(None, description="Filter by plan status"),
    db: HierarchicalDatabaseManager = Depends(get_database),
):
    """List all research plans for a topic."""
    try:
        # Verify topic exists
        topic = db.get_research_topic(topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Research topic not found")

        plans = db.get_research_plans_by_topic(topic_id, status_filter=status)
        return [ResearchPlanResponse(**plan) for plan in plans]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.get("/plans/{plan_id}", response_model=ResearchPlanResponse)
async def get_research_plan(
    plan_id: str = Path(..., description="Plan ID"),
    db: HierarchicalDatabaseManager = Depends(get_database),
):
    """Get a specific research plan."""
    try:
        plan = db.get_research_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Research plan not found")

        return ResearchPlanResponse(**plan)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.put("/plans/{plan_id}", response_model=ResearchPlanResponse)
async def update_research_plan(
    plan_update: ResearchPlanUpdate,
    plan_id: str = Path(..., description="Plan ID"),
    db: HierarchicalDatabaseManager = Depends(get_database),
):
    """Update a research plan."""
    try:
        # Build update data from non-None fields
        update_data = {}
        if plan_update.name is not None:
            update_data["name"] = plan_update.name
        if plan_update.description is not None:
            update_data["description"] = plan_update.description
        if plan_update.plan_type is not None:
            update_data["plan_type"] = plan_update.plan_type
        if plan_update.status is not None:
            update_data["status"] = plan_update.status
        if plan_update.plan_structure is not None:
            update_data["plan_structure"] = plan_update.plan_structure
        if plan_update.metadata is not None:
            update_data["metadata"] = plan_update.metadata

        plan = db.update_research_plan(plan_id, update_data)
        if not plan:
            raise HTTPException(status_code=404, detail="Research plan not found")

        return ResearchPlanResponse(**plan)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.delete("/plans/{plan_id}", response_model=SuccessResponse)
async def delete_research_plan(
    plan_id: str = Path(..., description="Plan ID"),
    db: HierarchicalDatabaseManager = Depends(get_database),
):
    """Delete a research plan and all its related data."""
    try:
        success = db.delete_research_plan(plan_id)
        if not success:
            raise HTTPException(status_code=404, detail="Research plan not found")

        return SuccessResponse(message="Research plan deleted successfully")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.post("/plans/{plan_id}/approve", response_model=ResearchPlanResponse)
async def approve_research_plan(
    plan_id: str = Path(..., description="Plan ID"),
    db: HierarchicalDatabaseManager = Depends(get_database),
):
    """Approve a research plan and update its approval status."""
    try:
        # First check if the plan exists
        plan = db.get_research_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Research plan not found")

        # Update the plan to approved status
        # Note: We use plan_approved field, not status change to 'approved'
        # Status remains as draft / active / completed / cancelled per the model definition
        update_data = {
            "plan_approved": True,
            "status": "active",
        }  # Set to active when approved

        success = db.update_research_plan(plan_id, update_data)
        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to approve research plan"
            )

        # Get the updated plan
        updated_plan = db.get_research_plan(plan_id)
        if not updated_plan:
            raise HTTPException(
                status_code=500, detail="Failed to retrieve updated plan"
            )

        return ResearchPlanResponse(**updated_plan)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# TASK ENDPOINTS
# =============================================================================


@v2_router.post("/plans/{plan_id}/tasks", response_model=TaskResponse)
async def create_task(
    task_request: TaskRequest,
    plan_id: str = Path(..., description="Plan ID"),
    db: HierarchicalDatabaseManager = Depends(get_database),
):
    """Create a new task within a plan."""
    try:
        import json
        from datetime import datetime
        from uuid import uuid4

        # Verify plan exists
        plan = db.get_research_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Research plan not found")

        # Generate ID and timestamps
        task_id = str(uuid4())
        now = datetime.utcnow()

        task_data = {
            "id": task_id,
            "plan_id": plan_id,
            "name": task_request.name,
            "description": task_request.description,
            "task_type": task_request.task_type,
            "task_order": task_request.task_order,
            "status": "pending",
            "stage": "planning",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "query": task_request.query,
            "max_results": task_request.max_results,
            "single_agent_mode": task_request.single_agent_mode,
            "estimated_cost": 0.0,
            "actual_cost": 0.0,
            "progress": 0.0,
            "metadata": json.dumps(task_request.metadata or {}),
        }

        task = db.create_task(task_data)
        if not task:
            raise HTTPException(status_code=500, detail="Failed to create task")

        return TaskResponse(**task)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.get("/plans/{plan_id}/tasks", response_model=List[TaskResponse])
async def list_tasks(
    plan_id: str = Path(..., description="Plan ID"),
    status: Optional[str] = Query(None, description="Filter by task status"),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    db: HierarchicalDatabaseManager = Depends(get_database),
):
    """List all tasks for a plan."""
    try:
        # Verify plan exists
        plan = db.get_research_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Research plan not found")

        tasks = db.get_tasks_by_plan(
            plan_id, status_filter=status, type_filter=task_type
        )
        return [TaskResponse(**task) for task in tasks]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str = Path(..., description="Task ID"),
    db: HierarchicalDatabaseManager = Depends(get_database),
):
    """Get a specific task."""
    try:
        task = db.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        return TaskResponse(**task)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_update: TaskUpdate,
    task_id: str = Path(..., description="Task ID"),
    db: HierarchicalDatabaseManager = Depends(get_database),
):
    """Update a task."""
    try:
        # Build update data from non-None fields
        update_data = {}
        if task_update.name is not None:
            update_data["name"] = task_update.name
        if task_update.description is not None:
            update_data["description"] = task_update.description
        if task_update.task_type is not None:
            update_data["task_type"] = task_update.task_type
        if task_update.task_order is not None:
            update_data["task_order"] = task_update.task_order
        if task_update.status is not None:
            update_data["status"] = task_update.status
        if task_update.stage is not None:
            update_data["stage"] = task_update.stage
        if task_update.query is not None:
            update_data["query"] = task_update.query
        if task_update.max_results is not None:
            update_data["max_results"] = task_update.max_results
        if task_update.single_agent_mode is not None:
            update_data["single_agent_mode"] = task_update.single_agent_mode
        if task_update.metadata is not None:
            update_data["metadata"] = task_update.metadata

        task = db.update_task(task_id, update_data)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        return TaskResponse(**task)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.delete("/tasks/{task_id}", response_model=SuccessResponse)
async def delete_task(
    task_id: str = Path(..., description="Task ID"),
    db: HierarchicalDatabaseManager = Depends(get_database),
):
    """Delete a task."""
    try:
        success = db.delete_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="Task not found")

        return SuccessResponse(message="Task deleted successfully")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# TASK EXECUTION ENDPOINTS
# =============================================================================


@v2_router.post("/tasks/{task_id}/execute", response_model=TaskResponse)
async def execute_task(
    task_id: str = Path(..., description="Task ID"),
    db: HierarchicalDatabaseManager = Depends(get_database),
    research_manager: Optional[ResearchManager] = Depends(get_research_manager),
):
    """Execute a research task using the Research Manager and AI agents."""
    try:
        # Get the task
        task = db.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Check if task is in a valid state for execution
        if task["status"] not in ["pending", "failed"]:
            raise HTTPException(
                status_code=400,
                detail=f"Task cannot be executed in status: {task['status']}",
            )

        # Check if research manager is available
        if not research_manager:
            raise HTTPException(
                status_code=503,
                detail="Research Manager not available. Please ensure the research system is properly initialized.",
            )

        # Update task status to running
        update_data = {"status": "running", "stage": "planning"}
        db.update_task(task_id, update_data)

        try:
            # Execute the task using the Research Manager
            # This will trigger the AI planning agent to generate a comprehensive research plan
            # Pass the existing plan_id so the research manager updates the correct plan
            options = task.get("metadata", {}).copy()
            if task.get("plan_id"):
                options["existing_plan_id"] = task["plan_id"]

            research_task_id, cost_info = await research_manager.start_research_task(
                query=task.get("query", ""),
                user_id=task.get("user_id", "system"),
                project_id=task.get("project_id"),
                options=options,
            )

            # For now, consider the task successful if we got a research task ID
            task_result = {
                "success": True,
                "task_id": research_task_id,
                "cost_info": cost_info,
                "results": [
                    {
                        "message": "Research task started successfully with AI planning agent"
                    }
                ],
                "research_plan": {"status": "AI plan generation in progress"},
            }

            if task_result and task_result.get("success"):
                # Update task with results from research manager
                execution_result = {
                    "status": "completed",
                    "stage": "complete",
                    "progress": 100.0,
                    "execution_results": task_result.get("results", []),
                    "synthesis": task_result.get("synthesis"),
                    "reasoning_output": task_result.get("reasoning"),
                    "metadata": {
                        "research_task_id": task_result.get("task_id"),
                        "cost_info": task_result.get("cost_info", {}),
                    },
                }

                # If this task generated a research plan, update the associated plan
                if task_result.get("research_plan") and task.get("plan_id"):
                    plan_structure = task_result["research_plan"]
                    db.update_research_plan(
                        task["plan_id"],
                        {
                            "plan_structure": plan_structure,
                            "status": "active",
                            "plan_approved": True,
                        },
                    )

            else:
                # Task failed
                execution_result = {
                    "status": "failed",
                    "stage": "failed",
                    "progress": 0.0,
                    "execution_results": [
                        {"error": task_result.get("error", "Unknown error occurred")}
                    ],
                }

        except Exception as e:
            # Handle research manager execution errors
            execution_result = {
                "status": "failed",
                "stage": "failed",
                "progress": 0.0,
                "execution_results": [
                    {"error": f"Research execution failed: {str(e)}"}
                ],
            }

        final_task = db.update_task(task_id, execution_result)
        if not final_task:
            raise HTTPException(
                status_code=500, detail="Failed to update task after execution"
            )

        # Ensure metadata is properly parsed as dict for TaskResponse validation
        if isinstance(final_task.get("metadata"), str):
            try:
                final_task["metadata"] = json.loads(final_task["metadata"])
            except (json.JSONDecodeError, TypeError):
                final_task["metadata"] = {}

        return TaskResponse(**final_task)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.post("/tasks/{task_id}/cancel", response_model=SuccessResponse)
async def cancel_task(
    task_id: str = Path(..., description="Task ID"),
    db: HierarchicalDatabaseManager = Depends(get_database),
):
    """Cancel a running task."""
    try:
        task = db.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        if task["status"] != "running":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel task with status: {task['status']}",
            )

        # Update task status to cancelled
        update_data = {"status": "cancelled", "stage": "complete"}
        db.update_task(task_id, update_data)

        return SuccessResponse(message="Task cancelled successfully")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# HIERARCHICAL NAVIGATION ENDPOINTS
# =============================================================================


@v2_router.get("/projects/{project_id}/hierarchy", response_model=ProjectHierarchy)
async def get_project_hierarchy(
    project_id: str = Path(..., description="Project ID"),
    db: HierarchicalDatabaseManager = Depends(get_database),
):
    """Get complete hierarchy for a project (topics -> plans -> tasks)."""
    try:
        hierarchy = db.get_project_hierarchy(project_id)
        if not hierarchy:
            raise HTTPException(status_code=404, detail="Project not found")

        return ProjectHierarchy(**hierarchy)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# STATISTICS ENDPOINTS
# =============================================================================


@v2_router.get("/projects/{project_id}/stats", response_model=ProjectStats)
async def get_project_stats(
    project_id: str = Path(..., description="Project ID"),
    db: HierarchicalDatabaseManager = Depends(get_database),
):
    """Get project statistics."""
    try:
        stats = db.get_project_stats(project_id)
        if not stats:
            raise HTTPException(status_code=404, detail="Project not found")

        return ProjectStats(**stats)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.get("/topics/{topic_id}/stats", response_model=TopicStats)
async def get_topic_stats(
    topic_id: str = Path(..., description="Topic ID"),
    db: HierarchicalDatabaseManager = Depends(get_database),
):
    """Get topic statistics."""
    try:
        stats = db.get_topic_stats(topic_id)
        if not stats:
            raise HTTPException(status_code=404, detail="Topic not found")

        return TopicStats(**stats)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.get("/plans/{plan_id}/stats", response_model=PlanStats)
async def get_plan_stats(
    plan_id: str = Path(..., description="Plan ID"),
    db: HierarchicalDatabaseManager = Depends(get_database),
):
    """Get plan statistics."""
    try:
        stats = db.get_plan_stats(plan_id)
        if not stats:
            raise HTTPException(status_code=404, detail="Plan not found")

        return PlanStats(**stats)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SEARCH ENDPOINTS
# =============================================================================


@v2_router.get("/projects/{project_id}/search")
async def search_project_hierarchy(
    project_id: str = Path(..., description="Project ID"),
    q: str = Query(..., description="Search query"),
    types: Optional[List[str]] = Query(
        None, description="Entity types to search (topic, plan, task)"
    ),
    status: Optional[List[str]] = Query(None, description="Status filters"),
    db: HierarchicalDatabaseManager = Depends(get_database),
):
    """Search across project hierarchy."""
    try:
        # Verify project exists
        project = db.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        results = db.search_project_hierarchy(
            project_id=project_id, query=q, entity_types=types, status_filters=status
        )

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SIMPLE RESEARCH ENDPOINTS
# =============================================================================


@v2_router.post("/topics/{topic_id}/research")
async def start_research(
    topic_id: str = Path(..., description="Topic ID"),
    query: str = Query(..., description="Research query"),
    db: HierarchicalDatabaseManager = Depends(get_database),
    research_manager: Optional[ResearchManager] = Depends(get_research_manager),
):
    """Start research on a topic-the Research Manager handles everything."""
    try:
        # Verify topic exists
        topic = db.get_research_topic(topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        # Check if research manager is available
        if not research_manager:
            raise HTTPException(
                status_code=503, detail="Research Manager not available"
            )

        # Start research-let the Research Manager handle plans and tasks
        research_task_id, cost_info = await research_manager.start_research_task(
            query=query,
            user_id="system",
            project_id=topic.get("project_id"),
            options={
                "topic_id": topic_id,
                "cost_override": True,  # Auto-approve for this simple endpoint
                "create_full_structure": True,  # Signal to create complete structure
            },
        )

        return {
            "success": True,
            "message": "Research started successfully",
            "research_task_id": research_task_id,
            "topic_id": topic_id,
            "query": query,
            "cost_info": cost_info,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
