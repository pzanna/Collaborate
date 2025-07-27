# Planning Agent Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Functions](#core-functions)
4. [API Gateway Integration](#api-gateway-integration)
5. [Usage Patterns](#usage-patterns)
6. [Configuration](#configuration)
7. [Error Handling](#error-handling)
8. [Testing](#testing)
9. [Examples](#examples)
10. [API Reference](#api-reference)
11. [Cost Estimation](#cost-estimation)

---

## Overview

The **Planning Agent** is a containerized microservice in the Eunice research system responsible for planning, analysis, reasoning, and synthesis tasks. It operates as the strategic brain of the research workflow, communicating exclusively via MCP (Model Context Protocol) and providing sophisticated cost estimation capabilities.

### Primary Responsibilities

- **Research Planning**: Generate comprehensive research plans and strategies
- **Information Analysis**: Analyze and extract insights from collected information
- **Result Synthesis**: Combine multiple sources into coherent, comprehensive responses
- **Chain of Thought Reasoning**: Perform step-by-step logical reasoning
- **Content Processing**: Summarize, extract insights, and evaluate content
- **Source Evaluation**: Compare and assess the credibility of information sources
- **Cost Estimation**: Provide accurate cost estimates with optimization recommendations
- **MCP Protocol Compliance**: Exclusive communication via MCP WebSocket

### Key Features

- **Containerized Architecture**: Docker-based microservice deployment
- **MCP Protocol Integration**: Exclusive WebSocket-based communication
- **Sophisticated Cost Estimation**: Real-time cost tracking and optimization
- **No Mock Data**: All responses generated through AI providers via MCP
- **JSON-structured Output**: Consistent, parseable response formats
- **Multi-capability Support**: 8 distinct research capabilities
- **Error Handling**: Comprehensive error handling and logging
- **Configuration-driven**: JSON-based configuration management

---

## Architecture

### Current Architecture (Version 0.3.1)

The Planning Agent operates as a containerized microservice within the Eunice ecosystem:

```text
API Gateway → MCP Server → Planning Agent Container
                    ↓
              AI Providers (OpenAI/XAI)
```

### Container Structure

```text
eunice-planning-agent:latest
├── src/
│   ├── planning_service.py      # Main service with HTTP and WebSocket support
│   ├── cost_estimator.py        # Sophisticated cost estimation system
│   └── config_manager.py        # Configuration management
├── config/
│   └── config.json             # Agent configuration
└── Dockerfile                  # Container definition
```

### Dependencies

- **MCP Server**: Exclusive communication via WebSocket
- **FastAPI**: HTTP server for health checks and API endpoints
- **WebSocket Client**: MCP protocol communication
- **AI Providers**: OpenAI and XAI integration via MCP
- **Cost Estimator**: Advanced cost tracking and optimization
- **Configuration Manager**: JSON-based settings management

### Core Components

```python
class PlanningAgentService:
    def __init__(self, agent_id: str = None, mcp_url: str = "ws://localhost:9000")
    
    # MCP Communication
    async def connect_to_mcp(self) -> bool
    async def send_mcp_request(self, method: str, params: dict) -> dict
    
    # Core Capabilities (8 total)
    async def _plan_research(self, payload: Dict[str, Any]) -> Dict[str, Any]
    async def _analyze_information(self, payload: Dict[str, Any]) -> Dict[str, Any] 
    async def _estimate_costs(self, payload: Dict[str, Any]) -> Dict[str, Any]
    async def _chain_of_thought(self, payload: Dict[str, Any]) -> Dict[str, Any]
    async def _summarize_content(self, payload: Dict[str, Any]) -> Dict[str, Any]
    async def _extract_insights(self, payload: Dict[str, Any]) -> Dict[str, Any]
    async def _compare_sources(self, payload: Dict[str, Any]) -> Dict[str, Any]
    async def _evaluate_credibility(self, payload: Dict[str, Any]) -> Dict[str, Any]
    
    # HTTP API Endpoints
    @app.get("/health")
    @app.post("/process")
    @app.post("/capabilities")
```

### Communication Flow

1. **API Gateway** receives request
2. **MCP Server** routes to Planning Agent
3. **Planning Agent** processes via WebSocket
4. **AI Provider** accessed via MCP protocol
5. **Response** returned through same path
6. **Cost tracking** throughout process

---

## API Gateway Integration

### Request Flow

The Planning Agent integrates with the API Gateway through the following flow:

1. **Client Request** → API Gateway (`/research/plan`)
2. **API Gateway** → MCP Server (WebSocket)
3. **MCP Server** → Planning Agent Container (WebSocket)
4. **Planning Agent** → AI Provider (via MCP)
5. **Response** → Client (reverse path)

### API Gateway Endpoints

#### Research Planning Endpoint

**POST** `/research/plan`

**Request Body**:

```json
{
  "query": "Your research question",
  "context": {
    "project_id": "optional_project_id",
    "scope": "low|medium|high",
    "duration_days": 30,
    "budget_limit": 50.0
  }
}
```

**Response**:

```json
{
  "status": "completed",
  "result": {
    "plan": {
      "objectives": ["Objective 1", "Objective 2"],
      "key_areas": ["Area 1", "Area 2"],
      "questions": ["Question 1", "Question 2"],
      "sources": ["Source 1", "Source 2"],
      "outcomes": ["Outcome 1", "Outcome 2"]
    },
    "cost_estimate": {
      "estimated_cost": 5.25,
      "tokens_estimated": 15000,
      "complexity": "MEDIUM"
    },
    "agent_id": "planning-12345",
    "processing_time": 2.5
  }
}
```

### Authentication

API Gateway requests require authentication:

```bash
curl -X POST "http://localhost:8000/research/plan" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "Analyze AI trends in healthcare"}'
```

### Rate Limiting

- **Default**: 100 requests per hour per API key
- **Burst**: Up to 10 concurrent requests
- **Cost-based**: Additional limits based on estimated cost

### API Error Responses

```json
{
  "error": {
    "code": "PLANNING_ERROR",
    "message": "Failed to generate research plan",
    "details": "MCP connection timeout",
    "timestamp": "2025-07-28T01:00:00Z"
  }
}
```

---

## Core Functions

### Available Capabilities

The Planning Agent provides 8 core capabilities, each accessible via MCP protocol:

1. **plan_research** - Generate comprehensive research plans
2. **analyze_information** - Analyze and extract insights from data
3. **cost_estimation** - Provide accurate cost estimates with optimization
4. **chain_of_thought** - Perform step-by-step logical reasoning
5. **summarize_content** - Create concise summaries of content
6. **extract_insights** - Extract key insights and recommendations
7. **compare_sources** - Compare multiple information sources
8. **evaluate_credibility** - Assess source credibility and reliability

### 1. Research Planning (`plan_research`)

**Purpose**: Generate comprehensive research plans with cost optimization.

**MCP Request**:

```json
{
  "method": "research_action",
  "params": {
    "agent_type": "planning",
    "action": "plan_research",
    "task_id": "task_001",
    "payload": {
      "query": "Analyze the impact of AI on healthcare diagnostics",
      "context": {
        "scope": "medium",
        "duration_days": 14,
        "budget_limit": 25.0
      }
    }
  }
}
```

**Response Structure**:

```json
{
  "status": "completed",
  "result": {
    "query": "Analyze the impact of AI on healthcare diagnostics",
    "plan": {
      "objectives": [
        "Assess current AI diagnostic tools",
        "Evaluate accuracy improvements",
        "Identify implementation challenges"
      ],
      "key_areas": [
        "Radiology AI applications",
        "Pathology automation",
        "Clinical decision support"
      ],
      "questions": [
        "What are the accuracy rates of AI diagnostic tools?",
        "How do costs compare to traditional methods?",
        "What are the regulatory requirements?"
      ],
      "sources": [
        "Medical journals and publications",
        "Healthcare technology reports",
        "Clinical trial databases"
      ],
      "outcomes": [
        "Comprehensive diagnostic AI assessment",
        "Implementation roadmap",
        "Cost-benefit analysis"
      ]
    },
    "cost_estimate": {
      "estimated_cost": 12.75,
      "tokens_estimated": 35000,
      "complexity": "MEDIUM",
      "optimization_suggestions": [
        "Consider focused scope to reduce costs",
        "Use cached data when available"
      ]
    },
    "agent_id": "planning-12345",
    "processing_time": 2.8
  }
}
```

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
    'plan': {                        # Structured research plan (parsed from JSON)
        'objectives': List[str],     # Research objectives list
        'key_areas': List[str],      # Areas to investigate list
        'questions': List[str],      # Specific questions list
        'sources': List[str],        # Information sources list
        'outcomes': List[str],       # Expected outcomes list
        'raw_plan': str             # Full AI response (fallback)
    },
    'raw_response': str,             # Complete AI response
    'planning_model': str            # AI model used (e.g., "gpt-4")
}
```

**Enhanced JSON Planning Format**:

The agent now uses structured JSON prompts to generate more consistent, parseable research plans:

```json
{
  "objectives": ["Define research scope", "Identify key metrics"],
  "key_areas": ["Market analysis", "Technology assessment"],
  "questions": [
    "What are the market trends?",
    "Which technologies are emerging?"
  ],
  "sources": ["Industry reports", "Academic publications"],
  "outcomes": ["Comprehensive market overview", "Technology roadmap"]
}
```

**Use Cases**:

- Initial research strategy development
- Academic research planning
- Market research preparation
- Investigation roadmap creation
- **Hierarchical task planning within projects**
- **Cost-optimized research planning**

**Example**:

```python
# Basic research planning
result = await planning_agent._plan_research({
    'query': 'Impact of AI on healthcare diagnostics',
    'context': {
        'domain': 'healthcare',
        'focus': 'diagnostic_accuracy',
        'stakeholders': ['doctors', 'patients', 'hospitals'],
        'project_id': 'proj_healthcare_ai_2025',  # Hierarchical context
        'plan_id': 'plan_diagnostic_impact_study'
    }
})

# Planning with cost considerations
result = await planning_agent._plan_research({
    'query': 'Comprehensive AI market analysis',
    'context': {
        'cost_budget': 50.0,  # USD budget constraint
        'time_constraint': '2_weeks',
        'research_depth': 'comprehensive',
        'single_agent_mode': False  # Multi-agent approach
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

### 1. Hierarchical Research Workflow Integration

The Planning Agent operates seamlessly within the hierarchical project structure:

```python
# 1. Project-level Planning (Strategic Overview)
project_plan = await planning_agent._plan_research({
    'query': 'AI Healthcare Research Initiative',
    'context': {
        'project_id': 'proj_ai_healthcare_2025',
        'scope': 'strategic_overview',
        'timeline': '12_months',
        'budget_range': '100000_usd'
    }
})

# 2. Topic-specific Planning (Detailed Investigation)
topic_plan = await planning_agent._plan_research({
    'query': 'AI diagnostic accuracy in radiology',
    'context': {
        'project_id': 'proj_ai_healthcare_2025',
        'topic_id': 'topic_radiology_ai',
        'research_depth': 'comprehensive',
        'stakeholders': ['radiologists', 'technicians', 'patients']
    }
})

# 3. Task-level Analysis (After Data Collection)
task_analysis = await planning_agent._analyze_information({
    'query': 'Radiological AI accuracy studies',
    'context': {
        'task_id': 'task_accuracy_analysis',
        'plan_id': 'plan_radiology_study',
        'search_results': collected_research_data,
        'cost_constraints': {'max_cost': 25.0}
    }
})

# 4. Multi-task Synthesis (Plan Completion)
plan_synthesis = await planning_agent._synthesize_results({
    'query': 'Complete radiology AI assessment',
    'context': {
        'plan_id': 'plan_radiology_study',
        'task_results': [task1_results, task2_results, task3_results],
        'search_results': all_collected_data,
        'reasoning_outputs': [analysis1, analysis2, analysis3],
        'execution_results': additional_research
    }
})
```

### 2. Cost-Optimized Planning Workflow

The agent now supports cost-aware planning and optimization:

```python
# Cost-constrained research planning
cost_optimized_plan = await planning_agent._plan_research({
    'query': 'Market analysis with budget constraints',
    'context': {
        'cost_budget': 30.0,  # USD budget limit
        'optimization_mode': 'cost_effective',
        'single_agent_preference': True,  # 60% cost reduction
        'quality_threshold': 'good'  # vs 'excellent' for comprehensive
    }
})

# Multi-agent vs single-agent planning comparison
comprehensive_plan = await planning_agent._plan_research({
    'query': 'Detailed competitive analysis',
    'context': {
        'research_mode': 'comprehensive',  # Multi-agent approach
        'cost_budget': 100.0,
        'quality_threshold': 'excellent'
    }
})

efficient_plan = await planning_agent._plan_research({
    'query': 'Detailed competitive analysis',
    'context': {
        'research_mode': 'efficient',  # Single-agent approach
        'cost_budget': 40.0,
        'quality_threshold': 'good'
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

### 3. Standalone Usage

Individual functions can be used independently for specific tasks:

```python
# Quick content summarization with cost tracking
summary = await planning_agent._summarize_content({
    'content': long_article,
    'max_length': 300,
    'context': {
        'task_id': 'task_summary_001',
        'cost_tracking': True
    }
})

# Insight extraction with hierarchical context
insights = await planning_agent._extract_insights({
    'content': research_report,
    'context': {
        'project_id': 'proj_market_research',
        'plan_id': 'plan_competitor_analysis'
    }
})

# Source comparison for validation
comparison = await planning_agent._compare_sources({
    'sources': [source1, source2, source3],
    'context': {
        'validation_purpose': 'fact_checking',
        'credibility_threshold': 0.8
    }
})
```

### 4. Batch Processing

Multiple operations with cost optimization:

```python
async def cost_optimized_batch_analysis(content_list, budget_limit: float):
    results = []
    total_cost = 0.0

    for content in content_list:
        # Estimate cost before processing
        estimated_cost = await estimate_processing_cost(content)

        if total_cost + estimated_cost > budget_limit:
            # Switch to efficient mode or skip
            continue

        # Process with cost tracking
        summary = await planning_agent._summarize_content({
            'content': content,
            'context': {'cost_tracking': True}
        })

        insights = await planning_agent._extract_insights({
            'content': content,
            'context': {'cost_tracking': True}
        })

        results.append({
            'summary': summary,
            'insights': insights,
            'processing_cost': summary.get('cost', 0) + insights.get('cost', 0)
        })

        total_cost += results[-1]['processing_cost']

    return results, total_cost
```

---

## Configuration

### AI Client Configuration

The Planning Agent supports multiple AI providers with enhanced configuration:

```json
{
  "ai_providers": {
    "openai": {
      "model": "gpt-4o",
      "temperature": 0.7,
      "max_tokens": 2000,
      "cost_per_1k_tokens": {
        "input": 0.005,
        "output": 0.015
      }
    },
    "xai": {
      "model": "grok-beta",
      "temperature": 0.7,
      "max_tokens": 2000,
      "cost_per_1k_tokens": {
        "input": 0.003,
        "output": 0.012
      }
    }
  },
  "planning_agent": {
    "default_provider": "openai",
    "fallback_provider": "xai",
    "cost_optimization": {
      "enable_single_agent_mode": true,
      "cost_threshold_usd": 10.0,
      "auto_approve_threshold": 5.0
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

### Example 1: Hierarchical Academic Research Planning

```python
import asyncio
from src.agents.planning_agent import PlanningAgent
from src.config.config_manager import ConfigManager

async def hierarchical_academic_research():
    config_manager = ConfigManager()
    agent = PlanningAgent(config_manager)
    await agent._initialize_agent()

    try:
        # Project-level strategic planning
        project_plan = await agent._plan_research({
            'query': 'Machine Learning in Climate Science Research Initiative',
            'context': {
                'project_id': 'proj_ml_climate_2025',
                'academic_level': 'graduate',
                'research_type': 'multi_year_initiative',
                'timeline': '3_years',
                'budget_estimate': 150000,
                'scope': 'strategic_overview'
            }
        })

        # Topic-specific detailed planning
        topic_plan = await agent._plan_research({
            'query': 'ML models for climate prediction accuracy',
            'context': {
                'project_id': 'proj_ml_climate_2025',
                'topic_id': 'topic_prediction_models',
                'research_type': 'systematic_review',
                'timeline': '6_months',
                'focus_areas': ['prediction_models', 'data_analysis', 'validation'],
                'cost_budget': 25.0  # USD for this planning phase
            }
        })

        # Task-level execution planning
        task_plan = await agent._plan_research({
            'query': 'Comparative analysis of LSTM vs Transformer models for climate data',
            'context': {
                'project_id': 'proj_ml_climate_2025',
                'topic_id': 'topic_prediction_models',
                'plan_id': 'plan_model_comparison',
                'task_type': 'comparative_analysis',
                'single_agent_mode': True,  # Cost optimization
                'research_depth': 'focused'
            }
        })

        print("Hierarchical Research Plans Generated:")
        print(f"Project Objectives: {project_plan['plan']['objectives']}")
        print(f"Topic Key Areas: {topic_plan['plan']['key_areas']}")
        print(f"Task Questions: {task_plan['plan']['questions']}")

    finally:
        await agent._cleanup_agent()

# Run the example
asyncio.run(hierarchical_academic_research())
```

### Example 2: Cost-Optimized Market Research

```python
async def cost_optimized_market_research():
    config_manager = ConfigManager()
    agent = PlanningAgent(config_manager)
    await agent._initialize_agent()

    try:
        # High-budget comprehensive analysis
        comprehensive_plan = await agent._plan_research({
            'query': 'Complete electric vehicle market analysis 2025',
            'context': {
                'project_id': 'proj_ev_market_analysis',
                'cost_budget': 75.0,  # Higher budget allows multi-agent
                'research_mode': 'comprehensive',
                'quality_target': 'excellent',
                'coverage': 'global'
            }
        })

        # Cost-constrained efficient analysis
        efficient_plan = await agent._plan_research({
            'query': 'Electric vehicle market key trends 2025',
            'context': {
                'project_id': 'proj_ev_market_analysis',
                'cost_budget': 20.0,  # Limited budget
                'research_mode': 'efficient',
                'single_agent_mode': True,  # 60% cost reduction
                'quality_target': 'good',
                'coverage': 'regional'
            }
        })

        # Analyze collected market data with cost tracking
        analysis = await agent._analyze_information({
            'query': 'EV market trends analysis',
            'context': {
                'task_id': 'task_trend_analysis',
                'plan_id': 'plan_ev_research',
                'cost_tracking': True,
                'search_results': [
                    {
                        'title': 'EV Market Report 2024',
                        'content': 'Electric vehicle sales increased by 40%...',
                        'source': 'MarketResearch.com',
                        'credibility_score': 0.9
                    },
                    {
                        'title': 'Global EV Adoption Trends',
                        'content': 'Regional adoption varies significantly...',
                        'source': 'BloombergNEF',
                        'credibility_score': 0.95
                    }
                ]
            }
        })

        print("Cost-Optimized Research Results:")
        print(f"Comprehensive Plan Cost Estimate: ${comprehensive_plan.get('estimated_cost', 0):.2f}")
        print(f"Efficient Plan Cost Estimate: ${efficient_plan.get('estimated_cost', 0):.2f}")
        print(f"Analysis Cost: ${analysis.get('actual_cost', 0):.2f}")

    finally:
        await agent._cleanup_agent()
```

### Example 3: Complete Hierarchical Research Workflow

```python
async def complete_hierarchical_workflow():
    """
    Demonstrates the complete hierarchical research workflow from
    project creation through task execution and synthesis.
    """
    config_manager = ConfigManager()
    agent = PlanningAgent(config_manager)
    await agent._initialize_agent()

    try:
        # 1. Project-level strategic planning
        project_strategy = await agent._plan_research({
            'query': 'AI-Powered Healthcare Diagnostics Research Program',
            'context': {
                'project_scope': 'multi_year_research_initiative',
                'funding_level': 'major_grant',
                'stakeholders': ['hospitals', 'tech_companies', 'researchers'],
                'timeline': '3_years',
                'expected_impact': 'clinical_implementation'
            }
        })

        # 2. Cross-topic synthesis
        final_synthesis = await agent._synthesize_results({
            'query': 'Complete AI healthcare diagnostics research synthesis',
            'context': {
                'project_strategy': project_strategy,
                'synthesis_goal': 'actionable_recommendations'
            }
        })

        return {
            'project_strategy': project_strategy,
            'final_synthesis': final_synthesis
        }

    finally:
        await agent._cleanup_agent()

# Run the complete workflow
workflow_result = asyncio.run(complete_hierarchical_workflow())
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

---

## Cost Estimation

### Sophisticated Cost Estimation System

The Planning Agent includes a sophisticated cost estimation system providing maximum accuracy for research planning:

#### Features

- **Real-time Cost Tracking**: Monitor costs as they occur
- **Provider-specific Pricing**: OpenAI and XAI pricing models
- **Complexity Assessment**: Intelligent LOW/MEDIUM/HIGH complexity scoring
- **Token Estimation**: Detailed input/output token breakdown
- **Optimization Recommendations**: Context-aware cost reduction suggestions
- **Threshold Monitoring**: Session and daily cost limits with alerts
- **Multi-agent Analysis**: Cost comparison between single vs multi-agent approaches

#### Cost Estimation Response

```json
{
  "cost_breakdown": {
    "ai_operations": {
      "estimated_tokens": 35000,
      "input_tokens": 26250,
      "output_tokens": 8750,
      "cost_per_1k_input": 0.00015,
      "cost_per_1k_output": 0.0006,
      "total_ai_cost": 9.1875,
      "complexity_level": "MEDIUM",
      "complexity_multiplier": 2.5,
      "provider": "openai",
      "model": "gpt-4o-mini"
    },
    "summary": {
      "ai_cost": 9.1875,
      "traditional_cost": 0.0,
      "total": 9.1875,
      "currency": "USD",
      "cost_per_day": 0.656,
      "cost_per_agent": 2.297
    },
    "thresholds": {
      "session_warning": 1.0,
      "session_limit": 5.0,
      "daily_limit": 50.0,
      "emergency_stop": 100.0
    },
    "optimization_suggestions": [
      "Consider breaking down into smaller sub-tasks",
      "Use caching to avoid redundant analysis"
    ]
  }
}
```

#### Cost Optimization Strategies

1. **Single Agent Mode**: 60% cost reduction for focused tasks
2. **Complexity Reduction**: Lower complexity scoring through query optimization
3. **Token Management**: Efficient prompt design and context management
4. **Batch Processing**: Group similar operations to reduce API calls
5. **Caching**: Reuse previous results when applicable

### Cost Configuration

Cost estimation settings in `config/config.json`:

```json
{
  "cost_settings": {
    "token_costs": {
      "openai": {
        "gpt-4o-mini": {
          "input": 0.00015,
          "output": 0.0006
        }
      },
      "xai": {
        "grok-beta": {
          "input": 0.0001,
          "output": 0.0005
        }
      }
    },
    "cost_thresholds": {
      "session_warning": 1.0,
      "session_limit": 5.0,
      "daily_limit": 50.0,
      "emergency_stop": 100.0
    },
    "complexity_multipliers": {
      "LOW": 1.0,
      "MEDIUM": 2.5,
      "HIGH": 5.0
    }
  },
  "research_manager": {
    "provider": "openai",
    "model": "gpt-4o-mini"
  }
}
```

---

## Testing and Usage Examples

### Test Scripts Available

1. **`test_planning_agent_api.py`** - Comprehensive API Gateway integration test
2. **`test_cost_estimation_comprehensive.py`** - Cost estimation system validation
3. **Container tests** - Docker container functionality tests

### Running API Gateway Tests

```bash
# Comprehensive test suite
python test_planning_agent_api.py

# Quick test with custom query
python test_planning_agent_api.py "Analyze AI trends in healthcare"

# Test specific endpoints
curl -X POST "http://localhost:8000/research/plan" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the benefits of renewable energy?",
    "context": {
      "scope": "medium",
      "duration_days": 14,
      "budget_limit": 25.0
    }
  }'
```

### Example API Responses

#### Successful Research Plan Response

```json
{
  "status": "completed",
  "result": {
    "query": "Analyze AI trends in healthcare",
    "plan": {
      "objectives": [
        "Identify current AI applications in healthcare",
        "Assess market growth and adoption rates",
        "Evaluate impact on patient outcomes"
      ],
      "key_areas": [
        "Diagnostic AI tools",
        "Treatment optimization",
        "Healthcare data analytics"
      ],
      "questions": [
        "Which AI applications show highest adoption?",
        "What are the accuracy improvements?",
        "How do costs compare to traditional methods?"
      ],
      "sources": [
        "Medical technology journals",
        "Healthcare industry reports",
        "Clinical trial databases"
      ],
      "outcomes": [
        "Comprehensive AI healthcare trend analysis",
        "Market opportunity assessment",
        "Implementation roadmap"
      ]
    },
    "cost_estimate": {
      "estimated_cost": 15.25,
      "tokens_estimated": 42000,
      "complexity": "MEDIUM",
      "optimization_suggestions": [
        "Consider focused scope on specific medical areas",
        "Use existing research summaries to reduce analysis time"
      ]
    },
    "agent_id": "planning-12345",
    "processing_time": 3.2
  }
}
```

### Integration Best Practices

1. **Error Handling**: Always check response status and handle errors gracefully
2. **Rate Limiting**: Respect API rate limits and implement backoff strategies  
3. **Cost Monitoring**: Monitor cost estimates and set appropriate budget limits
4. **Timeout Handling**: Set reasonable timeouts for API requests (30s recommended)
5. **Authentication**: Use proper API tokens for production environments

### Monitoring and Debugging

#### Logs Location

- **Container logs**: `docker logs eunice-planning-agent`
- **API Gateway logs**: Check API Gateway service logs
- **MCP Server logs**: Monitor MCP WebSocket connections

#### Health Checks

```bash
# Check container health
curl http://localhost:8007/health

# Check API Gateway health  
curl http://localhost:8000/health

# Test MCP connection
python -c "
import asyncio
import websockets
import json

async def test_mcp():
    async with websockets.connect('ws://localhost:9000') as ws:
        await ws.send(json.dumps({'method': 'ping'}))
        response = await ws.recv()
        print(json.loads(response))

asyncio.run(test_mcp())
"
```

---

This documentation provides a comprehensive guide to the Planning Agent's containerized architecture, API integration, and sophisticated cost estimation capabilities. The agent operates exclusively via MCP protocol, ensuring architectural compliance while providing maximum accuracy in research planning and cost optimization.
