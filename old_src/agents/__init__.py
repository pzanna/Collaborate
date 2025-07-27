"""
Eunice AI Agents Package

This package contains AI agents for different specialized tasks:
- AIAgent: Centralized AI service abstraction for multi-provider AI access
- DatabaseAgent: Centralized data access and persistence service
- LiteratureAgent: Multi - engine web search, academic paper retrieval, research workflows, and information analysis
- PlanningAgent: Task planning and coordination
- ExecutorAgent: Task execution and automation
- MemoryAgent: Data storage and retrieval
- SystematicReviewAgent: PRISMA-compliant systematic literature reviews
"""

from .artificial_intelligence.ai_agent import AIAgent
from .base_agent import BaseAgent
from .database import DatabaseAgent
from .executor.executor_agent import ExecutorAgent
from .literature.literature_agent import LiteratureAgent
from .literature.systematic_review_agent import SystematicReviewAgent
from .memory.memory_agent import MemoryAgent
from .planning.planning_agent import PlanningAgent

__all__ = [
    "AIAgent",
    "BaseAgent",
    "DatabaseAgent",
    "LiteratureAgent",
    "PlanningAgent",
    "ExecutorAgent",
    "MemoryAgent",
    "SystematicReviewAgent",
]
