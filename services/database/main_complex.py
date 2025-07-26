#!/usr/bin/env python3
"""
Database Service for Eunice Research Platform

This service provides a centralized data access layer with transaction management,
schema abstraction, and data consistency enforcement. It acts as the dedicated
database agent for all WRITE operations in the hybrid architecture pattern.

Key Features:
- PostgreSQL database integration
- Transaction management and consistency
- Schema abstraction and migration support
- Health checks and monitoring
- RESTful API for database operations
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import asyncpg
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import redis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/database-service.log') if os.getenv('LOG_LEVEL') == 'DEBUG' else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/eunice")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8011"))

# Database models
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    status: str
    created_at: str
    updated_at: str
    metadata: Optional[Dict[str, Any]]

class TopicCreate(BaseModel):
    project_id: str
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class TopicResponse(BaseModel):
    id: str
    project_id: str
    name: str
    description: Optional[str]
    status: str
    created_at: str
    updated_at: str
    metadata: Optional[Dict[str, Any]]

# Database connection management
class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.session_factory = None
        self.redis_client = None
        
    async def initialize(self):
        """Initialize database schema and connections"""
        try:
            # Test database connection
            conn = await asyncpg.connect(self.db_url)
            await conn.close()
            logger.info("Database connection established")
            
            # Test Redis connection
            self.redis_client.ping()
            logger.info("Redis connection established")
            
            # Initialize schema
            await self.init_schema()
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    async def initialize_schema(self):
        """Initialize database schema with tables."""
        try:
            with self.engine.connect() as conn:
                # Create projects table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS projects (
                        id VARCHAR(36) PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        description TEXT,
                        status VARCHAR(50) DEFAULT 'active',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata JSONB DEFAULT '{}'
                    )
                """))
                
                # Create topics table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS research_topics (
                        id VARCHAR(36) PRIMARY KEY,
                        project_id VARCHAR(36) REFERENCES projects(id) ON DELETE CASCADE,
                        name VARCHAR(255) NOT NULL,
                        description TEXT,
                        status VARCHAR(50) DEFAULT 'active',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata JSONB DEFAULT '{}'
                    )
                """))
                
                # Create plans table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS research_plans (
                        id VARCHAR(36) PRIMARY KEY,
                        topic_id VARCHAR(36) REFERENCES research_topics(id) ON DELETE CASCADE,
                        name VARCHAR(255) NOT NULL,
                        description TEXT,
                        status VARCHAR(50) DEFAULT 'active',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata JSONB DEFAULT '{}'
                    )
                """))
                
                # Create tasks table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS research_tasks (
                        id VARCHAR(36) PRIMARY KEY,
                        plan_id VARCHAR(36) REFERENCES research_plans(id) ON DELETE CASCADE,
                        name VARCHAR(255) NOT NULL,
                        description TEXT,
                        status VARCHAR(50) DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata JSONB DEFAULT '{}'
                    )
                """))
                
                conn.commit()
                logger.info("Database schema initialized successfully")
                
        except Exception as e:
            logger.error(f"Schema initialization failed: {e}")
            raise
    
    def get_connection(self):
        """Get database connection."""
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check database and Redis health."""
        health = {
            "database": "unknown",
            "redis": "unknown",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Check PostgreSQL
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            health["database"] = "healthy"
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            health["database"] = "unhealthy"
        
        try:
            # Check Redis
            self.redis_client.ping()
            health["redis"] = "healthy"
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            health["redis"] = "unhealthy"
        
        return health

# Global database manager
db_manager = DatabaseManager()

# FastAPI application
app = FastAPI(
    title="Eunice Database Service",
    description="Centralized data access layer for Eunice Research Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.on_event("startup")
async def startup_event():
    """Initialize database connections on startup."""
    await db_manager.initialize()

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    health = await db_manager.health_check()
    status = "healthy" if all(status == "healthy" for status in [health["database"], health["redis"]]) else "unhealthy"
    
    return {
        "service": "database-service",
        "status": status,
        "version": "1.0.0",
        "dependencies": health
    }

# Project CRUD operations
@app.post("/projects", response_model=ProjectResponse)
async def create_project(project: ProjectCreate):
    """Create a new project."""
    try:
        import uuid
        from datetime import datetime
        
        project_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO projects (id, name, description, status, created_at, updated_at, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                """, (
                    project_id,
                    project.name,
                    project.description,
                    "active",
                    now,
                    now,
                    project.metadata or {}
                ))
                
                result = cursor.fetchone()
                conn.commit()
                
                return ProjectResponse(
                    id=result["id"],
                    name=result["name"],
                    description=result["description"],
                    status=result["status"],
                    created_at=result["created_at"].isoformat(),
                    updated_at=result["updated_at"].isoformat(),
                    metadata=result["metadata"]
                )
                
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects")
async def list_projects(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: Optional[int] = Query(100, description="Limit results")
):
    """List all projects."""
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                query = "SELECT * FROM projects"
                params = []
                
                if status:
                    query += " WHERE status = %s"
                    params.append(status)
                
                query += " ORDER BY created_at DESC"
                
                if limit:
                    query += " LIMIT %s"
                    params.append(limit)
                
                cursor.execute(query, params)
                results = cursor.fetchall()
                
                projects = []
                for row in results:
                    projects.append(ProjectResponse(
                        id=row["id"],
                        name=row["name"],
                        description=row["description"],
                        status=row["status"],
                        created_at=row["created_at"].isoformat(),
                        updated_at=row["updated_at"].isoformat(),
                        metadata=row["metadata"]
                    ))
                
                return projects
                
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Get a specific project."""
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
                result = cursor.fetchone()
                
                if not result:
                    raise HTTPException(status_code=404, detail="Project not found")
                
                return ProjectResponse(
                    id=result["id"],
                    name=result["name"],
                    description=result["description"],
                    status=result["status"],
                    created_at=result["created_at"].isoformat(),
                    updated_at=result["updated_at"].isoformat(),
                    metadata=result["metadata"]
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, project: ProjectCreate):
    """Update a project."""
    try:
        from datetime import datetime
        
        now = datetime.utcnow()
        
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE projects 
                    SET name = %s, description = %s, updated_at = %s, metadata = %s
                    WHERE id = %s
                    RETURNING *
                """, (
                    project.name,
                    project.description,
                    now,
                    project.metadata or {},
                    project_id
                ))
                
                result = cursor.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="Project not found")
                
                conn.commit()
                
                return ProjectResponse(
                    id=result["id"],
                    name=result["name"],
                    description=result["description"],
                    status=result["status"],
                    created_at=result["created_at"].isoformat(),
                    updated_at=result["updated_at"].isoformat(),
                    metadata=result["metadata"]
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project."""
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM projects WHERE id = %s RETURNING id", (project_id,))
                result = cursor.fetchone()
                
                if not result:
                    raise HTTPException(status_code=404, detail="Project not found")
                
                conn.commit()
                return {"message": "Project deleted successfully", "id": project_id}
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Initialize with sample data endpoint
@app.post("/initialize-sample-data")
async def initialize_sample_data():
    """Initialize the database with sample data for testing."""
    try:
        import uuid
        from datetime import datetime
        
        sample_projects = [
            {
                "id": str(uuid.uuid4()),
                "name": "AI in Healthcare Research",
                "description": "Investigating applications of artificial intelligence in medical diagnosis and treatment",
                "status": "active",
                "metadata": {"priority": "high", "department": "medical_ai", "budget": 150000}
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Climate Change Impact Study",
                "description": "Analyzing the effects of climate change on biodiversity in temperate forests",
                "status": "active", 
                "metadata": {"priority": "medium", "department": "environmental", "budget": 85000}
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Neuroplasticity and Learning",
                "description": "Examining how brain plasticity affects learning capabilities across different age groups",
                "status": "active",
                "metadata": {"priority": "high", "department": "neuroscience", "budget": 120000}
            }
        ]
        
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                # Clear existing data
                cursor.execute("TRUNCATE TABLE projects CASCADE")
                
                # Insert sample projects
                for project in sample_projects:
                    now = datetime.utcnow()
                    cursor.execute("""
                        INSERT INTO projects (id, name, description, status, created_at, updated_at, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        project["id"],
                        project["name"],
                        project["description"],
                        project["status"],
                        now,
                        now,
                        project["metadata"]
                    ))
                
                conn.commit()
                
        logger.info("Sample data initialized successfully")
        return {
            "message": "Sample data initialized successfully",
            "projects_created": len(sample_projects)
        }
        
    except Exception as e:
        logger.error(f"Error initializing sample data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def main():
    """Main entry point for the database service."""
    try:
        logger.info(f"Starting Database Service on {HOST}:{PORT}")
        
        config = uvicorn.Config(
            app,
            host=HOST,
            port=PORT,
            log_level="info",
            access_log=True
        )
        
        server = uvicorn.Server(config)
        await server.serve()
        
    except Exception as e:
        logger.error(f"Database service error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Database service stopped by user")
    except Exception as e:
        logger.error(f"Failed to start database service: {e}")
        sys.exit(1)
