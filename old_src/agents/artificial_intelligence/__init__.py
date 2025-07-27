"""
Eunice AI Agent - Centralized AI service abstraction

This package provides centralized AI model access for the Eunice Research Platform,
following the Architecture.md Phase 2 specifications. It abstracts multiple AI
providers into a unified service interface with advanced features:

Core Components:
- AIAgent: Main service class providing unified AI access
- AIClientManager: Multi-provider client coordination 
- OpenAIClient: OpenAI API integration
- XAIClient: xAI (Grok) API integration
- Cost tracking, retry logic, and fallback mechanisms

Architecture Compliance:
- Phase 2: AI Agent service abstraction
- Centralized AI model access for all agents
- Multi-provider support with failover
- Cost optimization and tracking
- Error handling and retry mechanisms
"""

from .ai_agent import AIAgent
from .ai_client_manager import AIClientManager
from .openai_client import OpenAIClient, AIProviderConfig as OpenAIConfig
from .xai_client import XAIClient, AIProviderConfig as XAIConfig

__all__ = [
    "AIAgent",
    "AIClientManager", 
    "OpenAIClient",
    "XAIClient",
    "OpenAIConfig",
    "XAIConfig",
]

__version__ = "2.0.0"
__author__ = "Eunice Research Platform"
__description__ = "Centralized AI service abstraction for multi-provider AI access"
