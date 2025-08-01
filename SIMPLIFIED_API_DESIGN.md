# Simplified Literature Review API Design

## Current Problem

The API requires users to manually specify redundant information that already exists in the topic and plan hierarchy.

## Proposed Solution

### Single Endpoint for All Research Task Execution

```python
POST /v2/topics/{topic_id}/execute
{
  "task_type": "literature_review",  # literature_review | systematic_review | meta_analysis
  "depth": "phd"                     # undergraduate | masters | phd
}
```

### Data Resolution Flow

1. **topic_id** → Fetch topic (name, description)
2. **topic.plan** → Fetch approved research plan (research questions, scope)
3. **depth** → Apply depth configuration (max_results, sources, quality)
4. **Execute** → Send complete context to Research Manager

### Request Model

```python
class ExecuteResearchRequest(BaseModel):
    task_type: Literal["literature_review", "systematic_review", "meta_analysis"] = "literature_review"
    depth: Literal["undergraduate", "masters", "phd"] = "masters"
    
class LiteratureReviewDepthConfig:
    undergraduate: {
        max_results: 25,
        sources: ["semantic_scholar", "arxiv"],
        estimated_cost: 0.15,
        estimated_duration: "3-8 minutes"
    }
    masters: {
        max_results: 75,
        sources: ["semantic_scholar", "arxiv", "pubmed"], 
        estimated_cost: 0.35,
        estimated_duration: "8-15 minutes"
    }
    phd: {
        max_results: 200,
        sources: ["semantic_scholar", "arxiv", "pubmed", "crossref"],
        estimated_cost: 0.75,
        estimated_duration: "15-30 minutes"
    }
```

### Response Model

```python
class LiteratureReviewExecutionResponse(BaseModel):
    execution_id: str
    topic_name: str
    research_questions: List[str]
    depth: str
    estimated_cost: float
    estimated_duration: str
    status: "initiated"
    progress_url: str  # For real-time updates
```

## Benefits

### ✅ Eliminated Redundancy

- No need to re-enter topic name/description
- No need to specify research questions (from plan)
- No need to manually set max_results (from depth)

### ✅ Academic Workflow Alignment  

- Depth levels match academic rigor expectations
- Pre-configured source selections for each level
- Appropriate cost/time expectations

### ✅ Simplified User Experience

- One API call with minimal parameters
- Context automatically resolved from hierarchy
- Clear academic depth semantics

## Implementation

### API Gateway Enhancement

```python
@v2_router.post("/topics/{topic_id}/execute")
async def execute_research_task(
    request: ExecuteResearchRequest,
    topic_id: str = Path(...),
    db=Depends(get_database),
    mcp_client=Depends(get_mcp_client)
):
    # 1. Fetch topic details
    topic = await db.get_research_topic(topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")
    
    # 2. Get approved research plan
    plans = await db.get_research_plans_for_topic(topic_id)
    approved_plan = next((p for p in plans if p.plan_approved), None)
    if not approved_plan:
        raise HTTPException(400, "No approved research plan found")
    
    # 3. Apply depth configuration
    depth_config = RESEARCH_DEPTH_CONFIG[request.depth]
    
    # 4. Construct research context
    research_context = {
        "topic_name": topic.name,
        "topic_description": topic.description,
        "research_plan": approved_plan.plan_structure,
        "depth": request.depth,
        **depth_config
    }
    
    # 5. Execute via Research Manager
    execution_id = str(uuid4())
    mcp_payload = {
        "task_id": execution_id,
        "agent_type": "research_manager", 
        "action": "coordinate_research",
        "payload": {
            **research_context,
            "task_type": request.task_type  # Pass task_type to Research Manager
        }
    }
    
    await mcp_client.send_research_action(mcp_payload)
    
    return LiteratureReviewExecutionResponse(
        execution_id=execution_id,
        topic_name=topic.name,
        research_questions=approved_plan.plan_structure.get("questions", []),
        depth=request.depth,
        estimated_cost=depth_config["estimated_cost"],
        estimated_duration=depth_config["estimated_duration"],
        status="initiated",
        progress_url=f"/v2/executions/{execution_id}/progress"
    )
```

## Comparison

### Before (Complex)

```
User needs to provide:
- task_type, name, description, query, max_results, single_agent_mode, task_order, metadata

API calls required: 
- POST /plans/{id}/tasks
- POST /tasks/{id}/execute
```

### After (Simple)  

```text
User needs to provide:
- task_type, depth

API calls required:
- POST /topics/{id}/execute
```

## Result

This design perfectly aligns with your insight: **literature review execution only needs task_type (implicit), depth, and topic_id**. Everything else is derived automatically from the existing data hierarchy!
