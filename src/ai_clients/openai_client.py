"""OpenAI client wrapper for the Eunice application."""

import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional

import openai
from pydantic import BaseModel, Field

sys.path.append(os.path.dirname(os.path.dirname(__file__)))


class AIProviderConfig(BaseModel):
    """AI configuration model."""

    provider: str  # openai, xai
    model: str
    temperature: float = 0.7
    max_tokens: int = 2000
    system_prompt: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OpenAIClient:
    """OpenAI client wrapper."""

    def __init__(self, api_key: str, config: AIProviderConfig):
        self.client = openai.OpenAI(api_key=api_key)
        self.config = config
        self.logger = logging.getLogger(__name__)

    def get_response(self, user_message: str, system_prompt: Optional[str] = None) -> str:
        """Get response from OpenAI."""
        start_time = time.time()
        estimated_tokens = self.estimate_tokens(user_message)

        # Log API request details
        self.logger.info(
            f"OpenAI API Request - Model: {self.config.model}, "
            f"Message length: {len(user_message)}, Estimated tokens: {estimated_tokens}, "
            f"Temperature: {self.config.temperature}, Max tokens: {self.config.max_tokens}"
        )

        try:
            # Prepare messages for OpenAI API
            messages = []

            # Add system prompt
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            elif self.config.system_prompt:
                messages.append({"role": "system", "content": self.config.system_prompt})

            # Add user message
            messages.append({"role": "user", "content": user_message})

            # Make the API call
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            response_time = time.time() - start_time
            response_content = response.choices[0].message.content or ""

            # Log successful response details
            self.logger.info(
                f"OpenAI API Response - Success: Content length: {len(response_content)}, "
                f"Response time: {response_time:.2f}s, "
                f"Usage: {getattr(response, 'usage', 'N / A')}"
            )

            # Log response content (truncated and sanitized for log format)
            content_preview = response_content[:200] + "..." if len(response_content) > 200 else response_content
            # Sanitize content for single - line log entry (replace newlines and multiple spaces)
            sanitized_preview = content_preview.replace("\n", " ").replace("\r", " ")
            sanitized_preview = " ".join(sanitized_preview.split())  # Normalize whitespace
            self.logger.debug(f"OpenAI Response content preview: {sanitized_preview}")

            return response_content

        except Exception as e:
            response_time = time.time() - start_time
            error_msg = f"OpenAI API error: {str(e)}"

            # Log error details
            self.logger.error(
                f"OpenAI API Error - Model: {self.config.model}, "
                f"Response time: {response_time:.2f}s, Error: {error_msg}"
            )

            raise Exception(error_msg)

    def estimate_tokens(self, message: str) -> int:
        """Estimate token count for a message."""
        # Simple approximation: ~4 characters per token
        return len(message) // 4

    def update_config(self, **kwargs) -> None:
        """Update client configuration."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
