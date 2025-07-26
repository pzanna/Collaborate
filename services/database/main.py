#!/usr/bin/env python3
"""
Simple Database Service for Eunice Research Platform
Basic version for testing connectivity and basic functionality.
"""
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional

import asyncpg
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/eunice")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8011"))

# Data models
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime

# Initialize FastAPI app
app = FastAPI(
    title="Eunice Database Service",
    description="Centralized database service for the Eunice Research Platform",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection pool
db_pool = None

@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
        logger.info("Database connection pool created successfully")
        
        # Initialize schema
        await init_schema()
        logger.info("Database schema initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    global db_pool
    if db_pool:
        await db_pool.close()
        logger.info("Database connection pool closed")

async def init_schema():
    """Initialize database schema"""
    async with db_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create trigger for updated_at
        await conn.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """)
        
        await conn.execute("""
            DROP TRIGGER IF EXISTS update_projects_updated_at ON projects;
            CREATE TRIGGER update_projects_updated_at
                BEFORE UPDATE ON projects
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        """)

# Health check endpoint
@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

# Initialize sample data endpoint
@app.post("/initialize-sample-data")
async def initialize_sample_data():
    """Initialize database with sample data"""
    try:
        sample_projects = [
            ("Neural Network Optimization", "Research project focused on optimizing neural network architectures for biomedical applications."),
            ("Protein Folding Analysis", "Computational analysis of protein folding patterns using machine learning techniques."),
            ("Gene Expression Study", "Investigation of gene expression patterns in various biological conditions.")
        ]
        
        async with db_pool.acquire() as conn:
            # Clear existing data
            await conn.execute("DELETE FROM projects")
            
            # Insert sample data
            for name, description in sample_projects:
                await conn.execute(
                    "INSERT INTO projects (name, description) VALUES ($1, $2)",
                    name, description
                )
        
        return {"message": "Sample data initialized successfully", "count": len(sample_projects)}
    
    except Exception as e:
        logger.error(f"Failed to initialize sample data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Project CRUD endpoints
@app.get("/projects", response_model=List[Project])
async def list_projects():
    """List all projects"""
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM projects ORDER BY created_at DESC")
            
            projects = []
            for row in rows:
                projects.append(Project(
                    id=row['id'],
                    name=row['name'],
                    description=row['description'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                ))
            
            return projects
    
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/projects", response_model=Project)
async def create_project(project: ProjectCreate):
    """Create a new project"""
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO projects (name, description) 
                VALUES ($1, $2) 
                RETURNING id, name, description, created_at, updated_at
                """,
                project.name, project.description
            )
            
            return Project(
                id=row['id'],
                name=row['name'],
                description=row['description'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
    
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects/{project_id}", response_model=Project)
async def get_project(project_id: int):
    """Get a specific project by ID"""
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM projects WHERE id = $1",
                project_id
            )
            
            if not row:
                raise HTTPException(status_code=404, detail="Project not found")
            
            return Project(
                id=row['id'],
                name=row['name'],
                description=row['description'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        log_level="info",
        reload=False
    )
