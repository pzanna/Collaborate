#!/usr/bin/env python3
"""
MCP Server implementation for Database Service

This module implements an MCP (Model Context Protocol) server that exposes
all database operations as MCP tools. It follows the FastMCP pattern for
simple and maintainable code.

The server exposes all functions from database_tools.py as MCP tools:
- create_project, update_project, delete_project
- create_research_topic, update_research_topic, delete_research_topic
- create_research_plan, update_research_plan, delete_research_plan
- create_task, update_task, delete_task
- create_research_task, update_research_task, delete_research_task
- create_literature_record, update_literature_record, delete_literature_record
- create_search_term_optimization, update_search_term_optimization, delete_search_term_optimization
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP

# Import the database tools
from database_tools import database_write

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

mcp = FastMCP(name="database", stateless_http=True)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/eunice")

@mcp.tool()
async def create_project(
    name: str,
    description: Optional[str] = None,
    status: str = "active",
    metadata: Optional[Dict[str, Any]] = None,
    id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new project in the database."""
    data = {
        "name": name,
        "description": description,
        "status": status,
        "metadata": metadata or {},
    }
    if id:
        data["id"] = id
    
    result_json = await database_write("create_project", json.dumps(data))
    return json.loads(result_json)


@mcp.tool()
async def update_project(
    id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Update an existing project in the database."""
    data = {"id": id}
    if name is not None:
        data["name"] = name
    if description is not None:
        data["description"] = description
    if status is not None:
        data["status"] = status
    if metadata is not None:
        data["metadata"] = metadata
    
    result_json = await database_write("update_project", json.dumps(data))
    return json.loads(result_json)


@mcp.tool()
async def delete_project(id: str) -> Dict[str, Any]:
    """Delete a project from the database."""
    data = {"id": id}
    result_json = await database_write("delete_project", json.dumps(data))
    return json.loads(result_json)


@mcp.tool()
async def create_research_topic(
    project_id: str,
    name: str,
    description: Optional[str] = None,
    status: str = "active",
    metadata: Optional[Dict[str, Any]] = None,
    id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new research topic in the database."""
    data = {
        "project_id": project_id,
        "name": name,
        "description": description,
        "status": status,
        "metadata": metadata or {},
    }
    if id:
        data["id"] = id
    
    result_json = await database_write("create_research_topic", json.dumps(data))
    return json.loads(result_json)


@mcp.tool()
async def update_research_topic(
    id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Update an existing research topic in the database."""
    data = {"id": id}
    if name is not None:
        data["name"] = name
    if description is not None:
        data["description"] = description
    if status is not None:
        data["status"] = status
    if metadata is not None:
        data["metadata"] = metadata
    
    result_json = await database_write("update_research_topic", json.dumps(data))
    return json.loads(result_json)


@mcp.tool()
async def delete_research_topic(id: str) -> Dict[str, Any]:
    """Delete a research topic from the database."""
    data = {"id": id}
    result_json = await database_write("delete_research_topic", json.dumps(data))
    return json.loads(result_json)


@mcp.tool()
async def create_research_plan(
    topic_id: str,
    name: str,
    description: Optional[str] = None,
    plan_type: str = "comprehensive",
    status: str = "draft",
    plan_approved: bool = False,
    estimated_cost: float = 0.0,
    actual_cost: float = 0.0,
    metadata: Optional[Dict[str, Any]] = None,
    plan_structure: Optional[Dict[str, Any]] = None,
    initial_literature_results: Optional[Dict[str, Any]] = None,
    reviewed_literature_results: Optional[Dict[str, Any]] = None,
    id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new research plan in the database."""
    data = {
        "topic_id": topic_id,
        "name": name,
        "description": description,
        "plan_type": plan_type,
        "status": status,
        "plan_approved": plan_approved,
        "estimated_cost": estimated_cost,
        "actual_cost": actual_cost,
        "metadata": metadata or {},
        "plan_structure": plan_structure or {},
        "initial_literature_results": initial_literature_results or {},
        "reviewed_literature_results": reviewed_literature_results or {},
    }
    if id:
        data["id"] = id
    
    result_json = await database_write("create_research_plan", json.dumps(data))
    return json.loads(result_json)


@mcp.tool()
async def update_research_plan(
    id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    plan_type: Optional[str] = None,
    status: Optional[str] = None,
    plan_approved: Optional[bool] = None,
    estimated_cost: Optional[float] = None,
    actual_cost: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None,
    plan_structure: Optional[Dict[str, Any]] = None,
    initial_literature_results: Optional[Dict[str, Any]] = None,
    reviewed_literature_results: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Update an existing research plan in the database."""
    data = {"id": id}
    if name is not None:
        data["name"] = name
    if description is not None:
        data["description"] = description
    if plan_type is not None:
        data["plan_type"] = plan_type
    if status is not None:
        data["status"] = status
    if plan_approved is not None:
        data["plan_approved"] = plan_approved
    if estimated_cost is not None:
        data["estimated_cost"] = estimated_cost
    if actual_cost is not None:
        data["actual_cost"] = actual_cost
    if metadata is not None:
        data["metadata"] = metadata
    if plan_structure is not None:
        data["plan_structure"] = plan_structure
    if initial_literature_results is not None:
        data["initial_literature_results"] = initial_literature_results
    if reviewed_literature_results is not None:
        data["reviewed_literature_results"] = reviewed_literature_results
    
    result_json = await database_write("update_research_plan", json.dumps(data))
    return json.loads(result_json)


@mcp.tool()
async def delete_research_plan(id: str) -> Dict[str, Any]:
    """Delete a research plan from the database."""
    data = {"id": id}
    result_json = await database_write("delete_research_plan", json.dumps(data))
    return json.loads(result_json)


@mcp.tool()
async def create_task(
    plan_id: str,
    name: str,
    description: Optional[str] = None,
    task_type: str = "research",
    task_order: int = 1,
    status: str = "pending",
    metadata: Optional[Dict[str, Any]] = None,
    id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new task in the database."""
    data = {
        "plan_id": plan_id,
        "name": name,
        "description": description,
        "task_type": task_type,
        "task_order": task_order,
        "status": status,
        "metadata": metadata or {},
    }
    if id:
        data["id"] = id
    
    result_json = await database_write("create_task", json.dumps(data))
    return json.loads(result_json)


@mcp.tool()
async def update_task(
    id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    task_type: Optional[str] = None,
    task_order: Optional[int] = None,
    status: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Update an existing task in the database."""
    data = {"id": id}
    if name is not None:
        data["name"] = name
    if description is not None:
        data["description"] = description
    if task_type is not None:
        data["task_type"] = task_type
    if task_order is not None:
        data["task_order"] = task_order
    if status is not None:
        data["status"] = status
    if metadata is not None:
        data["metadata"] = metadata
    
    result_json = await database_write("update_task", json.dumps(data))
    return json.loads(result_json)


@mcp.tool()
async def delete_task(id: str) -> Dict[str, Any]:
    """Delete a task from the database."""
    data = {"id": id}
    result_json = await database_write("delete_task", json.dumps(data))
    return json.loads(result_json)


@mcp.tool()
async def create_research_task(
    plan_id: str,
    name: str,
    description: Optional[str] = None,
    task_type: str = "research",
    task_order: int = 1,
    status: str = "pending",
    stage: str = "planning",
    metadata: Optional[Dict[str, Any]] = None,
    id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new research task in the database."""
    data = {
        "plan_id": plan_id,
        "name": name,
        "description": description,
        "task_type": task_type,
        "task_order": task_order,
        "status": status,
        "stage": stage,
        "metadata": metadata or {},
    }
    if id:
        data["id"] = id
    
    result_json = await database_write("create_research_task", json.dumps(data))
    return json.loads(result_json)


@mcp.tool()
async def update_research_task(
    id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    task_type: Optional[str] = None,
    task_order: Optional[int] = None,
    status: Optional[str] = None,
    stage: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Update an existing research task in the database."""
    data = {"id": id}
    if name is not None:
        data["name"] = name
    if description is not None:
        data["description"] = description
    if task_type is not None:
        data["task_type"] = task_type
    if task_order is not None:
        data["task_order"] = task_order
    if status is not None:
        data["status"] = status
    if stage is not None:
        data["stage"] = stage
    if metadata is not None:
        data["metadata"] = metadata
    
    result_json = await database_write("update_research_task", json.dumps(data))
    return json.loads(result_json)


@mcp.tool()
async def delete_research_task(id: str) -> Dict[str, Any]:
    """Delete a research task from the database."""
    data = {"id": id}
    result_json = await database_write("delete_research_task", json.dumps(data))
    return json.loads(result_json)


@mcp.tool()
async def create_literature_record(
    title: str,
    project_id: str,
    authors: Optional[List[str]] = None,
    doi: Optional[str] = None,
    external_id: Optional[str] = None,
    year: Optional[int] = None,
    journal: Optional[str] = None,
    abstract: Optional[str] = None,
    url: Optional[str] = None,
    citation_count: int = 0,
    source: Optional[str] = None,
    publication_type: Optional[str] = None,
    mesh_terms: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new literature record in the database."""
    data = {
        "title": title,
        "project_id": project_id,
        "authors": authors or [],
        "doi": doi,
        "external_id": external_id,
        "year": year,
        "journal": journal,
        "abstract": abstract,
        "url": url,
        "citation_count": citation_count,
        "source": source,
        "publication_type": publication_type,
        "mesh_terms": mesh_terms or [],
        "categories": categories or [],
        "metadata": metadata or {},
    }
    if id:
        data["id"] = id
    
    result_json = await database_write("create_literature_record", json.dumps(data))
    return json.loads(result_json)


@mcp.tool()
async def update_literature_record(
    id: str,
    title: Optional[str] = None,
    authors: Optional[List[str]] = None,
    doi: Optional[str] = None,
    external_id: Optional[str] = None,
    year: Optional[int] = None,
    journal: Optional[str] = None,
    abstract: Optional[str] = None,
    url: Optional[str] = None,
    citation_count: Optional[int] = None,
    source: Optional[str] = None,
    publication_type: Optional[str] = None,
    mesh_terms: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Update an existing literature record in the database."""
    data = {"id": id}
    if title is not None:
        data["title"] = title
    if authors is not None:
        data["authors"] = authors
    if doi is not None:
        data["doi"] = doi
    if external_id is not None:
        data["external_id"] = external_id
    if year is not None:
        data["year"] = year
    if journal is not None:
        data["journal"] = journal
    if abstract is not None:
        data["abstract"] = abstract
    if url is not None:
        data["url"] = url
    if citation_count is not None:
        data["citation_count"] = citation_count
    if source is not None:
        data["source"] = source
    if publication_type is not None:
        data["publication_type"] = publication_type
    if mesh_terms is not None:
        data["mesh_terms"] = mesh_terms
    if categories is not None:
        data["categories"] = categories
    if metadata is not None:
        data["metadata"] = metadata
    
    result_json = await database_write("update_literature_record", json.dumps(data))
    return json.loads(result_json)


@mcp.tool()
async def delete_literature_record(id: str) -> Dict[str, Any]:
    """Delete a literature record from the database."""
    data = {"id": id}
    result_json = await database_write("delete_literature_record", json.dumps(data))
    return json.loads(result_json)


@mcp.tool()
async def create_search_term_optimization(
    source_type: str,
    source_id: str,
    original_query: str,
    optimized_terms: Dict[str, Any],
    optimization_context: Optional[Dict[str, Any]] = None,
    target_databases: Optional[List[str]] = None,
    expires_at: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new search term optimization in the database."""
    data = {
        "source_type": source_type,
        "source_id": source_id,
        "original_query": original_query,
        "optimized_terms": optimized_terms,
        "optimization_context": optimization_context or {},
        "target_databases": target_databases or [],
        "expires_at": expires_at,
        "metadata": metadata or {},
    }
    if id:
        data["id"] = id
    
    result_json = await database_write("create_search_term_optimization", json.dumps(data))
    return json.loads(result_json)


@mcp.tool()
async def update_search_term_optimization(
    id: str,
    original_query: Optional[str] = None,
    optimized_terms: Optional[Dict[str, Any]] = None,
    optimization_context: Optional[Dict[str, Any]] = None,
    target_databases: Optional[List[str]] = None,
    expires_at: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Update an existing search term optimization in the database."""
    data = {"id": id}
    if original_query is not None:
        data["original_query"] = original_query
    if optimized_terms is not None:
        data["optimized_terms"] = optimized_terms
    if optimization_context is not None:
        data["optimization_context"] = optimization_context
    if target_databases is not None:
        data["target_databases"] = target_databases
    if expires_at is not None:
        data["expires_at"] = expires_at
    if metadata is not None:
        data["metadata"] = metadata
    
    result_json = await database_write("update_search_term_optimization", json.dumps(data))
    return json.loads(result_json)


@mcp.tool()
async def delete_search_term_optimization(id: str) -> Dict[str, Any]:
    """Delete a search term optimization from the database."""
    data = {"id": id}
    result_json = await database_write("delete_search_term_optimization", json.dumps(data))
    return json.loads(result_json)


def main():
    """Main entry point for the MCP server."""
    import os
    
    logger.info("Starting Database MCP Server...")
    
    # Get host and port from environment variables
    host = os.getenv("SERVICE_HOST", "0.0.0.0")
    port = int(os.getenv("SERVICE_PORT", "8010"))
    
    logger.info(f"Starting MCP server on {host}:{port}/mcp")
    
    # Configure the server settings
    mcp.settings.host = host
    mcp.settings.port = port
    mcp.settings.streamable_http_path = "/mcp"
    
    # Run the server with streamable-http transport
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
