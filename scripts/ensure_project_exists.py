#!/usr/bin/env python3
"""
Production script to ensure the required project exists in the database.

This script addresses the issue where POST /v2/projects/{project_id}/topics 
returns 404 Not Found because the project doesn't exist in the database.

Usage:
    python3 ensure_project_exists.py [project_id]
    
If no project_id is provided, it will check for the specific ID from the logs:
589e3d6d-79d1-497e-9780-42f32d4547f5
"""

import asyncio
import sys
import os
import logging
import json
from datetime import datetime
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/eunice")


async def ensure_project_exists(project_id: str, project_name: Optional[str] = None) -> bool:
    """
    Ensure a project exists in the database.
    
    Args:
        project_id: The project ID to check/create
        project_name: Optional name for the project if creating
        
    Returns:
        True if project exists or was created successfully
    """
    try:
        import asyncpg
        
        logger.info(f"Connecting to database: {DATABASE_URL}")
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Check if project already exists
        logger.info(f"Checking if project {project_id} exists...")
        existing = await conn.fetchrow(
            "SELECT id, name, status FROM projects WHERE id = $1",
            project_id
        )
        
        if existing:
            logger.info(f"✅ Project already exists: {existing['name']} (status: {existing['status']})")
            await conn.close()
            return True
        
        # Project doesn't exist, create it
        logger.info(f"Project {project_id} not found. Creating...")
        
        now = datetime.now()
        project_data = {
            "id": project_id,
            "name": project_name or f"Project {project_id[:8]}",
            "description": "Project created to resolve topic creation issues",
            "status": "active",
            "metadata": {
                "created_by": "ensure_project_exists_script",
                "created_at": now.isoformat(),
                "purpose": "resolve_topic_creation_404"
            }
        }
        
        await conn.execute("""
            INSERT INTO projects (id, name, description, status, created_at, updated_at, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
            project_data["id"],
            project_data["name"],
            project_data["description"],
            project_data["status"],
            now,
            now,
            json.dumps(project_data["metadata"])
        )
        
        logger.info(f"✅ Successfully created project: {project_data['name']}")
        await conn.close()
        return True
        
    except ImportError:
        logger.error("asyncpg is not installed. Please install it: pip install asyncpg")
        return False
    except Exception as e:
        logger.error(f"Failed to ensure project exists: {e}")
        return False


async def list_all_projects() -> bool:
    """List all projects in the database for debugging."""
    try:
        import asyncpg
        
        conn = await asyncpg.connect(DATABASE_URL)
        
        projects = await conn.fetch(
            "SELECT id, name, status, created_at FROM projects ORDER BY created_at DESC"
        )
        
        logger.info(f"Found {len(projects)} projects in database:")
        for project in projects:
            logger.info(f"  - {project['id']}: {project['name']} ({project['status']})")
        
        await conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        return False


async def main():
    """Main function."""
    # Default project ID from the logs
    default_project_id = "589e3d6d-79d1-497e-9780-42f32d4547f5"
    
    # Get project ID from command line or use default
    if len(sys.argv) > 1:
        project_id = sys.argv[1]
    else:
        project_id = default_project_id
        logger.info(f"Using default project ID from logs: {project_id}")
    
    logger.info("=" * 60)
    logger.info("PROJECT EXISTENCE CHECKER")
    logger.info("=" * 60)
    
    # List all projects first
    logger.info("Listing all existing projects...")
    await list_all_projects()
    
    # Ensure the specific project exists
    logger.info(f"\nEnsuring project {project_id} exists...")
    success = await ensure_project_exists(project_id, "Test Research Project")
    
    if success:
        logger.info("\n✅ SUCCESS: Project is now available for topic creation")
        logger.info(f"You can now POST to /v2/projects/{project_id}/topics")
    else:
        logger.error("\n❌ FAILED: Could not ensure project exists")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())