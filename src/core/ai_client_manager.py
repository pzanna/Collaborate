"""AI Client Manager for coordinating multiple AI providers."""

import os
import sys
from typing import Dict, List, Optional, Any

# Import models and config
try:
    from ..models.data_models import Message, AIConfig
    from ..config.config_manager import ConfigManager
    from ..ai_clients.openai_client import OpenAIClient
    from ..ai_clients.xai_client import XAIClient
    from .response_coordinator import ResponseCoordinator
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models.data_models import Message, AIConfig
    from config.config_manager import ConfigManager
    from ai_clients.openai_client import OpenAIClient
    from ai_clients.xai_client import XAIClient
    from core.response_coordinator import ResponseCoordinator


class AIClientManager:
    """Manages multiple AI clients with intelligent response coordination."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.clients: Dict[str, Any] = {}
        self.response_coordinator = ResponseCoordinator(config_manager)
        self._initialize_clients()
    
    def _initialize_clients(self) -> None:
        """Initialize AI clients based on configuration."""
        # Initialize OpenAI client
        if "openai" in self.config_manager.config.ai_providers:
            try:
                api_key = self.config_manager.get_api_key("openai")
                config = self.config_manager.config.ai_providers["openai"]
                self.clients["openai"] = OpenAIClient(api_key, config)
            except Exception as e:
                print(f"Warning: Could not initialize OpenAI client: {e}")
        
        # Initialize xAI client
        if "xai" in self.config_manager.config.ai_providers:
            try:
                api_key = self.config_manager.get_api_key("xai")
                config = self.config_manager.config.ai_providers["xai"]
                self.clients["xai"] = XAIClient(api_key, config)
            except Exception as e:
                print(f"Warning: Could not initialize xAI client: {e}")
    
    def get_response(self, provider: str, messages: List[Message], system_prompt: Optional[str] = None) -> str:
        """Get response from a specific AI provider."""
        if provider not in self.clients:
            raise ValueError(f"Provider '{provider}' not available")
        
        client = self.clients[provider]
        return client.get_response(messages, system_prompt)
    
    def get_smart_responses(self, messages: List[Message], system_prompt: Optional[str] = None) -> Dict[str, str]:
        """Get responses from AI providers using smart response logic."""
        if not messages:
            return {}
        
        # Get the latest user message and context
        user_message = messages[-1]
        context = messages[:-1] if len(messages) > 1 else []
        
        # Determine which AIs should respond
        available_providers = self.get_available_providers()
        responding_providers = self.response_coordinator.coordinate_responses(
            user_message, context, available_providers
        )
        
        responses = {}
        
        for provider in responding_providers:
            try:
                # Adapt system prompt based on context
                adapted_prompt = self.adapt_system_prompt(provider, user_message.content)
                response = self.get_response(provider, messages, adapted_prompt)
                responses[provider] = response
            except Exception as e:
                print(f"Error getting response from {provider}: {e}")
                responses[provider] = f"Error: {str(e)}"
        
        return responses
    
    def get_all_responses(self, messages: List[Message], system_prompt: Optional[str] = None) -> Dict[str, str]:
        """Get responses from all available AI providers (legacy method)."""
        responses = {}
        
        for provider, client in self.clients.items():
            try:
                response = client.get_response(messages, system_prompt)
                responses[provider] = response
            except Exception as e:
                print(f"Error getting response from {provider}: {e}")
                responses[provider] = f"Error: {str(e)}"
        
        return responses
    
    def get_available_providers(self) -> List[str]:
        """Get list of available AI providers."""
        return list(self.clients.keys())
    
    def is_provider_available(self, provider: str) -> bool:
        """Check if a provider is available."""
        return provider in self.clients
    
    def update_provider_config(self, provider: str, **kwargs) -> None:
        """Update configuration for a specific provider."""
        if provider in self.clients:
            self.clients[provider].update_config(**kwargs)
        
        # Also update the config manager
        self.config_manager.update_provider_config(provider, **kwargs)
    
    def estimate_tokens(self, provider: str, messages: List[Message]) -> int:
        """Estimate token count for a provider."""
        if provider not in self.clients:
            return 0
        
        return self.clients[provider].estimate_tokens(messages)
    
    def get_provider_config(self, provider: str) -> Optional[AIConfig]:
        """Get configuration for a specific provider."""
        if provider in self.config_manager.config.ai_providers:
            return self.config_manager.config.ai_providers[provider]
        return None
    
    def adapt_system_prompt(self, provider: str, context: str) -> str:
        """Adapt system prompt based on context (for role adaptation)."""
        config = self.get_provider_config(provider)
        if not config or not config.role_adaptation:
            return config.system_prompt if config else ""
        
        # Simple context-aware adaptation
        base_prompt = config.system_prompt
        
        if "code" in context.lower() or "programming" in context.lower():
            return f"{base_prompt} Focus on technical accuracy and code quality."
        elif "research" in context.lower() or "analysis" in context.lower():
            return f"{base_prompt} Provide detailed analysis and cite relevant information."
        elif "creative" in context.lower() or "brainstorm" in context.lower():
            return f"{base_prompt} Think creatively and explore innovative solutions."
        else:
            return base_prompt
    
    def get_response_stats(self, session) -> Dict[str, Any]:
        """Get response statistics for a conversation session."""
        return self.response_coordinator.get_response_stats(session)
    
    def update_response_settings(self, **kwargs) -> None:
        """Update response coordinator settings."""
        self.response_coordinator.update_settings(**kwargs)
