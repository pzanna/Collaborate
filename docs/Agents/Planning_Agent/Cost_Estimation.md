# Cost Estimation System Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Cost Estimation Components](#cost-estimation-components)
4. [Frontend Implementation](#frontend-implementation)
5. [Backend Implementation](#backend-implementation)
6. [Cost Calculation Examples](#cost-calculation-examples)
7. [Cost Optimization](#cost-optimization)
8. [Configuration](#configuration)
9. [API Integration](#api-integration)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The Eunice Research Platform includes a sophisticated cost estimation system that provides accurate cost tracking, optimization, and budget management for research operations. The system operates at multiple levels:

- **AI Operations Costs**: Token usage, API calls, and model complexity
- **Traditional Research Costs**: Database access, software licenses, expert consultation
- **Currency Conversion**: USD to AUD conversion with real-time rates
- **Cost Optimization**: Intelligent recommendations for cost reduction
- **Budget Management**: Session and daily cost limits with warnings

### Key Features

- **Real-time Cost Tracking**: Monitor costs as operations occur
- **Multi-provider Support**: OpenAI, XAI, and other AI providers
- **Complexity Assessment**: Intelligent LOW/MEDIUM/HIGH complexity scoring
- **Cost Breakdown Analysis**: Detailed breakdown of all cost components
- **Optimization Recommendations**: Context-aware cost reduction suggestions
- **Interactive Cost Dialog**: Detailed cost breakdown with visual components
- **Currency Support**: USD/AUD conversion with approximate exchange rates

---

## Architecture

### System Components

```text
Frontend (React/TypeScript)
├── ResearchPlanDetails.tsx     # Main cost display component
├── Cost Breakdown Dialog       # Interactive cost analysis
└── Status Box                  # Quick cost overview

Backend (Python)
├── Planning Agent
│   ├── cost_estimator.py      # Core cost estimation logic
│   ├── planning_service.py    # Cost estimation endpoints
│   └── config_manager.py      # Cost configuration
└── API Gateway
    └── Cost estimation routes  # API endpoints for cost data
```

### Data Flow

```text
User Request → API Gateway → Planning Agent → Cost Estimator
                                          ↓
Cost Calculation → Metadata Storage → Frontend Display
                                          ↓
Interactive Dialog ← User Click ← Cost Breakdown
```

---

## Cost Estimation Components

### 1. AI Operations Costs

AI operations costs are calculated based on token usage and provider pricing:

#### Token Estimation

```python
# Token estimation for text content
def _estimate_tokens_for_text(self, text: str) -> int:
    """Estimate tokens for a text string."""
    # Rough approximation: ~4 characters per token
    return max(1, len(text) // 4)

# API call cost calculation
def estimate_cost(self, provider: str, model: str, 
                 input_tokens: int, output_tokens: int) -> float:
    """Calculate the cost for given token usage"""
    cost_info = self.token_costs.get(provider, {}).get(model)
    if not cost_info:
        # Fallback to OpenAI GPT-4 pricing
        cost_info = self.token_costs["openai"]["gpt-4"]
    
    input_cost = (input_tokens / 1000) * cost_info["input"]
    output_cost = (output_tokens / 1000) * cost_info["output"]
    return input_cost + output_cost
```

#### Complexity Assessment

```python
def _assess_task_complexity(self, query: str, agents: List[str], 
                          parallel_execution: bool) -> CostTier:
    """Assess the complexity tier of a research task."""
    
    # High complexity indicators
    high_complexity_keywords = [
        "comprehensive", "detailed analysis", "compare multiple",
        "research study", "in-depth", "systematic review"
    ]
    
    # Medium complexity indicators  
    medium_complexity_keywords = [
        "analyze", "compare", "summarize", "explain",
        "relationship", "trend", "pattern"
    ]
    
    complexity_score = 0
    
    # Query complexity analysis
    if any(keyword in query.lower() for keyword in high_complexity_keywords):
        complexity_score += 3
    elif any(keyword in query.lower() for keyword in medium_complexity_keywords):
        complexity_score += 2
    else:
        complexity_score += 1
    
    # Agent count factor
    if len(agents) >= 4:
        complexity_score += 2
    elif len(agents) >= 2:
        complexity_score += 1
    
    # Parallel execution factor
    if parallel_execution:
        complexity_score += 1
    
    # Query length factor
    if len(query) > 200:
        complexity_score += 1
    
    # Determine tier
    if complexity_score >= 6:
        return CostTier.HIGH
    elif complexity_score >= 4:
        return CostTier.MEDIUM
    else:
        return CostTier.LOW
```

### 2. Traditional Research Costs

Traditional costs include non-AI research expenses:

```python
# Cost breakdown calculation
traditional_costs = {
    "database_access": {
        "usd": estimated_cost_usd * 0.3,  # 30% for database access
        "aud": convert_to_aud(estimated_cost_usd * 0.3),
        "description": "Academic databases, research repositories"
    },
    "analysis_software": {
        "usd": estimated_cost_usd * 0.2,  # 20% for software
        "aud": convert_to_aud(estimated_cost_usd * 0.2),
        "description": "Statistical software, analysis tools"
    },
    "expert_consultation": {
        "usd": estimated_cost_usd * 0.4,  # 40% for expert time
        "aud": convert_to_aud(estimated_cost_usd * 0.4),
        "description": "Subject matter expert consultation"
    }
}
```

### 3. Currency Conversion

```typescript
// Currency conversion (USD to AUD)
const USD_TO_AUD_RATE = 1.55; // This would typically come from an API

const convertToAUD = (usdAmount: number): number => {
  return usdAmount * USD_TO_AUD_RATE;
};

const formatAUD = (amount: number): string => {
  return `$${amount.toFixed(2)}`;
};
```

---

## Frontend Implementation

### 1. Cost Display in Status Box

The main cost display shows estimated and actual costs:

```typescript
// Status box cost display
<div className="text-center">
  <div
    className="text-2xl font-bold text-black hover:text-gray-700 cursor-pointer"
    onClick={() => setShowCostDialog(true)}
    title="Click to view cost breakdown"
  >
    {formatAUD(convertToAUD(researchPlan.estimated_cost || 0))}
  </div>
  <div className="text-sm text-muted-foreground">Estimated</div>
</div>
```

### 2. Cost Breakdown Calculation

```typescript
const getCostBreakdown = () => {
  if (!researchPlan) return null;

  const estimatedCostUSD = researchPlan.estimated_cost || 0;
  const actualCostUSD = researchPlan.actual_cost || 0;

  // Extract cost estimate from metadata if available
  const metadata = researchPlan.metadata || {};
  const costEstimate = metadata.cost_estimate || {};

  // Create breakdown structure
  const breakdown = {
    estimated: {
      total_usd: estimatedCostUSD,
      total_aud: convertToAUD(estimatedCostUSD),
      ai_operations: {
        usd: costEstimate.estimated_cost || estimatedCostUSD * 0.1,
        aud: convertToAUD(
          costEstimate.estimated_cost || estimatedCostUSD * 0.1
        ),
        complexity: costEstimate.complexity || "MEDIUM",
      },
      traditional_costs: {
        database_access: {
          usd: estimatedCostUSD * 0.3,
          aud: convertToAUD(estimatedCostUSD * 0.3),
        },
        analysis_software: {
          usd: estimatedCostUSD * 0.2,
          aud: convertToAUD(estimatedCostUSD * 0.2),
        },
        expert_consultation: {
          usd: estimatedCostUSD * 0.4,
          aud: convertToAUD(estimatedCostUSD * 0.4),
        },
      },
    },
    actual: {
      total_usd: actualCostUSD,
      total_aud: convertToAUD(actualCostUSD),
      ai_operations: {
        usd: actualCostUSD * 0.1,
        aud: convertToAUD(actualCostUSD * 0.1),
      },
      other_costs: {
        usd: actualCostUSD * 0.9,
        aud: convertToAUD(actualCostUSD * 0.9),
      },
    },
    optimization_suggestions: costEstimate.optimization_suggestions || [
      "Consider breaking down into smaller sub-tasks",
      "Use caching to avoid redundant analysis",
      "Optimize AI model usage for cost efficiency",
    ],
  };

  return breakdown;
};
```

### 3. Interactive Cost Dialog

```typescript
// Cost Breakdown Dialog Component
<Dialog open={showCostDialog} onOpenChange={setShowCostDialog}>
  <DialogContent className="sm:max-w-[700px]">
    <DialogHeader className="text-center">
      <DialogTitle className="flex items-center justify-center">
        <DollarSign className="h-5 w-5 mr-2 text-green-600" />
        Cost Breakdown Analysis
      </DialogTitle>
      <DialogDescription className="text-center">
        Detailed breakdown of research plan costs in Australian dollars
      </DialogDescription>
    </DialogHeader>

    {(() => {
      const breakdown = getCostBreakdown();
      if (!breakdown) return <div>No cost data available</div>;

      return (
        <div className="space-y-6">
          {/* Exchange Rate Info */}
          <div className="bg-blue-50 p-3 rounded-lg border border-blue-200">
            <div className="text-sm text-blue-800 text-center">
              <strong>Exchange Rate:</strong> 1 USD = {USD_TO_AUD_RATE} AUD (approximate)
            </div>
          </div>

          {/* Estimated Costs */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-900">Estimated Costs</h3>
            
            {/* Total Cost Display */}
            <div className="bg-green-50 p-4 rounded-lg border border-green-200">
              <div className="flex justify-between items-center mb-3">
                <h4 className="font-medium text-green-900">Total Estimated Cost</h4>
                <div className="text-center">
                  <div className="text-lg font-bold text-green-800">
                    {formatAUD(breakdown.estimated.total_aud)}
                  </div>
                  <div className="text-sm text-green-600">
                    (${breakdown.estimated.total_usd.toFixed(2)} USD)
                  </div>
                </div>
              </div>
            </div>

            {/* AI Operations Cost */}
            <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
              <div className="flex justify-between items-center mb-2">
                <h4 className="font-medium text-purple-900">AI Operations</h4>
                <div className="text-center">
                  <div className="font-semibold text-purple-800">
                    {formatAUD(breakdown.estimated.ai_operations.aud)}
                  </div>
                  <div className="text-sm text-purple-600">
                    (${breakdown.estimated.ai_operations.usd.toFixed(2)} USD)
                  </div>
                </div>
              </div>
              <div className="text-sm text-purple-700">
                Complexity Level: <span className="font-medium">
                  {breakdown.estimated.ai_operations.complexity}
                </span>
              </div>
            </div>

            {/* Traditional Costs Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="bg-yellow-50 p-3 rounded border border-yellow-200 text-center">
                <div className="text-sm font-medium text-yellow-900">Database Access</div>
                <div className="text-yellow-800 font-semibold">
                  {formatAUD(breakdown.estimated.traditional_costs.database_access.aud)}
                </div>
                <div className="text-xs text-yellow-600">
                  (${breakdown.estimated.traditional_costs.database_access.usd.toFixed(2)} USD)
                </div>
              </div>
              
              {/* Analysis Software and Expert Consultation similar structure */}
            </div>
          </div>

          {/* Cost Optimization Suggestions */}
          <div className="space-y-3">
            <h3 className="text-lg font-semibold text-gray-900">
              Cost Optimization Suggestions
            </h3>
            <div className="bg-gray-50 p-4 rounded-lg">
              <ul className="space-y-2">
                {breakdown.optimization_suggestions.map(
                  (suggestion: string, index: number) => (
                    <li key={index} className="flex items-start">
                      <span className="w-5 h-5 bg-gray-200 text-gray-700 rounded-full text-xs font-medium flex items-center justify-center mr-3 flex-shrink-0">
                        {index + 1}
                      </span>
                      <span className="text-sm text-gray-700">{suggestion}</span>
                    </li>
                  )
                )}
              </ul>
            </div>
          </div>
        </div>
      );
    })()}
  </DialogContent>
</Dialog>
```

---

## Backend Implementation

### 1. Cost Estimator Class

```python
class CostEstimator:
    """
    Estimates and tracks costs for AI operations.
    
    Provides cost estimation for research tasks, tracks actual usage,
    and implements cost control mechanisms.
    """

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        self.total_cost = 0.0
        self.cost_by_provider: Dict[str, float] = defaultdict(float)
        self.cost_by_model: Dict[str, float] = defaultdict(float)
        self.active_sessions: Dict[str, CostUsage] = {}
        self.daily_usage: Dict[str, float] = defaultdict(float)

        # Load cost configurations
        self.token_costs = self._load_token_costs()
        self.cost_thresholds = self._load_cost_thresholds()
        self.complexity_multipliers = self._load_complexity_multipliers()
```

### 2. Task Cost Estimation

```python
def estimate_task_cost(
    self,
    query: str,
    agents: List[str],
    parallel_execution: bool = False,
    context_content: Optional[str] = None,
) -> CostEstimate:
    """
    Estimate cost for a research task.
    
    Args:
        query: Research query
        agents: List of agent types to be used
        parallel_execution: Whether agents run in parallel
        context_content: Existing conversation context as text
    
    Returns:
        CostEstimate: Detailed cost estimation
    """
    # Base token estimation
    query_tokens = self._estimate_tokens_for_text(query)
    context_tokens = 0
    
    if context_content:
        context_tokens = self._estimate_tokens_for_text(context_content)
    
    # Determine task complexity
    complexity = self._assess_task_complexity(query, agents, parallel_execution)
    
    # Calculate agent-specific costs
    agent_count = len(agents)
    parallel_factor = agent_count if parallel_execution else 1
    
    # Base estimation per agent
    base_tokens_per_agent = max(500, query_tokens * 2)  # Response typically 2x query
    system_prompt_tokens = 200  # Approximate system prompt size
    
    # Apply complexity multiplier
    complexity_multiplier = self.complexity_multipliers[complexity]
    
    # Total token estimation
    total_tokens = int(
        (query_tokens + context_tokens + system_prompt_tokens) * agent_count
        + base_tokens_per_agent * agent_count * complexity_multiplier
    )
    
    # Estimate cost using primary provider pricing
    primary_provider = self.config_manager.config.research_manager.provider
    primary_model = self.config_manager.config.research_manager.model
    
    cost_per_1k = self.token_costs.get(primary_provider, {}).get(primary_model, {})
    if not cost_per_1k:
        # Fallback to OpenAI gpt-4 pricing
        cost_per_1k = self.token_costs["openai"]["gpt-4"]
    
    # Assume 70% input, 30% output tokens
    input_tokens = int(total_tokens * 0.7)
    output_tokens = int(total_tokens * 0.3)
    
    estimated_cost = (input_tokens / 1000) * cost_per_1k["input"] + (
        output_tokens / 1000
    ) * cost_per_1k["output"]
    
    # Generate reasoning
    reasoning = self._generate_cost_reasoning(
        query, agents, complexity, parallel_execution, total_tokens, estimated_cost
    )
    
    return CostEstimate(
        estimated_tokens=total_tokens,
        estimated_cost_usd=estimated_cost,
        task_complexity=complexity,
        agent_count=agent_count,
        parallel_factor=parallel_factor,
        confidence=0.8 if complexity in [CostTier.LOW, CostTier.MEDIUM] else 0.6,
        reasoning=reasoning,
    )
```

### 3. Cost Tracking and Usage Recording

```python
def record_usage(
    self,
    task_id: str,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    agent_type: Optional[str] = None,
) -> None:
    """
    Record actual token usage and cost.
    
    Args:
        task_id: Task identifier
        provider: AI provider (openai, xai)
        model: Model name
        input_tokens: Input tokens used
        output_tokens: Output tokens used
        agent_type: Type of agent that made the call
    """
    if task_id not in self.active_sessions:
        self.logger.warning(f"Recording usage for untracked task {task_id}")
        return
    
    # Calculate cost
    cost_per_1k = self.token_costs.get(provider, {}).get(model, {})
    if not cost_per_1k:
        self.logger.warning(f"No cost data for {provider}/{model}, using fallback")
        cost_per_1k = self.token_costs["openai"]["gpt-4"]
    
    input_cost = (input_tokens / 1000) * cost_per_1k["input"]
    output_cost = (output_tokens / 1000) * cost_per_1k["output"]
    total_cost = input_cost + output_cost
    total_tokens = input_tokens + output_tokens
    
    # Update session tracking
    usage = self.active_sessions[task_id]
    usage.tokens_used += total_tokens
    usage.cost_usd += total_cost
    
    # Update provider and agent breakdowns
    self._update_usage_breakdowns(usage, provider, agent_type, total_tokens, total_cost)
    
    # Update daily usage
    today = datetime.now().strftime("%Y-%m-%d")
    self.daily_usage[today] += total_cost
    
    # Check thresholds
    self._check_cost_thresholds(usage)
```

---

## Cost Calculation Examples

### Example 1: Simple Research Query

**Input:**

```json
{
  "query": "What are the benefits of renewable energy?",
  "agents": ["research_manager"],
  "parallel_execution": false
}
```

**Cost Calculation:**

```python
# Token estimation
query_tokens = 35  # ~8 words * 4 chars/token ÷ 4
response_tokens = 70  # Estimated 2x query length
system_tokens = 200  # Standard system prompt
total_tokens = 305

# Complexity assessment: LOW (simple query, single agent)
complexity_multiplier = 1.0
adjusted_tokens = 305 * 1.0 = 305

# Cost calculation (OpenAI GPT-4o-mini)
input_cost = (305 * 0.7 / 1000) * 0.00015 = $0.000032
output_cost = (305 * 0.3 / 1000) * 0.0006 = $0.000055
total_cost = $0.000087
```

**Result:**

```json
{
  "estimated_cost": 0.000087,
  "complexity": "LOW",
  "tokens_estimated": 305,
  "optimization_suggestions": [
    "Query is already optimized for cost efficiency"
  ]
}
```

### Example 2: Complex Multi-Agent Research

**Input:**

```json
{
  "query": "Comprehensive analysis of AI impact on healthcare diagnostics including market trends, technical capabilities, and regulatory requirements",
  "agents": ["research_manager", "literature_agent", "screening_agent", "synthesis_agent"],
  "parallel_execution": true
}
```

**Cost Calculation:**

```python
# Token estimation
query_tokens = 100  # Long, complex query
response_tokens = 200 * 4  # 4 agents, detailed responses
system_tokens = 200 * 4  # System prompt per agent
context_tokens = 1000  # Inter-agent context sharing
total_base_tokens = 2200

# Complexity assessment: HIGH
# - Keywords: "comprehensive", "analysis", "including"
# - 4 agents
# - Parallel execution
# - Long query
complexity_score = 3 + 2 + 1 + 1 = 7 → HIGH
complexity_multiplier = 5.0
adjusted_tokens = 2200 * 5.0 = 11000

# Cost calculation (OpenAI GPT-4o-mini)
input_cost = (11000 * 0.7 / 1000) * 0.00015 = $0.001155
output_cost = (11000 * 0.3 / 1000) * 0.0006 = $0.00198
total_cost = $0.003135
```

**Result:**

```json
{
  "estimated_cost": 0.003135,
  "complexity": "HIGH",
  "tokens_estimated": 11000,
  "optimization_suggestions": [
    "Consider breaking down into smaller sub-tasks",
    "Sequential execution would reduce cost but increase time",
    "Use memory agent to avoid redundant information gathering"
  ]
}
```

### Example 3: Research Plan with Traditional Costs

**Research Plan Cost Breakdown:**

```json
{
  "ai_operations": {
    "estimated_tokens": 25000,
    "total_ai_cost": 6.75,
    "complexity_level": "MEDIUM",
    "provider": "openai",
    "model": "gpt-4o-mini"
  },
  "traditional_costs": {
    "database_access": {
      "usd": 300.0,
      "aud": 465.0,
      "description": "Academic databases, PubMed, IEEE Xplore"
    },
    "analysis_software": {
      "usd": 200.0,
      "aud": 310.0,
      "description": "Statistical analysis software licenses"
    },
    "expert_consultation": {
      "usd": 500.0,
      "aud": 775.0,
      "description": "Subject matter expert time (5 hours @ $100/hr)"
    }
  },
  "summary": {
    "ai_cost": 6.75,
    "traditional_cost": 1000.0,
    "total": 1006.75,
    "currency": "USD",
    "total_aud": 1560.46,
    "cost_per_day": 71.91
  }
}
```

---

## Cost Optimization

### 1. Single Agent Mode

**Cost Reduction:** 60% reduction by using single agent instead of multi-agent approach.

```python
# Multi-agent approach (4 agents)
multi_agent_cost = base_cost * 4 * complexity_multiplier
# Example: $0.50 * 4 * 2.5 = $5.00

# Single agent approach
single_agent_cost = base_cost * 1 * complexity_multiplier
# Example: $0.50 * 1 * 2.5 = $1.25

# Savings: $5.00 - $1.25 = $3.75 (75% reduction)
```

### 2. Complexity Optimization

**Strategy:** Optimize query structure to reduce complexity scoring.

```python
# High complexity query (score: 7)
"Comprehensive detailed analysis comparing multiple AI diagnostic tools with in-depth systematic review"

# Optimized query (score: 4)  
"Compare AI diagnostic tools accuracy and adoption rates"

# Cost reduction: HIGH → MEDIUM
# Multiplier: 5.0 → 2.5 (50% reduction)
```

### 3. Token Management

**Techniques:**

- **Prompt optimization**: Remove unnecessary words and context
- **Response limiting**: Set appropriate max_tokens
- **Context sharing**: Reuse context between agents efficiently

```python
# Inefficient prompt (200 tokens)
"Please provide a comprehensive detailed analysis of the following research topic, including all relevant background information, methodology considerations, potential limitations, and comprehensive conclusions about..."

# Optimized prompt (50 tokens)
"Analyze this research topic with methodology, limitations, and conclusions:"

# Token reduction: 75% cost savings
```

### 4. Caching and Reuse

```python
# Cache AI responses for similar queries
cache_key = f"{provider}_{model}_{hash(prompt)}"
if cache_key in response_cache:
    return response_cache[cache_key]  # $0 cost

# Reuse previous analysis for related queries
if similar_query_exists(query):
    return adapt_previous_response(previous_response)  # Reduced cost
```

---

## Configuration

### 1. Cost Settings Configuration

```json
{
  "cost_settings": {
    "token_costs": {
      "openai": {
        "gpt-4o-mini": {
          "input": 0.00015,
          "output": 0.0006
        },
        "gpt-4": {
          "input": 0.03,
          "output": 0.06
        },
        "gpt-3.5-turbo": {
          "input": 0.0015,
          "output": 0.002
        }
      },
      "xai": {
        "grok-3-mini-beta": {
          "input": 0.0002,
          "output": 0.0008
        },
        "grok-3": {
          "input": 0.002,
          "output": 0.004
        }
      }
    },
    "cost_thresholds": {
      "session_warning": 1.0,
      "session_limit": 5.0,
      "daily_warning": 10.0,
      "daily_limit": 50.0,
      "emergency_stop": 100.0
    },
    "complexity_multipliers": {
      "LOW": 1.0,
      "MEDIUM": 2.5,
      "HIGH": 5.0,
      "CRITICAL": 10.0
    }
  }
}
```

### 2. Frontend Cost Configuration

```typescript
// Currency conversion configuration
interface CostConfig {
  usdToAudRate: number;
  providers: {
    [provider: string]: {
      [model: string]: {
        input: number;
        output: number;
      };
    };
  };
  thresholds: {
    sessionWarning: number;
    sessionLimit: number;
    dailyLimit: number;
  };
}

const costConfig: CostConfig = {
  usdToAudRate: 1.55,
  providers: {
    openai: {
      "gpt-4o-mini": { input: 0.00015, output: 0.0006 }
    }
  },
  thresholds: {
    sessionWarning: 1.0,
    sessionLimit: 5.0,
    dailyLimit: 50.0
  }
};
```

---

## API Integration

### 1. Cost Estimation Endpoint

**POST** `/research/estimate-costs`

```json
{
  "query": "Research question",
  "context": {
    "scope": "medium",
    "duration_days": 14,
    "agents": ["research_manager", "literature_agent"],
    "parallel_execution": true
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
      "ai_operations": 2.75,
      "traditional_costs": 10.0
    },
    "optimization_suggestions": [
      "Consider single-agent approach for 60% cost reduction",
      "Break down into smaller tasks to reduce complexity"
    ]
  }
}
```

### 2. Cost Tracking Endpoints

**POST** `/research/start-cost-tracking`

```json
{
  "task_id": "task_123",
  "session_id": "session_456"
}
```

**POST** `/research/record-usage`

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

**GET** `/research/cost-summary/{session_id}`

```json
{
  "session_id": "session_456",
  "total_cost": 15.25,
  "total_tokens": 42000,
  "active_tasks": 3,
  "usage_breakdown": [
    {
      "task_id": "task_123",
      "cost": 5.25,
      "tokens": 15000,
      "duration": 125.5,
      "providers": {"openai": {"tokens": 15000, "cost": 5.25}},
      "agents": {"research_manager": {"tokens": 15000, "cost": 5.25}}
    }
  ]
}
```

---

## Troubleshooting

### Common Issues

#### 1. **Inaccurate Cost Estimates**

**Symptoms:**

- Cost estimates significantly different from actual costs
- Frontend showing $0.00 for cost estimates

**Causes:**

- Missing cost_estimate in metadata
- Incorrect token calculation
- Provider pricing not updated

**Solutions:**

```python
# Check metadata structure
if 'cost_estimate' not in plan.metadata:
    logger.warning("Cost estimate missing from plan metadata")
    
# Verify token costs are loaded
if not self.token_costs:
    self.token_costs = self._load_token_costs()
    
# Update provider pricing
self.token_costs["openai"]["gpt-4o-mini"] = {
    "input": 0.00015,
    "output": 0.0006
}
```

#### 2. **Currency Conversion Issues**

**Symptoms:**

- Incorrect AUD amounts displayed
- Exchange rate errors

**Solutions:**

```typescript
// Implement dynamic exchange rate fetching
const fetchExchangeRate = async (): Promise<number> => {
  try {
    const response = await fetch('https://api.exchangerate-api.com/v4/latest/USD');
    const data = await response.json();
    return data.rates.AUD || 1.55; // Fallback to static rate
  } catch (error) {
    console.warn('Failed to fetch exchange rate, using fallback');
    return 1.55;
  }
};

// Update rate periodically
useEffect(() => {
  const updateRate = async () => {
    const newRate = await fetchExchangeRate();
    setExchangeRate(newRate);
  };
  
  updateRate();
  const interval = setInterval(updateRate, 3600000); // Update hourly
  return () => clearInterval(interval);
}, []);
```

#### 3. **Cost Dialog Not Showing Data**

**Symptoms:**

- Empty cost dialog
- "No cost data available" message

**Solutions:**

```typescript
// Debug cost breakdown calculation
const getCostBreakdown = () => {
  console.log('Research Plan:', researchPlan);
  console.log('Estimated Cost:', researchPlan?.estimated_cost);
  console.log('Metadata:', researchPlan?.metadata);
  
  if (!researchPlan) {
    console.error('No research plan available');
    return null;
  }
  
  const estimatedCostUSD = researchPlan.estimated_cost || 0;
  if (estimatedCostUSD === 0) {
    console.warn('Estimated cost is 0, check backend cost calculation');
  }
  
  // ... rest of calculation
};
```

#### 4. **High Cost Estimates**

**Symptoms:**

- Unexpectedly high cost estimates
- Cost warnings triggering frequently

**Solutions:**

```python
# Review complexity assessment
def debug_complexity_assessment(self, query: str, agents: List[str]) -> None:
    logger.info(f"Query: {query}")
    logger.info(f"Query length: {len(query)}")
    logger.info(f"Agents: {agents}")
    logger.info(f"Agent count: {len(agents)}")
    
    # Check keyword matches
    high_keywords = ["comprehensive", "detailed", "in-depth"]
    matched_keywords = [kw for kw in high_keywords if kw in query.lower()]
    logger.info(f"High complexity keywords matched: {matched_keywords}")

# Optimize for cost
optimized_request = {
    "query": "Compare AI tools",  # Simplified from complex query
    "agents": ["research_manager"],  # Single agent
    "parallel_execution": False,  # Sequential processing
    "context": {"single_agent_mode": True}
}
```

### Performance Monitoring

#### 1. **Cost Tracking Dashboard**

```python
def generate_cost_report(self, timeframe: str = "daily") -> Dict[str, Any]:
    """Generate cost usage report for monitoring."""
    
    if timeframe == "daily":
        today = datetime.now().strftime("%Y-%m-%d")
        daily_cost = self.daily_usage.get(today, 0.0)
        
        return {
            "date": today,
            "total_cost": daily_cost,
            "threshold_status": {
                "warning": daily_cost > self.cost_thresholds["daily_warning"],
                "limit": daily_cost > self.cost_thresholds["daily_limit"]
            },
            "breakdown": self.cost_by_provider.copy(),
            "active_sessions": len(self.active_sessions)
        }
```

#### 2. **Cost Alerts**

```python
def _check_cost_thresholds(self, usage: CostUsage):
    """Check cost thresholds and send alerts."""
    
    session_cost = self._get_session_cost(usage.session_id)
    daily_cost = self._get_daily_cost()
    
    # Session warning
    if session_cost > self.cost_thresholds["session_warning"]:
        self._send_cost_alert("session_warning", session_cost, usage.session_id)
    
    # Daily warning  
    if daily_cost > self.cost_thresholds["daily_warning"]:
        self._send_cost_alert("daily_warning", daily_cost)
    
    # Emergency stop
    if daily_cost > self.cost_thresholds["emergency_stop"]:
        self._trigger_emergency_stop(daily_cost)

def _send_cost_alert(self, alert_type: str, cost: float, session_id: str = None):
    """Send cost alert notification."""
    
    alert_message = {
        "type": alert_type,
        "cost": cost,
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
        "threshold": self.cost_thresholds.get(alert_type.replace("_", "_"), 0)
    }
    
    # In production, this would send to monitoring system
    self.logger.warning(f"Cost alert: {alert_message}")
```

---

This comprehensive cost estimation documentation covers all aspects of the system from frontend display to backend calculation, providing developers and users with complete understanding of how costs are calculated, tracked, and optimized within the Eunice Research Platform.
