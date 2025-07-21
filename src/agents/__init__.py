"""
Agent framework for the Eunice research system.

This module provides specialized agents for different research tasks:
- BaseAgent: Abstract base class for all agents
- RetrieverAgent: Web search and information retrieval
- PlanningAgent: Planning, analysis and synthesis tasks
- ExecutorAgent: Task execution and automation
- MemoryAgent: Context and memory management
"""

from .base_agent import BaseAgent
from .retriever_agent import RetrieverAgent
from .planning_agent import PlanningAgent
from .executor_agent import ExecutorAgent
from .memory_agent import MemoryAgent

__all__ = [
    'BaseAgent',
    'RetrieverAgent', 
    'PlanningAgent',
    'ExecutorAgent',
    'MemoryAgent'
]
