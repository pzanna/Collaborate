"""
Agent framework for the Collaborate research system.

This module provides specialized agents for different research tasks:
- BaseAgent: Abstract base class for all agents
- RetrieverAgent: Web search and information retrieval
- ReasonerAgent: Analysis and synthesis tasks
- ExecutorAgent: Task execution and automation
- MemoryAgent: Context and memory management
"""

from .base_agent import BaseAgent
from .retriever_agent import RetrieverAgent
from .reasoner_agent import ReasonerAgent
from .executor_agent import ExecutorAgent
from .memory_agent import MemoryAgent

__all__ = [
    'BaseAgent',
    'RetrieverAgent', 
    'ReasonerAgent',
    'ExecutorAgent',
    'MemoryAgent'
]
