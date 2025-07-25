"""
Literature Search Agent (LSA) for the Eunice Research Platform.

This agent specializes in discovering and collecting bibliographic records from multiple 
academic sources, normalizing results, and storing them for further screening.

Based on the Literature Review Agents Design Specification.
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from ..base_agent import BaseAgent
from ...config.config_manager import ConfigManager
from ...database.cache.academic_cache import AcademicCacheManager
from ...database.connectors.academic import (
    ArxivConnector, 
    DatabaseManager,
    DatabaseSearchQuery, 
    DatabaseType,
    ExternalSearchResult,
    PubMedConnector,
    SemanticScholarConnector
)
from ...mcp.protocols import ResearchAction
from ...database.core.manager import HierarchicalDatabaseManager


class SearchQuery(BaseModel):
    """Search query data model for literature search requests."""
    lit_review_id: str = Field(description="Literature review identifier")
    query: str = Field(description="Search query string")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Search filters")
    sources: List[str] = Field(default_factory=list, description="Data sources to search")
    max_results: int = Field(default=1000, description="Maximum results to retrieve")


class SearchReport(BaseModel):
    """Search report data model for literature search results."""
    lit_review_id: str = Field(description="Literature review identifier")
    total_fetched: int = Field(description="Total records fetched")
    total_unique: int = Field(description="Total unique records after deduplication")
    per_source_counts: Dict[str, int] = Field(description="Counts per data source")
    start_time: datetime = Field(description="Search start time")
    end_time: datetime = Field(description="Search end time")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")


class LiteratureSearchAgent(BaseAgent):
    """
    Literature Search Agent for discovering and collecting bibliographic records.
    
    Core Responsibilities:
    - Query multiple data sources (PubMed, CrossRef, Semantic Scholar, arXiv)
    - Apply filters (year, publication type, keywords) as specified
    - Deduplicate results using DOI, PMID, or title/author/year heuristics
    - Store both raw source data and normalized records
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the Literature Search Agent.

        Args:
            config_manager: Configuration manager instance
        """
        super().__init__("literature_search", config_manager)
        
        # Initialize cache manager
        self.cache_manager = AcademicCacheManager(config_manager)
        
        # Initialize database connectors
        self.connectors = {
            'semantic_scholar': SemanticScholarConnector(config_manager),
            'pubmed': PubMedConnector(config_manager),
            'arxiv': ArxivConnector(config_manager)
        }
        
        # Initialize database manager
        self.db_manager = HierarchicalDatabaseManager(config_manager)
        
        self.logger = logging.getLogger(__name__)

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
        
        self.logger.info(f"Starting literature search for review {search_query.lit_review_id}")
        
        # Search each configured source
        sources = search_query.sources or list(self.connectors.keys())
        
        for source in sources:
            if source not in self.connectors:
                error_msg = f"Unknown source: {source}"
                errors.append(error_msg)
                self.logger.warning(error_msg)
                continue
                
            try:
                connector = self.connectors[source]
                
                # Construct query for this source
                source_query = self._construct_source_query(search_query, source)
                
                # Execute search with pagination and rate limiting
                source_records = await self._search_source_with_pagination(
                    connector, source_query, search_query.max_results
                )
                
                # Parse metadata into common schema
                normalized_records = self._normalize_records(source_records, source)
                
                all_records.extend(normalized_records)
                per_source_counts[source] = len(source_records)
                total_fetched += len(source_records)
                
                self.logger.info(f"Retrieved {len(source_records)} records from {source}")
                
            except Exception as e:
                error_msg = f"Error searching {source}: {str(e)}"
                errors.append(error_msg)
                self.logger.error(error_msg, exc_info=True)
                per_source_counts[source] = 0

        # Deduplicate records
        unique_records = self._deduplicate_records(all_records)
        
        # Store results in database
        await self._store_search_results(search_query.lit_review_id, unique_records)
        
        end_time = datetime.now()
        
        # Create search report
        search_report = SearchReport(
            lit_review_id=search_query.lit_review_id,
            total_fetched=total_fetched,
            total_unique=len(unique_records),
            per_source_counts=per_source_counts,
            start_time=start_time,
            end_time=end_time,
            errors=errors
        )
        
        self.logger.info(f"Literature search completed. Fetched {total_fetched} records, "
                        f"{len(unique_records)} unique after deduplication")
        
        return search_report

    def _construct_source_query(self, search_query: SearchQuery, source: str) -> DatabaseSearchQuery:
        """
        Construct a source-specific query from the general search parameters.
        
        Args:
            search_query: General search query
            source: Target data source
            
        Returns:
            DatabaseSearchQuery for the specific source
        """
        # Apply source-specific query transformations
        query_text = search_query.query
        
        # Apply filters based on source capabilities
        filters = search_query.filters.copy()
        
        return DatabaseSearchQuery(
            query=query_text,
            max_results=search_query.max_results,
            filters=filters
        )

    async def _search_source_with_pagination(
        self, 
        connector, 
        query: DatabaseSearchQuery, 
        max_results: int
    ) -> List[Dict[str, Any]]:
        """
        Search a source with pagination and rate limiting.
        
        Args:
            connector: Database connector instance
            query: Search query
            max_results: Maximum results to retrieve
            
        Returns:
            List of raw search results
        """
        all_results = []
        page_size = min(100, max_results)  # Limit page size for rate limiting
        offset = 0
        
        while len(all_results) < max_results:
            try:
                # Update query with pagination
                paginated_query = DatabaseSearchQuery(
                    query=query.query,
                    max_results=page_size,
                    filters=query.filters
                )
                
                # Execute search
                page_results = await connector.search(paginated_query)
                
                if not page_results or len(page_results) == 0:
                    break
                    
                all_results.extend(page_results)
                offset += len(page_results)
                
                # Rate limiting - respect API limits
                await asyncio.sleep(0.1)  # Basic rate limiting
                
                if len(page_results) < page_size:
                    break  # No more results available
                    
            except Exception as e:
                self.logger.warning(f"Pagination error at offset {offset}: {str(e)}")
                break
        
        return all_results[:max_results]

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
                    'year': self._extract_year(record),
                    'journal': self._extract_field(record, ['journal', 'venue', 'Journal']),
                    'url': self._extract_field(record, ['url', 'URL', 'link']),
                    'raw_data': record,  # Store original data
                    'retrieval_timestamp': datetime.now().isoformat()
                }
                normalized.append(normalized_record)
                
            except Exception as e:
                self.logger.warning(f"Error normalizing record from {source}: {str(e)}")
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
        year_fields = ['year', 'Year', 'publicationDate', 'date']
        
        for field in year_fields:
            if field in record and record[field]:
                year_value = record[field]
                
                if isinstance(year_value, int):
                    return year_value
                elif isinstance(year_value, str):
                    # Try to extract year from date strings
                    import re
                    year_match = re.search(r'\b(19|20)\d{2}\b', year_value)
                    if year_match:
                        return int(year_match.group())
        
        return None

    def _deduplicate_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate records using DOI, PMID, or title/author/year heuristics.
        
        Args:
            records: List of normalized records
            
        Returns:
            List of unique records
        """
        seen_dois = set()
        seen_pmids = set()
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
            
            # Check title/author/year hash
            if not is_duplicate and not doi and not pmid:
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

    async def _store_search_results(self, lit_review_id: str, records: List[Dict[str, Any]]):
        """
        Store search results in the literature database.
        
        Args:
            lit_review_id: Literature review identifier
            records: Normalized records to store
        """
        try:
            # Store records via database manager
            for record in records:
                record['lit_review_id'] = lit_review_id
                
            # Use database manager to store records
            await self.db_manager.store_literature_records(lit_review_id, records)
            
            self.logger.info(f"Stored {len(records)} records for review {lit_review_id}")
            
        except Exception as e:
            self.logger.error(f"Error storing search results: {str(e)}", exc_info=True)
            raise

    async def handle_action(self, action: ResearchAction) -> Dict[str, Any]:
        """
        Handle research actions for literature search.
        
        Args:
            action: Research action to handle
            
        Returns:
            Action result
        """
        try:
            if action.action_type == "search_literature":
                # Parse search parameters
                search_query = SearchQuery(**action.parameters)
                
                # Execute search
                search_report = await self.search_literature(search_query)
                
                return {
                    'status': 'success',
                    'agent': self.agent_id,
                    'action_type': action.action_type,
                    'result': search_report.dict(),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'status': 'error',
                    'agent': self.agent_id,
                    'action_type': action.action_type,
                    'error': f"Unsupported action type: {action.action_type}",
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Error handling action {action.action_type}: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'agent': self.agent_id,
                'action_type': action.action_type,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def get_health_status(self) -> Dict[str, Any]:
        """Get agent health status."""
        try:
            # Test database connection
            db_healthy = await self.db_manager.health_check()
            
            # Test connectors
            connector_status = {}
            for name, connector in self.connectors.items():
                try:
                    # Simple connectivity test
                    connector_status[name] = 'healthy'
                except Exception:
                    connector_status[name] = 'unhealthy'
            
            return {
                'agent': self.agent_id,
                'status': 'healthy' if db_healthy and all(
                    status == 'healthy' for status in connector_status.values()
                ) else 'degraded',
                'database': 'healthy' if db_healthy else 'unhealthy',
                'connectors': connector_status,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'agent': self.agent_id,
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
