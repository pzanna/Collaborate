"""
Eunice AI Agents Package

This package contains AI agents for different specialized tasks:
- LiteratureAgent: Multi - engine web search, academic paper retrieval, research workflows, and information analysis
- PlanningAgent: Task planning and coordination
- ExecutorAgent: Task execution and automation
- MemoryAgent: Data storage and retrieval
- SystematicReviewAgent: PRISMA - compliant systematic literature reviews
"""

from .base_agent import BaseAgent
from .executor_agent import ExecutorAgent
from .literature_agent import LiteratureAgent
from .memory_agent import MemoryAgent
from .planning_agent import PlanningAgent
from .systematic_review_agent import SystematicReviewAgent

__all__ = [
    "BaseAgent",
    "LiteratureAgent",
    "PlanningAgent",
    "ExecutorAgent",
    "MemoryAgent",
    "SystematicReviewAgent",
]
