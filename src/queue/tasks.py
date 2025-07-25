"""
Research Task Definitions for Queue System

This module defines the actual tasks that can be executed
asynchronously by the RQ workers.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import time

from rq import get_current_job
from src.mcp.client import MCPClient
from src.mcp.protocols import ResearchAction
from src.queue.config import redis_conn

# Setup logging
logger = logging.getLogger(__name__)

# Global MCP client instance for workers
mcp_client: Optional[MCPClient] = None

def get_mcp_client() -> MCPClient:
    """Get or create MCP client instance."""
    global mcp_client
    
    if mcp_client is None:
        mcp_client = MCPClient()
    
    return mcp_client

def update_job_progress(progress: int, stage: str = "", message: str = ""):
    """Update the current job's progress."""
    job = get_current_job()
    if job:
        job.meta['progress'] = progress
        job.meta['stage'] = stage
        job.meta['message'] = message
        job.meta['updated_at'] = datetime.utcnow().isoformat()
        job.save_meta()

def literature_search_task(query: str, search_type: str = "academic", 
                          max_results: int = 20, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Execute literature search task asynchronously.
    
    Args:
        query: Search query string
        search_type: Type of search (academic, patents, etc.)
        max_results: Maximum number of results to return
        filters: Additional filters (year range, document type, etc.)
    
    Returns:
        Dict containing search results and metadata
    """
    logger.info(f"Starting literature search task: {query}")
    
    # Initialize task_id at function start
    task_id = f"lit_search_{int(time.time())}"
    
    try:
        # Update progress
        update_job_progress(10, "initializing", "Setting up literature search")
        
        # Create research action
        research_action = ResearchAction(
            task_id=task_id,
            context_id=f"ctx_{task_id}",
            agent_type="literature",
            action="search_literature",
            payload={
                "query": query,
                "search_type": search_type,
                "max_results": max_results,
                "filters": filters or {}
            },
            priority="normal"
        )
        
        update_job_progress(25, "connecting", "Connecting to MCP server")
        
        # Get MCP client and connect
        client = get_mcp_client()
        
        # Run async operations in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Connect if needed
            if not client.is_connected:
                connected = loop.run_until_complete(client.connect())
                if not connected:
                    raise Exception("Failed to connect to MCP server")
            
            update_job_progress(40, "submitting", "Submitting search request")
            
            # Submit the task
            success = loop.run_until_complete(client.send_task(research_action))
            if not success:
                raise Exception("Failed to submit task to MCP server")
            
            update_job_progress(60, "processing", "Literature search in progress")
            
            # Monitor task progress
            start_time = time.time()
            timeout = 600  # 10 minutes timeout
            
            while time.time() - start_time < timeout:
                status_response = loop.run_until_complete(client.get_task_status(task_id))
                
                if status_response is None:
                    time.sleep(5)
                    continue
                
                status = status_response.get("status", "unknown")
                
                if status == "completed":
                    update_job_progress(100, "completed", "Literature search completed")
                    
                    result = status_response.get("result", {})
                    return {
                        "success": True,
                        "task_id": task_id,
                        "query": query,
                        "results": result,
                        "metadata": {
                            "search_type": search_type,
                            "max_results": max_results,
                            "filters": filters,
                            "execution_time": time.time() - start_time,
                            "completed_at": datetime.utcnow().isoformat()
                        }
                    }
                    
                elif status == "failed":
                    error_msg = status_response.get("error", "Unknown error")
                    raise Exception(f"Literature search failed: {error_msg}")
                
                # Update progress based on agent response
                progress = status_response.get("progress", 60)
                stage = status_response.get("stage", "processing")
                update_job_progress(min(90, max(60, progress)), stage, "Search in progress")
                
                time.sleep(5)  # Poll every 5 seconds
            
            # Timeout reached
            raise Exception(f"Literature search timed out after {timeout} seconds")
            
        finally:
            loop.close()
    
    except Exception as e:
        logger.error(f"Literature search task failed: {str(e)}")
        update_job_progress(0, "failed", str(e))
        return {
            "success": False,
            "task_id": task_id,
            "query": query,
            "error": str(e),
            "metadata": {
                "search_type": search_type,
                "max_results": max_results,
                "filters": filters,
                "failed_at": datetime.utcnow().isoformat()
            }
        }

def research_planning_task(research_question: str, context: str = "", 
                          requirements: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Execute research planning task asynchronously.
    
    Args:
        research_question: The main research question
        context: Additional context information
        requirements: Specific requirements or constraints
    
    Returns:
        Dict containing research plan and metadata
    """
    logger.info(f"Starting research planning task: {research_question}")
    
    # Initialize task_id at function start
    task_id = f"plan_{int(time.time())}"
    
    try:
        update_job_progress(10, "initializing", "Setting up research planning")
        
        research_action = ResearchAction(
            task_id=task_id,
            context_id=f"ctx_{task_id}",
            agent_type="planning",
            action="create_research_plan",
            payload={
                "research_question": research_question,
                "context": context,
                "requirements": requirements or {}
            },
            priority="normal"
        )
        
        update_job_progress(25, "connecting", "Connecting to planning agent")
        
        client = get_mcp_client()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            if not client.is_connected:
                connected = loop.run_until_complete(client.connect())
                if not connected:
                    raise Exception("Failed to connect to MCP server")
            
            update_job_progress(40, "submitting", "Submitting planning request")
            
            success = loop.run_until_complete(client.send_task(research_action))
            if not success:
                raise Exception("Failed to submit planning task")
            
            update_job_progress(60, "planning", "Generating research plan")
            
            # Monitor with longer timeout for planning tasks
            start_time = time.time()
            timeout = 900  # 15 minutes for planning
            
            while time.time() - start_time < timeout:
                status_response = loop.run_until_complete(client.get_task_status(task_id))
                
                if status_response is None:
                    time.sleep(10)
                    continue
                
                status = status_response.get("status", "unknown")
                
                if status == "completed":
                    update_job_progress(100, "completed", "Research plan completed")
                    
                    result = status_response.get("result", {})
                    return {
                        "success": True,
                        "task_id": task_id,
                        "research_question": research_question,
                        "plan": result,
                        "metadata": {
                            "context": context,
                            "requirements": requirements,
                            "execution_time": time.time() - start_time,
                            "completed_at": datetime.utcnow().isoformat()
                        }
                    }
                    
                elif status == "failed":
                    error_msg = status_response.get("error", "Unknown error")
                    raise Exception(f"Research planning failed: {error_msg}")
                
                progress = status_response.get("progress", 60)
                stage = status_response.get("stage", "planning")
                update_job_progress(min(90, max(60, progress)), stage, "Planning in progress")
                
                time.sleep(10)  # Poll every 10 seconds for planning
            
            raise Exception(f"Research planning timed out after {timeout} seconds")
            
        finally:
            loop.close()
    
    except Exception as e:
        logger.error(f"Research planning task failed: {str(e)}")
        update_job_progress(0, "failed", str(e))
        return {
            "success": False,
            "task_id": task_id,
            "research_question": research_question,
            "error": str(e),
            "metadata": {
                "context": context,
                "requirements": requirements,
                "failed_at": datetime.utcnow().isoformat()
            }
        }

def data_analysis_task(dataset: str, analysis_type: str, 
                      parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Execute data analysis task asynchronously.
    
    Args:
        dataset: Dataset identifier or path
        analysis_type: Type of analysis to perform
        parameters: Analysis parameters
    
    Returns:
        Dict containing analysis results and metadata
    """
    logger.info(f"Starting data analysis task: {analysis_type} on {dataset}")
    
    # Initialize task_id at function start
    task_id = f"analysis_{int(time.time())}"
    
    try:
        update_job_progress(10, "initializing", "Setting up data analysis")
        
        research_action = ResearchAction(
            task_id=task_id,
            context_id=f"ctx_{task_id}",
            agent_type="executor",
            action="analyze_data",
            payload={
                "dataset": dataset,
                "analysis_type": analysis_type,
                "parameters": parameters or {}
            },
            priority="normal"
        )
        
        update_job_progress(25, "connecting", "Connecting to analysis engine")
        
        client = get_mcp_client()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            if not client.is_connected:
                connected = loop.run_until_complete(client.connect())
                if not connected:
                    raise Exception("Failed to connect to MCP server")
            
            update_job_progress(40, "submitting", "Submitting analysis request")
            
            success = loop.run_until_complete(client.send_task(research_action))
            if not success:
                raise Exception("Failed to submit analysis task")
            
            update_job_progress(60, "analyzing", "Data analysis in progress")
            
            start_time = time.time()
            timeout = 1800  # 30 minutes for data analysis
            
            while time.time() - start_time < timeout:
                status_response = loop.run_until_complete(client.get_task_status(task_id))
                
                if status_response is None:
                    time.sleep(15)
                    continue
                
                status = status_response.get("status", "unknown")
                
                if status == "completed":
                    update_job_progress(100, "completed", "Data analysis completed")
                    
                    result = status_response.get("result", {})
                    return {
                        "success": True,
                        "task_id": task_id,
                        "dataset": dataset,
                        "analysis_type": analysis_type,
                        "results": result,
                        "metadata": {
                            "parameters": parameters,
                            "execution_time": time.time() - start_time,
                            "completed_at": datetime.utcnow().isoformat()
                        }
                    }
                    
                elif status == "failed":
                    error_msg = status_response.get("error", "Unknown error")
                    raise Exception(f"Data analysis failed: {error_msg}")
                
                progress = status_response.get("progress", 60)
                stage = status_response.get("stage", "analyzing")
                update_job_progress(min(90, max(60, progress)), stage, "Analysis in progress")
                
                time.sleep(15)  # Poll every 15 seconds for analysis
            
            raise Exception(f"Data analysis timed out after {timeout} seconds")
            
        finally:
            loop.close()
    
    except Exception as e:
        logger.error(f"Data analysis task failed: {str(e)}")
        update_job_progress(0, "failed", str(e))
        return {
            "success": False,
            "task_id": task_id,
            "dataset": dataset,
            "analysis_type": analysis_type,
            "error": str(e),
            "metadata": {
                "parameters": parameters,
                "failed_at": datetime.utcnow().isoformat()
            }
        }
