"""
Internet Search Agent (Literature) for research tasks.

This module provides the LiteratureAgent that handles internet search
and information retrieval tasks for the Eunice research platform.
"""

import asyncio
import logging
import os
from typing import Dict, List, Any, Optional, Union
from urllib.parse import quote_plus, urljoin
from datetime import datetime, timedelta

from .base_agent import BaseAgent, AgentStatus
from ..mcp.protocols import ResearchAction
from ..config.config_manager import ConfigManager
from ..utils.error_handler import ErrorHandler
from ..external.database_connectors import (
    DatabaseConnector, PubMedConnector, ArxivConnector, SemanticScholarConnector, DatabaseSearchQuery,
    DatabaseType, ExternalSearchResult, DatabaseManager
)
from ..external.academic_cache import AcademicCacheManager


class LiteratureAgent(BaseAgent):
    """
    Literature Agent for web search and information retrieval.
    
    This agent specializes in finding academic papers, research documents,
    and literature sources from the internet. It provides comprehensive
    search capabilities across multiple engines and academic databases.
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the Literature Agent.
        
        Args:
            config_manager: Configuration manager instance
        """
        super().__init__("literature", config_manager)
        
        # Initialize cache manager
        self.cache_manager = AcademicCacheManager(config_manager)
        
        # Initialize database manager
        self.db_manager = DatabaseManager()
        
        # Initialize database connectors
        self._init_database_connectors()
        
        # Academic search settings (no direct external connections)
        self.max_results_per_search = 10
        self.max_pages_per_result = 3
        self.request_timeout = 30
        
        # Search and caching settings
        self.enable_caching = True
        self.cache_duration = timedelta(hours=24)
        self.max_concurrent_searches = 3
        
        # SSL configuration for API connections
        self.verify_ssl = True  # Can be set to False for development environments with cert issues
        try:
            # Check if SSL verification should be disabled via config
            self.verify_ssl = config_manager.get('ssl_verification', True)
        except (AttributeError, ValueError):
            # Default to True if config doesn't specify
            self.verify_ssl = True
        
        # Content filtering
        self.min_content_length = 100
        self.max_content_length = 10000
        self.relevance_threshold = 0.3
        
        # Set up dedicated literature logging
        self._setup_literature_logging()
        
        self.logger.info("LiteratureAgent initialized")

    def _setup_literature_logging(self) -> None:
        """Set up dedicated logging for Literature Agent activities."""
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(os.getcwd(), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Create literature-specific logger
        self.literature_logger = logging.getLogger('literature_agent')
        self.literature_logger.setLevel(logging.INFO)
        
        # Avoid duplicate handlers
        if not self.literature_logger.handlers:
            # Create file handler for literature.log
            literature_log_path = os.path.join(logs_dir, 'literature.log')
            file_handler = logging.FileHandler(literature_log_path)
            file_handler.setLevel(logging.INFO)
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            
            # Add handler to logger
            self.literature_logger.addHandler(file_handler)
        
        self.literature_logger.info("Literature Agent logging initialized")

    def _init_database_connectors(self) -> None:
        """Initialize database connectors with API keys from config."""
        try:
            # Initialize PubMed connector
            try:
                pubmed_api_key = self.config.get_api_key("pubmed") or self.config.get_api_key("ncbi")
            except ValueError:
                pubmed_api_key = None
                self.logger.debug("PubMed/NCBI API key not configured")
            
            pubmed_connector = PubMedConnector(api_key=pubmed_api_key)
            self.db_manager.add_connector(pubmed_connector)
            
            # Initialize arXiv connector
            arxiv_connector = ArxivConnector()
            self.db_manager.add_connector(arxiv_connector)
            
            # Initialize Semantic Scholar connector
            try:
                semantic_scholar_api_key = self.config.get_api_key("semantic_scholar")
            except ValueError:
                semantic_scholar_api_key = None
                self.logger.debug("Semantic Scholar API key not configured")
            
            semantic_scholar_connector = SemanticScholarConnector(api_key=semantic_scholar_api_key)
            self.db_manager.add_connector(semantic_scholar_connector)
            
            self.logger.info("Database connectors initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database connectors: {e}")

    async def search_semantic_scholar_cached(
        self, 
        query: str, 
        max_results: int = 10,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search Semantic Scholar with caching support.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            use_cache: Whether to use cached results
            
        Returns:
            List[Dict[str, Any]]: Search results in Literature Agent format
        """
        cache_key_params = {'max_results': max_results}
        
        # Check cache first
        if use_cache and self.enable_caching:
            cached_results = await self.cache_manager.get_cached_results(
                query, 'semantic_scholar', **cache_key_params
            )
            if cached_results:
                return cached_results
        
        try:
            # Create structured database query
            db_query = DatabaseSearchQuery(
                query_id=f"semantic_scholar_{datetime.now().timestamp()}",
                database_type=DatabaseType.SEMANTIC_SCHOLAR,
                search_terms=query,
                search_fields=['title', 'abstract'],
                date_range=None,
                study_types=None,
                languages=None,
                publication_status=None,
                advanced_filters=None,
                max_results=max_results,
                offset=0
            )
            
            # Execute search using database connector
            semantic_scholar_results = await self.db_manager.search_multiple_databases(
                db_query, [DatabaseType.SEMANTIC_SCHOLAR]
            )
            
            # Convert to Literature Agent format
            results = self._convert_external_results_to_literature_format(
                semantic_scholar_results.get(DatabaseType.SEMANTIC_SCHOLAR, [])
            )
            
            # Cache results if found
            if results and use_cache and self.enable_caching:
                await self.cache_manager.cache_results(
                    query, 'semantic_scholar', results, 
                    self.cache_duration, 'semantic_scholar',
                    **cache_key_params
                )
            
            self.logger.info(f"Semantic Scholar search found {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"Semantic Scholar search failed: {e}")
            return []

    async def search_pubmed_structured(
        self, 
        query: str, 
        max_results: int = 10,
        search_fields: Optional[List[str]] = None,
        date_range: Optional[Dict[str, str]] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search PubMed using structured database connector with caching.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            search_fields: Fields to search in
            date_range: Date range filter
            use_cache: Whether to use cached results
            
        Returns:
            List[Dict[str, Any]]: Search results in Literature Agent format
        """
        cache_key_params = {
            'max_results': max_results,
            'search_fields': search_fields or [],
            'date_range': date_range or {}
        }
        
        # Check cache first
        if use_cache and self.enable_caching:
            cached_results = await self.cache_manager.get_cached_results(
                query, 'pubmed_structured', **cache_key_params
            )
            if cached_results:
                return cached_results
        
        try:
            # Create structured database query
            db_query = DatabaseSearchQuery(
                query_id=f"pubmed_{datetime.now().timestamp()}",
                database_type=DatabaseType.PUBMED,
                search_terms=query,
                search_fields=search_fields or ['title', 'abstract'],
                date_range=date_range,
                study_types=None,
                languages=None,
                publication_status=None,
                advanced_filters=None,
                max_results=max_results,
                offset=0
            )
            
            # Execute search using database connector
            pubmed_results = await self.db_manager.search_multiple_databases(
                db_query, [DatabaseType.PUBMED]
            )
            
            # Convert to Literature Agent format
            results = self._convert_external_results_to_literature_format(
                pubmed_results.get(DatabaseType.PUBMED, [])
            )
            
            # Cache results
            if results and use_cache and self.enable_caching:
                await self.cache_manager.cache_results(
                    query, 'pubmed_structured', results,
                    self.cache_duration, 'pubmed',
                    **cache_key_params
                )
            
            self.logger.info(f"PubMed structured search found {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"PubMed structured search failed: {e}")
            return []

    async def search_arxiv_structured(
        self,
        query: str,
        max_results: int = 10,
        search_fields: Optional[List[str]] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search arXiv using structured database connector with caching.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            search_fields: Fields to search in
            use_cache: Whether to use cached results
            
        Returns:
            List[Dict[str, Any]]: Search results in Literature Agent format
        """
        cache_key_params = {
            'max_results': max_results,
            'search_fields': search_fields or []
        }
        
        # Check cache first
        if use_cache and self.enable_caching:
            cached_results = await self.cache_manager.get_cached_results(
                query, 'arxiv_structured', **cache_key_params
            )
            if cached_results:
                return cached_results
        
        try:
            # Create structured database query
            db_query = DatabaseSearchQuery(
                query_id=f"arxiv_{datetime.now().timestamp()}",
                database_type=DatabaseType.ARXIV,
                search_terms=query,
                search_fields=search_fields or ['title', 'abstract'],
                date_range=None,
                study_types=None,
                languages=None,
                publication_status=None,
                advanced_filters=None,
                max_results=max_results,
                offset=0
            )
            
            # Execute search using database connector
            arxiv_results = await self.db_manager.search_multiple_databases(
                db_query, [DatabaseType.ARXIV]
            )
            
            # Convert to Literature Agent format
            results = self._convert_external_results_to_literature_format(
                arxiv_results.get(DatabaseType.ARXIV, [])
            )
            
            # Cache results
            if results and use_cache and self.enable_caching:
                await self.cache_manager.cache_results(
                    query, 'arxiv_structured', results,
                    self.cache_duration, 'arxiv',
                    **cache_key_params
                )
            
            self.logger.info(f"arXiv structured search found {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"arXiv structured search failed: {e}")
            return []

    async def comprehensive_academic_search(
        self,
        query: str,
        max_results_per_source: int = 10,
        include_pubmed: bool = True,
        include_arxiv: bool = True,
        include_semantic_scholar: bool = True,
        use_cache: bool = True
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Perform comprehensive academic search across multiple databases.
        
        Args:
            query: Search query
            max_results_per_source: Max results from each source
            include_pubmed: Whether to search PubMed
            include_arxiv: Whether to search arXiv
            include_semantic_scholar: Whether to search Semantic Scholar
            use_cache: Whether to use cached results
            
        Returns:
            Dict[str, List[Dict[str, Any]]]: Results from each source
        """
        self.logger.info(f"Starting comprehensive academic search for: {query}")
        
        # Prepare search tasks
        search_tasks = []
        
        if include_pubmed:
            search_tasks.append(
                self.search_pubmed_structured(query, max_results_per_source, use_cache=use_cache)
            )
        
        if include_arxiv:
            search_tasks.append(
                self.search_arxiv_structured(query, max_results_per_source, use_cache=use_cache)
            )
        
        if include_semantic_scholar:
            search_tasks.append(
                self.search_semantic_scholar_cached(query, max_results_per_source, use_cache=use_cache)
            )
        
        # Execute searches concurrently with semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.max_concurrent_searches)
        
        async def limited_search(search_coro):
            async with semaphore:
                return await search_coro
        
        # Execute searches
        results = await asyncio.gather(
            *[limited_search(task) for task in search_tasks],
            return_exceptions=True
        )
        
        # Organize results by source
        academic_results = {}
        source_names = []
        
        if include_pubmed:
            source_names.append('pubmed')
        if include_arxiv:
            source_names.append('arxiv')
        if include_semantic_scholar:
            source_names.append('semantic_scholar')
        
        for i, result in enumerate(results):
            source_name = source_names[i] if i < len(source_names) else f'source_{i}'
            
            if isinstance(result, Exception):
                self.logger.error(f"Search failed for {source_name}: {result}")
                academic_results[source_name] = []
            else:
                academic_results[source_name] = result or []
        
        # Log summary
        total_results = sum(len(results) for results in academic_results.values())
        sources_used = [source for source, results in academic_results.items() if results]
        
        self.logger.info(
            f"Comprehensive academic search completed: {total_results} results from {len(sources_used)} sources"
        )
        
        return academic_results

    def _convert_external_results_to_literature_format(
        self, 
        external_results: List[ExternalSearchResult]
    ) -> List[Dict[str, Any]]:
        """
        Convert external database results to Literature Agent format.
        
        Args:
            external_results: List of ExternalSearchResult objects
            
        Returns:
            List[Dict[str, Any]]: Results in Literature Agent format
        """
        literature_results = []
        
        for i, result in enumerate(external_results):
            # Build content description
            content_parts = [f"Academic paper: {result.title}"]
            
            if result.authors:
                author_str = ', '.join(result.authors[:3])
                if len(result.authors) > 3:
                    author_str += ' et al.'
                content_parts.append(f"Authors: {author_str}")
            
            if result.journal:
                content_parts.append(f"Journal: {result.journal}")
            
            if result.publication_date:
                content_parts.append(f"Published: {result.publication_date.strftime('%Y-%m-%d')}")
            
            if result.citation_count:
                content_parts.append(f"Citations: {result.citation_count}")
            
            if result.abstract:
                # Add first 200 characters of abstract
                abstract_preview = result.abstract[:200] + "..." if len(result.abstract) > 200 else result.abstract
                content_parts.append(f"Abstract: {abstract_preview}")
            
            content = " | ".join(content_parts)
            
            # Determine link type and URL preference
            final_url = result.url or ""
            link_type = result.database_source.value
            
            # Prefer DOI URLs for better access
            if result.doi:
                final_url = f"https://doi.org/{result.doi}"
                link_type = "doi"
            
            # Create Literature Agent compatible result
            literature_result = {
                'title': result.title,
                'url': final_url,
                'content': content,
                'source': result.database_source.value,
                'type': 'academic_paper',
                'link_type': link_type,
                'relevance_score': len(external_results) - i,  # Simple scoring
                'metadata': {
                    'external_id': result.external_id,
                    'authors': result.authors,
                    'journal': result.journal,
                    'publication_date': result.publication_date.isoformat() if result.publication_date else None,
                    'doi': result.doi,
                    'pmid': result.pmid,
                    'keywords': result.keywords,
                    'citation_count': result.citation_count,
                    'database_source': result.database_source.value,
                    'abstract_length': len(result.abstract) if result.abstract else 0,
                    'full_text_available': result.full_text_available,
                    'confidence_score': result.confidence_score
                }
            }
            
            literature_results.append(literature_result)
        
        return literature_results

    async def deduplicate_academic_results(
        self, 
        results_by_source: Dict[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Deduplicate academic results across sources.
        
        Args:
            results_by_source: Results organized by source
            
        Returns:
            List[Dict[str, Any]]: Deduplicated results
        """
        # Flatten all results
        all_results = []
        for source, results in results_by_source.items():
            for result in results:
                result['_original_source'] = source  # Track original source
                all_results.append(result)
        
        # Deduplicate by DOI, PMID, and title similarity
        seen_dois = set()
        seen_pmids = set()
        seen_titles = set()
        unique_results = []
        
        # Sort by relevance score to prefer higher quality results
        all_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        for result in all_results:
            is_duplicate = False
            metadata = result.get('metadata', {})
            
            # Check DOI duplicates
            doi = metadata.get('doi')
            if doi and doi in seen_dois:
                is_duplicate = True
            
            # Check PMID duplicates
            pmid = metadata.get('pmid')
            if pmid and pmid in seen_pmids:
                is_duplicate = True
            
            # Check title similarity (simple approach)
            title_normalized = result.get('title', '').lower().strip()
            if title_normalized in seen_titles:
                is_duplicate = True
            
            # Add if not duplicate
            if not is_duplicate:
                unique_results.append(result)
                if doi:
                    seen_dois.add(doi)
                if pmid:
                    seen_pmids.add(pmid)
                seen_titles.add(title_normalized)
        
        self.logger.info(f"Deduplication: {len(all_results)} -> {len(unique_results)} unique results")
        return unique_results

    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics.
        
        Returns:
            Dict[str, Any]: Cache statistics
        """
        return await self.cache_manager.get_cache_stats()

    async def cleanup_cache(self) -> int:
        """
        Clean up expired cache entries.
        
        Returns:
            int: Number of entries removed
        """
        return await self.cache_manager.cleanup_expired_cache()

    async def find_related_papers(self, title: str) -> List[Dict[str, Any]]:
        """
        Find related papers in cache.
        
        Args:
            title: Paper title to find related papers for
            
        Returns:
            List[Dict[str, Any]]: Related papers
        """
        return await self.cache_manager.find_similar_papers(title)

    async def _search_academic_papers(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for academic papers using the integrated academic search capabilities.
        
        Args:
            payload: Search parameters including query, filters, etc.
            
        Returns:
            Dict[str, Any]: Search results and metadata
        """
        try:
            # Extract search parameters from payload
            query = payload.get('query', '')
            max_results = payload.get('max_results', self.max_results_per_search)
            include_pubmed = payload.get('include_pubmed', True)
            include_arxiv = payload.get('include_arxiv', True)
            include_semantic_scholar = payload.get('include_semantic_scholar', True)
            use_cache = payload.get('use_cache', True)
            deduplicate = payload.get('deduplicate', True)
            
            if not query:
                return {
                    'success': False,
                    'error': 'No search query provided',
                    'results': [],
                    'total_results': 0,
                    'sources_used': []
                }
            
            self.literature_logger.info(f"Starting academic paper search for query: {query}")
            
            # Perform comprehensive search across databases
            results_by_source = await self.comprehensive_academic_search(
                query=query,
                max_results_per_source=max_results,
                include_pubmed=include_pubmed,
                include_arxiv=include_arxiv,
                include_semantic_scholar=include_semantic_scholar,
                use_cache=use_cache
            )
            
            # Deduplicate results if requested
            if deduplicate:
                final_results = await self.deduplicate_academic_results(results_by_source)
            else:
                # Flatten results without deduplication
                final_results = []
                for source_results in results_by_source.values():
                    final_results.extend(source_results)
            
            # Sort by relevance score
            final_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            # Limit total results
            if max_results and len(final_results) > max_results:
                final_results = final_results[:max_results]
            
            # Compile search metadata
            sources_used = [source for source, results in results_by_source.items() if results]
            total_results = len(final_results)
            
            self.literature_logger.info(
                f"Academic paper search completed: {total_results} results from {len(sources_used)} sources"
            )
            
            return {
                'success': True,
                'results': final_results,
                'total_results': total_results,
                'sources_used': sources_used,
                'query': query,
                'search_metadata': {
                    'max_results_requested': max_results,
                    'deduplicated': deduplicate,
                    'cached': use_cache,
                    'results_by_source': {
                        source: len(results) for source, results in results_by_source.items()
                    }
                }
            }
            
        except Exception as e:
            self.logger.error(f"Academic paper search failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'results': [],
                'total_results': 0,
                'sources_used': []
            }



    def _get_capabilities(self) -> List[str]:
        """Get literature agent capabilities."""
        return [
            'search_academic_papers',
        ]
    
    async def _initialize_agent_specific(self) -> None:
        """Initialize literature-specific resources."""
        # Literature Agent now only uses academic connector for external access
        # No direct HTTP session needed
        self.logger.info("LiteratureAgent initialized - using academic connector for external access")

    async def _initialize_agent(self) -> None:
        """Initialize literature agent resources."""
        await self._initialize_agent_specific()

    async def _cleanup_agent_specific(self) -> None:
        """Clean up literature-specific resources."""
        try:
            # Clean up expired cache entries as part of cleanup
            if hasattr(self.cache_manager, 'cleanup_expired_cache'):
                await self.cache_manager.cleanup_expired_cache()
                
            self.logger.info("Literature-specific resources cleaned up")
        except Exception as e:
            self.logger.error(f"Error during literature-specific cleanup: {e}")
        
    async def _cleanup_agent(self) -> None:
        """Clean up literature-specific resources."""        
        self.logger.info("LiteratureAgent cleanup completed")
    
    async def _process_task_impl(self, task: ResearchAction) -> Dict[str, Any]:
        """
        Process a retrieval task.
        
        Args:
            task: Research task to process
            
        Returns:
            Dict[str, Any]: Search results and metadata
        """
        action = task.action
        payload = task.payload
        
        if action == 'search_academic_papers':
            return await self._search_academic_papers(payload)
        
        else:
            raise ValueError(f"Unknown action: {action}")
    
    