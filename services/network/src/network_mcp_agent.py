"""
Updated Network Agent MCP Implementation v0.4.0

Enhancements:
- Supports Google Search, AI Model APIs, and Literature Database APIs
- Unified ExternalAPIService integration
- Extended task handlers for new API types
- Enhanced capability reporting
"""

import asyncio
import json
import logging
import uuid
import signal
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pathlib import Path
from abc import ABC

import websockets
from .base_mcp_agent import BaseMCPAgent
from .external_api_service import ExternalAPIService

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "service": "network-mcp-agent",
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno
        }
        return json.dumps(log_record)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)

class NetworkMCPAgent(BaseMCPAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__("network", config)
        self.api_service = ExternalAPIService(config)
        
        self.message_handlers["task_cancel_request"] = self._handle_task_cancel
        logger.info(f"Network MCP Agent {self.agent_id} initialized")
    
    def get_capabilities(self) -> List[str]:
        return self.api_service.get_capabilities()

    def setup_task_handlers(self) -> Dict[str, Any]:
        """Setup task handlers for network agent."""
        return {
            "google_search": self._handle_google_search,
            "web_search": self._handle_google_search,
            "multi_page_search": self._handle_multi_page_search,
            "search_capabilities": self._handle_search_capabilities,
            "ai_model_query": self._handle_ai_model_query,
            "literature_search": self._handle_literature_search
        }

    async def handle_task(self, task_type: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a specific task."""
        handler = self.task_handlers.get(task_type)
        if handler:
            return await handler(task_data)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _handle_google_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Handling Google search: {params.get('query')}")
        return await self.api_service.search("google_search", params)
    
    async def _handle_multi_page_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = params.get("query")
        if not query:
            raise ValueError("Search query is required")
        
        max_results = params.get("max_results", 50)
        logger.info(f"Performing multi-page Google search: '{query}' (max {max_results} results)")
        
        responses = await self.api_service.search("google_search", {
            "query": query,
            "max_results": max_results
        })
        
        # Ensure responses is a list
        if not isinstance(responses, list):
            responses = [responses] if responses else []
        
        # Calculate total results safely
        total_results = 0
        for r in responses:
            if isinstance(r, dict) and "results" in r:
                results = r.get("results", [])
                if isinstance(results, list):
                    total_results += len(results)
        
        return {
            "query": query,
            "total_pages": len(responses),
            "total_results": total_results,
            "pages": responses
        }
    
    async def _handle_ai_model_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        provider = params.get("provider", "openai")  # Default to OpenAI
        logger.info(f"Handling AI model query for {provider}: {params.get('prompt')}")
        return await self.api_service.search(f"ai_model_{provider}", params)
    
    async def _handle_literature_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        provider = params.get("provider", "pubmed")  # Default to PubMed
        logger.info(f"Handling literature search for {provider}: {params.get('query')}")
        return await self.api_service.search(f"literature_search_{provider}", params)
    
    async def _handle_search_capabilities(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "agent_capabilities": self.get_capabilities(),
            "api_configured": self.api_service.is_api_configured(),
            "rate_limits": {key: handler.rate_limiter.get_status() for key, handler in self.api_service.handlers.items()}
        }
    
    async def _handle_task_cancel(self, data: Dict[str, Any]):
        task_id = data.get("task_id")
        if task_id:
            logger.info(f"Received task cancellation for {task_id}")
            await self._send_jsonrpc_notification("task_result", {
                "task_id": task_id,
                "status": "cancelled",
                "agent_id": self.agent_id,
                "timestamp": datetime.now().isoformat()
            })
        else:
            await self._send_jsonrpc_notification("task_result", {
                "task_id": task_id or "unknown",
                "status": "error",
                "error": "Missing task_id in cancel request",
                "agent_id": self.agent_id,
                "timestamp": datetime.now().isoformat()
            })

if __name__ == "__main__":
    config_path = Path(__file__).parent.parent / "config" / "config.json"
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    agent = NetworkMCPAgent(config)
    asyncio.run(agent.start())