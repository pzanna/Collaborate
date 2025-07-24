"""
MCP (Message Control Protocol) Package

This package implements the Message Control Protocol for coordinating
research agents in the Eunice AI system.
"""

__version__ = "1.0.0"
__author__ = "Paul"

from .client import MCPClient
from .protocols import AgentResponse, ResearchAction, TaskStatus
from .server import MCPServer

__all__ = ["ResearchAction", "AgentResponse", "TaskStatus", "MCPClient", "MCPServer"]
