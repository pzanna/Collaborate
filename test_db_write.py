#!/usr/bin/env python3
"""Test script to directly test database write operations."""

import asyncio
import asyncpg
import json
from datetime import datetime
import uuid

async def test_database_write():
    """Test writing directly to the database."""
    
    # Database connection parameters
    database_url = "postgresql://postgres:password@localhost:5432/eunice"
    
    try:
        # Create connection
        conn = await asyncpg.connect(database_url)
        
        # Test data
        project_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        # Create project
        query = """
            INSERT INTO projects (
                id, name, description, status, created_at, updated_at, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
        """
        
        params = [
            project_id,
            "Direct Test Project",
            "Testing direct database write",
            "pending",
            now.isoformat(),
            now.isoformat(),
            json.dumps({"direct_test": True})
        ]
        
        result = await conn.fetchrow(query, *params)
        print(f"Insert result: {dict(result)}")
        
        # Verify the project exists
        verify_query = "SELECT * FROM projects WHERE id = $1"
        verify_result = await conn.fetchrow(verify_query, project_id)
        print(f"Verify result: {dict(verify_result) if verify_result else 'Not found'}")
        
        await conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_database_write())
