"""xAI client wrapper for the Collaborate application."""

import os
import sys
import logging
import time
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
        self.logger = logging.getLogger(__name__)
    
    def get_response(self, messages: List[Message], system_prompt: Optional[str] = None) -> str:
        """Get response from xAI."""
        start_time = time.time()
        estimated_tokens = self.estimate_tokens(messages)
        
        # Log API request details
        self.logger.info(f"xAI API Request - Model: {self.config.model}, "
                        f"Messages: {len(messages)}, Estimated tokens: {estimated_tokens}, "
                        f"Temperature: {self.config.temperature}, Max tokens: {self.config.max_tokens}")
        
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
            
            response_time = time.time() - start_time
            
            # Extract content from response
            if hasattr(response, 'content'):
                response_content = response.content or ""
            else:
                response_content = str(response)
            
            # Log successful response details
            self.logger.info(f"xAI API Response - Success: Content length: {len(response_content)}, "
                           f"Response time: {response_time:.2f}s")
            
            # Log response content (truncated for readability)
            content_preview = response_content[:200] + "..." if len(response_content) > 200 else response_content
            self.logger.debug(f"xAI Response content preview: {content_preview}")
            
            return response_content
        
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = f"xAI API error: {str(e)}"
            
            # Log error details
            self.logger.error(f"xAI API Error - Model: {self.config.model}, "
                            f"Response time: {response_time:.2f}s, Error: {error_msg}")
            
            raise Exception(error_msg)
    
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
