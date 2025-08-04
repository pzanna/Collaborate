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
import numpy as np
import pandas as pd

import onnxruntime as ort
from transformers import AutoTokenizer
from sentence_transformers import SentenceTransformer, util

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
        
        # Filter out records with empty abstracts
        # This ensures we only keep literature with meaningful content for review
        records_with_abstracts = self.deduplicator.filter_records_with_abstracts(unique_records)
        
        # Create simplified JSON records with only id, title, and abstract
        # This is done BEFORE storing in the database as per the workflow requirements
        simplified_json_records = self._create_simplified_json_records(records_with_abstracts)
        
        # Store initial literature results in research plan (before AI review)
        logger.info(f"📊 INITIAL LITERATURE STORAGE CHECK:")
        logger.info(f"  ├─ full_records_with_abstracts: {len(records_with_abstracts)} records")
        logger.info(f"  ├─ simplified_json_records: {len(simplified_json_records)} records")
        logger.info(f"  ├─ plan_id: {search_query.plan_id}")
        logger.info(f"  ├─ lit_review_id: {search_query.lit_review_id}")
        logger.info(f"  └─ database_integration: {'✅ Available' if self.database_integration else '❌ None'}")
        
        if search_query.plan_id and search_query.lit_review_id and self.database_integration and simplified_json_records:
            logger.info(f"📤 STORING INITIAL LITERATURE RESULTS: {len(simplified_json_records)} simplified JSON records → plan_id={search_query.plan_id}")
            try:
                initial_storage_success = await self.database_integration.store_initial_literature_results(
                    lit_review_id=search_query.lit_review_id,
                    plan_id=search_query.plan_id,
                    records=simplified_json_records  # Store simplified JSON instead of full records
                )
                if initial_storage_success:
                    logger.info(f"🎉 INITIAL LITERATURE JSON STORED: {len(simplified_json_records)} simplified records in research_plans.initial_literature_results")
                else:
                    logger.error("💥 INITIAL LITERATURE STORAGE FAILED: store_initial_literature_results returned False")
                    errors.append("Failed to store initial literature results")
            except Exception as e:
                logger.error(f"💥 INITIAL LITERATURE STORAGE EXCEPTION: {type(e).__name__}: {e}")
                logger.error(f"   └─ Failed to store initial literature results for plan_id={search_query.plan_id}")
                errors.append(f"Exception storing initial literature results: {e}")
        else:
            missing_conditions = []
            if not search_query.plan_id:
                missing_conditions.append("no plan_id")
            if not search_query.lit_review_id:
                missing_conditions.append("no lit_review_id")
            if not self.database_integration:
                missing_conditions.append("no database_integration")
            if not simplified_json_records:
                missing_conditions.append("no simplified_json_records")
            logger.warning(f"⚠️ SKIPPING INITIAL LITERATURE STORAGE: {', '.join(missing_conditions)}")
        
        # Rank documents by similarity to averaged query vector
        # Load sentence transformer model with offline fallback
        try:
            # Load tokenizer and ONNX session
            tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
            session = ort.InferenceSession("onnx_models/model.onnx")

            def get_embedding(text: str) -> np.ndarray:
                inputs = tokenizer(text, return_tensors="np", padding=True, truncation=True)
                outputs = session.run(None, {
                    "input_ids": inputs["input_ids"],
                    "attention_mask": inputs["attention_mask"]
                })
                return np.mean(outputs[0], axis=1).squeeze()

            # Compute average embedding for all search terms
            query_embeddings = [get_embedding(term) for term in search_terms]
            avg_query_vector = np.mean(query_embeddings, axis=0)

            # Rank all documents
            ranked = []
            for doc in simplified_json_records:
                title = doc.get("title") or ""
                abstract = doc.get("abstract") or ""
                text = f"{title} {abstract}"
                doc_vector = get_embedding(text)

                # Cosine similarity
                norm_q = np.linalg.norm(avg_query_vector)
                norm_d = np.linalg.norm(doc_vector)
                score = np.dot(avg_query_vector, doc_vector) / (norm_q * norm_d + 1e-9)

                ranked.append({
                    "Relevance Score": round(float(score), 4),
                    "Title": title,
                    "Year": doc.get("year"),
                    "Abstract": abstract[:300] + "..." if len(abstract) > 300 else abstract
                })

            # Sort and return top 10
            df = pd.DataFrame(sorted(ranked, key=lambda x: x["Relevance Score"], reverse=True))
            reviewed_records = df.head(10).to_dict(orient='records')

            logger.info(f"✅ Successfully ranked {len(reviewed_records)} records using SentenceTransformer model")
            
        except Exception as model_error:
            logger.warning(f"⚠️ Failed to load SentenceTransformer model: {model_error}")
            logger.info("📄 Using fallback ranking (first 20 records without semantic scoring)")
            
            # Fallback: Use first 20 records without ranking
            reviewed_records = []
            for doc in simplified_json_records[:20]:
                title = doc.get("title") or ""
                abstract = doc.get("abstract") or ""
                reviewed_records.append({
                    "Relevance Score": "N/A (No Model)",
                    "Title": title,
                    "Year": doc.get("year"),
                    "Abstract": abstract
                })

        # Store reviewed literature results in database JSON format
        logger.info(f"Checking storage conditions:")
        logger.info(f"  - reviewed_records: {len(reviewed_records) if reviewed_records else 0} records")
        logger.info(f"  - search_query.lit_review_id: {search_query.lit_review_id}")
        logger.info(f"  - self.database_integration: {'Available' if self.database_integration else 'None'}")
        
        if reviewed_records and search_query.lit_review_id and self.database_integration:
            logger.info(f"✅ All conditions met - storing {len(reviewed_records)} reviewed literature results in database JSON format")
            success = await self.database_integration.store_reviewed_literature_results(
                plan_id = search_query.plan_id, 
                reviewed_results = reviewed_records
            )
            if not success:
                error_msg = "Failed to store reviewed literature results in JSON format"
                logger.error(f"❌ {error_msg}")
                errors.append(error_msg)
            else:
                logger.info(f"🎉 REVIEWED LITERATURE JSON STORED: {len(reviewed_records)} records in research_plans.reviewed_literature_results")
                
                # Final step: Reconcile full records with reviewed records and store in literature_records table
                # This matches the reviewed articles with their full record data for complete storage
                reviewed_ids = {record.get("id") for record in reviewed_records if record.get("id")}
                matching_full_records = [
                    record for record in records_with_abstracts 
                    if record.get("internal_id") in reviewed_ids
                ]
                
                logger.info(f"🔄 RECONCILIATION: {len(reviewed_records)} reviewed articles → {len(matching_full_records)} full records matched")
                
                if matching_full_records:
                    literature_storage_errors = await self.database_integration.store_literature_records(
                        records=matching_full_records, 
                        search_query=search_query
                    )
                    if literature_storage_errors:
                        logger.error(f"❌ Errors storing full literature records: {literature_storage_errors}")
                        errors.extend(literature_storage_errors)
                    else:
                        logger.info(f"🎉 FULL LITERATURE RECORDS STORED: {len(matching_full_records)} complete records in literature_records table")
                else:
                    logger.warning("⚠️ No matching full records found for reviewed articles")
        else:
            missing_conditions = []
            if not reviewed_records:
                missing_conditions.append("no reviewed_records")
            if not search_query.lit_review_id:
                missing_conditions.append("no lit_review_id")
            if not self.database_integration:
                missing_conditions.append("no database_integration")
            logger.warning(f"❌ Skipping literature storage due to: {', '.join(missing_conditions)}")
        
        end_time = datetime.now()
        
        # Create search report
        search_report = SearchReport(
            lit_review_id=search_query.lit_review_id,
            total_fetched=total_fetched,
            total_unique=len(records_with_abstracts),  # Updated to reflect filtering
            per_source_counts=per_source_counts,
            start_time=start_time,
            end_time=end_time,
            errors=errors,
            records=reviewed_records  # Use reviewed records instead of unique_records
        )
        
        logger.info(f"Literature search completed. Fetched {total_fetched} records, "
                   f"{len(unique_records)} unique after deduplication, "
                   f"{len(records_with_abstracts)} with abstracts, "
                   f"{len(reviewed_records)} after AI review")
        
        return search_report
    
    async def _review_and_filter_records(self, search_query: SearchQuery, unique_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Review literature results using AI and filter to most relevant articles.
        
        Args:
            search_query: The original search query containing research plan
            unique_records: List of unique deduplicated records to review
            
        Returns:
            List of filtered records based on AI review, or original records if review fails
        """
        # Default to all unique records
        reviewed_records = unique_records
        
        if not search_query.research_plan or not self.ai_integration or not unique_records:
            logger.info("Skipping AI review: missing research plan, AI integration, or no records to review")
            return reviewed_records
        
        logger.info(f"Reviewing {len(unique_records)} unique records using AI agent")
        
        try:
            reviewed_articles = await self.ai_integration.review_literature_results(
                research_plan=search_query.research_plan,
                search_results=unique_records,
                plan_id=search_query.plan_id
            )
            
            if not reviewed_articles:
                logger.warning("AI review returned no results, using all unique records")
                return reviewed_records
            
            logger.info(f"AI review completed: {len(reviewed_articles)} articles selected from {len(unique_records)} candidates")
            
            # Debug: Log a sample of what the AI returned
            if reviewed_articles:
                sample_article = reviewed_articles[0]
                logger.debug(f"Sample AI-returned article: {sample_article}")
                logger.debug(f"AI returned internal_id: {sample_article.get('id')}")
            
            # Debug: Log a sample of what we're trying to match against
            if unique_records:
                sample_record = unique_records[0]
                logger.debug(f"Sample original record IDs: internal_id={sample_record.get('internal_id')}, external_id={sample_record.get('external_id')}, doi={sample_record.get('doi')}, url={sample_record.get('url')}")
            
            # Convert reviewed articles back to the same format as unique_records
            # The AI returns articles in format [{"id": "...", "title": "...", "Abstract": "..."}]
            # where "id" is now the internal_id, and we need to find matching records from unique_records
            
            # Create lookup sets for efficient matching
            reviewed_internal_ids = set()
            reviewed_titles = set()
            
            for article in reviewed_articles:
                if article.get("id"):
                    reviewed_internal_ids.add(article.get("id"))
                if article.get("title"):
                    reviewed_titles.add(article.get("title"))
            
            # Also create normalized title lookups for better matching
            reviewed_titles_normalized = {self._normalize_title(article.get("title", "")) for article in reviewed_articles if article.get("title")}
            
            filtered_records = []
            matched_count = 0
            
            for record in unique_records:
                # Primary matching strategy: use internal_id (most reliable)
                if record.get("internal_id") and record.get("internal_id") in reviewed_internal_ids:
                    filtered_records.append(record)
                    matched_count += 1
                    continue
                
                # Fallback matching strategies for robustness
                # 2. Match by external_id (if internal_id matching fails)
                if record.get("external_id") and record.get("external_id") in reviewed_internal_ids:
                    filtered_records.append(record)
                    matched_count += 1
                    continue
                
                # 3. Match by DOI (very reliable)
                if record.get("doi") and record.get("doi") in reviewed_internal_ids:
                    filtered_records.append(record)
                    matched_count += 1
                    continue
                
                # 4. Match by URL (fairly reliable)
                if record.get("url") and record.get("url") in reviewed_internal_ids:
                    filtered_records.append(record)
                    matched_count += 1
                    continue
                
                # 5. Match by exact title (good but can have formatting issues)
                if record.get("title") and record.get("title") in reviewed_titles:
                    filtered_records.append(record)
                    matched_count += 1
                    continue
                
                # 6. Match by normalized title (handles minor formatting differences)
                normalized_record_title = self._normalize_title(record.get("title", ""))
                if normalized_record_title and normalized_record_title in reviewed_titles_normalized:
                    filtered_records.append(record)
                    matched_count += 1
                    continue
            
            logger.info(f"Record matching details: {matched_count} matches found from {len(reviewed_articles)} AI-selected articles")
            
            if filtered_records:
                reviewed_records = filtered_records
                logger.info(f"Successfully matched {len(filtered_records)} complete records from AI review")
            else:
                logger.warning("Could not match any AI-reviewed articles to original records, using all unique records")
                
        except Exception as e:
            logger.error(f"Error during AI literature review: {e}")
            logger.info("Falling back to using all unique records")
        
        return reviewed_records
    
    def _create_simplified_json_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create simplified JSON records with only id, title, and abstract fields.
        This is used for storing in the initial_literature_results column and for AI review.
        
        Args:
            records: List of full normalized records
            
        Returns:
            List of simplified records with only id, title, and abstract
        """
        # Limit to maximum of 250 records
        limited_records = records[:250]
        
        simplified_records = []
        for record in limited_records:
            simplified_record = {
                "id": record.get("internal_id"),  # Use internal_id for consistency
                "title": record.get("title", ""),
                "abstract": record.get("abstract", "")
            }
            simplified_records.append(simplified_record)
        
        if len(records) > 250:
            logger.info(f"Limited records from {len(records)} to 250 for simplified JSON creation")
        
        logger.info(f"Created {len(simplified_records)} simplified JSON records for storage/AI review")
        return simplified_records
    
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
        import re
        normalized = re.sub(r'[^\w\s]', ' ', normalized)  # Replace punctuation with spaces
        normalized = re.sub(r'\s+', ' ', normalized)      # Collapse multiple spaces
        normalized = normalized.strip()
        
        return normalized
    
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
                    max_results=max(10, search_query.max_results),
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
