"""
MCP (Message Control Protocol) Package

This package implements the Message Control Protocol for coordinating
research agents in the Collaborate AI system.
"""

__version__ = "1.0.0"
__author__ = "Paul"

from .protocols import ResearchAction, AgentResponse, TaskStatus
from .client import MCPClient
from .server import MCPServer

__all__ = [
    'ResearchAction',
    'AgentResponse', 
    'TaskStatus',
    'MCPClient',
    'MCPServer'
]
