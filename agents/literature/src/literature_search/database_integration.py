"""
Database integration module for storing and retrieving data via MCP protocol.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .models import SearchQuery

logger = logging.getLogger(__name__)


class DatabaseIntegration:
    """Handles database operations via MCP protocol."""
    
    def __init__(self, websocket, agent_id: str):
        """Initialize database integration with MCP websocket connection."""
        self.websocket = websocket
        self.agent_id = agent_id
        self.pending_responses: Dict[str, asyncio.Future] = {}
    
    async def get_cached_search_terms(self, source_type: str, source_id: str, original_query: str) -> Optional[List[str]]:
        """
        Retrieve cached search terms from database.
        
        Args:
            source_type: 'plan' or 'task'
            source_id: ID of the plan or task
            original_query: Original query to match against
            
        Returns:
            List of cached search terms if found and not expired, None otherwise
        """
        try:
            if not self.websocket:
                return None
            
            # Send request to database agent via MCP
            task_id = f"get_search_terms_{uuid.uuid4().hex[:8]}"
            db_request = {
                "type": "research_action",  # Use research_action instead of task_request
                "data": {
                    "task_id": task_id,
                    "context_id": f"literature_search_cache",
                    "agent_type": "database",  # Target the database agent
                    "action": f"get_search_terms_for_{source_type}",
                    "payload": {
                        f"{source_type}_id": source_id
                    }
                },
                "client_id": self.agent_id,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.websocket.send(json.dumps(db_request))
            
            # Wait for response using Future-based approach
            try:
                # Create future for this request
                future = asyncio.Future()
                self.pending_responses[task_id] = future
                
                # Wait for response with timeout
                response_data = await asyncio.wait_for(future, timeout=5.0)

                logger.info(f"****** Received database response for cached search terms: {response_data.get('task_id')} : {task_id} - {response_data.get('type')} - {response_data.get('result')} ******")

                if (response_data.get("type") == "task_result" and 
                    response_data.get("task_id") == task_id):
                    
                    result = response_data.get("result", {})
                    if result.get("status") == "completed":
                        optimizations = result.get("optimizations", [])
                        
                        # Find the most recent optimization for this query
                        for optimization in optimizations:
                            if optimization.get("original_query") == original_query:
                                # Check if expired
                                expires_at = optimization.get("expires_at")
                                if expires_at:
                                    try:
                                        # Handle both timezone-aware and naive datetime strings
                                        if expires_at.endswith('Z'):
                                            expires_at = expires_at.replace('Z', '+00:00')
                                        
                                        expiry_time = datetime.fromisoformat(expires_at)
                                        
                                        # Convert to UTC for comparison if timezone-aware
                                        if expiry_time.tzinfo:
                                            current_time = datetime.now(expiry_time.tzinfo)
                                        else:
                                            current_time = datetime.now()
                                            
                                        if current_time > expiry_time:
                                            continue  # Skip expired
                                    except (ValueError, TypeError) as e:
                                        logger.warning(f"Invalid expires_at format: {expires_at}, error: {e}")
                                        continue
                                
                                return optimization.get("optimized_terms", [])
                    
                    return None
                        
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for database response")
                return None
            except Exception as e:
                logger.error(f"Error receiving database response: {e}")
                return None
            finally:
                # Clean up pending response
                self.pending_responses.pop(task_id, None)
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving cached search terms: {e}")
            return None
    
    async def store_search_terms(self, source_type: str, source_id: str, original_query: str, 
                                 optimized_terms: List[str], optimization_context: Dict[str, Any],
                                 target_databases: List[str]) -> bool:
        """
        Store optimized search terms in database.
        
        Args:
            source_type: 'plan' or 'task'
            source_id: ID of the plan or task
            original_query: Original query
            optimized_terms: List of optimized search terms
            optimization_context: Context from AI optimization
            target_databases: Target databases for the search
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            if not self.websocket:
                logger.warning("MCP connection not available for storing search terms")
                return False
            
            logger.info(f"Attempting to store {len(optimized_terms)} search terms for {source_type} {source_id}")
            logger.debug(f"Search terms to store: {optimized_terms}")
            
            # Send request to database agent via MCP
            task_id = f"store_search_terms_{uuid.uuid4().hex[:8]}"
            db_request = {
                "type": "research_action",  # Use research_action instead of task_request
                "data": {
                    "task_id": task_id,
                    "context_id": f"literature_search_storage",
                    "agent_type": "database",  # Target the database agent
                    "action": "create_search_term_optimization",  # Use direct creation instead of store
                    "payload": {
                        "source_type": source_type,
                        "source_id": source_id,
                        "original_query": original_query,
                        "optimized_terms": optimized_terms,
                        "optimization_context": optimization_context,
                        "target_databases": target_databases,
                        "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
                        "metadata": {
                            "created_by": "literature_service",
                            "optimization_version": "1.0",
                            "session_type": "temporary_literature_search"
                        }
                    }
                },
                "client_id": self.agent_id,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Sending store search terms request with task_id: {task_id}")
            await self.websocket.send(json.dumps(db_request))
            
            # Wait for response using Future-based approach
            try:
                # Create future for this request
                future = asyncio.Future()
                self.pending_responses[task_id] = future
                
                logger.info(f"Waiting for database response for task_id: {task_id}")
                # Wait for response with timeout
                response_data = await asyncio.wait_for(future, timeout=5.0)
                
                logger.info(f"Received database response: {response_data}")
                
                if (response_data.get("type") == "task_result" and 
                    response_data.get("task_id") == task_id):
                    
                    result = response_data.get("result", {})
                    logger.info(f"Database operation result: {result}")
                    
                    if result.get("status") == "completed":
                        logger.info(f"Successfully stored search terms for {source_type} {source_id}")
                        return True
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        logger.warning(f"Failed to store search terms: {error_msg}")
                        return False
                else:
                    logger.warning(f"Unexpected response format or task_id mismatch: {response_data}")
                    return False
                        
            except asyncio.TimeoutError:
                logger.warning(f"Timeout waiting for database response to store search terms (task_id: {task_id})")
                return False
            except Exception as e:
                logger.error(f"Error receiving database response for storing search terms (task_id: {task_id}): {e}", exc_info=True)
                return False
            finally:
                # Clean up pending response
                removed_future = self.pending_responses.pop(task_id, None)
                if removed_future:
                    logger.debug(f"Cleaned up pending response for task_id: {task_id}")
            
            return False  # Default return if no successful response
            
        except Exception as e:
            logger.error(f"Error storing search terms: {e}", exc_info=True)
            return False
    
    async def store_literature_records(self, records: List[Dict[str, Any]], search_query: SearchQuery) -> List[str]:
        """
        Store literature records in database via MCP protocol.
        
        Args:
            records: List of normalized literature records
            search_query: Original search query for context
            
        Returns:
            List of error messages if any storage failures occurred
        """
        storage_errors = []
        stored_count = 0
        
        if not self.websocket:
            error_msg = "MCP connection not available for storing literature records"
            logger.warning(error_msg)
            return [error_msg]
        
        # We need a project_id for the database, but we only have lit_review_id
        # For now, we'll use the lit_review_id as a temporary project identifier
        # In a real implementation, you'd want to map lit_review_id to actual project_id
        potential_project_id = search_query.plan_id or search_query.lit_review_id
        
        # Ensure the project exists before trying to store literature records
        project_id = await self._ensure_project_exists(potential_project_id, search_query)
        
        logger.info(f"Storing {len(records)} literature records to database (project_id: {project_id})")
        
        # Process records one at a time to avoid overwhelming the database connection pool
        # This ensures we don't exhaust database connections
        logger.info(f"Processing {len(records)} records sequentially to avoid connection pool exhaustion")
        
        for record_idx, record in enumerate(records):
            try:
                # Skip records without an abstract
                if not record.get("abstract"):
                    logger.info(f"Skipping record without abstract: {record.get('title', 'Unknown title')[:60]}...")
                    continue

                # Prepare literature record data for database storage
                literature_record_data = {
                    "title": record.get("title", ""),
                    "authors": record.get("authors", []),
                    "project_id": project_id,
                    "doi": record.get("doi"),
                    "pmid": record.get("pmid"),
                    "arxiv_id": record.get("arxiv_id"),
                    "year": record.get("year"),
                    "journal": record.get("journal"),
                    "abstract": record.get("abstract"),
                    "url": record.get("url"),
                    "citation_count": record.get("citation_count", 0),
                    "source": record.get("source"),
                    "publication_type": record.get("publication_type"),
                    "mesh_terms": record.get("mesh_terms", []),
                    "categories": record.get("categories", []),
                    "metadata": {
                        "lit_review_id": search_query.lit_review_id,
                        "search_terms": getattr(search_query, 'search_terms', []),
                        "retrieval_timestamp": record.get("retrieval_timestamp"),
                        "raw_data": record.get("raw_data", {})
                    }
                }
                
                # Send to database via MCP
                task_id = f"store_lit_record_{uuid.uuid4().hex[:8]}"
                db_request = {
                    "type": "research_action",
                    "data": {
                        "task_id": task_id,
                        "context_id": f"literature_storage_{record_idx}",
                        "agent_type": "database",
                        "action": "create_literature_record",
                        "payload": literature_record_data
                    },
                    "client_id": self.agent_id,
                    "timestamp": datetime.now().isoformat()
                }
                
                await self.websocket.send(json.dumps(db_request))
                
                # Wait for response before sending the next record
                try:
                    future = asyncio.Future()
                    self.pending_responses[task_id] = future
                    
                    response_data = await asyncio.wait_for(future, timeout=15.0)  # Longer timeout for individual records
                    
                    if (response_data.get("type") == "task_result" and 
                        response_data.get("task_id") == task_id):
                        
                        result = response_data.get("result", {})
                        if result.get("status") == "completed":
                            stored_count += 1
                            logger.info(f"✅ Stored record {stored_count}/{len(records)}: {record.get('title', 'Unknown title')[:60]}...")
                        else:
                            error_msg = f"Failed to store record {record_idx+1}: {result.get('error', 'Unknown error')}"
                            storage_errors.append(error_msg)
                            logger.warning(f"❌ {error_msg}")
                    else:
                        error_msg = f"Unexpected response for record {record_idx+1}: {response_data}"
                        storage_errors.append(error_msg)
                        logger.warning(f"❌ {error_msg}")
                        
                except asyncio.TimeoutError:
                    error_msg = f"Timeout storing record {record_idx+1}"
                    storage_errors.append(error_msg)
                    logger.warning(f"⏰ {error_msg}")
                except Exception as e:
                    error_msg = f"Error storing record {record_idx+1}: {e}"
                    storage_errors.append(error_msg)
                    logger.error(f"💥 {error_msg}")
                finally:
                    # Clean up pending response
                    self.pending_responses.pop(task_id, None)
                
                # Add a delay between each record to prevent overwhelming the database
                await asyncio.sleep(0.2)  # 200ms delay between records
                        
            except Exception as e:
                error_msg = f"Error preparing record {record_idx+1} for storage: {e}"
                storage_errors.append(error_msg)
                logger.error(f"💥 {error_msg}")
        
        logger.info(f"Literature record storage completed: {stored_count}/{len(records)} stored successfully")
        if storage_errors:
            logger.warning(f"Storage errors encountered: {len(storage_errors)} failures")
        
        return storage_errors
    
    async def _ensure_project_exists(self, project_id: str, search_query: SearchQuery) -> str:
        """
        Ensure a project exists in the database, creating one if needed.
        Returns the project_id to use for literature records.
        """
        try:
            # For now, we'll create a default project and wait for the response
            # This prevents foreign key constraint violations
            logger.info(f"Ensuring project {project_id} exists for literature storage")
            
            # Create task to ensure project exists
            task_id = f"ensure_project_{uuid.uuid4().hex[:8]}"
            create_request = {
                "type": "research_action",
                "data": {
                    "task_id": task_id,
                    "context_id": f"project_creation_{int(time.time())}",
                    "agent_type": "database",
                    "action": "create_project",
                    "payload": {
                        "project_id": project_id,
                        "name": f"Literature Review Project",
                        "description": f"Auto-created project for literature search",
                        "status": "active",
                        "created_by": "literature-service"
                    }
                },
                "client_id": self.agent_id,
                "timestamp": datetime.now().isoformat()
            }
            
            # Send the request via websocket and wait for response
            if self.websocket:
                await self.websocket.send(json.dumps(create_request))
                logger.info(f"Sent project creation request for {project_id}")
                
                # Wait for response to get the actual created project ID
                try:
                    future = asyncio.Future()
                    self.pending_responses[task_id] = future
                    
                    response_data = await asyncio.wait_for(future, timeout=10.0)
                    
                    if (response_data.get("type") == "task_result" and 
                        response_data.get("task_id") == task_id):
                        
                        result = response_data.get("result", {})
                        if result.get("status") == "completed":
                            created_project_id = result.get("project_id")
                            if created_project_id:
                                logger.info(f"Project created successfully with ID: {created_project_id}")
                                return created_project_id
                            else:
                                logger.warning(f"Project creation succeeded but no project_id returned, using original: {project_id}")
                                return project_id
                        else:
                            error_msg = result.get('error', 'Unknown error')
                            logger.warning(f"Project creation failed: {error_msg}, using original project_id: {project_id}")
                            return project_id
                    else:
                        logger.warning(f"Unexpected response for project creation: {response_data}")
                        return project_id
                        
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout waiting for project creation response, using original project_id: {project_id}")
                    return project_id
                except Exception as e:
                    logger.error(f"Error waiting for project creation response: {e}")
                    return project_id
                finally:
                    # Clean up pending response
                    self.pending_responses.pop(task_id, None)
            else:
                logger.warning("No websocket connection available for project creation")
                return project_id
                
        except Exception as e:
            logger.error(f"Error ensuring project exists: {e}")
            # Return the original project_id as fallback
            return project_id
    
    def handle_task_result(self, data: Dict[str, Any]) -> bool:
        """Handle task result responses for pending database requests."""
        if data.get("type") == "task_result":
            task_id = data.get("task_id")
            if task_id in self.pending_responses:
                future = self.pending_responses.pop(task_id)
                if not future.done():
                    future.set_result(data)
                return True
        return False
