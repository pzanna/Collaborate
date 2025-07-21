#!/usr/bin/env python3
"""
FastAPI Web Server for Eunice AI Platform
Provides REST API and WebSocket endpoints for the web UI
"""

import os
import sys
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, AsyncGenerator, Any
from contextlib import asynccontextmanager

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Import existing Eunice components
from src.config.config_manager import ConfigManager
from src.storage.hierarchical_database import HierarchicalDatabaseManager
from src.core.ai_client_manager import AIClientManager
from src.core.streaming_coordinator import StreamingResponseCoordinator
from src.core.research_manager import ResearchManager
from src.core.context_manager import ContextManager
from src.models.data_models import Project
from src.utils.export_manager import ExportManager
from src.utils.id_utils import generate_timestamped_id, generate_task_name
from src.utils.error_handler import (
    ErrorHandler, 
    EuniceError,
    format_error_for_user, 
    APIError
)
from src.mcp.client import MCPClient
from src.api.hierarchical_research_api import hierarchical_router
from functools import wraps
import logging

logger = logging.getLogger(__name__)

def handle_api_errors(func):
    """Decorator for consistent API error handling."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except EuniceError as e:
            raise HTTPException(status_code=400, detail=format_error_for_user(e))
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    return wrapper



# Pydantic models for API requests/responses
class ProjectCreate(BaseModel):
    name: str
    description: str = ""

class ResearchRequest(BaseModel):
    project_id: str  # New field for project association
    query: str
    name: Optional[str] = None  # Optional human-readable task name
    research_mode: str = "comprehensive"  # comprehensive, quick, deep
    max_results: int = 10
    
class ResearchTaskResponse(BaseModel):
    task_id: str
    project_id: str  # New field for project association
    query: str
    name: str  # Human-readable task name
    status: str
    stage: str  # Current stage of research
    created_at: str
    updated_at: str
    progress: float = 0.0
    estimated_cost: float = 0.0
    actual_cost: float = 0.0
    results: Optional[Dict[str, Any]] = None

class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    created_at: str
    updated_at: str
    research_task_count: int = 0  # New field for research task count


# Standard response models
class SuccessResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None

class BulkOperationResponse(BaseModel):
    success: bool
    processed: int
    failed: int
    errors: List[str] = []

# Pagination support
class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="Page number (starts from 1)")
    limit: int = Field(default=50, ge=1, le=1000, description="Items per page")
    sort_by: Optional[str] = Field(default=None, description="Field to sort by")
    sort_order: str = Field(default="asc", pattern="^(asc|desc)$", description="Sort order")

class PaginatedResponse(BaseModel):
    data: List[Any]
    pagination: Dict[str, Any] = Field(description="Pagination metadata")
    total: int
    page: int
    limit: int
    pages: int

# Filtering support
class FilterParams(BaseModel):
    created_after: Optional[str] = Field(default=None, description="Filter by creation date (ISO format)")
    created_before: Optional[str] = Field(default=None, description="Filter by creation date (ISO format)")
    status: Optional[str] = Field(default=None, description="Filter by status")
    search: Optional[str] = Field(default=None, description="Search query")

# Bulk operations
class BulkDeleteRequest(BaseModel):
    ids: List[str] = Field(description="List of IDs to delete")

class BulkUpdateRequest(BaseModel):
    ids: List[str] = Field(description="List of IDs to update")
    updates: Dict[str, Any] = Field(description="Updates to apply")

# API versioning
class APIVersionInfo(BaseModel):
    version: str
    supported_versions: List[str]
    deprecated_versions: List[str]
    migration_guide_url: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    database: Dict
    ai_providers: Dict
    research_system: Dict
    mcp_server: Dict
    errors: Dict


# Global state
config_manager: Optional[ConfigManager] = None
db_manager: Optional[HierarchicalDatabaseManager] = None  # Use hierarchical DB manager
ai_manager: Optional[AIClientManager] = None
streaming_coordinator: Optional[StreamingResponseCoordinator] = None
research_manager: Optional[ResearchManager] = None
context_manager: Optional[ContextManager] = None
mcp_client: Optional[MCPClient] = None
export_manager: Optional[ExportManager] = None


# WebSocket manager for real-time connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.research_connections: Dict[str, List[WebSocket]] = {}

    async def connect_research(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        self.active_connections.append(websocket)
        
        if task_id not in self.research_connections:
            self.research_connections[task_id] = []
        self.research_connections[task_id].append(websocket)

    def disconnect_research(self, websocket: WebSocket, task_id: str):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        if task_id in self.research_connections:
            if websocket in self.research_connections[task_id]:
                self.research_connections[task_id].remove(websocket)

    async def send_to_research(self, task_id: str, message: dict):
        if task_id in self.research_connections:
            for connection in self.research_connections[task_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    # Remove dead connections
                    self.research_connections[task_id].remove(connection)


# Initialize connection manager
manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global config_manager, db_manager, ai_manager, streaming_coordinator, research_manager, context_manager, mcp_client, export_manager
    
    print("🚀 Initializing Eunice Web Server...")
    
    # Initialize components (same as CLI)
    config_manager = ConfigManager()
    
    # Set up logging first
    config_manager.setup_logging()
    
    db_manager = HierarchicalDatabaseManager(config_manager.config.storage.database_path)
    export_manager = ExportManager(config_manager.config.storage.export_path)
    
    # Initialize context manager
    context_manager = ContextManager(config_manager)
    await context_manager.initialize()
    print("✓ Context manager initialized")
    
    # Initialize MCP client
    try:
        mcp_config = config_manager.get_mcp_config()
        mcp_client = MCPClient(
            host=mcp_config.get('host', '127.0.0.1'),
            port=mcp_config.get('port', 9000)
        )
        
        # Try to connect to MCP server
        if await mcp_client.connect():
            print("✓ MCP client connected successfully")
            
            # Initialize research manager with MCP client and database
            research_manager = ResearchManager(config_manager, db_manager)
            await research_manager.initialize(mcp_client)
            
            # Register completion callback to notify WebSocket clients
            async def research_completion_callback(completion_data):
                """Callback to notify WebSocket clients when research completes."""
                task_id = completion_data.get('task_id')
                if task_id:
                    try:
                        # Notify WebSocket clients about completion
                        await manager.send_to_research(task_id, {
                            'type': 'research_completed',
                            'task_id': task_id,
                            'success': completion_data.get('success', False),
                            'results': completion_data.get('results', {}),
                            'duration': completion_data.get('duration', 0),
                            'completed_stages': completion_data.get('completed_stages', []),
                            'failed_stages': completion_data.get('failed_stages', [])
                        })
                        print(f"✓ Notified WebSocket clients about completion of task {task_id}")
                    except Exception as e:
                        print(f"⚠ Failed to notify WebSocket clients: {e}")
            
            research_manager.register_completion_callback(research_completion_callback)
            print("✓ Research manager initialized with completion callbacks")
        else:
            print("⚠ MCP server not available, research features disabled")
            mcp_client = None
            research_manager = None
            
    except Exception as e:
        print(f"⚠ Failed to initialize MCP client: {e}")
        mcp_client = None
        research_manager = None
    
    try:
        ai_manager = AIClientManager(config_manager)
        available_providers = ai_manager.get_available_providers()
        
        # Initialize streaming coordinator
        streaming_coordinator = StreamingResponseCoordinator(
            config_manager=config_manager,
            ai_manager=ai_manager,
            db_manager=db_manager
        )
        
        print(f"✓ AI providers available: {', '.join(available_providers)}")
        print("✓ Real-time streaming enabled")
    except Exception as e:
        print(f"⚠ AI providers not available: {e}")
        ai_manager = None
        streaming_coordinator = None
    
    print("✓ Eunice Web Server initialized successfully!")
    
    yield
    
    # Cleanup on shutdown
    print("👋 Shutting down Eunice Web Server...")
    
    # Disconnect MCP client
    if mcp_client:
        await mcp_client.disconnect()
    
    # Cleanup research manager
    if research_manager:
        await research_manager.cleanup()
    
    # Cleanup context manager
    if context_manager:
        await context_manager.cleanup()


# Create FastAPI app with comprehensive documentation
app = FastAPI(
    title="Eunice Research Platform API",
    description="""
    ## Eunice Research Platform API
    
    A comprehensive REST API and WebSocket service for the Eunice AI Research Platform.
    
    ### Features
    - **Project Management**: Create and manage research projects
    - **Research Tasks**: Automated research task execution
    - **Hierarchical Research**: Complete topic-plan-task structure
    - **Search & Filtering**: Advanced search capabilities
    - **Bulk Operations**: Efficient batch processing
    
    ### API Structure
    - **Single Version**: Unified API v1.0.0 for consistency
    - **Comprehensive**: All features in one cohesive API
    
    ### Authentication
    Currently in development - all endpoints are public.
    """,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "Eunice Development Team",
        "url": "https://github.com/pzanna/Eunice"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    },
    servers=[
        {"url": "http://localhost:8000", "description": "Development server"},
        {"url": "https://api.eunice.ai", "description": "Production server"}
    ],
    tags_metadata=[
        {"name": "health", "description": "System health and status"},
        {"name": "projects", "description": "Project management operations"},
        {"name": "research", "description": "Research task management"},
        {"name": "tasks", "description": "Task monitoring and control"},
        {"name": "debug", "description": "Debug and development tools"},
        {"name": "v2-hierarchical", "description": "V2 Hierarchical Research API"},
        {"name": "websockets", "description": "Real-time WebSocket connections"}
    ]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include hierarchical research API router
app.include_router(hierarchical_router)

# Simple API version middleware (single version)
@app.middleware("http")
async def add_api_headers(request, call_next):
    """Add standard API headers to all responses."""
    response = await call_next(request)
    response.headers["X-API-Version"] = "1.0.0"
    return response

# =============================================================================
# EXCEPTION HANDLERS
# =============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions with standardized error format."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            success=False,
            error=exc.detail,
            details={
                "status_code": exc.status_code,
                "path": str(request.url.path),
                "method": request.method
            }
        ).dict()
    )

@app.exception_handler(ValueError)
async def value_error_handler(request, exc: ValueError):
    """Handle validation errors."""
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            success=False,
            error="Validation error",
            details={
                "message": str(exc),
                "path": str(request.url.path),
                "method": request.method
            }
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle unexpected errors."""
    import traceback
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            success=False,
            error="Internal server error",
            details={
                "type": type(exc).__name__,
                "path": str(request.url.path),
                "method": request.method,
                "traceback": traceback.format_exc() if app.debug else None
            }
        ).dict()
    )

# =============================================================================
# END EXCEPTION HANDLERS
# =============================================================================

# Request logging middleware
@app.middleware("http")
async def log_requests(request, call_next):
    """Log all API requests for monitoring and debugging."""
    import time
    start_time = time.time()
    
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Log the request
    print(f"API Request: {request.method} {request.url.path} - "
          f"Status: {response.status_code} - Time: {process_time:.3f}s")
    
    response.headers["X-Process-Time"] = str(process_time)
    return response


# API Version endpoint
@app.get("/api/version", response_model=APIVersionInfo, tags=["health"])
async def get_api_version():
    """Get API version information."""
    return APIVersionInfo(
        version="1.0.0",
        supported_versions=["1.0"],
        deprecated_versions=[],
        migration_guide_url="/docs"
    )


# Health endpoint
@app.get("/api/health", response_model=HealthResponse, tags=["health"])
async def get_health():
    """Get system health status."""
    try:
        # Check database
        db_status = {"status": "healthy", "tables": 0}
        try:
            # Simple DB check
            if db_manager:
                projects = db_manager.list_projects()
                db_status["tables"] = len(projects) if projects else 0
            else:
                db_status = {"status": "disabled", "reason": "Database manager not initialized"}
        except Exception as e:
            db_status = {"status": "error", "error": str(e)}
        
        # Check AI providers
        ai_status = {"status": "disabled", "providers": []}
        if ai_manager:
            try:
                providers = ai_manager.get_available_providers()
                ai_status = {"status": "healthy", "providers": providers}
            except Exception as e:
                ai_status = {"status": "error", "error": str(e)}
        
        # Check research system
        research_status = {"status": "disabled", "mcp_connected": False}
        if research_manager and mcp_client:
            try:
                research_status = {
                    "status": "healthy",
                    "mcp_connected": mcp_client.is_connected,
                    "active_tasks": len(research_manager.active_contexts)
                }
            except Exception as e:
                research_status = {"status": "error", "error": str(e)}
        
        # Check MCP server
        mcp_status = {"status": "offline", "connected": False}
        if mcp_client:
            try:
                # Get basic connection status
                connection_info = mcp_client.connection_status
                mcp_status.update({
                    "status": "healthy" if connection_info["connected"] else "offline",
                    "connected": connection_info["connected"],
                    "host": connection_info["host"],
                    "port": connection_info["port"],
                    "client_id": connection_info["client_id"],
                    "should_reconnect": connection_info["should_reconnect"]
                })
                
                # If connected, get server stats for more detailed health info
                if connection_info["connected"]:
                    try:
                        server_stats = await mcp_client.get_server_stats()
                        if server_stats:
                            mcp_status.update({
                                "server_stats": server_stats,
                                "detailed_health": "available"
                            })
                        else:
                            mcp_status["detailed_health"] = "unavailable"
                    except Exception as stats_e:
                        mcp_status["stats_error"] = str(stats_e)
                        mcp_status["detailed_health"] = "error"
                
            except Exception as e:
                mcp_status = {
                    "status": "error", 
                    "connected": False,
                    "error": str(e)
                }
        else:
            # MCP server is configured but not running/reachable
            mcp_config = config_manager.get_mcp_config() if config_manager else {}
            mcp_status = {
                "status": "offline",
                "connected": False,
                "reason": "MCP server not running or unreachable",
                "expected_host": mcp_config.get('host', '127.0.0.1'),
                "expected_port": mcp_config.get('port', 9000)
            }
        
        # Determine overall system status
        overall_status = "healthy"
        if (db_status.get("status") == "error" or 
            ai_status.get("status") == "error" or 
            research_status.get("status") == "error" or
            mcp_status.get("status") == "error"):
            overall_status = "degraded"
        
        return HealthResponse(
            status=overall_status,
            database=db_status,
            ai_providers=ai_status,
            research_system=research_status,
            mcp_server=mcp_status,
            errors={}
        )
    except Exception as e:
        return HealthResponse(
            status="error",
            database={"status": "error"},
            ai_providers={"status": "error"},
            research_system={"status": "error"},
            mcp_server={"status": "error"},
            errors={"general": str(e)}
        )


# Projects endpoints
@app.get("/api/projects", response_model=PaginatedResponse, tags=["projects"])
async def list_projects(
    pagination: PaginationParams = Depends(),
    filters: FilterParams = Depends()
):
    """Get all projects with pagination and filtering support."""
    try:
        # Get all projects (in a real implementation, this would be paginated at the DB level)
        all_projects = db_manager.list_projects() if db_manager else []
        
        # Count research tasks per project
        task_counts = {}
        for project in all_projects:
            if db_manager:
                task_counts[project['id']] = db_manager.get_research_task_count_by_project(project['id'])
            else:
                task_counts[project['id']] = 0
        
        # Apply filtering
        filtered_projects = all_projects
        if filters.search:
            filtered_projects = [p for p in filtered_projects 
                               if filters.search.lower() in p['name'].lower() 
                               or filters.search.lower() in p['description'].lower()]
        
        if filters.created_after:
            from datetime import datetime
            after_date = datetime.fromisoformat(filters.created_after.replace('Z', '+00:00'))
            filtered_projects = [p for p in filtered_projects if datetime.fromisoformat(p['created_at']) >= after_date]
        
        # Apply sorting
        if pagination.sort_by:
            from datetime import datetime
            reverse = pagination.sort_order == "desc"
            if pagination.sort_by == "name":
                filtered_projects.sort(key=lambda x: x['name'], reverse=reverse)
            elif pagination.sort_by == "created_at":
                filtered_projects.sort(key=lambda x: datetime.fromisoformat(x['created_at']), reverse=reverse)
        
        # Apply pagination
        total = len(filtered_projects)
        start_idx = (pagination.page - 1) * pagination.limit
        end_idx = start_idx + pagination.limit
        paginated_projects = filtered_projects[start_idx:end_idx]
        
        # Format response
        project_responses = [
            ProjectResponse(
                id=project['id'],
                name=project['name'],
                description=project['description'],
                created_at=project['created_at'],
                updated_at=project['updated_at'],
                research_task_count=task_counts.get(project['id'], 0)
            )
            for project in paginated_projects
        ]
        
        pages = (total + pagination.limit - 1) // pagination.limit
        
        return PaginatedResponse(
            data=project_responses,
            pagination={
                "page": pagination.page,
                "limit": pagination.limit,
                "total": total,
                "pages": pages,
                "has_next": pagination.page < pages,
                "has_prev": pagination.page > 1
            },
            total=total,
            page=pagination.page,
            limit=pagination.limit,
            pages=pages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/projects", response_model=ProjectResponse, tags=["projects"])
async def create_project(project: ProjectCreate):
    """Create a new project."""
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        new_project = Project(name=project.name, description=project.description)
        created_project = db_manager.create_project(new_project)
        
        if not created_project:
            raise HTTPException(status_code=400, detail="Failed to create project")
        
        return ProjectResponse(
            id=created_project['id'],
            name=created_project['name'],
            description=created_project.get('description', ''),
            created_at=created_project['created_at'],
            updated_at=created_project['updated_at'],
            research_task_count=0
        )
    except EuniceError as e:
        raise HTTPException(status_code=400, detail=format_error_for_user(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/projects/{project_id}", response_model=SuccessResponse)
async def delete_project(project_id: str):
    """Delete a project and all its associated research data."""
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        success = db_manager.delete_project(project_id)
        if not success:
            return SuccessResponse(success=False, message="Project not found or already deleted")
        
        return SuccessResponse(success=True, message="Project deleted successfully")
    except EuniceError as e:
        raise HTTPException(status_code=400, detail=format_error_for_user(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Research Task endpoints for projects
@app.get("/api/projects/{project_id}/research-tasks", response_model=List[ResearchTaskResponse])
async def list_project_research_tasks(project_id: str):
    """Get all research tasks for a specific project."""
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        research_tasks = db_manager.get_research_tasks_by_project(project_id)
        
        return [
            ResearchTaskResponse(
                task_id=task['id'],
                project_id=task['project_id'],
                query=task['query'],
                name=task['name'],
                status=task['status'],
                stage=task['stage'],
                created_at=task['created_at'],
                updated_at=task['updated_at'],
                progress=task['progress'],
                estimated_cost=task['estimated_cost'],
                actual_cost=task['actual_cost']
            )
            for task in research_tasks
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get research tasks: {str(e)}")


@app.get("/api/research-tasks", response_model=List[ResearchTaskResponse])
async def list_all_research_tasks(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100
):
    """Get research tasks with optional filters."""
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        research_tasks = db_manager.list_research_tasks(
            project_id=project_id,
            status_filter=status,
            limit=limit
        )
        
        return [
            ResearchTaskResponse(
                task_id=task['id'],
                project_id=task['project_id'],
                query=task['query'],
                name=task['name'],
                status=task['status'],
                stage=task['stage'],
                created_at=task['created_at'],
                updated_at=task['updated_at'],
                progress=task['progress'],
                estimated_cost=task['estimated_cost'],
                actual_cost=task['actual_cost']
            )
            for task in research_tasks
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get research tasks: {str(e)}")


# Research endpoints
@app.post("/api/research/start", response_model=ResearchTaskResponse)
async def start_research_task(request: ResearchRequest):
    """Start a new research task."""
    if not research_manager:
        raise HTTPException(status_code=503, detail="Research system not available")
    
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        # Generate task name if not provided
        task_name = generate_task_name(request.query, request.name)
        
        # Create options dict from request parameters
        options = {
            'research_mode': request.research_mode,
            'max_results': request.max_results,
            'project_id': request.project_id,  # Pass project_id in options
            'metadata': {}
        }
        
        # Create research task with proper parameters
        task_id, cost_info = await research_manager.start_research_task(
            query=request.query,
            user_id="web_user",  # Default user ID for web requests
            conversation_id="",  # No longer using conversations
            options=options
        )
        
        # Get task details from research manager
        task_context = research_manager.get_task_context(task_id)
        
        # Create database entry with hierarchical structure (topic → plan → task)
        task_data = {
            'id': task_id,
            'project_id': request.project_id,
            'query': request.query,
            'name': task_name,
            'status': "running",
            'stage': task_context.stage.value if task_context else "planning",
            'estimated_cost': task_context.estimated_cost if task_context else 0.0,
            'actual_cost': task_context.actual_cost if task_context else 0.0,
            'cost_approved': task_context.cost_approved if task_context else False,
            'single_agent_mode': task_context.single_agent_mode if task_context else False,
            'research_mode': request.research_mode,
            'max_results': request.max_results,
            'progress': 0.0,
            'metadata': {
                'created_via': 'web_api',
                'user_id': 'web_user'
            }
        }
        
        # Save to database with hierarchical structure (auto-creates topic and plan)
        created_task = db_manager.create_research_task_with_hierarchy(task_data, auto_create_topic=True)
        if not created_task:
            raise HTTPException(status_code=500, detail="Failed to save research task to database")
        
        return ResearchTaskResponse(
            task_id=task_id,
            project_id=request.project_id,
            query=request.query,
            name=task_name,
            status=created_task.get('status', 'running'),
            stage=created_task.get('stage', 'planning'),
            created_at=created_task.get('created_at'),
            updated_at=created_task.get('updated_at'),
            progress=created_task.get('progress', 0.0),
            estimated_cost=created_task.get('estimated_cost', 0.0),
            actual_cost=created_task.get('actual_cost', 0.0)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start research task: {str(e)}")


@app.get("/api/research/task/{task_id}", response_model=ResearchTaskResponse)
async def get_research_task(task_id: str):
    """Get status and results of a research task."""
    if not research_manager:
        raise HTTPException(status_code=503, detail="Research system not available")
    
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        # Try to get task from database first
        db_task = db_manager.get_research_task(task_id)
        if not db_task:
            raise HTTPException(status_code=404, detail="Research task not found")
        
        # Get current status from research manager if task is active
        task_context = research_manager.get_task_context(task_id)
        if task_context:
            # Update database with current progress
            db_task['status'] = "running" if task_context.stage.value in ["planning", "retrieval", "reasoning", "execution", "synthesis"] else task_context.stage.value
            db_task['stage'] = task_context.stage.value
            db_task['progress'] = research_manager.calculate_task_progress(task_id)
            db_task['actual_cost'] = task_context.actual_cost
            db_task['search_results'] = task_context.search_results
            db_task['reasoning_output'] = task_context.reasoning_output
            db_task['execution_results'] = task_context.execution_results
            db_task['synthesis'] = task_context.synthesis
            
            # Update database
            db_manager.update_research_task(db_task)
        
        # Prepare results
        results = None
        if db_task.get('stage') == "complete":
            results = {
                "search_results": db_task.get('search_results', []),
                "reasoning_output": db_task.get('reasoning_output'),
                "execution_results": db_task.get('execution_results', []),
                "synthesis": db_task.get('synthesis'),
                "metadata": db_task.get('metadata', {})
            }
        
        return ResearchTaskResponse(
            task_id=task_id,
            project_id=db_task['project_id'],
            query=db_task['query'],
            name=db_task['name'],
            status=db_task['status'],
            stage=db_task['stage'],
            created_at=db_task['created_at'],
            updated_at=db_task['updated_at'],
            progress=db_task.get('progress', 0.0),
            estimated_cost=db_task.get('estimated_cost', 0.0),
            actual_cost=db_task.get('actual_cost', 0.0),
            results=results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get research task: {str(e)}")


@app.delete("/api/research/task/{task_id}", response_model=SuccessResponse)
async def cancel_research_task(task_id: str):
    """Cancel a research task."""
    if not research_manager:
        raise HTTPException(status_code=503, detail="Research system not available")
    
    try:
        success = await research_manager.cancel_task(task_id)
        if not success:
            return SuccessResponse(success=False, message="Research task not found or already completed")
        
        return SuccessResponse(success=True, message="Research task cancelled successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel research task: {str(e)}")


# Research plan management endpoints

# Research Plan Compatibility API Endpoints
# These endpoints provide backward compatibility for the ResearchPlanViewer component
# while working with the new hierarchical research structure

class LegacyResearchPlanData(BaseModel):
    task_id: str
    research_plan: Optional[Dict[str, Any]] = None
    plan_approved: bool = False
    created_at: str
    updated_at: str

@app.get("/api/research/task/{task_id}/plan")
async def get_research_plan_for_task(task_id: str):
    """Get research plan data for a task (compatibility endpoint)."""
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        # Get the task
        task = db_manager.get_research_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Convert task to dict if it's not already
        task_dict = task.__dict__ if hasattr(task, '__dict__') else task
        
        # Check if task has planning stage completed and has plan data
        plan_data = None
        plan_approved = False
        
        # For tasks in the new hierarchical system, get plan from the associated plan
        if task_dict.get('plan_id'):
            try:
                plan = db_manager.get_research_plan(task_dict['plan_id'])
                if plan and plan.get('plan_structure'):
                    plan_structure = plan.get('plan_structure', {})
                    # Convert hierarchical plan to legacy format
                    # Support both legacy field names and new field names
                    plan_data = {
                        'raw_plan': plan_structure.get('raw_plan', ''),
                        'objectives': plan_structure.get('objectives', plan_structure.get('research_objectives', '')),
                        'key_areas': plan_structure.get('key_areas', plan_structure.get('methodology', '')),
                        'questions': plan_structure.get('questions', plan_structure.get('research_questions', '')),
                        'sources': plan_structure.get('sources', plan_structure.get('resources_needed', '')),
                        'outcomes': plan_structure.get('outcomes', plan_structure.get('expected_outcomes', ''))
                    }
                    plan_approved = plan.get('plan_approved', False)
            except Exception as e:
                print(f"Error getting hierarchical plan: {e}")
        
        # For legacy tasks, try to get plan data from the task directly
        if not plan_data and task_dict.get('research_plan'):
            plan_data = task_dict['research_plan']
            plan_approved = task_dict.get('plan_approved', False)
        
        # Check if planning stage is complete but waiting for approval
        if not plan_data and task_dict.get('stage') == "planning_complete":
            # Get the plan data from the research manager if available
            if research_manager:
                try:
                    context = research_manager.get_task_context(task_id)
                    if context and context.context_data.get('research_plan'):
                        plan_response = context.context_data['research_plan']
                        if plan_response and 'plan' in plan_response:
                            plan_data = plan_response['plan']
                            plan_approved = task_dict.get('status') != "waiting_approval"
                except Exception as e:
                    print(f"Error getting plan from research manager: {e}")
        
        return LegacyResearchPlanData(
            task_id=task_id,
            research_plan=plan_data,
            plan_approved=plan_approved,
            created_at=task_dict.get('created_at', datetime.now().isoformat()),
            updated_at=task_dict.get('updated_at', datetime.now().isoformat())
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get research plan: {str(e)}")

@app.put("/api/research/task/{task_id}/plan")
async def update_research_plan_for_task(task_id: str, request: Dict[str, Any]):
    """Update research plan data for a task (compatibility endpoint)."""
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        task = db_manager.get_research_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task_dict = task.__dict__ if hasattr(task, '__dict__') else task
        research_plan = request.get('research_plan', {})
        
        # For tasks in the new hierarchical system, update the associated plan
        if task_dict.get('plan_id'):
            try:
                plan_update_data = {
                    'plan_structure': research_plan,
                    'plan_approved': False  # Editing resets approval status
                }
                result = db_manager.update_research_plan(task_dict['plan_id'], plan_update_data)
                if result:
                    return {"success": True, "message": "Research plan updated"}
            except Exception as e:
                print(f"Failed to update hierarchical plan: {e}")
        
        # Fallback to legacy method
        success = db_manager.update_research_plan(task_id, research_plan)
        if success:
            return {"success": True, "message": "Research plan updated"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update research plan")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update research plan: {str(e)}")

@app.post("/api/research/task/{task_id}/plan/approve")
async def approve_research_plan_for_task(task_id: str, request: Dict[str, Any]):
    """Approve or reject research plan for a task (compatibility endpoint)."""
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        task = db_manager.get_research_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task_dict = task.__dict__ if hasattr(task, '__dict__') else task
        approved = request.get('approved', False)
        
        # Update task status based on approval
        if approved:
            # For tasks in the new hierarchical system
            if task_dict.get('plan_id'):
                try:
                    # Update plan approval status and set status to active
                    plan_update_data = {
                        'status': 'active',
                        'plan_approved': True
                    }
                    db_manager.update_research_plan(task_dict['plan_id'], plan_update_data)
                except Exception as e:
                    print(f"Failed to update hierarchical plan status: {e}")
            
            # Update task to proceed with research
            update_data = {
                'id': task_id,
                'status': 'running',
                'stage': 'retrieval',
                'plan_approved': True,
                **task_dict  # Include existing task data
            }
            db_manager.update_research_task(update_data)
            
            # Restart the research workflow if research manager is available
            if research_manager:
                try:
                    context = research_manager.get_task_context(task_id)
                    if context:
                        # Continue the research workflow
                        asyncio.create_task(research_manager._orchestrate_research_task(context))
                except Exception as e:
                    print(f"Failed to restart research workflow: {e}")
        else:
            # Plan rejected - mark plan as not approved and task as failed
            if task_dict.get('plan_id'):
                try:
                    # Update plan approval status
                    plan_update_data = {
                        'plan_approved': False
                    }
                    db_manager.update_research_plan(task_dict['plan_id'], plan_update_data)
                except Exception as e:
                    print(f"Failed to update hierarchical plan approval status: {e}")
            
            # Mark task as failed
            update_data = {
                'id': task_id,
                'status': 'failed',
                'stage': 'failed',
                'plan_approved': False,
                **task_dict  # Include existing task data
            }
            db_manager.update_research_task(update_data)
        
        return {"success": True, "approved": approved}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to approve research plan: {str(e)}")


# Phase 4: Task Viewer API Endpoints

class TaskResponse(BaseModel):
    task_id: str
    parent_id: Optional[str] = None
    agent_type: str
    status: str
    stage: str
    created_at: str
    updated_at: str
    content: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    dependencies: List[str] = []
    children: List[str] = []

class TaskGraphResponse(BaseModel):
    tasks: List[TaskResponse]
    connections: List[Dict[str, str]]
    statistics: Dict[str, Any]

class DebugPlanResponse(BaseModel):
    plan_id: str
    context_id: str
    prompt: str
    raw_response: str
    parsed_tasks: List[Dict[str, Any]]
    created_at: str
    execution_status: str
    modifications: List[Dict[str, Any]] = []

@app.get("/api/tasks/active", response_model=TaskGraphResponse)
async def get_active_tasks():
    """Get all active tasks with their dependencies and status."""
    if not mcp_client:
        raise HTTPException(status_code=503, detail="MCP server not available")
    
    try:
        # Get active tasks from MCP server
        tasks_data = await mcp_client.get_active_tasks()
        
        tasks = []
        connections = []
        
        for task_data in tasks_data.get('tasks', []):
            task = TaskResponse(
                task_id=task_data['task_id'],
                parent_id=task_data.get('parent_id'),
                agent_type=task_data['agent_type'],
                status=task_data['status'],
                stage=task_data.get('stage', 'unknown'),
                created_at=task_data['created_at'],
                updated_at=task_data['updated_at'],
                content=task_data.get('content', {}),
                metadata=task_data.get('metadata', {}),
                dependencies=task_data.get('dependencies', []),
                children=task_data.get('children', [])
            )
            tasks.append(task)
            
            # Build connections for graph visualization
            if task.parent_id:
                connections.append({
                    "from": task.parent_id,
                    "to": task.task_id,
                    "type": "parent-child"
                })
            
            for dep_id in task.dependencies:
                connections.append({
                    "from": dep_id,
                    "to": task.task_id,
                    "type": "dependency"
                })
        
        # Calculate statistics
        status_counts = {}
        agent_counts = {}
        for task in tasks:
            status_counts[task['status']] = status_counts.get(task['status'], 0) + 1
            agent_counts[task['agent_type']] = agent_counts.get(task['agent_type'], 0) + 1
        
        statistics = {
            "total_tasks": len(tasks),
            "status_breakdown": status_counts,
            "agent_breakdown": agent_counts,
            "connection_count": len(connections)
        }
        
        return TaskGraphResponse(
            tasks=tasks,
            connections=connections,
            statistics=statistics
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get active tasks: {str(e)}")

@app.get("/api/tasks/{task_id}", response_model=TaskResponse)
async def get_task_details(task_id: str):
    """Get detailed information about a specific task."""
    if not mcp_client:
        raise HTTPException(status_code=503, detail="MCP server not available")
    
    try:
        task_data = await mcp_client.get_task_details(task_id)
        
        if not task_data:
            # Return empty task response instead of error
            return TaskResponse(
                task_id=task_id,
                parent_id=None,
                agent_type="unknown",
                status="not_found",
                stage="unknown",
                created_at="",
                updated_at="",
                content={},
                metadata={},
                dependencies=[],
                children=[]
            )
        
        return TaskResponse(
            task_id=task_data['task_id'],
            parent_id=task_data.get('parent_id'),
            agent_type=task_data['agent_type'],
            status=task_data['status'],
            stage=task_data.get('stage', 'unknown'),
            created_at=task_data['created_at'],
            updated_at=task_data['updated_at'],
            content=task_data.get('content', {}),
            metadata=task_data.get('metadata', {}),
            dependencies=task_data.get('dependencies', []),
            children=task_data.get('children', [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task details: {str(e)}")

@app.post("/api/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    """Cancel a specific task."""
    if not mcp_client:
        raise HTTPException(status_code=503, detail="MCP server not available")
    
    try:
        success = await mcp_client.cancel_task(task_id)
        
        if not success:
            return {"success": False, "task_id": task_id, "message": "Task not found or cannot be cancelled"}
        
        return {"success": True, "task_id": task_id, "message": "Task cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel task: {str(e)}")

# Phase 4: Debug UI API Endpoints

@app.get("/api/debug/plans/latest", response_model=DebugPlanResponse)
async def get_latest_rm_plan(context_id: Optional[str] = None):
    """Get the latest RM AI plan for debugging."""
    if not research_manager:
        raise HTTPException(status_code=503, detail="Research manager not available")
    
    try:
        plan_data = await research_manager.get_latest_plan(context_id)
        
        if not plan_data:
            # Return an empty response instead of raising an error for better UI handling
            return DebugPlanResponse(
                plan_id="",
                context_id="",
                prompt="No plan data available",
                raw_response="",
                parsed_tasks=[],
                created_at="",
                execution_status="not_found"
            )
        
        return DebugPlanResponse(
            plan_id=plan_data['plan_id'],
            context_id=plan_data['context_id'],
            prompt=plan_data['prompt'],
            raw_response=plan_data['raw_response'],
            parsed_tasks=plan_data['parsed_tasks'],
            created_at=plan_data['created_at'],
            execution_status=plan_data['execution_status'],
            modifications=plan_data.get('modifications', [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get latest plan: {str(e)}")

@app.get("/api/debug/plans/{plan_id}", response_model=DebugPlanResponse)
async def get_rm_plan(plan_id: str):
    """Get a specific RM AI plan by ID."""
    if not research_manager:
        raise HTTPException(status_code=503, detail="Research manager not available")
    
    try:
        plan_data = await research_manager.get_plan(plan_id)
        
        if not plan_data:
            # Return an empty response instead of raising an error for better UI handling
            return DebugPlanResponse(
                plan_id=plan_id,
                context_id="",
                prompt="No plan data available",
                raw_response="",
                parsed_tasks=[],
                created_at="",
                execution_status="not_found"
            )
        
        return DebugPlanResponse(
            plan_id=plan_data['plan_id'],
            context_id=plan_data['context_id'],
            prompt=plan_data['prompt'],
            raw_response=plan_data['raw_response'],
            parsed_tasks=plan_data['parsed_tasks'],
            created_at=plan_data['created_at'],
            execution_status=plan_data['execution_status'],
            modifications=plan_data.get('modifications', [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get plan: {str(e)}")

@app.post("/api/debug/plans/{plan_id}/modify")
async def modify_rm_plan(plan_id: str, modifications: Dict[str, Any]):
    """Modify a specific RM AI plan."""
    if not research_manager:
        raise HTTPException(status_code=503, detail="Research manager not available")
    
    try:
        success = await research_manager.modify_plan(plan_id, modifications)
        
        if not success:
            # Return an empty response instead of raising an error for better UI handling
            return DebugPlanResponse(
                plan_id="",
                context_id="",
                prompt="No plan data available",
                raw_response="",
                parsed_tasks=[],
                created_at="",
                execution_status="not_found"
            )
        
        return {
            "success": True,
            "plan_id": plan_id,
            "modifications": modifications,
            "message": "Plan modified successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to modify plan: {str(e)}")

@app.get("/api/debug/plans")
async def list_rm_plans(context_id: Optional[str] = None, limit: int = 50):
    """List RM AI plans with optional context filtering."""
    if not research_manager:
        raise HTTPException(status_code=503, detail="Research manager not available")
    
    try:
        plans = await research_manager.list_plans(context_id, limit)
        
        return {
            "plans": [
                {
                    "plan_id": plan['plan_id'],
                    "context_id": plan['context_id'],
                    "created_at": plan['created_at'],
                    "execution_status": plan['execution_status'],
                    "task_count": len(plan.get('parsed_tasks', [])),
                    "has_modifications": len(plan.get('modifications', [])) > 0
                }
                for plan in plans
            ],
            "count": len(plans)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list plans: {str(e)}")


# Connection manager instance already defined earlier in the file


@app.websocket("/api/research/stream/{task_id}")
async def research_websocket(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for real-time research task streaming."""
    if not research_manager:
        await websocket.close(code=4503, reason="Research system not available")
        return
    
    try:
        await manager.connect_research(websocket, task_id)
        print(f"✓ Research WebSocket connected for task: {task_id}")
        
        # Set up progress callback for this WebSocket
        async def progress_callback(update):
            await manager.send_to_research(task_id, update)
        
        # Register callback with research manager
        research_manager.add_progress_callback(task_id, progress_callback)
        
        try:
            while True:
                # Keep connection alive and handle any client messages
                try:
                    data = await websocket.receive_text()
                    message_data = json.loads(data)
                    
                    # Handle client messages (e.g., cancel request)
                    if message_data.get("type") == "cancel_task":
                        await research_manager.cancel_task(task_id)
                        
                except asyncio.TimeoutError:
                    # Send keepalive ping
                    await websocket.send_text(json.dumps({"type": "ping"}))
                    
        except WebSocketDisconnect:
            pass
        
    except Exception as e:
        print(f"Research WebSocket error: {e}")
    finally:
        # Clean up
        if research_manager:
            research_manager.remove_progress_callback(task_id)
        manager.disconnect_research(websocket, task_id)


@app.websocket("/api/tasks/stream")
async def task_viewer_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time task viewing."""
    if not mcp_client:
        await websocket.close(code=4503, reason="MCP server not available")
        return
    
    try:
        await websocket.accept()
        print("✓ Task viewer WebSocket connected")
        
        # Send initial task data
        try:
            initial_tasks = await mcp_client.get_active_tasks()
            await websocket.send_text(json.dumps({
                "type": "initial_tasks",
                "data": initial_tasks
            }))
        except Exception as e:
            print(f"Failed to send initial task data: {e}")
        
        # Set up a periodic update loop
        async def send_task_updates():
            while True:
                try:
                    await asyncio.sleep(2)  # Update every 2 seconds
                    
                    # Get current active tasks
                    tasks_data = await mcp_client.get_active_tasks()
                    
                    # Send update
                    await websocket.send_text(json.dumps({
                        "type": "task_update",
                        "data": tasks_data,
                        "timestamp": datetime.now().isoformat()
                    }))
                    
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    print(f"Error sending task update: {e}")
                    break
        
        # Start the update loop
        update_task = asyncio.create_task(send_task_updates())
        
        try:
            while True:
                # Handle client messages
                try:
                    data = await websocket.receive_text()
                    message_data = json.loads(data)
                    
                    # Handle task cancellation requests
                    if message_data.get("type") == "cancel_task":
                        task_id = message_data.get("task_id")
                        if task_id:
                            success = await mcp_client.cancel_task(task_id)
                            await websocket.send_text(json.dumps({
                                "type": "task_cancelled",
                                "task_id": task_id,
                                "success": success
                            }))
                    
                    # Handle task detail requests
                    elif message_data.get("type") == "get_task_details":
                        task_id = message_data.get("task_id")
                        if task_id:
                            details = await mcp_client.get_task_details(task_id)
                            await websocket.send_text(json.dumps({
                                "type": "task_details",
                                "task_id": task_id,
                                "data": details
                            }))
                    
                    # Handle ping/keepalive
                    elif message_data.get("type") == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))
                        
                except asyncio.TimeoutError:
                    # Send keepalive ping
                    await websocket.send_text(json.dumps({"type": "ping"}))
                    
        except WebSocketDisconnect:
            print("Task viewer WebSocket disconnected")
        
    except Exception as e:
        print(f"Task viewer WebSocket error: {e}")
    finally:
        # Clean up
        if 'update_task' in locals():
            update_task.cancel()
        print("Task viewer WebSocket connection closed")


# Static files for serving the React app (when built)
if Path("frontend/build").exists():
    app.mount("/static", StaticFiles(directory="frontend/build/static"), name="static")
    
    @app.get("/", response_class=HTMLResponse)
    async def serve_frontend():
        """Serve the React frontend."""
        try:
            with open("frontend/build/index.html") as f:
                return HTMLResponse(content=f.read())
        except FileNotFoundError:
            return HTMLResponse(
                content="<h1>Frontend not built</h1><p>Run 'npm run build' in the frontend directory</p>",
                status_code=404
            )


def main():
    """Run the web server."""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description='Eunice Web Server')
    parser.add_argument('--host', default=os.getenv('EUNICE_HOST', '127.0.0.1'), help='Host to bind to')
    parser.add_argument('--port', type=int, default=int(os.getenv('EUNICE_WEB_PORT', '8000')), help='Port to bind to')
    parser.add_argument('--reload', action='store_true', help='Enable auto-reload for development')
    
    args = parser.parse_args()
    
    print(f"🌐 Starting Eunice Web Server on http://{args.host}:{args.port}")
    print("📱 Web UI available at the above URL")
    print("🔌 WebSocket streaming enabled for real-time chat")
    print("🔬 Research system integration enabled")
    
    uvicorn.run(
        "web_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )


if __name__ == "__main__":
    main()
