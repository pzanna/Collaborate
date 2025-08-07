"""
Google Search Service for Network Agent

This module provides Google Custom Search Engine integration for the Network Agent.
It handles search requests, result parsing, and rate limiting while maintaining
MCP protocol compliance.

Features:
- Google Custom Search API integration
- Search result normalization
- Rate limiting and error handling
- MCP protocol communication
- Async/await support
"""

import asyncio
import json
import logging
import os
import ssl
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode

import aiohttp
import requests
import certifi
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class SearchResult:
    """Represents a single search result."""
    
    def __init__(self, data: Dict[str, Any]):
        self.title = data.get("title", "")
        self.link = data.get("link", "")
        self.snippet = data.get("snippet", "")
        self.html_snippet = data.get("htmlSnippet", "")
        self.display_link = data.get("displayLink", "")
        self.formatted_url = data.get("formattedUrl", "")
        
        # Extract meta description if available
        self.meta_description = ""
        if "pagemap" in data and "metatags" in data["pagemap"]:
            metatags = data["pagemap"]["metatags"]
            if isinstance(metatags, list) and len(metatags) > 0:
                self.meta_description = metatags[0].get("og:description", "")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert search result to dictionary."""
        return {
            "title": self.title,
            "link": self.link,
            "snippet": self.snippet,
            "html_snippet": self.html_snippet,
            "display_link": self.display_link,
            "formatted_url": self.formatted_url,
            "meta_description": self.meta_description
        }


class SearchResponse:
    """Represents a complete search response."""
    
    def __init__(self, data: Dict[str, Any], query: str, page: int = 1):
        self.query = query
        self.page = page
        self.total_results = 0
        self.search_time = 0.0
        self.results: List[SearchResult] = []
        
        # Parse search information
        if "searchInformation" in data:
            search_info = data["searchInformation"]
            self.total_results = int(search_info.get("totalResults", 0))
            self.search_time = float(search_info.get("searchTime", 0.0))
        
        # Parse search results
        if "items" in data:
            self.results = [SearchResult(item) for item in data["items"]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert search response to dictionary."""
        return {
            "query": self.query,
            "page": self.page,
            "total_results": self.total_results,
            "search_time": self.search_time,
            "results_count": len(self.results),
            "results": [result.to_dict() for result in self.results]
        }


class RateLimiter:
    """Simple rate limiter for API requests."""
    
    def __init__(self, max_requests_per_day: int = 100, max_requests_per_minute: int = 10):
        self.max_requests_per_day = max_requests_per_day
        self.max_requests_per_minute = max_requests_per_minute
        
        # Track requests
        self.daily_requests = 0
        self.daily_reset_time = datetime.now(timezone.utc) + timedelta(days=1)
        self.minute_requests = []
    
    def can_make_request(self) -> bool:
        """Check if a request can be made without exceeding rate limits."""
        now = datetime.now(timezone.utc)
        
        # Reset daily counter if needed
        if now >= self.daily_reset_time:
            self.daily_requests = 0
            self.daily_reset_time = now + timedelta(days=1)
        
        # Clean up minute requests older than 1 minute
        cutoff_time = now - timedelta(minutes=1)
        self.minute_requests = [req_time for req_time in self.minute_requests if req_time > cutoff_time]
        
        # Check limits
        if self.daily_requests >= self.max_requests_per_day:
            logger.warning(f"Daily rate limit exceeded: {self.daily_requests}/{self.max_requests_per_day}")
            return False
        
        if len(self.minute_requests) >= self.max_requests_per_minute:
            logger.warning(f"Per-minute rate limit exceeded: {len(self.minute_requests)}/{self.max_requests_per_minute}")
            return False
        
        return True
    
    def record_request(self):
        """Record a successful request."""
        now = datetime.now(timezone.utc)
        self.daily_requests += 1
        self.minute_requests.append(now)


class GoogleSearchService:
    """Google Custom Search Engine service."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Google Search Service."""
        self.config = config
        self.google_config = config.get("google_search", {})
        
        # API configuration
        self.api_endpoint = self.google_config.get("api_endpoint", "https://www.googleapis.com/customsearch/v1")
        self.api_key = self.google_config.get("api_key", "")
        self.search_engine_id = self.google_config.get("search_engine_id", "")
        self.timeout = self.google_config.get("timeout", 30)
        
        # Search configuration
        self.default_page_size = self.google_config.get("default_page_size", 10)
        self.max_results = self.google_config.get("max_results", 100)
        
        # Rate limiting
        rate_limit_config = self.google_config.get("rate_limit", {})
        self.rate_limiter = RateLimiter(
            max_requests_per_day=rate_limit_config.get("max_requests_per_day", 100),
            max_requests_per_minute=rate_limit_config.get("max_requests_per_minute", 10)
        )
        
        # Connection state
        self.connected = False
        self.last_heartbeat = datetime.now(timezone.utc).isoformat()
        
        # Environment variable fallbacks (prefer environment over config)
        self.api_key = os.getenv("GOOGLE_API_KEY", self.api_key)
        self.search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID", self.search_engine_id)
        
        # Load from local .env file if still empty
        if not self.api_key or not self.search_engine_id:
            self._load_env_file()
        
        logger.info(f"Google Search Service initialized")
        logger.info(f"API configured: {self.is_api_configured()}")
    
    def _load_env_file(self):
        """Load environment variables from .env file."""
        try:
            # Look for .env file in the parent directory (agents/network/.env)
            env_paths = [
                Path(__file__).parent.parent / ".env",  # agents/network/.env
                Path(__file__).parent.parent.parent.parent / ".env",  # root .env
            ]
            
            for env_path in env_paths:
                if env_path.exists():
                    logger.debug(f"Loading environment from: {env_path}")
                    with open(env_path) as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key, value = line.split('=', 1)
                                key = key.strip()
                                value = value.strip()
                                
                                # Only set if not already set and relevant to Google Search
                                if key in ["GOOGLE_API_KEY", "GOOGLE_SEARCH_ENGINE_ID"]:
                                    if not os.getenv(key) and value:
                                        os.environ[key] = value
                                        if key == "GOOGLE_API_KEY" and not self.api_key:
                                            self.api_key = value
                                        elif key == "GOOGLE_SEARCH_ENGINE_ID" and not self.search_engine_id:
                                            self.search_engine_id = value
                    break
        except Exception as e:
            logger.debug(f"Could not load .env file: {e}")
    
    def is_api_configured(self) -> bool:
        """Check if API credentials are properly configured."""
        return bool(self.api_key and self.search_engine_id)
    
    def get_capabilities(self) -> List[str]:
        """Get list of search capabilities."""
        capabilities = [
            "web_search",
            "result_parsing",
            "rate_limiting"
        ]
        
        if self.is_api_configured():
            capabilities.append("google_custom_search")
        
        return capabilities
    
    def is_connected(self) -> bool:
        """Check if service is connected and ready."""
        return self.connected and self.is_api_configured()
    
    def get_last_heartbeat(self) -> str:
        """Get last heartbeat timestamp."""
        return self.last_heartbeat
    
    async def start(self):
        """Start the Google Search Service."""
        try:
            # Validate configuration
            if not self.is_api_configured():
                logger.warning("Google Search API not fully configured - some features may be limited")
                logger.warning("Please set GOOGLE_API_KEY and GOOGLE_SEARCH_ENGINE_ID environment variables")
            
            # Test API connection if configured
            if self.is_api_configured():
                await self._test_api_connection()
            
            self.connected = True
            self.last_heartbeat = datetime.now(timezone.utc).isoformat()
            logger.info("Google Search Service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Google Search Service: {e}")
            raise
    
    async def stop(self):
        """Stop the Google Search Service."""
        self.connected = False
        logger.info("Google Search Service stopped")
    
    async def _test_api_connection(self):
        """Test API connection with a simple query."""
        try:
            logger.info("Testing Google Custom Search API connection...")
            result = await self.search("test", max_results=1)
            logger.info("✅ Google Custom Search API connection successful")
        except Exception as e:
            logger.warning(f"⚠️ Google Custom Search API test failed: {e}")
            # Don't raise - service can still run without API
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def search(
        self, 
        query: str, 
        page: int = 1, 
        max_results: Optional[int] = None,
        **kwargs
    ) -> SearchResponse:
        """
        Perform a Google Custom Search.
        
        Args:
            query: Search query string
            page: Page number (1-based)
            max_results: Maximum number of results to return
            **kwargs: Additional search parameters
            
        Returns:
            SearchResponse object containing results
            
        Raises:
            ValueError: If API is not configured or rate limits exceeded
            Exception: If search fails
        """
        if not self.is_api_configured():
            raise ValueError("Google Search API not configured - missing API key or search engine ID")
        
        if not self.rate_limiter.can_make_request():
            raise ValueError("Rate limit exceeded - please try again later")
        
        # Calculate start index for pagination
        page_size = self.default_page_size
        start_index = (page - 1) * page_size + 1
        
        # Limit results if specified
        if max_results:
            page_size = min(page_size, max_results)
        
        # Build request parameters
        params = {
            "key": self.api_key,
            "cx": self.search_engine_id,
            "q": query,
            "start": start_index,
            "num": page_size
        }
        
        # Add additional parameters
        params.update(kwargs)
        
        try:
            logger.info(f"Performing Google search: '{query}' (page {page})")
            
            # Create SSL context that works on macOS
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            
            # Make API request
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                connector=connector
            ) as session:
                async with session.get(self.api_endpoint, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()
            
            # Record successful request
            self.rate_limiter.record_request()
            self.last_heartbeat = datetime.now(timezone.utc).isoformat()
            
            # Parse and return results
            search_response = SearchResponse(data, query, page)
            
            logger.info(f"Search completed: {len(search_response.results)} results found")
            logger.info(f"Total results available: {search_response.total_results}")
            
            return search_response
            
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error during search: {e}")
            raise Exception(f"Search request failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during search: {e}")
            raise
    
    async def search_multiple_pages(
        self, 
        query: str, 
        max_results: int = 50,
        **kwargs
    ) -> List[SearchResponse]:
        """
        Perform a multi-page Google search.
        
        Args:
            query: Search query string
            max_results: Maximum total results to retrieve
            **kwargs: Additional search parameters
            
        Returns:
            List of SearchResponse objects
        """
        if not self.is_api_configured():
            raise ValueError("Google Search API not configured")
        
        # Calculate number of pages needed
        page_size = self.default_page_size
        num_pages = min((max_results + page_size - 1) // page_size, 10)  # Google CSE max 100 results
        
        responses = []
        
        for page in range(1, num_pages + 1):
            try:
                response = await self.search(query, page=page, **kwargs)
                responses.append(response)
                
                # Stop if we have enough results or no more results available
                if len(response.results) < page_size:
                    break
                    
            except Exception as e:
                logger.error(f"Failed to fetch page {page}: {e}")
                break
        
        logger.info(f"Multi-page search completed: {len(responses)} pages, "
                   f"{sum(len(r.results) for r in responses)} total results")
        
        return responses
    
    def search_sync(self, query: str, page: int = 1, **kwargs) -> SearchResponse:
        """
        Synchronous version of search method.
        
        Args:
            query: Search query string
            page: Page number (1-based)
            **kwargs: Additional search parameters
            
        Returns:
            SearchResponse object containing results
        """
        if not self.is_api_configured():
            raise ValueError("Google Search API not configured")
        
        if not self.rate_limiter.can_make_request():
            raise ValueError("Rate limit exceeded")
        
        # Calculate start index
        page_size = self.default_page_size
        start_index = (page - 1) * page_size + 1
        
        # Build request parameters
        params = {
            "key": self.api_key,
            "cx": self.search_engine_id,
            "q": query,
            "start": start_index,
            "num": page_size
        }
        params.update(kwargs)
        
        try:
            logger.info(f"Performing Google search (sync): '{query}' (page {page})")
            
            response = requests.get(self.api_endpoint, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            # Record successful request
            self.rate_limiter.record_request()
            self.last_heartbeat = datetime.now(timezone.utc).isoformat()
            
            # Parse and return results
            search_response = SearchResponse(data, query, page)
            
            logger.info(f"Search completed: {len(search_response.results)} results found")
            
            return search_response
            
        except requests.RequestException as e:
            logger.error(f"HTTP error during search: {e}")
            raise Exception(f"Search request failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during search: {e}")
            raise
