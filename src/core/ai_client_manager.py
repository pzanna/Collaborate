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
    from ..utils.error_handler import handle_errors, APIError, NetworkError, safe_execute
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models.data_models import Message, AIConfig
    from config.config_manager import ConfigManager
    from ai_clients.openai_client import OpenAIClient
    from ai_clients.xai_client import XAIClient
    from core.response_coordinator import ResponseCoordinator
    from utils.error_handler import handle_errors, APIError, NetworkError, safe_execute


class AIClientManager:
    """Manages multiple AI clients with intelligent response coordination and error handling."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.clients: Dict[str, Any] = {}
        self.response_coordinator = ResponseCoordinator(config_manager)
        self.failed_providers: Dict[str, int] = {}  # Track failed providers
        self.max_retries = 3
        self._initialize_clients()
    
    @handle_errors(context="client_initialization")
    def _initialize_clients(self) -> None:
        """Initialize AI clients based on configuration."""
        # Initialize OpenAI client
        if "openai" in self.config_manager.config.ai_providers:
            try:
                api_key = self.config_manager.get_api_key("openai")
                if not api_key:
                    raise APIError("OpenAI API key not found", "openai")
                
                config = self.config_manager.config.ai_providers["openai"]
                self.clients["openai"] = OpenAIClient(api_key, config)
                print(f"✓ OpenAI client initialized successfully")
            except Exception as e:
                print(f"⚠️ Could not initialize OpenAI client: {e}")
                self.failed_providers["openai"] = self.failed_providers.get("openai", 0) + 1
        
        # Initialize xAI client
        if "xai" in self.config_manager.config.ai_providers:
            try:
                api_key = self.config_manager.get_api_key("xai")
                if not api_key:
                    raise APIError("xAI API key not found", "xai")
                
                config = self.config_manager.config.ai_providers["xai"]
                self.clients["xai"] = XAIClient(api_key, config)
                print(f"✓ xAI client initialized successfully")
            except Exception as e:
                print(f"⚠️ Could not initialize xAI client: {e}")
                self.failed_providers["xai"] = self.failed_providers.get("xai", 0) + 1
    
    @handle_errors(context="get_response", reraise=False, fallback_return="")
    def get_response(self, provider: str, messages: List[Message], 
                    system_prompt: Optional[str] = None, retry_count: int = 0) -> str:
        """Get response from a specific AI provider with error handling and retries."""
        if provider not in self.clients:
            raise APIError(f"Provider '{provider}' not available", provider)
        
        # Check if provider has failed too many times
        if self.failed_providers.get(provider, 0) >= self.max_retries:
            raise APIError(f"Provider '{provider}' has failed too many times", provider)
        
        try:
            client = self.clients[provider]
            response = client.get_response(messages, system_prompt)
            
            # Reset failure count on success
            if provider in self.failed_providers:
                self.failed_providers[provider] = 0
            
            return response
            
        except Exception as e:
            # Track failure
            self.failed_providers[provider] = self.failed_providers.get(provider, 0) + 1
            
            # Retry logic
            if retry_count < self.max_retries:
                print(f"⚠️ Retrying {provider} request (attempt {retry_count + 1}/{self.max_retries})...")
                return self.get_response(provider, messages, system_prompt, retry_count + 1)
            
            # Convert to appropriate error type
            if "timeout" in str(e).lower() or "connection" in str(e).lower():
                raise NetworkError(f"Network error with {provider}", {"provider": provider}, e)
            else:
                raise APIError(f"API error with {provider}: {str(e)}", provider, original_error=e)
    
    @handle_errors(context="get_smart_responses", reraise=False, fallback_return={})
    def get_smart_responses(self, messages: List[Message], 
                           system_prompt: Optional[str] = None) -> Dict[str, str]:
        """Get responses from AI providers using smart response logic with error handling."""
        if not messages:
            return {}
        
        # Get the latest user message and context
        user_message = messages[-1]
        context = messages[:-1] if len(messages) > 1 else []
        
        # Determine which AIs should respond
        available_providers = self.get_available_providers()
        if not available_providers:
            print("⚠️ No AI providers available")
            return {}
        
        responding_providers = self.response_coordinator.coordinate_responses(
            user_message, context, available_providers
        )
        
        responses = {}
        successful_responses = 0
        
        for provider in responding_providers:
            try:
                # Adapt system prompt based on context
                adapted_prompt = self.adapt_system_prompt(provider, user_message.content)
                response = self.get_response(provider, messages, adapted_prompt)
                
                if response and not response.startswith("Error:"):
                    responses[provider] = response
                    successful_responses += 1
                    
            except Exception as e:
                error_msg = f"Error getting response from {provider}: {str(e)}"
                print(f"❌ {error_msg}")
                responses[provider] = f"Error: {str(e)}"
        
        # If no responses were successful, try to get at least one
        if successful_responses == 0 and available_providers:
            print("⚠️ No successful responses, trying backup provider...")
            backup_provider = available_providers[0]
            
            try:
                backup_response = self.get_response(backup_provider, messages, system_prompt)
                if backup_response:
                    responses[backup_provider] = backup_response
                    print(f"✓ Got backup response from {backup_provider}")
            except Exception as e:
                print(f"❌ Backup provider {backup_provider} also failed: {e}")
        
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
    
    def get_provider_health(self) -> Dict[str, Any]:
        """Get health status of all AI providers."""
        health_status = {}
        
        for provider in self.get_available_providers():
            failure_count = self.failed_providers.get(provider, 0)
            health_status[provider] = {
                "status": "healthy" if failure_count == 0 else "degraded" if failure_count < self.max_retries else "unhealthy",
                "failure_count": failure_count,
                "max_retries": self.max_retries
            }
        
        return health_status
    
    def reset_provider_failures(self, provider: Optional[str] = None):
        """Reset failure counts for providers."""
        if provider:
            self.failed_providers[provider] = 0
            print(f"✓ Reset failure count for {provider}")
        else:
            self.failed_providers.clear()
            print("✓ Reset failure counts for all providers")
    
    def test_provider_connection(self, provider: str) -> bool:
        """Test connection to a specific provider."""
        if provider not in self.clients:
            return False
        
        try:
            # Simple test message
            test_messages = [
                Message(
                    conversation_id="test",
                    participant="user",
                    content="Test connection - please respond with 'OK'"
                )
            ]
            
            response = self.get_response(provider, test_messages)
            return bool(response and "error" not in response.lower())
            
        except Exception:
            return False
