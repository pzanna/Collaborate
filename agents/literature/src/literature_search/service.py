"""
Main Literature Search Service implementation.
"""

import asyncio
import json
import logging
import os
import ssl
import uuid
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd

import aiohttp
import websockets

from .ai_integration import AIIntegration
from .database_integration import DatabaseIntegration
from .models import SearchQuery, SearchReport
from .normalizers import RecordNormalizer
from .search_pipeline import LiteratureSearchPipeline

# Import constants from experiments search_engines
try:
    from experiments.search_engines import (
        SIMILARITY_QUANTILE, TOP_K_TERMS, MAX_RETRIES, BACKOFF_BASE, 
        SEARCH_LIMIT, YEAR_RANGE, NCBI_API_KEY, OPENALEX_EMAIL, CORE_API_KEY
    )
except ImportError:
    # Fallback constants if experiments module not available
    SIMILARITY_QUANTILE = 0.8
    TOP_K_TERMS = 1
    MAX_RETRIES = 5
    BACKOFF_BASE = 5
    SEARCH_LIMIT = 25
    YEAR_RANGE = (2000, 2025)
    NCBI_API_KEY = os.getenv('NCBI_API_KEY')
    OPENALEX_EMAIL = os.getenv('OPENALEX_EMAIL')
    CORE_API_KEY = os.getenv('CORE_API_KEY')

logger = logging.getLogger(__name__)


class LiteratureSearchService:
    """
    Literature Search Service for discovering and collecting bibliographic records.
    
    Handles literature search across multiple sources, normalization,
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
        self.normalizer = RecordNormalizer()
        self.search_pipeline = LiteratureSearchPipeline()
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
            
            # Initialize service components (SearchEngines now handled by search_pipeline)
            # self.search_engines = SearchEngines(self.session, self.core_api_key)
            
            # Connect to MCP server
            await self._connect_to_mcp_server()
            
            # Initialize MCP-dependent components
            self.ai_integration = AIIntegration(self.websocket, self.agent_id)
            self.database_integration = DatabaseIntegration(self.websocket, self.agent_id)
            
            # Set database integration reference in AI integration
            self.ai_integration.database_integration = self.database_integration
            
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
                    ping_interval=20,  # More frequent pings during long operations
                    ping_timeout=15    # Longer timeout for ping responses
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
                ai_handled = False
                db_handled = False
                
                if self.ai_integration:
                    ai_handled = self.ai_integration.handle_task_result(data)
                    if ai_handled:
                        logger.debug(f"✅ AI integration handled message: {data.get('type')} task_id={data.get('task_id')}")
                        continue
                
                if self.database_integration:
                    db_handled = self.database_integration.handle_task_result(data)
                    if db_handled:
                        logger.debug(f"✅ Database integration handled message: {data.get('type')} task_id={data.get('task_id')}")
                        continue
                
                # Log unhandled task results for debugging
                if data.get("type") == "task_result" and not ai_handled and not db_handled:
                    logger.warning(f"⚠️ Unhandled task result: task_id={data.get('task_id')}, neither AI nor DB integration claimed it")
                
                if data.get("type") == "task_request":
                    await self.task_queue.put(data)
                elif data.get("type") == "task":
                    await self.task_queue.put(data)
                elif data.get("type") == "ping":
                    await self.websocket.send(json.dumps({"type": "pong"}))
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("MCP server connection closed")
            self.mcp_connected = False
            # Attempt to reconnect
            asyncio.create_task(self._reconnect_to_mcp_server())
        except Exception as e:
            logger.error(f"Error handling MCP messages: {e}")
            self.mcp_connected = False
            # Attempt to reconnect
            asyncio.create_task(self._reconnect_to_mcp_server())
    
    async def _reconnect_to_mcp_server(self):
        """Attempt to reconnect to MCP server after connection loss."""
        logger.info("Attempting to reconnect to MCP server...")
        max_retries = 5
        retry_delay = 3
        
        for attempt in range(max_retries):
            try:
                await asyncio.sleep(retry_delay)  # Wait before retry
                
                logger.info(f"Reconnection attempt {attempt + 1}/{max_retries}")
                
                # Close existing connection if any
                if self.websocket:
                    try:
                        await self.websocket.close()
                    except:
                        pass
                
                # Create new connection
                self.websocket = await websockets.connect(
                    self.mcp_server_url,
                    ping_interval=20,  # More frequent pings during long operations
                    ping_timeout=15    # Longer timeout for ping responses
                )
                
                # Re-register with MCP server
                await self._register_with_mcp_server()
                
                # Restart message handler
                asyncio.create_task(self._handle_mcp_messages())
                
                self.mcp_connected = True
                logger.info("✅ Successfully reconnected to MCP server")
                
                # Update integrations with new websocket
                if self.ai_integration:
                    self.ai_integration.websocket = self.websocket
                if self.database_integration:
                    self.database_integration.websocket = self.websocket
                
                return
                
            except Exception as e:
                logger.warning(f"Reconnection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    retry_delay = min(retry_delay * 2, 30)  # Exponential backoff, max 30s
                else:
                    logger.error("❌ Failed to reconnect to MCP server after all attempts")
                    self.mcp_connected = False
    
    async def _ensure_mcp_connection(self) -> bool:
        """Ensure MCP connection is active, reconnect if necessary."""
        if self.mcp_connected and self.websocket and not self.websocket.closed:
            return True
            
        logger.info("MCP connection not active, attempting to reconnect...")
        await self._reconnect_to_mcp_server()
        return self.mcp_connected
    
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
            if action == "search_literature":
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
    
        
    async def _handle_search_literature(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle literature search request."""
        try:
            # Parse search parameters
            lit_review_id = payload.get("lit_review_id", str(uuid.uuid4()))
            plan_id = payload.get("plan_id", "")
            research_plan = payload.get("research_plan", "")
            filters = payload.get("filters", {})
            sources = payload.get("sources", ["core", "arxiv", "crossref", "semantic_scholar", "pubmed"])
            max_results = payload.get("max_results", 50)

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
        errors = []
        
        # Search each configured source with all terms
        sources = search_query.sources or ["semantic_scholar", "arxiv", "pubmed", "crossref", "core", "openalex"]

        logger.info(f"Starting literature search for review {search_query.lit_review_id}")
        
        # Extract AI-optimized search terms if research plan is available
        search_terms = await self._get_or_extract_search_terms(search_query, sources)
        logger.info(f"🔍 DEBUG: _get_or_extract_search_terms returned {len(search_terms)} terms:")
        for i, term in enumerate(search_terms):
            logger.info(f"🔍 DEBUG: Term {i+1}: '{term}' (type: {type(term)}, length: {len(str(term))})")
        
        # Additional safety check: ensure no terms contain OR combinations
        final_terms = []
        for term in search_terms:
            if " OR " in str(term):
                logger.warning(f"Found OR combination in term, splitting: '{term}'")
                split_terms = [t.strip() for t in str(term).split(" OR ") if t.strip()]
                final_terms.extend(split_terms)
            else:
                final_terms.append(term)
        
        if len(final_terms) != len(search_terms):
            logger.info(f"Split OR-combined terms: {len(search_terms)} -> {len(final_terms)} individual terms")
        
        search_query.query = final_terms  # Pass as list for individual ranking
        logger.info(f"🔍 DEBUG: search_query.query now contains {len(search_query.query)} items:")
        for i, item in enumerate(search_query.query):
            logger.info(f"🔍 DEBUG: Item {i+1}: '{item}' (type: {type(item)}, length: {len(str(item))})")

        # Main search loop via pipeline
        search_results = await self.search_pipeline.search_source(search_query)

        # AI review of results
        literature_list = await self._review_with_ai(search_query, search_results)

        # Store results in database
        await self._store_literature_results(search_query, literature_list, errors)
        
        end_time = datetime.now()
        
        # Create search report with actual metrics
        search_report = SearchReport(
            lit_review_id=search_query.lit_review_id,
            total_fetched=len(search_results) if search_results else 0,
            total_unique=len(literature_list),
            per_source_counts={},  # TODO: Implement if needed by pipeline
            start_time=start_time,
            end_time=end_time,
            errors=errors,
            records=literature_list
        )
        
        logger.info(f"Literature search completed. Found {len(search_results) if search_results else 0} results, "
                   f"{len(literature_list)} after AI review in {(end_time - start_time).total_seconds():.1f}s")

        return search_report
    
    async def _get_or_extract_search_terms(self, search_query: SearchQuery, sources: List[str]) -> List[str]:
        """Extract or retrieve cached search terms for the research plan."""
        if not (search_query.research_plan and self.database_integration and self.ai_integration):
            logger.info("No research plan provided, using original query")
            if isinstance(search_query.query, list):
                return search_query.query
            else:
                return [search_query.query or "general research"]
            
        # Check for cached terms first
        cached_terms = await self.database_integration.get_cached_search_terms(
            "plan", search_query.plan_id, str(search_query.research_plan)[:500]
        )
        if cached_terms:
            logger.info(f"Using {len(cached_terms)} cached search terms: {cached_terms}")
            logger.info(f"🔍 DEBUG: Examining each cached term:")
            for i, term in enumerate(cached_terms):
                logger.info(f"🔍 DEBUG: Cached term {i+1}: '{term}' (type: {type(term)}, length: {len(str(term))})")
                if " OR " in str(term):
                    logger.info(f"🔍 DEBUG: Term {i+1} contains OR - this is a combined query!")
            
            # Handle legacy cached terms that might contain OR-combined queries
            expanded_terms = []
            for term in cached_terms:
                if " OR " in term:
                    # Split combined OR query back into individual terms
                    individual_terms = [t.strip() for t in term.split(" OR ")]
                    expanded_terms.extend(individual_terms)
                    logger.info(f"Split legacy OR query into {len(individual_terms)} individual terms")
                else:
                    expanded_terms.append(term)
            
            logger.info(f"🔍 DEBUG: After processing, returning {len(expanded_terms)} terms:")
            for i, term in enumerate(expanded_terms):
                logger.info(f"🔍 DEBUG: Final term {i+1}: '{term}' (length: {len(str(term))})")
            return expanded_terms
            
        # Extract new terms using AI
        logger.info("Research plan provided, extracting AI-optimized search terms")
        ai_extracted_terms = await self.ai_integration.extract_search_terms_from_research_plan(
            search_query.research_plan
        )
        
        if ai_extracted_terms and isinstance(ai_extracted_terms, list):
            search_terms = ai_extracted_terms
            logger.info(f"Extracted {len(search_terms)} search terms from AI response: {search_terms}")
            
            # Store terms for future use
            try:
                storage_result = await self.database_integration.store_search_terms(
                    "plan", 
                    search_query.plan_id, 
                    str(search_query.research_plan)[:500],
                    search_terms, 
                    {"ai_model": "gpt-4o-mini", "extraction_method": "topic_based_json"}, 
                    sources
                )
                if storage_result:
                    logger.info(f"Successfully stored {len(search_terms)} search terms in database")
                else:
                    logger.warning("Failed to store search terms in database")
            except Exception as e:
                logger.error(f"Exception while storing search terms: {e}", exc_info=True)
                
            return search_terms
        else:
            logger.warning("No valid search terms returned from AI, using fallback")
            if isinstance(search_query.query, list):
                return search_query.query
            else:
                return [search_query.query or "general research"]
    
    async def _review_with_ai(self, search_query: SearchQuery, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Review search results with AI agent and return filtered list."""
        if search_results and self.ai_integration:
            logger.info(f"Reviewing {len(search_results)} search results with AI agent")
            literature_list = await self.ai_integration.review_literature_results(
                plan=search_query.research_plan,
                search_results=search_results
            )
            if not literature_list:
                logger.warning("AI review returned no results, using original search results")
                return search_results
            return literature_list
        else:
            logger.info("No AI integration available or no search results, using original search results")
            return search_results or []
    
    async def _store_literature_results(self, search_query: SearchQuery, literature_list: List[Dict[str, Any]], errors: List[str]):
        """Store literature results in database with retry logic."""
        if not (literature_list and search_query.lit_review_id and self.database_integration):
            missing_conditions = []
            if not literature_list:
                missing_conditions.append("no literature_list")
            if not search_query.lit_review_id:
                missing_conditions.append("no lit_review_id")
            if not self.database_integration:
                missing_conditions.append("no database_integration")
            logger.warning(f"❌ Skipping literature storage due to: {', '.join(missing_conditions)}")
            return
            
        logger.info(f"✅ Storing {len(literature_list)} reviewed literature results in database")
        
        # Ensure MCP connection is active
        connection_ready = await self._ensure_mcp_connection()
        if not connection_ready:
            error_msg = "Failed to establish MCP connection for database storage"
            logger.error(f"❌ {error_msg}")
            errors.append(error_msg)
            return
        
        # Retry storage operation
        max_storage_retries = 3
        for storage_attempt in range(max_storage_retries):
            try:
                logger.info(f"📤 Database storage attempt {storage_attempt + 1}/{max_storage_retries}")
                success = await self.database_integration.store_reviewed_literature_results(
                    plan_id=search_query.plan_id, 
                    reviewed_results=literature_list
                )
                
                if success:
                    logger.info(f"🎉 REVIEWED LITERATURE JSON STORED: {len(literature_list)} records")
                    await self._store_full_records(search_query, literature_list, errors)
                    return
                else:
                    logger.warning(f"⚠️ Storage attempt {storage_attempt + 1} failed, retrying...")
                    if storage_attempt < max_storage_retries - 1:
                        await asyncio.sleep(2)
                        await self._ensure_mcp_connection()
                        
            except Exception as storage_error:
                logger.error(f"❌ Storage attempt {storage_attempt + 1} failed with exception: {storage_error}")
                if storage_attempt < max_storage_retries - 1:
                    await asyncio.sleep(2)
                    await self._ensure_mcp_connection()
        
        error_msg = f"Failed to store reviewed literature results after {max_storage_retries} attempts"
        logger.error(f"❌ {error_msg}")
        errors.append(error_msg)
    
    async def _store_full_records(self, search_query: SearchQuery, literature_list: List[Dict[str, Any]], errors: List[str]):
        """Store full literature records."""
        if not (literature_list and self.database_integration):
            logger.warning("❌ Skipping full record storage: missing literature_list or database_integration")
            return

        logger.info(f"🔄 Storing {len(literature_list)} full literature records")
        
        try:
            literature_storage_errors = await self.database_integration.store_literature_records(
                records=literature_list, 
                search_query=search_query
            )
            if literature_storage_errors:
                logger.error(f"❌ Errors storing full literature records: {literature_storage_errors}")
                errors.extend(literature_storage_errors)
            else:
                logger.info(f"🎉 FULL LITERATURE RECORDS STORED: {len(literature_list)} complete records")
        except Exception as e:
            error_msg = f"Failed to store full literature records: {e}"
            logger.error(f"❌ {error_msg}")
            errors.append(error_msg)
    
    def _normalize_title(self, title: str) -> str:
        """
        Normalize a title for better matching by removing common formatting differences.
        
        Args:
            title: The title to normalize
            
        Returns:
            Normalized title for matching
        """
        if not title:
            return ""
        
        # Convert to lowercase and strip whitespace
        normalized = title.lower().strip()
        
        # Remove common punctuation and extra spaces
        normalized = re.sub(r'[^\w\s]', ' ', normalized)  # Replace punctuation with spaces
        normalized = re.sub(r'\s+', ' ', normalized)      # Collapse multiple spaces
        normalized = normalized.strip()
        
        return normalized
    
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


