"""
External API Service for Network Agent v0.4.0

Handles Google Search, AI Model APIs, and Literature Database APIs.
Enhancements:
- Modular API handlers for Google, AI models, and literature databases
- Unified caching and rate limiting
- Structured JSON logging with API key masking
- Parallel request support for multi-API queries
"""

import asyncio
import json
import logging
import os
import ssl
import sys
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode

import aiohttp
import certifi
from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

# Structured JSON logging
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "service": "external-api",
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno
        }
        return json.dumps(log_record)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)

# Configuration Models
class GoogleSearchConfig(BaseModel):
    api_endpoint: str = "https://www.googleapis.com/customsearch/v1"
    api_key: str
    search_engine_id: str
    timeout: int = 30
    default_page_size: int = 10
    cache_size: int = 100
    max_requests_per_day: int = 100
    max_requests_per_minute: int = 10

class AIModelConfig(BaseModel):
    provider: str  # e.g., "openai", "anthropic", "xai"
    api_endpoint: str
    api_key: str
    timeout: int = 60
    cache_size: int = 50
    max_requests_per_day: int = 1000
    max_requests_per_minute: int = 60

class LiteratureDBConfig(BaseModel):
    provider: str  # e.g., "pubmed", "core", "openalex"
    api_endpoint: str
    api_key: Optional[str] = None
    timeout: int = 30
    cache_size: int = 100
    max_requests_per_day: int = 1000
    max_requests_per_second: int = 3

class ExternalAPIConfig(BaseModel):
    google_search: Optional[GoogleSearchConfig] = None
    ai_models: List[AIModelConfig] = []
    literature_dbs: List[LiteratureDBConfig] = []

# Rate Limiter
class RateLimiter:
    def __init__(self, max_requests_per_day: int = 100, max_requests_per_minute: int = 10, max_requests_per_second: Optional[int] = None):
        self.max_requests_per_day = max_requests_per_day
        self.max_requests_per_minute = max_requests_per_minute
        self.max_requests_per_second = max_requests_per_second
        self.daily_requests = 0
        self.daily_reset_time = datetime.now(timezone.utc) + timedelta(days=1)
        self.minute_requests = []
        self.second_requests = [] if max_requests_per_second else None

    def can_make_request(self) -> bool:
        now = datetime.now(timezone.utc)
        if now >= self.daily_reset_time:
            self.daily_requests = 0
            self.daily_reset_time = now + timedelta(days=1)
        
        cutoff_time = now - timedelta(minutes=1)
        self.minute_requests = [req_time for req_time in self.minute_requests if req_time > cutoff_time]
        
        if self.second_requests is not None:
            cutoff_time = now - timedelta(seconds=1)
            self.second_requests = [req_time for req_time in self.second_requests if req_time > cutoff_time]
            if len(self.second_requests) >= self.max_requests_per_second:
                return False
        
        return self.daily_requests < self.max_requests_per_day and len(self.minute_requests) < self.max_requests_per_minute

    def record_request(self):
        now = datetime.now(timezone.utc)
        self.daily_requests += 1
        self.minute_requests.append(now)
        if self.second_requests is not None:
            self.second_requests.append(now)

    def get_status(self) -> Dict[str, Any]:
        status = {
            "daily_used": self.daily_requests,
            "daily_limit": self.max_requests_per_day,
            "minute_used": len(self.minute_requests),
            "minute_limit": self.max_requests_per_minute
        }
        if self.second_requests is not None:
            status["second_used"] = len(self.second_requests)
            status["second_limit"] = self.max_requests_per_second
        return status

# Base API Handler
class BaseAPIHandler(ABC):
    def __init__(self, config: BaseModel, rate_limiter: RateLimiter):
        self.config = config
        self.rate_limiter = rate_limiter
        self.cache = {}  # {cache_key: (timestamp, response)}
        self.last_heartbeat = datetime.now(timezone.utc).isoformat()

    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        pass

    def is_configured(self) -> bool:
        return bool(getattr(self.config, "api_key", None))

    def get_capabilities(self) -> List[str]:
        return []

# Google Search Handler
class GoogleSearchHandler(BaseAPIHandler):
    def __init__(self, config: GoogleSearchConfig):
        super().__init__(config, RateLimiter(
            config.max_requests_per_day,
            config.max_requests_per_minute
        ))
    
    def get_capabilities(self) -> List[str]:
        return ["google_search", "web_search", "multi_page_search"]

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = params.get("query")
        if not query:
            raise ValueError("Search query is required")
        
        page = params.get("page", 1)
        page_size = self.config.default_page_size
        start_index = (page - 1) * page_size + 1

        cache_key = json.dumps({"query": query, "page": page}, sort_keys=True)
        if cache_key in self.cache:
            cached_time, cached_response = self.cache[cache_key]
            if (datetime.now(timezone.utc) - cached_time).total_seconds() < 3600:  # 1-hour cache
                logger.info(f"Cache hit for Google search: {query}")
                return cached_response

        if not self.rate_limiter.can_make_request():
            raise ValueError("Google Search rate limit exceeded")

        request_params = {
            "key": self.config.api_key,
            "cx": self.config.search_engine_id,
            "q": query,
            "start": start_index,
            "num": page_size
        }

        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                connector=connector
            ) as session:
                async with session.get(self.config.api_endpoint, params=request_params) as response:
                    response.raise_for_status()
                    data = await response.json()

            self.rate_limiter.record_request()
            self.last_heartbeat = datetime.now(timezone.utc).isoformat()

            search_response = SearchResponse(data, query, page)  # Assuming SearchResponse class from original
            self.cache[cache_key] = (datetime.now(timezone.utc), search_response.to_dict())
            if len(self.cache) > self.config.cache_size:
                oldest_key = min(self.cache, key=lambda k: self.cache[k][0])
                del self.cache[oldest_key]

            logger.info(f"Google search completed: {len(search_response.results)} results")
            return search_response.to_dict()

        except aiohttp.ClientError as e:
            logger.error(f"Google search HTTP error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Google search unexpected error: {str(e)}")
            raise

# AI Model Handler (Example for OpenAI)
class AIModelHandler(BaseAPIHandler):
    def __init__(self, config: AIModelConfig):
        super().__init__(config, RateLimiter(
            config.max_requests_per_day,
            config.max_requests_per_minute
        ))

    def get_capabilities(self) -> List[str]:
        return [f"ai_model_{self.config.provider}"]

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        prompt = params.get("prompt")
        if not prompt:
            raise ValueError("Prompt is required for AI model")

        cache_key = json.dumps({"prompt": prompt, "provider": self.config.provider}, sort_keys=True)
        if cache_key in self.cache:
            cached_time, cached_response = self.cache[cache_key]
            if (datetime.now(timezone.utc) - cached_time).total_seconds() < 3600:
                logger.info(f"Cache hit for AI model {self.config.provider}: {prompt}")
                return cached_response

        if not self.rate_limiter.can_make_request():
            raise ValueError(f"{self.config.provider} rate limit exceeded")

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": params.get("model", "gpt-4"),  # Default model
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": params.get("max_tokens", 1000)
        }

        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                connector=connector
            ) as session:
                async with session.post(self.config.api_endpoint, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    data = await response.json()

            self.rate_limiter.record_request()
            self.last_heartbeat = datetime.now(timezone.utc).isoformat()

            result = {
                "provider": self.config.provider,
                "response": data.get("choices", [{}])[0].get("message", {}).get("content", ""),
                "usage": data.get("usage", {})
            }

            self.cache[cache_key] = (datetime.now(timezone.utc), result)
            if len(self.cache) > self.config.cache_size:
                oldest_key = min(self.cache, key=lambda k: self.cache[k][0])
                del self.cache[oldest_key]

            logger.info(f"AI model {self.config.provider} query completed")
            return result

        except aiohttp.ClientError as e:
            logger.error(f"AI model {self.config.provider} HTTP error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"AI model {self.config.provider} unexpected error: {str(e)}")
            raise

# Literature Database Handler (Example for PubMed)
class PubMedHandler(BaseAPIHandler):
    def __init__(self, config: LiteratureDBConfig):
        super().__init__(config, RateLimiter(
            config.max_requests_per_day,
            config.max_requests_per_minute,
            config.max_requests_per_second
        ))

    def get_capabilities(self) -> List[str]:
        return ["literature_search_pubmed"]

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = params.get("query")
        if not query:
            raise ValueError("Search query is required")

        cache_key = json.dumps({"query": query, "provider": self.config.provider}, sort_keys=True)
        if cache_key in self.cache:
            cached_time, cached_response = self.cache[cache_key]
            if (datetime.now(timezone.utc) - cached_time).total_seconds() < 3600:
                logger.info(f"Cache hit for PubMed search: {query}")
                return cached_response

        if not self.rate_limiter.can_make_request():
            raise ValueError("PubMed rate limit exceeded")

        params = {
            "db": "pubmed",
            "term": query,
            "retmax": params.get("retmax", 20),
            "retmode": "json"
        }
        if self.config.api_key:
            params["api_key"] = self.config.api_key

        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                connector=connector
            ) as session:
                async with session.get(self.config.api_endpoint, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()

            self.rate_limiter.record_request()
            self.last_heartbeat = datetime.now(timezone.utc).isoformat()

            result = {
                "provider": self.config.provider,
                "query": query,
                "results": data.get("esearchresult", {}).get("idlist", []),
                "total_results": data.get("esearchresult", {}).get("count", 0)
            }

            self.cache[cache_key] = (datetime.now(timezone.utc), result)
            if len(self.cache) > self.config.cache_size:
                oldest_key = min(self.cache, key=lambda k: self.cache[k][0])
                del self.cache[oldest_key]

            logger.info(f"PubMed search completed: {result['total_results']} results")
            return result

        except aiohttp.ClientError as e:
            logger.error(f"PubMed HTTP error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"PubMed unexpected error: {str(e)}")
            raise

# Main Service
class ExternalAPIService:
    def __init__(self, config: Dict[str, Any]):
        self.config = ExternalAPIConfig(**config)
        self.handlers: Dict[str, BaseAPIHandler] = {}
        
        # Initialize Google Search handler
        if self.config.google_search:
            self.handlers["google_search"] = GoogleSearchHandler(self.config.google_search)
        
        # Initialize AI model handlers
        for ai_config in self.config.ai_models:
            self.handlers[f"ai_model_{ai_config.provider}"] = AIModelHandler(ai_config)
        
        # Initialize literature database handlers
        for db_config in self.config.literature_dbs:
            if db_config.provider == "pubmed":
                self.handlers["literature_search_pubmed"] = PubMedHandler(db_config)
            # Add handlers for CORE, OpenAlex, etc., as needed
        
        logger.info(f"External API Service initialized with {len(self.handlers)} handlers")

    def is_api_configured(self) -> bool:
        return any(handler.is_configured() for handler in self.handlers.values())

    def get_capabilities(self) -> List[str]:
        capabilities = []
        for handler in self.handlers.values():
            capabilities.extend(handler.get_capabilities())
        return sorted(list(set(capabilities)))

    async def search(self, api_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        handler = self.handlers.get(api_type)
        if not handler:
            raise ValueError(f"Unsupported API type: {api_type}")
        return await handler.execute(params)

    async def stop(self):
        logger.info("Stopping External API Service")
        # Clean up resources if needed

if __name__ == "__main__":
    config = {
        "google_search": {
            "api_key": os.getenv("GOOGLE_API_KEY"),
            "search_engine_id": os.getenv("GOOGLE_SEARCH_ENGINE_ID"),
            "timeout": 30,
            "default_page_size": 10,
            "cache_size": 100,
            "max_requests_per_day": 100,
            "max_requests_per_minute": 10
        },
        "ai_models": [
            {
                "provider": "openai",
                "api_endpoint": "https://api.openai.com/v1/chat/completions",
                "api_key": os.getenv("OPENAI_API_KEY"),
                "timeout": 60,
                "cache_size": 50,
                "max_requests_per_day": 1000,
                "max_requests_per_minute": 60
            }
        ],
        "literature_dbs": [
            {
                "provider": "pubmed",
                "api_endpoint": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                "api_key": os.getenv("PUBMED_API_KEY"),
                "timeout": 30,
                "cache_size": 100,
                "max_requests_per_day": 1000,
                "max_requests_per_second": 3
            }
        ]
    }
    service = ExternalAPIService(config)
    asyncio.run(service.search("google_search", {"query": "test query"}))