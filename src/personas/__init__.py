"""
Persona Agents Module

This module contains specialized AI agents that embody domain expertise
for expert consultation via the MCP server.
"""

from .mcp_integration import PersonaMCPIntegration
from .neurobiologist_agent import NeurologistPersonaAgent
from .persona_registry import PersonaRegistry, PersonaType

__all__ = ["NeurologistPersonaAgent", "PersonaRegistry", "PersonaType", "PersonaMCPIntegration"]
