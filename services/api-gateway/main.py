#!/usr/bin/env python3
"""
Containerized API Gateway Service for Eunice Research Platform

This service provides a unified REST API interface that routes requests to appropriate 
research agents via the MCP (Message Control Protocol) server. It's designed to run 
as a containerized microservice in Phase 3 architecture.

Key Features:
- REST API endpoints for all research operations
- MCP p            
            return AcademicSearchResponse(
                papers=papers,
                total_results=len(papers),
                query=request.query,
                execution_time=None,
                sources=["literature_agent"]
            )tocol integration for agent communication
- Health checks and monitoring
- Graceful shutdown handling
- Production-ready configuration
"""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from config import Config
from mcp_client import MCPClient
from models import (
    APIRequest, APIResponse, LiteratureSearchRequest, ResearchRequest,
    TaskStatusResponse, AcademicSearchRequest, AcademicSearchResponse,
    AcademicPaper, DataAnalysisRequest, ProjectCreateRequest, ProjectResponse
)

# Import database manager for direct read access
from src.database.core.manager import HierarchicalDatabaseManager

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL.upper()),
    format=Config.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/api-gateway.log') if Config.LOG_LEVEL.upper() == 'DEBUG' else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global MCP client instance
mcp_client = None

# Global database manager for direct read access
database_manager = None


def get_database():
    """Get database manager for direct read operations."""
    global database_manager
    if database_manager is None:
        try:
            # Initialize database manager for read operations
            database_manager = HierarchicalDatabaseManager()
        except Exception as e:
            logger.error(f"Failed to initialize database manager: {e}")
            raise HTTPException(status_code=503, detail="Database not available")
    return database_manager


class APIGateway:
    """
    Containerized API Gateway for Phase 3 microservices architecture.
    
    Provides unified REST interface and routes requests to research agents
    via the MCP server using WebSocket communication.
    """
    
    def __init__(self):
        self.mcp_client: Optional[MCPClient] = None
        self.active_requests: Dict[str, Dict[str, Any]] = {}
        
    async def initialize(self) -> bool:
        """Initialize the API Gateway and connect to MCP server."""
        try:
            logger.info("Initializing API Gateway...")
            
            # Validate configuration
            Config.validate_config()
            
            # Initialize MCP client
            mcp_config = Config.get_mcp_config()
            self.mcp_client = MCPClient(
                host=mcp_config["host"],
                port=mcp_config["port"]
            )
            
            # Connect to MCP server with retries
            for attempt in range(mcp_config["retry_attempts"]):
                try:
                    if await self.mcp_client.connect():
                        logger.info(f"API Gateway connected to MCP server at {mcp_config['url']}")
                        return True
                    else:
                        logger.warning(f"Connection attempt {attempt + 1} failed")
                        if attempt < mcp_config["retry_attempts"] - 1:
                            await asyncio.sleep(mcp_config["retry_delay"])
                except Exception as e:
                    logger.error(f"Connection attempt {attempt + 1} error: {e}")
                    if attempt < mcp_config["retry_attempts"] - 1:
                        await asyncio.sleep(mcp_config["retry_delay"])
            
            logger.error("Failed to connect to MCP server after all attempts")
            return False
            
        except Exception as e:
            logger.error(f"Error initializing API Gateway: {e}")
            return False
    
    async def shutdown(self):
        """Cleanup resources on shutdown."""
        try:
            logger.info("Shutting down API Gateway...")
            if self.mcp_client:
                await self.mcp_client.disconnect()
            logger.info("API Gateway shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for the API Gateway service."""
        health_status = {
            "service": "api-gateway",
            "status": "healthy",
            "timestamp": None,
            "version": Config.API_VERSION,
            "dependencies": {}
        }
        
        try:
            from datetime import datetime
            health_status["timestamp"] = datetime.utcnow().isoformat()
            
            # Check MCP server connection
            if self.mcp_client and self.mcp_client.is_connected:
                health_status["dependencies"]["mcp_server"] = "connected"
            else:
                health_status["dependencies"]["mcp_server"] = "disconnected"
                health_status["status"] = "degraded"
            
            # Add more dependency checks as needed
            health_status["dependencies"]["database"] = "not_implemented"
            health_status["dependencies"]["redis"] = "not_implemented"
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
            return health_status
    
    async def handle_literature_search(self, request: LiteratureSearchRequest) -> APIResponse:
        """Route literature search request to Literature Agent via MCP."""
        try:
            if not self.mcp_client or not self.mcp_client.is_connected:
                raise HTTPException(status_code=503, detail="MCP server not available")
            
            # Create research action for literature search
            task_data = {
                "task_id": request.request_id,
                "context_id": f"literature_search_{request.request_id}",
                "agent_type": "literature",
                "action": "search_literature",
                "payload": {
                    "query": request.query,
                    "max_results": request.max_results,
                    "include_abstracts": request.include_abstracts,
                    "date_range": request.date_range
                },
                "priority": "normal",
                "timeout": 300
            }
            
            # Submit task to MCP server
            success = await self.mcp_client.send_research_action(task_data)
            
            if success:
                # Track the request
                self.active_requests[request.request_id] = {
                    "status": "submitted",
                    "agent_type": "literature",
                    "action": "search_literature"
                }
                
                return APIResponse(
                    success=True,
                    request_id=request.request_id,
                    data={"task_id": request.request_id, "status": "submitted"}
                )
            else:
                raise HTTPException(status_code=500, detail="Failed to submit task to MCP server")
                
        except Exception as e:
            logger.error(f"Error handling literature search: {e}")
            return APIResponse(
                success=False,
                request_id=request.request_id,
                error=str(e)
            )
    
    async def handle_research_task(self, request: ResearchRequest) -> APIResponse:
        """Route research task to appropriate agent via MCP."""
        try:
            if not self.mcp_client or not self.mcp_client.is_connected:
                raise HTTPException(status_code=503, detail="MCP server not available")
            
            # Create research action
            task_data = {
                "task_id": request.request_id,
                "context_id": f"research_task_{request.request_id}",
                "agent_type": request.agent_type,
                "action": request.action,
                "payload": request.payload,
                "priority": request.priority,
                "timeout": request.timeout or 300
            }
            
            # Submit task to MCP server
            success = await self.mcp_client.send_research_action(task_data)
            
            if success:
                # Track the request
                self.active_requests[request.request_id] = {
                    "status": "submitted",
                    "agent_type": request.agent_type,
                    "action": request.action
                }
                
                return APIResponse(
                    success=True,
                    request_id=request.request_id,
                    data={"task_id": request.request_id, "status": "submitted"}
                )
            else:
                raise HTTPException(status_code=500, detail="Failed to submit task to MCP server")
                
        except Exception as e:
            logger.error(f"Error handling research task: {e}")
            return APIResponse(
                success=False,
                request_id=request.request_id,
                error=str(e)
            )
    
    async def get_task_status(self, task_id: str) -> TaskStatusResponse:
        """Get the status of a task from MCP server."""
        try:
            if not self.mcp_client or not self.mcp_client.is_connected:
                raise HTTPException(status_code=503, detail="MCP server not available")
            
            # Get status from MCP server
            status_data = await self.mcp_client.get_task_status(task_id)
            
            if status_data:
                return TaskStatusResponse(
                    success=True,
                    request_id=task_id,
                    task_id=task_id,
                    status=status_data.get("status", "unknown"),
                    data={
                        "result": status_data.get("result"),
                        "error": status_data.get("error")
                    }
                )
            else:
                return TaskStatusResponse(
                    success=False,
                    request_id=task_id,
                    task_id=task_id,
                    status="unknown",
                    error="Task not found"
                )
                
        except Exception as e:
            logger.error(f"Error getting task status: {e}")
            return TaskStatusResponse(
                success=False,
                request_id=task_id,
                task_id=task_id,
                status="error",
                error=str(e)
            )


# Global gateway instance
gateway = APIGateway()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan (startup and shutdown)."""
    # Startup
    logger.info("Starting API Gateway service...")
    success = await gateway.initialize()
    if not success:
        logger.error("Failed to initialize API Gateway")
        # Continue anyway for health checks
    
    yield
    
    # Shutdown
    await gateway.shutdown()


# Create FastAPI application
app = FastAPI(
    title=Config.API_TITLE,
    description=Config.API_DESCRIPTION,
    version=Config.API_VERSION,
    docs_url=Config.DOCS_URL,
    redoc_url=Config.REDOC_URL,
    lifespan=lifespan
)

# Configure CORS
cors_config = Config.get_cors_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_config["allow_origins"],
    allow_credentials=cors_config["allow_credentials"],
    allow_methods=cors_config["allow_methods"],
    allow_headers=cors_config["allow_headers"]
)


# API Routes
@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return await gateway.health_check()


@app.get("/status")
async def get_status():
    """Get detailed service status."""
    health = await gateway.health_check()
    return {
        "service": health["service"],
        "status": health["status"],
        "version": health["version"],
        "dependencies": health["dependencies"],
        "active_requests": len(gateway.active_requests)
    }


@app.post("/literature/search", response_model=APIResponse)
async def literature_search(request: LiteratureSearchRequest):
    """Search academic literature via Literature Agent."""
    return await gateway.handle_literature_search(request)


@app.post("/academic/search", response_model=AcademicSearchResponse)
async def academic_search(request: AcademicSearchRequest):
    """
    Comprehensive academic search across multiple databases.
    
    This endpoint provides enhanced academic search functionality similar to 
    the existing academic_search_api.py but adapted for containerized deployment.
    """
    try:
        # Validate that at least one source is selected
        if not (request.include_pubmed or request.include_arxiv or request.include_semantic_scholar):
            raise HTTPException(
                status_code=400, 
                detail="At least one search source must be enabled"
            )

        # Create a literature search request for MCP
        literature_request = LiteratureSearchRequest(
            query=request.query,
            max_results=request.max_results_per_source,
            include_abstracts=True,
            date_range=None  # Could be extended in future
        )
        
        # Execute search via MCP
        mcp_response = await gateway.handle_literature_search(literature_request)
        
        # Convert MCP response to academic search format
        if mcp_response.success and mcp_response.data:
            # Extract papers from MCP response
            papers_data = mcp_response.data.get("papers", []) if mcp_response.data else []
            
            # Convert to AcademicPaper objects  
            papers = []
            for paper_data in papers_data:
                if isinstance(paper_data, dict):
                    paper = AcademicPaper(
                        title=paper_data.get("title", "Untitled"),
                        url=paper_data.get("url", ""),
                        content=paper_data.get("abstract", ""),
                        source=paper_data.get("database_source", "literature_agent"),
                        type="academic_paper",
                        link_type=paper_data.get("link_type", ""),
                        relevance_score=paper_data.get("relevance_score", 0.0),
                        metadata=paper_data.get("metadata", {})
                    )
                    papers.append(paper)

            return AcademicSearchResponse(
                papers=papers,
                total_results=len(papers),
                query=request.query,
                execution_time=None,
                sources=["literature_agent"]
            )
        else:
            # Handle failure case
            return AcademicSearchResponse(
                papers=[],
                total_results=0,
                query=request.query,
                execution_time=None,
                sources=["literature_agent"]
            )
            
    except Exception as e:
        logger.error(f"Academic search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/research/tasks", response_model=APIResponse)
async def submit_research_task(request: ResearchRequest):
    """Submit research task to appropriate agent."""
    return await gateway.handle_research_task(request)


@app.get("/tasks/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Get the status of a research task."""
    return await gateway.get_task_status(task_id)


@app.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a research task."""
    # Implementation depends on MCP server capabilities
    return {"message": "Cancel functionality not yet implemented"}


# Enhanced endpoints matching Phase 2 functionality
@app.post("/data/analysis", response_model=APIResponse)
async def analyze_data(request: DataAnalysisRequest):
    """Analyze research data via Executor Agent."""
    try:
        # Create research task for data analysis
        research_request = ResearchRequest(
            agent_type="executor",
            action="analyze_data",
            payload={
                "dataset": request.dataset,
                "analysis_type": request.analysis_type,
                "parameters": request.parameters,
                "output_format": request.output_format
            },
            priority="normal",
            timeout=600  # Data analysis might take longer
        )
        
        return await gateway.handle_research_task(research_request)
        
    except Exception as e:
        logger.error(f"Data analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/status")
async def get_agents_status():
    """Get status of all registered agents via MCP server."""
    try:
        if not gateway.mcp_client or not gateway.mcp_client.is_connected:
            raise HTTPException(status_code=503, detail="MCP server not available")
        
        # Get server stats which includes agent information
        stats = await gateway.mcp_client.get_server_stats()
        
        return {
            "success": True,
            "agents": stats or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/capabilities")
async def get_agent_capabilities():
    """Get capabilities of all registered agents."""
    # Static capabilities mapping for Phase 3
    capabilities = {
        "literature": ["search", "retrieve", "summarize", "extract_metadata"],
        "planning": ["plan", "coordinate", "optimize", "strategy"],
        "executor": ["execute", "analyze", "process", "compute"],
        "memory": ["store", "retrieve", "search", "organize"],
        "screening": ["filter", "classify", "score", "prioritize"],
        "synthesis": ["synthesize", "summarize", "integrate", "analyze"],
        "writer": ["write", "format", "structure", "edit"],
        "research_manager": ["coordinate", "manage", "orchestrate", "supervise"]
    }
    
    return {
        "success": True,
        "capabilities": capabilities,
        "total_agents": len(capabilities)
    }


# Queue-based endpoints (future extension point)
@app.post("/queue/literature/search")
async def queue_literature_search(request: LiteratureSearchRequest):
    """Submit literature search to task queue (placeholder for Phase 3 queue system)."""
    # For now, process immediately via MCP
    result = await gateway.handle_literature_search(request)
    
    return {
        "success": result.success,
        "job_id": request.request_id,
        "request_id": request.request_id,
        "status": "completed" if result.success else "failed",
        "message": "Literature search processed via MCP",
        "result": result.data if result.success else result.error
    }


@app.post("/queue/research/planning")
async def queue_research_planning(request: ResearchRequest):
    """Submit research planning to task queue."""
    # Ensure it's a planning request
    if request.agent_type != "planning":
        request.agent_type = "planning"
        request.action = "create_research_plan"
    
    result = await gateway.handle_research_task(request)
    
    return {
        "success": result.success,
        "job_id": request.request_id,
        "request_id": request.request_id,
        "status": "completed" if result.success else "failed",
        "message": "Research planning processed via MCP",
        "result": result.data if result.success else result.error
    }


@app.post("/queue/data/analysis")
async def queue_data_analysis(request: DataAnalysisRequest):
    """Submit data analysis to task queue."""
    result = await analyze_data(request)
    
    return {
        "success": result.success,
        "job_id": request.request_id,
        "request_id": request.request_id,
        "status": "completed" if result.success else "failed",
        "message": "Data analysis processed via MCP",
        "result": result.data if result.success else result.error
    }


@app.get("/metrics")
async def get_metrics():
    """Get service metrics for monitoring."""
    return {
        "active_requests": len(gateway.active_requests),
        "mcp_connected": gateway.mcp_client.is_connected if gateway.mcp_client else False,
        "service": "api-gateway",
        "version": Config.API_VERSION
    }


# Project Management Endpoints - Hybrid Architecture Pattern
# Per Architecture Documentation:
# - READ operations: Direct database access for performance
# - WRITE operations: Via dedicated database agent for consistency and orchestration

@app.post("/projects", response_model=ProjectResponse)
async def create_project(request: ProjectCreateRequest):
    """Create a new project via MCP server (WRITE operation)."""
    try:
        # Create database write task via dedicated database agent (per architecture)
        research_request = ResearchRequest(
            agent_type="database_agent",
            action="create_project",
            payload={
                "name": request.name,
                "description": request.description,
                "metadata": request.metadata or {}
            },
            priority="normal",
            timeout=300
        )
        
        mcp_response = await gateway.handle_research_task(research_request)
        
        if mcp_response.success and mcp_response.data:
            # For now, return a mock project response since we need the database integration
            # In a full implementation, this would extract the project from MCP response
            from datetime import datetime
            from uuid import uuid4
            
            project_id = str(uuid4())
            now = datetime.utcnow()
            
            return ProjectResponse(
                id=project_id,
                name=request.name,
                description=request.description,
                status="active",
                created_at=now.isoformat(),
                updated_at=now.isoformat(),
                metadata=request.metadata
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to create project via MCP")
            
    except Exception as e:
        logger.error(f"Project creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/projects")
async def list_projects(
    status: Optional[str] = Query(None, description="Filter by project status"),
    limit: Optional[int] = Query(None, description="Limit number of results")
):
    """List all projects via direct database access (READ operation)."""
    try:
        db = get_database()
        projects = db.get_projects(status_filter=status, limit=limit)
        return [ProjectResponse(**project) for project in projects]
        
    except Exception as e:
        logger.error(f"Project listing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/projects/{project_id}", response_model=ProjectResponse) 
async def get_project(project_id: str):
    """Get a specific project via direct database access (READ operation)."""
    try:
        db = get_database()
        project = db.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return ProjectResponse(**project)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Project retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, request: ProjectCreateRequest):
    """Update a project via MCP server (WRITE operation)."""
    try:
        # Create database write task via dedicated database agent (per architecture)
        research_request = ResearchRequest(
            agent_type="database_agent", 
            action="update_project",
            payload={
                "project_id": project_id,
                "name": request.name,
                "description": request.description,
                "metadata": request.metadata or {}
            },
            priority="normal",
            timeout=300
        )
        
        mcp_response = await gateway.handle_research_task(research_request)
        
        if mcp_response.success:
            # Return updated project from database
            db = get_database()
            project = db.get_project(project_id)
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
            return ProjectResponse(**project)
        else:
            raise HTTPException(status_code=500, detail="Failed to update project via MCP")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Project update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project via MCP server (WRITE operation)."""
    try:
        # Create database write task via dedicated database agent (per architecture)
        research_request = ResearchRequest(
            agent_type="database_agent",
            action="delete_project", 
            payload={"project_id": project_id},
            priority="normal",
            timeout=300
        )
        
        mcp_response = await gateway.handle_research_task(research_request)
        
        if mcp_response.success:
            return {"message": "Project deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete project via MCP")
            
    except Exception as e:
        logger.error(f"Project deletion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Signal handlers for graceful shutdown
def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


async def main():
    """Main entry point for the containerized API Gateway service."""
    try:
        logger.info(f"Starting API Gateway service on {Config.HOST}:{Config.PORT}")
        
        # Create uvicorn server configuration
        server_config = Config.get_server_config()
        config = uvicorn.Config(
            app,
            host=server_config["host"],
            port=server_config["port"],
            log_level=server_config["log_level"],
            access_log=server_config["access_log"]
        )
        
        # Start the server
        server = uvicorn.Server(config)
        await server.serve()
        
    except Exception as e:
        logger.error(f"API Gateway service error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("API Gateway service stopped by user")
    except Exception as e:
        logger.error(f"Failed to start API Gateway service: {e}")
        sys.exit(1)
