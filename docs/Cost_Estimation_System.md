# Cost Estimation System Documentation

_Last Updated: July 21, 2025_

## Overview

The Cost Estimation System in Eunice provides comprehensive cost management for AI operations, including pre-task cost estimation, real-time usage tracking, and automatic cost controls. This system ensures predictable spending while maintaining optimal performance across multi-agent research workflows.

## Architecture

### Core Components

#### 1. CostEstimator Class

The central orchestrator located in `src/mcp/cost_estimator.py` that handles:

- **Pre-task Cost Estimation**: Predicts token usage and costs before execution
- **Real-time Usage Tracking**: Monitors actual spending during task execution
- **Cost Control Logic**: Implements thresholds and approval workflows
- **Cost Optimization**: Provides recommendations for cost reduction

#### 2. Cost Data Models

##### CostTier Enum

```python
class CostTier(Enum):
    LOW = "low"          # Simple queries, single agent
    MEDIUM = "medium"    # Multi-agent, moderate complexity
    HIGH = "high"        # Complex research, parallel execution
    CRITICAL = "critical" # Emergency stop threshold
```

##### CostEstimate Dataclass

```python
@dataclass
class CostEstimate:
    estimated_tokens: int     # Predicted token consumption
    estimated_cost_usd: float # Predicted cost in USD
    task_complexity: CostTier # Complexity classification
    agent_count: int          # Number of agents involved
    parallel_factor: int      # Parallelism multiplier
    confidence: float         # Estimation confidence (0.0-1.0)
    reasoning: str           # Human-readable explanation
```

##### CostUsage Dataclass

```python
@dataclass
class CostUsage:
    task_id: str                    # Unique task identifier
    session_id: str                 # Session/conversation ID
    start_time: datetime            # Task start timestamp
    end_time: Optional[datetime]    # Task completion timestamp
    tokens_used: int               # Actual tokens consumed
    cost_usd: float                # Actual cost in USD
    provider_breakdown: Dict       # Cost per AI provider
    agent_breakdown: Dict          # Cost per agent type
```

## Cost Estimation Process

### 1. Task Analysis

The system analyzes multiple factors to estimate costs:

#### Query Complexity Assessment

```python
def _assess_task_complexity(self, query: str, agents: List[str],
                          parallel_execution: bool) -> CostTier:
```

**Complexity Indicators:**

- **High Complexity Keywords**: 'comprehensive', 'detailed analysis', 'systematic review'
- **Medium Complexity Keywords**: 'analyze', 'compare', 'summarize', 'explain'
- **Query Length**: Longer queries typically require more processing
- **Agent Count**: More agents increase complexity
- **Execution Mode**: Parallel execution adds overhead

#### Scoring Algorithm

```python
complexity_score = 0

# Query complexity (1-3 points)
if high_complexity_keywords in query: complexity_score += 3
elif medium_complexity_keywords in query: complexity_score += 2
else: complexity_score += 1

# Agent count (0-2 points)
if len(agents) >= 4: complexity_score += 2
elif len(agents) >= 2: complexity_score += 1

# Parallel execution (0-1 points)
if parallel_execution: complexity_score += 1

# Query length (0-1 points)
if len(query) > 200: complexity_score += 1

# Final classification
if complexity_score >= 6: return CostTier.HIGH
elif complexity_score >= 4: return CostTier.MEDIUM
else: return CostTier.LOW
```

### 2. Token Estimation

#### Base Token Calculation

```python
# Input tokens
query_tokens = len(query) // 4  # ~4 characters per token
context_tokens = sum(len(msg.content) // 4 for msg in context_messages)
system_prompt_tokens = 200  # Standard system prompt size

# Output tokens (per agent)
base_tokens_per_agent = max(500, query_tokens * 2)  # Response ~2x query length

# Apply complexity multiplier
complexity_multiplier = {
    CostTier.LOW: 1.0,      # Simple operations
    CostTier.MEDIUM: 2.5,   # Moderate complexity
    CostTier.HIGH: 5.0,     # Complex research
    CostTier.CRITICAL: 10.0 # Emergency threshold
}[task_complexity]

# Total token estimation
total_tokens = int(
    (query_tokens + context_tokens + system_prompt_tokens) * agent_count +
    base_tokens_per_agent * agent_count * complexity_multiplier
)
```

#### Token Distribution

- **Input Tokens (70%)**: Query, context, system prompts
- **Output Tokens (30%)**: AI-generated responses and analysis

### 3. Cost Calculation

#### Provider Pricing Model

```python
token_costs = {
    'openai': {
        'gpt-4o-mini': {'input': 0.00015, 'output': 0.0006},  # per 1K tokens
        'gpt-4': {'input': 0.03, 'output': 0.06},
        'gpt-3.5-turbo': {'input': 0.0015, 'output': 0.002}
    },
    'xai': {
        'grok-3-mini-beta': {'input': 0.0002, 'output': 0.0008},
        'grok-3': {'input': 0.002, 'output': 0.004}
    }
}
```

#### Cost Calculation Formula

```python
input_tokens = int(total_tokens * 0.7)
output_tokens = int(total_tokens * 0.3)

estimated_cost = (
    (input_tokens / 1000) * cost_per_1k['input'] +
    (output_tokens / 1000) * cost_per_1k['output']
)
```

## Cost Control Mechanisms

### 1. Cost Thresholds

#### Default Threshold Configuration

```python
cost_thresholds = {
    'session_warning': 1.0,    # Warning at $1 per session
    'session_limit': 5.0,      # Hard limit at $5 per session
    'daily_warning': 10.0,     # Warning at $10 per day
    'daily_limit': 50.0,       # Hard limit at $50 per day
    'emergency_stop': 100.0    # Emergency stop at $100
}
```

#### Threshold Enforcement

```python
def should_proceed_with_task(self, estimate: CostEstimate, session_id: str) -> tuple[bool, str]:
    # Check session limits
    session_cost = self._get_session_cost(session_id)
    if session_cost + estimate.estimated_cost_usd > self.cost_thresholds['session_limit']:
        return False, "Session cost limit exceeded"

    # Check daily limits
    today_cost = self._get_daily_cost()
    if today_cost + estimate.estimated_cost_usd > self.cost_thresholds['daily_limit']:
        return False, "Daily cost limit exceeded"

    # Check emergency stop
    if estimate.estimated_cost_usd > self.cost_thresholds['emergency_stop']:
        return False, "Task cost exceeds emergency threshold"

    return True, "Cost within acceptable limits"
```

### 2. Cost Approval Workflow

#### Automatic Approval

- **Low-cost tasks** (< session warning threshold) proceed automatically
- **Pre-approved tasks** with `cost_override=True` bypass limits

#### User Approval Required

- **Medium-cost tasks** require explicit user consent
- **High-cost tasks** show detailed cost breakdown and alternatives

#### Rejection Scenarios

- **Session limit exceeded**: Current session spending + estimated cost > limit
- **Daily limit exceeded**: Today's spending + estimated cost > daily limit
- **Emergency threshold**: Single task cost exceeds emergency stop

## Real-Time Usage Tracking

### 1. Session Management

#### Starting Cost Tracking

```python
def start_cost_tracking(self, task_id: str, session_id: str) -> None:
    self.active_sessions[task_id] = CostUsage(
        task_id=task_id,
        session_id=session_id,
        start_time=datetime.now()
    )
```

#### Recording Usage

```python
def record_usage(self, task_id: str, provider: str, model: str,
                input_tokens: int, output_tokens: int,
                agent_type: Optional[str] = None) -> None:
    # Calculate actual cost
    cost_per_1k = self.token_costs[provider][model]
    input_cost = (input_tokens / 1000) * cost_per_1k['input']
    output_cost = (output_tokens / 1000) * cost_per_1k['output']
    total_cost = input_cost + output_cost

    # Update tracking
    usage = self.active_sessions[task_id]
    usage.tokens_used += total_tokens
    usage.cost_usd += total_cost

    # Update breakdowns
    self._update_provider_breakdown(usage, provider, total_tokens, total_cost)
    self._update_agent_breakdown(usage, agent_type, total_tokens, total_cost)

    # Check thresholds
    self._check_cost_thresholds(usage)
```

### 2. Cost Breakdown Tracking

#### Provider Breakdown

Tracks costs per AI provider (OpenAI, XAI, etc.):

```python
provider_breakdown = {
    'openai': {'tokens': 1500, 'cost': 0.045},
    'xai': {'tokens': 800, 'cost': 0.016}
}
```

#### Agent Breakdown

Tracks costs per agent type:

```python
agent_breakdown = {
    'literature': {'tokens': 1200, 'cost': 0.036},
    'planning': {'tokens': 800, 'cost': 0.024},
    'executor': {'tokens': 300, 'cost': 0.009}
}
```

### 3. Daily Usage Aggregation

```python
daily_usage = {
    '2025-07-21': 15.75,  # Total cost for July 21, 2025
    '2025-07-20': 8.50,   # Total cost for July 20, 2025
    # ... historical data
}
```

## Cost Optimization

### 1. Optimization Recommendations

The system provides intelligent recommendations based on cost analysis:

#### High-Cost Task Recommendations

```python
def get_cost_recommendations(self, estimate: CostEstimate) -> Dict[str, Any]:
    recommendations = {'suggestions': [], 'alternatives': {}}

    # Cost-based suggestions
    if estimate.estimated_cost_usd > 1.0:
        recommendations['suggestions'].append(
            "Consider breaking down into smaller sub-tasks"
        )

    # Agent optimization
    if estimate.agent_count > 2:
        recommendations['alternatives']['single_agent'] = {
            'estimated_cost': estimate.estimated_cost_usd * 0.4,
            'trade_offs': 'Reduced parallel processing, simpler analysis'
        }

    # Execution mode optimization
    if estimate.parallel_factor > 1:
        recommendations['alternatives']['sequential'] = {
            'estimated_cost': estimate.estimated_cost_usd * 0.7,
            'trade_offs': 'Longer execution time, reduced parallelism benefits'
        }

    return recommendations
```

#### Common Optimization Strategies

1. **Single-Agent Mode**

   - **Cost Reduction**: ~60% cost savings
   - **Trade-offs**: Simpler analysis, no parallel processing
   - **Best for**: Simple queries, budget constraints

2. **Sequential Execution**

   - **Cost Reduction**: ~30% cost savings
   - **Trade-offs**: Longer execution time
   - **Best for**: Non-time-critical tasks

3. **Task Decomposition**

   - **Cost Reduction**: Variable, often 20-40%
   - **Trade-offs**: Multiple smaller results vs. comprehensive analysis
   - **Best for**: Complex, multi-part queries

4. **Memory Agent Utilization**
   - **Cost Reduction**: Prevents redundant information gathering
   - **Trade-offs**: Requires context management
   - **Best for**: Repeated or related queries

### 2. Cost-Performance Trade-offs

#### Performance Modes

```python
# High Performance (Default)
agents = ["literature", "planning", "executor", "memory"]
parallel_execution = True
complexity_multiplier = 1.0

# Balanced Performance
agents = ["literature", "planning"]
parallel_execution = True
complexity_multiplier = 0.6

# Cost-Optimized
agents = ["literature"]
parallel_execution = False
complexity_multiplier = 0.4
```

## Integration with Research Manager

### 1. Cost Estimation in Task Flow

#### Pre-Task Estimation

```python
async def _estimate_task_cost(
    self,
    query: str,
    conversation_id: str,
    options: Optional[Dict[str, Any]] = None
) -> tuple[Dict[str, Any], bool, bool]:
    # Determine agent configuration
    single_agent_mode = options.get('single_agent_mode', False)
    agents_to_use = ["literature"] if single_agent_mode else ["literature", "planning", "executor", "memory"]

    # Get cost estimate
    cost_estimate = self.cost_estimator.estimate_task_cost(
        query=query,
        agents=agents_to_use,
        parallel_execution=not single_agent_mode
    )

    # Check approval
    should_proceed, cost_reason = self.cost_estimator.should_proceed_with_task(
        cost_estimate, conversation_id
    )

    return cost_info, should_proceed, single_agent_mode
```

#### Task Execution with Cost Tracking

```python
async def start_research_task(self, query: str, user_id: str, conversation_id: str, options: Optional[Dict[str, Any]] = None):
    # Estimate costs
    cost_info, should_proceed, single_agent_mode = await self._estimate_task_cost(query, conversation_id, options)

    # Create context with cost information
    context = ResearchContext(
        estimated_cost=cost_info['estimate']['cost_usd'],
        single_agent_mode=single_agent_mode
    )

    # Approval logic
    if should_proceed or context.cost_approved:
        # Start cost tracking
        self.cost_estimator.start_cost_tracking(task_id, conversation_id)

        # Execute task
        asyncio.create_task(self._orchestrate_research_task(context))
```

### 2. Runtime Cost Monitoring

#### Agent Communication with Cost Tracking

When agents make API calls, usage is automatically recorded:

```python
# After each agent API call
self.cost_estimator.record_usage(
    task_id=context.task_id,
    provider="openai",
    model="gpt-4o-mini",
    input_tokens=request_tokens,
    output_tokens=response_tokens,
    agent_type="literature"
)
```

#### Final Cost Reconciliation

```python
# At task completion
final_usage = self.cost_estimator.end_cost_tracking(context.task_id)
if final_usage:
    context.actual_cost = final_usage.cost_usd
    self.logger.info(f"Task completed: estimated ${context.estimated_cost:.4f}, actual ${context.actual_cost:.4f}")
```

## Web API Integration

### 1. Cost Estimation Endpoints

#### Pre-Task Cost Estimation

```python
# GET /api/research/estimate
{
    "query": "Analyze market trends in AI",
    "single_agent_mode": false
}

# Response
{
    "estimate": {
        "tokens": 2500,
        "cost_usd": 0.075,
        "complexity": "medium",
        "agent_count": 4,
        "confidence": 0.8,
        "reasoning": "Query complexity: medium; Agent count: 4; Estimated 2,500 tokens"
    },
    "recommendations": {
        "suggestions": ["Consider single-agent mode for cost savings"],
        "alternatives": {
            "single_agent": {
                "estimated_cost": 0.030,
                "trade_offs": "Reduced parallel processing"
            }
        }
    }
}
```

#### Task Cost Status

```python
# GET /api/research/task/{task_id}/cost
{
    "task_id": "uuid-123",
    "estimated_cost": 0.075,
    "actual_cost": 0.082,
    "cost_approved": true,
    "single_agent_mode": false,
    "current_usage": {
        "tokens_used": 2650,
        "cost_usd": 0.082,
        "duration_seconds": 45.2,
        "provider_breakdown": {
            "openai": {"tokens": 2650, "cost": 0.082}
        },
        "agent_breakdown": {
            "literature": {"tokens": 1200, "cost": 0.036},
            "planning": {"tokens": 1450, "cost": 0.046}
        }
    }
}
```

### 2. Usage Summary Endpoints

#### Session Cost Summary

```python
# GET /api/research/costs/session/{session_id}
{
    "session_id": "conv_123",
    "total_cost": 0.245,
    "total_tokens": 7500,
    "active_tasks": 2,
    "usage_breakdown": [
        {
            "task_id": "task_1",
            "cost": 0.082,
            "tokens": 2650,
            "duration": 45.2
        },
        {
            "task_id": "task_2",
            "cost": 0.163,
            "tokens": 4850,
            "duration": 67.8
        }
    ]
}
```

#### Daily Usage Summary

```python
# GET /api/research/costs/daily
{
    "total_active_sessions": 5,
    "total_active_tasks": 8,
    "total_cost": 12.75,
    "total_tokens": 425000,
    "daily_usage": {
        "2025-07-21": 12.75,
        "2025-07-20": 8.50,
        "2025-07-19": 15.25
    },
    "thresholds": {
        "session_warning": 1.0,
        "session_limit": 5.0,
        "daily_warning": 10.0,
        "daily_limit": 50.0
    }
}
```

## Configuration and Customization

### 1. Cost Configuration

#### Provider Pricing Updates

```python
# Update token costs for new models or providers
cost_estimator.token_costs['anthropic'] = {
    'claude-3': {'input': 0.008, 'output': 0.024}
}
```

#### Threshold Customization

```python
# Update cost control thresholds
research_manager.update_cost_thresholds({
    'session_warning': 0.50,   # Lower warning threshold
    'session_limit': 2.00,     # Stricter session limit
    'daily_limit': 25.00       # Reduced daily limit
})
```

### 2. Complexity Assessment Tuning

#### Custom Complexity Keywords

```python
# Add domain-specific complexity indicators
high_complexity_keywords.extend([
    'regulatory analysis', 'compliance review',
    'multi-jurisdictional', 'cross-referencing'
])
```

#### Complexity Multiplier Adjustment

```python
# Adjust complexity multipliers for domain-specific tasks
complexity_multipliers = {
    CostTier.LOW: 0.8,      # Reduce for simple domain queries
    CostTier.MEDIUM: 2.0,   # Standard complexity
    CostTier.HIGH: 4.0,     # Reduce high complexity penalty
    CostTier.CRITICAL: 8.0  # Adjusted emergency threshold
}
```

## Monitoring and Analytics

### 1. Cost Monitoring Dashboards

#### Real-Time Cost Tracking

- **Active Task Costs**: Live monitoring of running research tasks
- **Session Utilization**: Cost accumulation per conversation
- **Provider Distribution**: Spending breakdown across AI providers
- **Agent Efficiency**: Cost per agent type and performance metrics

#### Historical Analytics

- **Daily/Weekly/Monthly Trends**: Cost patterns over time
- **Task Complexity Analysis**: Accuracy of complexity predictions
- **Cost vs. Performance**: Correlation between spending and result quality
- **Optimization Impact**: Savings from cost reduction strategies

### 2. Alert System

#### Threshold Alerts

```python
# Cost threshold monitoring
if session_cost > thresholds['session_warning']:
    send_alert('Session cost approaching limit', session_id)

if daily_cost > thresholds['daily_warning']:
    send_alert('Daily spending approaching limit', date)

if task_cost > thresholds['emergency_stop']:
    send_emergency_alert('Task exceeds emergency threshold', task_id)
```

#### Anomaly Detection

- **Unexpected Cost Spikes**: Detection of unusually expensive tasks
- **Estimation Accuracy**: Monitoring prediction vs. actual cost variance
- **Usage Pattern Changes**: Identification of unusual spending patterns

## Best Practices

### 1. Cost-Effective Task Design

#### Query Optimization

1. **Be Specific**: Focused queries reduce complexity and cost
2. **Avoid Redundancy**: Don't repeat information in queries
3. **Use Context**: Leverage conversation history efficiently
4. **Break Down Complex Tasks**: Split large queries into smaller components

#### Agent Selection Strategy

1. **Single-Agent Mode**: Use for simple, straightforward queries
2. **Selective Multi-Agent**: Choose only necessary agents
3. **Sequential Processing**: When time permits, reduce parallel overhead
4. **Memory Utilization**: Leverage memory agent to avoid redundant searches

### 2. Budget Management

#### Session Planning

1. **Set Clear Budgets**: Define spending limits per conversation
2. **Monitor Progress**: Track costs throughout research sessions
3. **Plan for Complexity**: Reserve budget for unexpected complexity
4. **Use Estimates**: Always check cost estimates before proceeding

#### Daily/Monthly Budgeting

1. **Establish Limits**: Set realistic daily and monthly spending caps
2. **Track Trends**: Monitor spending patterns and adjust limits
3. **Plan for Growth**: Account for increased usage over time
4. **Emergency Reserves**: Maintain buffer for critical tasks

### 3. Optimization Strategies

#### Proactive Cost Management

1. **Regular Reviews**: Analyze cost reports and identify optimization opportunities
2. **Threshold Tuning**: Adjust cost limits based on usage patterns
3. **Provider Optimization**: Use most cost-effective AI providers for each task type
4. **Batch Processing**: Group related queries to reduce overhead

#### Performance vs. Cost Balance

1. **Quality Requirements**: Define minimum acceptable result quality
2. **Time Constraints**: Balance speed vs. cost for urgent tasks
3. **User Expectations**: Communicate cost-performance trade-offs clearly
4. **Fallback Strategies**: Have cost-effective alternatives ready

## Troubleshooting

### 1. Common Cost Issues

#### Estimation Inaccuracy

**Problem**: Actual costs significantly higher than estimates
**Solutions**:

- Review complexity assessment keywords
- Update token estimation models
- Calibrate complexity multipliers
- Monitor provider pricing changes

#### Unexpected Cost Spikes

**Problem**: Sudden increase in task costs
**Solutions**:

- Check for query complexity changes
- Verify provider pricing updates
- Review agent selection logic
- Investigate parallel execution overhead

#### Threshold Violations

**Problem**: Tasks exceeding cost limits unexpectedly
**Solutions**:

- Review threshold configuration
- Analyze task complexity trends
- Update estimation algorithms
- Implement progressive warnings

### 2. Cost Control Failures

#### Budget Overruns

**Problem**: Daily or session limits exceeded
**Solutions**:

- Implement stricter pre-approval workflows
- Add emergency stop mechanisms
- Review estimation accuracy
- Strengthen threshold enforcement

#### Approval Bypass Issues

**Problem**: High-cost tasks proceeding without approval
**Solutions**:

- Audit cost override usage
- Strengthen approval workflows
- Implement multi-level approvals for high costs
- Add mandatory delay for expensive tasks

## Future Enhancements

### 1. Advanced Cost Prediction

#### Machine Learning Integration

- **Historical Analysis**: Use past task data to improve predictions
- **Pattern Recognition**: Identify cost patterns for similar queries
- **Dynamic Pricing**: Adapt to provider pricing changes automatically
- **User Behavior Modeling**: Predict user cost preferences

#### Enhanced Complexity Assessment

- **Semantic Analysis**: Use AI to assess query complexity more accurately
- **Domain-Specific Models**: Specialized complexity assessment for different fields
- **Real-Time Adjustment**: Dynamic complexity scoring based on intermediate results

### 2. Advanced Cost Controls

#### Dynamic Pricing

- **Time-Based Pricing**: Different cost limits for peak vs. off-peak hours
- **User-Specific Limits**: Customized thresholds per user or organization
- **Project-Based Budgets**: Cost allocation and tracking per research project
- **Subscription Models**: Monthly allowances with overage controls

#### Smart Optimization

- **Automatic Mode Selection**: AI-driven choice between performance modes
- **Cost-Quality Optimization**: Automatic trade-off optimization
- **Predictive Scaling**: Preemptive cost control based on usage trends
- **Real-Time Recommendations**: Dynamic suggestions during task execution

---

_For technical support or questions about the cost estimation system, please refer to the source code documentation or contact the development team._
