"""xAI client wrapper for the Collaborate application."""

import os
import sys
from xai_sdk import Client
from xai_sdk.chat import user, system, assistant
from typing import List, Optional

# Import models
try:
    from ..models.data_models import Message, AIConfig
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models.data_models import Message, AIConfig


class XAIClient:
    """xAI client wrapper."""
    
    def __init__(self, api_key: str, config: AIConfig):
        self.client = Client(api_key=api_key)
        self.config = config
    
    def get_response(self, messages: List[Message], system_prompt: Optional[str] = None) -> str:
        """Get response from xAI."""
        try:
            # Create a chat instance
            chat = self.client.chat.create(model=self.config.model)
            
            # Add system prompt if provided
            if system_prompt:
                chat.append(system(system_prompt))
            elif self.config.system_prompt:
                chat.append(system(self.config.system_prompt))
            
            # Add messages in chronological order
            for message in messages:
                if message.participant == "user":
                    chat.append(user(message.content))
                elif message.participant == "xai":
                    chat.append(assistant(message.content))
                elif message.participant == "openai":
                    # Include OpenAI responses as user messages for context
                    chat.append(user(f"[OpenAI]: {message.content}"))
            
            # Get response from the chat
            response = chat.sample()
            
            # Extract content from response
            if hasattr(response, 'content'):
                return response.content or ""
            
            # If we can't find content, return the string representation
            return str(response)
        
        except Exception as e:
            raise Exception(f"xAI API error: {str(e)}")
    
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
