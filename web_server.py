#!/usr/bin/env python3
"""
FastAPI Web Server for Eunice AI Platform
Provides REST API and WebSocket endpoints for the web UI
"""

import os
import sys
import asyncio
import json
import logging
import time
import traceback
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
from src.core.research_manager import ResearchManager
from src.core.context_manager import ContextManager
from src.utils.error_handler import (
    ErrorHandler, 
    EuniceError,
    format_error_for_user, 
    APIError
)
from src.mcp.client import MCPClient
# V2 Hierarchical Research API
from src.api.v2_hierarchical_api import v2_router
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



# Keep only essential models for health and WebSocket functionality
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
research_manager: Optional[ResearchManager] = None
context_manager: Optional[ContextManager] = None
mcp_client: Optional[MCPClient] = None

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
    
    # Set database manager for V2 API
    set_database_manager(db_manager)
    
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
        print(f"✓ AI providers available: {', '.join(available_providers)}")
    except Exception as e:
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
    ## Eunice Research Platform API v2.0
    
    A comprehensive REST API and WebSocket service for the Eunice AI Research Platform.
    
    ### Features
    - **V2 Hierarchical Research API**: Complete topic-plan-task structure with proper relationships
    - **Health Monitoring**: System status and health endpoints
    - **Real-time WebSockets**: Live updates for research progress
    - **Static File Serving**: Frontend application support
    
    ### API Structure
    - **V2 Hierarchical API**: All research functionality under `/api/v2/*`
    - **Health Endpoints**: System status under `/api/health` and `/api/version`
    - **WebSocket Endpoints**: Real-time connections under `/api/*/stream`
    
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

# Include V2 hierarchical research API router
from src.api.v2_hierarchical_api import v2_router, set_database_manager
# Import ErrorResponse from V2 API for exception handlers
from src.models.hierarchical_data_models import ErrorResponse
# Set the database manager for V2 API (will be set during startup)
app.include_router(v2_router)

# Simple API middleware for consistent headers
@app.middleware("http")
async def add_api_headers(request, call_next):
    """Add standard API headers to all responses."""
    response = await call_next(request)
    response.headers["X-API-Version"] = "2.0.0"
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
        version="2.0.0",
        supported_versions=["2.0"],
        deprecated_versions=["1.0"],
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
