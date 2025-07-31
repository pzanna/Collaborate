# Literature Review Process in Eunice Research Platform

## Overview

The literature review process in Eunice involves coordinated interaction between the Research Manager and Literature Search Agent through the MCP (Model Context Protocol) server. This document outlines the complete workflow from initiation to completion.

## Architecture Components

### 1. Research Manager Service

- **Role**: Orchestrates the overall research workflow
- **Location**: `/agents/research-manager/src/research_manager_service.py`
- **Stage**: `LITERATURE_REVIEW` in `ResearchStage` enum
- **Responsibilities**:
  - Cost estimation for literature searches
  - Task delegation to Literature Search Agent
  - Progress tracking and monitoring
  - Result aggregation and quality control

### 2. Literature Search Agent

- **Role**: Executes academic literature searches
- **Location**: `/agents/literature/src/literature_service.py`
- **Capabilities**:
  - Multi-source search (PubMed, arXiv, Semantic Scholar, CrossRef)
  - Result normalization and deduplication
  - Academic record processing
  - Rate limiting and error handling

### 3. MCP Server

- **Role**: Message routing and task coordination
- **Location**: `/services/mcp-server/mcp_server.py`
- **Functions**:
  - Agent registration and discovery
  - Message routing between agents
  - Task lifecycle management

## Literature Review Triggers

The literature review process is initiated through several trigger mechanisms:

### 1. Task Execution via API Gateway (Primary Trigger)

The most common trigger is when a user executes a research task through the API Gateway:

**API Endpoint**: `POST /v2/tasks/{task_id}/execute`

**Trigger Flow**:

1. User creates a task with `task_type: "research"` and a research query
2. User calls the execute endpoint for that task
3. API Gateway sends an MCP message to coordinate research:

```python
execution_data = {
    "task_id": str(uuid4()),
    "context_id": f"task-execution-{task_id}",
    "agent_type": "research",  # Routes to Research Manager
    "action": "execute_task",
    "payload": {
        "task_id": task_id,
        "query": task.get("query", ""),
        "task_type": task.get("task_type", "research"),
        "max_results": task.get("max_results", 10),
        "single_agent_mode": task.get("single_agent_mode", False)
    }
}
```

### 2. Direct Research Coordination (Alternative Trigger)

The Research Manager can also be triggered directly via MCP with a `coordinate_research` action:

```python
task_data = {
    "task_type": "coordinate_research",
    "data": {
        "query": "machine learning applications in medical diagnosis",
        "user_id": "researcher_001",
        "project_id": "proj_123",
        "single_agent_mode": false,
        "filters": {
            "year_min": 2020,
            "publication_types": ["journal_article", "review"],
            "max_results": 100
        }
    }
}
```

### 3. AI-Generated Research Plan to Search Terms Conversion

When a research plan is created via the AI Planning Agent, the search terms for literature review are now derived through an enhanced AI-powered process:

**Source of AI Request**: The API Gateway endpoint `POST /v2/topics/{topic_id}/ai-plans` initiates AI-powered research plan generation.

**Enhanced AI Conversion Process**:

1. **AI Planning Agent Generates Structured Plan**:

   ```python
   # Planning Agent creates detailed research plan via AI
   plan_structure = {
       "objectives": ["Objective 1", "Objective 2", "Objective 3"],
       "key_areas": ["Area 1", "Area 2", "Area 3"],
       "questions": ["Question 1", "Question 2", "Question 3"],
       "sources": ["PubMed", "ArXiv", "Semantic Scholar", "CrossRef"]
   }
   ```

2. **Literature Service Requests AI Search Term Optimization**:

   ```python
   # Literature service delegates AI functionality to AI agent via MCP
   if search_query.research_plan:
       search_terms = await self._extract_search_terms_from_research_plan(
           search_query.research_plan, 
           search_query.query
       )
   else:
       search_terms = [search_query.query]  # Fallback to original query
   ```

3. **AI Agent Handles Search Term Optimization**:

   ```python
   # AI Agent receives MCP request for search term optimization
   optimization_request = {
       "type": "task",
       "target_agent": "ai_agent",
       "action": "optimize_search_terms",
       "payload": {
           "research_plan": research_plan,
           "original_query": original_query,
           "context": "literature_search",
           "target_databases": ["PubMed", "arXiv", "Semantic Scholar", "CrossRef"],
           "max_terms": 5
       }
   }
   ```

4. **AI Agent Analysis and Response**:

   The AI agent processes the research plan using its AI clients (OpenAI/XAI) and returns optimized search terms via MCP:

   ```python
   # AI agent response via MCP
   {
       "type": "task_result",
       "status": "completed",
       "optimized_terms": [
           "machine learning medical diagnosis",
           "deep learning radiology imaging",
           "AI diagnostic accuracy studies",
           "computer vision medical applications",
           "neural networks healthcare"
       ]
   }
   ```

5. **Multi-Term Literature Search**:

   ```python
   # Each AI-optimized term searches all sources
   for term in search_terms:
       modified_query = SearchQuery(query=term, ...)
       results = await self._search_semantic_scholar(modified_query)
       all_results.extend(results)
   ```

**Current Implementation**: The search terms are primarily derived from the original user query (`context.query`), but AI-enhanced search term extraction is now available when a research plan is provided.

**New AI Search Term Extraction**: The Literature Search Service now includes AI-powered search term optimization:

```python
# Literature Search Service - Enhanced Implementation
if search_query.research_plan:
    logger.info("Research plan provided, extracting AI-optimized search terms")
    search_terms = await self._extract_search_terms_from_research_plan(
        search_query.research_plan, 
        search_query.query
    )
else:
    logger.info("No research plan provided, using original query")
    search_terms = [search_query.query]
```

The AI extraction process:

1. **AI Planning Agent Generates Research Plan** with objectives, key areas, questions, and sources
2. **Literature Service Analyzes Plan** using OpenAI or XAI clients to extract 3-5 optimized search terms
3. **Multi-Term Search** executes searches using each optimized term across all sources
4. **Result Aggregation** combines and deduplicates results from all search terms

**Legacy Implementation Evidence**: In the old source code (`/old_src/agents/research_manager/research_manager.py`), the Research Manager's `_execute_literature_review_stage` function shows this pattern:

```python
# Old implementation - line 736-750
action = ResearchAction(
    task_id=context.task_id,
    context_id=context.task_id,
    agent_type="literature", 
    action="search_academic_papers",
    payload={
        "query": context.query,                # Direct user query
        "research_plan": research_plan,        # Plan sent as context only
        "search_depth": "comprehensive",
        "max_results": 10,
    },
)
```

The research plan is passed to the literature agent as context, but the actual search terms are extracted directly from `context.query` - the original user input.

**Enhanced Capabilities**: The new implementation now:

- Analyzes research plan objectives and key areas to generate domain-specific search terms
- Uses AI to identify scientific terminology and synonyms  
- Optimizes search queries for each academic database's specific syntax
- Distributes search results across multiple terms for broader coverage
- Combines results intelligently while avoiding duplication

### 4. Automatic Stage Progression

Once triggered, the Research Manager automatically progresses through stages:

- **PLANNING** → **COST_ESTIMATION** → **LITERATURE_REVIEW**
- Literature review begins when `ResearchStage.LITERATURE_REVIEW` is reached
- Cost estimation must be approved (automatic if under threshold)

### 5. Trigger Conditions

The literature review begins when:

- ✅ A research task exists with a valid query
- ✅ Cost estimation is approved (automatic if under threshold)
- ✅ Research Manager transitions to `ResearchStage.LITERATURE_REVIEW`
- ✅ Literature Search Agent is available and responsive

## Literature Review Workflow

### Phase 1: Research Initiation

1. **User Request Received** (via Web UI or API Gateway)

   ```json
   {
     "query": "machine learning applications in medical diagnosis",
     "user_id": "researcher_001",
     "project_id": "proj_123",
     "single_agent_mode": false,
     "filters": {
       "year_min": 2020,
       "publication_types": ["journal_article", "review"],
       "max_results": 100
     }
   }
   ```

2. **Research Manager Creates Context**

   ```python
   context = ResearchContext(
       task_id=str(uuid.uuid4()),
       query=query,
       user_id=user_id,
       project_id=project_id,
       stage=ResearchStage.PLANNING
   )
   ```

### Phase 2: Cost Estimation

1. **Research Manager Estimates Costs**

   ```python
   operations = [
       {"type": "literature_search", "quantity": 4},  # 4 sources
       {"type": "synthesis", "quantity": 1}
   ]
   estimated_cost = await self._calculate_operation_costs(operations)
   # Result: ~$0.28 for comprehensive search
   ```

2. **Cost Approval** (if required)

   - Automatic approval for costs under threshold
   - User approval required for expensive operations

### Phase 3: Literature Search Execution

1. **Transition to Literature Review Stage**

   ```python
   context.stage = ResearchStage.LITERATURE_REVIEW
   context.updated_at = datetime.now()
   ```

2. **Delegate to Literature Search Agent**

   ```python
   delegation_message = {
       "jsonrpc": "2.0",
       "method": "task/delegate",
       "params": {
           "task_id": context.task_id,
           "target_agent": "literature_search",
           "action_data": {
               "action": "search_literature",
               "payload": {
                   "lit_review_id": context.task_id,
                   "query": context.query,
                   "sources": ["semantic_scholar", "pubmed", "arxiv", "crossref"],
                   "max_results": 100,
                   "filters": {
                       "year_min": 2020,
                       "publication_types": ["journal_article", "review"]
                   }
               }
           }
       }
   }
   ```

### Phase 4: Multi-Source Literature Search

1. **Literature Agent Processes Request**

   - Validates search parameters
   - Creates SearchQuery object
   - Executes parallel searches across sources

2. **Parallel Source Searches**

   ```python
   # Semantic Scholar Search
   semantic_results = await self._search_semantic_scholar(search_query)
   
   # PubMed Search  
   pubmed_results = await self._search_pubmed(search_query)
   
   # arXiv Search
   arxiv_results = await self._search_arxiv(search_query)
   
   # CrossRef Search
   crossref_results = await self._search_crossref(search_query)
   ```

3. **Result Processing Pipeline**

   ```python
   # Step 1: Normalize records from different sources
   normalized_records = []
   for source, records in source_results.items():
       normalized = self._normalize_records(records, source)
       normalized_records.extend(normalized)
   
   # Step 2: Deduplicate across sources
   unique_records = self._deduplicate_records(normalized_records)
   
   # Step 3: Quality filtering
   filtered_records = self._filter_by_quality(unique_records)
   ```

### Phase 5: Result Aggregation and Analysis

1. **Search Report Generation**

    ```python
    search_report = SearchReport(
        lit_review_id=search_query.lit_review_id,
        total_fetched=len(all_records),
        total_unique=len(unique_records),
        per_source_counts={
            "semantic_scholar": 45,
            "pubmed": 32,
            "arxiv": 18,
            "crossref": 28
        },
        start_time=start_time,
        end_time=end_time,
        errors=[],
        records=unique_records
    )
    ```

2. **Return Results to Research Manager**

    ```json
    {
        "type": "task_result",
        "task_id": "uuid-task-id",
        "agent_id": "literature_search",
        "result": {
            "status": "completed",
            "search_report": {
                "total_fetched": 123,
                "total_unique": 95,
                "duration": 45.7,
                "per_source_counts": {...}
            },
            "records": [...],
            "timestamp": "2024-07-31T15:30:00Z"
        }
    }
    ```

### Phase 6: Research Manager Processing

1. **Update Research Context**

    ```python
    # Store search results
    context.search_results = search_report.records
    context.completed_stages.append(ResearchStage.LITERATURE_REVIEW)
    context.actual_cost += search_cost
    
    # Progress to next stage
    context.stage = ResearchStage.REASONING
    ```

2. **Generate Literature Review Summary**

    ```python
    summary = {
        "total_papers_found": len(context.search_results),
        "search_quality": "high",
        "key_themes_identified": ["deep learning", "clinical applications", "diagnostic accuracy"],
        "date_range": "2020-2024",
        "top_venues": ["Nature Medicine", "NEJM", "IEEE TMI"],
        "search_completeness": 0.89
    }
    ```

## Data Structures

### SearchQuery Object

```python
@dataclass
class SearchQuery:
    lit_review_id: str
    query: str
    filters: Dict[str, Any] = field(default_factory=dict)
    sources: List[str] = field(default_factory=list)
    max_results: int = 100
    search_depth: str = "standard"
```

### Normalized Record Schema

```python
{
    "source": "semantic_scholar",
    "title": "Deep Learning for Medical Image Analysis",
    "authors": ["Smith, J.", "Doe, A."],
    "abstract": "This paper presents...",
    "doi": "10.1038/s41591-2024-123",
    "pmid": "38234567",
    "year": 2024,
    "journal": "Nature Medicine",
    "url": "https://...",
    "citation_count": 127,
    "publication_type": "journal_article",
    "mesh_terms": ["Deep Learning", "Medical Imaging"],
    "retrieval_timestamp": "2024-07-31T15:30:00Z"
}
```

## Error Handling and Recovery

### Common Error Scenarios

1. **API Rate Limiting**
   - Automatic retry with exponential backoff
   - Source prioritization when limits reached
   - Graceful degradation to available sources

2. **Network Connectivity Issues**
   - Connection timeout handling
   - Fallback to cached results
   - Partial result acceptance

3. **Invalid Query Parameters**
   - Query sanitization and validation
   - Default parameter substitution
   - User feedback on corrections

4. **Service Unavailability**
   - Health check integration
   - Circuit breaker pattern
   - Alternative source routing

### Recovery Strategies

```python
async def _handle_search_failure(self, source: str, error: Exception):
    """Handle search failure with appropriate recovery strategy"""
    if isinstance(error, RateLimitError):
        # Wait and retry
        await asyncio.sleep(error.retry_after)
        return await self._retry_search(source)
    elif isinstance(error, ConnectionError):
        # Try alternative sources
        return await self._search_alternative_sources()
    else:
        # Log error and continue with partial results
        logger.error(f"Search failed for {source}: {error}")
        return []
```

## Performance Optimization

### Parallel Processing

- Concurrent searches across multiple sources
- Asynchronous I/O for API calls
- Rate limiting compliance per source

### Caching Strategy

- Query result caching (1 hour TTL)
- API response caching per source
- Deduplication cache for efficiency

### Resource Management

- Connection pooling for HTTP requests
- Memory-efficient streaming for large result sets
- Garbage collection for completed tasks

## Quality Assurance

### Result Validation

```python
def _validate_search_results(self, records: List[Dict]) -> List[Dict]:
    """Validate and filter search results for quality"""
    validated = []
    for record in records:
        if self._is_high_quality_record(record):
            validated.append(record)
    return validated

def _is_high_quality_record(self, record: Dict) -> bool:
    """Check if record meets quality criteria"""
    return all([
        record.get('title'),
        record.get('authors'),
        record.get('year'),
        len(record.get('abstract', '')) > 100
    ])
```

### Deduplication Algorithm

```python
def _deduplicate_records(self, records: List[Dict]) -> List[Dict]:
    """Advanced deduplication using multiple identifiers"""
    seen_dois = set()
    seen_pmids = set()
    seen_hashes = set()
    unique_records = []
    
    for record in records:
        # Primary: DOI matching
        doi = record.get('doi')
        if doi and doi in seen_dois:
            continue
        elif doi:
            seen_dois.add(doi)
        
        # Secondary: PMID matching
        pmid = record.get('pmid')
        if pmid and pmid in seen_pmids:
            continue
        elif pmid:
            seen_pmids.add(pmid)
        
        # Tertiary: Content hash matching
        content_hash = self._generate_content_hash(record)
        if content_hash in seen_hashes:
            continue
        
        seen_hashes.add(content_hash)
        unique_records.append(record)
    
    return unique_records
```

## Monitoring and Metrics

### Key Performance Indicators

- Search completion rate
- Average search duration
- Result quality scores
- Deduplication effectiveness
- API quota utilization

### Logging and Tracing

```python
logger.info("Literature search completed", 
           task_id=context.task_id,
           total_results=len(results),
           duration=duration,
           sources_used=list(source_counts.keys()),
           cost=actual_cost)
```

## Next Steps in Research Workflow

After literature review completion, the Research Manager proceeds to:

1. **Reasoning Stage** - Analyze found literature for insights
2. **Execution Stage** - Generate specific research outputs
3. **Synthesis Stage** - Compile comprehensive research report

Each stage follows the same MCP-based delegation pattern with specialized agents handling domain-specific tasks.
