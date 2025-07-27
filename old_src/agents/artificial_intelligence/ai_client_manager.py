"""AI Client Manager for coordinating multiple AI providers."""

import asyncio
import logging
import os
import sys
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def generate_uuid() -> str:
    """Generate a unique ID."""
    return str(uuid4())


# Import models and config
try:
    from .openai_client import AIProviderConfig as OpenAIAIProviderConfig
    from .openai_client import OpenAIClient
    from .xai_client import AIProviderConfig as XAIAIProviderConfig  
    from .xai_client import XAIClient
    from ...config.config_manager import ConfigManager
    from ..planning.cost_estimator import CostEstimator
    from ...utils.error_handler import APIError, NetworkError, handle_errors
    from ...core.simplified_coordinator import SimplifiedCoordinator
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from openai_client import AIProviderConfig as OpenAIAIProviderConfig
    from openai_client import OpenAIClient
    from xai_client import AIProviderConfig as XAIAIProviderConfig
    from xai_client import XAIClient
    from config.config_manager import ConfigManager
    from core.simplified_coordinator import SimplifiedCoordinator
    from agents.planning.cost_estimator import CostEstimator
    from utils.error_handler import APIError, NetworkError, handle_errors


class AIProviderConfig(BaseModel):
    """AI configuration model."""

    provider: str  # openai, xai
    model: str
    temperature: float = 0.7
    max_tokens: int = 2000
    system_prompt: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AIClientManager:
    """Manages multiple AI clients with simplified coordination."""

    def __init__(
        self,
        config_manager: ConfigManager,
        cost_estimator: Optional[CostEstimator] = None,
    ):
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
            self.coordinator.base_participation_chance = (
                coord_config.base_participation_chance
            )
            self.coordinator.max_recent_turns = coord_config.max_consecutive_turns
            self.coordinator.mention_boost = coord_config.mention_boost
            self.coordinator.question_boost = coord_config.question_boost
            self.coordinator.engagement_boost = getattr(
                coord_config, "engagement_boost", 0.2
            )

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
                # Convert config to OpenAIAIProviderConfig if necessary
                if not isinstance(config, OpenAIAIProviderConfig):
                    config = OpenAIAIProviderConfig(**config.dict())
                self.clients["openai"] = OpenAIClient(api_key, config)
                self.coordinator.register_participant("openai")
                self.logger.info("OpenAI client initialized.")
            except Exception as e:
                print(f"⚠️ OpenAI client failed: {e}")
                self.failed_providers["openai"] = 1

        # Initialize xAI client
        if "xai" in self.config_manager.config.ai_providers:
            try:
                api_key = self.config_manager.get_api_key("xai")
                if not api_key:
                    raise APIError("XAI API key not found", "xai")

                config = self.config_manager.config.ai_providers["xai"]
                # Convert config to XAIAIProviderConfig if necessary
                if not isinstance(config, XAIAIProviderConfig):
                    config = XAIAIProviderConfig(**config.dict())
                self.clients["xai"] = XAIClient(api_key, config)
                self.coordinator.register_participant("xai")
                self.logger.info("XAI client initialized.")
            except Exception as e:
                print(f"⚠️ xAI client failed: {e}")
                self.failed_providers["xai"] = 1

    @handle_errors(context="get_response", reraise=False, fallback_return="")
    def get_response(
        self,
        provider: str,
        user_message: str,
        system_prompt: Optional[str] = None,
        retry_count: int = 0,
        task_id: Optional[str] = None,
        agent_type: Optional[str] = None,
    ) -> str:
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
        self.logger.info(
            f"AI Manager: Requesting response from {provider} "
            f"(retry: {retry_count}, message length: {len(user_message)})"
        )

        try:
            client = self.clients[provider]

            # Estimate tokens before request (for cost tracking)
            input_tokens = 0
            if hasattr(client, "estimate_tokens"):
                try:
                    input_tokens = client.estimate_tokens(user_message)
                except Exception as e:
                    self.logger.warning(f"Token estimation failed for {provider}: {e}")

            # Get response
            response = client.get_response(user_message, system_prompt)

            # Estimate output tokens
            output_tokens = 0
            if hasattr(client, "estimate_tokens") and response:
                try:
                    output_tokens = client.estimate_tokens(response)
                except Exception as e:
                    self.logger.warning(
                        f"Output token estimation failed for {provider}: {e}"
                    )

            # Record cost usage if tracking is active
            if task_id and self.cost_estimator:
                model = getattr(client, "model", "unknown")
                self.cost_estimator.record_usage(
                    task_id=task_id,
                    provider=provider,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    agent_type=agent_type,
                )

            # Reset failure count on success
            if provider in self.failed_providers:
                self.failed_providers[provider] = 0
                self.logger.info(f"AI Manager: Reset failure count for {provider}")

            self.logger.info(
                f"AI Manager: Successfully received response from {provider}"
            )
            return response

        except Exception as e:
            # Track failure
            self.failed_providers[provider] = self.failed_providers.get(provider, 0) + 1

            self.logger.warning(
                f"AI Manager: {provider} failed (count: {self.failed_providers[provider]}), "
                f"Error: {str(e)}"
            )

            # Retry logic
            if retry_count < self.max_retries:
                self.logger.info(
                    f"AI Manager: Retrying {provider} request "
                    f"(attempt {retry_count + 1}/{self.max_retries})"
                )
                return self.get_response(
                    provider,
                    user_message,
                    system_prompt,
                    retry_count + 1,
                    task_id,
                    agent_type,
                )

            # Convert to appropriate error type
            if "timeout" in str(e).lower() or "connection" in str(e).lower():
                raise NetworkError(
                    f"Network error with {provider}", {"provider": provider}, e
                )
            else:
                raise APIError(
                    f"API error with {provider}: {str(e)}", provider, original_error=e
                )

    @handle_errors(context="get_smart_responses", reraise=False, fallback_return={})
    def get_smart_responses(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, str]:
        """Get responses from participating AIs using simplified coordination"""

        if not user_message:
            self.logger.info("AI Manager: No message provided for smart responses")
            return {}

        available_providers = self.get_available_providers()

        if not available_providers:
            self.logger.warning(
                "AI Manager: No available providers for smart responses"
            )
            return {}

        # Determine participants using simple rules
        participants = self.coordinator.get_participating_providers(
            user_message, available_providers, []
        )

        self.logger.info(
            f"AI Manager: Coordination decision-Participants: {', '.join(participants)} "
            f"(from available: {', '.join(available_providers)})"
        )

        responses = {}

        for provider in participants:
            try:
                # Simple system prompt for group participation
                group_prompt = self._create_group_prompt(provider, system_prompt)

                response = self.get_response(
                    provider,
                    user_message,
                    group_prompt,
                    task_id=task_id,
                    agent_type="coordinator",
                )

                if response and not response.startswith("Error:"):
                    responses[provider] = response

            except Exception as e:
                print(f"❌ Error from {provider}: {e}")
                responses[provider] = f"Error: {str(e)}"

        return responses

    def _create_group_prompt(
        self, provider: str, base_prompt: Optional[str] = None
    ) -> str:
        """Create group conversation prompt using config"""
        provider_config = self.config_manager.config.ai_providers.get(provider, {})

        # Use configured system prompt as base
        configured_prompt = getattr(provider_config, "system_prompt", "")

        # Add any additional context
        if base_prompt:
            return f"{configured_prompt}\n\n{base_prompt}"

        return configured_prompt

    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        return [
            p
            for p in self.clients.keys()
            if self.failed_providers.get(p, 0) < self.max_retries
        ]

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

    def adapt_system_prompt(self, provider: str, user_message: str) -> str:
        """Adapt system prompt for provider (simplified version)"""
        return self._create_group_prompt(provider)

    # Compatibility methods for existing code
    def get_response_stats(self, session) -> Dict[str, Any]:
        """Get simple response statistics (for compatibility)"""
        return {
            "total_providers": len(self.clients),
            "available_providers": len(self.get_available_providers()),
            "failed_providers": len(self.failed_providers),
        }

    def update_settings(self, **kwargs):
        """Update coordination settings (for compatibility)"""
        for key, value in kwargs.items():
            if hasattr(self.coordinator, key):
                setattr(self.coordinator, key, value)

    # Streaming methods for compatibility
    async def stream_responses(
        self, user_message: str, system_prompt: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream responses from participating AIs"""

        if not user_message:
            return

        available_providers = self.get_available_providers()

        if not available_providers:
            yield {"type": "error", "message": "No providers available"}
            return

        # Get participants
        participants = self.coordinator.get_participating_providers(
            user_message, available_providers, []
        )

        yield {
            "type": "participants_selected",
            "participants": participants,
            "message": f"🎯 {', '.join(participants)} will respond",
        }

        # Stream responses from each participant
        for i, provider in enumerate(participants):
            yield {
                "type": "provider_starting",
                "provider": provider,
                "position": i + 1,
                "total": len(participants),
            }

            try:
                # Get response (in real implementation, this would stream)
                group_prompt = self._create_group_prompt(provider, system_prompt)

                # Get response
                response = await asyncio.get_event_loop().run_in_executor(
                    None, self.get_response, provider, user_message, group_prompt
                )

                if response and not response.startswith("Error:"):
                    yield {
                        "type": "response_chunk",
                        "provider": provider,
                        "chunk": response,
                        "partial_response": response,
                    }

                    yield {
                        "type": "provider_completed",
                        "provider": provider,
                        "response": response,
                    }

            except Exception as e:
                yield {"type": "provider_error", "provider": provider, "error": str(e)}

        yield {"type": "conversation_completed", "total_responses": len(participants)}

    def get_provider_health(self) -> Dict[str, Any]:
        """Get health status of all providers (for web server compatibility)"""
        health_status = {}

        for provider in self.clients.keys():
            failure_count = self.failed_providers.get(provider, 0)
            health_status[provider] = {
                "status": "healthy" if failure_count < self.max_retries else "failed",
                "failure_count": failure_count,
                "max_retries": self.max_retries,
                "available": provider in self.get_available_providers(),
            }

        return health_status

    async def generate_text(
        self,
        prompt: str,
        provider: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate text using the best available provider or a specified one.

        Args:
            prompt: The input prompt.
            provider: Optional specific provider to use.
            temperature: Optional temperature override.
            max_tokens: Optional max_tokens override.
            system_prompt: Optional system prompt override.
            metadata: Optional metadata for cost estimation.

        Yields:
            A dictionary containing the generated text chunk and provider info.
        """
        selected_provider = provider or self._select_provider(prompt)

        if not selected_provider:
            yield {"error": "No available providers.", "provider": "none"}
            return

        try:
            client = self.clients[selected_provider]
            config = client.config

            # Override config if parameters are provided
            temp = temperature if temperature is not None else config.temperature
            tokens = max_tokens if max_tokens is not None else config.max_tokens
            sys_prompt = (
                system_prompt if system_prompt is not None else config.system_prompt
            )

            # Estimate cost before generation
            if self.cost_estimator:
                estimated_cost = self.cost_estimator.estimate_cost(
                    prompt,
                    provider=selected_provider,
                    model=config.model,
                    max_tokens=tokens,
                    metadata=metadata,
                )
                yield {
                    "status": "info",
                    "message": f"Estimated cost: ${estimated_cost:.6f}",
                }

            # Generate text
            full_response = ""
            async for chunk in client.generate_text_stream(
                prompt, temp, tokens, sys_prompt
            ):
                full_response += chunk
                yield {"text": chunk, "provider": selected_provider}

            # Update cost with actual usage
            if self.cost_estimator:
                actual_cost = self.cost_estimator.update_cost(
                    prompt,
                    full_response,
                    provider=selected_provider,
                    model=config.model,
                    metadata=metadata,
                )
                yield {"status": "info", "message": f"Actual cost: ${actual_cost:.6f}"}

            # Reset failure count on success
            if selected_provider in self.failed_providers:
                self.failed_providers[selected_provider] = 0

        except (APIError, NetworkError) as e:
            self.logger.error(f"Error with provider {selected_provider}: {e}")
            self._handle_provider_failure(selected_provider)
            # Retry with another provider
            async for chunk in self.generate_text(
                prompt, None, temperature, max_tokens, system_prompt, metadata
            ):
                yield chunk
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")
            yield {"error": str(e), "provider": selected_provider}

    def _select_provider(self, prompt: str) -> Optional[str]:
        """Select the best provider using the coordinator."""
        available_providers = [
            p
            for p in self.clients
            if self.failed_providers.get(p, 0) < self.max_retries
        ]
        if not available_providers:
            return None

        # Use coordinator to select provider
        return self.coordinator.select_participant(
            prompt, available_participants=available_providers
        )

    def _handle_provider_failure(self, provider: str):
        """Handle provider failure by incrementing failure count."""
        if provider in self.failed_providers:
            self.failed_providers[provider] += 1
        else:
            self.failed_providers[provider] = 1

        self.logger.warning(
            f"Provider {provider} failed. Failure count: {self.failed_providers[provider]}"
        )

    async def get_embedding(
        self, text: str, provider: Optional[str] = None
    ) -> List[float]:
        """
        Get embeddings for a text using a specified or best provider.

        Args:
            text: The text to embed.
            provider: Optional specific provider to use.

        Returns:
            A list of floats representing the embedding.
        """
        selected_provider = provider or self._select_provider(text)

        if not selected_provider:
            raise APIError("No available providers for embeddings.", "none")

        try:
            client = self.clients[selected_provider]
            embedding = await client.get_embedding(text)

            # Reset failure count on success
            if selected_provider in self.failed_providers:
                self.failed_providers[selected_provider] = 0

            return embedding

        except (APIError, NetworkError) as e:
            self.logger.error(f"Embedding error with provider {selected_provider}: {e}")
            self._handle_provider_failure(selected_provider)
            # Retry with another provider
            return await self.get_embedding(text, None)
        except Exception as e:
            self.logger.error(f"An unexpected embedding error occurred: {e}")
            raise APIError(f"Embedding failed: {e}", selected_provider) from e

    def get_total_cost(self) -> float:
        """Get the total estimated cost of all API calls."""
        return self.cost_estimator.get_total_cost() if self.cost_estimator else 0.0

    def get_cost_by_provider(self) -> Dict[str, float]:
        """Get the total estimated cost by provider."""
        return self.cost_estimator.get_cost_by_provider() if self.cost_estimator else {}

    def get_cost_by_model(self) -> Dict[str, float]:
        """Get the total estimated cost by model."""
        return self.cost_estimator.get_cost_by_model() if self.cost_estimator else {}

    def reset_cost(self):
        """Reset the cost estimator."""
        if self.cost_estimator:
            self.cost_estimator.reset()


# Example usage
async def main():
    """Example usage of the AIClientManager."""
    config_manager = ConfigManager()
    cost_estimator = CostEstimator(config_manager)
    ai_manager = AIClientManager(config_manager, cost_estimator)

    prompt = "Explain the theory of relativity in simple terms."

    print(f"Generating text for prompt: '{prompt}'")
    try:
        async for response in ai_manager.generate_text(prompt):
            if "text" in response:
                print(response["text"], end="", flush=True)
            elif "error" in response:
                print(f"\nError: {response['error']}")
            elif "status" in response:
                print(f"\n[{response['status'].upper()}] {response['message']}")
        print("\n---")

        # Example of getting embeddings
        embedding_text = "This is a test for embeddings."
        print(f"Getting embedding for: '{embedding_text}'")
        embedding = await ai_manager.get_embedding(embedding_text)
        print(f"Embedding received (first 5 dimensions): {embedding[:5]}")
        print(f"Total cost: ${ai_manager.get_total_cost():.6f}")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    # To run this example, ensure you have a 'config/default_config.json'
    # and your API keys are set in a '.env' file.
    # Example config:
    # {
    #     "ai_providers": {
    #         "openai": {
    #             "provider": "openai",
    #             "model": "gpt-4o",
    #             "temperature": 0.7,
    #             "max_tokens": 150
    #         },
    #         "xai": {
    #             "provider": "xai",
    #             "model": "grok-1.5-flash",
    #             "temperature": 0.8,
    #             "max_tokens": 200
    #         }
    #     },
    #     "coordination": {
    #         "base_participation_chance": 0.5,
    #         "max_consecutive_turns": 2,
    #         "mention_boost": 0.7,
    #         "question_boost": 0.3
    #     }
    # }
    asyncio.run(main())
