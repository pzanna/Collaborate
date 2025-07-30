"""V2 API endpoints for hierarchical research structure - Clean Implementation for API Gateway Service."""

import json
import logging
from typing import List, Optional
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from src.data_models.hierarchical_data_models import (
    # Request models
    ProjectRequest, ResearchTopicRequest, ResearchPlanRequest, TaskRequest,
    # Update models  
    ProjectUpdate, ResearchTopicUpdate, ResearchPlanUpdate, TaskUpdate,
    # Response models
    ProjectResponse, ResearchTopicResponse, ResearchPlanResponse, TaskResponse,
    # Utility models
    SuccessResponse, ProjectHierarchy, ProjectStats, TopicStats, PlanStats
)

# Import database and MCP client access
from native_database_client import get_native_database

logger = logging.getLogger(__name__)

# Create router for V2 hierarchical research endpoints
v2_router = APIRouter(prefix="/v2", tags=["v2-hierarchical"])


# Dependency functions
def get_database():
    """Dependency to get database manager."""
    try:
        db_client = get_native_database()
        if not db_client._initialized:
            raise HTTPException(status_code=503, detail="Database service not available")
        return db_client
    except Exception as e:
        raise HTTPException(status_code=503, detail="Database service not available")


# MCP client reference (will be set by main app)
_mcp_client = None


def set_mcp_client(client):
    """Set the MCP client reference."""
    global _mcp_client
    _mcp_client = client


def get_mcp_client():
    """Dependency to get MCP client."""
    return _mcp_client


# Override dependencies with actual implementations (backward compatibility)
def override_dependencies(database_dependency, mcp_client_dependency):
    """Override the dependency functions with actual implementations."""
    pass  # No longer needed with direct approach


# =============================================================================
# PROJECT ENDPOINTS
# =============================================================================

@v2_router.post("/projects", response_model=ProjectResponse)
async def create_project(
    project_request: ProjectRequest,
    db=Depends(get_database),
    mcp_client=Depends(get_mcp_client),
):
    """Create a new project."""
    try:
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

        # Send project creation via MCP
        if mcp_client and mcp_client.is_connected:
            task_data = {
                "task_id": str(uuid4()),
                "context_id": f"project-{project_id}",
                "agent_type": "database",
                "action": "create_project",
                "payload": project_data
            }
            success = await mcp_client.send_research_action(task_data)
            if not success:
                raise HTTPException(status_code=503, detail="Failed to send project creation to MCP server")

        # Return the project response immediately (optimistic response)
        project_response_data = {
            "id": project_id,
            "name": project_request.name,
            "description": project_request.description,
            "status": "active",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "topics_count": 0,
            "plans_count": 0,
            "tasks_count": 0,
            "total_cost": 0.0,
            "completion_rate": 0.0,
            "metadata": project_request.metadata or {},
        }

        return ProjectResponse(**project_response_data)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(
    status: Optional[str] = Query(None, description="Filter by project status"),
    limit: Optional[int] = Query(None, description="Limit number of results"),
    db=Depends(get_database),
):
    """List all projects."""
    try:
        # Use database client to get projects
        projects = await db.get_projects(status_filter=status, limit=limit)
        
        # For each project, get the statistics to populate topic/plan/task counts
        enriched_projects = []
        for project in projects:
            try:
                stats = await db.get_project_stats(project["id"])
                if stats:
                    # Merge project data with statistics
                    enriched_project = {**project, **stats}
                    enriched_projects.append(enriched_project)
                else:
                    # If no stats available, add default values
                    enriched_project = {
                        **project,
                        "topics_count": 0,
                        "plans_count": 0, 
                        "tasks_count": 0,
                        "total_cost": 0.0,
                        "completion_rate": 0.0
                    }
                    enriched_projects.append(enriched_project)
            except Exception as e:
                logger.warning(f"Failed to get stats for project {project['id']}: {e}")
                # Add default values if stats fail
                enriched_project = {
                    **project,
                    "topics_count": 0,
                    "plans_count": 0,
                    "tasks_count": 0, 
                    "total_cost": 0.0,
                    "completion_rate": 0.0
                }
                enriched_projects.append(enriched_project)
                
        return [ProjectResponse(**project) for project in enriched_projects]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str = Path(..., description="Project ID"),
    db=Depends(get_database),
):
    """Get a specific project."""
    try:
        # Use database client to get project
        project = await db.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get project statistics to populate topic/plan/task counts
        try:
            stats = await db.get_project_stats(project_id)
            if stats:
                # Merge project data with statistics
                enriched_project = {**project, **stats}
            else:
                # Add default values if no stats available
                enriched_project = {
                    **project,
                    "topics_count": 0,
                    "plans_count": 0,
                    "tasks_count": 0,
                    "total_cost": 0.0,
                    "completion_rate": 0.0
                }
        except Exception as e:
            logger.warning(f"Failed to get stats for project {project_id}: {e}")
            # Add default values if stats fail
            enriched_project = {
                **project,
                "topics_count": 0,
                "plans_count": 0,
                "tasks_count": 0,
                "total_cost": 0.0,
                "completion_rate": 0.0
            }

        return ProjectResponse(**enriched_project)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_update: ProjectUpdate,
    project_id: str = Path(..., description="Project ID"),
    db=Depends(get_database),
    mcp_client=Depends(get_mcp_client),
):
    """Update a project."""
    try:
        # First check if project exists
        existing_project = await db.get_project(project_id)
        if not existing_project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Build update data from non-None fields
        update_data = {"id": project_id}
        if project_update.name is not None:
            update_data["name"] = project_update.name
        if project_update.description is not None:
            update_data["description"] = project_update.description
        if project_update.status is not None:
            update_data["status"] = project_update.status
        if project_update.metadata is not None:
            update_data["metadata"] = json.dumps(project_update.metadata)

        # Send project update via MCP
        if mcp_client and mcp_client.is_connected:
            task_data = {
                "task_id": str(uuid4()),
                "context_id": f"project-{project_id}",
                "agent_type": "database",
                "action": "update_project",
                "payload": update_data
            }
            success = await mcp_client.send_research_action(task_data)
            if not success:
                raise HTTPException(status_code=503, detail="Failed to send project update to MCP server")

        # Return updated project (we merge existing data with updates)
        updated_project = existing_project.copy()
        if project_update.name is not None:
            updated_project["name"] = project_update.name
        if project_update.description is not None:
            updated_project["description"] = project_update.description
        if project_update.status is not None:
            updated_project["status"] = project_update.status
        if project_update.metadata is not None:
            updated_project["metadata"] = project_update.metadata
        
        updated_project["updated_at"] = datetime.utcnow().isoformat()

        return ProjectResponse(**updated_project)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.delete("/projects/{project_id}", response_model=SuccessResponse)
async def delete_project(
    project_id: str = Path(..., description="Project ID"),
    db=Depends(get_database),
    mcp_client=Depends(get_mcp_client),
):
    """Delete a project and all its related data."""
    try:
        # First check if project exists
        existing_project = await db.get_project(project_id)
        if not existing_project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Send project deletion via MCP
        if mcp_client and mcp_client.is_connected:
            task_data = {
                "task_id": str(uuid4()),
                "context_id": f"project-{project_id}",
                "agent_type": "database",
                "action": "delete_project",
                "payload": {"id": project_id}
            }
            success = await mcp_client.send_research_action(task_data)
            if not success:
                raise HTTPException(status_code=503, detail="Failed to send project deletion to MCP server")

        return SuccessResponse(message="Project deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# RESEARCH TOPIC ENDPOINTS
# =============================================================================

@v2_router.post("/projects/{project_id}/topics", response_model=ResearchTopicResponse)
async def create_research_topic(
    topic_request: ResearchTopicRequest,
    project_id: str = Path(..., description="Project ID"),
    db=Depends(get_database),
    mcp_client=Depends(get_mcp_client),
):
    """Create a new research topic within a project."""
    try:
        # First check if project exists
        existing_project = await db.get_project(project_id)
        if not existing_project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Generate ID and timestamps
        topic_id = str(uuid4())
        now = datetime.utcnow()

        topic_data = {
            "id": topic_id,
            "project_id": project_id,
            "name": topic_request.name,
            "description": topic_request.description or "",
            "status": "active",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "metadata": json.dumps(topic_request.metadata or {}),
        }

        # Send topic creation via MCP
        if mcp_client and mcp_client.is_connected:
            task_data = {
                "task_id": str(uuid4()),
                "context_id": f"topic-{topic_id}",
                "agent_type": "database",
                "action": "create_research_topic",
                "payload": topic_data
            }
            success = await mcp_client.send_research_action(task_data)
            if not success:
                raise HTTPException(status_code=503, detail="Failed to send topic creation to MCP server")

        # Return the topic response immediately (optimistic response)
        topic_response_data = {
            "id": topic_id,
            "project_id": project_id,
            "name": topic_request.name,
            "description": topic_request.description or "",
            "status": "active",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "plans_count": 0,
            "tasks_count": 0,
            "total_cost": 0.0,
            "completion_rate": 0.0,
            "metadata": topic_request.metadata or {},
        }

        return ResearchTopicResponse(**topic_response_data)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.get("/projects/{project_id}/topics", response_model=List[ResearchTopicResponse])
async def list_research_topics(
    project_id: str = Path(..., description="Project ID"),
    status: Optional[str] = Query(None, description="Filter by topic status"),
    db=Depends(get_database),
):
    """List all research topics for a project."""
    try:
        # First check if project exists
        existing_project = await db.get_project(project_id)
        if not existing_project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get topics for the project using database client
        topics = await db.get_research_topics(project_id=project_id)
        
        # Apply status filter if provided
        if status:
            topics = [topic for topic in topics if topic.get("status") == status]
        
        # Enhance each topic with actual plan and task counts
        enriched_topics = []
        for topic in topics:
            try:
                # Get research plans for this topic to get actual counts
                plans = await db.get_research_plans(topic["id"])
                plans_count = len(plans) if plans else 0
                
                # For tasks count, we'd need to aggregate across all plans
                # For now, using the default 0 from the database client
                # This could be enhanced by adding a get_topic_stats method
                enhanced_topic = {
                    **topic,
                    "plans_count": plans_count,
                    # tasks_count remains 0 for now until we add proper aggregation
                }
                enriched_topics.append(enhanced_topic)
            except Exception as e:
                logger.warning(f"Failed to get enhanced stats for topic {topic['id']}: {e}")
                # Use the original topic data if enhancement fails
                enriched_topics.append(topic)
        
        return [ResearchTopicResponse(**topic) for topic in enriched_topics]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.get("/topics/{topic_id}", response_model=ResearchTopicResponse)
async def get_research_topic(
    topic_id: str = Path(..., description="Topic ID"),
    db=Depends(get_database),
):
    """Get a specific research topic."""
    try:
        # Get topic using database client
        topic = await db.get_research_topic(topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Research topic not found")

        return ResearchTopicResponse(**topic)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.put("/topics/{topic_id}", response_model=ResearchTopicResponse)
async def update_research_topic(
    topic_update: ResearchTopicUpdate,
    topic_id: str = Path(..., description="Topic ID"),
    db=Depends(get_database),
    mcp_client=Depends(get_mcp_client),
):
    """Update a research topic."""
    try:
        # First check if topic exists
        existing_topic = await db.get_research_topic(topic_id)
        if not existing_topic:
            raise HTTPException(status_code=404, detail="Research topic not found")

        # Build update data from non-None fields
        update_data = {"id": topic_id}
        if topic_update.name is not None:
            update_data["name"] = topic_update.name
        if topic_update.description is not None:
            update_data["description"] = topic_update.description
        if topic_update.metadata is not None:
            update_data["metadata"] = json.dumps(topic_update.metadata)

        # Send topic update via MCP
        if mcp_client and mcp_client.is_connected:
            task_data = {
                "task_id": str(uuid4()),
                "context_id": f"topic-{topic_id}",
                "agent_type": "database",
                "action": "update_research_topic",
                "payload": update_data
            }
            success = await mcp_client.send_research_action(task_data)
            if not success:
                raise HTTPException(status_code=503, detail="Failed to send topic update to MCP server")

        # Return updated topic (we merge existing data with updates)
        updated_topic = existing_topic.copy()
        if topic_update.name is not None:
            updated_topic["name"] = topic_update.name
        if topic_update.description is not None:
            updated_topic["description"] = topic_update.description
        if topic_update.metadata is not None:
            updated_topic["metadata"] = topic_update.metadata
        
        updated_topic["updated_at"] = datetime.utcnow().isoformat()

        return ResearchTopicResponse(**updated_topic)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.delete("/topics/{topic_id}", response_model=SuccessResponse)
async def delete_research_topic(
    topic_id: str = Path(..., description="Topic ID"),
    db=Depends(get_database),
    mcp_client=Depends(get_mcp_client),
):
    """Delete a research topic and all its related data."""
    try:
        # First check if topic exists
        existing_topic = await db.get_research_topic(topic_id)
        if not existing_topic:
            raise HTTPException(status_code=404, detail="Research topic not found")

        # Send topic deletion via MCP
        if mcp_client and mcp_client.is_connected:
            task_data = {
                "task_id": str(uuid4()),
                "context_id": f"topic-{topic_id}",
                "agent_type": "database",
                "action": "delete_research_topic",
                "payload": {"id": topic_id}
            }
            success = await mcp_client.send_research_action(task_data)
            if not success:
                raise HTTPException(status_code=503, detail="Failed to send topic deletion to MCP server")

        return SuccessResponse(message="Research topic deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.get("/projects/{project_id}/topics/{topic_id}", response_model=ResearchTopicResponse)
async def get_research_topic_by_project(
    project_id: str = Path(..., description="Project ID"),
    topic_id: str = Path(..., description="Topic ID"),
    db=Depends(get_database),
):
    """Get a specific research topic within a project."""
    try:
        # First check if project exists
        existing_project = await db.get_project(project_id)
        if not existing_project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get topic using database client
        topic = await db.get_research_topic(topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Research topic not found")
        
        # Verify the topic belongs to the project
        if topic["project_id"] != project_id:
            raise HTTPException(status_code=404, detail="Research topic not found in this project")

        return ResearchTopicResponse(**topic)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.put("/projects/{project_id}/topics/{topic_id}", response_model=ResearchTopicResponse)
async def update_research_topic_by_project(
    topic_update: ResearchTopicUpdate,
    project_id: str = Path(..., description="Project ID"),
    topic_id: str = Path(..., description="Topic ID"),
    db=Depends(get_database),
    mcp_client=Depends(get_mcp_client),
):
    """Update a research topic within a project."""
    try:
        # First check if project exists
        existing_project = await db.get_project(project_id)
        if not existing_project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Check if topic exists and belongs to project
        existing_topic = await db.get_research_topic(topic_id)
        if not existing_topic:
            raise HTTPException(status_code=404, detail="Research topic not found")
        
        if existing_topic["project_id"] != project_id:
            raise HTTPException(status_code=404, detail="Research topic not found in this project")

        # Build update data from non-None fields
        update_data = {"id": topic_id}
        if topic_update.name is not None:
            update_data["name"] = topic_update.name
        if topic_update.description is not None:
            update_data["description"] = topic_update.description
        if topic_update.metadata is not None:
            update_data["metadata"] = json.dumps(topic_update.metadata)

        # Send topic update via MCP
        if mcp_client and mcp_client.is_connected:
            task_data = {
                "task_id": str(uuid4()),
                "context_id": f"topic-{topic_id}",
                "agent_type": "database",
                "action": "update_research_topic",
                "payload": update_data
            }
            success = await mcp_client.send_research_action(task_data)
            if not success:
                raise HTTPException(status_code=503, detail="Failed to send topic update to MCP server")

        # Return updated topic (we merge existing data with updates)
        updated_topic = existing_topic.copy()
        if topic_update.name is not None:
            updated_topic["name"] = topic_update.name
        if topic_update.description is not None:
            updated_topic["description"] = topic_update.description
        if topic_update.metadata is not None:
            updated_topic["metadata"] = topic_update.metadata
        
        updated_topic["updated_at"] = datetime.utcnow().isoformat()

        return ResearchTopicResponse(**updated_topic)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.delete("/projects/{project_id}/topics/{topic_id}", response_model=SuccessResponse)
async def delete_research_topic_by_project(
    project_id: str = Path(..., description="Project ID"),
    topic_id: str = Path(..., description="Topic ID"),
    db=Depends(get_database),
    mcp_client=Depends(get_mcp_client),
):
    """Delete a research topic within a project."""
    try:
        # First check if project exists
        existing_project = await db.get_project(project_id)
        if not existing_project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Check if topic exists and belongs to project
        existing_topic = await db.get_research_topic(topic_id)
        if not existing_topic:
            raise HTTPException(status_code=404, detail="Research topic not found")
        
        if existing_topic["project_id"] != project_id:
            raise HTTPException(status_code=404, detail="Research topic not found in this project")

        # Send topic deletion via MCP
        if mcp_client and mcp_client.is_connected:
            task_data = {
                "task_id": str(uuid4()),
                "context_id": f"topic-{topic_id}",
                "agent_type": "database",
                "action": "delete_research_topic",
                "payload": {"id": topic_id}
            }
            success = await mcp_client.send_research_action(task_data)
            if not success:
                raise HTTPException(status_code=503, detail="Failed to send topic deletion to MCP server")

        return SuccessResponse(message="Research topic deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@v2_router.get("/projects/{project_id}/stats", response_model=ProjectStats)
async def get_project_stats(
    project_id: str = Path(..., description="Project ID"),
    db=Depends(get_database),
):
    """Get project statistics."""
    try:
        # Get project statistics from database
        stats = await db.get_project_stats(project_id)
        if not stats:
            raise HTTPException(status_code=404, detail="Project not found")

        return ProjectStats(**stats)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.get("/projects/{project_id}/hierarchy", response_model=ProjectHierarchy)
async def get_project_hierarchy(
    project_id: str = Path(..., description="Project ID"),
    db=Depends(get_database),
):
    """Get complete hierarchy for a project (topics -> plans -> tasks)."""
    try:
        # Get complete project hierarchy from database
        hierarchy = await db.get_project_hierarchy(project_id)
        if not hierarchy:
            raise HTTPException(status_code=404, detail="Project not found")

        return ProjectHierarchy(**hierarchy)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
