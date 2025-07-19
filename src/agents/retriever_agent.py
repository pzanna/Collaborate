"""
Internet Search Agent (Retriever) for research tasks.

This module provides the RetrieverAgent that handles internet search
and information retrieval tasks for the research system.
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, List, Any, Optional
from urllib.parse import quote_plus, urljoin
from bs4 import BeautifulSoup
import re

from .base_agent import BaseAgent, AgentStatus
from ..mcp.protocols import ResearchAction
from ..config.config_manager import ConfigManager
from ..utils.error_handler import ErrorHandler


class RetrieverAgent(BaseAgent):
    """
    Internet Search Agent for retrieving information from the web.
    
    This agent handles:
    - Web search using multiple search engines
    - Web page content extraction
    - PDF document retrieval
    - Research paper searching
    - Content filtering and relevance scoring
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the Retriever Agent.
        
        Args:
            config_manager: Configuration manager instance
        """
        super().__init__("retriever", config_manager)
        
        # Search configuration
        self.search_engines = {
            'duckduckgo': 'https://api.duckduckgo.com/',
            'searx': 'https://searx.be/search',
            'google_scholar': 'https://scholar.google.com/scholar'
        }
        
        # HTTP session for requests
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Search settings
        self.max_results_per_search = 10
        self.max_pages_per_result = 3
        self.request_timeout = 30
        self.user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        
        # Content filtering
        self.min_content_length = 100
        self.max_content_length = 10000
        self.relevance_threshold = 0.3
        
        self.logger.info("RetrieverAgent initialized")
    
    def _get_capabilities(self) -> List[str]:
        """Get retriever agent capabilities."""
        return [
            'search_information',
            'extract_web_content',
            'search_academic_papers',
            'retrieve_documents',
            'filter_results',
            'rank_relevance'
        ]
    
    async def _initialize_agent(self) -> None:
        """Initialize retriever-specific resources."""
        # Create HTTP session
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=self.request_timeout)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': self.user_agent}
        )
        
        self.logger.info("RetrieverAgent HTTP session initialized")
    
    async def _cleanup_agent(self) -> None:
        """Clean up retriever-specific resources."""
        if self.session:
            await self.session.close()
            self.session = None
        
        self.logger.info("RetrieverAgent cleanup completed")
    
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
        
        if action == 'search_information':
            return await self._search_information(payload)
        elif action == 'extract_web_content':
            return await self._extract_web_content(payload)
        elif action == 'search_academic_papers':
            return await self._search_academic_papers(payload)
        elif action == 'retrieve_documents':
            return await self._retrieve_documents(payload)
        elif action == 'filter_results':
            return await self._filter_results(payload)
        elif action == 'rank_relevance':
            return await self._rank_relevance(payload)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _search_information(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for information using multiple search engines.
        
        Args:
            payload: Search parameters
            
        Returns:
            Dict[str, Any]: Search results
        """
        query = payload.get('query', '')
        max_results = payload.get('max_results', self.max_results_per_search)
        search_engines = payload.get('search_engines', ['duckduckgo'])
        
        if not query:
            raise ValueError("Query is required for search")
        
        self.logger.info(f"Searching for: {query}")
        
        all_results = []
        
        # Search using each specified engine
        for engine in search_engines:
            try:
                results = await self._search_engine(engine, query, max_results)
                all_results.extend(results)
                self.logger.info(f"Found {len(results)} results from {engine}")
            except Exception as e:
                self.logger.error(f"Search failed for {engine}: {e}")
                continue
        
        # Remove duplicates and rank results
        unique_results = self._remove_duplicates(all_results)
        ranked_results = await self._rank_results(unique_results, query)
        
        return {
            'query': query,
            'results': ranked_results[:max_results],
            'total_found': len(unique_results),
            'search_engines_used': search_engines,
            'timestamp': asyncio.get_event_loop().time()
        }
    
    async def _search_engine(self, engine: str, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Search using a specific search engine.
        
        Args:
            engine: Search engine name
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List[Dict[str, Any]]: Search results
        """
        if engine == 'duckduckgo':
            return await self._search_duckduckgo(query, max_results)
        elif engine == 'searx':
            return await self._search_searx(query, max_results)
        elif engine == 'google_scholar':
            return await self._search_google_scholar(query, max_results)
        else:
            raise ValueError(f"Unknown search engine: {engine}")
    
    async def _search_duckduckgo(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Search using DuckDuckGo.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List[Dict[str, Any]]: Search results
        """
        try:
            if not self.session:
                raise RuntimeError("HTTP session not initialized")
                
            # DuckDuckGo Instant Answer API
            url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1&skip_disambig=1"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"DuckDuckGo API returned status {response.status}")
                
                content_type = response.headers.get('content-type', '').lower()
                if 'application/json' not in content_type:
                    # DuckDuckGo is returning non-JSON content, fall back to web search
                    self.logger.warning(f"DuckDuckGo returned unexpected content type: {content_type}")
                    return await self._search_web_fallback(query, max_results)
                
                try:
                    data = await response.json()
                except Exception as json_error:
                    self.logger.error(f"Failed to parse JSON from DuckDuckGo: {json_error}")
                    return await self._search_web_fallback(query, max_results)
                
                results = []
                
                # Extract instant answer
                if data.get('Answer'):
                    results.append({
                        'title': 'DuckDuckGo Instant Answer',
                        'url': data.get('AnswerURL', ''),
                        'content': data.get('Answer', ''),
                        'source': 'duckduckgo',
                        'type': 'instant_answer'
                    })
                
                # Extract related topics
                for topic in data.get('RelatedTopics', [])[:max_results]:
                    if isinstance(topic, dict) and 'Text' in topic:
                        results.append({
                            'title': topic.get('Text', '').split(' - ')[0],
                            'url': topic.get('FirstURL', ''),
                            'content': topic.get('Text', ''),
                            'source': 'duckduckgo',
                            'type': 'related_topic'
                        })
                
                # If no instant results, fall back to web search
                if not results:
                    results = await self._search_web_fallback(query, max_results)
                
                return results[:max_results]
                
        except Exception as e:
            self.logger.error(f"DuckDuckGo search failed: {e}")
            return []
    
    async def _search_web_fallback(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Fallback search when external search fails.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List[Dict[str, Any]]: Empty results list
        """
        self.logger.warning(f"Search fallback triggered for query: {query}")
        return []

    async def _search_searx(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Search using SearX.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List[Dict[str, Any]]: Search results
        """
        try:
            if not self.session:
                raise RuntimeError("HTTP session not initialized")
                
            url = f"https://searx.be/search?q={quote_plus(query)}&format=json"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                results = []
                
                for result in data.get('results', [])[:max_results]:
                    results.append({
                        'title': result.get('title', ''),
                        'url': result.get('url', ''),
                        'content': result.get('content', ''),
                        'source': 'searx',
                        'type': 'web_result'
                    })
                
                return results
                
        except Exception as e:
            self.logger.error(f"SearX search failed: {e}")
            return []
    
    async def _search_google_scholar(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Search Google Scholar for academic papers.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List[Dict[str, Any]]: Search results
        """
        try:
            if not self.session:
                raise RuntimeError("HTTP session not initialized")
                
            # This is a simplified approach - in production, you'd use proper APIs
            url = f"https://scholar.google.com/scholar?q={quote_plus(query)}&hl=en"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                results = []
                
                # Extract academic results
                for result in soup.find_all('div', class_='gs_r')[:max_results]:
                    title_elem = result.find('h3', class_='gs_rt')
                    snippet_elem = result.find('div', class_='gs_rs')
                    
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        link = title_elem.find('a')
                        url = link.get('href', '') if link else ''
                        content = snippet_elem.get_text(strip=True) if snippet_elem else ''
                        
                        results.append({
                            'title': title,
                            'url': url,
                            'content': content,
                            'source': 'google_scholar',
                            'type': 'academic_paper'
                        })
                
                return results
                
        except Exception as e:
            self.logger.error(f"Google Scholar search failed: {e}")
            return []
    
    async def _extract_web_content(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract content from web pages.
        
        Args:
            payload: Extraction parameters
            
        Returns:
            Dict[str, Any]: Extracted content
        """
        url = payload.get('url', '')
        
        if not url:
            raise ValueError("URL is required for content extraction")
        
        try:
            if not self.session:
                raise RuntimeError("HTTP session not initialized")
                
            async with self.session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"Failed to fetch URL {url}: status {response.status}")
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract title
                title = soup.find('title')
                title_text = title.get_text(strip=True) if title else ''
                
                # Extract main content
                content = self._extract_main_content(soup)
                
                # Extract metadata
                metadata = self._extract_metadata(soup)
                
                return {
                    'url': url,
                    'title': title_text,
                    'content': content,
                    'metadata': metadata,
                    'extracted_at': asyncio.get_event_loop().time()
                }
                
        except Exception as e:
            self.logger.error(f"Content extraction failed for {url}: {e}")
            raise
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """
        Extract main content from HTML.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            str: Extracted content
        """
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()
        
        # Try to find main content areas
        main_content = None
        
        # Look for common content containers
        for selector in ['main', 'article', '.content', '.main-content', '#content']:
            element = soup.select_one(selector)
            if element:
                main_content = element
                break
        
        if not main_content:
            main_content = soup.find('body') or soup
        
        # Extract text
        text = main_content.get_text(separator=' ', strip=True)
        
        # Clean up text
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Limit content length
        if len(text) > self.max_content_length:
            text = text[:self.max_content_length] + '...'
        
        return text
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract metadata from HTML.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Dict[str, Any]: Extracted metadata
        """
        metadata = {}
        
        # Extract meta tags
        for meta in soup.find_all('meta'):
            name = meta.get('name') or meta.get('property')
            content = meta.get('content')
            
            if name and content:
                metadata[name] = content
        
        # Extract structured data
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                json_data = json.loads(script.string)
                metadata['structured_data'] = json_data
                break
            except:
                continue
        
        return metadata
    
    def _remove_duplicates(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate results.
        
        Args:
            results: List of search results
            
        Returns:
            List[Dict[str, Any]]: Unique results
        """
        seen_urls = set()
        unique_results = []
        
        for result in results:
            url = result.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)
        
        return unique_results
    
    async def _rank_results(self, results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """
        Rank search results by relevance.
        
        Args:
            results: List of search results
            query: Original search query
            
        Returns:
            List[Dict[str, Any]]: Ranked results
        """
        # Simple relevance scoring based on query terms
        query_terms = query.lower().split()
        
        for result in results:
            score = 0
            title = result.get('title', '').lower()
            content = result.get('content', '').lower()
            
            # Score based on query terms in title and content
            for term in query_terms:
                score += title.count(term) * 2  # Title matches are worth more
                score += content.count(term)
            
            # Bonus for certain result types
            if result.get('type') == 'academic_paper':
                score += 1
            elif result.get('type') == 'instant_answer':
                score += 2
            
            result['relevance_score'] = score
        
        # Sort by relevance score
        return sorted(results, key=lambda x: x.get('relevance_score', 0), reverse=True)
    
    async def _search_academic_papers(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Search for academic papers."""
        query = payload.get('query', '')
        max_results = payload.get('max_results', 10)
        
        results = await self._search_google_scholar(query, max_results)
        
        return {
            'query': query,
            'results': results,
            'total_found': len(results),
            'search_type': 'academic_papers'
        }
    
    async def _retrieve_documents(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve documents from URLs."""
        urls = payload.get('urls', [])
        
        documents = []
        for url in urls:
            try:
                doc = await self._extract_web_content({'url': url})
                documents.append(doc)
            except Exception as e:
                self.logger.error(f"Failed to retrieve {url}: {e}")
                continue
        
        return {
            'documents': documents,
            'total_retrieved': len(documents),
            'total_requested': len(urls)
        }
    
    async def _filter_results(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Filter results based on criteria."""
        results = payload.get('results', [])
        min_score = payload.get('min_relevance_score', self.relevance_threshold)
        
        filtered = [
            result for result in results
            if result.get('relevance_score', 0) >= min_score
        ]
        
        return {
            'results': filtered,
            'total_filtered': len(filtered),
            'total_original': len(results)
        }
    
    async def _rank_relevance(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Rank results by relevance."""
        results = payload.get('results', [])
        query = payload.get('query', '')
        
        ranked = await self._rank_results(results, query)
        
        return {
            'results': ranked,
            'query': query,
            'ranking_method': 'term_frequency'
        }
