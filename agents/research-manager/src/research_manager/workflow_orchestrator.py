"""
Workflow orchestration module for Research Manager.

This module handles the coordination of multi-stage research workflows including:
- Literature search initiation and management
- Synthesis coordination
- Review process orchestration
- Workflow state transitions and completion
"""

import logging
from datetime import datetime
from typing import Any, Dict

from .models import ResearchContext, ResearchStage

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """Orchestrates research workflows across multiple agents."""
    
    def __init__(self, service_ref):
        """Initialize with reference to main service."""
        self.service = service_ref
    
    async def start_research_workflow(self, context: ResearchContext) -> Dict[str, Any]:
        """Start the research workflow for a task."""
        try:
            # Initialize workflow state
            context.stage = ResearchStage.LITERATURE_REVIEW
            context.updated_at = datetime.now()
            
            # Estimate initial costs
            estimated_cost = await self._estimate_research_costs(context)
            context.estimated_cost = estimated_cost
            
            logger.info(f"Started research workflow for task {context.task_id}")
            
            # Start the complete workflow - literature search first
            literature_result = await self._start_literature_search(context)
            
            # Store literature search results and continue workflow
            if literature_result.get("delegated"):
                # Mark literature stage as initiated
                context.metadata["literature_delegated"] = True
                context.metadata["literature_delegation_id"] = literature_result.get("delegation_id")
                
                logger.info(f"Literature search delegated for task {context.task_id}, workflow will continue upon completion")
                
                return {
                    "workflow_started": True,
                    "initial_stage": context.stage.value,
                    "estimated_cost": estimated_cost,
                    "task_id": context.task_id,
                    "literature_search_status": "delegated",
                    "workflow_status": "literature_search_initiated"
                }
            else:
                logger.error(f"Failed to delegate literature search for task {context.task_id}")
                context.stage = ResearchStage.FAILED
                return {
                    "workflow_started": False,
                    "error": "Failed to delegate literature search"
                }
            
        except Exception as e:
            logger.error(f"Failed to start research workflow: {e}")
            context.stage = ResearchStage.FAILED
            return {
                "workflow_started": False,
                "error": str(e)
            }
    
    async def _start_literature_search(self, context: ResearchContext) -> Dict[str, Any]:
        """Start literature search for the research task."""
        try:
            if not self.service.mcp_communicator.mcp_connected:
                logger.error("Cannot start literature search: MCP connection not available")
                return {"status": "failed", "error": "MCP connection not available"}
            
            # Get the actual research plan from context metadata
            research_plan = context.metadata.get("research_plan", {})
            
            logger.info(f"Starting literature search with research plan: {research_plan}")
            
            # Use the delegation method to properly route through MCP server
            delegation_result = await self.service.mcp_communicator.delegate_to_agent(
                task_id=context.task_id,
                agent_type="literature",
                action_data={
                    "action": "search_literature",
                    "lit_review_id": context.task_id,
                    "plan_id": context.plan_id,
                    "research_plan": research_plan,  # Use the actual research plan
                    "max_results": context.metadata.get("max_results", 50)
                }
            )
            
            # Track delegation if successful
            if delegation_result.get("delegated"):
                delegation_id = f"literature_search_{delegation_result.get('delegation_id')}"
                context.delegated_tasks[delegation_id] = {
                    "agent_type": "literature_search",
                    "task_id": delegation_result.get("delegation_id"),
                    "action": "search_literature",
                    "status": "in_progress",
                    "started_at": datetime.now().isoformat()
                }
                context.metadata["literature_delegation_id"] = delegation_id
            
            logger.info(f"Literature search delegation result: {delegation_result}")
            
            return delegation_result
            
        except Exception as e:
            logger.error(f"Failed to start literature search: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }

    async def continue_workflow_after_literature(self, context: ResearchContext, literature_results: Dict[str, Any]) -> Dict[str, Any]:
        """Continue the research workflow after literature search completion."""
        try:
            logger.info(f"Continuing workflow for task {context.task_id} after literature search")
            
            # Store literature search results
            context.search_results = literature_results.get("records", [])
            context.metadata["literature_search_completed"] = True
            context.metadata["literature_results"] = literature_results
            
            # Move to synthesis stage
            context.stage = ResearchStage.SYNTHESIS
            
            # Start synthesis process
            synthesis_result = await self._start_synthesis(context)
            
            if synthesis_result.get("delegated"):
                context.metadata["synthesis_delegated"] = True
                context.metadata["synthesis_delegation_id"] = synthesis_result.get("delegation_id")
                logger.info(f"Synthesis delegated for task {context.task_id}")
                
                return {
                    "workflow_continued": True,
                    "current_stage": context.stage.value,
                    "synthesis_status": "delegated"
                }
            else:
                logger.error(f"Failed to delegate synthesis for task {context.task_id}")
                return {
                    "workflow_continued": False,
                    "error": "Failed to delegate synthesis"
                }
                
        except Exception as e:
            logger.error(f"Failed to continue workflow after literature search: {e}")
            return {
                "workflow_continued": False,
                "error": str(e)
            }

    async def _start_synthesis(self, context: ResearchContext) -> Dict[str, Any]:
        """Start synthesis of literature search results."""
        try:
            if not self.service.mcp_communicator.mcp_connected:
                logger.error("Cannot start synthesis: MCP connection not available")
                return {"status": "failed", "error": "MCP connection not available"}
            
            # Get the actual research plan from context metadata
            research_plan = context.metadata.get("research_plan", {})
            
            # Prepare synthesis payload
            synthesis_payload = {
                "action": "synthesize_evidence",
                "task_id": context.task_id,
                "literature_results": context.search_results,
                "research_plan": research_plan,  # Use the actual research plan
                "synthesis_type": "comprehensive",
                "include_citations": True
            }
            
            # Delegate to synthesis agent
            delegation_result = await self.service.mcp_communicator.delegate_to_agent(
                task_id=context.task_id,
                agent_type="synthesis_review",
                action_data=synthesis_payload
            )
            
            # Track delegation if successful
            if delegation_result.get("delegated"):
                delegation_id = f"synthesis_review_{delegation_result.get('delegation_id')}"
                context.delegated_tasks[delegation_id] = {
                    "agent_type": "synthesis_review",
                    "task_id": delegation_result.get("delegation_id"),
                    "action": "synthesize_evidence",
                    "status": "in_progress",
                    "started_at": datetime.now().isoformat()
                }
                context.metadata["synthesis_delegation_id"] = delegation_id
            
            logger.info(f"Synthesis delegation result: {delegation_result}")
            
            return delegation_result
            
        except Exception as e:
            logger.error(f"Failed to start synthesis: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }

    async def continue_workflow_after_synthesis(self, context: ResearchContext, synthesis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Continue the research workflow after synthesis completion."""
        try:
            logger.info(f"Continuing workflow for task {context.task_id} after synthesis")
            
            # Store synthesis results
            context.synthesis = synthesis_results.get("synthesis", "")
            context.metadata["synthesis_completed"] = True
            context.metadata["synthesis_results"] = synthesis_results
            
            # Move to systematic review stage
            context.stage = ResearchStage.SYSTEMATIC_REVIEW
            
            # Start review process
            review_result = await self._start_review(context)
            
            if review_result.get("delegated"):
                context.metadata["review_delegated"] = True
                context.metadata["review_delegation_id"] = review_result.get("delegation_id")
                logger.info(f"Review delegated for task {context.task_id}")
                
                return {
                    "workflow_continued": True,
                    "current_stage": context.stage.value,
                    "review_status": "delegated"
                }
            else:
                logger.error(f"Failed to delegate review for task {context.task_id}")
                return {
                    "workflow_continued": False,
                    "error": "Failed to delegate review"
                }
                
        except Exception as e:
            logger.error(f"Failed to continue workflow after synthesis: {e}")
            return {
                "workflow_continued": False,
                "error": str(e)
            }

    async def _start_review(self, context: ResearchContext) -> Dict[str, Any]:
        """Start review of synthesized results."""
        try:
            if not self.service.mcp_communicator.mcp_connected:
                logger.error("Cannot start review: MCP connection not available")
                return {"status": "failed", "error": "MCP connection not available"}
            
            # Get the actual research plan from context metadata
            research_plan = context.metadata.get("research_plan", {})
            
            # Prepare review payload
            review_payload = {
                "action": "screen_literature",
                "task_id": context.task_id,
                "literature_results": context.search_results,
                "synthesis_results": context.synthesis,
                "research_plan": research_plan,  # Use the actual research plan
                "review_criteria": {
                    "quality_assessment": True,
                    "relevance_scoring": True,
                    "bias_detection": True
                }
            }
            
            # Delegate to screening agent for review
            delegation_result = await self.service.mcp_communicator.delegate_to_agent(
                task_id=context.task_id,
                agent_type="screening",
                action_data=review_payload
            )
            
            # Track delegation if successful
            if delegation_result.get("delegated"):
                delegation_id = f"screening_agent_{delegation_result.get('delegation_id')}"
                context.delegated_tasks[delegation_id] = {
                    "agent_type": "screening_agent",
                    "task_id": delegation_result.get("delegation_id"),
                    "action": "screen_literature",
                    "status": "in_progress",
                    "started_at": datetime.now().isoformat()
                }
                context.metadata["review_delegation_id"] = delegation_id
            
            logger.info(f"Review delegation result: {delegation_result}")
            
            return delegation_result
            
        except Exception as e:
            logger.error(f"Failed to start review: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }

    async def complete_workflow(self, context: ResearchContext, review_results: Dict[str, Any]) -> Dict[str, Any]:
        """Complete the research workflow."""
        try:
            logger.info(f"Completing workflow for task {context.task_id}")
            
            # Store review results
            context.metadata["review_completed"] = True
            context.metadata["review_results"] = review_results
            context.stage = ResearchStage.COMPLETE
            
            # Compile final results
            final_results = {
                "task_id": context.task_id,
                "workflow_status": "completed",
                "stages_completed": ["literature_search", "synthesis", "review"],
                "literature_results": context.metadata.get("literature_results", {}),
                "synthesis_results": context.metadata.get("synthesis_results", {}),
                "review_results": review_results,
                "total_duration": (datetime.now() - context.created_at).total_seconds(),
                "estimated_cost": context.estimated_cost
            }
            
            logger.info(f"Research workflow completed for task {context.task_id}")
            
            return {
                "workflow_completed": True,
                "final_stage": context.stage.value,
                "results": final_results
            }
            
        except Exception as e:
            logger.error(f"Failed to complete workflow: {e}")
            return {
                "workflow_completed": False,
                "error": str(e)
            }
    
    async def _estimate_research_costs(self, context: ResearchContext) -> float:
        """Estimate costs for a research task."""
        base_cost = 0.50
        
        # Adjust based on task description complexity
        description_length = len(context.task_description.split())
        complexity_multiplier = min(description_length / 10, 3.0)
        
        # Adjust based on single agent mode
        mode_multiplier = 0.7 if context.single_agent_mode else 1.0
        
        estimated_cost = base_cost * complexity_multiplier * mode_multiplier
        
        return round(estimated_cost, 2)
