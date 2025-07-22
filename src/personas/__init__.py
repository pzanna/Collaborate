"""
Persona Agents Module

This module contains specialized AI agents that embody domain expertise
for expert consultation via the MCP server.
"""

from .neurobiologist_agent import NeurologistPersonaAgent
from .persona_registry import PersonaRegistry, PersonaType
from .mcp_integration import PersonaMCPIntegration

__all__ = [
    'NeurologistPersonaAgent',
    'PersonaRegistry', 
    'PersonaType',
    'PersonaMCPIntegration'
]
