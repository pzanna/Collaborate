# Eunice Research Platform API Documentation

## Overview

The Eunice Research Platform provides a comprehensive REST API for managing hierarchical research projects. The API follows RESTful principles and uses JSON for data exchange.

**Base URL**: `http://localhost:8001`  
**API Version**: v2 (Current)  
**Documentation**: Available at `/docs` (Swagger UI) and `/redoc` (ReDoc)

## Authentication

Currently, the API does not require authentication. This will be implemented in Version 0.3.2 with JWT tokens.

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

### Projects

#### Create Project

```http
POST /v2/projects
```

Creates a new research project.

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

#### List Projects

```http
GET /v2/projects?status=active&limit=10
```

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

#### Get Project

```http
GET /v2/projects/{project_id}
```

Retrieves detailed information about a specific project.

#### Update Project

```http
PUT /v2/projects/{project_id}
```

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

### Research Topics (In Development - v0.3.1)

Research topics organize specific areas of investigation within a project.

#### Create Research Topic

```http
POST /v2/projects/{project_id}/topics
```

*Status: Implementation pending*

#### List Research Topics

```http
GET /v2/projects/{project_id}/topics
```

*Status: Implementation pending*

#### Get Research Topic

```http
GET /v2/topics/{topic_id}
```

*Status: Implementation pending*

#### Update Research Topic

```http
PUT /v2/topics/{topic_id}
```

*Status: Implementation pending*

#### Delete Research Topic

```http
DELETE /v2/topics/{topic_id}
```

*Status: Implementation pending*

### Research Plans (Planned - v0.3.2)

Research plans define structured approaches to investigate topics.

*Status: Design phase*

### Tasks (Planned - v0.3.3)

Individual work units within research plans.

*Status: Design phase*

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

### Version 3.1.0 (Planned - August 2025)

- 🔄 Research topic management endpoints
- 🔄 Enhanced project metadata handling
- 🔄 Bulk operations support

### Version 3.2.0 (Planned - September 2025)

- ❌ Research plan management endpoints
- ❌ JWT authentication system
- ❌ Rate limiting implementation
- ❌ Advanced query capabilities

## Support

For API support and questions:

- GitHub Issues: [Eunice Repository](https://github.com/pzanna/Eunice/issues)
- Documentation: [Project Wiki](docs/)
- Architecture: [Service Architecture](docs/VERSION03_SERVICE_ARCHITECTURE.md)
