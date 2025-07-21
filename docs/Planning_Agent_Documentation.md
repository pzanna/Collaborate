# Planning Agent Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Functions](#core-functions)
4. [Usage Patterns](#usage-patterns)
5. [Configuration](#configuration)
6. [Error Handling](#error-handling)
7. [Testing](#testing)
8. [Examples](#examples)
9. [API Reference](#api-reference)

---

## Overview

The **Planning Agent** is a core component of the Eunice research system responsible for planning, analysis, reasoning, and synthesis tasks. It serves as the strategic brain of the research workflow, orchestrating how research tasks are approached and executed.

### Primary Responsibilities

- **Research Planning**: Generate comprehensive research plans and strategies
- **Information Analysis**: Analyze and extract insights from collected information
- **Result Synthesis**: Combine multiple sources into coherent, comprehensive responses
- **Chain of Thought Reasoning**: Perform step-by-step logical reasoning
- **Content Processing**: Summarize, extract insights, and evaluate content
- **Source Evaluation**: Compare and assess the credibility of information sources

### Key Features

- Multi-AI client support (OpenAI, XAI)
- Flexible prompt engineering for different task types
- Structured response parsing and organization
- Error handling and graceful degradation
- Async/await pattern for efficient processing
- Comprehensive logging and monitoring

---

## Architecture

### Class Hierarchy

```
BaseAgent
└── PlanningAgent
```

### Dependencies

- **Base Agent**: Inherits core agent functionality
- **AI Clients**: OpenAI and XAI client integrations
- **Config Manager**: Configuration and API key management
- **MCP Protocols**: Research action definitions and data structures
- **Data Models**: Message and response data structures

### Core Components

```python
class PlanningAgent(BaseAgent):
    def __init__(self, config_manager: ConfigManager)

    # Core capabilities
    async def _plan_research(self, payload: Dict[str, Any]) -> Dict[str, Any]
    async def _analyze_information(self, payload: Dict[str, Any]) -> Dict[str, Any]
    async def _synthesize_results(self, payload: Dict[str, Any]) -> Dict[str, Any]
    async def _chain_of_thought(self, payload: Dict[str, Any]) -> Dict[str, Any]

    # Content processing
    async def _summarize_content(self, payload: Dict[str, Any]) -> Dict[str, Any]
    async def _extract_insights(self, payload: Dict[str, Any]) -> Dict[str, Any]
    async def _compare_sources(self, payload: Dict[str, Any]) -> Dict[str, Any]
    async def _evaluate_credibility(self, payload: Dict[str, Any]) -> Dict[str, Any]
```

---

## Core Functions

### 1. Research Planning (`_plan_research`)

**Purpose**: Generate comprehensive research plans for given queries and contexts.

**Input Parameters**:

```python
payload = {
    'query': str,           # Required: Research question or topic
    'context': dict         # Optional: Additional context information
}
```

**Output Structure**:

```python
{
    'query': str,                    # Original query
    'plan': {                        # Structured research plan
        'raw_plan': str,             # Full AI response
        'objectives': str,           # Research objectives
        'key_areas': str,            # Areas to investigate
        'questions': str,            # Specific questions to answer
        'sources': str,              # Information sources to consult
        'outcomes': str              # Expected outcomes
    },
    'raw_response': str,             # Complete AI response
    'planning_model': str            # AI model used
}
```

**Use Cases**:

- Initial research strategy development
- Academic research planning
- Market research preparation
- Investigation roadmap creation

**Example**:

```python
result = await planning_agent._plan_research({
    'query': 'Impact of AI on healthcare diagnostics',
    'context': {
        'domain': 'healthcare',
        'focus': 'diagnostic_accuracy',
        'stakeholders': ['doctors', 'patients', 'hospitals']
    }
})
```

### 2. Information Analysis (`_analyze_information`)

**Purpose**: Analyze collected information and extract actionable insights.

**Input Parameters**:

```python
payload = {
    'query': str,           # Research query
    'context': {
        'search_results': list,     # Optional: Search results to analyze
        # ... other context data
    }
}
```

**Output Structure**:

```python
{
    'query': str,
    'analysis': {
        'type': str,                 # 'knowledge_based' or 'search_based'
        'findings': str,             # Key findings
        'source': str,               # Analysis source
        'confidence': str,           # Confidence level
        # Additional structured analysis fields
    },
    'sources_analyzed': int,         # Number of sources processed
    'raw_response': str,
    'analysis_model': str
}
```

**Processing Modes**:

1. **Knowledge-based**: Uses AI's general knowledge when no search results available
2. **Search-based**: Analyzes provided search results and external content

**Analysis Components**:

- Key findings and insights
- Themes and patterns identification
- Important facts and statistics
- Contradictions or inconsistencies
- Information gaps
- Reliability assessment

### 3. Result Synthesis (`_synthesize_results`)

**Purpose**: Combine multiple information sources into a comprehensive, coherent response.

**Input Parameters**:

```python
payload = {
    'query': str,
    'context': {
        'search_results': list,      # Search results
        'reasoning_output': str,     # Previous analysis
        'execution_results': list,   # Execution outputs
        # ... other accumulated data
    }
}
```

**Output Structure**:

```python
{
    'query': str,
    'synthesis': {
        'raw_synthesis': str,        # Complete synthesis
        'answer': str,               # Direct answer to query
        'evidence': str,             # Supporting evidence
        'perspectives': str,         # Multiple viewpoints
        'implications': str,         # Practical implications
        'recommendations': str,      # Further research suggestions
        'citations': str             # Source citations
    },
    'sources_used': int,
    'raw_response': str,
    'synthesis_model': str
}
```

**Synthesis Process**:

1. Aggregates all available information
2. Identifies key themes and insights
3. Resolves contradictions and conflicts
4. Provides balanced perspectives
5. Generates actionable recommendations

### 4. Chain of Thought Reasoning (`_chain_of_thought`)

**Purpose**: Perform step-by-step logical reasoning for complex problems.

**Input Parameters**:

```python
payload = {
    'query': str,           # Problem or question
    'context': dict         # Relevant context information
}
```

**Output Structure**:

```python
{
    'query': str,
    'reasoning_chain': str,          # Step-by-step reasoning process
    'reasoning_model': str
}
```

**Reasoning Process**:

1. Problem decomposition into components
2. Systematic analysis of each component
3. Logical connection identification
4. Well-reasoned conclusion development
5. Assumption and limitation identification

### 5. Content Summarization (`_summarize_content`)

**Purpose**: Create concise summaries of lengthy content.

**Input Parameters**:

```python
payload = {
    'content': str,         # Required: Content to summarize
    'max_length': int       # Optional: Maximum summary length (default: 500)
}
```

**Output Structure**:

```python
{
    'original_length': int,          # Original content length
    'summary': str,                  # Generated summary
    'summary_length': int,           # Summary length
    'compression_ratio': float       # Summary/original ratio
}
```

### 6. Insight Extraction (`_extract_insights`)

**Purpose**: Extract key insights, trends, and recommendations from content.

**Input Parameters**:

```python
payload = {
    'content': str          # Content to analyze
}
```

**Output Structure**:

```python
{
    'content_analyzed': int,         # Content length processed
    'insights': str,                 # Extracted insights
    'extraction_model': str
}
```

**Extracted Elements**:

- Top 5 key insights
- Important trends or patterns
- Surprising findings
- Actionable recommendations

### 7. Source Comparison (`_compare_sources`)

**Purpose**: Compare multiple information sources for consistency and reliability.

**Input Parameters**:

```python
payload = {
    'sources': list         # List of sources to compare (minimum 2)
}
```

**Output Structure**:

```python
{
    'sources_compared': int,         # Number of sources analyzed
    'comparison': str,               # Detailed comparison
    'comparison_model': str
}
```

**Comparison Analysis**:

- Agreements between sources
- Disagreements or contradictions
- Unique information from each source
- Credibility assessment
- Overall reliability ranking

### 8. Credibility Evaluation (`_evaluate_credibility`)

**Purpose**: Assess the credibility and reliability of information sources.

**Input Parameters**:

```python
payload = {
    'sources': list         # Sources to evaluate
}
```

**Output Structure**:

```python
{
    'sources_evaluated': int,        # Number of sources assessed
    'credibility_assessment': str,   # Detailed assessment
    'evaluation_model': str
}
```

**Evaluation Criteria**:

- Authority and expertise
- Objectivity and bias
- Currency and timeliness
- Accuracy and reliability
- Overall credibility score (1-10)

---

## Usage Patterns

### 1. Research Workflow Integration

The Planning Agent typically operates within a larger research workflow:

```python
# 1. Initial Planning
plan_result = await planning_agent._plan_research({
    'query': research_query,
    'context': initial_context
})

# 2. Information Analysis (after data collection)
analysis_result = await planning_agent._analyze_information({
    'query': research_query,
    'context': {
        'search_results': collected_data
    }
})

# 3. Final Synthesis
synthesis_result = await planning_agent._synthesize_results({
    'query': research_query,
    'context': {
        'search_results': collected_data,
        'reasoning_output': analysis_result['analysis']['findings'],
        'execution_results': []
    }
})
```

### 2. Standalone Usage

Individual functions can be used independently:

```python
# Quick content summarization
summary = await planning_agent._summarize_content({
    'content': long_article,
    'max_length': 300
})

# Insight extraction
insights = await planning_agent._extract_insights({
    'content': research_report
})
```

### 3. Batch Processing

Multiple operations can be performed in sequence:

```python
async def comprehensive_analysis(content_list):
    results = []
    for content in content_list:
        # Summarize each piece
        summary = await planning_agent._summarize_content({
            'content': content
        })

        # Extract insights
        insights = await planning_agent._extract_insights({
            'content': content
        })

        results.append({
            'summary': summary,
            'insights': insights
        })

    return results
```

---

## Configuration

### AI Client Configuration

The Planning Agent supports multiple AI providers through configuration:

```json
{
  "ai_providers": {
    "openai": {
      "model": "gpt-4",
      "temperature": 0.7,
      "max_tokens": 2000
    },
    "xai": {
      "model": "grok-beta",
      "temperature": 0.7,
      "max_tokens": 2000
    }
  }
}
```

### Agent Parameters

```python
class PlanningAgent:
    def __init__(self, config_manager: ConfigManager):
        # Default configuration
        self.default_model = "gpt-4"
        self.max_context_length = 8000
        self.temperature = 0.7
```

### Environment Variables

Required environment variables for API access:

- `OPENAI_API_KEY`: OpenAI API key
- `XAI_API_KEY`: XAI API key (if using XAI)

---

## Error Handling

### Exception Types

The Planning Agent handles several types of errors:

1. **ValueError**: Invalid input parameters
2. **RuntimeError**: Missing AI clients or configuration issues
3. **API Errors**: AI service unavailability or quota limits
4. **Network Errors**: Connection issues

### Error Responses

When errors occur, functions may return error information:

```python
{
    'error': True,
    'error_type': 'APIError',
    'error_message': 'API rate limit exceeded',
    'raw_response': 'Error generating response: ...'
}
```

### Graceful Degradation

The agent implements several fallback mechanisms:

1. **AI Client Fallback**: If primary client fails, tries secondary client
2. **Knowledge-based Analysis**: Falls back to general knowledge when search results unavailable
3. **Error Logging**: Comprehensive error logging for debugging

---

## Testing

### Test Files Available

1. **`test_plan_research_production.py`**: Production tests with real AI clients
2. **`quick_test_plan_research.py`**: Quick testing with custom queries
3. **`test_plan_research_direct.py`**: Unit tests with mocked components

### Running Tests

```bash
# Production test with real AI clients
PYTHONPATH=/path/to/src python tests/test_plan_research_production.py

# Quick test with custom query
PYTHONPATH=/path/to/src python tests/quick_test_plan_research.py "Your query here"

# Unit tests (no API calls required)
PYTHONPATH=/path/to/src python tests/test_plan_research_direct.py
```

### Test Coverage

The test suite covers:

- ✅ Basic functionality with valid inputs
- ✅ Error handling with invalid inputs
- ✅ AI client integration
- ✅ Response parsing and structuring
- ✅ Context handling
- ✅ Resource cleanup

---

## Examples

### Example 1: Academic Research Planning

```python
import asyncio
from src.agents.planning_agent import PlanningAgent
from src.config.config_manager import ConfigManager

async def academic_research_example():
    config_manager = ConfigManager()
    agent = PlanningAgent(config_manager)
    await agent._initialize_agent()

    try:
        result = await agent._plan_research({
            'query': 'Impact of machine learning on climate change research',
            'context': {
                'academic_level': 'graduate',
                'research_type': 'systematic_review',
                'timeline': '6_months',
                'focus_areas': ['prediction_models', 'data_analysis', 'visualization']
            }
        })

        print("Research Plan Generated:")
        print(f"Objectives: {result['plan']['objectives']}")
        print(f"Key Areas: {result['plan']['key_areas']}")

    finally:
        await agent._cleanup_agent()

# Run the example
asyncio.run(academic_research_example())
```

### Example 2: Market Research Analysis

```python
async def market_research_example():
    config_manager = ConfigManager()
    agent = PlanningAgent(config_manager)
    await agent._initialize_agent()

    try:
        # Analyze market data
        analysis = await agent._analyze_information({
            'query': 'Electric vehicle market trends 2024',
            'context': {
                'search_results': [
                    {
                        'title': 'EV Market Report 2024',
                        'content': 'Electric vehicle sales increased by 40%...',
                        'source': 'MarketResearch.com'
                    }
                    # ... more search results
                ]
            }
        })

        # Extract actionable insights
        insights = await agent._extract_insights({
            'content': analysis['raw_response']
        })

        print("Market Analysis:")
        print(analysis['analysis']['findings'])
        print("\nKey Insights:")
        print(insights['insights'])

    finally:
        await agent._cleanup_agent()
```

### Example 3: Content Processing Pipeline

```python
async def content_processing_pipeline(documents):
    config_manager = ConfigManager()
    agent = PlanningAgent(config_manager)
    await agent._initialize_agent()

    try:
        processed_docs = []

        for doc in documents:
            # Summarize document
            summary = await agent._summarize_content({
                'content': doc['content'],
                'max_length': 200
            })

            # Extract insights
            insights = await agent._extract_insights({
                'content': doc['content']
            })

            processed_docs.append({
                'title': doc['title'],
                'summary': summary['summary'],
                'insights': insights['insights'],
                'compression_ratio': summary['compression_ratio']
            })

        # Compare all documents
        comparison = await agent._compare_sources({
            'sources': processed_docs
        })

        return {
            'processed_documents': processed_docs,
            'comparison_analysis': comparison['comparison']
        }

    finally:
        await agent._cleanup_agent()
```

---

## API Reference

### Class Methods

#### `__init__(self, config_manager: ConfigManager)`

Initialize the Planning Agent with configuration.

**Parameters**:

- `config_manager`: ConfigManager instance for accessing configuration and API keys

#### `async _initialize_agent(self) -> None`

Initialize AI clients and agent resources.

**Raises**:

- `RuntimeError`: If no AI clients are available

#### `async _cleanup_agent(self) -> None`

Clean up AI clients and release resources.

#### `_get_capabilities(self) -> List[str]`

Return list of agent capabilities.

**Returns**:

- List of capability strings

### Processing Methods

All processing methods follow the pattern:

```python
async def _method_name(self, payload: Dict[str, Any]) -> Dict[str, Any]
```

#### Core Research Methods

- `_plan_research(payload)`: Generate research plans
- `_analyze_information(payload)`: Analyze information and extract insights
- `_synthesize_results(payload)`: Synthesize multiple sources
- `_chain_of_thought(payload)`: Perform step-by-step reasoning

#### Content Processing Methods

- `_summarize_content(payload)`: Summarize content
- `_extract_insights(payload)`: Extract key insights
- `_compare_sources(payload)`: Compare multiple sources
- `_evaluate_credibility(payload)`: Evaluate source credibility

### Utility Methods

#### `async _get_ai_response(self, prompt: str) -> str`

Get response from AI client.

**Parameters**:

- `prompt`: Input prompt string

**Returns**:

- AI response string

**Raises**:

- `RuntimeError`: If no AI client available

#### `_prepare_content_for_analysis(self, search_results: List[Dict]) -> str`

Format search results for analysis.

#### `_parse_research_plan(self, response: str) -> Dict[str, Any]`

Parse AI response into structured research plan.

#### `_extract_section(self, text: str, section_name: str) -> str`

Extract specific section from structured text.

---

## Performance Considerations

### Optimization Tips

1. **Batch Processing**: Group similar operations when possible
2. **Context Reuse**: Reuse agent instances to avoid reinitialization overhead
3. **Response Caching**: Cache AI responses for repeated queries
4. **Token Management**: Monitor token usage for cost optimization

### Monitoring

The agent provides comprehensive logging:

- Initialization and cleanup events
- API call success/failure
- Processing times and token usage
- Error conditions and recovery

### Scalability

For high-throughput scenarios:

- Use connection pooling for AI clients
- Implement request queuing and rate limiting
- Consider async processing with multiple agent instances
- Monitor and optimize prompt efficiency

---

## Troubleshooting

### Common Issues

1. **"No AI client available"**

   - Check API key configuration
   - Verify network connectivity
   - Ensure AI provider is properly configured

2. **"Query is required for research planning"**

   - Ensure payload contains non-empty 'query' field
   - Check payload structure

3. **API Rate Limiting**

   - Implement exponential backoff
   - Consider using multiple API keys
   - Optimize prompt length and frequency

4. **Poor Response Quality**
   - Refine prompt engineering
   - Adjust temperature and model parameters
   - Provide more context in queries

### Debug Mode

Enable debug logging for detailed troubleshooting:

```python
import logging
logging.getLogger('planning_agent').setLevel(logging.DEBUG)
```

---

This documentation provides a comprehensive guide to the Planning Agent's capabilities, usage patterns, and best practices. For additional examples and advanced usage scenarios, refer to the test files and example implementations in the codebase.
