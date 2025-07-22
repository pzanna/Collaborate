"""xAI client wrapper for the Eunice application."""

import os
import sys
import logging
import time
from xai_sdk import Client
from xai_sdk.chat import user, system, assistant
from typing import List, Optional, Dict, Any
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


class XAIClient:
    """xAI client wrapper."""
    
    def __init__(self, api_key: str, config: AIProviderConfig):
        self.client = Client(api_key=api_key)
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def get_response(self, user_message: str, system_prompt: Optional[str] = None) -> str:
        """Get response from xAI."""
        start_time = time.time()
        estimated_tokens = self.estimate_tokens(user_message)
        
        # Log API request details
        self.logger.info(f"xAI API Request - Model: {self.config.model}, "
                        f"Message length: {len(user_message)}, Estimated tokens: {estimated_tokens}, "
                        f"Temperature: {self.config.temperature}, Max tokens: {self.config.max_tokens}")
        
        try:
            # Create a chat instance
            chat = self.client.chat.create(model=self.config.model)
            
            # Add system prompt if provided
            if system_prompt:
                chat.append(system(system_prompt))
            elif self.config.system_prompt:
                chat.append(system(self.config.system_prompt))
            
            # Add user message
            chat.append(user(user_message))
            
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
            
            # Log response content (truncated and sanitized for log format)
            content_preview = response_content[:200] + "..." if len(response_content) > 200 else response_content
            # Sanitize content for single-line log entry (replace newlines and multiple spaces)
            sanitized_preview = content_preview.replace('\n', ' ').replace('\r', ' ')
            sanitized_preview = ' '.join(sanitized_preview.split())  # Normalize whitespace
            self.logger.debug(f"xAI Response content preview: {sanitized_preview}")
            
            return response_content
        
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = f"xAI API error: {str(e)}"
            
            # Log error details
            self.logger.error(f"xAI API Error - Model: {self.config.model}, "
                            f"Response time: {response_time:.2f}s, Error: {error_msg}")
            
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
