#!/usr/bin/env python3
"""
Database Tools for Eunice Research Platform

This module provides database write functions for the Eunice platform.
To answer the configuration question: I envision one centralized tool with multiple commands 
rather than separate tools for each operation. This approach:
- Reduces tool proliferation in the system
- Centralizes connection management, logging, and error handling
- Allows easy addition of new commands without changing the tool interface
- Improves security by using parameterized queries in a controlled manner
- Simplifies integration with AI agents or API gateways (one tool call format)

The main function is database_write(command: str, data: str) where:
- command is like "create_project", "update_task", "delete_plan"
- data is a JSON string with the required fields

Returns a JSON string with {"status": "success", "id": "...", "message": "..."} or {"status": "error", "error": "..."}

This follows best practices for microservices and tool design.
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict

import asyncpg

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/eunice")


async def database_write(command: str, data: str) -> str:
    """
    Centralized database write function.
    
    Args:
        command: The operation command (e.g., "create_project", "update_task")
        data: JSON string with operation data
        
    Returns:
        JSON string with result
    """
    try:
        data_dict: Dict[str, Any] = json.loads(data)
        conn = await asyncpg.connect(DATABASE_URL)
        
        try:
            if command.startswith("create_"):
                result = await _handle_create(command, data_dict, conn)
            elif command.startswith("update_"):
                result = await _handle_update(command, data_dict, conn)
            elif command.startswith("delete_"):
                result = await _handle_delete(command, data_dict, conn)
            else:
                raise ValueError(f"Unknown command: {command}")
                
            return json.dumps(result)
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Database write error for command {command}: {e}")
        return json.dumps({"status": "error", "error": str(e)})


async def _handle_create(command: str, data: Dict[str, Any], conn: asyncpg.Connection) -> Dict[str, Any]:
    """Handle create operations."""
    entity = command.replace("create_", "")
    now = datetime.utcnow()
    
    if entity == "project":
        project_id = data.get("id", str(uuid.uuid4()))
        await conn.execute("""
            INSERT INTO projects (id, name, description, status, created_at, updated_at, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, 
            project_id,
            data["name"],
            data.get("description"),
            data.get("status", "active"),
            now,
            now,
            json.dumps(data.get("metadata", {}))
        )
        return {"status": "success", "id": project_id, "message": "Project created"}
    
    elif entity == "research_topic":
        topic_id = data.get("id", str(uuid.uuid4()))
        await conn.execute("""
            INSERT INTO research_topics (id, project_id, name, description, status, created_at, updated_at, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """,
            topic_id,
            data["project_id"],
            data["name"],
            data.get("description"),
            data.get("status", "active"),
            now,
            now,
            json.dumps(data.get("metadata", {}))
        )
        return {"status": "success", "id": topic_id, "message": "Research topic created"}
    
    elif entity == "research_plan":
        plan_id = data.get("id", str(uuid.uuid4()))
        await conn.execute("""
            INSERT INTO research_plans (id, topic_id, name, description, plan_type, status, plan_approved,
                                      created_at, updated_at, estimated_cost, actual_cost, metadata,
                                      plan_structure, initial_literature_results, reviewed_literature_results)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
        """,
            plan_id,
            data["topic_id"],
            data["name"],
            data.get("description"),
            data.get("plan_type", "comprehensive"),
            data.get("status", "draft"),
            data.get("plan_approved", False),
            now,
            now,
            data.get("estimated_cost", 0.0),
            data.get("actual_cost", 0.0),
            json.dumps(data.get("metadata", {})),
            json.dumps(data.get("plan_structure", {})),
            json.dumps(data.get("initial_literature_results", {})),
            json.dumps(data.get("reviewed_literature_results", {}))
        )
        return {"status": "success", "id": plan_id, "message": "Research plan created"}
    
    elif entity == "task":
        task_id = data.get("id", str(uuid.uuid4()))
        await conn.execute("""
            INSERT INTO tasks (id, plan_id, name, description, task_type, task_order, status, created_at, updated_at, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """,
            task_id,
            data["plan_id"],
            data["name"],
            data.get("description"),
            data.get("task_type", "research"),
            data.get("task_order", 1),
            data.get("status", "pending"),
            now,
            now,
            json.dumps(data.get("metadata", {}))
        )
        return {"status": "success", "id": task_id, "message": "Task created"}
    
    elif entity == "research_task":
        # Note: Since synced, but allow direct create if needed
        task_id = data.get("id", str(uuid.uuid4()))
        await conn.execute("""
            INSERT INTO research_tasks (id, plan_id, name, description, task_type, task_order, status, stage, created_at, updated_at, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """,
            task_id,
            data["plan_id"],
            data["name"],
            data.get("description"),
            data.get("task_type", "research"),
            data.get("task_order", 1),
            data.get("status", "pending"),
            data.get("stage", "planning"),
            now,
            now,
            json.dumps(data.get("metadata", {}))
        )
        return {"status": "success", "id": task_id, "message": "Research task created"}
    
    elif entity == "literature_record":
        record_id = data.get("id", str(uuid.uuid4()))
        await conn.execute("""
            INSERT INTO literature_records (id, title, authors, project_id, doi, external_id, year, journal, abstract, url,
                                          citation_count, source, publication_type, mesh_terms, categories,
                                          created_at, updated_at, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
        """,
            record_id,
            data["title"],
            json.dumps(data.get("authors", [])),
            data["project_id"],
            data.get("doi"),
            data.get("external_id"),
            data.get("year"),
            data.get("journal"),
            data.get("abstract"),
            data.get("url"),
            data.get("citation_count", 0),
            data.get("source"),
            data.get("publication_type"),
            json.dumps(data.get("mesh_terms", [])),
            json.dumps(data.get("categories", [])),
            now,
            now,
            json.dumps(data.get("metadata", {}))
        )
        return {"status": "success", "id": record_id, "message": "Literature record created"}
    
    elif entity == "search_term_optimization":
        opt_id = data.get("id", str(uuid.uuid4()))
        await conn.execute("""
            INSERT INTO search_term_optimizations (id, source_type, source_id, original_query, optimized_terms,
                                                 optimization_context, target_databases, created_at, updated_at, expires_at, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """,
            opt_id,
            data["source_type"],
            data["source_id"],
            data["original_query"],
            json.dumps(data["optimized_terms"]),
            json.dumps(data.get("optimization_context", {})),
            json.dumps(data.get("target_databases", [])),
            now,
            now,
            data.get("expires_at"),
            json.dumps(data.get("metadata", {}))
        )
        return {"status": "success", "id": opt_id, "message": "Search term optimization created"}
    
    else:
        raise ValueError(f"Unknown create entity: {entity}")


async def _handle_update(command: str, data: Dict[str, Any], conn: asyncpg.Connection) -> Dict[str, Any]:
    """Handle update operations."""
    entity = command.replace("update_", "")
    now = datetime.utcnow()
    
    if "id" not in data:
        raise ValueError("ID required for update")
    
    if entity == "project":
        await conn.execute("""
            UPDATE projects SET
                name = $1,
                description = $2,
                status = $3,
                updated_at = $4,
                metadata = $5
            WHERE id = $6
        """,
            data["name"],
            data.get("description"),
            data.get("status"),
            now,
            json.dumps(data.get("metadata", {})),
            data["id"]
        )
        return {"status": "success", "id": data["id"], "message": "Project updated"}
    
    elif entity == "research_topic":
        await conn.execute("""
            UPDATE research_topics SET
                name = $1,
                description = $2,
                status = $3,
                updated_at = $4,
                metadata = $5
            WHERE id = $6
        """,
            data["name"],
            data.get("description"),
            data.get("status"),
            now,
            json.dumps(data.get("metadata", {})),
            data["id"]
        )
        return {"status": "success", "id": data["id"], "message": "Research topic updated"}
    
    elif entity == "research_plan":
        await conn.execute("""
            UPDATE research_plans SET
                name = $1,
                description = $2,
                plan_type = $3,
                status = $4,
                plan_approved = $5,
                updated_at = $6,
                estimated_cost = $7,
                actual_cost = $8,
                metadata = $9,
                plan_structure = $10,
                initial_literature_results = $11,
                reviewed_literature_results = $12
            WHERE id = $13
        """,
            data["name"],
            data.get("description"),
            data.get("plan_type"),
            data.get("status"),
            data.get("plan_approved"),
            now,
            data.get("estimated_cost"),
            data.get("actual_cost"),
            json.dumps(data.get("metadata", {})),
            json.dumps(data.get("plan_structure", {})),
            json.dumps(data.get("initial_literature_results", {})),
            json.dumps(data.get("reviewed_literature_results", {})),
            data["id"]
        )
        return {"status": "success", "id": data["id"], "message": "Research plan updated"}
    
    elif entity == "task":
        await conn.execute("""
            UPDATE tasks SET
                name = $1,
                description = $2,
                task_type = $3,
                task_order = $4,
                status = $5,
                updated_at = $6,
                metadata = $7
            WHERE id = $8
        """,
            data["name"],
            data.get("description"),
            data.get("task_type"),
            data.get("task_order"),
            data.get("status"),
            now,
            json.dumps(data.get("metadata", {})),
            data["id"]
        )
        return {"status": "success", "id": data["id"], "message": "Task updated"}
    
    elif entity == "research_task":
        await conn.execute("""
            UPDATE research_tasks SET
                name = $1,
                description = $2,
                task_type = $3,
                task_order = $4,
                status = $5,
                stage = $6,
                updated_at = $7,
                metadata = $8
            WHERE id = $9
        """,
            data["name"],
            data.get("description"),
            data.get("task_type"),
            data.get("task_order"),
            data.get("status"),
            data.get("stage"),
            now,
            json.dumps(data.get("metadata", {})),
            data["id"]
        )
        return {"status": "success", "id": data["id"], "message": "Research task updated"}
    
    elif entity == "literature_record":
        await conn.execute("""
            UPDATE literature_records SET
                title = $1,
                authors = $2,
                doi = $3,
                external_id = $4,
                year = $5,
                journal = $6,
                abstract = $7,
                url = $8,
                citation_count = $9,
                source = $10,
                publication_type = $11,
                mesh_terms = $12,
                categories = $13,
                updated_at = $14,
                metadata = $15
            WHERE id = $16
        """,
            data["title"],
            json.dumps(data.get("authors", [])),
            data.get("doi"),
            data.get("external_id"),
            data.get("year"),
            data.get("journal"),
            data.get("abstract"),
            data.get("url"),
            data.get("citation_count"),
            data.get("source"),
            data.get("publication_type"),
            json.dumps(data.get("mesh_terms", [])),
            json.dumps(data.get("categories", [])),
            now,
            json.dumps(data.get("metadata", {})),
            data["id"]
        )
        return {"status": "success", "id": data["id"], "message": "Literature record updated"}
    
    elif entity == "search_term_optimization":
        await conn.execute("""
            UPDATE search_term_optimizations SET
                original_query = $1,
                optimized_terms = $2,
                optimization_context = $3,
                target_databases = $4,
                updated_at = $5,
                expires_at = $6,
                metadata = $7
            WHERE id = $8
        """,
            data["original_query"],
            json.dumps(data["optimized_terms"]),
            json.dumps(data.get("optimization_context", {})),
            json.dumps(data.get("target_databases", [])),
            now,
            data.get("expires_at"),
            json.dumps(data.get("metadata", {})),
            data["id"]
        )
        return {"status": "success", "id": data["id"], "message": "Search term optimization updated"}
    
    else:
        raise ValueError(f"Unknown update entity: {entity}")


async def _handle_delete(command: str, data: Dict[str, Any], conn: asyncpg.Connection) -> Dict[str, Any]:
    """Handle delete operations."""
    entity = command.replace("delete_", "")
    
    if "id" not in data:
        raise ValueError("ID required for delete")
    
    if entity == "project":
        await conn.execute("DELETE FROM projects WHERE id = $1", data["id"])
    elif entity == "research_topic":
        await conn.execute("DELETE FROM research_topics WHERE id = $1", data["id"])
    elif entity == "research_plan":
        await conn.execute("DELETE FROM research_plans WHERE id = $1", data["id"])
    elif entity == "task":
        await conn.execute("DELETE FROM tasks WHERE id = $1", data["id"])
    elif entity == "research_task":
        await conn.execute("DELETE FROM research_tasks WHERE id = $1", data["id"])
    elif entity == "literature_record":
        await conn.execute("DELETE FROM literature_records WHERE id = $1", data["id"])
    elif entity == "search_term_optimization":
        await conn.execute("DELETE FROM search_term_optimizations WHERE id = $1", data["id"])
    else:
        raise ValueError(f"Unknown delete entity: {entity}")
    
    return {"status": "success", "id": data["id"], "message": f"{entity.capitalize()} deleted"}


if __name__ == "__main__":
    # Example usage
    async def test():
        result = await database_write("create_project", json.dumps({"name": "Test Project", "description": "Test desc"}))
        print(result)
    
    asyncio.run(test())