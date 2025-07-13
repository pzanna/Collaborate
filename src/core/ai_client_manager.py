# ai_client_manager.py
"""AI Client Manager for coordinating multiple AI providers."""

import os
import sys
import time
import asyncio
from typing import Dict, List, Optional, Any, AsyncGenerator, Generator

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
        if not messages:
            return {}
        
        user_message = messages[-1]
        context = messages[:-1]  # Base context
        
        available_providers = self.get_available_providers()
        if not available_providers:
            return {}
        
        # Get ordered providers
        responding_providers = self.response_coordinator.coordinate_responses(
            user_message, context, available_providers
        )
        
        responses = {}
        temp_history = context[:]  # Copy to build shared history
        temp_history.append(user_message)  # Include current user message
        
        # Sequential querying
        for provider in responding_providers:
            try:
                # Adapt prompt with FULL temp_history (now includes prior AI responses)
                adapted_prompt = self.adapt_system_prompt(provider, user_message.content, temp_history)
                response = self.get_response(provider, temp_history, adapted_prompt)  # Pass temp_history
                
                if response and not response.startswith("Error:"):
                    responses[provider] = response
                    # Append to temp_history as a Message
                    temp_history.append(Message(
                        conversation_id=user_message.conversation_id,
                        participant=provider,
                        content=response
                    ))
            except Exception as e:
                print(f"❌ Error from {provider}: {e}")
                responses[provider] = f"Error: {str(e)}"
        
        # Optional chaining: Check for cues in last response
        max_chains = 2
        chain_count = 0
        while chain_count < max_chains:
            if not responses:
                break
            last_provider = list(responses.keys())[-1]
            last_response = responses[last_provider]
            cue_target = self.response_coordinator.detect_chaining_cue(last_response, available_providers)
            if cue_target and cue_target != last_provider:
                chain_count += 1
                print(f"🔗 Detected cue to {cue_target} from {last_provider}")
                try:
                    adapted_prompt = self.adapt_system_prompt(cue_target, last_response, temp_history)
                    chain_response = self.get_response(cue_target, temp_history, adapted_prompt)
                    responses[cue_target + "_chain"] = chain_response  # Or append to existing
                    temp_history.append(Message(
                        conversation_id=user_message.conversation_id,
                        participant=cue_target,
                        content=chain_response
                    ))
                except Exception as e:
                    print(f"❌ Chain error: {e}")
            else:
                break
        
        # If no responses were successful, try to get at least one
        successful_responses = len([r for r in responses.values() if r and not r.startswith("Error:")])
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
    
    @handle_errors(context="get_collaborative_responses", reraise=False, fallback_return={})
    def get_collaborative_responses(self, messages: List[Message], 
                                   max_rounds: int = 2, 
                                   system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Get responses through multiple collaborative rounds with iteration."""
        if not messages:
            return {}

        user_message = messages[-1]
        context = messages[:-1]
        available_providers = self.get_available_providers()
        
        if not available_providers:
            return {}

        all_responses = {}
        current_context = context[:]
        current_context.append(user_message)
        
        print(f"🔄 Starting collaborative conversation with {max_rounds} rounds...")
        
        for round_num in range(max_rounds):
            print(f"📍 Round {round_num + 1}/{max_rounds}")
            
            # Get responses for this round
            round_responses = self.get_smart_responses(current_context, system_prompt)
            
            if not round_responses:
                print(f"⚠️ No responses in round {round_num + 1}, ending iteration")
                break
            
            # Store responses by round
            for provider, response in round_responses.items():
                if provider not in all_responses:
                    all_responses[provider] = []
                all_responses[provider].append({
                    'round': round_num + 1,
                    'content': response,
                    'timestamp': time.time()
                })
                
                # Add to context for next round
                current_context.append(Message(
                    conversation_id=user_message.conversation_id,
                    participant=provider,
                    content=response
                ))
            
            # Check if iteration should continue
            if not self._should_continue_iteration(round_responses, round_num, current_context):
                print(f"✓ Collaboration completed after {round_num + 1} rounds")
                break
        
        # Format final results
        final_responses = {}
        for provider, rounds in all_responses.items():
            final_responses[provider] = {
                'responses': rounds,
                'final_response': rounds[-1]['content'] if rounds else "",
                'round_count': len(rounds)
            }
        
        return final_responses
    
    def _should_continue_iteration(self, round_responses: Dict[str, str], 
                                 round_num: int, context: List[Message]) -> bool:
        """Determine if another iteration round would be valuable."""
        # Don't continue if no responses
        if not round_responses:
            return False
        
        # Check for explicit continuation cues
        for response in round_responses.values():
            if any(cue in response.lower() for cue in [
                'let me build on', 'i would add', 'alternatively', 
                'another perspective', 'to expand on', '@'
            ]):
                return True
        
        # Check for questions or incomplete thoughts
        question_indicators = ['?', 'what if', 'consider', 'thoughts on']
        for response in round_responses.values():
            if any(indicator in response.lower() for indicator in question_indicators):
                return True
        
        # Don't continue if responses are too similar (convergence)
        if len(round_responses) > 1:
            response_texts = list(round_responses.values())
            similarity = self._calculate_response_similarity(response_texts)
            if similarity > 0.8:  # High similarity suggests convergence
                return False
        
        # Continue if responses are substantial and diverse
        avg_length = sum(len(r) for r in round_responses.values()) / len(round_responses)
        return avg_length > 50  # Continue if responses are substantial
    
    def _calculate_response_similarity(self, responses: List[str]) -> float:
        """Calculate average similarity between responses."""
        if len(responses) < 2:
            return 0.0
        
        from itertools import combinations
        similarities = []
        
        for r1, r2 in combinations(responses, 2):
            words1 = set(r1.lower().split())
            words2 = set(r2.lower().split())
            
            if not words1 or not words2:
                similarity = 0.0
            else:
                intersection = words1.intersection(words2)
                union = words1.union(words2)
                similarity = len(intersection) / len(union) if union else 0.0
            
            similarities.append(similarity)
        
        return sum(similarities) / len(similarities)

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
    
    def adapt_system_prompt(self, provider: str, context: str, history: Optional[List[Message]] = None) -> str:
        config = self.get_provider_config(provider)
        if not config:
            return ""
        
        base_prompt = config.system_prompt
        
        # Add collaboration context with actual history
        collaboration_hint = self.response_coordinator._add_collaboration_context(provider, history or [])
        if collaboration_hint:
            base_prompt += f"\n\n{collaboration_hint}"
        
        # Existing role adaptation...
        if "code" in context.lower():
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
    
    async def get_streaming_responses(self, messages: List[Message], 
                                     system_prompt: Optional[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream responses as they become available with real-time updates."""
        if not messages:
            return

        user_message = messages[-1]
        context = messages[:-1]
        available_providers = self.get_available_providers()
        
        if not available_providers:
            return

        # Get ordered providers
        responding_providers = self.response_coordinator.coordinate_responses(
            user_message, context, available_providers
        )
        
        yield {
            'type': 'providers_selected',
            'providers': responding_providers,
            'timestamp': time.time()
        }

        temp_history = context[:]
        temp_history.append(user_message)
        
        # Stream responses sequentially
        for provider_idx, provider in enumerate(responding_providers):
            yield {
                'type': 'provider_started',
                'provider': provider,
                'index': provider_idx,
                'total': len(responding_providers),
                'timestamp': time.time()
            }
            
            try:
                # Adapt prompt with current context
                adapted_prompt = self.adapt_system_prompt(provider, user_message.content, temp_history)
                
                # Stream the response from this provider
                response_chunks = []
                async for chunk in self._stream_provider_response(provider, temp_history, adapted_prompt):
                    response_chunks.append(chunk)
                    yield {
                        'type': 'response_chunk',
                        'provider': provider,
                        'chunk': chunk,
                        'partial_response': ''.join(response_chunks),
                        'timestamp': time.time()
                    }
                
                # Complete response for this provider
                full_response = ''.join(response_chunks)
                if full_response and not full_response.startswith("Error:"):
                    temp_history.append(Message(
                        conversation_id=user_message.conversation_id,
                        participant=provider,
                        content=full_response
                    ))
                    
                    yield {
                        'type': 'provider_completed',
                        'provider': provider,
                        'response': full_response,
                        'timestamp': time.time()
                    }
                
            except Exception as e:
                yield {
                    'type': 'provider_error',
                    'provider': provider,
                    'error': str(e),
                    'timestamp': time.time()
                }
        
        yield {
            'type': 'conversation_completed',
            'total_providers': len(responding_providers),
            'timestamp': time.time()
        }
    
    async def _stream_provider_response(self, provider: str, messages: List[Message], 
                                       system_prompt: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Stream response from a specific provider (simulated for now)."""
        # This is a simulation of streaming - in real implementation, 
        # you would integrate with actual streaming APIs
        
        try:
            # Get the full response first (actual implementation would stream from API)
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.get_response, provider, messages, system_prompt
            )
            
            if not response or response.startswith("Error:"):
                yield response or f"Error: No response from {provider}"
                return
            
            # Simulate streaming by yielding chunks
            words = response.split()
            chunk_size = max(1, len(words) // 10)  # Stream in ~10 chunks
            
            for i in range(0, len(words), chunk_size):
                chunk = ' '.join(words[i:i + chunk_size])
                if i + chunk_size < len(words):
                    chunk += ' '
                
                yield chunk
                await asyncio.sleep(0.1)  # Simulate network delay
                
        except Exception as e:
            yield f"Error streaming from {provider}: {str(e)}"
    
    def get_streaming_responses_sync(self, messages: List[Message], 
                                   system_prompt: Optional[str] = None) -> Generator[Dict[str, Any], None, None]:
        """Synchronous version of streaming responses for non-async contexts."""
        try:
            import asyncio
            
            # Create event loop if none exists
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run the async generator
            async def run_streaming():
                results = []
                async for update in self.get_streaming_responses(messages, system_prompt):
                    results.append(update)
                return results
            
            updates = loop.run_until_complete(run_streaming())
            for update in updates:
                yield update
                
        except Exception as e:
            yield {
                'type': 'error',
                'error': f"Streaming error: {str(e)}",
                'timestamp': time.time()
            }