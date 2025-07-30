# Creating a Research Plan

This document outlines the process for creating a research plan within the Eunice platform's current microservices architecture, detailing the steps from user initiation to database storage.

## 1. User Initiates Research Plan Creation

**Entry Points:**

- User creates a **Project** via web interface or API
- User creates a **Research Topic** within the project
- User navigates to Project Details page and clicks "Start Research"

**Frontend Components:**

- `ProjectDetails.tsx` - Lists topics with "Start Research" button
- `ResearchPlanDetails.tsx` - Shows research plan details, allows editing and approval

## 2. Frontend API Call

**Frontend File:** `frontend/src/components/ProjectDetails.tsx`
**Method:** `handleCreateResearchPlan()`

**Process:**

1. **Form Validation**: Validates required fields (topic name is used for Plan name)
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

## 7. Current vs Target Architecture Comparison

### Current Manual System (As Implemented)

1. **Manual Plan Creation**: Users manually create research plans via web interface
2. **Basic Structure**: Plans start with simple name/description fields stored in `plan_structure: {}`
3. **Microservices Communication**: Frontend → API Gateway → MCP Server → Database Service
4. **PostgreSQL Storage**: Direct database operations with connection pooling
5. **No AI Integration**: Currently no automatic plan generation
6. **No Approval Process**: Plans created directly without approval workflow
7. **No Cost Estimation**: Cost tracking not currently implemented

### Target AI-Driven System (To Be Implemented)

1. **AI-Generated Plans**: Planning Agent auto-generates comprehensive research plans
2. **Rich Structure**: Plans include objectives, key areas, questions, sources, and expected outcomes
3. **Planning Agent Integration**: Containerized planning agent via MCP protocol
4. **Cost Estimation System**: Sophisticated cost tracking with CostEstimator class
5. **Approval Workflow**: Plans require explicit approval before execution
6. **Multi-Provider Support**: OpenAI and XAI integration for plan generation

## 8. Implementation Requirements for AI-Driven Planning

Based on the current Planning Agent capabilities, here are the specific enhancements needed:

### 1. Planning Agent Integration

**Current State**: Planning Agent exists as containerized service with these capabilities:

- `plan_research` - Generate comprehensive research plans
- `analyze_information` - Analyze collected information  
- `cost_estimation` - Provide cost estimates with CostEstimator class
- `chain_of_thought` - Perform logical reasoning
- `summarize_content` - Create content summaries
- `extract_insights` - Extract key insights
- `compare_sources` - Compare information sources
- `evaluate_credibility` - Assess source credibility

**Legacy Implementation Reference**: The `agents/planning/src/planning_service_old.py` contains the complete AI prompts and expected outcomes for all capabilities. Key implementation details:

**AI Prompt Templates**:

```python
# Research Plan Generation Prompt (from planning_service_old.py)
prompt = f"""
Please create a comprehensive research plan for the following query:

Query: {query}
Scope: {scope}
Context: {json.dumps(context, indent=2)}

Please provide a detailed research plan with:
1. Clear research objectives (3-5 specific goals)
2. Key areas to investigate (4-6 major research domains)
3. Specific questions to answer (5-8 focused research questions)
4. Information sources to consult (academic databases, repositories, etc.)
5. Expected outcomes and deliverables
6. Realistic timeline with phases

Format your response as a JSON object with this exact structure:
{{
    "objectives": ["Objective 1", "Objective 2", "Objective 3"],
    "key_areas": ["Area 1", "Area 2", "Area 3", "Area 4"],
    "questions": ["Question 1", "Question 2", "Question 3", "Question 4", "Question 5"],
    "sources": ["PubMed", "ArXiv", "Semantic Scholar", "Google Scholar", "IEEE Xplore"],
    "timeline": {{
        "total_days": 14,
        "phases": {{
            "literature_search": 3,
            "data_collection": 5,
            "analysis": 4,
            "synthesis": 2
        }}
    }},
    "outcomes": ["Literature review", "Data analysis", "Research synthesis", "Final report"]
}}
"""
```

**Expected Response Structure**:

```json
{
  "status": "completed",
  "result": {
    "query": "User research question",
    "scope": "comprehensive|medium|focused",
    "plan": {
      "objectives": ["Specific goal 1", "Specific goal 2", "Specific goal 3"],
      "key_areas": ["Research domain 1", "Research domain 2", "Research domain 3"],
      "questions": ["Focused question 1", "Focused question 2", "Focused question 3"],
      "sources": ["Academic database 1", "Repository 2", "Database 3"],
      "timeline": {
        "total_days": 14,
        "phases": {
          "literature_search": 3,
          "data_collection": 5,
          "analysis": 4,
          "synthesis": 2
        }
      },
      "outcomes": ["Deliverable 1", "Deliverable 2", "Deliverable 3"]
    },
    "agent_id": "planning-12345",
    "processing_time": 2.1,
    "ai_generated": true
  }
}
```

**Cost Estimation Capabilities** (from CostEstimator and planning_service_old.py):

- **Sophisticated Cost Analysis**: Real complexity assessment using keyword analysis
- **Multi-provider Pricing**: OpenAI (`gpt-4o-mini`) and XAI (`grok-beta`) support
- **Token Estimation**: Accurate input/output token calculations
- **Complexity Scoring**: LOW/MEDIUM/HIGH based on query analysis and agent count
- **Optimization Suggestions**: Context-aware recommendations for cost reduction

**Required Integration**:

- Connect API Gateway to Planning Agent via MCP protocol
- Add "Generate Plan" button to research plan creation form
- Implement AI-generated plan parsing and storage
- Use exact prompt templates from `planning_service_old.py`
- Parse JSON responses using the established structure

### 2. Enhanced Plan Structure Schema

**Current Schema**:

```json
{
  "plan_structure": {},
  "metadata": {}
}
```

**Required Enhanced Schema**:

```json
{
  "plan_structure": {
    "objectives": ["Research objective 1", "Research objective 2"],
    "key_areas": ["Area to investigate 1", "Area to investigate 2"], 
    "questions": ["Specific question 1", "Specific question 2"],
    "sources": ["Information source 1", "Information source 2"],
    "outcomes": ["Expected outcome 1", "Expected outcome 2"],
    "generated_by": "ai|manual",
    "complexity_level": "LOW|MEDIUM|HIGH",
    "estimated_duration": "timeline_estimate"
  },
  "metadata": {
    "ai_model_used": "gpt-4o-mini",
    "generation_cost": 5.25,
    "generation_timestamp": "2025-07-30T12:00:00Z",
    "confidence_score": 0.85
  }
}
```

### 3. Cost Estimation Integration

**Current Capability**: Planning Agent has sophisticated CostEstimator class with:

- Real-time cost tracking
- Provider-specific pricing (OpenAI, XAI)
- Complexity assessment (LOW/MEDIUM/HIGH)
- Token estimation and breakdown
- Optimization recommendations
- Threshold monitoring

**Required Implementation**:

- Add cost estimation before plan generation
- Display cost estimates to users before approval
- Integrate cost tracking with plan creation workflow
- Add budget limits and cost approval thresholds

### 4. Approval Workflow

**Required Components**:

- Plan approval status field: `plan_approved: boolean`
- Approval actions: "Approve Plan", "Request Changes", "Reject Plan"
- Approval history tracking in metadata
- Role-based approval permissions
- Cost-based approval thresholds (auto-approve under $5, require approval over $10)

### 5. Frontend Enhancements

**Required UI Components**:

- "Generate AI Plan" button in plan creation dialog
- Plan structure display with collapsible sections (objectives, questions, etc.)
- Cost estimation display before generation
- Approval workflow interface (approve/reject buttons)
- Plan comparison view (manual vs AI-generated)
- Cost breakdown and optimization suggestions display

## Implementation Roadmap

Based on the existing Planning Agent infrastructure, here's the specific implementation plan:

### Phase 1 - API Gateway Integration (Week 1-2)

**Backend Changes:**

- **API Gateway** (`services/api-gateway/v2_hierarchical_api.py`):
  - Add new endpoint: `POST /v2/topics/{topic_id}/plans/generate`
  - Implement `generate_ai_research_plan()` method
  - Add MCP communication to Planning Agent
  - Integrate cost estimation before plan generation

- **Database Schema** (`services/database/`):
  - Update `research_plans` table to support enhanced `plan_structure` JSON
  - Add cost tracking fields: `generation_cost`, `estimated_cost`
  - Add approval workflow fields: `approval_status`, `approved_by`, `approved_at`

**Sample API Integration:**

```python
async def generate_ai_research_plan(topic_id: str, plan_request: dict):
    # 1. Get cost estimate from Planning Agent
    cost_estimate = await mcp_client.send_request({
        "method": "research_action",
        "params": {
            "agent_type": "planning",
            "action": "cost_estimation",
            "payload": {
                "query": plan_request["description"],
                "context": {"complexity": "medium"}
            }
        }
    })
    
    # 2. Check cost approval thresholds
    if cost_estimate["estimated_cost"] > 10.0:
        return {"status": "requires_approval", "cost_estimate": cost_estimate}
    
    # 3. Generate plan via Planning Agent
    plan_result = await mcp_client.send_request({
        "method": "research_action", 
        "params": {
            "agent_type": "planning",
            "action": "plan_research",
            "payload": {
                "query": plan_request["description"],
                "context": plan_request.get("context", {})
            }
        }
    })
    
    return {"status": "generated", "plan": plan_result, "cost": cost_estimate}
```

### Phase 2 - Frontend Enhancement (Week 3-4)

**Frontend Changes:**

- **Plan Creation Dialog** (`frontend/src/components/`):
  - Add "Generate AI Plan" button alongside manual creation
  - Implement cost estimation display
  - Add plan preview with structured sections (objectives, questions, etc.)
  - Create approval workflow interface

**New Components to Create:**

```typescript
// PlanGenerationDialog.tsx
interface PlanGenerationProps {
  topicId: string;
  onPlanGenerated: (plan: AIGeneratedPlan) => void;
}

// CostEstimationDisplay.tsx
interface CostDisplayProps {
  estimate: CostEstimate;
  onApprove: () => void;
  onReject: () => void;
}

// PlanStructureView.tsx  
interface PlanViewProps {
  planStructure: {
    objectives: string[];
    key_areas: string[];
    questions: string[];
    sources: string[];
    outcomes: string[];
  };
  isEditable: boolean;
}
```

### Phase 3 - Approval Workflow (Week 5-6)

**Implementation Details:**

- **Backend**: Add approval state management
- **Frontend**: Implement approval UI with cost-based thresholds
- **Integration**: Connect Planning Agent cost estimation with approval logic

**Approval Logic:**

```python
def determine_approval_requirement(cost_estimate: float, user_role: str) -> str:
    if cost_estimate < 5.0:
        return "auto_approved"
    elif cost_estimate < 25.0 and user_role in ["admin", "researcher"]:
        return "user_approved" 
    else:
        return "manager_approval_required"
```

### Technical Integration Points

**1. MCP Protocol Messages:**

```json
{
  "method": "research_action",
  "params": {
    "agent_type": "planning",
    "action": "plan_research",
    "task_id": "plan_gen_001",
    "payload": {
      "query": "Research question here",
      "context": {
        "scope": "medium",
        "budget_limit": 25.0,
        "single_agent_mode": false
      }
    }
  }
}
```

**2. Planning Agent Response Format:**

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
      "estimated_cost": 12.75,
      "complexity": "MEDIUM",
      "optimization_suggestions": ["suggestion 1"]
    }
  }
}
```

**3. Database Storage Integration:**

```sql
UPDATE research_plans SET 
  plan_structure = $1::jsonb,
  metadata = $2::jsonb,
  generation_cost = $3,
  plan_approved = $4
WHERE id = $5;
```

## 9. AI Prompt Templates and Expected Outcomes

The `agents/planning/src/planning_service_old.py` contains the complete implementation with proven AI prompts and response structures that should be preserved in the new integration.

### Core AI Prompt Templates

#### 1. Research Planning Prompt

```python
prompt = f"""
Please create a comprehensive research plan for the following query:

Query: {query}
Scope: {scope}
Context: {json.dumps(context, indent=2)}

Please provide a detailed research plan with:
1. Clear research objectives (3-5 specific goals)
2. Key areas to investigate (4-6 major research domains)
3. Specific questions to answer (5-8 focused research questions)
4. Information sources to consult (academic databases, repositories, etc.)
5. Expected outcomes and deliverables
6. Realistic timeline with phases

Format your response as a JSON object with this exact structure:
{{
    "objectives": ["Objective 1", "Objective 2", "Objective 3"],
    "key_areas": ["Area 1", "Area 2", "Area 3", "Area 4"],
    "questions": ["Question 1", "Question 2", "Question 3", "Question 4", "Question 5"],
    "sources": ["PubMed", "ArXiv", "Semantic Scholar", "Google Scholar", "IEEE Xplore"],
    "timeline": {{
        "total_days": 14,
        "phases": {{
            "literature_search": 3,
            "data_collection": 5,
            "analysis": 4,
            "synthesis": 2
        }}
    }},
    "outcomes": ["Literature review", "Data analysis", "Research synthesis", "Final report"]
}}

Please be thorough and consider all relevant aspects of the research topic.
Ensure the plan is realistic and executable within the given timeframe.
"""
```

#### 2. Information Analysis Prompt

```python
prompt = f"""
Please analyze the following content with a focus on {analysis_type} analysis:

Content: {content}

Provide a comprehensive analysis including:
1. Executive summary of the content
2. Key points and findings (3-5 main points)
3. Deep insights and implications
4. Actionable recommendations
5. Confidence assessment of the analysis

Format your response as a JSON object with this exact structure:
{{
    "summary": "Executive summary of the content analysis",
    "key_points": ["Point 1", "Point 2", "Point 3", "Point 4"],
    "insights": ["Insight 1", "Insight 2", "Insight 3"],
    "recommendations": ["Recommendation 1", "Recommendation 2", "Recommendation 3"],
    "confidence_score": 0.85,
    "analysis_type": "{analysis_type}"
}}
"""
```

#### 3. Cost Estimation Prompt

```python
prompt = f"""
Please estimate traditional research costs for a project with the following parameters:

Duration: {duration_days} days
Resources needed: {resources_needed}
Project context: {project_context}

Provide detailed cost estimates for each resource category based on current market rates:
1. Database access subscriptions
2. Survey and data collection tools
3. Analysis software licenses
4. Expert consultation fees
5. Cloud computing resources
6. Additional operational costs

Consider regional variations and current market pricing. Format your response as a JSON object:
{{
    "resources": {{
        "items": {resources_needed},
        "costs": {{
            "database_access": 200,
            "survey_tools": 150,
            "analysis_software": 300,
            "expert_consultation": 500,
            "data_collection": 400,
            "cloud_compute": 100
        }},
        "total": 1650
    }},
    "duration_days": {duration_days},
    "cost_breakdown_reasoning": "Explanation of how costs were estimated",
    "market_factors": ["Factor 1", "Factor 2"],
    "cost_confidence": 0.8
}}
"""
```

### Expected Response Structures

#### 1. Research Plan Response

```json
{
  "status": "completed",
  "result": {
    "query": "User research question",
    "scope": "comprehensive",
    "plan": {
      "objectives": [
        "Identify current trends in the research area",
        "Analyze effectiveness of existing solutions",
        "Determine gaps in current knowledge"
      ],
      "key_areas": [
        "Literature review and analysis",
        "Current market solutions",
        "Technical implementation challenges",
        "Future research directions"
      ],
      "questions": [
        "What are the most recent developments in this field?",
        "Which approaches show the highest success rates?",
        "What are the main limitations of current solutions?",
        "Where are the most promising research opportunities?"
      ],
      "sources": [
        "PubMed",
        "IEEE Xplore",
        "ArXiv",
        "Google Scholar",
        "Semantic Scholar"
      ],
      "timeline": {
        "total_days": 14,
        "phases": {
          "literature_search": 3,
          "data_collection": 5,
          "analysis": 4,
          "synthesis": 2
        }
      },
      "outcomes": [
        "Comprehensive literature review",
        "Market analysis report",
        "Technical feasibility assessment",
        "Research recommendations"
      ]
    },
    "agent_id": "planning-12345",
    "processing_time": 2.1,
    "ai_generated": true
  }
}
```

#### 2. Cost Estimation Response (Enhanced)

```json
{
  "status": "completed",
  "result": {
    "project_scope": "medium",
    "cost_breakdown": {
      "ai_operations": {
        "estimated_tokens": 25000,
        "input_tokens": 18750,
        "output_tokens": 6250,
        "total_ai_cost": 6.75,
        "complexity_level": "MEDIUM",
        "complexity_multiplier": 2.5,
        "provider": "openai",
        "model": "gpt-4o-mini"
      },
      "traditional_costs": {
        "resources": {
          "costs": {
            "database_access": 200,
            "analysis_software": 300,
            "expert_consultation": 500
          },
          "total": 1000
        }
      },
      "summary": {
        "ai_cost": 6.75,
        "traditional_cost": 1000,
        "total": 1006.75,
        "currency": "USD",
        "cost_per_day": 67.12
      },
      "optimization_suggestions": [
        "Consider breaking down into smaller sub-tasks",
        "Use caching to avoid redundant analysis"
      ]
    },
    "agent_id": "planning-12345"
  }
}
```

### Implementation Requirements

1. **Preserve Exact Prompt Templates**: Use the proven prompts from `planning_service_old.py`
2. **Maintain Response Structure**: Keep the established JSON response formats
3. **AI Communication**: All AI requests must go through MCP protocol (no direct provider access)
4. **Error Handling**: Implement the same fallback mechanisms as in the legacy service
5. **Cost Integration**: Use the sophisticated CostEstimator class for real-time cost tracking
