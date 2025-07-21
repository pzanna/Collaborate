"""OpenAI client wrapper for the Eunice application."""

import openai
import os
import sys
import logging
import time
from typing import List, Dict, Any, Optional

# Import models
try:
    from ..models.data_models import Message, AIConfig
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models.data_models import Message, AIConfig


class OpenAIClient:
    """OpenAI client wrapper."""
    
    def __init__(self, api_key: str, config: AIConfig):
        self.client = openai.OpenAI(api_key=api_key)
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def get_response(self, messages: List[Message], system_prompt: Optional[str] = None) -> str:
        """Get response from OpenAI."""
        start_time = time.time()
        estimated_tokens = self.estimate_tokens(messages)
        
        # Log API request details
        self.logger.info(f"OpenAI API Request - Model: {self.config.model}, "
                        f"Messages: {len(messages)}, Estimated tokens: {estimated_tokens}, "
                        f"Temperature: {self.config.temperature}, Max tokens: {self.config.max_tokens}")
        
        try:
            # Convert messages to OpenAI format
            openai_messages = self._convert_messages_to_openai_format(messages, system_prompt)
            
            # Make the API call
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=openai_messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            response_time = time.time() - start_time
            response_content = response.choices[0].message.content or ""
            
            # Log successful response details
            self.logger.info(f"OpenAI API Response - Success: Content length: {len(response_content)}, "
                           f"Response time: {response_time:.2f}s, "
                           f"Usage: {getattr(response, 'usage', 'N/A')}")
            
            # Log response content (truncated for readability)
            content_preview = response_content[:200] + "..." if len(response_content) > 200 else response_content
            self.logger.debug(f"OpenAI Response content preview: {content_preview}")
            
            return response_content
        
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = f"OpenAI API error: {str(e)}"
            
            # Log error details
            self.logger.error(f"OpenAI API Error - Model: {self.config.model}, "
                            f"Response time: {response_time:.2f}s, Error: {error_msg}")
            
            raise Exception(error_msg)
    
    def _convert_messages_to_openai_format(self, messages: List[Message], system_prompt: Optional[str] = None) -> List[Dict[str, Any]]:
        """Convert internal messages to OpenAI format."""
        openai_messages = []
        
        # Add system prompt
        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})
        elif self.config.system_prompt:
            openai_messages.append({"role": "system", "content": self.config.system_prompt})
        
        # Convert messages
        for message in messages:
            if message.participant == "user":
                openai_messages.append({"role": "user", "content": message.content})
            elif message.participant == "openai":
                openai_messages.append({"role": "assistant", "content": message.content})
            elif message.participant == "xai":
                # Include xAI responses as user messages for context
                openai_messages.append({"role": "user", "content": f"[xAI]: {message.content}"})
        
        return openai_messages
    
    def estimate_tokens(self, messages: List[Message]) -> int:
        """Estimate token count for messages."""
        # Simple approximation: ~4 characters per token
        total_chars = sum(len(msg.content) for msg in messages)
        return total_chars // 4
    
    def update_config(self, **kwargs) -> None:
        """Update client configuration."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
