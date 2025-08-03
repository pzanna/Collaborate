"""
Task handlers for Research Manager Service.

This module contains handlers for different types of research coordination tasks
including cost estimation, progress tracking, delegation, workflow management,
and action approval.
"""

import logging
from datetime import datetime
from typing import Any, Dict

from .models import ResearchContext, ResearchStage

logger = logging.getLogger(__name__)


class TaskHandlers:
    """Handlers for different research management tasks."""
    
    def __init__(self, service_ref):
        """Initialize with reference to main service."""
        self.service = service_ref
    
    async def handle_estimate_costs(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle cost estimation request."""
        try:
            task_id = data.get("task_id", "")
            operations = data.get("operations", [])
            
            if not task_id:
                return {
                    "status": "failed",
                    "error": "Task ID is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Calculate estimated costs
            total_cost = await self._calculate_operation_costs(operations)
            
            return {
                "status": "completed",
                "task_id": task_id,
                "estimated_cost": total_cost,
                "operations": operations,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to estimate costs: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def handle_track_progress(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle progress tracking request."""
        try:
            task_id = data.get("task_id", "")
            
            if not task_id:
                return {
                    "status": "failed",
                    "error": "Task ID is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Get task progress
            context = self.service.active_contexts.get(task_id)
            if not context:
                return {
                    "status": "failed",
                    "error": f"Task {task_id} not found",
                    "timestamp": datetime.now().isoformat()
                }
            
            progress = await self._get_task_progress(context)
            
            return {
                "status": "completed",
                "task_id": task_id,
                "progress": progress,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to track progress: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def handle_delegate_tasks(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task delegation request."""
        try:
            task_id = data.get("task_id", "")
            agent_type = data.get("agent_type", "")
            action_data = data.get("action_data", {})
            
            if not all([task_id, agent_type]):
                return {
                    "status": "failed",
                    "error": "Task ID and agent type are required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Delegate task to agent
            result = await self.service.mcp_communicator.delegate_to_agent(
                task_id, agent_type, action_data
            )
            
            return {
                "status": "completed",
                "task_id": task_id,
                "agent_type": agent_type,
                "delegation_result": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to delegate tasks: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def handle_manage_workflows(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle workflow management request."""
        try:
            operation = data.get("operation", "")
            task_id = data.get("task_id", "")
            
            if not operation:
                return {
                    "status": "failed",
                    "error": "Operation is required",
                    "available_operations": ["start", "pause", "resume", "cancel", "status"],
                    "timestamp": datetime.now().isoformat()
                }
            
            if operation == "start":
                result = await self._start_workflow(data)
            elif operation == "pause":
                result = await self._pause_workflow(task_id)
            elif operation == "resume":
                result = await self._resume_workflow(task_id)
            elif operation == "cancel":
                result = await self._cancel_task(task_id)
            elif operation == "status":
                result = await self._get_workflow_status(task_id)
            else:
                return {
                    "status": "failed",
                    "error": f"Unknown operation: {operation}",
                    "available_operations": ["start", "pause", "resume", "cancel", "status"],
                    "timestamp": datetime.now().isoformat()
                }
            
            return {
                "status": "completed",
                "operation": operation,
                "task_id": task_id,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to manage workflows: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def handle_approve_actions(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle action approval request."""
        try:
            task_id = data.get("task_id", "")
            action_id = data.get("action_id", "")
            approved = data.get("approved", False)
            
            if not all([task_id, action_id]):
                return {
                    "status": "failed",
                    "error": "Task ID and action ID are required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Process approval
            result = await self._process_approval(task_id, action_id, approved)
            
            return {
                "status": "completed",
                "task_id": task_id,
                "action_id": action_id,
                "approved": approved,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to approve actions: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _calculate_operation_costs(self, operations: list) -> float:
        """Calculate estimated costs for operations."""
        total_cost = 0.0
        
        # Simple cost estimation based on operation types
        cost_per_operation = {
            "literature_search": 0.05,
            "reasoning": 0.10,
            "code_execution": 0.15,
            "synthesis": 0.08,
            "systematic_review": 0.20
        }
        
        for operation in operations:
            op_type = operation.get("type", "unknown")
            quantity = operation.get("quantity", 1)
            
            unit_cost = cost_per_operation.get(op_type, 0.10)
            total_cost += unit_cost * quantity
        
        return total_cost
    
    async def _get_task_progress(self, context: ResearchContext) -> Dict[str, Any]:
        """Get progress information for a task."""
        total_stages = len(ResearchStage) - 2  # Exclude COMPLETE and FAILED
        completed_stages = len(context.completed_stages)
        failed_stages = len(context.failed_stages)
        
        progress_percentage = (completed_stages / total_stages) * 100 if total_stages > 0 else 0
        
        return {
            "task_id": context.task_id,
            "current_stage": context.stage.value,
            "progress_percentage": progress_percentage,
            "completed_stages": [stage.value for stage in context.completed_stages],
            "failed_stages": [stage.value for stage in context.failed_stages],
            "retry_count": context.retry_count,
            "estimated_cost": context.estimated_cost,
            "actual_cost": context.actual_cost,
            "created_at": context.created_at.isoformat(),
            "updated_at": context.updated_at.isoformat()
        }
    
    async def _start_workflow(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Start a new workflow."""
        try:
            task_description = data.get("task_description", data.get("query", ""))
            user_id = data.get("user_id", "anonymous")
            topic_id = data.get("topic_id", "default_topic")
            max_results = data.get("max_results", 50)
            plan_id = data.get("plan_id", "")
            
            if not task_description:
                return {"error": "Task description is required"}
            
            # Create new context
            import uuid
            task_id = str(uuid.uuid4())
            context = ResearchContext(
                task_id=task_id,
                plan_id=plan_id,
                task_description=task_description,
                user_id=user_id,
                topic_id=topic_id,
                max_results=max_results
            )
            
            self.service.active_contexts[task_id] = context
            
            # Start workflow via workflow orchestrator
            workflow_result = await self.service.workflow_orchestrator.start_research_workflow(context)
            
            return {
                "started": True,
                "task_id": task_id,
                "workflow_result": workflow_result
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _pause_workflow(self, task_id: str) -> Dict[str, Any]:
        """Pause a workflow."""
        try:
            context = self.service.active_contexts.get(task_id)
            if not context:
                return {"error": f"Task {task_id} not found"}
            
            # Simple pause implementation - would need more sophisticated state management
            logger.info(f"Paused workflow for task {task_id}")
            
            return {"paused": True, "task_id": task_id}
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _resume_workflow(self, task_id: str) -> Dict[str, Any]:
        """Resume a workflow."""
        try:
            context = self.service.active_contexts.get(task_id)
            if not context:
                return {"error": f"Task {task_id} not found"}
            
            # Simple resume implementation
            logger.info(f"Resumed workflow for task {task_id}")
            
            return {"resumed": True, "task_id": task_id}
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _cancel_task(self, task_id: str) -> Dict[str, Any]:
        """Cancel a task."""
        try:
            context = self.service.active_contexts.get(task_id)
            if not context:
                return {"error": f"Task {task_id} not found"}
            
            # Update context state
            context.stage = ResearchStage.FAILED
            context.updated_at = datetime.now()
            
            # Remove from active contexts
            del self.service.active_contexts[task_id]
            
            logger.info(f"Cancelled task {task_id}")
            
            return {"cancelled": True, "task_id": task_id}
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_workflow_status(self, task_id: str) -> Dict[str, Any]:
        """Get workflow status."""
        try:
            context = self.service.active_contexts.get(task_id)
            if not context:
                return {"error": f"Task {task_id} not found"}
            
            return await self._get_task_progress(context)
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _process_approval(self, task_id: str, action_id: str, approved: bool) -> Dict[str, Any]:
        """Process an approval decision."""
        try:
            context = self.service.active_contexts.get(task_id)
            if not context:
                return {"error": f"Task {task_id} not found"}
            
            # Simple approval processing
            if approved:
                logger.info(f"Approved action {action_id} for task {task_id}")
                return {"processed": True, "approved": True}
            else:
                logger.info(f"Rejected action {action_id} for task {task_id}")
                return {"processed": True, "approved": False}
                
        except Exception as e:
            return {"error": str(e)}
