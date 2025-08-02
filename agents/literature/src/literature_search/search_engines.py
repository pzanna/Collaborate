"""
Search engine implementations for various academic databases.
"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import aiohttp

from .models import SearchQuery
from .parsers import ArxivParser, PubmedParser

logger = logging.getLogger(__name__)


class SearchEngines:
    """Collection of search engine implementations for academic databases."""
    
    def __init__(self, session: aiohttp.ClientSession, core_api_key: Optional[str] = None):
        """Initialize search engines with HTTP session and configuration."""
        self.session = session
        self.core_api_key = core_api_key
        
        # Initialize parsers
        self.arxiv_parser = ArxivParser()
        self.pubmed_parser = PubmedParser()
        
        # API configurations
        self.api_configs = {
            'semantic_scholar': {
                'base_url': 'https://api.semanticscholar.org/graph/v1/paper/search',
                'rate_limit': 5,  # seconds between requests
                'max_results_per_request': 100
            },
            'pubmed': {
                'base_url': 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils',
                'rate_limit': 2,  # NCBI rate limit (1 requests per second)
                'max_results_per_request': 100
            },
            'arxiv': {
                'base_url': 'http://export.arxiv.org/api/query',
                'rate_limit': 5,  # arXiv rate limit recommendation
                'max_results_per_request': 100
            },
            'crossref': {
                'base_url': 'https://api.crossref.org/works',
                'rate_limit': 2,  # CrossRef rate limit
                'max_results_per_request': 100
            },
            'core': {
                'base_url': 'https://api.core.ac.uk/v3/search/works',
                'rate_limit': 2, # CORE API rate limit
                'max_results_per_request': 100
            }
        }
    
    def _clean_xml_content(self, xml_content: str) -> str:
        """
        Clean XML content by removing tags and normalizing whitespace.
        
        Args:
            xml_content: Raw XML content that may contain tags
            
        Returns:
            Cleaned text content
        """
        if not xml_content or not isinstance(xml_content, str):
            return ""
        
        # 1) Remove title tags and their content (e.g. <jats:title>…</jats:title>)
        no_titles = re.sub(
            r'<\s*[^>]*title[^>]*>.*?</\s*[^>]*title[^>]*>',
            '',
            xml_content,
            flags=re.IGNORECASE | re.DOTALL
        )

        # 2) Remove any other tags
        no_tags = re.sub(r'<[^>]+>', '', no_titles)

        # 3) Collapse whitespace and trim
        return ' '.join(no_tags.split()).strip()
    
    async def search_semantic_scholar(self, search_query: SearchQuery) -> List[Dict[str, Any]]:
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
            }
            
            # Compose the full URL with query parameters for logging/debugging
            full_url = f"{url}?{urlencode(params)}"
            logger.info(f"Semantic Scholar full request URL: {full_url}")

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
    
    async def search_arxiv(self, search_query: SearchQuery) -> List[Dict[str, Any]]:
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

            full_url = f"{url}?{urlencode(params)}"
            logger.info(f"arXiv full request URL: {full_url}")

            # Rate limiting
            await asyncio.sleep(config['rate_limit'])
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    xml_content = await response.text()
                    return self.arxiv_parser.parse_xml(xml_content)
                else:
                    logger.warning(f"arXiv API returned status {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error searching arXiv: {e}")
            return []
    
    async def search_pubmed(self, search_query: SearchQuery) -> List[Dict[str, Any]]:
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

            full_url = f"{search_url}?{urlencode(search_params)}"
            logger.info(f"PubMed full request URL: {full_url}")

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
                    return self.pubmed_parser.parse_xml(xml_content)
                else:
                    logger.warning(f"PubMed fetch returned status {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error searching PubMed: {e}")
            return []
    
    async def search_crossref(self, search_query: SearchQuery) -> List[Dict[str, Any]]:
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
            
            full_url = f"{url}?{urlencode(params)}"
            logger.info(f"CrossRef full request URL: {full_url}")

            # Rate limiting
            await asyncio.sleep(config['rate_limit'])
            
            headers = {
                'User-Agent': 'Eunice-Research-Platform/1.0 (mailto:contact@eunice.example.com)',
                'Accept': 'application/json'
            }
            
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get('message', {}).get('items', [])
                    
                    # Clean XML content from abstracts in CrossRef results
                    for item in items:
                        if 'abstract' in item and item['abstract']:
                            item['abstract'] = self._clean_xml_content(item['abstract'])
                    
                    return items
                else:
                    logger.warning(f"CrossRef API returned status {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error searching CrossRef: {e}")
            return []
    
    async def search_core(self, search_query: SearchQuery) -> List[Dict[str, Any]]:
        """Search CORE API."""
        try:
            if not self.session:
                logger.error("HTTP session not initialized")
                return []
                
            config = self.api_configs['core']
            url = config['base_url']
            
            params = {
                'q': search_query.query,
                'limit': min(search_query.max_results, config['max_results_per_request']),
                'citationCount': '>0', # Filter for articles with citations
            }
            
            # Compose the full URL with query parameters for logging/debugging
            full_url = f"{url}?{urlencode(params)}"
            logger.info(f"CORE full request URL: {full_url}")

            headers = {}
            if self.core_api_key:
                headers['Authorization'] = f'Bearer {self.core_api_key}'

            # Rate limiting
            await asyncio.sleep(config['rate_limit'])
            
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('results', [])
                else:
                    logger.warning(f"CORE API returned status {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error searching CORE: {e}")
            return []
    
    async def search_source(self, source: str, search_query: SearchQuery) -> List[Dict[str, Any]]:
        """Search a specific source."""
        try:
            if source == "semantic_scholar":
                return await self.search_semantic_scholar(search_query)
            elif source == "arxiv":
                return await self.search_arxiv(search_query)
            elif source == "pubmed":
                return await self.search_pubmed(search_query)
            elif source == "crossref":
                return await self.search_crossref(search_query)
            elif source == "core":
                return await self.search_core(search_query)
            else:
                logger.warning(f"Unsupported source: {source}")
                return []
                
        except Exception as e:
            logger.error(f"Error searching {source}: {e}")
            return []
