"""
Task processor for Research Manager Service.

This module handles parsing and routing of incoming tasks, including:
- Message format detection and normalization
- Task type identification and routing
- Legacy format support
- Task result handling and workflow continuation
"""

import logging
import traceback
from datetime import datetime
from typing import Any, Dict

from .models import ResearchStage

logger = logging.getLogger(__name__)


class TaskProcessor:
    """Processes and routes incoming tasks for Research Manager."""
    
    def __init__(self, service_ref):
        """Initialize with reference to main service."""
        self.service = service_ref
    
    async def process_research_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a research coordination task."""
        try:
            # Handle MCP server task format
            task_type = task_data.get("type", "")
            
            logger.info(f"Processing message type: {task_type}")
            logger.info(f"Full task data: {task_data}")
            
            # Handle MCP control messages (don't process as tasks)
            if task_type in ["registration_confirmed", "heartbeat", "ping", "pong"]:
                logger.info(f"Received MCP control message: {task_type}")
                return {
                    "status": "acknowledged",
                    "message_type": task_type,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Handle research_action messages from MCP server
            if task_type == "research_action":
                return await self._handle_research_action(task_data)
            
            # Handle task_request messages from MCP server
            elif task_type == "task_request":
                logger.info(f"Received task request from MCP server")
                return await self._handle_task_request(task_data)
            
            # Handle task_result messages from delegated agents
            elif task_type == "task_result":
                logger.info(f"Received task result from delegated agent")
                return await self._handle_task_result(task_data)
            
            # Handle ping
            elif task_type == "ping":
                return {"status": "alive", "timestamp": datetime.now().isoformat()}
            
            # Unknown message type
            else:
                return {
                    "status": "failed",
                    "error": f"Unknown message type: {task_type}",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error processing research task: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_research_action(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle research_action messages from MCP server."""
        data = task_data.get("data", {})
        action = data.get("action", "")
        task_id = data.get("task_id", "")
        context_id = data.get("context_id", "")
        payload = data.get("payload", {})
        
        logger.info(f"Processing research action: {action} for task_id: {task_id}")
        
        if action == "coordinate_research":
            # Add task_id from MCP message structure to payload
            payload["task_id"] = task_id
            return await self._handle_coordinate_research(payload)
        elif action == "estimate_costs":
            return await self.service.task_handlers.handle_estimate_costs(payload)
        elif action == "track_progress":
            return await self.service.task_handlers.handle_track_progress(payload)
        elif action == "delegate_tasks":
            return await self.service.task_handlers.handle_delegate_tasks(payload)
        elif action == "manage_workflows":
            return await self.service.task_handlers.handle_manage_workflows(payload)
        elif action == "approve_actions":
            return await self.service.task_handlers.handle_approve_actions(payload)
        else:
            return {
                "status": "failed",
                "error": f"Unknown research action: {action}",
                "timestamp": datetime.now().isoformat()
            }

    async def _handle_task_request(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle legacy task_request format."""
        task_id = task_data.get("task_id", "")
        action = task_data.get("task_type", "")
        data = task_data.get("data", {})
        context_id = task_data.get("context_id", "")
        
        # Include task_id in data for handler
        data["task_id"] = task_id
        data["context_id"] = context_id
        
        if action == "coordinate_research":
            return await self._handle_coordinate_research(data)
        elif action == "estimate_costs":
            return await self.service.task_handlers.handle_estimate_costs(data)
        elif action == "track_progress":
            return await self.service.task_handlers.handle_track_progress(data)
        elif action == "delegate_tasks":
            return await self.service.task_handlers.handle_delegate_tasks(data)
        elif action == "manage_workflows":
            return await self.service.task_handlers.handle_manage_workflows(data)
        elif action == "approve_actions":
            return await self.service.task_handlers.handle_approve_actions(data)
        else:
            return {
                "status": "failed",
                "error": f"Unknown task type: {action}",
                "timestamp": datetime.now().isoformat()
            }
           
    async def _handle_coordinate_research(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle research coordination request."""
        try:
            # Extract task information from API Gateway payload format
            task_id = data.get("task_id", "")
            
            # Map API Gateway payload to Research Manager expected format
            topic_id = data.get("topic_id", "")
            topic_name = data.get("topic_name", "")
            topic_description = data.get("topic_description", "")
            plan_id = data.get("plan_id", "")
            research_plan = data.get("research_plan", {})
            task_type = data.get("task_type", "research")
            depth = data.get("depth", "standard")

            # API Gateway format - derive parameters from topic data
            task_name = topic_name
            task_description = topic_description
            topic_id = topic_id  # Use topic_id as plan reference
            user_id = "api_user"  # Default for API requests. TODO: Extract from auth context if available
            max_results = 50 if depth == "phd" else 25 if depth == "masters" else 10
            
            if not task_id:
                return {
                    "status": "failed",
                    "error": "Task ID is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            logger.info(f"Coordinating research for task {task_id}")
            logger.info(f"Research plan received: {research_plan}")
            
            # Check if research plan is empty and needs to be fetched from database
            if not research_plan or research_plan == {}:
                logger.info(f"Research plan is empty, attempting to fetch from database using topic_id: {topic_id}")
                research_plan = await self.service.mcp_communicator.fetch_from_database(topic_id)
                if not research_plan or research_plan == {}:
                    logger.warning(f"No research plan found for topic_id {topic_id}, will delegate to planning agent")
                    research_plan = await self.service.mcp_communicator.generate_research_plan(topic_name, topic_description)
            
            logger.info(f"Final research plan for delegation: {research_plan}")
            
            # Create research context using the provided task ID
            from .models import ResearchContext
            context = ResearchContext(
                task_id=task_id,
                plan_id=plan_id,
                task_description=task_description,
                user_id=user_id,
                topic_id=topic_id,
                max_results=max_results
            )
            
            # Add additional context
            context.metadata = {
                "task_name": task_name,
                "task_type": task_type,
                "max_results": max_results,
                "topic_id": topic_id,
                "topic_name": topic_name,
                "research_plan": research_plan,
                "depth": depth
            }
            
            # Store context
            self.service.active_contexts[task_id] = context
            
            # Start research workflow which will trigger literature search
            workflow_result = await self.service.workflow_orchestrator.start_research_workflow(context)
            
            return {
                "status": "completed",
                "task_id": task_id,
                "workflow_result": workflow_result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to coordinate research: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_task_result(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task result from delegated agents and continue workflow."""
        try:
            task_id = task_data.get("task_id")
            agent_id = task_data.get("agent_id")
            result = task_data.get("result", {})
            
            logger.info(f"Received task result from {agent_id} for task {task_id}")
            logger.info(f"Result status: {result.get('status')}")
            
            # Find the context and delegation info for this task result
            found_context = None
            found_delegation_id = None
            found_agent_type = None
            
            # Search through all active contexts to find the matching delegation
            for ctx_task_id, ctx in self.service.active_contexts.items():
                for delegation_id, delegation_info in ctx.delegated_tasks.items():
                    if delegation_info["task_id"] == task_id:
                        found_context = ctx
                        found_delegation_id = delegation_id
                        found_agent_type = delegation_info["agent_type"]
                        break
                if found_context:
                    break
            
            if not found_context or not found_delegation_id:
                logger.warning(f"No active context found for task result {task_id}")
                return {
                    "status": "acknowledged",
                    "message": "Task result received but no active context found",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Update delegation status
            found_context.delegated_tasks[found_delegation_id]["status"] = "completed"
            found_context.delegated_tasks[found_delegation_id]["result"] = result
            found_context.delegated_tasks[found_delegation_id]["completed_at"] = datetime.now().isoformat()
            
            logger.info(f"Found delegation: {found_delegation_id} for agent type: {found_agent_type}")
            
            # Continue workflow based on current stage and completed delegation
            if found_agent_type == "literature_search" and found_context.stage == ResearchStage.LITERATURE_REVIEW:
                logger.info("Literature search completed, continuing to synthesis")
                await self.service.workflow_orchestrator.continue_workflow_after_literature(found_context, result)
            elif found_agent_type == "synthesis_review" and found_context.stage == ResearchStage.SYNTHESIS:
                logger.info("Synthesis completed, continuing to review")
                await self.service.workflow_orchestrator.continue_workflow_after_synthesis(found_context, result)
            elif found_agent_type == "screening_agent" and found_context.stage == ResearchStage.SYSTEMATIC_REVIEW:
                logger.info("Review completed, finalizing workflow")
                await self.service.workflow_orchestrator.complete_workflow(found_context, result)
            else:
                logger.warning(f"Unexpected task result: agent_type={found_agent_type}, stage={found_context.stage}")
            
            return {
                "status": "acknowledged",
                "message": f"Task result processed for {found_agent_type}",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error handling task result: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _get_agent_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            "agent_id": self.service.agent_id,
            "agent_type": self.service.agent_type,
            "status": "ready" if self.service.mcp_communicator.mcp_connected else "disconnected",
            "capabilities": self.service.capabilities,
            "timestamp": datetime.now().isoformat(),
            "mcp_connected": self.service.mcp_communicator.mcp_connected,
            "active_tasks": len(self.service.active_contexts),
            "max_concurrent_tasks": self.service.max_concurrent_tasks,
            "agent_availability": self.service.agent_availability,
        }
