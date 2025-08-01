"""
Main Literature Search Service implementation.
"""

import asyncio
import json
import logging
import os
import ssl
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import websockets

from .ai_integration import AIIntegration
from .database_integration import DatabaseIntegration
from .deduplication import RecordDeduplicator
from .models import SearchQuery, SearchReport
from .normalizers import RecordNormalizer
from .search_engines import SearchEngines

logger = logging.getLogger(__name__)


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
        self.core_api_key = os.environ.get("CORE_API_KEY")

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
        
        # Initialize service components
        self.search_engines: Optional[SearchEngines] = None
        self.normalizer = RecordNormalizer()
        self.deduplicator = RecordDeduplicator()
        self.ai_integration: Optional[AIIntegration] = None
        self.database_integration: Optional[DatabaseIntegration] = None
        
        logger.info(f"Literature Search Service initialized on port {self.service_port}")
    
    async def start(self):
        """Start the Literature Search Service."""
        try:
            # Initialize HTTP session with SSL context for development
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={'User-Agent': 'Eunice-Research-Platform/1.0'},
                connector=connector
            )
            
            # Initialize service components
            self.search_engines = SearchEngines(self.session, self.core_api_key)
            
            # Connect to MCP server
            await self._connect_to_mcp_server()
            
            # Initialize MCP-dependent components
            self.ai_integration = AIIntegration(self.websocket, self.agent_id)
            self.database_integration = DatabaseIntegration(self.websocket, self.agent_id)
            
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
                
                # Handle task result responses for pending AI/DB requests
                if self.ai_integration and self.ai_integration.handle_task_result(data):
                    continue
                if self.database_integration and self.database_integration.handle_task_result(data):
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
            plan_id = payload.get("plan_id", "")
            max_results = payload.get("max_results", 10)
            search_depth = payload.get("search_depth", "standard")
            sources = payload.get("sources", ["core", "arxiv", "crossref", "semantic_scholar", "pubmed"])

            if not research_plan:
                return {
                    "status": "failed",
                    "error": "Research plan is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Create search query
            search_query = SearchQuery(
                lit_review_id=str(uuid.uuid4()),
                plan_id=plan_id,
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
            plan_id = payload.get("plan_id", "")
            research_plan = payload.get("research_plan", "")
            filters = payload.get("filters", {})
            sources = payload.get("sources", ["core", "arxiv", "crossref", "semantic_scholar", "pubmed"])
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
                plan_id=plan_id,
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
            normalized_records = self.normalizer.normalize_records(records, source)
            
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
        # Search each configured source with all terms
        sources = search_query.sources or ["semantic_scholar", "arxiv", "pubmed", "crossref", "core"]

        logger.info(f"Starting literature search for review {search_query.lit_review_id}")
        
        # Extract AI-optimized search terms if research plan is available
        search_terms = []
        if search_query.research_plan and self.database_integration and self.ai_integration:
            # Check for cached terms first
            cached_terms = await self.database_integration.get_cached_search_terms(
                "plan", search_query.plan_id, str(search_query.research_plan)[:500]
            )
            if cached_terms:
                search_terms = cached_terms
                logger.info(f"Using {len(search_terms)} cached search terms: {search_terms}")
            else:    
                logger.info("Research plan provided, extracting AI-optimized search terms")
                ai_extracted_terms = await self.ai_integration.extract_search_terms_from_research_plan(
                    search_query.research_plan
                )
            
                # AI extraction now returns a list of search terms directly
                if ai_extracted_terms and isinstance(ai_extracted_terms, list):
                    search_terms = ai_extracted_terms
                    logger.info(f"Extracted {len(search_terms)} search terms from AI response: {search_terms}")
                    # Store terms for future use
                    try:
                        storage_result = await self.database_integration.store_search_terms(
                            "plan", 
                            search_query.plan_id, 
                            str(search_query.research_plan)[:500], # Truncate to avoid issues
                            search_terms, 
                            {"ai_model": "gpt-4o-mini", "extraction_method": "topic_based_json"}, 
                            sources
                        )
                        if storage_result:
                            logger.info(f"Successfully stored {len(search_terms)} search terms in database")
                        else:
                            logger.warning(f"Failed to store search terms in database")
                    except Exception as e:
                        logger.error(f"Exception while storing search terms: {e}", exc_info=True)
                else:
                    logger.warning("No valid search terms returned from AI, using fallback")
                    search_terms = [search_query.query or "general research"]
        else:
            logger.info("No research plan provided, using original query")
            search_terms = [search_query.query or "general research"]

        logger.info(f"Using search terms: {search_terms}")

        # Execute searches concurrently but with rate limiting
        search_tasks = []
        if self.search_engines:
            for source in sources:
                task = asyncio.create_task(
                    self._search_source_with_terms(source, search_query, search_terms)
                )
                search_tasks.append((source, task))
        else:
            error_msg = "Search engines not initialized"
            errors.append(error_msg)
            logger.error(error_msg)
        
        # Wait for all searches to complete
        for source, task in search_tasks:
            try:
                source_records = await task
                
                if source_records:
                    # Normalize records
                    normalized_records = self.normalizer.normalize_records(source_records, source)
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
        unique_records = self.deduplicator.deduplicate_records(all_records)
        
        # Store literature records in database
        if unique_records and search_query.lit_review_id and self.database_integration:
            logger.info(f"Storing {len(unique_records)} literature records in database")
            storage_errors = await self.database_integration.store_literature_records(unique_records, search_query)
            if storage_errors:
                errors.extend(storage_errors)
        
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
    
    async def _search_source_with_terms(self, source: str, search_query: SearchQuery, search_terms: List[str]) -> List[Dict[str, Any]]:
        """Search a specific source using multiple AI-optimized search terms."""
        try:
            if not self.search_engines:
                logger.error("Search engines not initialized")
                return []
                
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
                results = await self.search_engines.search_source(source, modified_query)
                
                if results:
                    all_results.extend(results)
                    logger.info(f"Found {len(results)} results for term '{term}' in {source}")
            
            # Remove duplicates within this source's results
            unique_results = self.deduplicator.deduplicate_source_results(all_results)
            logger.info(f"Total unique results from {source} using AI search terms: {len(unique_results)}")
            
            return unique_results
            
        except Exception as e:
            logger.error(f"Error searching {source} with AI terms: {e}")
            return []
    
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
