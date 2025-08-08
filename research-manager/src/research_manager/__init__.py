"""
Research Manager Package for Eunice Research Platform.

This package provides modular components for research workflow orchestration,
task delegation, and multi-agent coordination via MCP protocol.
"""

from .models import ResearchStage, ResearchContext, ResearchAction, AgentResponse
from .service import ResearchManagerService

__all__ = [
    "ResearchStage",
    "ResearchContext", 
    "ResearchAction",
    "AgentResponse",
    "ResearchManagerService"
]
