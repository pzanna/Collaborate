# Eunice Function Map

## Overview
This document lists the functions available within the Eunice Research Platform.

## Project Functions

### Create Project
Function name: create_project
Description: Creates a new research project that serves as the top-level container for organizing research topics, plans, and tasks
Trigger: User
API: /v2/projects
Input: { "name": "string", "description": "string", "metadata": {}}
Database table: projects
Unit test: None

### Update Project
Function name: update_project
Description: Updates an existing project's details including name, description, status, and metadata
Trigger: User
API: /v2/projects/{project_id}
Input: { "project_id": "string", "name": "string", "description": "string", "status": "string", "metadata": {}}
Database table: projects
Unit test: None

### Delete Project
Function name: delete_project
Description: Permanently removes a project and all its associated research topics, plans, and tasks from the system
Trigger: User
API: /v2/projects/{project_id}
Input: { "project_id": "string"}
Database table: projects
Unit test: None

### List Projects
Function name: list_projects
Description: Retrieves a list of all projects with optional filtering by status and pagination support
Trigger: User
API: /v2/projects
Input: { "status": "string (optional)", "limit": "number (optional)"}
Database table: projects
Unit test: None

### Get Project
Function name: get_project
Description: Retrieves detailed information about a specific project including metadata and statistics
Trigger: User
API: /v2/projects/{project_id}
Input: { "project_id": "string"}
Database table: projects
Unit test: None

### Get Project Statistics
Function name: get_project_stats
Description: Retrieves comprehensive project-level statistics aggregating data across all topics, plans, and tasks
Trigger: User
API: /v2/projects/{project_id}/stats
Input: { "project_id": "string"}
Database table: projects (aggregated data)
Unit test: None

### Get Project Hierarchy
Function name: get_project_hierarchy
Description: Retrieves the complete hierarchical structure of a project including all topics, plans, and tasks
Trigger: User
API: /v2/projects/{project_id}/hierarchy
Input: { "project_id": "string"}
Database table: Multiple (projects, research_topics, research_plans, tasks)
Unit test: None

## Research Topic Functions

### Create Research Topic
Function name: create_research_topic
Description: Creates a new research topic within a project to define specific areas of investigation or research focus
Trigger: User
API: /v2/projects/{project_id}/topics
Input: { "project_id": "string", "name": "string", "description": "string", "metadata": {}}
Database table: research_topics
Unit test: None

### Update Research Topic
Function name: update_research_topic
Description: Updates an existing research topic's properties including name, description, status, and metadata
Trigger: User
API: /v2/topics/{topic_id}
Input: { "topic_id": "string", "name": "string", "description": "string", "status": "string", "metadata": {}}
Database table: research_topics
Unit test: None

### Delete Research Topic
Function name: delete_research_topic
Description: Permanently removes a research topic and all its associated research plans and tasks
Trigger: User
API: /v2/topics/{topic_id}
Input: { "topic_id": "string"}
Database table: research_topics
Unit test: None

### List Research Topics
Function name: list_research_topics
Description: Retrieves all research topics within a project with optional status filtering
Trigger: User
API: /v2/projects/{project_id}/topics
Input: { "project_id": "string", "status": "string (optional)"}
Database table: research_topics
Unit test: None

### Get Research Topic
Function name: get_research_topic
Description: Retrieves detailed information about a specific research topic including statistics and metadata
Trigger: User
API: /v2/topics/{topic_id}
Input: { "topic_id": "string"}
Database table: research_topics
Unit test: None

### Get Research Topic by Project
Function name: get_research_topic_by_project
Description: Retrieves a specific research topic within the context of its parent project
Trigger: User
API: /v2/projects/{project_id}/topics/{topic_id}
Input: { "project_id": "string", "topic_id": "string"}
Database table: research_topics
Unit test: None

### Get Research Topic Statistics
Function name: get_topic_stats
Description: Retrieves comprehensive statistics for a research topic including plan counts, task progress, and cost analysis
Trigger: User
API: /v2/topics/{topic_id}/stats
Input: { "topic_id": "string"}
Database table: research_topics (aggregated data)
Unit test: None

## Research Plan Functions

### Create Research Plan (Depricated)
Function name: create_research_plan
Description: Creates a structured research plan within a topic, defining the methodology, approach, and detailed structure for conducting research
Trigger: User
API: /v2/topics/{topic_id}/plans
Input: { "topic_id": "string"}
Database table: research_plans
Unit test: None

### Approve Research Plan
Function name: approve_research_plan
Description: Approves a research plan and updates its status to active, enabling task execution
Trigger: User
API: /v2/plans/{plan_id}/approve
Input: { "plan_id": "string"}
Database table: research_plans
Unit test: None

### Update Research Plan
Function name: update_research_plan
Description: Updates an existing research plan's details, methodology, structure, literature results, and approval status
Trigger: User
API: /v2/plans/{plan_id}
Input: { "plan_id": "string", "name": "string", "description": "string", "plan_type": "string", "status": "string", "plan_structure": {}, "initial_literature_results": {}, "reviewed_literature_results": {}, "metadata": {}}
Database table: research_plans
Unit test: None

### Delete Research Plan
Function name: delete_research_plan
Description: Permanently removes a research plan and all its associated tasks and execution data
Trigger: User
API: /v2/plans/{plan_id}
Input: { "plan_id": "string"}
Database table: research_plans
Unit test: None

### List Research Plans
Function name: list_research_plans
Description: Retrieves all research plans within a topic with filtering and pagination options
Trigger: User
API: /v2/topics/{topic_id}/plans
Input: { "topic_id": "string"}
Database table: research_plans
Unit test: None

### Get Research Plan
Function name: get_research_plan
Description: Retrieves detailed information about a specific research plan including structure, literature results, and task statistics
Trigger: User
API: /v2/plans/{plan_id}
Input: { "plan_id": "string"}
Database table: research_plans
Unit test: None

### Get Research Plan Statistics
Function name: get_plan_stats
Description: Retrieves detailed statistics for a research plan including task completion rates and cost tracking
Trigger: User
API: /v2/plans/{plan_id}/stats
Input: { "plan_id": "string"}
Database table: research_plans (aggregated data)
Unit test: None

### Generate AI Research Plan
Function name: generate_ai_research_plan
Description: Creates an AI-powered research plan with cost estimation and automated structure generation
Trigger: User
API: /v2/topics/{topic_id}/ai-plans
Input: { "topic_id": "string"}
Database table: research_plans
AI Prompt: create_research_plan.json
Prompt fields: research_topics({name}, {description})
Unit test: None

## Task Functions

### Create Task
Function name: create_task
Description: Creates a general task within a research plan to represent individual work units or activities
Trigger: User
API: MCP Direct (via database service)
Input: { "plan_id": "string", "name": "string", "description": "string", "task_type": "string", "task_order": "number", "metadata": {}}
Database table: tasks
Unit test: None

### Update Task
Function name: update_task
Description: Updates an existing task's properties including name, description, type, execution order, and status
Trigger: User
API: MCP Direct (via database service)
Input: { "task_id": "string", "name": "string", "description": "string", "task_type": "string", "task_order": "number", "status": "string", "metadata": {}}
Database table: tasks
Unit test: None

### Delete Task
Function name: delete_task
Description: Permanently removes a task from the system along with any associated execution data
Trigger: User
API: MCP Direct (via database service)
Input: { "task_id": "string"}
Database table: tasks
Unit test: None

## Research Task Functions

### Create Research Task
Function name: create_research_task
Description: Creates a specialized research task with enhanced tracking capabilities including execution stages and research-specific metadata
Trigger: User
API: MCP Direct (via database service)
Input: { "plan_id": "string", "name": "string", "description": "string", "task_type": "string", "task_order": "number", "stage": "string", "metadata": {}}
Database table: research_tasks
Unit test: None

### Update Research Task
Function name: update_research_task
Description: Updates a research task's properties including execution stage, status, and research-specific parameters
Trigger: User
API: MCP Direct (via database service)
Input: { "task_id": "string", "name": "string", "description": "string", "task_type": "string", "task_order": "number", "status": "string", "stage": "string", "metadata": {}}
Database table: research_tasks
Unit test: None

### Delete Research Task
Function name: delete_research_task
Description: Permanently removes a research task and all its execution history and stage tracking data
Trigger: User
API: MCP Direct (via database service)
Input: { "task_id": "string"}
Database table: research_tasks

### Execute Research Task
Function name: execute_research_task
Description: Initiates a research task execution with specified parameters and coordinates with research agents
Trigger: User
API: /v2/topics/{topic_id}/execute
Input: { "topic_id": "string", "task_type": "string", "depth": "string"}
Database table: Multiple (coordinated execution)
Unit test: None

### Get Execution Progress
Function name: get_execution_progress
Description: Retrieves real-time progress information for an active research execution including current stage and completion percentage
Trigger: User
API: /v2/executions/{execution_id}/progress
Input: { "execution_id": "string"}
Database table: execution_tracking (or in-memory tracking)
Unit test: None

## Literature Record Functions

### Create Literature Record
Function name: create_literature_record
Description: Creates a new literature record to store and organize academic papers, articles, and publications related to research projects
Trigger: User
API: MCP Direct (via database service)
Input: { "project_id": "string", "title": "string", "authors": [], "doi": "string", "external_id": "string", "year": "number", "journal": "string", "abstract": "string", "url": "string", "citation_count": "number", "source": "string", "publication_type": "string", "mesh_terms": [], "categories": [], "metadata": {}}
Database table: literature_records
Unit test: None

### Update Literature Record
Function name: update_literature_record
Description: Updates an existing literature record's bibliographic information, metadata, categorization, and citation data
Trigger: User
API: MCP Direct (via database service)
Input: { "record_id": "string", "title": "string", "authors": [], "doi": "string", "external_id": "string", "year": "number", "journal": "string", "abstract": "string", "url": "string", "citation_count": "number", "source": "string", "publication_type": "string", "mesh_terms": [], "categories": [], "metadata": {}}
Database table: literature_records
Unit test: None

### Delete Literature Record
Function name: delete_literature_record
Description: Permanently removes a literature record from the system along with any associated annotations and categorizations
Trigger: User
API: MCP Direct (via database service)
Input: { "record_id": "string"}
Database table: literature_records
Unit test: None

## Search Term Optimization Functions

### Create Search Term Optimization
Function name: create_search_term_optimization
Description: Creates optimized search terms and queries for improved literature discovery across multiple academic databases and sources
Trigger: User
API: MCP Direct (via database service)
Input: { "source_type": "string", "source_id": "string", "original_query": "string", "optimized_terms": [], "optimization_context": {}, "target_databases": [], "expires_at": "string", "metadata": {}}
Database table: search_term_optimizations
Unit test: None

### Update Search Term Optimization
Function name: update_search_term_optimization
Description: Updates existing search term optimizations with refined queries, additional target databases, or updated optimization context
Trigger: User
API: MCP Direct (via database service)
Input: { "optimization_id": "string", "original_query": "string", "optimized_terms": [], "optimization_context": {}, "target_databases": [], "expires_at": "string", "metadata": {}}
Database table: search_term_optimizations
Unit test: None

### Delete Search Term Optimization
Function name: delete_search_term_optimization
Description: Permanently removes a search term optimization record and its associated optimization data
Trigger: User
API: MCP Direct (via database service)
Input: { "optimization_id": "string"}
Database table: search_term_optimizations
Unit test: None

## System Health Functions

### Health Check
Function name: health_check
Description: Provides basic health status of the API Gateway service and its core dependencies
Trigger: System/User
API: /health
Input: {}
Database table: None (service status)
Unit test: None

### System Status
Function name: system_status
Description: Provides detailed status information about all connected services and their operational state
Trigger: System/User
API: /status
Input: {}
Database table: None (service status)
Unit test: None

### System Metrics
Function name: system_metrics
Description: Provides performance metrics and operational statistics for monitoring and debugging
Trigger: System/User
API: /metrics
Input: {}
Database table: None (runtime metrics)
Unit test: None


## 🧠 Example: Task Flow – "Generate AI Research Plan"

1. UI sends: `POST /v2/topics/{topic_id}/ai-plans`
2. API Gateway:
   - Validates request and checks topic exists
   - Constructs MCP Task: `coordinate_research` with plan generation context
3. Task routed via MCP to **Research Manager**
4. Research Manager:
   - Calls DBService tool: `get_research_topic` to fetch topic details
   - Loads prompt configuration from JSON: `create_research_plan.json`
   - Processes AI model response using configured template
   - Calls DBService tool: `create_research_plan` with structured plan data
5. API Gateway receives plan creation confirmation
6. Returns ResearchPlanResponse with plan details, cost estimates, and approval status

