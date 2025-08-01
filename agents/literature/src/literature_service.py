"""
Literature Search Agent Service for Eunice Research Platform.

This module provides a containerized Literature Search Agent that specializes in:
- Academic literature discovery and collection
- Multi-source bibliographic search (PubMed, arXiv, Semantic Scholar)
- Result normalization and deduplication
- Integration with MCP protocol for task coordination

ARCHITECTURE COMPLIANCE:
- ONLY exposes health check API endpoint (/health)
- ALL business operations via MCP protocol exclusively
- NO direct HTTP/REST endpoints for business logic
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import ssl
import sys
import uuid
import xml.etree.ElementTree as ET
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote

import aiohttp
import uvicorn
import websockets
from fastapi import FastAPI

# Import the standardized health check service
sys.path.append(str(Path(__file__).parent.parent))
from health_check_service import create_health_check_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# No AI client imports needed - AI functionality delegated to AI agent via MCP


@dataclass
class SearchQuery:
    """Search query data model for literature search requests."""
    lit_review_id: str
    research_plan: str = ""
    query: str = ""
    filters: Dict[str, Any] = field(default_factory=dict)
    sources: List[str] = field(default_factory=list)
    max_results: int = 100
    search_depth: str = "standard"


@dataclass
class SearchReport:
    """Search report data model for literature search results."""
    lit_review_id: str
    total_fetched: int
    total_unique: int
    per_source_counts: Dict[str, int]
    start_time: datetime
    end_time: datetime
    errors: List[str] = field(default_factory=list)
    records: List[Dict[str, Any]] = field(default_factory=list)


class LiteratureSearchService:
    """
    Literature Search Service for discovering and collecting bibliographic records.
    
    Handles academic literature search across multiple sources, normalization,
    deduplication, and integration with MCP protocol.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Literature Search Service."""
        self.config = config
        self.agent_id = "literature_search"
        self.agent_type = "literature"
        
        # Service configuration
        self.service_host = config.get("service_host", "0.0.0.0")
        self.service_port = config.get("service_port", 8003)
        self.mcp_server_url = config.get("mcp_server_url", "ws://mcp-server:9000")
        
        # Search configuration
        self.max_concurrent_searches = config.get("max_concurrent_searches", 3)
        self.search_timeout = config.get("search_timeout", 300)
        self.rate_limit_delay = config.get("rate_limit_delay", 1.0)
        
        # MCP connection
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.mcp_connected = False
        
        # HTTP session for API calls
        self.session: Optional[aiohttp.ClientSession] = None
        
        # AI clients for search term extraction - delegated to AI agent via MCP
        self.ai_agent_available = False
        
        # Task processing queue
        self.task_queue = asyncio.Queue()
        
        # Response tracking for AI agent communications
        self.pending_responses: Dict[str, asyncio.Future] = {}
        
        # API endpoints and configurations
        self.api_configs = {
            'semantic_scholar': {
                'base_url': 'https://api.semanticscholar.org/graph/v1/paper/search',
                'rate_limit': 1.0,  # seconds between requests
                'max_results_per_request': 100
            },
            'pubmed': {
                'base_url': 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils',
                'rate_limit': 0.34,  # NCBI rate limit (3 requests per second)
                'max_results_per_request': 100
            },
            'arxiv': {
                'base_url': 'http://export.arxiv.org/api/query',
                'rate_limit': 3.0,  # arXiv rate limit recommendation
                'max_results_per_request': 100
            },
            'crossref': {
                'base_url': 'https://api.crossref.org/works',
                'rate_limit': 1.0,  # CrossRef rate limit
                'max_results_per_request': 100
            }
        }
        
        logger.info(f"Literature Search Service initialized on port {self.service_port}")
    
    async def start(self):
        """Start the Literature Search Service."""
        try:
            # Initialize HTTP session with SSL context for development
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={'User-Agent': 'Eunice-Research-Platform/1.0'},
                connector=connector
            )
            
            # Connect to MCP server
            await self._connect_to_mcp_server()
            
            # Check if AI agent is available for search optimization
            await self._check_ai_agent_availability()
            
            # Start task processing
            asyncio.create_task(self._process_task_queue())
            
            logger.info("Literature Search Service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Literature Search Service: {e}")
            raise
    
    async def stop(self):
        """Stop the Literature Search Service."""
        try:
            # Close HTTP session
            if self.session:
                await self.session.close()
            
            # Close MCP connection
            if self.websocket:
                await self.websocket.close()
            
            logger.info("Literature Search Service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping Literature Search Service: {e}")
    
    async def _connect_to_mcp_server(self):
        """Connect to MCP server."""
        max_retries = 10
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Connecting to MCP server at {self.mcp_server_url} (attempt {attempt + 1})")
                
                self.websocket = await websockets.connect(
                    self.mcp_server_url,
                    ping_interval=30,
                    ping_timeout=10
                )
                
                # Register with MCP server
                await self._register_with_mcp_server()
                
                # Start message handler
                asyncio.create_task(self._handle_mcp_messages())
                
                self.mcp_connected = True
                logger.info("Successfully connected to MCP server")
                return
                
            except Exception as e:
                logger.warning(f"Failed to connect to MCP server (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("Failed to connect to MCP server after all retries")
                    raise
    
    async def _register_with_mcp_server(self):
        """Register this agent with the MCP server."""
        if not self.websocket:
            logger.error("WebSocket connection not established")
            return
            
        capabilities = [
            "search_academic_papers",
            "search_literature",
            "normalize_records",
            "deduplicate_results",
            "multi_source_search",
            "bibliographic_search"
        ]
        
        registration_message = {
            "type": "agent_register",
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": capabilities,
            "timestamp": datetime.now().isoformat()
        }
        
        await self.websocket.send(json.dumps(registration_message))
        logger.info(f"Registered with MCP server: {len(capabilities)} capabilities")
    
    async def _handle_mcp_messages(self):
        """Handle incoming MCP messages."""
        try:
            while self.websocket:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                # Handle task result responses for pending AI requests
                if data.get("type") == "task_result":
                    task_id = data.get("task_id")
                    if task_id in self.pending_responses:
                        future = self.pending_responses.pop(task_id)
                        if not future.done():
                            future.set_result(data)
                    continue
                
                if data.get("type") == "task_request":
                    await self.task_queue.put(data)
                elif data.get("type") == "task":
                    await self.task_queue.put(data)
                elif data.get("type") == "ping":
                    await self.websocket.send(json.dumps({"type": "pong"}))
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("MCP server connection closed")
            self.mcp_connected = False
        except Exception as e:
            logger.error(f"Error handling MCP messages: {e}")
            self.mcp_connected = False
    
    async def _process_task_queue(self):
        """Process tasks from the MCP queue."""
        while True:
            try:
                # Get task from queue
                task_data = await self.task_queue.get()
                
                # Process the task
                result = await self._process_literature_task(task_data)
                
                # Send result back to MCP server
                if self.websocket and self.mcp_connected:
                    response = {
                        "type": "task_result",
                        "task_id": task_data.get("task_id"),
                        "agent_id": self.agent_id,
                        "result": result
                    }
                    await self.websocket.send(json.dumps(response))
                
                # Mark task as done
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing task: {e}")
                await asyncio.sleep(1)
    
    async def _process_literature_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a literature search task."""
        try:
            # Handle both task and task_request formats
            if task_data.get("type") == "task_request":
                action = task_data.get("task_type", "")
                payload = task_data.get("data", {})
            else:
                action = task_data.get("action", "")
                payload = task_data.get("payload", {})
            
            # Route to appropriate handler
            if action == "search_academic_papers":
                return await self._handle_search_academic_papers(payload)
            elif action == "search_literature":
                return await self._handle_search_literature(payload)
            elif action == "normalize_records":
                return await self._handle_normalize_records(payload)
            else:
                return {
                    "status": "failed",
                    "error": f"Unknown action: {action}",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error processing literature task: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_search_academic_papers(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle academic paper search request."""
        try:
            research_plan = payload.get("research_plan", "")
            max_results = payload.get("max_results", 10)
            search_depth = payload.get("search_depth", "standard")
            sources = payload.get("sources", ["semantic_scholar", "arxiv", "crossref"])

            if not research_plan:
                return {
                    "status": "failed",
                    "error": "Research plan is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Create search query
            search_query = SearchQuery(
                lit_review_id=str(uuid.uuid4()),
                research_plan=research_plan,
                max_results=max_results,
                sources=sources,
                search_depth=search_depth
            )
            
            # Execute search
            search_report = await self.search_literature(search_query)
            
            return {
                "status": "completed",
                "results": search_report.records,
                "summary": {
                    "total_found": search_report.total_fetched,
                    "total_unique": search_report.total_unique,
                    "sources": search_report.per_source_counts,
                    "search_duration": (search_report.end_time - search_report.start_time).total_seconds()
                },
                "errors": search_report.errors,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to handle search academic papers: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_search_literature(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle literature search request."""
        try:
            # Parse search parameters
            lit_review_id = payload.get("lit_review_id", str(uuid.uuid4()))
            research_plan = payload.get("research_plan", "")
            filters = payload.get("filters", {})
            sources = payload.get("sources", ["semantic_scholar", "arxiv", "crossref"])
            max_results = payload.get("max_results", 100)

            if not research_plan:
                return {
                    "status": "failed",
                    "error": "Research plan is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Create search query
            search_query = SearchQuery(
                lit_review_id=lit_review_id,
                research_plan=research_plan,
                filters=filters,
                sources=sources,
                max_results=max_results
            )
            
            # Execute search
            search_report = await self.search_literature(search_query)
            
            return {
                "status": "completed",
                "search_report": {
                    "lit_review_id": search_report.lit_review_id,
                    "total_fetched": search_report.total_fetched,
                    "total_unique": search_report.total_unique,
                    "per_source_counts": search_report.per_source_counts,
                    "duration": (search_report.end_time - search_report.start_time).total_seconds(),
                    "errors": search_report.errors
                },
                "records": search_report.records,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to handle search literature: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_normalize_records(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle record normalization request."""
        try:
            records = payload.get("records", [])
            source = payload.get("source", "unknown")
            
            if not records:
                return {
                    "status": "failed",
                    "error": "Records are required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Normalize records
            normalized_records = self._normalize_records(records, source)
            
            return {
                "status": "completed",
                "normalized_records": normalized_records,
                "count": len(normalized_records),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to handle normalize records: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def search_literature(self, search_query: SearchQuery) -> SearchReport:
        """
        Execute a literature search across multiple sources.
        
        Args:
            search_query: Search query parameters
            
        Returns:
            SearchReport with results summary
        """
        start_time = datetime.now()
        total_fetched = 0
        per_source_counts = {}
        errors = []
        all_records = []
        
        logger.info(f"Starting literature search for review {search_query.lit_review_id}")
        
        # Extract AI-optimized search terms if research plan is available
        search_terms = []
        if search_query.research_plan:
            logger.info("Research plan provided, extracting AI-optimized search terms")
            search_topics_response = await self._extract_search_terms_from_research_plan(
                search_query.research_plan
            )
            
            # Parse the AI response - it should be JSON string containing search topics
            if search_topics_response:
                try:
                    if isinstance(search_topics_response, str):
                        # If it's a string, try to parse as JSON
                        search_topics_dict = json.loads(search_topics_response)
                    elif isinstance(search_topics_response, dict):
                        # If it's already a dict, use it directly
                        search_topics_dict = search_topics_response
                    else:
                        # If it's a list of strings, use them directly
                        search_terms = search_topics_response if isinstance(search_topics_response, list) else [str(search_topics_response)]
                        search_topics_dict = None
                    
                    # Extract all search terms from the dictionary structure
                    if search_topics_dict:
                        for topic, terms in search_topics_dict.items():
                            if isinstance(terms, list):
                                search_terms.extend(terms)
                            else:
                                search_terms.append(str(terms))
                                
                    logger.info(f"Extracted {len(search_terms)} search terms from AI response")
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse AI response as JSON: {e}. Using fallback.")
                    search_terms = [search_query.query or "general research"]
            else:
                logger.warning("No search terms returned from AI, using fallback")
                search_terms = [search_query.query or "general research"]
        else:
            logger.info("No research plan provided, using original query")
            search_terms = [search_query.query or "general research"]

        logger.info(f"Using search terms: {search_terms}")

        # Search each configured source with all terms
        sources = search_query.sources or ["semantic_scholar", "arxiv", "crossref"]
        
        # Execute searches concurrently but with rate limiting
        search_tasks = []
        for source in sources:
            if source in self.api_configs:
                task = asyncio.create_task(
                    self._search_source_with_terms(source, search_query, search_terms)
                )
                search_tasks.append((source, task))
            else:
                error_msg = f"Unknown source: {source}"
                errors.append(error_msg)
                logger.warning(error_msg)
        
        # Wait for all searches to complete
        for source, task in search_tasks:
            try:
                source_records = await task
                
                if source_records:
                    # Normalize records
                    normalized_records = self._normalize_records(source_records, source)
                    all_records.extend(normalized_records)
                    per_source_counts[source] = per_source_counts.get(source, 0) + len(source_records)
                    total_fetched += len(source_records)
                    
                    logger.info(f"Retrieved {len(source_records)} records from {source}")
                else:
                    if source not in per_source_counts:
                        per_source_counts[source] = 0
                        
            except Exception as e:
                error_msg = f"Error searching {source}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg, exc_info=True)
                per_source_counts[source] = 0
        
        # Deduplicate records
        unique_records = self._deduplicate_records(all_records)
        
        end_time = datetime.now()
        
        # Create search report
        search_report = SearchReport(
            lit_review_id=search_query.lit_review_id,
            total_fetched=total_fetched,
            total_unique=len(unique_records),
            per_source_counts=per_source_counts,
            start_time=start_time,
            end_time=end_time,
            errors=errors,
            records=unique_records
        )
        
        logger.info(f"Literature search completed. Fetched {total_fetched} records, "
                   f"{len(unique_records)} unique after deduplication")
        
        return search_report
        
    async def _search_source(self, source: str, search_query: SearchQuery) -> List[Dict[str, Any]]:
        """Search a specific source."""
        try:
            if source == "semantic_scholar":
                return await self._search_semantic_scholar(search_query)
            elif source == "arxiv":
                return await self._search_arxiv(search_query)
            elif source == "pubmed":
                return await self._search_pubmed(search_query)
            elif source == "crossref":
                return await self._search_crossref(search_query)
            else:
                logger.warning(f"Unsupported source: {source}")
                return []
                
        except Exception as e:
            logger.error(f"Error searching {source}: {e}")
            return []
    
    async def _search_source_with_terms(self, source: str, search_query: SearchQuery, search_terms: List[str]) -> List[Dict[str, Any]]:
        """Search a specific source using multiple AI-optimized search terms."""
        try:
            all_results = []
            
            # Search with each optimized term
            for term in search_terms:
                # Create a modified search query with the optimized term
                modified_query = SearchQuery(
                    lit_review_id=search_query.lit_review_id,
                    query=term,
                    filters=search_query.filters,
                    sources=search_query.sources,
                    max_results=max(10, search_query.max_results // len(search_terms)),  # Distribute max results
                    search_depth=search_query.search_depth,
                    research_plan=search_query.research_plan
                )
                
                # Search with the modified query
                if source == "semantic_scholar":
                    results = await self._search_semantic_scholar(modified_query)
                elif source == "arxiv":
                    results = await self._search_arxiv(modified_query)
                elif source == "pubmed":
                    results = await self._search_pubmed(modified_query)
                elif source == "crossref":
                    results = await self._search_crossref(modified_query)
                else:
                    logger.warning(f"Unsupported source: {source}")
                    results = []
                
                if results:
                    all_results.extend(results)
                    logger.info(f"Found {len(results)} results for term '{term}' in {source}")
            
            # Remove duplicates within this source's results
            unique_results = self._deduplicate_source_results(all_results)
            logger.info(f"Total unique results from {source} using AI search terms: {len(unique_results)}")
            
            return unique_results
            
        except Exception as e:
            logger.error(f"Error searching {source} with AI terms: {e}")
            return []
    
    def _deduplicate_source_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicates within a single source's results."""
        seen_identifiers = set()
        unique_results = []
        
        for result in results:
            # Create a unique identifier for this result
            identifier = None
            
            # Try DOI first (most reliable)
            if 'doi' in result and result['doi']:
                identifier = f"doi:{result['doi']}"
            # Try arXiv ID
            elif 'id' in result and result['id'] and 'arxiv' in str(result['id']).lower():
                identifier = f"arxiv:{result['id']}"
            # Try paper ID (for Semantic Scholar)
            elif 'paperId' in result and result['paperId']:
                identifier = f"paperId:{result['paperId']}"
            # Fall back to title-based identification
            elif 'title' in result and result['title']:
                title_value = result['title']
                # Handle lists by taking the first element
                if isinstance(title_value, list):
                    title_value = title_value[0] if len(title_value) > 0 and title_value[0] else ""
                identifier = f"title:{str(title_value).lower().strip()}"
            
            if identifier and identifier not in seen_identifiers:
                seen_identifiers.add(identifier)
                unique_results.append(result)
            elif not identifier:
                # If we can't create an identifier, include it anyway
                unique_results.append(result)
        
        return unique_results
    
    async def _search_semantic_scholar(self, search_query: SearchQuery) -> List[Dict[str, Any]]:
        """Search Semantic Scholar API."""
        try:
            if not self.session:
                logger.error("HTTP session not initialized")
                return []
                
            config = self.api_configs['semantic_scholar']
            url = config['base_url']
            
            params = {
                'query': search_query.query,
                'limit': min(search_query.max_results, config['max_results_per_request']),
                'fields': 'paperId,title,abstract,authors,year,venue,doi,url,citationCount'
            }
            
            # Apply filters
            if 'year_min' in search_query.filters:
                params['year'] = f"{search_query.filters['year_min']}-"
            if 'year_max' in search_query.filters:
                if 'year' in params:
                    params['year'] = f"{search_query.filters.get('year_min', 1900)}-{search_query.filters['year_max']}"
                else:
                    params['year'] = f"-{search_query.filters['year_max']}"
            
            # Rate limiting
            await asyncio.sleep(config['rate_limit'])
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', [])
                else:
                    logger.warning(f"Semantic Scholar API returned status {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error searching Semantic Scholar: {e}")
            return []
    
    async def _search_arxiv(self, search_query: SearchQuery) -> List[Dict[str, Any]]:
        """Search arXiv API."""
        try:
            if not self.session:
                logger.error("HTTP session not initialized")
                return []
                
            config = self.api_configs['arxiv']
            url = config['base_url']
            
            # Build search query
            search_terms = []
            query_parts = search_query.query.split()
            
            # Simple query construction - can be enhanced
            if len(query_parts) > 1:
                search_terms.append(f'all:"{search_query.query}"')
            else:
                search_terms.append(f'all:{search_query.query}')
            
            params = {
                'search_query': ' AND '.join(search_terms),
                'start': 0,
                'max_results': min(search_query.max_results, config['max_results_per_request']),
                'sortBy': 'relevance',
                'sortOrder': 'descending'
            }
            
            # Rate limiting
            await asyncio.sleep(config['rate_limit'])
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    xml_content = await response.text()
                    return self._parse_arxiv_xml(xml_content)
                else:
                    logger.warning(f"arXiv API returned status {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error searching arXiv: {e}")
            return []
    
    async def _search_pubmed(self, search_query: SearchQuery) -> List[Dict[str, Any]]:
        """Search PubMed API."""
        try:
            if not self.session:
                logger.error("HTTP session not initialized")
                return []
                
            config = self.api_configs['pubmed']
            
            # First, search for IDs
            search_url = f"{config['base_url']}/esearch.fcgi"
            search_params = {
                'db': 'pubmed',
                'term': search_query.query,
                'retmax': min(search_query.max_results, config['max_results_per_request']),
                'retmode': 'json'
            }
            
            # Rate limiting
            await asyncio.sleep(config['rate_limit'])
            
            async with self.session.get(search_url, params=search_params) as response:
                if response.status != 200:
                    logger.warning(f"PubMed search returned status {response.status}")
                    return []
                
                search_data = await response.json()
                id_list = search_data.get('esearchresult', {}).get('idlist', [])
                
                if not id_list:
                    return []
            
            # Fetch details for the IDs
            fetch_url = f"{config['base_url']}/efetch.fcgi"
            fetch_params = {
                'db': 'pubmed',
                'id': ','.join(id_list),
                'retmode': 'xml'
            }
            
            # Rate limiting
            await asyncio.sleep(config['rate_limit'])
            
            async with self.session.get(fetch_url, params=fetch_params) as response:
                if response.status == 200:
                    xml_content = await response.text()
                    return self._parse_pubmed_xml(xml_content)
                else:
                    logger.warning(f"PubMed fetch returned status {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error searching PubMed: {e}")
            return []
    
    async def _search_crossref(self, search_query: SearchQuery) -> List[Dict[str, Any]]:
        """Search CrossRef API."""
        try:
            if not self.session:
                logger.error("HTTP session not initialized")
                return []
                
            config = self.api_configs['crossref']
            url = config['base_url']
            
            params = {
                'query': search_query.query,
                'rows': min(search_query.max_results, config['max_results_per_request']),
                'sort': 'relevance',
                'order': 'desc'
            }
            
            # Apply filters
            filters = []
            if 'year_min' in search_query.filters:
                filters.append(f"from-pub-date:{search_query.filters['year_min']}")
            if 'year_max' in search_query.filters:
                filters.append(f"until-pub-date:{search_query.filters['year_max']}")
            if 'publication_types' in search_query.filters:
                for pub_type in search_query.filters['publication_types']:
                    if pub_type == 'journal_article':
                        filters.append('type:journal-article')
            
            if filters:
                params['filter'] = ','.join(filters)
            
            # Rate limiting
            await asyncio.sleep(config['rate_limit'])
            
            headers = {
                'User-Agent': 'Eunice-Research-Platform/1.0 (mailto:contact@eunice.example.com)',
                'Accept': 'application/json'
            }
            
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('message', {}).get('items', [])
                else:
                    logger.warning(f"CrossRef API returned status {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error searching CrossRef: {e}")
            return []
    
    def _parse_arxiv_xml(self, xml_content: str) -> List[Dict[str, Any]]:
        """Parse arXiv XML response."""
        try:
            import xml.etree.ElementTree as ET
            
            root = ET.fromstring(xml_content)
            entries = []
            
            # arXiv uses Atom namespace
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            for entry in root.findall('atom:entry', ns):
                try:
                    title = entry.find('atom:title', ns)
                    summary = entry.find('atom:summary', ns)
                    published = entry.find('atom:published', ns)
                    
                    authors = []
                    for author in entry.findall('atom:author', ns):
                        name = author.find('atom:name', ns)
                        if name is not None and name.text:
                            authors.append(name.text.strip())
                    
                    # Extract arXiv ID from id
                    entry_id = entry.find('atom:id', ns)
                    arxiv_id = None
                    if entry_id is not None and entry_id.text:
                        # Extract ID from URL like http://arxiv.org/abs/2301.12345v1
                        match = re.search(r'abs/([0-9]+\.[0-9]+)', entry_id.text)
                        if match:
                            arxiv_id = match.group(1)
                    
                    # Extract categories
                    categories = []
                    for category in entry.findall('atom:category', ns):
                        term = category.get('term')
                        if term:
                            categories.append(term)
                    
                    record = {
                        'title': title.text.strip() if title is not None and title.text else None,
                        'abstract': summary.text.strip() if summary is not None and summary.text else None,
                        'authors': authors,
                        'published': published.text if published is not None else None,
                        'arxiv_id': arxiv_id,
                        'url': entry_id.text if entry_id is not None else None,
                        'categories': categories
                    }
                    entries.append(record)
                    
                except Exception as e:
                    logger.warning(f"Error parsing arXiv entry: {e}")
                    continue
            
            return entries
            
        except Exception as e:
            logger.error(f"Error parsing arXiv XML: {e}")
            return []
    
    def _parse_pubmed_xml(self, xml_content: str) -> List[Dict[str, Any]]:
        """Parse PubMed XML response."""
        try:
            import xml.etree.ElementTree as ET
            
            root = ET.fromstring(xml_content)
            entries = []
            
            for article in root.findall('.//PubmedArticle'):
                try:
                    # Extract basic information
                    title_elem = article.find('.//ArticleTitle')
                    abstract_elem = article.find('.//AbstractText')
                    pmid_elem = article.find('.//PMID')
                    
                    # Extract authors
                    authors = []
                    for author in article.findall('.//Author'):
                        lastname = author.find('LastName')
                        forename = author.find('ForeName')
                        if lastname is not None and forename is not None:
                            if lastname.text and forename.text:
                                authors.append(f"{forename.text} {lastname.text}")
                    
                    # Extract publication year
                    year_elem = article.find('.//PubDate/Year')
                    
                    # Extract journal
                    journal_elem = article.find('.//Journal/Title')
                    
                    # Extract DOI
                    doi_elem = article.find('.//ArticleId[@IdType="doi"]')
                    
                    # Extract keywords/MeSH terms
                    mesh_terms = []
                    for mesh in article.findall('.//MeshHeading/DescriptorName'):
                        if mesh.text:
                            mesh_terms.append(mesh.text)
                    
                    record = {
                        'title': title_elem.text if title_elem is not None and title_elem.text else None,
                        'abstract': abstract_elem.text if abstract_elem is not None and abstract_elem.text else None,
                        'authors': authors,
                        'pmid': pmid_elem.text if pmid_elem is not None and pmid_elem.text else None,
                        'year': year_elem.text if year_elem is not None and year_elem.text else None,
                        'journal': journal_elem.text if journal_elem is not None and journal_elem.text else None,
                        'doi': doi_elem.text if doi_elem is not None and doi_elem.text else None,
                        'mesh_terms': mesh_terms
                    }
                    entries.append(record)
                    
                except Exception as e:
                    logger.warning(f"Error parsing PubMed entry: {e}")
                    continue
            
            return entries
            
        except Exception as e:
            logger.error(f"Error parsing PubMed XML: {e}")
            return []
    
    def _normalize_records(self, records: List[Dict[str, Any]], source: str) -> List[Dict[str, Any]]:
        """
        Normalize records from a specific source to common schema.
        
        Args:
            records: Raw records from source
            source: Source identifier
            
        Returns:
            List of normalized records
        """
        normalized = []
        
        for record in records:
            try:
                normalized_record = {
                    'source': source,
                    'title': self._extract_field(record, ['title', 'Title']),
                    'authors': self._extract_authors(record),
                    'abstract': self._extract_field(record, ['abstract', 'Abstract', 'summary']),
                    'doi': self._extract_field(record, ['doi', 'DOI', 'externalIds.DOI']),
                    'pmid': self._extract_field(record, ['pmid', 'PMID', 'externalIds.PubMed']),
                    'arxiv_id': self._extract_field(record, ['arxiv_id', 'id']),
                    'year': self._extract_year(record),
                    'journal': self._extract_field(record, ['journal', 'venue', 'Journal', 'container-title']),
                    'url': self._extract_field(record, ['url', 'URL', 'link']),
                    'citation_count': self._extract_field(record, ['citationCount', 'citations', 'is-referenced-by-count']),
                    'publication_type': self._extract_field(record, ['type', 'publication_type']),
                    'mesh_terms': record.get('mesh_terms', []) if source == 'pubmed' else [],
                    'categories': record.get('categories', []) if source == 'arxiv' else [],
                    'raw_data': record,  # Store original data
                    'retrieval_timestamp': datetime.now().isoformat()
                }
                normalized.append(normalized_record)
                
            except Exception as e:
                logger.warning(f"Error normalizing record from {source}: {str(e)}")
                continue
        
        return normalized
    
    def _extract_field(self, record: Dict[str, Any], field_names: List[str]) -> Optional[str]:
        """Extract field value using multiple possible field names."""
        for field_name in field_names:
            if '.' in field_name:
                # Handle nested fields
                value = record
                for part in field_name.split('.'):
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        value = None
                        break
                if value:
                    # Handle lists by taking the first element or joining
                    if isinstance(value, list):
                        if len(value) > 0:
                            return str(value[0]) if value[0] else None
                        else:
                            return None
                    return str(value)
            else:
                if field_name in record and record[field_name]:
                    value = record[field_name]
                    # Handle lists by taking the first element or joining
                    if isinstance(value, list):
                        if len(value) > 0:
                            return str(value[0]) if value[0] else None
                        else:
                            return None
                    return str(value)
        return None
    
    def _extract_authors(self, record: Dict[str, Any]) -> List[str]:
        """Extract and normalize author information."""
        authors = []
        
        # Try different author field formats
        author_fields = ['authors', 'Authors', 'author', 'Author']
        
        for field in author_fields:
            if field in record and record[field]:
                author_data = record[field]
                
                if isinstance(author_data, list):
                    for author in author_data:
                        if isinstance(author, dict):
                            # Handle different author formats
                            name = None
                            if 'name' in author:
                                name = author['name']
                            elif 'given' in author and 'family' in author:
                                # CrossRef format
                                name = f"{author.get('given', '')} {author.get('family', '')}"
                            elif 'firstName' in author and 'lastName' in author:
                                # Other formats
                                name = f"{author.get('firstName', '')} {author.get('lastName', '')}"
                            elif 'forename' in author and 'lastname' in author:
                                # PubMed format
                                name = f"{author.get('forename', '')} {author.get('lastname', '')}"
                            
                            if name and name.strip():
                                authors.append(name.strip())
                        elif isinstance(author, str):
                            authors.append(author)
                elif isinstance(author_data, str):
                    # Parse string of authors
                    authors.extend([a.strip() for a in author_data.split(',') if a.strip()])
                
                if authors:
                    break
        
        return authors
    
    def _extract_year(self, record: Dict[str, Any]) -> Optional[int]:
        """Extract publication year."""
        year_fields = ['year', 'Year', 'publicationDate', 'date', 'published']
        
        for field in year_fields:
            if field in record and record[field]:
                year_value = record[field]
                
                if isinstance(year_value, int):
                    return year_value
                elif isinstance(year_value, str):
                    # Try to extract year from date strings
                    year_match = re.search(r'\b(19|20)\d{2}\b', year_value)
                    if year_match:
                        return int(year_match.group())
        
        # Handle CrossRef date arrays
        if 'published-print' in record:
            date_parts = record['published-print'].get('date-parts', [])
            if date_parts and len(date_parts[0]) > 0:
                return int(date_parts[0][0])
        
        if 'published-online' in record:
            date_parts = record['published-online'].get('date-parts', [])
            if date_parts and len(date_parts[0]) > 0:
                return int(date_parts[0][0])
        
        if 'created' in record:
            date_parts = record['created'].get('date-parts', [])
            if date_parts and len(date_parts[0]) > 0:
                return int(date_parts[0][0])
        
        return None
    
    async def _check_ai_agent_availability(self):
        """Check if AI agent is available via MCP for search term extraction."""
        try:
            if not self.websocket or not self.mcp_connected:
                logger.info("MCP connection not available, AI search term optimization will be disabled")
                self.ai_agent_available = False
                return
            
            # Send a ping to check if AI agent is available
            check_message = {
                "type": "agent_check",
                "target_agent": "ai_agent",
                "capabilities": ["optimize_search_terms"],
                "timestamp": datetime.now().isoformat()
            }
            
            await self.websocket.send(json.dumps(check_message))
            logger.info("AI agent availability check sent via MCP")
            self.ai_agent_available = True  # Assume available for now
            
        except Exception as e:
            logger.warning(f"Error checking AI agent availability: {e}")
            self.ai_agent_available = False


    async def _extract_search_terms_from_research_plan(self, research_plan):
        """
        Extract optimized search terms from research plan using AI agent via MCP.
        
        Args:
            research_plan: AI-generated research plan with objectives, questions, etc. (can be dict or str)
            
        Returns:
            List of optimized search terms for academic databases
        """

        logger.info(f"Extracting search terms from research plan: {research_plan}")

        # Create research planning prompt
        prompt = (
            "You are a scientific search-strategy assistant. When given a research plan, "
            "reply ONLY with VALID JSON matching the schema in the instruction, "
            "containing highly targeted literature-search phrases ready for PubMed / "
            "Web of Science / Google Scholar. Do not add commentary or markdown.\n\n"
            f"Plan: {research_plan}\n\n"
            "Format your response in JSON with the following structure:\n"
            "{\n"
            '    "topic 1": ["Search String 1", "Search String 2", ...],\n'
            '    "topic 2": ["Search String 1", "Search String 2", ...],\n'
            '    "topic 3": ["Search String 1", "Search String 2", ...],\n'
            "    ...\n"
            "}\n"
            "Ensure the search strings are specific, relevant, and suitable for "
            "academic databases.\n"
        )

        # Send request to AI agent via MCP for search term optimization
        optimization_request = {
            "type": "research_action",
            "data": {
                "task_id": f"search_term_optimization_{uuid.uuid4().hex[:8]}",
                "context_id": f"literature_ai_optimization",
                "agent_type": "ai_service",  # Use correct agent type for AI service
                "action": "ai_chat_completion",  # Use the actual AI service action
                "payload": {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert research assistant specializing in academic literature search optimization. Extract 3-5 highly targeted search terms from the provided research plan that will be most effective for finding relevant academic papers in databases like PubMed, arXiv, Semantic Scholar, and CrossRef."
                        },
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ],
                    "max_tokens": 200,
                    "temperature": 0.3
                }
            },
            "client_id": self.agent_id,
            "timestamp": datetime.now().isoformat()
        }
        
        if not self.websocket or not self.mcp_connected:
            logger.warning("MCP connection not available, unable to perform a search")
            fallback_query = (research_plan[:100] if isinstance(research_plan, str) else str(research_plan)[:100])
            return [fallback_query]
        
        # Send the request
        task_id = optimization_request["data"]["task_id"]
        await self.websocket.send(json.dumps(optimization_request))
        logger.info("Search term optimization request sent to AI agent via MCP")
        # Wait for response using Future-based approach
        try:
            # Create future for this request
            future = asyncio.Future()
            self.pending_responses[task_id] = future
            
            # Wait for response with timeout
            response_data = await asyncio.wait_for(future, timeout=30.0)
            
            if (response_data.get("type") == "task_result" and 
                response_data.get("task_id") == task_id):
                
                if response_data.get("status") == "completed":
                    chat_response = response_data.get("result", {})
                    logger.info(f"Raw AI result received: {chat_response}")
                
                    if "choices" in chat_response and len(chat_response["choices"]) > 0:
                        choice = chat_response["choices"][0]

                        if "message" in choice and "content" in choice["message"]:
                            content = choice["message"]["content"]
                            logger.info(f"Search topics and terms extracted: {content}")
                            logger.info(f"Extracted content from OpenAI response: {len(content)} chars")
                            # Return topics and search terms
                            return content

            logger.warning("No valid search terms returned from AI agent")
            return []
            
        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for AI agent response")
            return []
        except Exception as e:
            logger.error(f"Error extracting search terms from research plan: {e}")
            return []
        finally:
            # Clean up pending response
            self.pending_responses.pop(task_id, None)
            logger.info("Pending response cleaned up for search term optimization request")
    
    
    async def _get_cached_search_terms(self, source_type: str, source_id: str, original_query: str) -> Optional[List[str]]:
        """
        Retrieve cached search terms from database.
        
        Args:
            source_type: 'plan' or 'task'
            source_id: ID of the plan or task
            original_query: Original query to match against
            
        Returns:
            List of cached search terms if found and not expired, None otherwise
        """
        try:
            if not self.websocket or not self.mcp_connected:
                return None
            
            # Send request to database agent via MCP
            task_id = f"get_search_terms_{uuid.uuid4().hex[:8]}"
            db_request = {
                "type": "research_action",
                "data": {
                    "task_id": task_id,
                    "context_id": f"search_terms_cache_{source_type}_{source_id}",
                    "agent_type": "database",
                    "action": f"get_search_terms_for_{source_type}",
                    "payload": {
                        f"{source_type}_id": source_id
                    }
                },
                "client_id": "literature_search",
                "timestamp": datetime.now().isoformat()
            }
            
            task_id = db_request["data"]["task_id"]
            await self.websocket.send(json.dumps(db_request))
            
            # Wait for response using Future-based approach
            try:
                # Create future for this request
                future = asyncio.Future()
                self.pending_responses[task_id] = future
                
                # Wait for response with timeout
                response_data = await asyncio.wait_for(future, timeout=5.0)
                
                if (response_data.get("type") == "task_result" and 
                    response_data.get("task_id") == task_id):
                    
                    result = response_data.get("result", {})
                    if result.get("status") == "completed":
                        optimizations = result.get("optimizations", [])
                        
                        # Find the most recent optimization for this query
                        for optimization in optimizations:
                            if optimization.get("original_query") == original_query:
                                # Check if expired
                                expires_at = optimization.get("expires_at")
                                if expires_at:
                                    try:
                                        # Handle both timezone-aware and naive datetime strings
                                        if expires_at.endswith('Z'):
                                            expires_at = expires_at.replace('Z', '+00:00')
                                        
                                        expiry_time = datetime.fromisoformat(expires_at)
                                        
                                        # Convert to UTC for comparison if timezone-aware
                                        if expiry_time.tzinfo:
                                            current_time = datetime.now(expiry_time.tzinfo)
                                        else:
                                            current_time = datetime.now()
                                            
                                        if current_time > expiry_time:
                                            continue  # Skip expired
                                    except (ValueError, TypeError) as e:
                                        logger.warning(f"Invalid expires_at format: {expires_at}, error: {e}")
                                        continue
                                
                                return optimization.get("optimized_terms", [])
                    
                    return None
                        
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for database response")
                return None
            except Exception as e:
                logger.error(f"Error receiving database response: {e}")
                return None
            finally:
                # Clean up pending response
                self.pending_responses.pop(task_id, None)
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving cached search terms: {e}")
            return None
    
    async def _store_search_terms(self, source_type: str, source_id: str, original_query: str, 
                                 optimized_terms: List[str], optimization_context: Dict[str, Any],
                                 target_databases: List[str]) -> bool:
        """
        Store optimized search terms in database.
        
        Args:
            source_type: 'plan' or 'task'
            source_id: ID of the plan or task
            original_query: Original query
            optimized_terms: List of optimized search terms
            optimization_context: Context from AI optimization
            target_databases: Target databases for the search
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            if not self.websocket or not self.mcp_connected:
                return False
            
            # Send request to database agent via MCP
            task_id = f"store_search_terms_{uuid.uuid4().hex[:8]}"
            db_request = {
                "type": "research_action",
                "data": {
                    "task_id": task_id,
                    "context_id": f"store_search_terms_{source_type}_{source_id}",
                    "agent_type": "database",
                    "action": "store_optimized_search_terms",
                    "payload": {
                        "source_type": source_type,
                        "source_id": source_id,
                        "original_query": original_query,
                        "optimized_terms": optimized_terms,
                        "optimization_context": optimization_context,
                        "target_databases": target_databases,
                        "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),  # Cache for 24 hours
                        "metadata": {
                            "created_by": "literature_service",
                            "optimization_version": "1.0"
                        }
                    }
                },
                "client_id": "literature_search",
                "timestamp": datetime.now().isoformat()
            }
            
            task_id = db_request["data"]["task_id"]
            await self.websocket.send(json.dumps(db_request))
            
            # Wait for response using Future-based approach
            try:
                # Create future for this request
                future = asyncio.Future()
                self.pending_responses[task_id] = future
                
                # Wait for response with timeout
                response_data = await asyncio.wait_for(future, timeout=5.0)
                
                if (response_data.get("type") == "task_result" and 
                    response_data.get("task_id") == task_id):
                    
                    result = response_data.get("result", {})
                    if result.get("status") == "completed":
                        logger.info(f"Successfully stored search terms for {source_type} {source_id}")
                        return True
                    else:
                        logger.warning(f"Failed to store search terms: {result.get('error', 'Unknown error')}")
                        return False
                        
            except asyncio.TimeoutError:
                logger.warning("Timeout storing search terms in database")
                return False
            except Exception as e:
                logger.error(f"Error receiving database response: {e}")
                return False
            finally:
                # Clean up pending response
                self.pending_responses.pop(task_id, None)
            
            return False  # Default return if no successful response
            
        except Exception as e:
            logger.error(f"Error storing search terms: {e}")
            return False
    
    def _deduplicate_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate records using DOI, PMID, arXiv ID, or title/author/year heuristics.
        
        Args:
            records: List of normalized records
            
        Returns:
            List of unique records
        """
        seen_dois = set()
        seen_pmids = set()
        seen_arxiv_ids = set()
        seen_hashes = set()
        unique_records = []
        
        for record in records:
            is_duplicate = False
            
            # Check DOI first (most reliable)
            doi = record.get('doi')
            if doi:
                if doi in seen_dois:
                    is_duplicate = True
                else:
                    seen_dois.add(doi)
            
            # Check PMID
            pmid = record.get('pmid')
            if not is_duplicate and pmid:
                if pmid in seen_pmids:
                    is_duplicate = True
                else:
                    seen_pmids.add(pmid)
            
            # Check arXiv ID
            arxiv_id = record.get('arxiv_id')
            if not is_duplicate and arxiv_id:
                if arxiv_id in seen_arxiv_ids:
                    is_duplicate = True
                else:
                    seen_arxiv_ids.add(arxiv_id)
            
            # Check title/author/year hash if no unique identifiers
            if not is_duplicate and not doi and not pmid and not arxiv_id:
                content_hash = self._generate_content_hash(record)
                if content_hash in seen_hashes:
                    is_duplicate = True
                else:
                    seen_hashes.add(content_hash)
            
            if not is_duplicate:
                unique_records.append(record)
        
        return unique_records
    
    def _generate_content_hash(self, record: Dict[str, Any]) -> str:
        """Generate hash for title/author/year deduplication."""
        title = (record.get('title') or '').lower().strip()
        authors = record.get('authors', [])
        year = record.get('year')
        
        # Create normalized string for hashing
        author_string = ', '.join(sorted([a.lower().strip() for a in authors]))
        content_string = f"{title}|{author_string}|{year}"
        
        return hashlib.md5(content_string.encode(), usedforsecurity=False).hexdigest()


# Request/Response models removed - NO DIRECT API ENDPOINTS ALLOWED
# All business operations must go through MCP protocol exclusively

# Global service instance
literature_service: Optional[LiteratureSearchService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global literature_service
    
    # Load configuration
    config_path = Path("/app/config/config.json")
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
    else:
        config = {
            "service_host": "0.0.0.0",
            "service_port": 8003,
            "mcp_server_url": "ws://mcp-server:9000",
            "max_concurrent_searches": 3,
            "search_timeout": 300,
            "rate_limit_delay": 1.0
        }
    
    # Start service
    literature_service = LiteratureSearchService(config)
    await literature_service.start()
    
    try:
        yield
    finally:
        # Cleanup
        if literature_service:
            await literature_service.stop()


def get_mcp_status() -> Dict[str, Any]:
    """Get MCP connection status for health check."""
    if literature_service:
        return {
            "connected": literature_service.mcp_connected,
            "last_heartbeat": datetime.now().isoformat()
        }
    return {"connected": False, "last_heartbeat": "never"}


def get_additional_metadata() -> Dict[str, Any]:
    """Get additional metadata for health check."""
    if literature_service:
        return {
            "capabilities": [
                "search_academic_papers",
                "search_literature", 
                "normalize_records",
                "deduplicate_results",
                "multi_source_search",
                "bibliographic_search"
            ],
            "supported_sources": list(literature_service.api_configs.keys()),
            "api_integrations": {
                "semantic_scholar": "AI-powered academic search with rich metadata",
                "pubmed": "Medical and life sciences literature",
                "arxiv": "Preprint server for physics, mathematics, computer science",
                "crossref": "DOI-based academic publication metadata"
            },
            "features": [
                "multi_source_parallel_search",
                "intelligent_deduplication",
                "format_normalization", 
                "rate_limiting",
                "error_recovery",
                "mcp_protocol_integration"
            ]
        }
    return {}


# Create health check only FastAPI application
app = create_health_check_app(
    agent_type="literature",
    agent_id="literature-search-agent",
    version="1.0.0",
    get_mcp_status=get_mcp_status,
    get_additional_metadata=get_additional_metadata
)

# Set lifespan for service management
app.router.lifespan_context = lifespan


if __name__ == "__main__":
    logger.info("🚨 ARCHITECTURE COMPLIANCE: Literature Search Agent")
    logger.info("✅ ONLY health check API exposed")
    logger.info("✅ All business operations via MCP protocol exclusively")
    
    uvicorn.run(
        "literature_service:app",
        host="0.0.0.0",
        port=8003,
        log_level="info"
    )
