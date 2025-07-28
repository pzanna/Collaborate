"""
Literature Search Agent Service for Eunice Research Platform.

This module provides a containerized Literature Search Agent that specializes in:
- Academic literature discovery and collection
- Multi-source bibliographic search (PubMed, arXiv, Semantic Scholar)
- Result normalization and deduplication
- Integration with MCP protocol for task coordination
"""

import asyncio
import hashlib
import json
import logging
import re
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote

import aiohttp
import uvicorn
import websockets
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class SearchQuery:
    """Search query data model for literature search requests."""
    lit_review_id: str
    query: str
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
        self.websocket = None
        self.mcp_connected = False
        
        # HTTP session for API calls
        self.session = None
        
        # Task processing queue
        self.task_queue = asyncio.Queue()
        
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
            }
        }
        
        logger.info(f"Literature Search Service initialized on port {self.service_port}")
    
    async def start(self):
        """Start the Literature Search Service."""
        try:
            # Initialize HTTP session
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={'User-Agent': 'Eunice-Research-Platform/1.0'}
            )
            
            # Connect to MCP server
            await self._connect_to_mcp_server()
            
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
        capabilities = [
            "search_academic_papers",
            "search_literature",
            "normalize_records",
            "deduplicate_results",
            "multi_source_search",
            "bibliographic_search"
        ]
        
        registration_message = {
            "type": "register",
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": capabilities,
            "service_info": {
                "host": self.service_host,
                "port": self.service_port,
                "health_endpoint": f"http://{self.service_host}:{self.service_port}/health"
            }
        }
        
        await self.websocket.send(json.dumps(registration_message))
        logger.info(f"Registered with MCP server: {len(capabilities)} capabilities")
    
    async def _handle_mcp_messages(self):
        """Handle incoming MCP messages."""
        try:
            while self.websocket:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                if data.get("type") == "task":
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
            query = payload.get("query", "")
            max_results = payload.get("max_results", 10)
            search_depth = payload.get("search_depth", "standard")
            sources = payload.get("sources", ["semantic_scholar", "arxiv"])
            
            if not query:
                return {
                    "status": "failed",
                    "error": "Query is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Create search query
            search_query = SearchQuery(
                lit_review_id=str(uuid.uuid4()),
                query=query,
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
            query = payload.get("query", "")
            filters = payload.get("filters", {})
            sources = payload.get("sources", ["semantic_scholar", "arxiv"])
            max_results = payload.get("max_results", 100)
            
            if not query:
                return {
                    "status": "failed",
                    "error": "Query is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Create search query
            search_query = SearchQuery(
                lit_review_id=lit_review_id,
                query=query,
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
        
        # Search each configured source
        sources = search_query.sources or ["semantic_scholar", "arxiv"]
        
        # Execute searches concurrently but with rate limiting
        search_tasks = []
        for source in sources:
            if source in self.api_configs:
                task = asyncio.create_task(
                    self._search_source(source, search_query)
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
                    per_source_counts[source] = len(source_records)
                    total_fetched += len(source_records)
                    
                    logger.info(f"Retrieved {len(source_records)} records from {source}")
                else:
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
            else:
                logger.warning(f"Unsupported source: {source}")
                return []
                
        except Exception as e:
            logger.error(f"Error searching {source}: {e}")
            return []
    
    async def _search_semantic_scholar(self, search_query: SearchQuery) -> List[Dict[str, Any]]:
        """Search Semantic Scholar API."""
        try:
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
                        if name is not None:
                            authors.append(name.text)
                    
                    # Extract arXiv ID from id
                    entry_id = entry.find('atom:id', ns)
                    arxiv_id = entry_id.text.split('/')[-1] if entry_id is not None else None
                    
                    record = {
                        'title': title.text.strip() if title is not None else None,
                        'abstract': summary.text.strip() if summary is not None else None,
                        'authors': authors,
                        'published': published.text if published is not None else None,
                        'arxiv_id': arxiv_id,
                        'url': entry_id.text if entry_id is not None else None
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
                            authors.append(f"{forename.text} {lastname.text}")
                    
                    # Extract publication year
                    year_elem = article.find('.//PubDate/Year')
                    
                    # Extract journal
                    journal_elem = article.find('.//Journal/Title')
                    
                    record = {
                        'title': title_elem.text if title_elem is not None else None,
                        'abstract': abstract_elem.text if abstract_elem is not None else None,
                        'authors': authors,
                        'pmid': pmid_elem.text if pmid_elem is not None else None,
                        'year': year_elem.text if year_elem is not None else None,
                        'journal': journal_elem.text if journal_elem is not None else None
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
                    'journal': self._extract_field(record, ['journal', 'venue', 'Journal']),
                    'url': self._extract_field(record, ['url', 'URL', 'link']),
                    'citation_count': self._extract_field(record, ['citationCount', 'citations']),
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
                    return str(value)
            else:
                if field_name in record and record[field_name]:
                    return str(record[field_name])
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
                            name = author.get('name', '') or f"{author.get('firstName', '')} {author.get('lastName', '')}"
                            if name.strip():
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
        
        return None
    
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
            if not is_duplicate:
                pmid = record.get('pmid')
                if pmid:
                    if pmid in seen_pmids:
                        is_duplicate = True
                    else:
                        seen_pmids.add(pmid)
            
            # Check arXiv ID
            if not is_duplicate:
                arxiv_id = record.get('arxiv_id')
                if arxiv_id:
                    if arxiv_id in seen_arxiv_ids:
                        is_duplicate = True
                    else:
                        seen_arxiv_ids.add(arxiv_id)
            
            # Check title/author/year hash
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
        
        return hashlib.md5(content_string.encode()).hexdigest()


# Request/Response models for FastAPI
class SearchRequest(BaseModel):
    query: str = Field(description="Search query string")
    max_results: int = Field(default=10, description="Maximum number of results")
    sources: List[str] = Field(default=["semantic_scholar", "arxiv"], description="Sources to search")
    search_depth: str = Field(default="standard", description="Search depth: standard, comprehensive")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Additional filters")


class TaskRequest(BaseModel):
    action: str
    payload: Dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    agent_type: str
    mcp_connected: bool
    capabilities: List[str]
    supported_sources: List[str]


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


# FastAPI application
app = FastAPI(
    title="Literature Search Service",
    description="Literature Search Agent for academic paper discovery and collection",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    if not literature_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    capabilities = [
        "search_academic_papers",
        "search_literature",
        "normalize_records",
        "deduplicate_results",
        "multi_source_search",
        "bibliographic_search"
    ]
    
    return HealthResponse(
        status="healthy",
        agent_type="literature",
        mcp_connected=literature_service.mcp_connected,
        capabilities=capabilities,
        supported_sources=list(literature_service.api_configs.keys())
    )


@app.post("/search")
async def search_papers(request: SearchRequest):
    """Search for academic papers."""
    if not literature_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        # Create search query
        search_query = SearchQuery(
            lit_review_id=str(uuid.uuid4()),
            query=request.query,
            max_results=request.max_results,
            sources=request.sources,
            search_depth=request.search_depth,
            filters=request.filters
        )
        
        # Execute search
        search_report = await literature_service.search_literature(search_query)
        
        return {
            "results": search_report.records,
            "summary": {
                "total_found": search_report.total_fetched,
                "total_unique": search_report.total_unique,
                "sources": search_report.per_source_counts,
                "search_duration": (search_report.end_time - search_report.start_time).total_seconds()
            },
            "errors": search_report.errors
        }
        
    except Exception as e:
        logger.error(f"Error searching papers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/task")
async def process_task(request: TaskRequest):
    """Process a literature search task directly (for testing)."""
    if not literature_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        result = await literature_service._process_literature_task({
            "action": request.action,
            "payload": request.payload
        })
        return result
    except Exception as e:
        logger.error(f"Error processing task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "literature_service:app",
        host="0.0.0.0",
        port=8003,
        log_level="info"
    )
