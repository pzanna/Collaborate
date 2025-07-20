#!/usr/bin/env python3
"""
FastAPI Web Server for Collaborate AI Platform
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

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

# Import existing Collaborate components
from src.config.config_manager import ConfigManager
from src.storage.database import DatabaseManager
from src.core.ai_client_manager import AIClientManager
from src.core.streaming_coordinator import StreamingResponseCoordinator
from src.core.research_manager import ResearchManager
from src.core.context_manager import ContextManager
from src.models.data_models import Project, Conversation, Message
from src.utils.export_manager import ExportManager
from src.utils.error_handler import (
    ErrorHandler, 
    CollaborateError,
    format_error_for_user, 
    APIError
)
from src.mcp.client import MCPClient


# Pydantic models for API requests/responses
class ProjectCreate(BaseModel):
    name: str
    description: str = ""

class ConversationCreate(BaseModel):
    project_id: str
    title: str

class MessageCreate(BaseModel):
    conversation_id: str
    content: str

class ResearchRequest(BaseModel):
    conversation_id: str
    query: str
    research_mode: str = "comprehensive"  # comprehensive, quick, deep
    max_results: int = 10
    
class ResearchTaskResponse(BaseModel):
    task_id: str
    conversation_id: str
    query: str
    status: str
    created_at: str
    updated_at: str
    progress: float = 0.0
    results: Optional[Dict[str, Any]] = None

class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    participant: str
    content: str
    timestamp: str
    
class ConversationResponse(BaseModel):
    id: str
    project_id: str
    title: str
    status: str
    created_at: str
    updated_at: str
    message_count: int = 0

class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    created_at: str
    updated_at: str
    conversation_count: int = 0

class HealthResponse(BaseModel):
    status: str
    database: Dict
    ai_providers: Dict
    research_system: Dict
    errors: Dict


# Global state
config_manager: Optional[ConfigManager] = None
db_manager: Optional[DatabaseManager] = None
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
        self.conversation_connections: Dict[str, List[WebSocket]] = {}
        self.research_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, conversation_id: Optional[str] = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        
        if conversation_id:
            if conversation_id not in self.conversation_connections:
                self.conversation_connections[conversation_id] = []
            self.conversation_connections[conversation_id].append(websocket)

    async def connect_research(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        self.active_connections.append(websocket)
        
        if task_id not in self.research_connections:
            self.research_connections[task_id] = []
        self.research_connections[task_id].append(websocket)

    def disconnect(self, websocket: WebSocket, conversation_id: Optional[str] = None):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        if conversation_id and conversation_id in self.conversation_connections:
            if websocket in self.conversation_connections[conversation_id]:
                self.conversation_connections[conversation_id].remove(websocket)

    def disconnect_research(self, websocket: WebSocket, task_id: str):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        if task_id in self.research_connections:
            if websocket in self.research_connections[task_id]:
                self.research_connections[task_id].remove(websocket)

    async def send_to_conversation(self, conversation_id: str, message: dict):
        if conversation_id in self.conversation_connections:
            for connection in self.conversation_connections[conversation_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    # Remove dead connections
                    self.conversation_connections[conversation_id].remove(connection)

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
    
    print("🚀 Initializing Collaborate Web Server...")
    
    # Initialize components (same as CLI)
    config_manager = ConfigManager()
    
    # Set up logging first
    config_manager.setup_logging()
    
    db_manager = DatabaseManager(config_manager.config.storage.database_path)
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
            
            # Initialize research manager with MCP client
            research_manager = ResearchManager(config_manager)
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
    
    print("✓ Collaborate Web Server initialized successfully!")
    
    yield
    
    # Cleanup on shutdown
    print("👋 Shutting down Collaborate Web Server...")
    
    # Disconnect MCP client
    if mcp_client:
        await mcp_client.disconnect()
    
    # Cleanup research manager
    if research_manager:
        await research_manager.cleanup()
    
    # Cleanup context manager
    if context_manager:
        await context_manager.cleanup()


# Create FastAPI app
app = FastAPI(
    title="Collaborate AI Platform API",
    description="REST API and WebSocket endpoints for real-time AI collaboration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health endpoint
@app.get("/api/health", response_model=HealthResponse)
async def get_health():
    """Get system health status."""
    try:
        # Check database
        db_status = {"status": "healthy", "tables": 0}
        try:
            # Simple DB check
            projects = db_manager.list_projects()
            db_status["tables"] = len(projects) if projects else 0
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
        
        return HealthResponse(
            status="healthy",
            database=db_status,
            ai_providers=ai_status,
            research_system=research_status,
            errors={}
        )
    except Exception as e:
        return HealthResponse(
            status="error",
            database={"status": "error"},
            ai_providers={"status": "error"},
            research_system={"status": "error"},
            errors={"general": str(e)}
        )


# Projects endpoints
@app.get("/api/projects", response_model=List[ProjectResponse])
async def list_projects():
    """Get all projects."""
    try:
        projects = db_manager.list_projects()
        conversations = db_manager.list_conversations()
        
        # Count conversations per project
        conv_counts = {}
        for conv in conversations:
            conv_counts[conv.project_id] = conv_counts.get(conv.project_id, 0) + 1
        
        return [
            ProjectResponse(
                id=project.id,
                name=project.name,
                description=project.description,
                created_at=project.created_at.isoformat(),
                updated_at=project.updated_at.isoformat(),
                conversation_count=conv_counts.get(project.id, 0)
            )
            for project in projects
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/projects", response_model=ProjectResponse)
async def create_project(project: ProjectCreate):
    """Create a new project."""
    try:
        new_project = Project(name=project.name, description=project.description)
        created_project = db_manager.create_project(new_project)
        
        if not created_project:
            raise HTTPException(status_code=400, detail="Failed to create project")
        
        return ProjectResponse(
            id=created_project.id,
            name=created_project.name,
            description=created_project.description,
            created_at=created_project.created_at.isoformat(),
            updated_at=created_project.updated_at.isoformat(),
            conversation_count=0
        )
    except CollaborateError as e:
        raise HTTPException(status_code=400, detail=format_error_for_user(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project and all its conversations and messages."""
    try:
        success = db_manager.delete_project(project_id)
        if not success:
            return {"success": False, "message": "Project not found or already deleted"}
        
        return {"success": True, "message": "Project deleted successfully"}
    except CollaborateError as e:
        raise HTTPException(status_code=400, detail=format_error_for_user(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Conversations endpoints
@app.get("/api/conversations", response_model=List[ConversationResponse])
async def list_conversations(project_id: Optional[str] = None):
    """Get all conversations, optionally filtered by project."""
    try:
        conversations = db_manager.list_conversations()
        
        if project_id:
            conversations = [c for c in conversations if c.project_id == project_id]
        
        # Get message counts
        response_conversations = []
        for conv in conversations:
            session = db_manager.get_conversation_session(conv.id)
            message_count = len(session.messages) if session else 0
            
            response_conversations.append(ConversationResponse(
                id=conv.id,
                project_id=conv.project_id,
                title=conv.title,
                status=conv.status,
                created_at=conv.created_at.isoformat(),
                updated_at=conv.updated_at.isoformat(),
                message_count=message_count
            ))
        
        return response_conversations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/conversations", response_model=ConversationResponse)
async def create_conversation(conversation: ConversationCreate):
    """Create a new conversation."""
    try:
        new_conversation = Conversation(
            project_id=conversation.project_id,
            title=conversation.title
        )
        created_conversation = db_manager.create_conversation(new_conversation)
        
        if not created_conversation:
            raise HTTPException(status_code=400, detail="Failed to create conversation")
        
        return ConversationResponse(
            id=created_conversation.id,
            project_id=created_conversation.project_id,
            title=created_conversation.title,
            status=created_conversation.status,
            created_at=created_conversation.created_at.isoformat(),
            updated_at=created_conversation.updated_at.isoformat(),
            message_count=0
        )
    except CollaborateError as e:
        raise HTTPException(status_code=400, detail=format_error_for_user(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation and all its messages."""
    try:
        success = db_manager.delete_conversation(conversation_id)
        if not success:
            return {"success": False, "message": "Conversation not found or already deleted"}
        
        return {"success": True, "message": "Conversation deleted successfully"}
    except CollaborateError as e:
        raise HTTPException(status_code=400, detail=format_error_for_user(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(conversation_id: str):
    """Get all messages in a conversation."""
    try:
        session = db_manager.get_conversation_session(conversation_id)
        if not session:
            return []  # Return empty list if conversation not found
        
        return [
            MessageResponse(
                id=msg.id,
                conversation_id=msg.conversation_id,
                participant=msg.participant,
                content=msg.content,
                timestamp=msg.timestamp.isoformat()
            )
            for msg in session.messages
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Research endpoints
@app.post("/api/research/start", response_model=ResearchTaskResponse)
async def start_research_task(request: ResearchRequest):
    """Start a new research task."""
    if not research_manager:
        raise HTTPException(status_code=503, detail="Research system not available")
    
    try:
        # Create options dict from request parameters
        options = {
            'research_mode': request.research_mode,
            'max_results': request.max_results,
            'metadata': {}
        }
        
        # Create research task with proper parameters
        task_id, cost_info = await research_manager.start_research_task(
            query=request.query,
            user_id="web_user",  # Default user ID for web requests
            conversation_id=request.conversation_id,
            options=options
        )
        
        # Get task details
        task_context = research_manager.get_task_context(task_id)
        
        return ResearchTaskResponse(
            task_id=task_id,
            conversation_id=request.conversation_id,
            query=request.query,
            status=task_context.stage.value,
            created_at=task_context.created_at.isoformat(),
            updated_at=task_context.updated_at.isoformat(),
            progress=0.0
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start research task: {str(e)}")


@app.get("/api/research/task/{task_id}", response_model=ResearchTaskResponse)
async def get_research_task(task_id: str):
    """Get status and results of a research task."""
    if not research_manager:
        raise HTTPException(status_code=503, detail="Research system not available")
    
    try:
        task_context = research_manager.get_task_context(task_id)
        if not task_context:
            # Return empty task response instead of error
            return ResearchTaskResponse(
                task_id=task_id,
                conversation_id="",
                query="Task not found",
                status="not_found",
                created_at="",
                updated_at="",
                progress=0.0,
                results=None
            )
        
        # Calculate progress
        progress = research_manager.calculate_task_progress(task_id)
        
        # Prepare results
        results = None
        if task_context.stage == task_context.stage.COMPLETE:
            results = {
                "search_results": task_context.search_results,
                "reasoning_output": task_context.reasoning_output,
                "execution_results": task_context.execution_results,
                "synthesis": task_context.synthesis,
                "metadata": task_context.metadata
            }
        
        return ResearchTaskResponse(
            task_id=task_id,
            conversation_id=task_context.conversation_id,
            query=task_context.query,
            status=task_context.stage.value,
            created_at=task_context.created_at.isoformat(),
            updated_at=task_context.updated_at.isoformat(),
            progress=progress,
            results=results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get research task: {str(e)}")


@app.delete("/api/research/task/{task_id}")
async def cancel_research_task(task_id: str):
    """Cancel a research task."""
    if not research_manager:
        raise HTTPException(status_code=503, detail="Research system not available")
    
    try:
        success = await research_manager.cancel_task(task_id)
        if not success:
            return {"success": False, "message": "Research task not found or already completed"}
        
        return {"success": True, "message": "Research task cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel research task: {str(e)}")


# ===== Context Tracking API Endpoints =====

@app.post("/api/context/create")
async def create_context(conversation_id: str, context_id: Optional[str] = None):
    """Create a new session context."""
    if not context_manager:
        raise HTTPException(status_code=503, detail="Context system not available")
    
    try:
        created_context_id = await context_manager.create_context(conversation_id, context_id)
        return {
            "success": True,
            "context_id": created_context_id,
            "conversation_id": conversation_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create context: {str(e)}")


@app.get("/api/context/{context_id}")
async def get_context(context_id: str):
    """Get a session context by ID."""
    if not context_manager:
        raise HTTPException(status_code=503, detail="Context system not available")
    
    try:
        context = await context_manager.get_context(context_id)
        if not context:
            return {
                "context_id": context_id,
                "conversation_id": "",
                "created_at": "",
                "updated_at": "",
                "status": "not_found",
                "current_stage": "",
                "active_agents": [],
                "memory_references": [],
                "message_count": 0,
                "task_count": 0,
                "trace_count": 0,
                "metadata": {},
                "settings": {}
            }
        
        return {
            "context_id": context.context_id,
            "conversation_id": context.conversation_id,
            "created_at": context.created_at.isoformat(),
            "updated_at": context.updated_at.isoformat(),
            "status": context.status,
            "current_stage": context.current_stage,
            "active_agents": context.active_agents,
            "memory_references": context.memory_references,
            "message_count": len(context.messages),
            "task_count": len(context.research_tasks),
            "trace_count": len(context.context_traces),
            "metadata": context.metadata,
            "settings": context.settings
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get context: {str(e)}")


@app.post("/api/context/{context_id}/resume")
async def resume_context(context_id: str):
    """Resume a context with full data restoration."""
    if not context_manager:
        raise HTTPException(status_code=503, detail="Context system not available")
    
    try:
        context = await context_manager.resume_context(context_id)
        if not context:
            return {
                "success": False,
                "context_id": context_id,
                "conversation_id": "",
                "message_count": 0,
                "task_count": 0,
                "trace_count": 0,
                "current_stage": "",
                "status": "not_found",
                "message": "Context not found or could not be resumed"
            }
        
        return {
            "success": True,
            "context_id": context.context_id,
            "conversation_id": context.conversation_id,
            "message_count": len(context.messages),
            "task_count": len(context.research_tasks),
            "trace_count": len(context.context_traces),
            "current_stage": context.current_stage,
            "status": context.status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resume context: {str(e)}")


@app.get("/api/context/{context_id}/traces")
async def get_context_traces(context_id: str, limit: int = 100):
    """Get context traces for a context."""
    if not context_manager:
        raise HTTPException(status_code=503, detail="Context system not available")
    
    try:
        traces = await context_manager.get_context_traces(context_id, limit)
        
        return {
            "context_id": context_id,
            "traces": [
                {
                    "trace_id": trace.trace_id,
                    "task_id": trace.task_id,
                    "stage": trace.stage,
                    "content": trace.content,
                    "timestamp": trace.timestamp.isoformat(),
                    "metadata": trace.metadata
                }
                for trace in traces
            ],
            "count": len(traces)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get context traces: {str(e)}")


@app.get("/api/contexts")
async def list_contexts(conversation_id: Optional[str] = None, status: Optional[str] = None, limit: int = 50):
    """List contexts with optional filtering."""
    if not context_manager:
        raise HTTPException(status_code=503, detail="Context system not available")
    
    try:
        contexts = await context_manager.list_contexts(conversation_id, status, limit)
        return {
            "contexts": contexts,
            "count": len(contexts)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list contexts: {str(e)}")


@app.post("/api/context/{context_id}/trace")
async def add_context_trace(context_id: str, stage: str, content: dict, task_id: Optional[str] = None, metadata: Optional[dict] = None):
    """Add a context trace entry."""
    if not context_manager:
        raise HTTPException(status_code=503, detail="Context system not available")
    
    try:
        trace_id = await context_manager.add_context_trace(
            context_id=context_id,
            stage=stage,
            content=content,
            task_id=task_id,
            metadata=metadata
        )
        
        return {
            "success": True,
            "trace_id": trace_id,
            "context_id": context_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add context trace: {str(e)}")


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
            status_counts[task.status] = status_counts.get(task.status, 0) + 1
            agent_counts[task.agent_type] = agent_counts.get(task.agent_type, 0) + 1
        
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


@app.websocket("/api/chat/stream/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: str):
    """WebSocket endpoint for real-time chat streaming."""
    try:
        await manager.connect(websocket, conversation_id)
        print(f"✓ WebSocket connected for conversation: {conversation_id}")
    except Exception as e:
        print(f"✗ Failed to establish WebSocket connection: {e}")
        raise
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Handle connection initialization
            if message_data.get("type") == "connection_init":
                print(f"WebSocket connection initialized for conversation {conversation_id}")
                # Send a welcome message or confirmation
                await manager.send_to_conversation(conversation_id, {
                    "type": "connection_confirmed",
                    "conversation_id": conversation_id
                })
                continue
            
            if message_data.get("type") == "user_message":
                content = message_data.get("content", "").strip()
                if not content:
                    continue
                
                print(f"📝 Processing user message: {content[:50]}...")
                
                # Create and save user message
                user_message = Message(
                    conversation_id=conversation_id,
                    participant="user",
                    content=content
                )
                
                try:
                    db_manager.create_message(user_message)
                    print(f"✅ User message saved to database: {user_message.id}")
                    
                    # Broadcast user message to all connected clients
                    await manager.send_to_conversation(conversation_id, {
                        "type": "user_message",
                        "message": {
                            "id": user_message.id,
                            "conversation_id": user_message.conversation_id,
                            "participant": user_message.participant,
                            "content": user_message.content,
                            "timestamp": user_message.timestamp.isoformat()
                        }
                    })
                    
                    # Check if this is a research query
                    if content.lower().startswith(('research:', 'find:', 'search:', 'analyze:')):
                        # Handle research mode
                        if research_manager:
                            try:
                                # Extract query (remove prefix)
                                query = content.split(':', 1)[1].strip()
                                
                                # Create options for research task
                                options = {
                                    'research_mode': "comprehensive",
                                    'max_results': 10,
                                    'metadata': {}
                                }
                                
                                # Start research task
                                task_id, cost_info = await research_manager.start_research_task(
                                    query=query,
                                    user_id="web_user",
                                    conversation_id=conversation_id,
                                    options=options
                                )
                                
                                # Notify client about research task
                                await manager.send_to_conversation(conversation_id, {
                                    "type": "research_started",
                                    "task_id": task_id,
                                    "query": query
                                })
                                
                                # Set up progress callback
                                async def research_progress_callback(update):
                                    await manager.send_to_conversation(conversation_id, update)
                                
                                research_manager.add_progress_callback(task_id, research_progress_callback)
                                
                            except Exception as e:
                                print(f"❌ Research task error: {e}")
                                await manager.send_to_conversation(conversation_id, {
                                    "type": "error",
                                    "message": f"Research task failed: {str(e)}"
                                })
                        else:
                            await manager.send_to_conversation(conversation_id, {
                                "type": "error",
                                "message": "Research system not available"
                            })
                    
                except Exception as e:
                    print(f"❌ Failed to save user message: {e}")
                    await manager.send_to_conversation(conversation_id, {
                        "type": "error",
                        "message": f"Failed to save message: {str(e)}"
                    })
                    continue
                    
    except WebSocketDisconnect:
        manager.disconnect(websocket, conversation_id)
    except Exception as e:
        print(f"WebSocket error: {e}")


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
if Path("frontend/dist").exists():
    app.mount("/static", StaticFiles(directory="frontend/dist/static"), name="static")
    
    @app.get("/", response_class=HTMLResponse)
    async def serve_frontend():
        """Serve the React frontend."""
        try:
            with open("frontend/dist/index.html") as f:
                return HTMLResponse(content=f.read())
        except FileNotFoundError:
            return HTMLResponse(
                content="<h1>Frontend not built</h1><p>Run 'npm run build' in the frontend directory</p>",
                status_code=404
            )


def main():
    """Run the web server."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Collaborate Web Server')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
    parser.add_argument('--reload', action='store_true', help='Enable auto-reload')
    
    args = parser.parse_args()
    
    print(f"🌐 Starting Collaborate Web Server on http://{args.host}:{args.port}")
    print("📱 Web UI will be available once frontend is built")
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
