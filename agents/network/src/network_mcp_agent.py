"""
Network Agent MCP Implementation

This module provides the MCP (Model Context Protocol) integration for the Network Agent,
enabling it to communicate with the MCP server and handle search-related tasks.

Architecture Compliance:
- Pure MCP JSON-RPC over WebSocket
- No HTTP/REST endpoints for business logic
- Task-based communication pattern
"""

import asyncio
import json
import logging
import uuid
import signal
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path
from abc import ABC, abstractmethod

import websockets
from .google_search_service import GoogleSearchService

logger = logging.getLogger(__name__)


class NetworkMCPAgent:
    """
    Network Agent MCP implementation.
    
    Handles:
    - WebSocket connection to MCP server
    - Search task processing
    - Result formatting and transmission
    - Error handling and recovery
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Network MCP agent."""
        self.agent_type = "network"
        self.agent_id = f"network-{uuid.uuid4().hex[:8]}"
        self.config = config
        
        # Connection configuration
        mcp_config = config.get("mcp", {})
        self.mcp_server_url = mcp_config.get("server_url", "ws://mcp-server:9000")
        self.reconnect_attempts = mcp_config.get("reconnect_attempts", 5)
        self.reconnect_delay = mcp_config.get("reconnect_delay", 5)
        self.ping_interval = mcp_config.get("ping_interval", 30)
        self.ping_timeout = mcp_config.get("ping_timeout", 10)
        
        # Connection state
        self.websocket = None
        self.connected = False
        self.running = False
        self.last_heartbeat = datetime.now(timezone.utc).isoformat()
        
        # Search service
        self.search_service = GoogleSearchService(config)
        
        # Task handlers
        self.task_handlers = {
            "google_search": self._handle_google_search,
            "web_search": self._handle_web_search,
            "multi_page_search": self._handle_multi_page_search,
            "search_capabilities": self._handle_search_capabilities
        }
        
        logger.info(f"Network MCP Agent {self.agent_id} initialized")
    
    def get_capabilities(self) -> List[str]:
        """Return list of agent capabilities."""
        return self.config.get("capabilities", [])
    
    async def start(self):
        """Start the Network MCP agent."""
        try:
            self.running = True
            
            # Start search service
            await self.search_service.start()
            
            # Connect to MCP server with retry logic
            await self._connect_with_retry()
            
            # Start heartbeat
            asyncio.create_task(self._heartbeat_loop())
            
            logger.info("🚀 Network MCP Agent started successfully")
            
            # Keep agent running with automatic reconnection
            try:
                while self.running:
                    if not self.connected:
                        logger.warning("Connection lost, attempting to reconnect...")
                        await self._connect_with_retry()
                    
                    await asyncio.sleep(1)
                    
            except KeyboardInterrupt:
                logger.info("Shutdown signal received")
            finally:
                await self.stop()
            
        except Exception as e:
            logger.error(f"Failed to start Network MCP Agent: {e}")
            raise
    
    async def stop(self):
        """Stop the Network MCP agent."""
        self.running = False
        
        if self.websocket:
            await self.websocket.close()
        
        await self.search_service.stop()
        
        logger.info("🛑 Network MCP Agent stopped")
    
    def is_connected(self) -> bool:
        """Check if agent is connected to MCP server."""
        return self.connected and self.websocket is not None
    
    def get_last_heartbeat(self) -> str:
        """Get last heartbeat timestamp."""
        return self.last_heartbeat
    
    async def _connect_with_retry(self):
        """Connect to MCP server with retry logic."""
        for attempt in range(self.reconnect_attempts):
            try:
                logger.info(f"Connecting to MCP server: {self.mcp_server_url} (attempt {attempt + 1})")
                
                self.websocket = await websockets.connect(
                    self.mcp_server_url,
                    ping_interval=self.ping_interval,
                    ping_timeout=self.ping_timeout
                )
                
                self.connected = True
                logger.info("✅ Connected to MCP server")
                
                # Register agent
                await self._register_agent()
                
                # Start message handling loop
                asyncio.create_task(self._message_loop())
                
                return
                
            except Exception as e:
                logger.error(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < self.reconnect_attempts - 1:
                    await asyncio.sleep(self.reconnect_delay)
                else:
                    raise Exception(f"Failed to connect after {self.reconnect_attempts} attempts")
    
    async def _register_agent(self):
        """Register agent with MCP server."""
        registration_message = {
            "type": "agent_register",
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": self.get_capabilities(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self._send_message(registration_message)
        logger.info(f"Agent registered: {self.agent_id} with capabilities: {self.get_capabilities()}")
    
    async def _message_loop(self):
        """Main message handling loop."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.connected = False
        except Exception as e:
            logger.error(f"Message loop error: {e}")
            self.connected = False
    
    async def _handle_message(self, data: Dict[str, Any]):
        """Handle incoming MCP message."""
        message_type = data.get("type")
        
        logger.debug(f"Received message: {message_type}")
        
        if message_type == "task_request":
            await self._handle_task_request(data)
        elif message_type == "task":
            await self._handle_task_request(data)
        elif message_type == "ping":
            await self._send_message({"type": "pong"})
        elif message_type == "registration_confirmed":
            logger.info("✅ Agent registration confirmed by MCP server")
        else:
            logger.warning(f"Unknown message type: {message_type}")
    
    async def _handle_task_request(self, data: Dict[str, Any]):
        """Handle incoming task request."""
        try:
            task_id = data.get("task_id")
            task_type = data.get("task_type") or data.get("action")
            task_data = data.get("data") or data.get("payload", {})
            
            logger.info(f"Processing task: {task_type} (ID: {task_id})")
            
            # Execute the task
            if task_type in self.task_handlers:
                result = await self.task_handlers[task_type](task_data)
                
                # Send result back to MCP server
                response = {
                    "type": "task_result",
                    "task_id": task_id,
                    "status": "completed",
                    "result": result
                }
                await self._send_message(response)
                
                logger.info(f"✅ Task completed: {task_type}")
                
            else:
                # Task type not supported
                error_response = {
                    "type": "task_result", 
                    "task_id": task_id,
                    "status": "error",
                    "error": f"Unsupported task type: {task_type}"
                }
                await self._send_message(error_response)
                logger.error(f"❌ Unsupported task type: {task_type}")
                
        except Exception as e:
            logger.error(f"Error processing task: {e}")
            
            task_id = data.get("task_id")
            if task_id:
                error_response = {
                    "type": "task_result",
                    "task_id": task_id, 
                    "status": "error",
                    "error": str(e)
                }
                await self._send_message(error_response)
    
    async def _send_message(self, message: Dict[str, Any]):
        """Send message to MCP server."""
        if self.websocket:
            try:
                await self.websocket.send(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
    
    async def _heartbeat_loop(self):
        """Heartbeat loop to maintain connection."""
        while self.running:
            try:
                if self.connected:
                    self.last_heartbeat = datetime.now(timezone.utc).isoformat()
                
                await asyncio.sleep(self.ping_interval)
                
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(5)
    
    # Task Handlers
    
    async def _handle_google_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Google search task."""
        query = params.get("query")
        if not query:
            raise ValueError("Search query is required")
        
        page = params.get("page", 1)
        max_results = params.get("max_results")
        
        logger.info(f"Performing Google search: '{query}'")
        
        search_response = await self.search_service.search(
            query=query,
            page=page,
            max_results=max_results
        )
        
        return search_response.to_dict()
    
    async def _handle_web_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general web search task (alias for Google search)."""
        return await self._handle_google_search(params)
    
    async def _handle_multi_page_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle multi-page search task."""
        query = params.get("query")
        if not query:
            raise ValueError("Search query is required")
        
        max_results = params.get("max_results", 50)
        
        logger.info(f"Performing multi-page search: '{query}' (max {max_results} results)")
        
        responses = await self.search_service.search_multiple_pages(
            query=query,
            max_results=max_results
        )
        
        return {
            "query": query,
            "total_pages": len(responses),
            "total_results": sum(len(r.results) for r in responses),
            "pages": [response.to_dict() for response in responses]
        }
    
    async def _handle_search_capabilities(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle search capabilities inquiry."""
        return {
            "agent_capabilities": self.get_capabilities(),
            "search_capabilities": self.search_service.get_capabilities(),
            "api_configured": self.search_service.is_api_configured(),
            "rate_limits": {
                "daily_limit": self.search_service.rate_limiter.max_requests_per_day,
                "minute_limit": self.search_service.rate_limiter.max_requests_per_minute,
                "daily_used": self.search_service.rate_limiter.daily_requests,
                "minute_used": len(self.search_service.rate_limiter.minute_requests)
            }
        }
