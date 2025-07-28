"""
AI Service - Centralized AI Provider Access with MCP Integration

This service provides unified access to multiple AI providers (OpenAI, Anthropic, XAI)
with load balancing, cost optimization, caching, and usage tracking.
Enhanced with MCP client capabilities for bidirectional agent communication.
Fully aligned with Phase 3 Service Architecture specifications.
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import hashlib

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import httpx
import openai
import anthropic
import redis.asyncio as redis
import websockets
from datetime import datetime, timedelta


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware to enforce MCP-only access"""
    
    def __init__(self, app, security_config: Dict[str, Any]):
        super().__init__(app)
        self.security_config = security_config
        self.mcp_only = security_config.get("mcp_only", True)
        self.allowed_origins = security_config.get("allowed_origins", ["mcp-server"])
        self.require_mcp_auth = security_config.get("require_mcp_auth", True)
        
    async def dispatch(self, request: Request, call_next):
        # Allow health checks for monitoring
        if request.url.path == "/health":
            return await call_next(request)
        
        # Get client information
        client_host = request.client.host if request.client else "unknown"
        
        # If MCP-only mode is enabled, validate the request
        if self.mcp_only:
            # Check if request comes from allowed origins
            origin = request.headers.get("host", "").split(":")[0]
            x_forwarded_for = request.headers.get("x-forwarded-for")
            x_real_ip = request.headers.get("x-real-ip")
            
            # Allow requests from MCP server or internal Docker network
            allowed_sources = [
                "mcp-server",  # Docker service name
                "127.0.0.1",   # Localhost
                "localhost",   # Localhost
                "::1"          # IPv6 localhost
            ]
            
            # Check if request has MCP authentication header
            mcp_auth_header = request.headers.get("x-mcp-auth")
            mcp_service_id = request.headers.get("x-mcp-service-id")
            
            if self.require_mcp_auth:
                if not mcp_auth_header or not mcp_service_id:
                    logger.warning(f"Blocked direct access attempt from {client_host} - missing MCP headers")
                    return JSONResponse(
                        status_code=403,
                        content={
                            "error": "Direct access forbidden",
                            "message": "AI Service only accepts requests routed through MCP Server",
                            "code": "MCP_AUTH_REQUIRED"
                        }
                    )
                
                # Validate MCP authentication
                if mcp_service_id != "mcp-server":
                    logger.warning(f"Blocked access attempt with invalid MCP service ID: {mcp_service_id}")
                    return JSONResponse(
                        status_code=403,
                        content={
                            "error": "Invalid MCP authentication",
                            "message": "Request must come from authorized MCP Server",
                            "code": "INVALID_MCP_AUTH"
                        }
                    )
            
            # Additional validation for non-Docker environments
            if not any(source in client_host for source in allowed_sources):
                # Allow if it's from internal Docker network (typically 172.x.x.x)
                if not (client_host.startswith("172.") or client_host.startswith("10.") or client_host.startswith("192.168.")):
                    logger.warning(f"Blocked external access attempt from {client_host}")
                    return JSONResponse(
                        status_code=403,
                        content={
                            "error": "External access forbidden",
                            "message": "AI Service only accepts requests from MCP Server",
                            "code": "EXTERNAL_ACCESS_DENIED"
                        }
                    )
        
        # Log authorized request
        logger.debug(f"Authorized request from {client_host} to {request.url.path}")
        return await call_next(request)

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
            "security": {
                "mcp_only": True,
                "allowed_origins": ["mcp-server"],
                "require_mcp_auth": True,
                "block_direct_access": True
            },
            "mcp": {
                "enabled": True,
                "server_host": "mcp-server",
                "server_port": 9000,
                "client_id": "ai-service",
                "reconnect_delay": 5
            },
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


class MCPClient:
    """MCP Client for AI Service to communicate with agents via MCP Server"""
    
    def __init__(self, host: str = "mcp-server", port: int = 9000, client_id: str = "ai-service"):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.websocket: Optional[Any] = None
        self.is_connected = False
        self.response_callbacks: Dict[str, asyncio.Future] = {}
        self._listen_task: Optional[asyncio.Task] = None
        self._should_reconnect = True
        self.reconnect_delay = 5
        
    async def connect(self) -> bool:
        """Connect to MCP server"""
        try:
            uri = f"ws://{self.host}:{self.port}/ws"
            logger.info(f"AI Service connecting to MCP Server at {uri}")
            self.websocket = await websockets.connect(uri)
            self.is_connected = True
            
            # Start listening for messages
            self._listen_task = asyncio.create_task(self._listen_for_messages())
            
            # Register as AI service with MCP server
            await self._register_service()
            
            logger.info("AI Service successfully connected to MCP Server")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            self.is_connected = False
            return False
    
    async def _register_service(self):
        """Register AI service with MCP server"""
        registration_message = {
            "type": "service_registration",
            "service_id": self.client_id,
            "service_type": "ai-service",
            "capabilities": ["chat_completions", "embeddings", "model_management"],
            "timestamp": datetime.utcnow().isoformat()
        }
        await self._send_message(registration_message)
    
    async def _listen_for_messages(self):
        """Listen for incoming messages from MCP server"""
        if not self.websocket:
            logger.error("No websocket connection available")
            return
            
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode message: {e}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
        except websockets.exceptions.ConnectionClosed:
            logger.warning("MCP connection closed")
            self.is_connected = False
            if self._should_reconnect:
                await self._reconnect()
    
    async def _handle_message(self, data: Dict[str, Any]):
        """Handle incoming messages from MCP server"""
        message_type = data.get("type")
        
        if message_type == "agent_notification":
            # Handle notifications to specific agents
            await self._handle_agent_notification(data)
        elif message_type == "usage_alert":
            # Handle usage/cost alerts
            await self._handle_usage_alert(data)
        elif message_type == "model_availability":
            # Handle model availability updates
            await self._handle_model_availability(data)
        else:
            logger.debug(f"Received unknown message type: {message_type}")
    
    async def _handle_agent_notification(self, data: Dict[str, Any]):
        """Handle notifications to agents"""
        agent_id = data.get("target_agent")
        notification = data.get("notification")
        logger.info(f"Sending notification to agent {agent_id}: {notification}")
    
    async def _handle_usage_alert(self, data: Dict[str, Any]):
        """Handle usage/cost alerts"""
        alert_type = data.get("alert_type")
        threshold = data.get("threshold")
        current_usage = data.get("current_usage")
        logger.warning(f"Usage alert: {alert_type} - {current_usage}/{threshold}")
    
    async def _handle_model_availability(self, data: Dict[str, Any]):
        """Handle model availability updates"""
        provider = data.get("provider")
        model = data.get("model")
        available = data.get("available")
        logger.info(f"Model availability update: {provider}/{model} = {available}")
    
    async def _send_message(self, message: Dict[str, Any]):
        """Send message to MCP server"""
        if not self.is_connected or not self.websocket:
            logger.error("Cannot send message: not connected to MCP server")
            return False
        
        try:
            await self.websocket.send(json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    async def notify_agent(self, agent_id: str, notification: Dict[str, Any]) -> bool:
        """Send notification to specific agent via MCP Server"""
        message = {
            "type": "agent_notification",
            "source": self.client_id,
            "target_agent": agent_id,
            "notification": notification,
            "timestamp": datetime.utcnow().isoformat()
        }
        return await self._send_message(message)
    
    async def broadcast_usage_alert(self, alert_type: str, details: Dict[str, Any]) -> bool:
        """Broadcast usage alert to all connected agents"""
        message = {
            "type": "usage_alert",
            "source": self.client_id,
            "alert_type": alert_type,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
        return await self._send_message(message)
    
    async def update_model_availability(self, provider: str, model: str, available: bool) -> bool:
        """Update model availability status"""
        message = {
            "type": "model_availability",
            "source": self.client_id,
            "provider": provider,
            "model": model,
            "available": available,
            "timestamp": datetime.utcnow().isoformat()
        }
        return await self._send_message(message)
    
    async def _reconnect(self):
        """Attempt to reconnect to MCP server"""
        while self._should_reconnect and not self.is_connected:
            logger.info(f"Attempting to reconnect to MCP server in {self.reconnect_delay} seconds...")
            await asyncio.sleep(self.reconnect_delay)
            await self.connect()
    
    async def disconnect(self):
        """Disconnect from MCP server"""
        self._should_reconnect = False
        if self._listen_task:
            self._listen_task.cancel()
        if self.websocket:
            await self.websocket.close()
        self.is_connected = False

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.get("logging", {}).get("level", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="AI Service",
    description="Centralized AI provider access with load balancing and cost optimization (MCP-only access)",
    version="1.0.0"
)

# Add security middleware
security_config = config.get("security", {})
app.add_middleware(SecurityMiddleware, security_config=security_config)

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
    cache_status: Dict[str, Any]
    metrics: Dict[str, Any]

class MetricsResponse(BaseModel):
    total_requests: int
    requests_by_provider: Dict[str, int]
    average_response_time: float
    error_rate: float
    cache_hit_rate: float
    uptime_seconds: int

class AIService:
    """Centralized AI service with multi-provider support, caching, monitoring, and MCP integration"""
    
    def __init__(self):
        self.start_time = time.time()
        self.request_count = 0
        self.error_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.response_times = []
        self.provider_request_counts = {"openai": 0, "anthropic": 0, "xai": 0}
        self.clients = {}
        self.provider_health = {}
        self.load_balancer_index = 0
        self.redis_client = None
        
        # Initialize MCP client if enabled
        mcp_config = config.get("mcp", {})
        self.mcp_client = None
        if mcp_config.get("enabled", True):
            self.mcp_client = MCPClient(
                host=mcp_config.get("server_host", "mcp-server"),
                port=mcp_config.get("server_port", 9000),
                client_id=mcp_config.get("client_id", "ai-service")
            )
        
        self._initialize_clients()
        asyncio.create_task(self._initialize_redis())
        
        # Initialize MCP connection
        if self.mcp_client:
            asyncio.create_task(self._initialize_mcp_client())
    
    async def _initialize_mcp_client(self):
        """Initialize MCP client connection"""
        if not self.mcp_client:
            logger.warning("No MCP client available for initialization")
            return
            
        try:
            success = await self.mcp_client.connect()
            if success:
                logger.info("AI Service MCP client initialized successfully")
            else:
                logger.warning("Failed to initialize MCP client - continuing without MCP integration")
        except Exception as e:
            logger.error(f"Error initializing MCP client: {e}")
            self.mcp_client = None
        
    async def _initialize_redis(self):
        """Initialize Redis connection for caching"""
        caching_config = config.get("caching", {})
        if caching_config.get("enabled", False):
            redis_url = os.getenv("REDIS_URL", caching_config.get("redis_url", "redis://localhost:6379"))
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                await self.redis_client.ping()
                logger.info("Redis connection established successfully")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Caching disabled.")
                self.redis_client = None
        
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
        
        # Enhanced load balancing strategy
        load_balance_strategy = config.get("load_balancing", {}).get("strategy", "round_robin")
        
        if load_balance_strategy == "least_connections":
            # Select provider with least active requests
            return min(available_providers, key=lambda p: self.provider_request_counts.get(p, 0))
        elif load_balance_strategy == "weighted_round_robin":
            # Weighted selection based on provider performance
            weights = {"openai": 3, "anthropic": 2, "xai": 1}  # Example weights
            weighted_providers = [p for p in available_providers for _ in range(weights.get(p, 1))]
            if weighted_providers:
                provider = weighted_providers[self.load_balancer_index % len(weighted_providers)]
                self.load_balancer_index += 1
                return provider
        
        # Default: Round-robin load balancing
        provider = available_providers[self.load_balancer_index % len(available_providers)]
        self.load_balancer_index += 1
        
        return provider
    
    async def _cache_get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response"""
        if not self.redis_client:
            return None
        
        try:
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                self.cache_hits += 1
                return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
        
        self.cache_misses += 1
        return None
    
    async def _cache_set(self, cache_key: str, data: Dict[str, Any], ttl: int = 3600):
        """Set cached response"""
        if not self.redis_client:
            return
        
        try:
            await self.redis_client.setex(cache_key, ttl, json.dumps(data))
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
    
    def _generate_cache_key(self, request_data: Dict[str, Any]) -> str:
        """Generate cache key for request"""
        # Create a hash of the request parameters for caching
        cache_str = json.dumps(request_data, sort_keys=True)
        return f"ai_response:{hashlib.md5(cache_str.encode(), usedforsecurity=False).hexdigest()}"
    
    async def chat_completion(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """Generate chat completion using selected AI provider with caching"""
        start_time = time.time()
        self.request_count += 1
        
        # Generate cache key
        cache_data = {
            "model": request.model,
            "messages": [{"role": msg.role, "content": msg.content} for msg in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens
        }
        cache_key = self._generate_cache_key(cache_data)
        
        # Check cache first
        cached_response = await self._cache_get(cache_key)
        if cached_response:
            logger.info("Cache hit for chat completion request")
            return ChatCompletionResponse(**cached_response)
        
        provider = None
        content = ""
        usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        try:
            provider = self._select_provider(request.provider, request.model)
            self.provider_request_counts[provider] += 1
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
            self.response_times.append(processing_time)
            
            # Keep only last 1000 response times for memory efficiency
            if len(self.response_times) > 1000:
                self.response_times = self.response_times[-1000:]
            
            response_data = {
                "content": content,
                "model": request.model,
                "provider": provider or "unknown",
                "usage": usage,
                "processing_time": processing_time
            }
            
            # Cache the response
            caching_config = config.get("caching", {})
            if caching_config.get("enabled", False):
                ttl = caching_config.get("ttl_seconds", 3600)
                await self._cache_set(cache_key, response_data, ttl)
            
            return ChatCompletionResponse(**response_data)
            
        except Exception as e:
            self.error_count += 1
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
        """Get service health status with caching and metrics"""
        uptime = int(time.time() - self.start_time)
        
        # Calculate cache hit rate
        total_cache_requests = self.cache_hits + self.cache_misses
        cache_hit_rate = (self.cache_hits / total_cache_requests) if total_cache_requests > 0 else 0.0
        
        # Calculate average response time
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0.0
        
        # Calculate error rate
        error_rate = (self.error_count / self.request_count) if self.request_count > 0 else 0.0
        
        cache_status = {
            "redis_connected": self.redis_client is not None,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": cache_hit_rate
        }
        
        metrics = {
            "average_response_time": avg_response_time,
            "error_rate": error_rate,
            "requests_by_provider": self.provider_request_counts.copy()
        }
        
        return {
            "status": "healthy" if any(h["status"] == "healthy" for h in self.provider_health.values()) else "unhealthy",
            "providers": self.provider_health,
            "uptime_seconds": uptime,
            "total_requests": self.request_count,
            "cache_status": cache_status,
            "metrics": metrics
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get detailed service metrics"""
        uptime = int(time.time() - self.start_time)
        
        # Calculate metrics
        total_cache_requests = self.cache_hits + self.cache_misses
        cache_hit_rate = (self.cache_hits / total_cache_requests) if total_cache_requests > 0 else 0.0
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0.0
        error_rate = (self.error_count / self.request_count) if self.request_count > 0 else 0.0
        
        return {
            "total_requests": self.request_count,
            "requests_by_provider": self.provider_request_counts.copy(),
            "average_response_time": avg_response_time,
            "error_rate": error_rate,
            "cache_hit_rate": cache_hit_rate,
            "uptime_seconds": uptime
        }
    
    # MCP Integration Methods
    async def notify_agent_completion(self, agent_id: str, task_id: str, result: Dict[str, Any]) -> bool:
        """Notify agent when AI task is completed"""
        if not self.mcp_client or not self.mcp_client.is_connected:
            logger.debug("MCP client not available for agent notification")
            return False
        
        notification = {
            "type": "ai_task_completed",
            "task_id": task_id,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        return await self.mcp_client.notify_agent(agent_id, notification)
    
    async def notify_usage_threshold(self, threshold_type: str, current_usage: float, limit: float) -> bool:
        """Notify all agents about usage threshold being reached"""
        if not self.mcp_client or not self.mcp_client.is_connected:
            logger.debug("MCP client not available for usage notification")
            return False
        
        alert_details = {
            "threshold_type": threshold_type,
            "current_usage": current_usage,
            "limit": limit,
            "percentage": (current_usage / limit) * 100 if limit > 0 else 0
        }
        return await self.mcp_client.broadcast_usage_alert("threshold_reached", alert_details)
    
    async def notify_model_status_change(self, provider: str, model: str, available: bool, reason: str = "") -> bool:
        """Notify about model availability changes"""
        if not self.mcp_client or not self.mcp_client.is_connected:
            logger.debug("MCP client not available for model status notification")
            return False
        
        success = await self.mcp_client.update_model_availability(provider, model, available)
        if success:
            logger.info(f"Notified MCP about {provider}/{model} availability: {available} ({reason})")
        return success
    
    async def stream_response_to_agent(self, agent_id: str, task_id: str, partial_response: str) -> bool:
        """Stream partial responses back to requesting agent"""
        if not self.mcp_client or not self.mcp_client.is_connected:
            return False
        
        notification = {
            "type": "ai_streaming_response",
            "task_id": task_id,
            "partial_response": partial_response,
            "timestamp": datetime.utcnow().isoformat()
        }
        return await self.mcp_client.notify_agent(agent_id, notification)
    
    async def shutdown_mcp_client(self):
        """Clean shutdown of MCP client"""
        if self.mcp_client:
            await self.mcp_client.disconnect()
            logger.info("MCP client disconnected successfully")

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

# Graceful shutdown handler
async def shutdown_handler():
    """Handle graceful shutdown"""
    logger.info("Shutting down AI Service...")
    await ai_service.shutdown_mcp_client()
    logger.info("AI Service shutdown complete")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    asyncio.create_task(shutdown_handler())
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    SERVICE_HOST = os.getenv("SERVICE_HOST", config["service"]["host"])
    SERVICE_PORT = int(os.getenv("SERVICE_PORT", config["service"]["port"]))
    
    logger.info(f"Starting AI Service on {SERVICE_HOST}:{SERVICE_PORT}")
    logger.info(f"MCP Integration: {'Enabled' if config.get('mcp', {}).get('enabled', True) else 'Disabled'}")
    
    uvicorn.run(
        app,
        host=SERVICE_HOST,
        port=SERVICE_PORT,
        log_level="info"
    )
