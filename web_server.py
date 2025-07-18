#!/usr/bin/env python3
"""
FastAPI Web Server for Collaborate AI Platform
Provides REST API and WebSocket endpoints for the web UI
"""

import os
import sys
import asyncio
import json
from pathlib import Path
from typing import List, Dict, Optional, AsyncGenerator
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
from config.config_manager import ConfigManager
from storage.database import DatabaseManager
from core.ai_client_manager import AIClientManager
from core.streaming_coordinator import StreamingResponseCoordinator
from models.data_models import Project, Conversation, Message
from utils.export_manager import ExportManager
from utils.error_handler import (
    get_error_handler, format_error_for_user, 
    CollaborateError, NetworkError, APIError, DatabaseError
)


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
    errors: Dict


# Global instances
config_manager: ConfigManager = None
db_manager: DatabaseManager = None
ai_manager: AIClientManager = None
streaming_coordinator: StreamingResponseCoordinator = None
export_manager: ExportManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global config_manager, db_manager, ai_manager, streaming_coordinator, export_manager
    
    print("🚀 Initializing Collaborate Web Server...")
    
    # Initialize components (same as CLI)
    config_manager = ConfigManager()
    db_manager = DatabaseManager(config_manager.config.storage.database_path)
    export_manager = ExportManager(config_manager.config.storage.export_path)
    
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
        # Database health
        db_stats = db_manager.get_database_stats()
        
        # AI providers health
        ai_health = {}
        if ai_manager:
            ai_health = ai_manager.get_provider_health()
        
        # Error statistics
        error_handler = get_error_handler()
        error_stats = error_handler.get_error_stats()
        
        return HealthResponse(
            status="healthy" if db_stats.get("status") == "healthy" else "degraded",
            database=db_stats,
            ai_providers=ai_health,
            errors=error_stats
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
            raise HTTPException(status_code=404, detail="Project not found")
        
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
            raise HTTPException(status_code=404, detail="Conversation not found")
        
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
            raise HTTPException(status_code=404, detail="Conversation not found")
        
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


# WebSocket manager for real-time connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.conversation_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, conversation_id: Optional[str] = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        
        if conversation_id:
            if conversation_id not in self.conversation_connections:
                self.conversation_connections[conversation_id] = []
            self.conversation_connections[conversation_id].append(websocket)

    def disconnect(self, websocket: WebSocket, conversation_id: Optional[str] = None):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        if conversation_id and conversation_id in self.conversation_connections:
            if websocket in self.conversation_connections[conversation_id]:
                self.conversation_connections[conversation_id].remove(websocket)

    async def send_to_conversation(self, conversation_id: str, message: dict):
        if conversation_id in self.conversation_connections:
            for connection in self.conversation_connections[conversation_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    # Remove dead connections
                    self.conversation_connections[conversation_id].remove(connection)


manager = ConnectionManager()


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
                except Exception as e:
                    print(f"❌ Failed to save user message: {e}")
                    await manager.send_to_conversation(conversation_id, {
                        "type": "error",
                        "message": f"Failed to save message: {str(e)}"
                    })
                    continue
                
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
                
                # Stream AI responses if streaming coordinator available
                if streaming_coordinator:
                    try:
                        session = db_manager.get_conversation_session(conversation_id)
                        context_messages = session.get_context_messages(
                            config_manager.config.conversation.max_context_tokens
                        )
                        
                        print(f"🤖 Starting AI streaming for conversation {conversation_id}")
                        
                        # Stream the conversation chain
                        async for update in streaming_coordinator.stream_conversation_chain(
                            user_message, context_messages
                        ):
                            # Forward streaming updates to all connected clients
                            await manager.send_to_conversation(conversation_id, update)
                            
                        print(f"✅ AI streaming completed for conversation {conversation_id}")
                        
                    except Exception as e:
                        print(f"❌ AI streaming error for conversation {conversation_id}: {e}")
                        # Send error message to client
                        await manager.send_to_conversation(conversation_id, {
                            "type": "error",
                            "message": f"AI response error: {str(e)}"
                        })
                        import traceback
                        traceback.print_exc()
                else:
                    print("⚠️ No streaming coordinator available")
                    await manager.send_to_conversation(conversation_id, {
                        "type": "error",
                        "message": "AI streaming not available"
                    })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, conversation_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket, conversation_id)


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
    
    uvicorn.run(
        "web_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )


if __name__ == "__main__":
    main()
