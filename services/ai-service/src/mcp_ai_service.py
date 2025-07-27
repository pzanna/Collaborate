#!/usr/bin/env python3
"""
AI Service - MCP Client Implementation
Pure MCP protocol-based AI service that connects to MCP Server as a client
and provides AI capabilities to other agents through the MCP protocol.
"""

import asyncio
import json
import logging
import os
import signal
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
import time

import websockets
import openai
import anthropic
import httpx
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ai_service_mcp_client")


class MCPAIService:
    """AI Service implemented as MCP Client"""
    
    def __init__(self):
        # MCP Client configuration  
        self.mcp_server_url = os.getenv('MCP_SERVER_URL', 'ws://mcp-server:9000')
        self.agent_id = f"ai-service-{uuid.uuid4().hex[:8]}"
        self.agent_type = "ai_service"
        
        # AI Provider configuration
        self.openai_client = None
        self.anthropic_client = None
        self.xai_client = None
        
        # Connection state
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        self.is_running = False
        
        # Request tracking
        self.pending_requests: Dict[str, asyncio.Future] = {}
        
        # Capabilities this service provides
        self.capabilities = [
            "ai_chat_completion",
            "ai_embedding",
            "ai_model_info",
            "ai_usage_stats"
        ]
        
        # Initialize AI clients
        self._init_ai_clients()
    
    def _init_ai_clients(self):
        """Initialize AI provider clients"""
        try:
            # OpenAI
            openai_key = os.getenv('OPENAI_API_KEY')
            if openai_key and self._validate_api_key(openai_key, "openai"):
                self.openai_client = openai.AsyncOpenAI(api_key=openai_key)
                logger.info("OpenAI client initialized")
            
            # Anthropic
            anthropic_key = os.getenv('ANTHROPIC_API_KEY') 
            if anthropic_key and self._validate_api_key(anthropic_key, "anthropic"):
                self.anthropic_client = anthropic.AsyncAnthropic(api_key=anthropic_key)
                logger.info("Anthropic client initialized")
            
            # XAI (using OpenAI-compatible API)
            xai_key = os.getenv('XAI_API_KEY')
            if xai_key and self._validate_api_key(xai_key, "xai"):
                self.xai_client = openai.AsyncOpenAI(
                    api_key=xai_key,
                    base_url="https://api.x.ai/v1"
                )
                logger.info("XAI client initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize AI clients: {e}")
    
    def _validate_api_key(self, api_key: str, provider: str) -> bool:
        """Validate API key format and content"""
        if not api_key or len(api_key) < 10:
            return False
        
        # Check for placeholder values
        placeholder_values = [
            "your_api_key_here", "insert_key_here", "api_key",
            "placeholder", "example", "test", "demo"
        ]
        
        if api_key.lower() in placeholder_values:
            return False
        
        # Provider-specific validation
        if provider == "openai" and not (api_key.startswith("sk-") and len(api_key) > 20):
            return False
        elif provider == "anthropic" and not (api_key.startswith("sk-ant-") and len(api_key) > 20):
            return False
        elif provider == "xai" and not (api_key.startswith("xai-") and len(api_key) > 10):
            return False
        
        return True
    
    async def start(self):
        """Start the MCP AI Service client"""
        logger.info(f"Starting AI Service MCP Client: {self.agent_id}")
        
        self.is_running = True
        
        while self.is_running:
            try:
                await self._connect_to_mcp_server()
                await self._run_client_loop()
            except Exception as e:
                logger.error(f"Connection error: {e}")
                if self.is_running:
                    logger.info("Reconnecting in 5 seconds...")
                    await asyncio.sleep(5)
    
    async def stop(self):
        """Stop the AI Service client"""
        logger.info("Stopping AI Service MCP Client")
        self.is_running = False
        
        if self.websocket:
            await self.websocket.close()
        
        # Cancel pending requests
        for future in self.pending_requests.values():
            if not future.done():
                future.cancel()
    
    async def _connect_to_mcp_server(self):
        """Connect to MCP Server and register as agent"""
        logger.info(f"Connecting to MCP Server: {self.mcp_server_url}")
        
        self.websocket = await websockets.connect(self.mcp_server_url)
        self.is_connected = True
        
        # Register with MCP Server
        registration_message = {
            "type": "agent_register",
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": self.capabilities,
            "timestamp": datetime.now().isoformat()
        }
        
        await self.websocket.send(json.dumps(registration_message))
        logger.info("Registration message sent to MCP Server")
    
    async def _run_client_loop(self):
        """Main client loop for handling MCP messages"""
        heartbeat_task = None
        try:
            # Start background tasks
            heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            # Message handling loop
            if self.websocket:
                async for message in self.websocket:
                    try:
                        data = json.loads(message)
                        await self._handle_mcp_message(data)
                    except json.JSONDecodeError:
                        logger.error("Received invalid JSON message")
                    except Exception as e:
                        logger.error(f"Error handling message: {e}")
            
        except websockets.exceptions.ConnectionClosed:
            logger.info("Connection to MCP Server closed")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Client loop error: {e}")
        finally:
            if heartbeat_task:
                heartbeat_task.cancel()
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeat to MCP Server"""
        while self.is_connected and self.is_running:
            try:
                heartbeat_message = {
                    "type": "heartbeat",
                    "agent_id": self.agent_id,
                    "timestamp": datetime.now().isoformat()
                }
                
                if self.websocket:
                    await self.websocket.send(json.dumps(heartbeat_message))
                
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
                
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                break
    
    async def _handle_mcp_message(self, data: Dict[str, Any]):
        """Handle incoming MCP message"""
        message_type = data.get("type")
        
        if message_type == "registration_confirmed":
            await self._handle_registration_confirmed(data)
        elif message_type == "heartbeat_ack":
            await self._handle_heartbeat_ack(data)
        elif message_type == "task_request":
            await self._handle_task_request(data)
        elif message_type == "ai_response":
            await self._handle_ai_response(data)
        else:
            logger.warning(f"Unknown message type: {message_type}")
    
    async def _handle_registration_confirmed(self, data: Dict[str, Any]):
        """Handle registration confirmation from MCP Server"""
        server_id = data.get("server_id")
        logger.info(f"Registration confirmed by MCP Server: {server_id}")
        
        # Send status update
        await self._send_status_update("active")
    
    async def _handle_heartbeat_ack(self, data: Dict[str, Any]):
        """Handle heartbeat acknowledgment"""
        # Optional: track heartbeat timing for connection health
        pass
    
    async def _handle_task_request(self, data: Dict[str, Any]):
        """Handle task request from MCP Server"""
        task_id = data.get("task_id")
        task_type = data.get("task_type")
        task_data = data.get("data", {})
        
        logger.info(f"Received task request: {task_id} ({task_type})")
        
        try:
            # Process task based on type
            if task_type == "ai_chat_completion":
                result = await self._handle_chat_completion(task_data)
            elif task_type == "ai_embedding":
                result = await self._handle_embedding(task_data)
            elif task_type == "ai_model_info":
                result = await self._handle_model_info(task_data)
            elif task_type == "ai_usage_stats":
                result = await self._handle_usage_stats(task_data)
            else:
                raise ValueError(f"Unknown task type: {task_type}")
            
            # Send result back to MCP Server
            result_message = {
                "type": "task_result",
                "task_id": task_id,
                "result": result,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            }
            
            if self.websocket:
                await self.websocket.send(json.dumps(result_message))
            logger.info(f"Task completed: {task_id}")
            
        except Exception as e:
            # Send error result
            error_message = {
                "type": "task_result",
                "task_id": task_id,
                "error": str(e),
                "status": "error",
                "timestamp": datetime.now().isoformat()
            }
            
            if self.websocket:
                await self.websocket.send(json.dumps(error_message))
            logger.error(f"Task failed: {task_id} - {e}")
    
    async def _handle_ai_response(self, data: Dict[str, Any]):
        """Handle AI response for requests we made"""
        request_id = data.get("request_id")
        
        if request_id in self.pending_requests:
            future = self.pending_requests.pop(request_id)
            if not future.done():
                if data.get("status") == "success":
                    future.set_result(data.get("result"))
                else:
                    future.set_exception(Exception(data.get("error", "Unknown error")))
    
    async def _send_status_update(self, status: str):
        """Send status update to MCP Server"""
        status_message = {
            "type": "agent_status",
            "agent_id": self.agent_id,
            "status": status,
            "metrics": {
                "openai_available": self.openai_client is not None,
                "anthropic_available": self.anthropic_client is not None,
                "xai_available": self.xai_client is not None,
                "uptime": time.time()
            },
            "timestamp": datetime.now().isoformat()
        }
        
        if self.websocket:
            await self.websocket.send(json.dumps(status_message))
    
    # AI Task Handlers
    
    async def _handle_chat_completion(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle chat completion request"""
        provider = task_data.get("provider", "openai")
        messages = task_data.get("messages", [])
        model = task_data.get("model")
        
        if provider == "openai" and self.openai_client:
            if not model:
                model = "gpt-4o-mini"
            
            response = await self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                **{k: v for k, v in task_data.items() 
                   if k not in ["provider", "messages", "model"]}
            )
            
            return {
                "id": response.id,
                "choices": [
                    {
                        "index": choice.index,
                        "message": {
                            "role": choice.message.role,
                            "content": choice.message.content
                        },
                        "finish_reason": choice.finish_reason
                    }
                    for choice in response.choices
                ],
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                "model": response.model,
                "provider": "openai"
            }
        
        elif provider == "anthropic" and self.anthropic_client:
            if not model:
                model = "claude-3-haiku-20240307"
            
            # Convert messages to Anthropic format
            system_prompt = None
            anthropic_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = msg["content"]
                else:
                    anthropic_messages.append(msg)
            
            kwargs = {
                "model": model,
                "max_tokens": task_data.get("max_tokens", 1000),
                "messages": anthropic_messages
            }
            
            if system_prompt:
                kwargs["system"] = system_prompt
            
            response = await self.anthropic_client.messages.create(**kwargs)
            
            # Get text content from response
            content = ""
            if response.content and len(response.content) > 0:
                first_block = response.content[0]
                if hasattr(first_block, 'text'):
                    content = first_block.text
                else:
                    content = str(first_block)
            
            return {
                "id": response.id,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": content
                        },
                        "finish_reason": response.stop_reason
                    }
                ],
                "usage": {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                },
                "model": response.model,
                "provider": "anthropic"
            }
        
        elif provider == "xai" and self.xai_client:
            if not model:
                model = "grok-beta"
            
            response = await self.xai_client.chat.completions.create(
                model=model,
                messages=messages,
                **{k: v for k, v in task_data.items() 
                   if k not in ["provider", "messages", "model"]}
            )
            
            return {
                "id": response.id,
                "choices": [
                    {
                        "index": choice.index,
                        "message": {
                            "role": choice.message.role,
                            "content": choice.message.content
                        },
                        "finish_reason": choice.finish_reason
                    }
                    for choice in response.choices
                ],
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                "model": response.model,
                "provider": "xai"
            }
        
        else:
            raise ValueError(f"Provider '{provider}' not available or not configured")
    
    async def _handle_embedding(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle embedding request"""
        provider = task_data.get("provider", "openai")
        text = task_data.get("text", "")
        model = task_data.get("model")
        
        if provider == "openai" and self.openai_client:
            if not model:
                model = "text-embedding-3-small"
            
            response = await self.openai_client.embeddings.create(
                model=model,
                input=text
            )
            
            return {
                "data": [
                    {
                        "embedding": embedding.embedding,
                        "index": embedding.index
                    }
                    for embedding in response.data
                ],
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                "provider": "openai"
            }
        
        else:
            raise ValueError(f"Embedding provider '{provider}' not available")
    
    async def _handle_model_info(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle model info request"""
        available_models = []
        
        if self.openai_client:
            available_models.extend([
                {"provider": "openai", "model": "gpt-4o", "type": "chat"},
                {"provider": "openai", "model": "gpt-4o-mini", "type": "chat"},
                {"provider": "openai", "model": "text-embedding-3-small", "type": "embedding"},
                {"provider": "openai", "model": "text-embedding-3-large", "type": "embedding"}
            ])
        
        if self.anthropic_client:
            available_models.extend([
                {"provider": "anthropic", "model": "claude-3-opus-20240229", "type": "chat"},
                {"provider": "anthropic", "model": "claude-3-sonnet-20240229", "type": "chat"},
                {"provider": "anthropic", "model": "claude-3-haiku-20240307", "type": "chat"}
            ])
        
        if self.xai_client:
            available_models.extend([
                {"provider": "xai", "model": "grok-beta", "type": "chat"}
            ])
        
        return {
            "available_models": available_models,
            "providers_configured": {
                "openai": self.openai_client is not None,
                "anthropic": self.anthropic_client is not None,
                "xai": self.xai_client is not None
            }
        }
    
    async def _handle_usage_stats(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle usage statistics request"""
        # This would integrate with usage tracking system
        return {
            "total_requests": 0,
            "requests_by_provider": {
                "openai": 0,
                "anthropic": 0,
                "xai": 0
            },
            "total_tokens": 0,
            "estimated_cost": 0.0
        }
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        if sys.platform != "win32":
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))


async def main():
    """Main entry point for AI Service MCP Client"""
    ai_service = MCPAIService()
    
    try:
        # Setup signal handlers
        ai_service._setup_signal_handlers()
        
        # Start the service
        await ai_service.start()
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await ai_service.stop()


if __name__ == "__main__":
    asyncio.run(main())
