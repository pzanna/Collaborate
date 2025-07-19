"""AI Client Manager for coordinating multiple AI providers."""

import os
import sys
import time
import logging
import asyncio
from typing import Dict, List, Optional, Any, AsyncGenerator, Generator
from datetime import datetime

# Import models and config
try:
    from ..models.data_models import Message, AIConfig
    from ..config.config_manager import ConfigManager
    from ..ai_clients.openai_client import OpenAIClient
    from ..ai_clients.xai_client import XAIClient
    from .simplified_coordinator import SimplifiedCoordinator
    from ..utils.error_handler import handle_errors, APIError, NetworkError, safe_execute
    from ..mcp.cost_estimator import CostEstimator
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models.data_models import Message, AIConfig
    from config.config_manager import ConfigManager
    from ai_clients.openai_client import OpenAIClient
    from ai_clients.xai_client import XAIClient
    from core.simplified_coordinator import SimplifiedCoordinator
    from utils.error_handler import handle_errors, APIError, NetworkError, safe_execute
    from mcp.cost_estimator import CostEstimator


class AIClientManager:
    """Manages multiple AI clients with simplified coordination."""
    
    def __init__(self, config_manager: ConfigManager, cost_estimator: Optional[CostEstimator] = None):
        self.config_manager = config_manager
        self.cost_estimator = cost_estimator or CostEstimator(config_manager)
        self.clients: Dict[str, Any] = {}
        self.coordinator = SimplifiedCoordinator()
        self.failed_providers: Dict[str, int] = {}  # Track failed providers
        self.max_retries = 3
        self.logger = logging.getLogger(__name__)
        
        # Apply coordination settings from config
        self._apply_coordination_config()
        
        # Initialize clients
        self._initialize_clients()
    
    def _apply_coordination_config(self):
        """Apply coordination settings from configuration"""
        coord_config = self.config_manager.config.coordination
        
        if coord_config:
            self.coordinator.base_participation_chance = coord_config.base_participation_chance
            self.coordinator.max_recent_turns = coord_config.max_consecutive_turns
            self.coordinator.mention_boost = coord_config.mention_boost
            self.coordinator.question_boost = coord_config.question_boost
            self.coordinator.engagement_boost = getattr(coord_config, 'engagement_boost', 0.2)
    
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
                print("✓ OpenAI client initialized")
            except Exception as e:
                print(f"⚠️ OpenAI client failed: {e}")
                self.failed_providers["openai"] = 1
        
        # Initialize xAI client
        if "xai" in self.config_manager.config.ai_providers:
            try:
                api_key = self.config_manager.get_api_key("xai")
                if not api_key:
                    raise APIError("xAI API key not found", "xai")
                
                config = self.config_manager.config.ai_providers["xai"]
                self.clients["xai"] = XAIClient(api_key, config)
                print("✓ xAI client initialized")
            except Exception as e:
                print(f"⚠️ xAI client failed: {e}")
                self.failed_providers["xai"] = 1
    
    @handle_errors(context="get_response", reraise=False, fallback_return="")
    def get_response(self, provider: str, messages: List[Message], 
                    system_prompt: Optional[str] = None, retry_count: int = 0,
                    task_id: Optional[str] = None, agent_type: Optional[str] = None) -> str:
        """Get response from a specific AI provider with error handling and retries."""
        if provider not in self.clients:
            error_msg = f"Provider '{provider}' not available"
            self.logger.error(f"AI Manager Error: {error_msg}")
            raise APIError(error_msg, provider)
        
        # Check if provider has failed too many times
        if self.failed_providers.get(provider, 0) >= self.max_retries:
            error_msg = f"Provider '{provider}' has failed too many times"
            self.logger.error(f"AI Manager Error: {error_msg}")
            raise APIError(error_msg, provider)
        
        # Log the request
        self.logger.info(f"AI Manager: Requesting response from {provider} "
                        f"(retry: {retry_count}, messages: {len(messages)})")
        
        try:
            client = self.clients[provider]
            
            # Estimate tokens before request (for cost tracking)
            input_tokens = 0
            if hasattr(client, 'estimate_tokens'):
                try:
                    input_tokens = client.estimate_tokens(messages, system_prompt)
                except Exception as e:
                    self.logger.warning(f"Token estimation failed for {provider}: {e}")
            
            # Get response
            response = client.get_response(messages, system_prompt)
            
            # Estimate output tokens
            output_tokens = 0
            if hasattr(client, 'estimate_tokens') and response:
                try:
                    # Create a temporary message for output token estimation
                    output_msg = Message(
                        conversation_id="temp",
                        participant="assistant", 
                        content=response
                    )
                    output_tokens = client.estimate_tokens([output_msg])
                except Exception as e:
                    self.logger.warning(f"Output token estimation failed for {provider}: {e}")
            
            # Record cost usage if tracking is active
            if task_id and self.cost_estimator:
                model = getattr(client, 'model', 'unknown')
                self.cost_estimator.record_usage(
                    task_id=task_id,
                    provider=provider,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    agent_type=agent_type
                )
            
            # Reset failure count on success
            if provider in self.failed_providers:
                self.failed_providers[provider] = 0
                self.logger.info(f"AI Manager: Reset failure count for {provider}")
            
            self.logger.info(f"AI Manager: Successfully received response from {provider}")
            return response
            
        except Exception as e:
            # Track failure
            self.failed_providers[provider] = self.failed_providers.get(provider, 0) + 1
            
            self.logger.warning(f"AI Manager: {provider} failed (count: {self.failed_providers[provider]}), "
                              f"Error: {str(e)}")
            
            # Retry logic
            if retry_count < self.max_retries:
                self.logger.info(f"AI Manager: Retrying {provider} request "
                               f"(attempt {retry_count + 1}/{self.max_retries})")
                return self.get_response(provider, messages, system_prompt, retry_count + 1, task_id, agent_type)
            
            # Convert to appropriate error type
            if "timeout" in str(e).lower() or "connection" in str(e).lower():
                raise NetworkError(f"Network error with {provider}", {"provider": provider}, e)
            else:
                raise APIError(f"API error with {provider}: {str(e)}", provider, original_error=e)
    
    @handle_errors(context="get_smart_responses", reraise=False, fallback_return={})
    def get_smart_responses(self, messages: List[Message], 
                            system_prompt: Optional[str] = None,
                            task_id: Optional[str] = None) -> Dict[str, str]:
        """Get responses from participating AIs using simplified coordination"""
        
        if not messages:
            self.logger.info("AI Manager: No messages provided for smart responses")
            return {}
            
        user_message = messages[-1]
        conversation_history = messages[:-1]
        available_providers = self.get_available_providers()
        
        if not available_providers:
            self.logger.warning("AI Manager: No available providers for smart responses")
            return {}
        
        # Determine participants using simple rules
        participants = self.coordinator.get_participating_providers(
            user_message.content, available_providers, conversation_history
        )
        
        self.logger.info(f"AI Manager: Coordination decision - Participants: {', '.join(participants)} "
                        f"(from available: {', '.join(available_providers)})")
        
        responses = {}
        shared_context = messages  # All AIs see the same context
        
        for provider in participants:
            try:
                # Simple system prompt for group participation
                group_prompt = self._create_group_prompt(provider, system_prompt)
                
                response = self.get_response(provider, shared_context, group_prompt, 
                                           task_id=task_id, agent_type="coordinator")
                
                if response and not response.startswith("Error:"):
                    responses[provider] = response
                    
                    # Add this response to shared context for next provider
                    ai_message = Message(
                        conversation_id=user_message.conversation_id,
                        participant=provider,
                        content=response,
                        timestamp=datetime.now()
                    )
                    shared_context.append(ai_message)
                        
            except Exception as e:
                print(f"❌ Error from {provider}: {e}")
                responses[provider] = f"Error: {str(e)}"
        
        return responses
    
    def _create_group_prompt(self, provider: str, base_prompt: Optional[str] = None) -> str:
        """Create group conversation prompt using config"""
        provider_config = self.config_manager.config.ai_providers.get(provider, {})
        
        # Use configured system prompt as base
        configured_prompt = getattr(provider_config, 'system_prompt', '')
        
        # Add any additional context
        if base_prompt:
            return f"{configured_prompt}\n\n{base_prompt}"
        
        return configured_prompt
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        return [p for p in self.clients.keys() 
                if self.failed_providers.get(p, 0) < self.max_retries]
    
    def get_provider_count(self) -> int:
        """Get total number of initialized providers."""
        return len(self.clients)
    
    def get_failed_providers(self) -> Dict[str, int]:
        """Get dictionary of failed providers and their failure counts."""
        return self.failed_providers.copy()
    
    def reset_provider_failures(self, provider: Optional[str] = None) -> None:
        """Reset failure count for a specific provider or all providers."""
        if provider:
            self.failed_providers[provider] = 0
        else:
            self.failed_providers.clear()
    
    def adapt_system_prompt(self, provider: str, user_message: str, 
                           conversation_history: List[Message]) -> str:
        """Adapt system prompt for provider (simplified version)"""
        return self._create_group_prompt(provider)
    
    # Compatibility methods for existing code
    def get_response_stats(self, session) -> Dict[str, Any]:
        """Get simple response statistics (for compatibility)"""
        return {
            "total_providers": len(self.clients),
            "available_providers": len(self.get_available_providers()),
            "failed_providers": len(self.failed_providers)
        }
    
    def update_settings(self, **kwargs):
        """Update coordination settings (for compatibility)"""
        for key, value in kwargs.items():
            if hasattr(self.coordinator, key):
                setattr(self.coordinator, key, value)
    
    # Streaming methods for compatibility
    async def stream_responses(self, messages: List[Message], 
                              system_prompt: Optional[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream responses from participating AIs"""
        
        if not messages:
            return
            
        user_message = messages[-1]
        conversation_history = messages[:-1]
        available_providers = self.get_available_providers()
        
        if not available_providers:
            yield {'type': 'error', 'message': 'No providers available'}
            return
        
        # Get participants
        participants = self.coordinator.get_participating_providers(
            user_message.content, available_providers, conversation_history
        )
        
        yield {
            'type': 'participants_selected',
            'participants': participants,
            'message': f"🎯 {', '.join(participants)} will respond"
        }
        
        # Stream responses from each participant
        shared_context = messages
        
        for i, provider in enumerate(participants):
            yield {
                'type': 'provider_starting',
                'provider': provider,
                'position': i + 1,
                'total': len(participants)
            }
            
            try:
                # Get response (in real implementation, this would stream)
                group_prompt = self._create_group_prompt(provider, system_prompt)
                
                # Get response
                response = await asyncio.get_event_loop().run_in_executor(
                    None, self.get_response, provider, shared_context, group_prompt
                )
                
                if response and not response.startswith("Error:"):
                    yield {
                        'type': 'response_chunk',
                        'provider': provider,
                        'chunk': response,
                        'partial_response': response
                    }
                    
                    # Add to shared context for next provider
                    ai_message = Message(
                        conversation_id=user_message.conversation_id,
                        participant=provider,
                        content=response,
                        timestamp=datetime.now()
                    )
                    shared_context.append(ai_message)
                    
                    yield {
                        'type': 'provider_completed',
                        'provider': provider,
                        'response': response
                    }
                    
            except Exception as e:
                yield {
                    'type': 'provider_error',
                    'provider': provider,
                    'error': str(e)
                }
        
        yield {
            'type': 'conversation_completed',
            'total_responses': len(participants)
        }
    
    def get_provider_health(self) -> Dict[str, Any]:
        """Get health status of all providers (for web server compatibility)"""
        health_status = {}
        
        for provider in self.clients.keys():
            failure_count = self.failed_providers.get(provider, 0)
            health_status[provider] = {
                "status": "healthy" if failure_count < self.max_retries else "failed",
                "failure_count": failure_count,
                "max_retries": self.max_retries,
                "available": provider in self.get_available_providers()
            }
        
        return health_status
