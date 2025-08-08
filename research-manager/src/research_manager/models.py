"""
Data models and classes for Research Manager Service.

This module contains all the data structures used for research workflow
management, task tracking, and agent coordination.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ResearchStage(Enum):
    """Research task stages."""
    PLANNING = "planning"
    LITERATURE_REVIEW = "literature_review"
    SYSTEMATIC_REVIEW = "systematic_review"
    REASONING = "reasoning"
    EXECUTION = "execution"
    SYNTHESIS = "synthesis"
    COMPLETE = "complete"
    FAILED = "failed"

    
@dataclass
class ResearchContext:
    """Research context for tracking task state."""
    task_id: str
    plan_id: str
    task_description: str
    user_id: str
    topic_id: str
    max_results: int = 25
    project_id: Optional[str] = None
    stage: ResearchStage = ResearchStage.PLANNING
    estimated_cost: float = 0.0
    actual_cost: float = 0.0
    cost_approved: bool = False
    single_agent_mode: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_stages: List[ResearchStage] = field(default_factory=list)
    failed_stages: List[ResearchStage] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 2
    context_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Delegation tracking
    delegated_tasks: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Results storage
    search_results: List[Dict[str, Any]] = field(default_factory=list)
    reasoning_output: str = ""
    execution_results: List[Dict[str, Any]] = field(default_factory=list)
    synthesis: str = ""


@dataclass
class ResearchAction:
    """Research action for agent communication."""
    task_id: str
    context_id: str
    agent_type: str
    action: str
    payload: Dict[str, Any]
    priority: str = "normal"
    parallelism: int = 1
    timeout: int = 300
    retry_count: int = 0
    dependencies: List[str] = field(default_factory=list)


@dataclass
class AgentResponse:
    """Response from an agent."""
    task_id: str
    context_id: str
    agent_type: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
