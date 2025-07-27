"""
AI Service - Centralized AI Provider Access

This service provides unified access to multiple AI providers (OpenAI, Anthropic, XAI)
with load balancing, cost optimization, and usage tracking.
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
import httpx
import openai
import anthropic
from datetime import datetime, timedelta

# Load configuration
def load_config():
    """Load configuration from config file"""
    config_path = Path(__file__).parent.parent / "config" / "config.json"
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "service": {"host": "0.0.0.0", "port": 8010, "name": "ai-service"},
            "providers": {
                "openai": {"enabled": True, "models": ["gpt-4o-mini", "gpt-4"]},
                "anthropic": {"enabled": True, "models": ["claude-3-haiku", "claude-3-sonnet"]},
                "xai": {"enabled": True, "models": ["grok-3-mini-beta", "grok-3"]}
            },
            "load_balancing": {"strategy": "round_robin", "health_check_interval": 30},
            "rate_limiting": {"requests_per_minute": 100, "tokens_per_minute": 50000},
            "logging": {"level": "INFO"}
        }

config = load_config()

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.get("logging", {}).get("level", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="AI Service",
    description="Centralized AI provider access with load balancing and cost optimization",
    version="1.0.0"
)

# Request/Response Models
class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: system, user, or assistant")
    content: str = Field(..., description="Message content")

class ChatCompletionRequest(BaseModel):
    model: str = Field(..., description="AI model to use")
    messages: List[ChatMessage] = Field(..., description="Conversation messages")
    temperature: float = Field(0.7, description="Sampling temperature")
    max_tokens: int = Field(2000, description="Maximum tokens to generate")
    provider: Optional[str] = Field(None, description="Specific provider to use")

class ChatCompletionResponse(BaseModel):
    content: str = Field(..., description="Generated response content")
    model: str = Field(..., description="Model used for generation")
    provider: str = Field(..., description="Provider used")
    usage: Dict[str, Any] = Field(..., description="Token usage information")
    processing_time: float = Field(..., description="Processing time in seconds")

class EmbeddingRequest(BaseModel):
    input: Union[str, List[str]] = Field(..., description="Text to embed")
    model: str = Field("text-embedding-ada-002", description="Embedding model")
    provider: Optional[str] = Field(None, description="Specific provider to use")

class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]] = Field(..., description="Generated embeddings")
    model: str = Field(..., description="Model used")
    provider: str = Field(..., description="Provider used")
    usage: Dict[str, Any] = Field(..., description="Token usage information")

class HealthResponse(BaseModel):
    status: str
    providers: Dict[str, Dict[str, Any]]
    uptime_seconds: int
    total_requests: int

class AIService:
    """Centralized AI service with multi-provider support"""
    
    def __init__(self):
        self.start_time = time.time()
        self.request_count = 0
        self.clients = {}
        self.provider_health = {}
        self.load_balancer_index = 0
        
        self._initialize_clients()
        
    def _initialize_clients(self):
        """Initialize AI provider clients with secure API key handling"""
        providers_config = config.get("providers", {})
        
        # Initialize OpenAI client
        if providers_config.get("openai", {}).get("enabled", False):
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key and self._validate_api_key(api_key, "openai"):
                try:
                    self.clients["openai"] = openai.AsyncOpenAI(api_key=api_key)
                    self.provider_health["openai"] = {"status": "healthy", "last_check": time.time()}
                    logger.info("OpenAI client initialized successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize OpenAI client: {e}")
                    self.provider_health["openai"] = {"status": "unhealthy", "error": str(e)}
            else:
                logger.warning("OpenAI API key not found or invalid")
        
        # Initialize Anthropic client
        if providers_config.get("anthropic", {}).get("enabled", False):
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key and self._validate_api_key(api_key, "anthropic"):
                try:
                    self.clients["anthropic"] = anthropic.AsyncAnthropic(api_key=api_key)
                    self.provider_health["anthropic"] = {"status": "healthy", "last_check": time.time()}
                    logger.info("Anthropic client initialized successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize Anthropic client: {e}")
                    self.provider_health["anthropic"] = {"status": "unhealthy", "error": str(e)}
            else:
                logger.warning("Anthropic API key not found or invalid")
        
        # Initialize XAI client (using OpenAI-compatible API)
        if providers_config.get("xai", {}).get("enabled", False):
            api_key = os.getenv("XAI_API_KEY")
            if api_key and self._validate_api_key(api_key, "xai"):
                try:
                    self.clients["xai"] = openai.AsyncOpenAI(
                        api_key=api_key,
                        base_url="https://api.x.ai/v1"
                    )
                    self.provider_health["xai"] = {"status": "healthy", "last_check": time.time()}
                    logger.info("XAI client initialized successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize XAI client: {e}")
                    self.provider_health["xai"] = {"status": "unhealthy", "error": str(e)}
            else:
                logger.warning("XAI API key not found or invalid")
        
        if not self.clients:
            logger.error("No AI providers configured!")
        else:
            logger.info(f"Initialized {len(self.clients)} AI provider clients")
            
    def _validate_api_key(self, api_key: str, provider: str) -> bool:
        """Validate API key format for security"""
        if not api_key or len(api_key) < 10:
            return False
            
        # Basic format validation
        if provider == "openai" and not api_key.startswith("sk-"):
            logger.warning("OpenAI API key should start with 'sk-'")
            return False
        elif provider == "anthropic" and not api_key.startswith("sk-ant-"):
            logger.warning("Anthropic API key should start with 'sk-ant-'")
            return False
        elif provider == "xai" and not api_key.startswith("xai-"):
            logger.warning("XAI API key should start with 'xai-'")
            return False
            
        # Check for placeholder values
        placeholder_patterns = [
            "your_", "replace_", "api_key_here", "example_", "test_key"
        ]
        if any(pattern in api_key.lower() for pattern in placeholder_patterns):
            logger.warning(f"API key for {provider} appears to be a placeholder")
            return False
            
        return True
            
    def _get_provider_for_model(self, model: str) -> str:
        """Determine which provider to use for a given model based on model name"""
        # OpenAI models
        if any(model.startswith(prefix) for prefix in ["gpt-", "text-embedding", "whisper", "dall-e"]):
            return "openai"
        
        # Anthropic models (Claude)
        if any(model.startswith(prefix) for prefix in ["claude-"]):
            return "anthropic"
            
        # XAI models (Grok)
        if any(model.startswith(prefix) for prefix in ["grok-"]):
            return "xai"
            
        # Default fallback based on exact model names from config
        providers_config = config.get("providers", {})
        for provider, provider_config in providers_config.items():
            if model in provider_config.get("models", []):
                return provider
        
        # Final fallback to OpenAI
        logger.warning(f"Unknown model '{model}', defaulting to OpenAI")
        return "openai"
    
    def _select_provider(self, preferred_provider: Optional[str] = None, model: Optional[str] = None) -> str:
        """Select AI provider using load balancing or model-based routing"""
        available_providers = [p for p, health in self.provider_health.items() 
                              if health["status"] == "healthy" and p in self.clients]
        
        if not available_providers:
            raise HTTPException(status_code=503, detail="No healthy AI providers available")
        
        # If model is specified, use model-based routing
        if model:
            model_provider = self._get_provider_for_model(model)
            if model_provider in available_providers:
                return model_provider
            else:
                logger.warning(f"Preferred provider '{model_provider}' for model '{model}' not available, using fallback")
        
        # Use preferred provider if specified and available
        if preferred_provider and preferred_provider in available_providers:
            return preferred_provider
        
        # Round-robin load balancing for fallback
        provider = available_providers[self.load_balancer_index % len(available_providers)]
        self.load_balancer_index += 1
        
        return provider
    
    async def chat_completion(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """Generate chat completion using selected AI provider"""
        start_time = time.time()
        self.request_count += 1
        
        provider = None
        content = ""
        usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        try:
            provider = self._select_provider(request.provider, request.model)
            client = self.clients[provider]
            
            # Convert messages to provider format
            messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
            
            if provider == "openai" or provider == "xai":
                response = await client.chat.completions.create(
                    model=request.model,
                    messages=messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens
                )
                
                # Handle reasoning models (like grok-3-mini) that may have reasoning_content
                message = response.choices[0].message
                content = message.content or ""
                
                # For reasoning models, check if there's reasoning_content to include
                # According to xAI docs, grok-3-mini and grok-3-mini-fast return reasoning_content
                reasoning_content = getattr(message, 'reasoning_content', None)
                if reasoning_content:
                    if content:
                        content = f"**Reasoning Process:**\n{reasoning_content}\n\n**Final Response:**\n{content}"
                    else:
                        # If no final content but has reasoning, use reasoning as the response
                        content = f"**Reasoning Process:**\n{reasoning_content}"
                
                # Include reasoning tokens in usage if available (for reasoning models)
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                }
                
                # Add reasoning tokens if available (specific to reasoning models)
                if hasattr(response.usage, 'reasoning_tokens') and response.usage.reasoning_tokens:
                    usage["reasoning_tokens"] = response.usage.reasoning_tokens
                
            elif provider == "anthropic":
                # Convert system message for Anthropic
                system_msg = ""
                user_messages = []
                
                for msg in messages:
                    if msg["role"] == "system":
                        system_msg = msg["content"]
                    else:
                        user_messages.append(msg)
                
                # Use the modern Anthropic API
                response = await client.messages.create(
                    model=request.model,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    system=system_msg if system_msg else "You are a helpful assistant.",
                    messages=user_messages
                )
                
                # Extract content from modern API response
                if hasattr(response, 'content') and response.content:
                    if isinstance(response.content, list) and len(response.content) > 0:
                        content = response.content[0].text if hasattr(response.content[0], 'text') else str(response.content[0])
                    else:
                        content = str(response.content)
                else:
                    content = ""
                
                # Extract usage information
                usage = {
                    "prompt_tokens": getattr(response.usage, 'input_tokens', 0) if hasattr(response, 'usage') else 0,
                    "completion_tokens": getattr(response.usage, 'output_tokens', 0) if hasattr(response, 'usage') else 0,
                    "total_tokens": (getattr(response.usage, 'input_tokens', 0) + getattr(response.usage, 'output_tokens', 0)) if hasattr(response, 'usage') else 0
                }
            
            processing_time = time.time() - start_time
            
            return ChatCompletionResponse(
                content=content,
                model=request.model,
                provider=provider or "unknown",
                usage=usage,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Chat completion error: {e}")
            # Mark provider as unhealthy
            if provider:
                self.provider_health[provider]["status"] = "unhealthy"
            raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")
    
    async def create_embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Create embeddings using selected AI provider"""
        try:
            # Only OpenAI supports embeddings currently
            provider = self._select_provider(request.provider, request.model)
            
            # Force OpenAI for embeddings since others don't support it yet
            if provider != "openai":
                if "openai" in self.clients and self.provider_health.get("openai", {}).get("status") == "healthy":
                    provider = "openai"
                else:
                    raise HTTPException(status_code=503, detail="OpenAI client not available for embeddings")
            
            client = self.clients[provider]
            
            input_texts = request.input if isinstance(request.input, list) else [request.input]
            
            response = await client.embeddings.create(
                model=request.model,
                input=input_texts
            )
            
            embeddings = [data.embedding for data in response.data]
            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0
            }
            
            return EmbeddingResponse(
                embeddings=embeddings,
                model=request.model,
                provider=provider,
                usage=usage
            )
            
        except Exception as e:
            logger.error(f"Embedding creation error: {e}")
            raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get service health status"""
        uptime = int(time.time() - self.start_time)
        
        return {
            "status": "healthy" if any(h["status"] == "healthy" for h in self.provider_health.values()) else "unhealthy",
            "providers": self.provider_health,
            "uptime_seconds": uptime,
            "total_requests": self.request_count
        }

# Global service instance
ai_service = AIService()

# API Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    health_data = ai_service.get_health_status()
    return HealthResponse(**health_data)

@app.post("/ai/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    """Generate chat completions"""
    return await ai_service.chat_completion(request)

@app.post("/ai/embeddings", response_model=EmbeddingResponse)
async def create_embeddings(request: EmbeddingRequest):
    """Create text embeddings"""
    return await ai_service.create_embeddings(request)

@app.get("/ai/models/available")
async def get_available_models():
    """Get available models by provider"""
    models = {}
    providers_config = config.get("providers", {})
    
    for provider, provider_config in providers_config.items():
        if provider_config.get("enabled", False) and provider in ai_service.clients:
            models[provider] = provider_config.get("models", [])
    
    return {"models": models}

@app.get("/ai/usage/statistics")
async def get_usage_statistics():
    """Get usage statistics"""
    return {
        "total_requests": ai_service.request_count,
        "uptime_seconds": int(time.time() - ai_service.start_time),
        "providers": ai_service.provider_health
    }

if __name__ == "__main__":
    SERVICE_HOST = os.getenv("SERVICE_HOST", config["service"]["host"])
    SERVICE_PORT = int(os.getenv("SERVICE_PORT", config["service"]["port"]))
    
    logger.info(f"Starting AI Service on {SERVICE_HOST}:{SERVICE_PORT}")
    
    uvicorn.run(
        app,
        host=SERVICE_HOST,
        port=SERVICE_PORT,
        log_level="info"
    )
