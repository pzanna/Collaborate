"""V2 API endpoints for hierarchical research structure - Clean Implementation for API Gateway Service."""

import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from data_models.hierarchical_data_models import (
    # Request models
    ProjectRequest, ResearchTopicRequest, ResearchPlanRequest, ExecuteResearchRequest,
    # Update models  
    ProjectUpdate, ResearchTopicUpdate, ResearchPlanUpdate,
    # Response models
    ProjectResponse, ResearchTopicResponse, ResearchPlanResponse, ResearchExecutionResponse,
    # Utility models
    SuccessResponse, ProjectHierarchy, ProjectStats, TopicStats, PlanStats
)

# Import database client access
from native_database_client import get_native_database

# Import MCP client for write operations - Commented out due to transport compatibility issues
# from mcp_client import get_mcp_client

# For now, we'll use the same database client for both reads and writes
# TODO: Re-implement MCP client once transport issues are resolved

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


async def get_mcp_database():
    """Dependency to get database client for write operations."""
    # For now, return the same database client used for reads
    # TODO: Re-implement MCP client once transport issues are resolved
    return get_database()


# =============================================================================
# PROJECT ENDPOINTS
# =============================================================================

@v2_router.post("/projects", response_model=ProjectResponse)
async def create_project(
    project_request: ProjectRequest,
    db=Depends(get_database),
    mcp_db=Depends(get_mcp_database),
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
            "status": "pending",
            "metadata": project_request.metadata or {},
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }

        # Store project creation via database client (bypassing MCP for now)
        result = await mcp_db.create_project(project_data)
        if result is None:
            raise HTTPException(status_code=500, detail="Failed to create project: No result returned")
        logger.info(f"Created project {project_id} via database: {result}")

        # Use the actual database result to construct response
        project_response_data = {
            "id": result["id"],
            "name": result["name"],
            "description": result["description"],
            "status": result["status"],
            "created_at": result["created_at"],
            "updated_at": result["updated_at"],
            "topics_count": 0,  # These will be calculated separately if needed
            "plans_count": 0,
            "tasks_count": 0,
            "total_cost": 0.0,
            "completion_rate": 0.0,
            "metadata": result.get("metadata", {}),
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
    mcp_db=Depends(get_mcp_database),
):
    """Update a project."""
    try:
        # First check if project exists
        existing_project = await db.get_project(project_id)
        if not existing_project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Build update data for MCP call
        updates: Dict[str, Any] = {}
        if project_update.name is not None:
            updates["name"] = project_update.name
        if project_update.description is not None:
            updates["description"] = project_update.description
        if project_update.status is not None:
            updates["status"] = project_update.status
        if project_update.metadata is not None:
            updates["metadata"] = project_update.metadata

        # Send project update via database client (bypassing MCP for now)
        # Update project via database
        result = await mcp_db.update_project(project_id, updates)
        if result is None:
            raise HTTPException(status_code=500, detail="Failed to update project: No result returned")
        logger.info(f"Updated project {project_id} via database: {result}")

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
    mcp_db=Depends(get_mcp_database),
):
    """Delete a project and all its related data."""
    try:
        # First check if project exists
        existing_project = await db.get_project(project_id)
        if not existing_project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Send project deletion via database client (bypassing MCP for now)
        await mcp_db.delete_project(project_id)
        logger.info(f"Deleted project {project_id} via database")

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
    mcp_db=Depends(get_mcp_database),
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
            "metadata": topic_request.metadata or {},
        }

        # Send topic creation via database database client
        result = await mcp_db.create_research_topic(topic_data)
        if result is None:
            raise HTTPException(status_code=500, detail=f"Failed to create research topic: 'No result returned'")
        logger.info(f"Created topic {topic_id} via database: {result}")

        # Return the topic response immediately
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
    mcp_db=Depends(get_mcp_database),
):
    """Update a research topic."""
    try:
        # First check if topic exists
        existing_topic = await db.get_research_topic(topic_id)
        if not existing_topic:
            raise HTTPException(status_code=404, detail="Research topic not found")

        # Build update data for MCP call
        updates: Dict[str, Any] = {}
        if topic_update.name is not None:
            updates["name"] = topic_update.name
        if topic_update.description is not None:
            updates["description"] = topic_update.description
        if topic_update.metadata is not None:
            updates["metadata"] = topic_update.metadata

        # Send topic update via database database client
        result = await mcp_db.update_research_topic(topic_id, updates)
        if result is None:
            raise HTTPException(status_code=500, detail=f"Failed to update research topic: 'No result returned'")
        logger.info(f"Updated topic {topic_id} via database: {result}")

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
    mcp_db=Depends(get_mcp_database),
):
    """Delete a research topic and all its related data."""
    try:
        # First check if topic exists
        existing_topic = await db.get_research_topic(topic_id)
        if not existing_topic:
            raise HTTPException(status_code=404, detail="Research topic not found")

        # Send topic deletion via database database client
        await mcp_db.delete_research_topic(topic_id)
        logger.info(f"Deleted topic {topic_id} via database")

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
    mcp_db=Depends(get_mcp_database),
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

        # Build update data for MCP call
        updates: Dict[str, Any] = {}
        if topic_update.name is not None:
            updates["name"] = topic_update.name
        if topic_update.description is not None:
            updates["description"] = topic_update.description
        if topic_update.metadata is not None:
            updates["metadata"] = topic_update.metadata

        # Send topic update via database database client
        result = await mcp_db.update_research_topic(topic_id, updates)
        if result is None:
            raise HTTPException(status_code=500, detail=f"Failed to update research topic: 'No result returned'")
        logger.info(f"Updated topic {topic_id} in project {project_id} via database: {result}")

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
    mcp_db=Depends(get_mcp_database),
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

        # Send topic deletion via database database client
        await mcp_db.delete_research_topic(topic_id)
        logger.info(f"Deleted topic {topic_id} in project {project_id} via database")

        return SuccessResponse(message="Research topic deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# RESEARCH PLAN ENDPOINTS
# =============================================================================

@v2_router.post("/topics/{topic_id}/plans", response_model=ResearchPlanResponse)
async def create_research_plan(
    plan_request: ResearchPlanRequest,
    topic_id: str = Path(..., description="Topic ID"),
    db=Depends(get_database),
    mcp_db=Depends(get_mcp_database),
):
    """Create a new research plan within a topic."""
    try:
        # First check if topic exists
        existing_topic = await db.get_research_topic(topic_id)
        if not existing_topic:
            raise HTTPException(status_code=404, detail="Research topic not found")

        # Generate ID and timestamps
        plan_id = str(uuid4())
        now = datetime.utcnow()

        plan_data = {
            "id": plan_id,
            "topic_id": topic_id,
            "name": plan_request.name,
            "description": plan_request.description or "",
            "plan_type": plan_request.plan_type,
            "status": "draft",
            "plan_approved": False,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "estimated_cost": 0.0,
            "actual_cost": 0.0,
            "plan_structure": plan_request.plan_structure or {},
            "initial_literature_results": plan_request.initial_literature_results or {},
            "reviewed_literature_results": plan_request.reviewed_literature_results or {},
            "metadata": plan_request.metadata or {},
        }

        # Send plan creation via database database client
        result = await mcp_db.create_research_plan(plan_data)
        if result is None:
            raise HTTPException(status_code=500, detail=f"Failed to create research plan: 'No result returned'")
        logger.info(f"Created plan {plan_id} via database: {result}")

        # Return the plan data we expect to be created
        plan_response_data = {
            **plan_data,
            "tasks_count": 0,
            "completed_tasks": 0,
            "progress": 0.0,
            "plan_structure": plan_request.plan_structure or {},
            "initial_literature_results": plan_request.initial_literature_results or {},
            "reviewed_literature_results": plan_request.reviewed_literature_results or {},
            "metadata": plan_request.metadata or {}
        }

        return ResearchPlanResponse(**plan_response_data)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.post("/topics/{topic_id}/ai-plans", response_model=ResearchPlanResponse)
async def generate_ai_research_plan(
    plan_request: ResearchPlanRequest,
    topic_id: str = Path(..., description="Topic ID"),
    db=Depends(get_database),
    mcp_db=Depends(get_mcp_database),
):
    """Generate an AI-powered research plan within a topic."""
    try:
        # First check if topic exists
        existing_topic = await db.get_research_topic(topic_id)
        if not existing_topic:
            raise HTTPException(status_code=404, detail="Research topic not found")

        # Generate ID and timestamps
        plan_id = str(uuid4())
        now = datetime.utcnow()

        # For now, return a basic plan structure without AI generation
        # TODO: Implement AI plan generation when needed
        basic_plan_structure = {
            "title": plan_request.name,
            "description": plan_request.description or "",
            "sections": [
                {"title": "Literature Review", "description": "Comprehensive review of existing literature"},
                {"title": "Methodology", "description": "Research methodology and approach"},
                {"title": "Data Collection", "description": "Data collection strategy"},
                {"title": "Analysis", "description": "Data analysis plan"},
                {"title": "Results", "description": "Expected results and findings"},
                {"title": "Conclusion", "description": "Summary and implications"}
            ],
            "estimated_duration": "4-6 weeks",
            "complexity": "medium"
        }

        plan_data = {
            "id": plan_id,
            "topic_id": topic_id,
            "name": plan_request.name,
            "description": plan_request.description or "",
            "plan_type": plan_request.plan_type,
            "status": "draft",
            "plan_approved": False,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "estimated_cost": 5.0,
            "actual_cost": 0.0,
            "plan_structure": basic_plan_structure,
            "initial_literature_results": plan_request.initial_literature_results or {},
            "reviewed_literature_results": plan_request.reviewed_literature_results or {},
            "metadata": {
                "ai_generated": True,
                "ai_model_used": "basic-template",
                "generation_cost": 0.0,
                "generation_timestamp": now.isoformat(),
                "confidence_score": 0.8,
                **(plan_request.metadata or {})
            },
        }

        # Send plan creation via database database client
        result = await mcp_db.create_research_plan(plan_data)
        if result is None:
            raise HTTPException(status_code=500, detail=f"Failed to create AI research plan: 'No result returned'")
        logger.info(f"Created AI plan {plan_id} via database: {result}")

        # Return the AI-generated plan data
        plan_response_data = {
            **plan_data,
            "tasks_count": 0,
            "completed_tasks": 0,
            "progress": 0.0,
            "plan_structure": basic_plan_structure,
            "initial_literature_results": plan_request.initial_literature_results or {},
            "reviewed_literature_results": plan_request.reviewed_literature_results or {},
            "metadata": {
                "ai_generated": True,
                "ai_model_used": "basic-template",
                "generation_cost": 0.0,
                "generation_timestamp": now.isoformat(),
                "confidence_score": 0.8,
                **(plan_request.metadata or {})
            }
        }

        return ResearchPlanResponse(**plan_response_data)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating AI research plan: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate AI research plan: {str(e)}")


@v2_router.get("/topics/{topic_id}/plans", response_model=List[ResearchPlanResponse])
async def list_research_plans(
    topic_id: str = Path(..., description="Topic ID"),
    status: Optional[str] = Query(None, description="Filter by plan status"),
    db=Depends(get_database),
):
    """List all research plans for a topic."""
    try:
        # First check if topic exists
        existing_topic = await db.get_research_topic(topic_id)
        if not existing_topic:
            raise HTTPException(status_code=404, detail="Research topic not found")

        # Get plans for the topic using database client
        plans = await db.get_research_plans(topic_id)
        
        # Apply status filter if provided
        if status:
            plans = [plan for plan in plans if plan.get("status") == status]
        
        # Enhance each plan with task counts
        enriched_plans = []
        for plan in plans:
            try:
                # Get tasks for this plan to get actual counts
                tasks = await db.get_tasks(plan["id"])
                tasks_count = len(tasks) if tasks else 0
                completed_tasks = len([t for t in (tasks or []) if t.get("status") == "completed"])
                progress = (completed_tasks / tasks_count * 100) if tasks_count > 0 else 0.0
                
                enhanced_plan = {
                    **plan,
                    "tasks_count": tasks_count,
                    "completed_tasks": completed_tasks,
                    "progress": progress,
                }
                enriched_plans.append(enhanced_plan)
            except Exception as e:
                logger.warning(f"Failed to get enhanced stats for plan {plan['id']}: {e}")
                # Use the original plan data if enhancement fails
                enhanced_plan = {
                    **plan,
                    "tasks_count": 0,
                    "completed_tasks": 0,
                    "progress": 0.0,
                }
                enriched_plans.append(enhanced_plan)
        
        return [ResearchPlanResponse(**plan) for plan in enriched_plans]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.get("/plans/{plan_id}", response_model=ResearchPlanResponse)
async def get_research_plan(
    plan_id: str = Path(..., description="Plan ID"),
    db=Depends(get_database),
):
    """Get a specific research plan."""
    try:
        # Get plan using database client
        plan = await db.get_research_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Research plan not found")

        # Enhance with task counts
        try:
            tasks = await db.get_tasks(plan_id)
            tasks_count = len(tasks) if tasks else 0
            completed_tasks = len([t for t in (tasks or []) if t.get("status") == "completed"])
            progress = (completed_tasks / tasks_count * 100) if tasks_count > 0 else 0.0
            
            enhanced_plan = {
                **plan,
                "tasks_count": tasks_count,
                "completed_tasks": completed_tasks,
                "progress": progress,
            }
        except Exception as e:
            logger.warning(f"Failed to get enhanced stats for plan {plan_id}: {e}")
            enhanced_plan = {
                **plan,
                "tasks_count": 0,
                "completed_tasks": 0,
                "progress": 0.0,
            }

        return ResearchPlanResponse(**enhanced_plan)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.put("/plans/{plan_id}", response_model=ResearchPlanResponse)
async def update_research_plan(
    plan_update: ResearchPlanUpdate,
    plan_id: str = Path(..., description="Plan ID"),
    db=Depends(get_database),
    mcp_db=Depends(get_mcp_database),
):
    """Update a research plan."""
    try:
        # First check if plan exists
        existing_plan = await db.get_research_plan(plan_id)
        if not existing_plan:
            raise HTTPException(status_code=404, detail="Research plan not found")

        # Build update data for MCP call
        updates = {}
        if plan_update.name is not None:
            updates["name"] = plan_update.name
        if plan_update.description is not None:
            updates["description"] = plan_update.description
        if plan_update.plan_type is not None:
            updates["plan_type"] = plan_update.plan_type
        if plan_update.status is not None:
            updates["status"] = plan_update.status
        if plan_update.plan_structure is not None:
            updates["plan_structure"] = plan_update.plan_structure
        if plan_update.initial_literature_results is not None:
            updates["initial_literature_results"] = plan_update.initial_literature_results
        if plan_update.reviewed_literature_results is not None:
            updates["reviewed_literature_results"] = plan_update.reviewed_literature_results
        if plan_update.metadata is not None:
            updates["metadata"] = plan_update.metadata

        # Send plan update via database database client
        result = await mcp_db.update_research_plan(plan_id, updates)
        if result is None:
            raise HTTPException(status_code=500, detail=f"Failed to update research plan: 'No result returned'")
        logger.info(f"Updated plan {plan_id} via database: {result}")
        # For now, return optimistic response

        # Return updated plan (we merge existing data with updates)
        updated_plan = existing_plan.copy()
        if plan_update.name is not None:
            updated_plan["name"] = plan_update.name
        if plan_update.description is not None:
            updated_plan["description"] = plan_update.description
        if plan_update.plan_type is not None:
            updated_plan["plan_type"] = plan_update.plan_type
        if plan_update.status is not None:
            updated_plan["status"] = plan_update.status
        if plan_update.plan_structure is not None:
            updated_plan["plan_structure"] = plan_update.plan_structure
        if plan_update.metadata is not None:
            updated_plan["metadata"] = plan_update.metadata
        
        updated_plan["updated_at"] = datetime.utcnow().isoformat()

        # Add enhanced stats
        try:
            tasks = await db.get_tasks(plan_id)
            tasks_count = len(tasks) if tasks else 0
            completed_tasks = len([t for t in (tasks or []) if t.get("status") == "completed"])
            progress = (completed_tasks / tasks_count * 100) if tasks_count > 0 else 0.0
            
            updated_plan.update({
                "tasks_count": tasks_count,
                "completed_tasks": completed_tasks,
                "progress": progress,
            })
        except Exception as e:
            logger.warning(f"Failed to get enhanced stats for updated plan {plan_id}: {e}")
            updated_plan.update({
                "tasks_count": 0,
                "completed_tasks": 0,
                "progress": 0.0,
            })

        return ResearchPlanResponse(**updated_plan)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.delete("/plans/{plan_id}", response_model=SuccessResponse)
async def delete_research_plan(
    plan_id: str = Path(..., description="Plan ID"),
    db=Depends(get_database),
    mcp_db=Depends(get_mcp_database),
):
    """Delete a research plan and all its related data."""
    try:
        # First check if plan exists
        existing_plan = await db.get_research_plan(plan_id)
        if not existing_plan:
            raise HTTPException(status_code=404, detail="Research plan not found")

        # Send plan deletion via database database client
        await mcp_db.delete_research_plan(plan_id)
        logger.info(f"Deleted plan {plan_id} via database")

        return SuccessResponse(message="Research plan deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.post("/plans/{plan_id}/approve", response_model=ResearchPlanResponse)
async def approve_research_plan(
    plan_id: str = Path(..., description="Plan ID"),
    db=Depends(get_database),
    mcp_db=Depends(get_mcp_database),
):
    """Approve a research plan and update its approval status."""
    try:
        # First check if the plan exists
        existing_plan = await db.get_research_plan(plan_id)
        if not existing_plan:
            raise HTTPException(status_code=404, detail="Research plan not found")

        # Send plan approval via database database client
        result = await mcp_db.approve_research_plan(plan_id)
        if result is None:
            raise HTTPException(status_code=500, detail=f"Failed to approve research plan: 'No result returned'")
        logger.info(f"Approved plan {plan_id} via database: {result}")

        # Return updated plan
        updated_plan = existing_plan.copy()
        updated_plan["plan_approved"] = True
        updated_plan["status"] = "active"
        updated_plan["updated_at"] = datetime.utcnow().isoformat()

        # Add enhanced stats
        try:
            tasks = await db.get_tasks(plan_id)
            tasks_count = len(tasks) if tasks else 0
            completed_tasks = len([t for t in (tasks or []) if t.get("status") == "completed"])
            progress = (completed_tasks / tasks_count * 100) if tasks_count > 0 else 0.0
            
            updated_plan.update({
                "tasks_count": tasks_count,
                "completed_tasks": completed_tasks,
                "progress": progress,
            })
        except Exception as e:
            logger.warning(f"Failed to get enhanced stats for approved plan {plan_id}: {e}")
            updated_plan.update({
                "tasks_count": 0,
                "completed_tasks": 0,
                "progress": 0.0,
            })

        return ResearchPlanResponse(**updated_plan)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SIMPLIFIED RESEARCH EXECUTION ENDPOINT
# =============================================================================

@v2_router.post("/topics/{topic_id}/execute", response_model=ResearchExecutionResponse)
async def execute_research_task(
    request: ExecuteResearchRequest,
    topic_id: str = Path(..., description="Topic ID"),
    db=Depends(get_database),
):
    """Execute a research task with simplified parameters."""
    try:
        # Import depth configuration
        from research_depth_config import get_depth_config
        
        # 1. Fetch topic details
        topic = await db.get_research_topic(topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Research topic not found")
        
        # 2. Get approved research plan for this topic
        plans = await db.get_research_plans(topic_id)
        approved_plan = next((p for p in plans if p.get("plan_approved", False)), None)
        logger.info(f"Approved plan found: {plans}")
        if not approved_plan:
            raise HTTPException(
                status_code=400, 
                detail="No approved research plan found for this topic. Please create and approve a research plan first."
            )
        
        # 3. Apply depth configuration
        try:
            depth_config = get_depth_config(request.depth)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # 4. Construct research context with all necessary information
        research_context = {
            "topic_id": topic_id,
            "topic_name": topic.get("name", ""),
            "topic_description": topic.get("description", ""),
            "plan_id": approved_plan.get("id", ""),
            "research_plan": approved_plan.get("plan_structure", {}),
            "task_type": request.task_type,
            "depth": request.depth
        }
        
        # 5. For now, return a basic execution response without actual execution
        # TODO: Implement actual research execution when needed
        execution_id = str(uuid4())
        
        # 6. Extract research questions from plan structure
        plan_structure = approved_plan.get("plan_structure", {})
        research_questions = []
        if isinstance(plan_structure, dict):
            research_questions = plan_structure.get("questions", [])
        
        # 7. Return execution response
        return ResearchExecutionResponse(
            execution_id=execution_id,
            topic_name=topic.get("name", ""),
            research_questions=research_questions,
            task_type=request.task_type,
            depth=request.depth,
            estimated_cost=depth_config["estimated_cost"],
            estimated_duration=depth_config["estimated_duration"],
            status="initiated",
            progress_url=f"/v2/executions/{execution_id}/progress"
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error executing research task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ENHANCED STATISTICS ENDPOINTS  
# =============================================================================

@v2_router.get("/topics/{topic_id}/stats", response_model=TopicStats)
async def get_topic_stats(
    topic_id: str = Path(..., description="Topic ID"),
    db=Depends(get_database),
):
    """Get topic statistics."""
    try:
        # First check if topic exists
        existing_topic = await db.get_research_topic(topic_id)
        if not existing_topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        # Calculate statistics using database client
        plans = await db.get_research_plans(topic_id)
        plans_count = len(plans) if plans else 0
        
        # Aggregate tasks across all plans
        tasks_count = 0
        total_cost = 0.0
        completed_tasks = 0
        
        for plan in (plans or []):
            try:
                tasks = await db.get_tasks(plan["id"])
                task_list = tasks if tasks else []
                tasks_count += len(task_list)
                completed_tasks += len([t for t in task_list if t.get("status") == "completed"])
                total_cost += sum(t.get("actual_cost", 0.0) for t in task_list)
            except Exception as e:
                logger.warning(f"Failed to get tasks for plan {plan['id']}: {e}")
        
        completion_rate = (completed_tasks / tasks_count * 100) if tasks_count > 0 else 0.0
        
        stats = {
            "plans_count": plans_count,
            "tasks_count": tasks_count,
            "total_cost": total_cost,
            "completion_rate": completion_rate
        }

        return TopicStats(**stats)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v2_router.get("/plans/{plan_id}/stats", response_model=PlanStats)
async def get_plan_stats(
    plan_id: str = Path(..., description="Plan ID"),
    db=Depends(get_database),
):
    """Get plan statistics."""
    try:
        # First check if plan exists
        existing_plan = await db.get_research_plan(plan_id)
        if not existing_plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        # Calculate statistics using database client
        tasks = await db.get_tasks(plan_id)
        tasks_count = len(tasks) if tasks else 0
        completed_tasks = len([t for t in (tasks or []) if t.get("status") == "completed"])
        total_cost = sum(t.get("actual_cost", 0.0) for t in (tasks or []))
        progress = (completed_tasks / tasks_count * 100) if tasks_count > 0 else 0.0
        
        stats = {
            "tasks_count": tasks_count,
            "completed_tasks": completed_tasks,
            "total_cost": total_cost,
            "progress": progress
        }

        return PlanStats(**stats)

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
        # First check if project exists
        existing_project = await db.get_project(project_id)
        if not existing_project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Calculate statistics using database client
        topics = await db.get_research_topics(project_id=project_id)
        topics_count = len(topics) if topics else 0
        
        # Aggregate plans and tasks across all topics
        plans_count = 0
        tasks_count = 0
        total_cost = 0.0
        completed_tasks = 0
        
        for topic in (topics or []):
            try:
                plans = await db.get_research_plans(topic["id"])
                plans_count += len(plans) if plans else 0
                
                for plan in (plans or []):
                    try:
                        tasks = await db.get_tasks(plan["id"])
                        task_list = tasks if tasks else []
                        tasks_count += len(task_list)
                        completed_tasks += len([t for t in task_list if t.get("status") == "completed"])
                        total_cost += sum(t.get("actual_cost", 0.0) for t in task_list)
                    except Exception as e:
                        logger.warning(f"Failed to get tasks for plan {plan['id']}: {e}")
            except Exception as e:
                logger.warning(f"Failed to get plans for topic {topic['id']}: {e}")
        
        completion_rate = (completed_tasks / tasks_count * 100) if tasks_count > 0 else 0.0
        
        stats = {
            "topics_count": topics_count,
            "plans_count": plans_count,
            "tasks_count": tasks_count,
            "total_cost": total_cost,
            "completion_rate": completion_rate
        }

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


# =============================================================================
# EXECUTION PROGRESS ENDPOINT
# =============================================================================

@v2_router.get("/executions/{execution_id}/progress")
async def get_execution_progress(
    execution_id: str = Path(..., description="Execution ID"),
    db=Depends(get_database),
):
    """Get progress information for a research execution."""
    try:
        # For now, return a simple progress structure
        # In a full implementation, this would track actual progress
        return {
            "execution_id": execution_id,
            "status": "in_progress",
            "progress_percentage": 0,
            "current_stage": "initializing",
            "stages": [
                "initializing",
                "planning", 
                "literature_search",
                "screening",
                "synthesis",
                "writing",
                "completed"
            ],
            "estimated_time_remaining": "unknown",
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting execution progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))
