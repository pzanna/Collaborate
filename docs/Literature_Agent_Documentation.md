# Literature Agent Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Functions](#core-functions)
4. [Search Engines](#search-engines)
5. [Content Extraction](#content-extraction)
6. [Usage Patterns](#usage-patterns)
7. [Configuration](#configuration)
8. [Error Handling](#error-handling)
9. [Testing](#testing)
10. [Examples](#examples)
11. [API Reference](#api-reference)

---

## Overview

The **Literature Agent** is a core component of the Eunice research system responsible for internet search and information retrieval tasks. It serves as the primary data collection engine, gathering information from multiple web sources to support research workflows within the hierarchical project structure.

### Primary Responsibilities

- **Multi-Engine Web Search**: Search across Google, Bing, Yahoo, Google Scholar, and Semantic Scholar
- **Semantic Scholar API Integration**: Enhanced academic search with official API access and automatic fallback
- **Content Extraction**: Extract and clean content from web pages with metadata parsing
- **Academic Research**: Specialized search for academic papers and scholarly content with rich metadata
- **Document Retrieval**: Batch retrieval of documents from multiple URLs with parallel processing
- **Result Filtering**: Filter results based on relevance and quality criteria
- **Relevance Ranking**: Rank search results based on query relevance using advanced algorithms
- **Research Workflows**: High-level automated workflows for common research scenarios
- **Fact Verification**: Multi-source verification with credibility analysis
- **Cost Optimization**: Budget-aware search strategies for resource management

### Key Features

- Multiple search engine support with automatic failover
- **Semantic Scholar API integration** with fallback to Google Scholar web scraping
- **Enhanced academic metadata** including citations, authors, venues, and open access PDFs
- Robust HTML parsing and content extraction with metadata parsing
- SSL/TLS support with certificate validation
- Duplicate result detection and removal
- Relevance scoring and ranking algorithms
- Async/await pattern for efficient processing
- Comprehensive error handling and graceful degradation
- **Hierarchical research structure integration**
- **Cost-aware search optimization** with budget-based strategies
- **Academic and scholarly content specialization**
- **High-level automated research workflows**
- **Multi-source fact verification capabilities**
- **Batch document processing** with parallel extraction

---

## Recent Improvements: Semantic Scholar API Integration

### Enhanced Academic Search Capabilities

The Literature Agent now features **Semantic Scholar API integration**, providing significantly improved academic research capabilities:

#### **Primary Benefits**

- **Higher Quality Results**: Direct access to Semantic Scholar's curated academic database
- **Rich Metadata**: Comprehensive paper information including citations, abstracts, authors, venues, and fields of study
- **Open Access Detection**: Automatic identification and prioritization of freely available PDFs
- **Better Performance**: API-based access is more reliable than web scraping
- **Rate Limit Management**: Optional API key support for increased rate limits

#### **Automatic Fallback System**

The system uses **Semantic Scholar API first** with intelligent fallback:

1. **Primary**: Semantic Scholar API for all academic searches
2. **Fallback**: Google Scholar web scraping if API fails or returns no results

This ensures maximum reliability while providing the best possible results.

#### **Enhanced Academic Result Structure**

```python
{
    'title': str,                    # Paper title
    'url': str,                      # Direct paper URL or open access PDF
    'content': str,                  # Rich description with metadata
    'source': 'semantic_scholar',   # Source identifier
    'type': 'academic_paper',
    'link_type': str,               # 'open_access_pdf', 'semantic_scholar', etc.
    'relevance_score': int,
    'metadata': {
        'paper_id': str,            # Semantic Scholar paper ID
        'year': int,                # Publication year
        'citation_count': int,      # Number of citations
        'authors': List[str],       # Author names
        'venue': str,               # Publication venue
        'fields_of_study': List[str], # Research fields
        'has_open_access_pdf': bool,
        'abstract_length': int
    }
}
```

#### **Configuration**

**Environment Variable** (Optional):

```bash
SEMANTIC_SCHOLAR_API_KEY=your_api_key_here
```

**Benefits of API Key**:

- Higher rate limits (1 request/second vs shared pool)
- Better performance and reliability
- Priority access during high traffic

**Get API Key**: [https://www.semanticscholar.org/product/api#api-key](https://www.semanticscholar.org/product/api#api-key)

#### **Integration Points**

The Semantic Scholar API is integrated throughout the system:

- **Academic Paper Search** (`_search_academic_papers`): Primary method for all academic searches
- **Cost-Optimized Search**: High budget searches now include Semantic Scholar
- **Comprehensive Research Pipeline**: Automatic inclusion in academic research workflows
- **Multi-Source Validation**: Academic source validation using Semantic Scholar

---

## Architecture

### Class Hierarchy

```text
BaseAgent
└── LiteratureAgent
```

### Dependencies

- **Base Agent**: Inherits core agent functionality and MCP communication
- **Config Manager**: Configuration and API key management
- **HTTP Client**: aiohttp for async web requests with SSL support
- **HTML Parser**: BeautifulSoup for HTML parsing and content extraction
- **MCP Protocols**: Research action definitions and data structures
- **SSL Context**: Secure HTTP connections with certificate validation

### Core Components

```python
class LiteratureAgent(BaseAgent):
    def __init__(self, config_manager: ConfigManager)

    # Core search capabilities
    async def _search_information(self, payload: Dict[str, Any]) -> Dict[str, Any]
    async def _search_academic_papers(self, payload: Dict[str, Any]) -> Dict[str, Any]
    async def _search_semantic_scholar(self, query: str, max_results: int) -> List[Dict[str, Any]]
    async def _search_google_scholar(self, query: str, max_results: int) -> List[Dict[str, Any]]

    # Individual search engines (internal methods)
    async def _search_google(self, query: str, max_results: int) -> List[Dict[str, Any]]
    async def _search_bing(self, query: str, max_results: int) -> List[Dict[str, Any]]
    async def _search_yahoo(self, query: str, max_results: int) -> List[Dict[str, Any]]

    # Content processing
    async def _extract_web_content(self, payload: Dict[str, Any]) -> Dict[str, Any]
    async def _retrieve_documents(self, payload: Dict[str, Any]) -> Dict[str, Any]

    # Result processing
    async def _filter_results(self, payload: Dict[str, Any]) -> Dict[str, Any]
    async def _rank_relevance(self, payload: Dict[str, Any]) -> Dict[str, Any]

    # High-level research workflow functions
    async def academic_research_workflow(self, research_topic: str, max_papers: int = 20) -> Dict[str, Any]
    async def multi_source_validation(self, claim: str) -> Dict[str, Any]
    async def cost_optimized_search(self, query: str, budget_level: str = 'medium') -> Dict[str, Any]
    async def comprehensive_research_pipeline(self, topic: str, include_academic: bool = True,
                                           include_news: bool = True, max_results: int = 10) -> Dict[str, Any]
    async def fact_verification_workflow(self, claim: str, require_academic: bool = True) -> Dict[str, Any]

    # Utility methods
    def _remove_duplicates(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]
    async def _rank_results(self, results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]
    def _extract_main_content(self, soup: BeautifulSoup) -> str
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]
```

---

## Core Functions

### 1. Information Search (`_search_information`)

**Purpose**: Search for information using multiple search engines with intelligent result aggregation.

**Input Parameters**:

```python
payload = {
    'query': str,                    # Required: Search query
    'max_results': int,              # Optional: Maximum results per engine (default: 10)
    'search_engines': List[str]      # Optional: Engines to use (default: ['google', 'bing', 'yahoo'])
}
```

**Output Structure**:

```python
{
    'query': str,                    # Original search query
    'results': List[Dict],           # Aggregated and ranked results
    'total_found': int,              # Total unique results found
    'search_engines_used': List[str], # Engines that were queried
    'timestamp': float               # Search timestamp
}
```

**Result Item Structure**:

```python
{
    'title': str,                    # Page/document title
    'url': str,                      # URL of the resource
    'content': str,                  # Brief content description
    'source': str,                   # Search engine used
    'type': str,                     # Result type ('web_result', 'academic_paper', etc.)
    'relevance_score': int           # Relevance ranking score
}
```

**Search Process**:

1. **Multi-Engine Querying**: Simultaneously searches specified engines
2. **Duplicate Removal**: Eliminates duplicate URLs across results
3. **Relevance Ranking**: Scores results based on query term frequency
4. **Result Aggregation**: Combines and limits results to requested maximum

**Use Cases**:

- General web research
- Market analysis data collection
- Technical documentation search
- News and current events research
- **Hierarchical task-specific data gathering**
- **Cost-optimized research with result limits**

### 2. Academic Paper Search (`_search_academic_papers`)

**Purpose**: Specialized search for academic papers and scholarly content using Semantic Scholar API with Google Scholar fallback.

**Input Parameters**:

```python
payload = {
    'query': str,           # Research topic or keywords
    'max_results': int      # Maximum number of papers (default: 10)
}
```

**Output Structure**:

```python
{
    'query': str,
    'results': List[Dict],           # Academic paper results
    'total_found': int,
    'search_type': 'academic_papers'
}
```

**Academic Result Structure** (Semantic Scholar):

```python
{
    'title': str,                    # Paper title
    'url': str,                      # Direct paper URL or open access PDF
    'content': str,                  # Rich description with metadata
    'source': 'semantic_scholar',   # Source identifier
    'type': 'academic_paper',
    'link_type': str,               # 'open_access_pdf', 'semantic_scholar', etc.
    'relevance_score': int,
    'metadata': {
        'paper_id': str,            # Semantic Scholar paper ID
        'year': int,                # Publication year
        'citation_count': int,      # Number of citations
        'authors': List[str],       # Author names
        'venue': str,               # Publication venue
        'fields_of_study': List[str], # Research fields
        'has_open_access_pdf': bool,
        'abstract_length': int
    }
}
```

**Academic Result Structure** (Google Scholar Fallback):

```python
{
    'title': str,                    # Paper title
    'url': str,                      # Link to paper or citation page
    'content': str,                  # "Academic paper: {title}"
    'source': 'google_scholar',
    'type': 'academic_paper',
    'relevance_score': int
}
```

**Features**:

- **Primary Semantic Scholar API integration** with enhanced metadata
- **Google Scholar fallback** for comprehensive coverage
- **Open access PDF prioritization**
- **Rich academic metadata extraction**
- **Citation count and venue information**
- **Automatic source quality assessment**

### 3. Web Content Extraction (`_extract_web_content`)

**Purpose**: Extract and clean content from web pages for analysis.

**Input Parameters**:

```python
payload = {
    'url': str              # Required: URL to extract content from
}
```

**Output Structure**:

```python
{
    'url': str,                      # Original URL
    'title': str,                    # Page title
    'content': str,                  # Cleaned main content
    'metadata': Dict[str, Any],      # Extracted metadata
    'extracted_at': float            # Extraction timestamp
}
```

**Extraction Process**:

1. **HTML Retrieval**: Fetches page content with proper headers
2. **Content Identification**: Locates main content areas (article, main, .content)
3. **Cleanup**: Removes scripts, styles, navigation, and other non-content elements
4. **Text Extraction**: Converts HTML to clean text with proper spacing
5. **Metadata Parsing**: Extracts meta tags, Open Graph data, and structured data
6. **Content Limiting**: Enforces maximum content length (10,000 characters)

**Metadata Extraction**:

- Standard meta tags (description, keywords, author)
- Open Graph properties (og:title, og:description, og:image)
- Twitter Card data
- Structured data (JSON-LD, microdata)

### 4. Document Retrieval (`_retrieve_documents`)

**Purpose**: Batch retrieval of content from multiple URLs.

**Input Parameters**:

```python
payload = {
    'urls': List[str]       # List of URLs to retrieve
}
```

**Output Structure**:

```python
{
    'documents': List[Dict],         # Successfully retrieved documents
    'total_retrieved': int,          # Number of successful retrievals
    'total_requested': int           # Total URLs requested
}
```

**Batch Processing Features**:

- Parallel document retrieval for efficiency
- Individual error handling (failed URLs don't stop batch)
- Progress tracking and reporting
- Content validation and filtering

### 5. Result Filtering (`_filter_results`)

**Purpose**: Filter search results based on quality and relevance criteria.

**Input Parameters**:

```python
payload = {
    'results': List[Dict],           # Results to filter
    'min_relevance_score': float     # Minimum relevance threshold (default: 0.3)
}
```

**Output Structure**:

```python
{
    'results': List[Dict],           # Filtered results
    'total_filtered': int,           # Number of results that passed filter
    'total_original': int            # Original number of results
}
```

**Filtering Criteria**:

- Relevance score threshold
- Content length validation
- URL validity checks
- Duplicate detection
- Source credibility assessment

### 6. Relevance Ranking (`_rank_relevance`)

**Purpose**: Rank search results by relevance to the query.

**Input Parameters**:

```python
payload = {
    'results': List[Dict],   # Results to rank
    'query': str             # Original search query
}
```

**Output Structure**:

```python
{
    'results': List[Dict],           # Re-ranked results
    'query': str,
    'ranking_method': 'term_frequency'
}
```

**Ranking Algorithm**:

1. **Term Frequency Analysis**: Count query terms in title and content
2. **Position Weighting**: Title matches weighted 2x content matches
3. **Type Bonuses**: Academic papers (+1), instant answers (+2)
4. **Final Scoring**: Combined score determines ranking order

---

## Search Engines

### Supported Engines

#### 1. Google Search

- **URL Pattern**: `https://www.google.com/search?q={query}&num={max_results}`
- **Features**: Comprehensive web search, instant answers, rich snippets
- **Parsing Strategy**: Multi-pattern regex extraction with redirect handling
- **Strengths**: Largest index, best relevance algorithms, rich results

#### 2. Bing Search

- **URL Pattern**: `https://www.bing.com/search?q={query}&count={max_results}`
- **Features**: Web search with Microsoft integration, visual search
- **Parsing Strategy**: HTML structure analysis with fallback patterns
- **Strengths**: Good for technical content, API integration options

#### 3. Yahoo Search

- **URL Pattern**: `https://search.yahoo.com/search?p={query}&n={max_results}`
- **Features**: Web search with news integration
- **Parsing Strategy**: Standard result extraction with content filtering
- **Strengths**: News and current events, alternative perspective

#### 4. Semantic Scholar API

- **URL Pattern**: `https://api.semanticscholar.org/graph/v1/paper/search`
- **Features**: Academic paper search, citation tracking, open access detection, rich metadata
- **Integration**: Primary API-based access with automatic rate limiting
- **Strengths**: High-quality academic content, comprehensive metadata, open access prioritization

#### 5. Google Scholar (Fallback)

- **URL Pattern**: `https://scholar.google.com/scholar?q={query}&hl=en`
- **Features**: Academic paper search, citation tracking, author profiles
- **Parsing Strategy**: Scholar-specific result patterns, citation extraction
- **Strengths**: Academic content, peer-reviewed sources, research papers (fallback for Semantic Scholar)

### Search Engine Selection

**Automatic Selection**:

```python
# Default multi-engine search
search_engines = ['google', 'bing', 'yahoo']

# Academic-focused search (uses Semantic Scholar API primarily)
search_engines = ['semantic_scholar', 'google_scholar']

# Comprehensive high-budget search
search_engines = ['google', 'bing', 'yahoo', 'semantic_scholar']

# Fast single-engine search
search_engines = ['google']
```

**Engine-Specific Optimizations**:

- **Google**: Handles URL redirects, rich snippet extraction
- **Bing**: Optimized for technical and Microsoft ecosystem content
- **Yahoo**: Focused on news and current events
- **Semantic Scholar**: Primary academic search with API-based access and rich metadata
- **Google Scholar**: Academic paper parsing, citation format recognition (fallback)

---

## Content Extraction

### HTML Processing Pipeline

#### 1. Content Identification

```python
# Priority order for content containers
selectors = ['main', 'article', '.content', '.main-content', '#content']
```

#### 2. Unwanted Element Removal

```python
unwanted_elements = ['script', 'style', 'nav', 'footer', 'header', 'aside']
```

#### 3. Text Extraction and Cleaning

- **Whitespace Normalization**: Multiple spaces/newlines → single space
- **HTML Tag Removal**: Clean text extraction with proper spacing
- **Content Length Limiting**: Maximum 10,000 characters with truncation
- **Encoding Handling**: Proper UTF-8 text processing

### Metadata Extraction

#### Meta Tag Patterns

```python
# Standard meta tags
meta_pattern = r'<meta[^>]+name=["\']([^"\']+)["\'][^>]+content=["\']([^"\']+)["\'][^>]*>'

# Property-based meta tags (Open Graph, Twitter Cards)
prop_pattern = r'<meta[^>]+property=["\']([^"\']+)["\'][^>]+content=["\']([^"\']+)["\'][^>]*>'
```

#### Extracted Metadata Types

- **SEO Meta**: title, description, keywords, author
- **Open Graph**: og:title, og:description, og:image, og:type
- **Twitter Cards**: twitter:card, twitter:title, twitter:description
- **Custom Properties**: Application-specific metadata

### Content Quality Assessment

#### Quality Indicators

- **Content Length**: Minimum 100 characters for relevance
- **Structure Quality**: Presence of headings, paragraphs, lists
- **Metadata Richness**: Number and quality of meta tags
- **Language Detection**: Primary content language identification

---

## Usage Patterns

The Literature Agent now includes high-level workflow functions that orchestrate multiple search operations for common research scenarios. These are implemented as top-level methods that can be called directly via MCP actions.

### 1. Academic Research Workflow (`academic_research_workflow`)

**Purpose**: Complete academic research data collection pipeline for comprehensive literature review.

**MCP Action**: `academic_research_workflow`

**Input Parameters**:

```python
payload = {
    'research_topic': str,    # Required: Research topic or keywords
    'max_papers': int         # Optional: Maximum papers to search initially (default: 20)
}
```

**Example Usage**:

```python
# Via MCP action
action = ResearchAction(
    task_id="academic_research_001",
    context_id="research_context",
    agent_type="Literature",
    action="academic_research_workflow",
    payload={
        'research_topic': 'transformer models natural language processing',
        'max_papers': 25
    }
)

# Direct method call
results = await literature_agent.academic_research_workflow(
    research_topic="machine learning in healthcare",
    max_papers=15
)
```

**Workflow Steps**:

1. Initial broad academic search using Google Scholar
2. Content extraction from top 5 papers
3. Quality filtering with high relevance threshold (0.7)
4. Focused follow-up search for recent studies

**Output Structure**:

```python
{
    'research_topic': str,
    'broad_search': Dict,           # Initial academic search results
    'paper_content': Dict,          # Extracted content from top papers
    'filtered_results': Dict,       # High-quality filtered results
    'focused_search': Dict,         # Focused follow-up search
    'total_papers_found': int,
    'content_extracted': int
}
```

### 2. Multi-Source Validation (`multi_source_validation`)

**Purpose**: Validate information claims across different source types (web, academic, news).

**MCP Action**: `multi_source_validation`

**Input Parameters**:

```python
payload = {
    'claim': str              # Required: Information claim to validate
}
```

**Example Usage**:

```python
# Validate a factual claim
results = await literature_agent.multi_source_validation(
    claim="Electric vehicles have a lower carbon footprint than gas cars"
)
```

**Workflow Steps**:

1. Google search for general web sources
2. Academic paper search for scholarly evidence
3. News search for recent coverage and announcements
4. Content extraction from all found sources

### 3. Cost-Optimized Search (`cost_optimized_search`)

**Purpose**: Adjust search strategy based on budget or resource constraints.

**MCP Action**: `cost_optimized_search`

**Input Parameters**:

```python
payload = {
    'query': str,             # Required: Search query
    'budget_level': str       # Optional: 'low', 'medium', 'high' (default: 'medium')
}
```

**Budget Strategies**:

- **Low**: Single engine (Google), 3 results maximum
- **Medium**: Two engines (Google, Bing), 7 results maximum
- **High**: All engines, 15 results maximum

### 4. Comprehensive Research Pipeline (`comprehensive_research_pipeline`)

**Purpose**: Complete research pipeline combining web, academic, and news sources.

**MCP Action**: `comprehensive_research_pipeline`

**Input Parameters**:

```python
payload = {
    'topic': str,                    # Required: Research topic
    'include_academic': bool,        # Optional: Include academic sources (default: True)
    'include_news': bool,           # Optional: Include news sources (default: True)
    'max_results': int              # Optional: Max results per search type (default: 10)
}
```

**Comprehensive Workflow**:

1. Primary web search across multiple engines
2. Academic search (if enabled)
3. News and current events search (if enabled)
4. Content extraction from top results across all sources
5. Quality filtering and relevance ranking
6. Summary statistics and analysis

### 5. Fact Verification Workflow (`fact_verification_workflow`)

**Purpose**: Comprehensive fact verification with credibility analysis.

**MCP Action**: `fact_verification_workflow`

**Input Parameters**:

```python
payload = {
    'claim': str,                   # Required: Fact or claim to verify
    'require_academic': bool        # Optional: Require academic sources (default: True)
}
```

**Verification Process**:

1. Academic source verification
2. News source validation
3. Official documentation search
4. Content extraction and analysis
5. Credibility scoring and verification status determination

**Verification Statuses**:

- **highly_credible**: Academic sources + 3+ high-credibility sources
- **moderately_credible**: 2+ high-credibility sources
- **low_credibility**: Some sources found but low quality
- **unverified**: No reliable sources found

### Historical Usage Patterns (Now Implemented)

The usage patterns from the original documentation have been implemented as the workflow functions above. Here are examples of how they map:

```python
# Old pattern: Manual hierarchical research
# Now available as: comprehensive_research_pipeline

# Project-level information gathering
project_results = await literature_agent.comprehensive_research_pipeline(
    topic='AI healthcare market analysis 2024',
    include_academic=True,
    include_news=True,
    max_results=15
)

# Academic research workflow
# Now available as: academic_research_workflow
academic_results = await literature_agent.academic_research_workflow(
    research_topic='machine learning diagnostic accuracy radiology',
    max_papers=20
)

# Multi-source validation
# Now available as: multi_source_validation
validation_results = await literature_agent.multi_source_validation(
    claim='CNN vs Transformer radiology image analysis performance'
)

# Cost optimization
# Now available as: cost_optimized_search
efficient_results = await literature_agent.cost_optimized_search(
    query='electric vehicle market trends',
    budget_level='low'
)
```

---

## Configuration

### Agent Configuration

```python
class LiteratureAgent:
    def __init__(self, config_manager: ConfigManager):
        # Search engine endpoints
        self.search_engines = {
            'google': 'https://www.google.com/search',
            'bing': 'https://www.bing.com/search',
            'yahoo': 'https://search.yahoo.com/search',
            'google_scholar': 'https://scholar.google.com/scholar',
            'semantic_scholar': 'https://api.semanticscholar.org/graph/v1'
        }

        # Request configuration
        self.max_results_per_search = 10
        self.max_pages_per_result = 3
        self.request_timeout = 30
        self.user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'

        # Content filtering
        self.min_content_length = 100
        self.max_content_length = 10000
        self.relevance_threshold = 0.3
```

### HTTP Session Configuration

```python
# SSL/TLS Configuration
try:
    import certifi
    ssl_context = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    ssl_context = ssl.create_default_context()

# Connection pooling
connector = aiohttp.TCPConnector(
    limit=10,           # Total connection pool size
    limit_per_host=5,   # Connections per host
    ssl=ssl_context
)

# Session configuration
self.session = aiohttp.ClientSession(
    connector=connector,
    timeout=aiohttp.ClientTimeout(total=self.request_timeout),
    headers={'User-Agent': self.user_agent}
)
```

### Environment Variables

Optional configuration through environment variables:

- `SEMANTIC_SCHOLAR_API_KEY`: API key for enhanced Semantic Scholar access (higher rate limits)
- `LITERATURE_TIMEOUT`: Override default request timeout (default: 30 seconds)
- `LITERATURE_MAX_RESULTS`: Override default max results per search (default: 10)
- `LITERATURE_USER_AGENT`: Custom user agent string

---

## Error Handling

### Exception Types

The Literature Agent handles several types of errors:

1. **ValueError**: Invalid input parameters (missing query, invalid URLs)
2. **RuntimeError**: Agent not initialized, missing HTTP session
3. **aiohttp.ClientError**: Network connectivity issues, timeouts
4. **SSL/TLS Errors**: Certificate validation failures
5. **HTML Parsing Errors**: Malformed content, encoding issues

### Error Response Structure

```python
{
    'error': True,
    'error_type': 'NetworkError',
    'error_message': 'Connection timeout after 30 seconds',
    'url': 'https://example.com',
    'retry_possible': True
}
```

### Graceful Degradation

#### Search Engine Failover

```python
# If Google fails, try Bing and Yahoo
for engine in search_engines:
    try:
        results = await self._search_engine(engine, query, max_results)
        all_results.extend(results)
    except Exception as e:
        self.logger.error(f"Search failed for {engine}: {e}")
        continue  # Try next engine
```

#### Content Extraction Fallback

```python
# Multiple parsing strategies
try:
    # Primary strategy: structured content extraction
    content = self._extract_main_content(soup)
except Exception:
    # Fallback: simple text extraction
    content = soup.get_text(separator=' ', strip=True)
```

#### SSL/TLS Handling

```python
# Automatic SSL context creation with fallbacks
try:
    import certifi
    ssl_context = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    ssl_context = ssl.create_default_context()
except Exception:
    # Final fallback to basic SSL
    ssl_context = ssl.create_default_context()
```

---

## Testing

### Test Files Available

1. **`test_literature_simple.py`**: Basic functionality tests with real search engines
2. **`test_literature_standalone.py`**: Standalone testing with custom queries
3. **`test_literature_integration.py`**: Full integration tests with MCP communication

### Running Tests

```bash
# Simple functionality test
PYTHONPATH=/path/to/src python tests/literature/test_literature_simple.py

# Standalone test with custom query
PYTHONPATH=/path/to/src python tests/literature/test_literature_standalone.py "machine learning"

# Full integration test
PYTHONPATH=/path/to/src python tests/literature/test_literature_integration.py
```

### Test Coverage

The test suite covers:

- ✅ Multi-engine search functionality
- ✅ Content extraction and cleaning
- ✅ Academic paper search
- ✅ Duplicate detection and removal
- ✅ Relevance ranking algorithms
- ✅ Error handling and recovery
- ✅ SSL/TLS connection handling
- ✅ Batch document retrieval

### Performance Testing

```python
async def performance_test():
    """Test retrieval performance under load."""

    queries = ["AI research", "machine learning", "data science", "python programming"]
    start_time = time.time()

    # Concurrent searches
    tasks = []
    for query in queries:
        task = literature_agent._search_information({
            'query': query,
            'max_results': 5
        })
        tasks.append(task)

    results = await asyncio.gather(*tasks)

    total_time = time.time() - start_time
    total_results = sum(len(r['results']) for r in results)

    print(f"Retrieved {total_results} results in {total_time:.2f} seconds")
    print(f"Average: {total_results/total_time:.2f} results/second")
```

---

## Examples

### Example 1: Basic Web Search

```python
import asyncio
from src.agents.literature_agent import LiteratureAgent
from src.config.config_manager import ConfigManager

async def basic_web_search():
    """Demonstrate basic web search functionality."""

    config_manager = ConfigManager()
    agent = LiteratureAgent(config_manager)
    await agent.initialize()

    try:
        # Basic search across multiple engines
        results = await agent._search_information({
            'query': 'Python async programming best practices',
            'max_results': 10,
            'search_engines': ['google', 'bing', 'yahoo']
        })

        print(f"Found {results['total_found']} results")
        print(f"Using engines: {results['search_engines_used']}")

        # Display top 3 results
        for i, result in enumerate(results['results'][:3], 1):
            print(f"\n{i}. {result['title']}")
            print(f"   URL: {result['url']}")
            print(f"   Source: {result['source']}")
            print(f"   Relevance: {result['relevance_score']}")

    finally:
        await agent.cleanup()

# Run the example
asyncio.run(basic_web_search())
```

### Example 2: Academic Research Pipeline

```python
async def academic_research_pipeline():
    """Complete academic research data collection pipeline."""

    config_manager = ConfigManager()
    agent = LiteratureAgent(config_manager)
    await agent.initialize()

    try:
        research_topic = "transformer models natural language processing"

        # 1. Academic paper search
        print("🔍 Searching for academic papers...")
        academic_results = await agent._search_academic_papers({
            'query': research_topic,
            'max_results': 15
        })

        print(f"Found {len(academic_results['results'])} academic papers")

        # 2. Supplementary web search
        print("🌐 Searching web for additional context...")
        web_results = await agent._search_information({
            'query': f"{research_topic} tutorial implementation",
            'max_results': 8,
            'search_engines': ['google', 'bing']
        })

        # 3. Content extraction from top sources
        print("📄 Extracting content from top sources...")
        top_urls = [result['url'] for result in academic_results['results'][:3]]
        top_urls.extend([result['url'] for result in web_results['results'][:2]])

        documents = await agent._retrieve_documents({
            'urls': top_urls
        })

        print(f"Successfully extracted content from {documents['total_retrieved']} documents")

        # 4. Filter and rank all results
        all_results = academic_results['results'] + web_results['results']
        filtered_results = await agent._filter_results({
            'results': all_results,
            'min_relevance_score': 0.5
        })

        final_ranking = await agent._rank_relevance({
            'results': filtered_results['results'],
            'query': research_topic
        })

        print(f"Final results: {len(final_ranking['results'])} high-quality sources")

        return {
            'academic_papers': academic_results,
            'web_sources': web_results,
            'extracted_content': documents,
            'final_ranking': final_ranking
        }

    finally:
        await agent.cleanup()
```

### Example 3: Hierarchical Research Data Collection

```python
async def hierarchical_research_workflow():
    """Demonstrate hierarchical research data collection."""

    config_manager = ConfigManager()
    agent = LiteratureAgent(config_manager)
    await agent.initialize()

    try:
        # Project-level: Broad market research
        project_search = await agent._search_information({
            'query': 'electric vehicle market growth 2024 analysis',
            'max_results': 20,
            'search_engines': ['google', 'bing', 'yahoo'],
            'context': {
                'project_id': 'proj_ev_market_2024',
                'level': 'project',
                'scope': 'comprehensive'
            }
        })

        # Topic-level: Specific technology focus
        topic_search = await agent._search_information({
            'query': 'lithium battery technology electric vehicles 2024',
            'max_results': 12,
            'search_engines': ['google', 'google_scholar'],
            'context': {
                'project_id': 'proj_ev_market_2024',
                'topic_id': 'topic_battery_tech',
                'level': 'topic'
            }
        })

        # Task-level: Specific data points
        task_search = await agent._search_information({
            'query': 'Tesla Model 3 battery degradation study 2024',
            'max_results': 5,
            'search_engines': ['google_scholar', 'google'],
            'context': {
                'project_id': 'proj_ev_market_2024',
                'topic_id': 'topic_battery_tech',
                'task_id': 'task_degradation_analysis',
                'level': 'task'
            }
        })

        # Extract detailed content from task-level results
        task_content = await agent._retrieve_documents({
            'urls': [result['url'] for result in task_search['results']]
        })

        print("Hierarchical Research Results:")
        print(f"Project level: {len(project_search['results'])} results")
        print(f"Topic level: {len(topic_search['results'])} results")
        print(f"Task level: {len(task_search['results'])} results")
        print(f"Detailed content: {task_content['total_retrieved']} documents")

        return {
            'project_data': project_search,
            'topic_data': topic_search,
            'task_data': task_search,
            'detailed_content': task_content
        }

    finally:
        await agent.cleanup()
```

### Example 4: Multi-Source Fact Verification

```python
async def fact_verification_workflow():
    """Verify information across multiple sources and types."""

    config_manager = ConfigManager()
    agent = LiteratureAgent(config_manager)
    await agent.initialize()

    try:
        claim = "GPT-4 has 175 billion parameters"

        # Search across different source types
        print("🔍 Searching across multiple source types...")

        # Academic sources
        academic_verification = await agent._search_academic_papers({
            'query': f"{claim} research paper parameters",
            'max_results': 5
        })

        # News and tech sources
        news_verification = await agent._search_information({
            'query': f"{claim} news announcement",
            'max_results': 5,
            'search_engines': ['google', 'bing']
        })

        # Official documentation search
        official_verification = await agent._search_information({
            'query': f"OpenAI GPT-4 technical documentation parameters",
            'max_results': 3,
            'search_engines': ['google']
        })

        # Extract content for detailed analysis
        all_urls = []
        for source in [academic_verification, news_verification, official_verification]:
            all_urls.extend([r['url'] for r in source['results']])

        content_analysis = await agent._retrieve_documents({
            'urls': all_urls
        })

        # Analyze source credibility
        all_results = (academic_verification['results'] +
                      news_verification['results'] +
                      official_verification['results'])

        high_credibility = await agent._filter_results({
            'results': all_results,
            'min_relevance_score': 0.6
        })

        print("Fact Verification Results:")
        print(f"Academic sources: {len(academic_verification['results'])}")
        print(f"News sources: {len(news_verification['results'])}")
        print(f"Official sources: {len(official_verification['results'])}")
        print(f"High credibility sources: {high_credibility['total_filtered']}")
        print(f"Content extracted: {content_analysis['total_retrieved']} documents")

        return {
            'claim': claim,
            'academic_sources': academic_verification,
            'news_sources': news_verification,
            'official_sources': official_verification,
            'content_analysis': content_analysis,
            'high_credibility': high_credibility
        }

    finally:
        await agent.cleanup()
```

---

## API Reference

### Class Methods

#### `__init__(self, config_manager: ConfigManager)`

Initialize the Literature Agent with configuration.

**Parameters**:

- `config_manager`: ConfigManager instance for accessing configuration

#### `async initialize(self) -> bool`

Initialize HTTP session and SSL context.

**Returns**:

- `bool`: True if initialization successful

**Raises**:

- `RuntimeError`: If SSL context creation fails

#### `async cleanup(self) -> None`

Clean up HTTP session and release resources.

#### `_get_capabilities(self) -> List[str]`

Return list of agent capabilities.

**Returns**:

- `List[str]`: Capability strings

### Core Processing Methods

#### `async _search_information(self, payload: Dict[str, Any]) -> Dict[str, Any]`

Multi-engine information search.

**Parameters**:

- `payload['query']`: Search query (required)
- `payload['max_results']`: Maximum results per engine (optional, default: 10)
- `payload['search_engines']`: Engines to use (optional, default: ['google', 'bing', 'yahoo'])

**Returns**:

- Dictionary with aggregated search results

**Raises**:

- `ValueError`: If query is missing

#### `async _search_academic_papers(self, payload: Dict[str, Any]) -> Dict[str, Any]`

Search for academic papers using Semantic Scholar API with Google Scholar fallback.

**Parameters**:

- `payload['query']`: Research topic (required)
- `payload['max_results']`: Maximum papers (optional, default: 10)

**Returns**:

- Dictionary with academic search results including enhanced metadata from Semantic Scholar

#### `async _extract_web_content(self, payload: Dict[str, Any]) -> Dict[str, Any]`

Extract content from a web page.

**Parameters**:

- `payload['url']`: URL to extract from (required)

**Returns**:

- Dictionary with extracted content and metadata

**Raises**:

- `ValueError`: If URL is missing
- `Exception`: If page cannot be fetched or parsed

#### `async _retrieve_documents(self, payload: Dict[str, Any]) -> Dict[str, Any]`

Batch retrieval of documents from multiple URLs.

**Parameters**:

- `payload['urls']`: List of URLs (required)

**Returns**:

- Dictionary with retrieved documents and statistics

#### `async _filter_results(self, payload: Dict[str, Any]) -> Dict[str, Any]`

Filter results based on quality criteria.

**Parameters**:

- `payload['results']`: Results to filter (required)
- `payload['min_relevance_score']`: Minimum score threshold (optional, default: 0.3)

**Returns**:

- Dictionary with filtered results and statistics

#### `async _rank_relevance(self, payload: Dict[str, Any]) -> Dict[str, Any]`

Rank results by relevance to query.

**Parameters**:

- `payload['results']`: Results to rank (required)
- `payload['query']`: Original query (required)

**Returns**:

- Dictionary with re-ranked results

### Search Engine Methods

#### `async _search_google(self, query: str, max_results: int) -> List[Dict[str, Any]]`

Search Google with result parsing and redirect handling.

#### `async _search_bing(self, query: str, max_results: int) -> List[Dict[str, Any]]`

Search Bing with result parsing and content extraction.

#### `async _search_yahoo(self, query: str, max_results: int) -> List[Dict[str, Any]]`

Search Yahoo with result parsing and news integration.

#### `async _search_semantic_scholar(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]`

Search Semantic Scholar API for academic papers with rich metadata.

#### `async _search_google_scholar(self, query: str, max_results: int) -> List[Dict[str, Any]]`

Search Google Scholar for academic papers (used as fallback for Semantic Scholar).

### High-Level Workflow Methods

#### `async academic_research_workflow(self, research_topic: str, max_papers: int = 20) -> Dict[str, Any]`

Complete academic research data collection workflow.

**Parameters**:

- `research_topic`: Research topic or keywords (required)
- `max_papers`: Maximum number of papers to search initially (optional, default: 20)

**Returns**:

- Dictionary with comprehensive research results including broad search, content extraction, filtering, and focused search

#### `async multi_source_validation(self, claim: str) -> Dict[str, Any]`

Validate information across multiple source types.

**Parameters**:

- `claim`: Information claim to validate (required)

**Returns**:

- Dictionary with validation results from web, academic, and news sources

#### `async cost_optimized_search(self, query: str, budget_level: str = 'medium') -> Dict[str, Any]`

Optimize search strategy based on budget constraints.

**Parameters**:

- `query`: Search query (required)
- `budget_level`: Budget level - 'low', 'medium', or 'high' (optional, default: 'medium')

**Returns**:

- Dictionary with search results optimized for the specified budget level

#### `async comprehensive_research_pipeline(self, topic: str, include_academic: bool = True, include_news: bool = True, max_results: int = 10) -> Dict[str, Any]`

Complete research pipeline combining multiple search strategies.

**Parameters**:

- `topic`: Research topic (required)
- `include_academic`: Whether to include academic sources (optional, default: True)
- `include_news`: Whether to include news sources (optional, default: True)
- `max_results`: Maximum results per search type (optional, default: 10)

**Returns**:

- Dictionary with comprehensive research results, content analysis, filtering, and summary statistics

#### `async fact_verification_workflow(self, claim: str, require_academic: bool = True) -> Dict[str, Any]`

Comprehensive fact verification with credibility analysis.

**Parameters**:

- `claim`: Fact or claim to verify (required)
- `require_academic`: Whether to require academic sources for verification (optional, default: True)

**Returns**:

- Dictionary with verification status, sources from multiple types, content analysis, and credibility assessment

### Utility Methods

#### `_remove_duplicates(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]`

Remove duplicate results based on URL.

#### `async _rank_results(self, results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]`

Internal relevance ranking implementation.

#### `_extract_main_content(self, soup: BeautifulSoup) -> str`

Extract main content from HTML soup object.

#### `_extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]`

Extract metadata from HTML soup object.

---

## Performance Considerations

### Optimization Strategies

1. **Connection Pooling**: Reuse HTTP connections for efficiency
2. **Concurrent Searches**: Parallel search across engines
3. **Request Batching**: Group related requests together
4. **Content Caching**: Cache extracted content to avoid re-fetching
5. **Smart Filtering**: Early filtering to reduce processing overhead

### Monitoring Metrics

The agent tracks:

- Search response times per engine
- Content extraction success rates
- Network error rates and patterns
- SSL/TLS handshake performance
- Result quality and relevance scores

### Scalability Guidelines

For high-throughput scenarios:

- Use multiple agent instances with load balancing
- Implement request rate limiting per search engine
- Consider search engine API alternatives for heavy usage
- Monitor and respect robots.txt and rate limits
- Implement exponential backoff for failed requests

---

## Troubleshooting

### Common Issues

1. **"HTTP session not initialized"**

   - Ensure `await agent.initialize()` is called before using
   - Check SSL context creation logs for errors

2. **Search returns empty results**

   - Verify network connectivity
   - Check if search engines are accessible
   - Review query format and special characters

3. **SSL/TLS Certificate Errors**

   - Install certifi package: `pip install certifi`
   - Check system certificate store
   - Review SSL context creation logs

4. **Content extraction failures**

   - Verify URL accessibility
   - Check for anti-bot protection on target sites
   - Review HTML structure changes

5. **Poor search relevance**
   - Refine query with more specific terms
   - Adjust relevance scoring threshold
   - Use appropriate search engines for content type

### Debug Mode

Enable debug logging for detailed troubleshooting:

```python
import logging
logging.getLogger('literature_agent').setLevel(logging.DEBUG)
```

### Performance Debugging

```python
async def debug_search_performance():
    """Debug search performance across engines."""

    query = "machine learning algorithms"
    engines = ['google', 'bing', 'yahoo', 'google_scholar']

    for engine in engines:
        start_time = time.time()
        try:
            results = await agent._search_engine(engine, query, 5)
            elapsed = time.time() - start_time
            print(f"{engine}: {len(results)} results in {elapsed:.2f}s")
        except Exception as e:
            print(f"{engine}: Failed - {e}")
```

---

This documentation provides a comprehensive guide to the Literature Agent's capabilities, architecture, and usage patterns. For additional examples and advanced usage scenarios, refer to the test files and example implementations in the codebase.
