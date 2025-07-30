# Creating a Research Plan

This document outlines the process for creating a research plan within the Eunice platform's current microservices architecture, detailing the steps from user initiation to database storage.

## 1. User Initiates Research Plan Creation

**Entry Points:**

- User creates a **Project** via web interface or API
- User creates a **Research Topic** within the project  
- User navigates to Topic Details page and clicks "New Research Plan"
- User fills out the research plan creation form

**Frontend Components:**

- `ProjectDetails.tsx` - Lists topics with "Start Research" button
- `TopicDetails.tsx` - Shows topic details and research plan management
- Research plan creation dialog with form fields for name and description

## 2. Frontend API Call

**Frontend File:** `frontend/src/components/TopicDetails.tsx`
**Method:** `handleCreateResearchPlan()`

**Process:**

1. **Form Validation**: Validates required fields (plan name)
2. **API Request**: Calls `apiClient.createResearchPlan()` with:
   - Topic ID
   - Plan name
   - Plan description
   - Optional metadata and plan structure
3. **State Update**: Updates local state with new research plan

**API Client:** `frontend/src/utils/api.ts`

```typescript
async createResearchPlan(
  topicId: string, 
  plan: CreateResearchPlanRequest
): Promise<ResearchPlan>
```

## 3. API Gateway Processing

**Service:** API Gateway
**File:** `services/api-gateway/v2_hierarchical_api.py`
**Endpoint:** `POST /v2/topics/{topic_id}/plans`
**Method:** `create_research_plan()`

**Steps:**

1. **Topic Validation**: Verifies topic exists using database client
2. **Plan Data Creation**: Generates plan data structure with:
   - Unique plan ID (UUID)
   - Topic association
   - Initial status: "draft"
   - Timestamps
   - Cost tracking fields (initialized to 0.0)
3. **MCP Communication**: Sends research plan creation via MCP protocol

## 4. MCP Server Message Routing

**Service:** MCP Server
**File:** `services/mcp-server/mcp_server.py`
**Method:** `_handle_research_action()`

**Process:**

1. **Message Reception**: Receives research action from API Gateway
2. **Agent Routing**: Routes create_research_plan action to Database Agent
3. **Task Tracking**: Maintains task state for monitoring
4. **Response Handling**: Manages responses between services

## 5. Database Service Processing

**Service:** Database Service  
**File:** `services/database/database_service.py`
**Database Connection:** Direct PostgreSQL via asyncpg

**Tables Involved:**

- `projects` - Project information
- `research_topics` - Topic under project  
- `research_plans` - Research plan with structure and metadata
- `tasks` - Individual tasks within plans (for future use)

**Database Operations:**

1. **Plan Creation**: Inserts new research plan record
2. **Relationship Linking**: Associates plan with topic and project
3. **Status Tracking**: Sets initial status and approval state
4. **Cost Initialization**: Sets estimated and actual costs to 0.0

**Plan Structure Storage:**

```json
{
  "id": "generated-uuid",
  "topic_id": "topic-uuid", 
  "name": "User-provided plan name",
  "description": "User-provided description",
  "plan_type": "comprehensive",
  "status": "draft",
  "plan_approved": false,
  "created_at": "ISO timestamp",
  "updated_at": "ISO timestamp", 
  "estimated_cost": 0.0,
  "actual_cost": 0.0,
  "plan_structure": {},
  "metadata": {}
}
```

## 6. Response Flow

**Database → MCP Server → API Gateway → Frontend:**

1. **Database Response**: Returns created plan data with generated ID
2. **MCP Acknowledgment**: MCP server confirms successful creation
3. **API Response**: API Gateway sends plan data to frontend
4. **UI Update**: Frontend updates topic view with new research plan

## 7. Current vs Previous Design Differences

### Current Microservices Architecture

1. **Manual Plan Creation**: Users manually create research plans via web interface
2. **Simple Structure**: Plans start with basic name/description fields
3. **Microservices Communication**: API Gateway → MCP Server → Database Service
4. **PostgreSQL Storage**: Direct database operations with connection pooling
5. **Minimal AI Integration**: No automatic plan generation currently

### Previous Monolithic Design

1. **AI-Generated Plans**: Research Manager used AI agents to auto-generate detailed plans
2. **Rich Structure**: Plans included objectives, questions, sources, expected outcomes
3. **Agent Orchestration**: Planning Agent created comprehensive research workflows
4. **Approval Process**: Plans required explicit approval before execution
5. **Cost Estimation**: Built-in cost analysis before plan creation

## 8. Future Enhancement Opportunities

To reproduce the old system's AI-driven planning capabilities:

1. **Add AI Planning Service**: Create dedicated service for plan generation
2. **Enhance Plan Structure**: Expand plan_structure field to include:
   - Research objectives
   - Key areas to investigate
   - Specific questions to answer
   - Recommended information sources
   - Expected outcomes
3. **Implement Auto-Generation**: Add "Generate Plan" feature using AI
4. **Add Approval Workflow**: Implement plan approval before execution
5. **Cost Estimation Integration**: Add cost analysis before plan approval

## Implementation Roadmap

To achieve AI-generated research plans similar to the old system:

### Phase 1 - Enhanced Plan Structure

- Expand plan creation form with structured fields
- Update database schema for rich plan data
- Modify API to handle complex plan structures

### Phase 2 - AI Integration

- Create AI Planning Service (separate microservice)
- Integrate with OpenAI/XAI for plan generation
- Add automatic plan creation from research queries

### Phase 3 - Workflow Management

- Implement plan approval workflow
- Add cost estimation and approval gates
- Create plan execution coordination between services

This would bridge the gap between the current manual system and the previous AI-driven approach while maintaining the microservices architecture.
