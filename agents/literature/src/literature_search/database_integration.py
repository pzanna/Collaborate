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
    
    async def store_initial_literature_results(self, lit_review_id: str, plan_id: str, records: List[Dict[str, Any]]) -> bool:
        """
        Store initial literature results (before AI review) in the research plan.
        
        Args:
            lit_review_id: ID of the literature review
            plan_id: ID of the research plan
            records: List of initial literature records (with abstracts, before AI review)
            
        Returns:
            True if storage was successful, False otherwise
        """
        logger.info(f"📥 INITIAL LITERATURE STORAGE: storing {len(records)} records for plan_id={plan_id}")
        
        if not self.websocket:
            logger.error("❌ WebSocket connection not available for storing initial literature results")
            return False
        
        if not plan_id:
            logger.error("❌ plan_id is required for storing initial literature results")
            return False
        
        if not lit_review_id:
            logger.error("❌ lit_review_id is required for storing initial literature results")
            return False
        
        if not records:
            logger.warning("⚠️ No initial records provided for storage")
            return True  # Empty results is not an error
        
        try:
            task_id = f"store_initial_literature_{uuid.uuid4().hex[:8]}"
            
            # Prepare the JSON payload to store in initial_literature_results column
            initial_results_json = {
                "lit_review_id": lit_review_id,
                "records": records,
                "metadata": {
                    "stored_by": "literature-service",
                    "storage_timestamp": datetime.now().isoformat(),
                    "record_count": len(records),
                    "records_with_abstracts": True,
                    "pre_ai_review": True
                }
            }
            
            # Send request to database agent via MCP
            db_request = {
                "type": "research_action",
                "data": {
                    "task_id": task_id,
                    "context_id": f"initial_literature_storage_{int(time.time())}",
                    "agent_type": "database",
                    "action": "store_initial_literature_results",
                    "payload": {
                        "plan_id": plan_id,
                        "initial_literature_results": initial_results_json
                    }
                },
                "client_id": self.agent_id,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"📤 Sending initial literature results storage request (task_id: {task_id})")
            logger.info(f"   └─ Storing {len(records)} records in research_plans.initial_literature_results (plan_id={plan_id})")
            await self.websocket.send(json.dumps(db_request))
            
            # Wait for response
            try:
                future = asyncio.Future()
                self.pending_responses[task_id] = future
                
                response_data = await asyncio.wait_for(future, timeout=10.0)
                
                logger.info(f"📥 Received initial storage response: {response_data}")
                
                if (response_data.get("type") == "task_result" and 
                    response_data.get("task_id") == task_id):
                    
                    result = response_data.get("result", {})
                    if result.get("status") == "completed":
                        logger.info(f"🎉 INITIAL LITERATURE JSON STORED: {len(records)} records → research_plans.initial_literature_results")
                        logger.info(f"   └─ Plan ID: {plan_id}, Lit Review ID: {lit_review_id}")
                        return True
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        logger.error(f"❌ Failed to store initial literature results: {error_msg}")
                        return False
                else:
                    logger.error(f"❌ Unexpected response format for initial literature storage: {response_data}")
                    return False
                    
            except asyncio.TimeoutError:
                logger.error(f"⏰ Timeout waiting for initial literature storage response (task_id: {task_id})")
                return False
            except Exception as e:
                logger.error(f"❌ Error receiving initial literature storage response: {e}")
                return False
            finally:
                self.pending_responses.pop(task_id, None)
                
        except Exception as e:
            logger.error(f"❌ Error storing initial literature results: {e}", exc_info=True)
            return False

    async def store_reviewed_literature_results(self, plan_id: str, reviewed_results: List[Dict[str, Any]]) -> bool:
        """
        Store reviewed literature results in the database.
        
        Args:
            plan_id: ID of the research plan
            reviewed_results: List of AI-reviewed literature results
            
        Returns:
            True if storage was successful, False otherwise
        """
        logger.info(f"🗄️ store_reviewed_literature_results called with plan_id: {plan_id}, {len(reviewed_results)} results")
        
        if not self.websocket:
            logger.error("❌ WebSocket connection not available for storing reviewed results")
            return False
        
        if not plan_id:
            logger.error("❌ plan_id is required for storing reviewed literature results")
            return False
        
        if not reviewed_results:
            logger.warning("⚠️ No reviewed results provided for storage")
            return True  # Empty results is not an error
        
        try:
            task_id = f"store_reviewed_literature_{uuid.uuid4().hex[:8]}"
            
            # Send request to database agent via MCP
            db_request = {
                "type": "research_action",
                "data": {
                    "task_id": task_id,
                    "context_id": f"literature_review_storage_{int(time.time())}",
                    "agent_type": "database",
                    "action": "store_reviewed_literature_results",
                    "payload": {
                        "plan_id": plan_id,
                        "reviewed_results": reviewed_results,
                        "metadata": {
                            "stored_by": "literature-service",
                            "storage_timestamp": datetime.now().isoformat(),
                            "result_count": len(reviewed_results)
                        }
                    }
                },
                "client_id": self.agent_id,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"📤 Sending reviewed literature results storage request (task_id: {task_id})")
            await self.websocket.send(json.dumps(db_request))
            
            # Wait for response
            try:
                future = asyncio.Future()
                self.pending_responses[task_id] = future
                
                response_data = await asyncio.wait_for(future, timeout=10.0)
                
                logger.info(f"📥 Received storage response: {response_data}")
                
                if (response_data.get("type") == "task_result" and 
                    response_data.get("task_id") == task_id):
                    
                    result = response_data.get("result", {})
                    if result.get("status") == "completed":
                        logger.info(f"✅ Successfully stored {len(reviewed_results)} reviewed literature results")
                        return True
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        logger.error(f"❌ Failed to store reviewed literature results: {error_msg}")
                        return False
                else:
                    logger.error(f"❌ Unexpected response format: {response_data}")
                    return False
                    
            except asyncio.TimeoutError:
                logger.error(f"⏰ Timeout waiting for reviewed literature storage response (task_id: {task_id})")
                return False
            except Exception as e:
                logger.error(f"❌ Error receiving storage response: {e}")
                return False
            finally:
                self.pending_responses.pop(task_id, None)
                
        except Exception as e:
            logger.error(f"❌ Error storing reviewed literature results: {e}", exc_info=True)
            return False
    
    async def store_literature_records(self, records: List[Dict[str, Any]], search_query: SearchQuery) -> List[str]:
        """
        Store literature records in the database.
        
        Args:
            records: List of literature records to store
            search_query: Original search query for context
            
        Returns:
            List of error messages if any storage operations failed
        """
        logger.info(f"🗄️ store_literature_records called with {len(records)} records")
        logger.info(f"   search_query.lit_review_id: {search_query.lit_review_id}")
        logger.info(f"   search_query.plan_id: {search_query.plan_id}")
        
        if not records:
            logger.warning("No records provided for storage")
            return ["No records provided"]
        
        if not self.websocket:
            logger.error("❌ WebSocket connection not available for storing literature records")
            return ["WebSocket connection not available"]
        
        if not search_query.lit_review_id:
            logger.error("❌ lit_review_id is required for storing literature records")
            return ["lit_review_id is required"]
        
        errors = []
        
        try:
            # Ensure project exists first if we have a plan_id
            project_id = None
            if search_query.plan_id:
                project_id = await self._ensure_project_exists(search_query.plan_id, search_query)
            
            task_id = f"store_literature_{uuid.uuid4().hex[:8]}"
            
            # Send request to database agent via MCP
            db_request = {
                "type": "research_action",
                "data": {
                    "task_id": task_id,
                    "context_id": f"literature_storage_{int(time.time())}",
                    "agent_type": "database",
                    "action": "store_literature_records",
                    "payload": {
                        "lit_review_id": search_query.lit_review_id,
                        "plan_id": search_query.plan_id,
                        "project_id": project_id,
                        "records": records,
                        "search_context": {
                            "query": search_query.query,
                            "sources": search_query.sources,
                            "filters": search_query.filters
                        },
                        "metadata": {
                            "stored_by": "literature-service",
                            "storage_timestamp": datetime.now().isoformat(),
                            "record_count": len(records)
                        }
                    }
                },
                "client_id": self.agent_id,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"📤 Sending literature records storage request (task_id: {task_id})")
            await self.websocket.send(json.dumps(db_request))
            
            # Wait for response
            try:
                future = asyncio.Future()
                self.pending_responses[task_id] = future
                
                response_data = await asyncio.wait_for(future, timeout=10.0)
                
                logger.info(f"📥 Received storage response: {response_data}")
                
                if (response_data.get("type") == "task_result" and 
                    response_data.get("task_id") == task_id):
                    
                    result = response_data.get("result", {})
                    if result.get("status") == "completed":
                        stored_count = result.get("stored_count", 0)
                        logger.info(f"✅ Successfully stored {stored_count} literature records")
                        
                        # Check if all records were stored
                        if stored_count < len(records):
                            errors.append(f"Only {stored_count} of {len(records)} records were stored")
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        logger.error(f"❌ Failed to store literature records: {error_msg}")
                        errors.append(f"Storage failed: {error_msg}")
                else:
                    logger.error(f"❌ Unexpected response format: {response_data}")
                    errors.append("Unexpected response format from database")
                    
            except asyncio.TimeoutError:
                logger.error(f"⏰ Timeout waiting for literature storage response (task_id: {task_id})")
                errors.append("Timeout waiting for database response")
            except Exception as e:
                logger.error(f"❌ Error receiving storage response: {e}")
                errors.append(f"Error receiving storage response: {e}")
            finally:
                self.pending_responses.pop(task_id, None)
                
        except Exception as e:
            logger.error(f"❌ Error storing literature records: {e}", exc_info=True)
            errors.append(f"Error storing literature records: {e}")
        
        return errors
    
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
        logger.info(f"🔄 Database integration received task result: type={data.get('type')}, task_id={data.get('task_id')}")
        logger.info(f"   Pending responses: {list(self.pending_responses.keys())}")
        
        if data.get("type") == "task_result":
            task_id = data.get("task_id")
            # Only handle task results that we're actually waiting for
            if task_id in self.pending_responses:
                future = self.pending_responses.pop(task_id)
                if not future.done():
                    future.set_result(data)
                    logger.info(f"✅ Successfully resolved future for task_id: {task_id}")
                    return True
                else:
                    logger.warning(f"⚠️ Future already done for task_id: {task_id}")
                    return True  # We handled it, even if already done
            else:
                logger.warning(f"❌ No pending response found for task_id: {task_id}")
                return False  # We didn't handle this task result
        else:
            logger.debug(f"🔍 Non-task_result message: {data.get('type')}")
            return False  # We didn't handle this message
        return False
