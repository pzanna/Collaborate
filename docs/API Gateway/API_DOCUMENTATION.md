# Eunice Research Platform API Documentation

**Version**: v0.3.1  
**Last Updated**: July 30, 2025  
**Test Status**: ✅ Core functionality verified (90% operations working)

## Overview

The Eunice Research Platform provides a comprehensive REST API for managing hierarchical research projects. The API follows RESTful principles and uses JSON for data exchange with a hierarchical structure: **Projects → Topics → Research Plans → Tasks**.

**Base URL**: `http://localhost:8001`  
**API Version**: v2 (Current)  
**Documentation**: Available at `/docs` (Swagger UI) and `/redoc` (ReDoc)  
**Testing Results**:

- [Detailed Test Results](../testing/API_TESTING_RESULTS_v031.md) - Comprehensive testing evidence
- [Testing Checklist](../testing/API_TESTING_CHECKLIST_v031.md) - Complete verification checklist

## Architecture

The API uses a **dual database access pattern** for optimal performance:

- **Write Operations (CREATE)**: API Gateway → MCP Server → Database Agent → PostgreSQL
- **Read Operations (LIST/GET)**: API Gateway → Native Database Client → PostgreSQL  
- **Update/Delete Operations**: Currently experiencing routing issues (see Known Issues)

## Authentication

Currently, the API does not require authentication. This will be implemented in Version 0.3.2 with JWT tokens.

## Known Issues (v0.3.1)

- **Individual Resource Routing**: Some `GET /v2/plans/{id}`, `PUT`, and `DELETE` endpoints for Research Plans have routing issues
- **Update/Delete Persistence**: Task and Plan updates may not persist despite success responses
- **Workaround**: Core CREATE and LIST operations work perfectly for all use cases

## Response Format

All API responses follow a consistent format:

### Success Response

```json
{
  "id": "unique-identifier",
  "data": { ... },
  "timestamp": "2025-07-28T10:30:00Z"
}
```

### Error Response

```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "timestamp": "2025-07-28T10:30:00Z"
}
```

## Core Endpoints

### Health & Status

#### Health Check

```http
GET /health
```

Returns the overall health status of the API Gateway service.

**Response:**

```json
{
  "service": "api-gateway",
  "status": "healthy",
  "version": "3.0.0",
  "timestamp": "2025-07-28T10:30:00Z",
  "dependencies": {
    "mcp_server": "connected",
    "database": "connected"
  }
}
```

#### Service Status

```http
GET /status
```

Returns detailed service information including active connections and metrics.

## Project Management API (v2)

### Projects ✅ FULLY TESTED - ALL OPERATIONS WORKING

#### Create Project ✅ VERIFIED

```http
POST /v2/projects
```

Creates a new research project.

**Test Status**: ✅ PASSED - Full functionality verified  
**Database Integration**: ✅ Confirmed data persistence  
**MCP Communication**: ✅ Proper routing through Database Agent

**Request Body:**

```json
{
  "name": "My Research Project",
  "description": "A comprehensive study on...",
  "metadata": {
    "domain": "computer_science",
    "priority": "high"
  }
}
```

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My Research Project",
  "description": "A comprehensive study on...",
  "status": "active",
  "created_at": "2025-07-28T10:30:00Z",
  "updated_at": "2025-07-28T10:30:00Z",
  "topics_count": 0,
  "plans_count": 0,
  "tasks_count": 0,
  "total_cost": 0.0,
  "completion_rate": 0.0,
  "metadata": {
    "domain": "computer_science",
    "priority": "high"
  }
}
```

#### List Projects ✅ VERIFIED

```http
GET /v2/projects?status=active&limit=10
```

**Test Status**: ✅ PASSED - High performance via native database client  
**Performance**: ✅ Fast response times confirmed

**Query Parameters:**

- `status` (optional): Filter by project status (`active`, `archived`)
- `limit` (optional): Maximum number of results to return

**Response:**

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "My Research Project",
    "status": "active",
    "created_at": "2025-07-28T10:30:00Z",
    "topics_count": 3,
    "completion_rate": 45.2
  }
]
```

#### Get Project ✅ VERIFIED

```http
GET /v2/projects/{project_id}
```

**Test Status**: ✅ PASSED - Complete object retrieval confirmed  
**Data Integrity**: ✅ All fields returned correctly

Retrieves detailed information about a specific project.

#### Update Project ✅ VERIFIED

```http
PUT /v2/projects/{project_id}
```

**Test Status**: ✅ PASSED - Updates persist correctly to database  
**Major Bug Fixed**: ✅ Multiple data format support implemented

**Request Body:**

```json
{
  "name": "Updated Project Name",
  "description": "Updated description",
  "status": "active",
  "metadata": { ... }
}
```

All fields are optional. Only provided fields will be updated.

#### Delete Project

```http
DELETE /v2/projects/{project_id}
```

Permanently deletes a project and all associated data (topics, plans, tasks).

**Response:**

```json
{
  "success": true,
  "message": "Project deleted successfully",
  "timestamp": "2025-07-28T10:30:00Z"
}
```

### Project Statistics & Hierarchy

#### Get Project Statistics

```http
GET /v2/projects/{project_id}/stats
```

Returns statistical information about the project.

**Response:**

```json
{
  "topics_count": 5,
  "plans_count": 12,
  "tasks_count": 45,
  "total_cost": 1250.00,
  "completion_rate": 67.3
}
```

#### Get Project Hierarchy

```http
GET /v2/projects/{project_id}/hierarchy
```

Returns the complete hierarchical structure of the project.

**Response:**

```json
{
  "project": { ... },
  "topics": [
    {
      "id": "topic-1",
      "project_id": "project-id",
      "name": "Literature Review",
      "description": "Comprehensive literature review on...",
      "status": "active",
      "created_at": "2025-07-28T10:30:00Z",
      "plans_count": 2,
      "tasks_count": 8,
      "completion_rate": 75.0
    }
  ],
  "plans": [
    {
      "id": "plan-1",
      "topic_id": "topic-1",
      "name": "Systematic Review Plan",
      "plan_type": "comprehensive",
      "status": "active",
      "tasks_count": 4,
      "progress": 50.0
    }
  ],
  "tasks": [
    {
      "id": "task-1",
      "plan_id": "plan-1",
      "name": "Database Search",
      "task_type": "research",
      "status": "completed",
      "progress": 100.0
    }
  ]
}
```

### Research Topics ✅ FULLY TESTED - ALL OPERATIONS WORKING

Research topics organize specific areas of investigation within a project.

#### Create Research Topic ✅ VERIFIED

```http
POST /v2/projects/{project_id}/topics
```

**Test Status**: ✅ PASSED - Full functionality verified  
**Database Integration**: ✅ Confirmed storage in `research_topics` table  
**Hierarchy Validation**: ✅ Proper project-topic relationships established

**Request Body:**

```json
{
  "name": "Literature Review",
  "description": "Comprehensive literature review on machine learning",
  "metadata": {
    "priority": "high",
    "category": "research"
  }
}
```

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Literature Review",
  "description": "Comprehensive literature review on machine learning",
  "status": "active",
  "created_at": "2025-07-30T10:30:00Z",
  "updated_at": "2025-07-30T10:30:00Z",
  "plans_count": 0,
  "tasks_count": 0,
  "total_cost": 0.0,
  "completion_rate": 0.0,
  "metadata": {
    "priority": "high",
    "category": "research"
  }
}
```

#### List Research Topics ✅ VERIFIED

```http
GET /v2/projects/{project_id}/topics?status=active
```

**Test Status**: ✅ PASSED - Filtered retrieval working correctly  
**Performance**: ✅ Fast response via native database client

**Query Parameters:**

- `status` (optional): Filter by topic status (`active`, `archived`)

**Response:**

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Literature Review",
    "description": "Comprehensive literature review on machine learning",
    "status": "active",
    "created_at": "2025-07-30T10:30:00Z",
    "updated_at": "2025-07-30T10:30:00Z",
    "plans_count": 0,
    "tasks_count": 0,
    "total_cost": 0.0,
    "completion_rate": 0.0,
    "metadata": {}
  }
]
```

#### Get Research Topic

```http
GET /v2/topics/{topic_id}
```

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Literature Review",
  "description": "Comprehensive literature review on machine learning",
  "status": "active",
  "created_at": "2025-07-30T10:30:00Z",
  "updated_at": "2025-07-30T10:30:00Z",
  "plans_count": 0,
  "tasks_count": 0,
  "total_cost": 0.0,
  "completion_rate": 0.0,
  "metadata": {}
}
```

#### Get Research Topic within Project

```http
GET /v2/projects/{project_id}/topics/{topic_id}
```

**Response:** Same as above, but with additional validation that the topic belongs to the specified project.

#### Update Research Topic

```http
PUT /v2/topics/{topic_id}
```

**Request Body:**

```json
{
  "name": "Updated Literature Review",
  "description": "Updated comprehensive literature review",
  "metadata": {
    "priority": "medium"
  }
}
```

All fields are optional. Only provided fields will be updated.

**Response:** Updated topic object (same structure as create response).

#### Update Research Topic within Project

```http
PUT /v2/projects/{project_id}/topics/{topic_id}
```

**Request Body:** Same as above.

**Response:** Updated topic object with additional validation that the topic belongs to the specified project.

#### Delete Research Topic

```http
DELETE /v2/topics/{topic_id}
```

Permanently deletes a research topic and all associated data (plans, tasks).

**Response:**

```json
{
  "success": true,
  "message": "Research topic deleted successfully",
  "data": null,
  "timestamp": "2025-07-30T10:30:00Z"
}
```

#### Delete Research Topic within Project

```http
DELETE /v2/projects/{project_id}/topics/{topic_id}
```

Permanently deletes a research topic with additional validation that the topic belongs to the specified project.

**Response:** Same as above.

### Research Plans ⚠️ CORE FUNCTIONALITY WORKING - Some Individual Endpoints Have Issues

Research plans define structured approaches to investigate topics.

**Status**: ✅ Core operations (CREATE, LIST) working correctly  
**Issues**: ❌ Individual resource endpoints (GET /v2/plans/{id}, PUT, DELETE) have API Gateway routing problems  
**Major Fixes Applied**:

- ✅ Fixed capability mismatch between API Gateway and Database Agent
- ✅ Fixed database schema alignment (topic_id vs project_id)
- ✅ Verified MCP server communication and database persistence

#### Create Research Plan ✅ VERIFIED

```http
POST /v2/topics/{topic_id}/plans
```

**Test Status**: ✅ PASSED - Major bugs resolved, full functionality confirmed  
**Critical Fixes**: ✅ Database Agent capability registration and schema alignment  
**Database Integration**: ✅ Confirmed storage in `research_plans` table with correct relationships

#### List Research Plans ✅ VERIFIED

```http
GET /v2/topics/{topic_id}/plans
```

**Test Status**: ✅ PASSED - Fast retrieval via native database client  
**Metadata Parsing**: ✅ JSON metadata correctly parsed and returned

#### Individual Plan Operations ❌ KNOWN ISSUES

- `GET /v2/plans/{plan_id}` - Returns "Not Found" despite data existing
- `PUT /v2/plans/{plan_id}` - Routing issues prevent access
- `DELETE /v2/plans/{plan_id}` - Same routing pattern problem

### Tasks ⚠️ CORE FUNCTIONALITY WORKING - Update/Delete Issues

Individual work units within research plans.

**Status**: ✅ Core operations (CREATE, LIST, GET individual) working correctly  
**Issues**: ❌ UPDATE and DELETE operations don't persist changes despite success responses  
**Major Fixes Applied**:

- ✅ Fixed Database Agent to use correct `plan_id` and `research_tasks` table
- ✅ Fixed native database client table mismatch
- ✅ Verified task validation and metadata handling

#### Create Task ✅ VERIFIED

```http
POST /v2/plans/{plan_id}/tasks
```

**Test Status**: ✅ PASSED - Database schema issues resolved  
**Validation Working**: ✅ task_type field properly validated  
**Database Integration**: ✅ Confirmed storage in `research_tasks` table

#### List Tasks ✅ VERIFIED

```http
GET /v2/plans/{plan_id}/tasks
```

**Test Status**: ✅ PASSED - Native database client fixed to use correct table  
**Performance**: ✅ Fast retrieval with proper metadata parsing

#### Get Individual Task ✅ VERIFIED

```http
GET /v2/tasks/{task_id}
```

**Test Status**: ✅ PASSED - Complete task object retrieval confirmed

#### Update/Delete Tasks ❌ PERSISTENCE ISSUES

- `PUT /v2/tasks/{task_id}` - Returns success but changes not persisted
- `DELETE /v2/tasks/{task_id}` - Returns success but deletion not persisted

## Cost Estimation API ✅ FULLY FUNCTIONAL

The Cost Estimation API provides sophisticated cost analysis for research operations, including AI token usage, traditional research costs, and optimization recommendations.

### Planning Cost Estimation ✅ VERIFIED

#### Estimate Research Planning Costs

```http
POST /research/plan/estimate-costs
```

Estimates costs for research planning operations with detailed breakdown.

**Request Body:**

```json
{
  "query": "Research question or topic",
  "context": {
    "scope": "low|medium|high",
    "duration_days": 14,
    "agents": ["research_manager", "literature_agent"],
    "parallel_execution": true,
    "budget_limit": 50.0
  }
}
```

**Response:**

```json
{
  "status": "completed",
  "cost_estimate": {
    "estimated_cost": 12.75,
    "tokens_estimated": 35000,
    "complexity": "MEDIUM",
    "breakdown": {
      "ai_operations": {
        "estimated_tokens": 35000,
        "input_tokens": 24500,
        "output_tokens": 10500,
        "total_ai_cost": 2.75,
        "complexity_level": "MEDIUM",
        "provider": "openai",
        "model": "gpt-4o-mini"
      },
      "traditional_costs": {
        "database_access": 3.0,
        "analysis_software": 2.0,
        "expert_consultation": 5.0
      },
      "summary": {
        "ai_cost": 2.75,
        "traditional_cost": 10.0,
        "total": 12.75,
        "currency": "USD",
        "cost_per_day": 0.91
      }
    },
    "optimization_suggestions": [
      "Consider single-agent approach for 60% cost reduction",
      "Break down into smaller tasks to reduce complexity"
    ]
  },
  "timestamp": "2025-07-31T10:30:00Z"
}
```

### Cost Tracking ✅ VERIFIED

#### Start Cost Tracking

```http
POST /research/cost/start-tracking
```

Initiates cost tracking for a research session or task.

**Request Body:**

```json
{
  "task_id": "task_123",
  "session_id": "session_456",
  "project_id": "proj_789"
}
```

**Response:**

```json
{
  "status": "tracking_started",
  "task_id": "task_123",
  "session_id": "session_456",
  "start_time": "2025-07-31T10:30:00Z"
}
```

#### Record Usage

```http
POST /research/cost/record-usage
```

Records actual token usage and costs for operations.

**Request Body:**

```json
{
  "task_id": "task_123",
  "provider": "openai",
  "model": "gpt-4o-mini",
  "input_tokens": 1500,
  "output_tokens": 500,
  "agent_type": "research_manager"
}
```

**Response:**

```json
{
  "status": "usage_recorded",
  "cost_calculated": 0.45,
  "total_session_cost": 2.75,
  "tokens_used": 2000,
  "timestamp": "2025-07-31T10:30:00Z"
}
```

#### Get Cost Summary

```http
GET /research/cost/summary/{session_id}
```

Retrieves detailed cost summary for a research session.

**Response:**

```json
{
  "session_id": "session_456",
  "total_cost": 15.25,
  "total_tokens": 42000,
  "active_tasks": 3,
  "currency": "USD",
  "start_time": "2025-07-31T10:00:00Z",
  "duration_minutes": 125.5,
  "usage_breakdown": [
    {
      "task_id": "task_123",
      "cost": 5.25,
      "tokens": 15000,
      "duration": 45.2,
      "providers": {
        "openai": {"tokens": 15000, "cost": 5.25}
      },
      "agents": {
        "research_manager": {"tokens": 15000, "cost": 5.25}
      }
    }
  ],
  "cost_thresholds": {
    "session_warning": 1.0,
    "session_limit": 5.0,
    "daily_limit": 50.0,
    "status": "within_limits"
  },
  "optimization_recommendations": [
    "Consider using single-agent mode for simpler tasks",
    "Enable caching to reduce redundant API calls"
  ]
}
```

### Currency Conversion ✅ VERIFIED

#### Get Exchange Rates

```http
GET /research/cost/exchange-rates
```

Returns current exchange rates for cost calculations.

**Response:**

```json
{
  "base_currency": "USD",
  "rates": {
    "AUD": 1.55,
    "EUR": 0.92,
    "GBP": 0.79
  },
  "last_updated": "2025-07-31T10:00:00Z"
}
```

### Cost Optimization ✅ VERIFIED

#### Get Optimization Recommendations

```http
POST /research/cost/optimize
```

Analyzes current usage patterns and provides cost optimization suggestions.

**Request Body:**

```json
{
  "current_costs": {
    "daily_usage": 25.50,
    "session_costs": [5.25, 8.75, 11.50],
    "complexity_distribution": {
      "low": 0.3,
      "medium": 0.5,
      "high": 0.2
    }
  }
}
```

**Response:**

```json
{
  "optimization_analysis": {
    "potential_savings": 15.75,
    "savings_percentage": 38.2,
    "recommendations": [
      {
        "strategy": "single_agent_mode",
        "potential_saving": 9.50,
        "impact": "60% cost reduction for focused tasks"
      },
      {
        "strategy": "complexity_reduction",
        "potential_saving": 4.25,
        "impact": "Optimize query structure to reduce complexity scoring"
      },
      {
        "strategy": "batch_processing",
        "potential_saving": 2.00,
        "impact": "Group similar operations to reduce API calls"
      }
    ]
  },
  "cost_breakdown_analysis": {
    "highest_cost_operations": [
      "comprehensive_research_planning",
      "multi_agent_parallel_execution"
    ],
    "optimization_opportunities": [
      "Enable caching for repeated queries",
      "Use sequential execution for non-time-critical tasks"
    ]
  }
}
```

## Data Models

### Project

```json
{
  "id": "string (UUID)",
  "name": "string (required, max 255 chars)",
  "description": "string (optional)",
  "status": "enum: active, archived",
  "created_at": "string (ISO 8601)",
  "updated_at": "string (ISO 8601)",
  "topics_count": "integer",
  "plans_count": "integer", 
  "tasks_count": "integer",
  "total_cost": "number",
  "completion_rate": "number (0-100)",
  "metadata": "object (optional)"
}
```

### Research Topic

```json
{
  "id": "string (UUID)",
  "project_id": "string (UUID, required)",
  "name": "string (required, max 255 chars)",
  "description": "string (optional)",
  "status": "enum: active, paused, completed, archived",
  "created_at": "string (ISO 8601)",
  "updated_at": "string (ISO 8601)",
  "plans_count": "integer",
  "tasks_count": "integer",
  "total_cost": "number",
  "completion_rate": "number (0-100)",
  "metadata": "object (optional)"
}
```

### Research Plan

```json
{
  "id": "string (UUID)",
  "topic_id": "string (UUID, required)",
  "name": "string (required, max 255 chars)",
  "description": "string (optional)",
  "plan_type": "enum: comprehensive, quick, deep, custom",
  "status": "enum: draft, active, completed, cancelled",
  "plan_approved": "boolean",
  "created_at": "string (ISO 8601)",
  "updated_at": "string (ISO 8601)",
  "estimated_cost": "number",
  "actual_cost": "number",
  "tasks_count": "integer",
  "completed_tasks": "integer",
  "progress": "number (0-100)",
  "plan_structure": "object",
  "metadata": "object (optional)"
}
```

### Task

```json
{
  "id": "string (UUID)",
  "plan_id": "string (UUID, required)",
  "name": "string (required, max 255 chars)",
  "description": "string (optional)",
  "task_type": "enum: research, analysis, synthesis, validation",
  "task_order": "integer",
  "status": "enum: pending, running, completed, failed, cancelled",
  "stage": "enum: planning, literature_review, reasoning, execution, synthesis, complete, failed",
  "created_at": "string (ISO 8601)",
  "updated_at": "string (ISO 8601)",
  "estimated_cost": "number",
  "actual_cost": "number",
  "cost_approved": "boolean",
  "single_agent_mode": "boolean", 
  "max_results": "integer",
  "progress": "number (0-100)",
  "query": "string (optional)",
  "search_results": "array",
  "reasoning_output": "string (optional)",
  "execution_results": "array",
  "synthesis": "string (optional)",
  "metadata": "object (optional)"
}
```

## HTTP Status Codes

- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request data
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error
- `503 Service Unavailable` - Dependent service unavailable

## Rate Limiting

Currently not implemented. Will be added in Version 0.3.2.

## Error Handling

### Validation Errors (422)

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "name"],
      "msg": "Field required",
      "input": { ... }
    }
  ]
}
```

### Not Found Errors (404)

```json
{
  "detail": "Project not found"
}
```

### Server Errors (500)

```json
{
  "detail": "Internal server error occurred"
}
```

## MCP Integration

The API Gateway integrates with the MCP (Message Control Protocol) server for:

- Project creation and management
- Task routing to appropriate agents
- Real-time updates and notifications
- Agent coordination and load balancing

### MCP Message Flow

```
REST Request → API Gateway → MCP Research Action → MCP Server → Database Agent
REST Response ← API Gateway ← MCP Response ← MCP Server ← Database Agent
```

## Development & Testing

### Interactive Documentation

- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`

### Testing Endpoints

```bash
# Health check
curl http://localhost:8001/health

# Create project
curl -X POST http://localhost:8001/v2/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Project", "description": "Testing the API"}'

# List projects
curl http://localhost:8001/v2/projects

# Get project statistics
curl http://localhost:8001/v2/projects/{project_id}/stats

# Get project hierarchy
curl http://localhost:8001/v2/projects/{project_id}/hierarchy
```

## Changelog

### Version 3.0.0 (July 2025)

- ✅ Complete project management API
- ✅ Project statistics and hierarchy endpoints
- ✅ Enhanced error handling and validation
- ✅ MCP integration for real-time operations
- ✅ Native PostgreSQL database integration

### Version 3.1.0 (July 2025 - ✅ Completed)

- ✅ Research topic management endpoints (full CRUD operations)
- ✅ Enhanced project metadata handling
- ✅ Hierarchical topic validation and access control
- ✅ Topic deletion with cascade operations

### Version 3.2.0 (In Development - August 2025)

- 🔄 Research plan management endpoints
- 🔄 JWT authentication system
- 🔄 Rate limiting implementation
- 🔄 Bulk operations support

### Version 3.3.0 (Planned - September 2025)

- ❌ Advanced query capabilities
- ❌ Task management endpoints
- ❌ Real-time collaboration features
- ❌ Advanced analytics and reporting

## Support

For API support and questions:

- GitHub Issues: [Eunice Repository](https://github.com/pzanna/Eunice/issues)
- Documentation: [Project Wiki](docs/)
- Architecture: [Service Architecture](docs/VERSION03_SERVICE_ARCHITECTURE.md)
