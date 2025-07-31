# MCP Task Capabilities Documentation

## Overview

This document collates and documents all task capabilities across MCP agents and services in the Eunice Research Platform. Each agent and service provides specific task types that can be used to build a generic task API.

---

## Core MCP Services

### 1. AI Service (`ai-service`)

**Location**: `/services/ai-service/`  
**Agent Type**: `ai_service`

#### Task Types

- `ai_chat_completion` - Chat completion with various AI providers
- `ai_embedding` - Generate text embeddings  
- `ai_model_info` - Get model information and capabilities
- `ai_usage_stats` - Retrieve AI usage statistics and metrics

#### Supported Providers

- OpenAI (GPT-4o-mini, GPT-4, etc.)
- Anthropic (Claude models)
- xAI (Grok models)

---

### 2. MCP Server (`mcp-server`)

**Location**: `/services/mcp-server/`  
**Agent Type**: `mcp_server`

#### Core Functions

- Agent registration and discovery
- Task routing and distribution
- Load balancing and health monitoring
- WebSocket-based communication

#### Task Management

- `task_request` - Route tasks to appropriate agents
- `task_result` - Handle task completion results
- `agent_register` - Register new agents
- `agent_status` - Monitor agent health

---

## Research Agents

### 3. Database Agent (`database`)

**Location**: `/agents/database/`  
**Agent Type**: `database`

#### Task Types

- `create_project` - Create new research projects
- `update_project` - Update project information
- `delete_project` - Remove projects
- `get_project` - Retrieve project details
- `create_topic` - Create research topics
- `update_topic` - Update topic information  
- `delete_topic` - Remove topics
- `get_topic` - Retrieve topic details
- `create_research_topic` - Create research topics
- `update_research_topic` - Update research topics
- `delete_research_topic` - Remove research topics
- `get_research_topic` - Retrieve research topic details
- `create_plan` - Create research plans
- `update_plan` - Update plan information
- `delete_plan` - Remove plans
- `get_plan` - Retrieve plan details
- `create_research_plan` - Create research plans
- `update_research_plan` - Update research plans
- `delete_research_plan` - Remove research plans
- `get_research_plan` - Retrieve research plan details
- `create_task` - Create research tasks
- `update_task` - Update task information
- `delete_task` - Remove tasks
- `get_task` - Retrieve task details
- `database_operations` - General database operations
- `data_storage` - Data storage and retrieval
- `query_processing` - Process database queries
- `transaction_management` - Manage database transactions

---

### 4. Literature Agent (`literature`)

**Location**: `/agents/literature/`  
**Agent Type**: `literature`

#### Task Types

- `search_academic_papers` - Search for academic publications
- `search_literature` - Comprehensive literature search
- `normalize_records` - Normalize bibliographic records
- `deduplicate_results` - Remove duplicate publications
- `multi_source_search` - Search across multiple databases
- `bibliographic_search` - Specialized bibliographic searches

#### Supported Sources

- Semantic Scholar (AI-powered academic search)
- PubMed (Medical and life sciences)
- arXiv (Preprint server)
- CrossRef (DOI-based metadata)

---

### 5. Planning Agent (`planning`)

**Location**: `/agents/planning/`  
**Agent Type**: `planning`

#### Task Types

- `plan_research` - Generate comprehensive research plans
- `analyze_information` - Analyze and extract insights from data
- `cost_estimation` - Provide accurate cost estimates with optimization
- `chain_of_thought` - Perform step-by-step logical reasoning
- `summarize_content` - Create concise summaries of content
- `extract_insights` - Extract key insights and recommendations
- `compare_sources` - Compare multiple information sources
- `evaluate_credibility` - Assess source credibility and reliability

#### Core Capabilities

- Research Planning and Strategy
- Information Analysis and Synthesis
- Result Synthesis and Combination
- Chain of Thought Reasoning
- Content Processing and Summarization
- Source Evaluation and Comparison
- Cost Estimation and Optimization
- MCP Protocol Compliance

---

### 6. Memory Agent (`memory`)

**Location**: `/agents/memory/`  
**Agent Type**: `memory`

#### Task Types

- `store_memory` - Store research context and findings
- `retrieve_memory` - Retrieve stored information
- `search_knowledge` - Search knowledge base
- `manage_knowledge_graph` - Manage knowledge graph operations
- `consolidate_memory` - Consolidate and organize stored information

---

### 7. Synthesis Agent (`synthesis`)

**Location**: `/agents/synthesis/`  
**Agent Type**: `synthesis`

#### Task Types

- `data_extraction` - Extract structured data from studies
- `evidence_synthesis` - Synthesize evidence from multiple sources
- `meta_analysis` - Perform statistical meta-analysis
- `statistical_aggregation` - Aggregate statistical data
- `evidence_table_generation` - Generate evidence tables
- `outcome_extraction` - Extract outcome measures
- `forest_plot_generation` - Generate forest plots
- `heterogeneity_assessment` - Assess statistical heterogeneity
- `narrative_synthesis` - Perform narrative synthesis
- `thematic_synthesis` - Conduct thematic analysis
- `framework_synthesis` - Apply theoretical frameworks

#### Statistical Methods

- Fixed and random effects meta-analysis
- I² heterogeneity assessment
- Cohen's d effect size calculation
- Forest plot generation
- Evidence quality assessment

---

### 8. Writer Agent (`writer`)

**Location**: `/agents/writer/`  
**Agent Type**: `writer`

#### Task Types

- `manuscript_generation` - Generate formatted manuscripts
- `citation_formatting` - Format citations in various styles
- `bibliography_creation` - Create bibliographies
- `document_export` - Export documents to different formats
- `multi_format_support` - Support multiple document formats
- `reference_management` - Manage references and citations
- `template_application` - Apply document templates
- `academic_writing` - Academic writing assistance
- `document_structuring` - Structure documents properly
- `figure_table_integration` - Integrate figures and tables
- `cross_referencing` - Create cross-references
- `version_control` - Document version management
- `apply_template` - Apply document templates
- `structure_document` - Structure document content
- `integrate_figures` - Integrate figures and tables
- `create_cross_references` - Create cross-references
- `format_document` - Format document content
- `generate_outline` - Generate document outlines

#### Supported Formats

- Markdown
- LaTeX  
- DOCX
- PDF
- HTML

#### Citation Styles

- APA
- Vancouver
- Harvard
- Chicago

---

### 9. Research Manager (`research-manager`)

**Location**: `/agents/research-manager/`  
**Agent Type**: `research_manager`

#### Task Types

- `coordinate_research` - Coordinate multi-agent research tasks
- `estimate_costs` - Estimate research costs
- `track_progress` - Track research progress
- `delegate_tasks` - Delegate tasks to appropriate agents
- `manage_workflows` - Manage research workflows
- `approve_actions` - Approve research actions

#### Research Stages

- `PLANNING` - Research planning phase
- `LITERATURE_REVIEW` - Literature review phase
- `REASONING` - Reasoning and analysis phase
- `EXECUTION` - Execution phase
- `SYNTHESIS` - Synthesis phase
- `SYSTEMATIC_REVIEW` - Systematic review phase
- `COMPLETE` - Completed research
- `FAILED` - Failed research

---

### 10. Screening Agent (`screening`)

**Location**: `/agents/screening/`  
**Agent Type**: `screening`

#### Task Types

- `screen_studies` - Screen studies for inclusion/exclusion
- `extract_metadata` - Extract study metadata
- `assess_quality` - Assess study quality
- `resolve_conflicts` - Resolve screening conflicts
- `generate_flowchart` - Generate PRISMA flowcharts

---

### 11. Executor Agent (`executor`)

**Location**: `/agents/executor/`  
**Agent Type**: `executor`

#### Task Types

- `execute_research_task` - Execute general research tasks
- `coordinate_agents` - Coordinate multiple agents
- `validate_results` - Validate research results
- `quality_control` - Perform quality control checks

---

## API Gateway Integration

### Current Task Type Limitation

The current API Gateway uses a limited TaskType definition:

```python
TaskType = Literal["research", "analysis", "synthesis", "validation"]
```

### Generic Task API Requirements

Based on the analysis above, a generic task API should support all the documented task types across agents. The suggested implementation approach is:

1. **Dynamic Task Type Registry**: Replace hardcoded Literal with a registry-based system
2. **Agent-Specific Task Handlers**: Route tasks based on agent capabilities  
3. **Polymorphic Task Models**: Support different payload structures per task type
4. **Task Validation**: Validate task types against agent capabilities
5. **Fallback Mechanisms**: Handle unknown task types gracefully

### Recommended Task Categories

1. **Database Operations**: All CRUD operations for projects, topics, plans, tasks
2. **Literature Operations**: Search, retrieval, normalization, deduplication
3. **Analysis Operations**: Planning, cost estimation, information analysis
4. **Synthesis Operations**: Evidence synthesis, meta-analysis, statistical operations
5. **Writing Operations**: Document generation, formatting, citation management
6. **Coordination Operations**: Multi-agent coordination, workflow management
7. **AI Operations**: Chat completion, embeddings, model operations
8. **Memory Operations**: Storage, retrieval, knowledge management
9. **Screening Operations**: Study screening, quality assessment
10. **Execution Operations**: Task execution, validation, quality control

---

## Implementation Notes

### MCP Protocol Compliance

All agents follow the MCP protocol for task communication:

- JSON-RPC 2.0 message format
- WebSocket-based communication
- Standardized task request/response patterns
- Agent registration and capability discovery

### Task Execution Patterns

1. **Request Format**: `{"method": "task/execute", "params": {"task_type": "...", "data": {...}}}`
2. **Response Format**: `{"result": {"status": "completed|failed", "data": {...}}}`
3. **Error Handling**: Standardized error codes and messages
4. **Timeout Management**: Configurable timeouts per task type

### Extension Points

The system is designed for extensibility:

- New agents can register additional task types
- Task handlers can be added dynamically
- Agent capabilities are discoverable at runtime
- Load balancing supports multiple instances of each agent type

---

*Last Updated: January 31, 2025*  
*This document represents the complete task capability mapping across the Eunice Research Platform's MCP architecture.*
