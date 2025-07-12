"""OpenAI client wrapper for the Collaborate application."""

import openai
import os
import sys
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
    
    def get_response(self, messages: List[Message], system_prompt: Optional[str] = None) -> str:
        """Get response from OpenAI."""
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
            
            return response.choices[0].message.content or ""
        
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
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
