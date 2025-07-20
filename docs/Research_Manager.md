# Research Manager Documentation

_Last Updated: July 21, 2025_

## Overview

The **Research Manager** (`src/core/research_manager.py`) is the central orchestrator for multi-agent research tasks in the Eunice AI collaboration platform. It coordinates between different AI agents (Retriever, Reasoner, Executor, Memory) to perform complex research tasks using a structured workflow with advanced cost control and real-time monitoring.

> **📘 Related Documentation**: For detailed information about the cost estimation system, see [Cost Estimation System Documentation](Cost_Estimation_System.md).

## Architecture

### Core Components

#### 1. Research Stages Pipeline

The research process follows a structured pipeline defined by `ResearchStage` enum:

```python
class ResearchStage(Enum):
    PLANNING = "planning"        # Research plan generation
    RETRIEVAL = "retrieval"      # Information gathering
    REASONING = "reasoning"      # Analysis and reasoning
    EXECUTION = "execution"      # Task execution
    SYNTHESIS = "synthesis"      # Results combination
    COMPLETE = "complete"        # Successful completion
    FAILED = "failed"           # Task failure
```

#### 2. Research Context

Each research task is tracked using a `ResearchContext` dataclass that maintains:

- **Task Metadata**: ID, query, user, conversation references
- **Stage Progression**: Current stage, completed/failed stages, retry logic
- **Research Data**: Search results, reasoning output, execution results, synthesis
- **Cost Tracking**: Estimated vs actual costs, approval status
- **Context Management**: Data persistence and metadata

#### 3. Agent Communication

Communication with AI agents occurs via the **MCP (Message Control Protocol)**:

- **ResearchAction**: Structured messages sent to agents
- **AgentResponse**: Responses received from agents
- **MCPClient**: WebSocket-based communication layer
- **Task Routing**: Intelligent agent selection and load balancing

## Core Workflow

### 1. Task Initiation

```python
async def start_research_task(
    query: str,
    user_id: str,
    conversation_id: str,
    options: Optional[Dict[str, Any]] = None
) -> tuple[str, Dict[str, Any]]
```

**Process:**

1. **Cost Estimation**: Uses centralized `_estimate_task_cost()` method to predict resource usage
2. **Approval Logic**: Applies cost thresholds and user approval workflows
3. **Context Creation**: Initializes `ResearchContext` with task metadata and cost information
4. **Orchestration Start**: Begins asynchronous task execution

**Cost Control Features:**

- **Centralized Cost Estimation**: New `_estimate_task_cost()` method consolidates all cost logic
- Pre-task cost estimation with confidence scoring and complexity assessment
- Automatic approval for low-cost tasks based on configurable thresholds
- User approval workflow for high-cost operations with detailed cost breakdown
- Single-agent mode for cost optimization (60% cost reduction)
- Real-time cost tracking during execution with provider and agent breakdowns
- **Cost Recommendations**: Intelligent suggestions for cost optimization including alternative execution modes

### 2. Task Orchestration

The `_orchestrate_research_task` method executes research stages:

#### Full Multi-Agent Mode (Comprehensive Research)

1. **Planning Stage** (`_execute_planning_stage`)

   - Analyzes query and creates research plan
   - Uses Reasoner agent for strategic planning
   - Establishes research objectives and approach

2. **Retrieval Stage** (`_execute_retrieval_stage`)

   - Executes information gathering
   - Uses Retriever agent for web search and data collection
   - Configurable search depth and result limits

3. **Reasoning Stage** (`_execute_reasoning_stage`)

   - Analyzes gathered information
   - Uses Reasoner agent for comprehensive analysis
   - Generates insights and connections

4. **Execution Stage** (`_execute_execution_stage`)

   - Performs specific research tasks
   - Uses Executor agent for complex operations
   - Handles dynamic task execution

5. **Synthesis Stage** (`_execute_synthesis_stage`)
   - Combines all research outputs
   - Uses Reasoner agent for final synthesis
   - Generates comprehensive research summary

#### Single-Agent Mode (Cost-Optimized)

- **Planning + Retrieval Only**: Uses only Retriever agent
- **Reduced Complexity**: Optimized for cost-sensitive operations
- **Faster Execution**: Streamlined workflow for simple queries

### 3. Agent Communication Protocol

#### Message Flow

```python
# Send action to agent
action = ResearchAction(
    task_id=context.task_id,
    context_id=context.conversation_id,
    agent_type="retriever",
    action="search_information",
    payload={...}
)

response = await self._send_to_agent("retriever", action)
```

#### Response Handling

- **Async Response Tracking**: Uses `Future` objects for response management
- **Timeout Handling**: 60-second default timeout per agent call
- **Error Recovery**: Automatic retry logic with exponential backoff
- **Status Updates**: Real-time progress notifications

## Key Features

### 1. Advanced Cost Control

The Research Manager implements sophisticated cost management through a centralized cost estimation system:

#### Centralized Cost Estimation

```python
async def _estimate_task_cost(
    self,
    query: str,
    conversation_id: str,
    options: Optional[Dict[str, Any]] = None
) -> tuple[Dict[str, Any], bool, bool]:
    """
    Centralized cost estimation with approval logic.
    Returns: (cost_info, should_proceed, single_agent_mode)
    """
```

**Key Features:**

- **Unified Cost Logic**: All cost estimation consolidated in a single method
- **Agent Configuration**: Automatic selection between single and multi-agent modes
- **Complexity Assessment**: Advanced task complexity scoring using multiple factors
- **Cost Tier Classification**: LOW, MEDIUM, HIGH, and CRITICAL tiers with different multipliers

#### Pre-Task Cost Estimation

- **Token Prediction**: Estimates API usage based on query complexity, agent count, and execution mode
- **Multi-Agent Costs**: Calculates costs for all participating agents with complexity multipliers
- **Confidence Scoring**: Provides reliability metrics for estimates (0.6-0.8 confidence range)
- **Provider Breakdown**: Costs per AI provider (OpenAI, XAI, etc.) with model-specific pricing
- **Cost Reasoning**: Human-readable explanations for cost estimates

#### Real-Time Cost Tracking

```python
# Enhanced cost tracking with detailed breakdowns
self.cost_estimator.start_cost_tracking(task_id, conversation_id)

# Record usage per agent and provider
self.cost_estimator.record_usage(
    task_id=task_id,
    provider="openai",
    model="gpt-4o-mini",
    input_tokens=request_tokens,
    output_tokens=response_tokens,
    agent_type="retriever"
)

# Get final usage with breakdowns
final_usage = self.cost_estimator.end_cost_tracking(task_id)
```

**Enhanced Tracking Features:**

- **Provider-Specific Tracking**: Separate cost tracking for each AI provider
- **Agent-Level Breakdown**: Cost attribution per agent type (retriever, reasoner, executor, memory)
- **Token Distribution**: Separate tracking of input vs output tokens
- **Session Aggregation**: Cumulative costs across related tasks in a conversation
- **Daily Usage Monitoring**: Automatic daily cost accumulation and threshold checking

#### Cost Thresholds and Controls

- **Multi-Level Thresholds**: Session warnings ($1), session limits ($5), daily warnings ($10), daily limits ($50), emergency stops ($100)
- **Automatic Approval**: Low-cost tasks proceed without user intervention based on configurable thresholds
- **Progressive Warnings**: Escalating alerts as costs approach various threshold levels
- **User Approval**: High-cost tasks require explicit user consent with detailed cost breakdown
- **Cost Override**: Manual cost approval for important tasks using `cost_override=True` parameter
- **Budget Limits**: Session and conversation-level spending limits with real-time enforcement
- **Emergency Controls**: Automatic task blocking when costs exceed critical thresholds

### 2. Progress Tracking and Monitoring

#### Real-Time Updates

```python
# Progress calculation
progress = len(context.completed_stages) / total_stages * 100

# WebSocket notifications
await self._notify_progress(context)
```

#### Callback System

- **Progress Callbacks**: Real-time stage completion updates
- **Completion Callbacks**: Final results and status notifications
- **Task-Specific Callbacks**: Custom handlers per research task
- **Error Callbacks**: Failure notifications and recovery suggestions

### 3. Error Handling and Resilience

#### Retry Logic

- **Stage-Level Retries**: Automatic retry for failed stages (default: 3 attempts)
- **Exponential Backoff**: Increasing delays between retry attempts
- **Partial Success**: Continues with completed stages after failures
- **Graceful Degradation**: Provides best-effort results when possible

#### Error Recovery

```python
# Retry failed stages
if context.retry_count < context.max_retries:
    context.retry_count += 1
    success = await executor(context)
```

### 4. Web API Integration

The Research Manager integrates with the FastAPI web server through dedicated endpoints:

#### Research Task Endpoints

- `POST /api/research/start` - Start new research task
- `GET /api/research/task/{task_id}` - Get task status and results
- `DELETE /api/research/task/{task_id}` - Cancel active task

#### WebSocket Streaming

- `/api/research/stream/{task_id}` - Real-time progress updates
- Task completion notifications
- Error and status change notifications

#### Example API Usage

```python
# Start research task
response = await start_research_task(ResearchRequest(
    conversation_id="conv_123",
    query="Analyze market trends in AI",
    research_mode="comprehensive",
    max_results=10
))

# Returns: ResearchTaskResponse with task_id and status
```

### 5. Agent System Integration

#### Supported Agent Types

- **RetrieverAgent** (`src/agents/retriever_agent.py`)

  - Web search and information gathering
  - Document retrieval and processing
  - Source validation and ranking

- **ReasonerAgent** (`src/agents/reasoner_agent.py`)

  - Strategic planning and analysis
  - Information synthesis and reasoning
  - Insight generation and connection

- **ExecutorAgent** (`src/agents/executor_agent.py`)

  - Complex task execution
  - Dynamic action processing
  - Result validation and formatting

- **MemoryAgent** (`src/agents/memory_agent.py`)
  - Context management and persistence
  - Knowledge base integration
  - Conversation history tracking

#### Agent Communication

All agents implement the `BaseAgent` interface and communicate via:

- **ResearchAction**: Structured task messages
- **AgentResponse**: Standardized response format
- **MCP Protocol**: WebSocket-based message routing
- **Status Updates**: Real-time progress reporting

## Configuration

### Research Manager Settings

```python
# Configuration via ConfigManager
research_config = {
    'max_concurrent_tasks': 5,
    'task_timeout': 600,  # 10 minutes
    'response_timeout': 60,  # 1 minute per agent
    'max_retries': 3,
    'cost_thresholds': {
        'low_cost': 0.10,
        'medium_cost': 1.00,
        'high_cost': 5.00
    }
}
```

### MCP Client Configuration

```python
mcp_config = {
    'host': '127.0.0.1',
    'port': 9000,
    'connection_timeout': 30,
    'message_timeout': 60
}
```

## Usage Examples

### Basic Research Task

```python
# Initialize Research Manager
research_manager = ResearchManager(config_manager)
await research_manager.initialize()

# Start research task
task_id, cost_info = await research_manager.start_research_task(
    query="What are the latest developments in quantum computing?",
    user_id="user_123",
    conversation_id="conv_456",
    options={
        'research_mode': 'comprehensive',
        'max_results': 15,
        'single_agent_mode': False
    }
)

# Monitor progress
status = research_manager.get_task_status(task_id)
print(f"Progress: {research_manager.calculate_task_progress(task_id)}%")
```

### Cost-Optimized Research

```python
# Single-agent mode for cost savings
task_id, cost_info = await research_manager.start_research_task(
    query="Simple web search for Python tutorials",
    user_id="user_123",
    conversation_id="conv_456",
    options={
        'single_agent_mode': True,  # Use only retriever
        'max_results': 5
    }
)
```

### Real-Time Progress Monitoring

```python
# Register progress callback
async def progress_handler(progress_data):
    print(f"Task {progress_data['task_id']}: {progress_data['progress']}%")
    print(f"Current stage: {progress_data['stage']}")

research_manager.register_progress_callback(progress_handler)

# Register completion callback
async def completion_handler(completion_data):
    if completion_data['success']:
        print("Research completed successfully!")
        print(f"Results: {completion_data['results']}")
    else:
        print("Research failed!")

research_manager.register_completion_callback(completion_handler)
```

## Cost Management

> **📘 Detailed Cost Documentation**: For comprehensive information about cost estimation algorithms, thresholds, and optimization strategies, see [Cost Estimation System Documentation](Cost_Estimation_System.md).

### Cost Estimation API

The Research Manager now uses a centralized cost estimation approach through the `_estimate_task_cost()` method:

```python
# Centralized cost estimation with enhanced features
cost_info, should_proceed, single_agent_mode = await research_manager._estimate_task_cost(
    query="Analyze market trends in quantum computing",
    conversation_id="conv_123",
    options={'single_agent_mode': False}
)

print(f"Cost estimate: ${cost_info['estimate']['cost_usd']:.4f}")
print(f"Complexity: {cost_info['estimate']['complexity']}")
print(f"Agent count: {cost_info['estimate']['agent_count']}")
print(f"Confidence: {cost_info['estimate']['confidence']}")
print(f"Should proceed: {should_proceed}")
```

### Enhanced Cost Estimation

```python
# Both async and sync versions available
# Async version (uses centralized estimation)
estimate = await research_manager.estimate_query_cost_async(
    query="Complex market analysis",
    single_agent_mode=False
)

# Sync version (backwards compatibility)
estimate = research_manager.estimate_query_cost(
    query="Complex market analysis",
    single_agent_mode=False
)

print(f"Estimated cost: ${estimate['estimate']['cost_usd']:.4f}")
print(f"Complexity: {estimate['estimate']['complexity']}")
print(f"Reasoning: {estimate['estimate']['reasoning']}")
print(f"Recommendations: {estimate['recommendations']}")
```

### Enhanced Cost Tracking

```python
# Get detailed real-time cost status
cost_status = research_manager.get_task_cost_status(task_id)
print(f"Estimated: ${cost_status['estimated_cost']:.4f}")
print(f"Actual: ${cost_status['actual_cost']:.4f}")
print(f"Cost approved: {cost_status['cost_approved']}")
print(f"Single agent mode: {cost_status['single_agent_mode']}")

# Current usage breakdown
if cost_status['current_usage']:
    usage = cost_status['current_usage']
    print(f"Tokens used: {usage['tokens_used']:,}")
    print(f"Duration: {usage['duration_seconds']:.1f}s")
    print(f"Provider breakdown: {usage['provider_breakdown']}")
    print(f"Agent breakdown: {usage['agent_breakdown']}")
```

### Advanced Cost Analytics

```python
# Session-level cost summary
session_summary = research_manager.get_cost_summary(session_id="conv_123")
print(f"Session total: ${session_summary['total_cost']:.4f}")
print(f"Active tasks: {session_summary['active_tasks']}")

# System-wide cost summary
system_summary = research_manager.get_cost_summary()
print(f"Daily usage: {system_summary['daily_usage']}")
print(f"Current thresholds: {system_summary['thresholds']}")
```

### Advanced Budget Management

```python
# Get current cost thresholds
current_thresholds = research_manager.get_cost_thresholds()
print(f"Current thresholds: {current_thresholds}")

# Update cost thresholds with new values
research_manager.update_cost_thresholds({
    'session_warning': 0.50,   # Lower warning threshold
    'session_limit': 2.00,     # Stricter session limit
    'daily_warning': 5.00,     # Reduced daily warning
    'daily_limit': 25.00,      # Lower daily limit
    'emergency_stop': 50.00    # Adjusted emergency threshold
})

# Cost threshold enforcement examples
estimate = research_manager.estimate_query_cost("Complex research task")
if estimate['estimate']['cost_usd'] > current_thresholds['session_warning']:
    print("⚠️  Task cost exceeds session warning threshold")

# Pre-task cost approval workflow
task_id, cost_info = await research_manager.start_research_task(
    query="Expensive comprehensive analysis",
    user_id="user_123",
    conversation_id="conv_456",
    options={'cost_override': True}  # Manual approval for high-cost tasks
)

print(f"Task started: {cost_info['task_started']}")
print(f"Cost reason: {cost_info.get('cost_reason', 'Approved')}")
```

### Cost Optimization Recommendations

The Research Manager provides intelligent cost optimization suggestions:

```python
# Get cost recommendations for a query
estimate = await research_manager.estimate_query_cost_async(
    query="Comprehensive market analysis with competitor research",
    single_agent_mode=False
)

recommendations = estimate['recommendations']
print(f"Current tier: {recommendations['current_tier']}")
print(f"Suggestions: {recommendations['suggestions']}")

# Example recommendations output:
# Current tier: high
# Suggestions: [
#   "Consider breaking down into smaller sub-tasks",
#   "Evaluate if all agents are necessary - consider single-agent approach",
#   "Sequential execution would reduce cost but increase time"
# ]

# Cost-saving alternatives
alternatives = recommendations['alternatives']
if 'single_agent' in alternatives:
    alt = alternatives['single_agent']
    print(f"Single-agent cost: ${alt['estimated_cost']:.4f}")
    print(f"Trade-offs: {alt['trade_offs']}")

if 'sequential' in alternatives:
    alt = alternatives['sequential']
    print(f"Sequential cost: ${alt['estimated_cost']:.4f}")
    print(f"Trade-offs: {alt['trade_offs']}")
```

**Common Optimization Strategies:**

1. **Single-Agent Mode** (~60% cost reduction)

   - Use `single_agent_mode=True` for simple queries
   - Best for: Basic information gathering, simple analysis

2. **Sequential Execution** (~30% cost reduction)

   - Agents run one after another instead of in parallel
   - Best for: Non-time-critical tasks, budget-constrained scenarios

3. **Task Decomposition** (20-40% cost reduction)

   - Break complex queries into smaller sub-tasks
   - Best for: Multi-part research, complex analysis projects

4. **Memory Agent Utilization**
   - Leverage conversation context to avoid redundant searches
   - Best for: Follow-up questions, iterative research

## Performance Monitoring

### Task Performance

```python
# Performance tracking built-in
self.performance_monitor.start_timer(f"research_task_{task_id}")
# ... task execution ...
self.performance_monitor.end_timer(f"research_task_{task_id}")
```

### Active Task Management

```python
# Get all active tasks
active_tasks = research_manager.get_active_tasks()
for task in active_tasks:
    print(f"Task {task['task_id']}: {task['stage']} ({task['progress']}%)")

# Cancel specific task
success = await research_manager.cancel_task(task_id)
```

## Error Handling

### Common Error Scenarios

1. **MCP Connection Failures**: Automatic reconnection with exponential backoff
2. **Agent Timeouts**: Retry logic with configurable timeout values
3. **Cost Limit Exceeded**: Graceful task termination with partial results
4. **Invalid Queries**: Pre-validation and user feedback
5. **Resource Exhaustion**: Queue management and task prioritization

### Error Recovery Strategies

```python
try:
    task_id, cost_info = await research_manager.start_research_task(...)
except Exception as e:
    # Comprehensive error handling
    error_info = research_manager.error_handler.handle_error(e, "start_research_task")
    print(f"Error: {error_info['user_message']}")
```

## Integration Points

### Web Server Integration

- **FastAPI Endpoints**: RESTful API for research task management
- **WebSocket Streaming**: Real-time updates and progress monitoring
- **Authentication**: User context and permission handling
- **Rate Limiting**: Request throttling and abuse prevention

### Database Integration

- **Context Persistence**: Long-term storage of research contexts
- **Cost Tracking**: Historical usage and billing data
- **Result Caching**: Performance optimization for repeated queries
- **Audit Logging**: Comprehensive activity tracking

### AI Provider Integration

- **Multi-Provider Support**: OpenAI, XAI, and other AI services with provider-specific pricing models
- **Load Balancing**: Intelligent provider selection based on cost and performance
- **Fallback Strategies**: Provider failure handling with cost-aware backup providers
- **Advanced Cost Management**: Real-time cost tracking per provider with detailed breakdowns

### Cost Estimation System Integration

- **Centralized Cost Logic**: Integration with the comprehensive [Cost Estimation System](Cost_Estimation_System.md)
- **Real-time Usage Tracking**: Provider and agent-level cost attribution
- **Threshold Management**: Multi-level cost controls with automatic enforcement
- **Cost Optimization**: Intelligent recommendations and alternative execution modes

## Debugging and Monitoring

### Debug UI Support

```python
# Get latest AI plan for debugging
plan = await research_manager.get_latest_plan(context_id)

# List all plans with filtering
plans = await research_manager.list_plans(context_id="conv_123", limit=20)

# Modify plan for testing
success = await research_manager.modify_plan(plan_id, modifications)
```

### Logging and Tracing

- **Structured Logging**: JSON-formatted logs for analysis
- **Performance Metrics**: Detailed timing and resource usage
- **Error Tracking**: Comprehensive error reporting and analysis
- **Audit Trails**: Complete task execution history

## Best Practices

### Optimal Usage Patterns

1. **Query Optimization**: Structure queries for better AI understanding
2. **Cost Management**: Use single-agent mode for simple tasks
3. **Progress Monitoring**: Implement real-time UI updates
4. **Error Handling**: Provide graceful degradation and user feedback
5. **Resource Management**: Monitor concurrent task limits

### Performance Optimization

1. **Caching**: Implement result caching for repeated queries
2. **Batching**: Group related tasks for efficiency
3. **Load Balancing**: Distribute tasks across available agents
4. **Connection Pooling**: Reuse MCP connections when possible
5. **Memory Management**: Clean up completed task contexts

### Security Considerations

1. **Input Validation**: Sanitize all user inputs
2. **Cost Controls**: Prevent resource exhaustion attacks
3. **Authentication**: Verify user permissions for research tasks
4. **Data Privacy**: Handle sensitive information appropriately
5. **Audit Logging**: Track all research activities

## Future Enhancements

### Recent Architectural Improvements

#### Cost Estimation Refactoring (v1.1)

The Research Manager has been enhanced with a centralized cost estimation architecture:

**Key Improvements:**

- **Centralized Logic**: All cost estimation consolidated into `_estimate_task_cost()` method
- **Code Reusability**: Eliminates duplication between different cost estimation scenarios
- **Enhanced API**: New async `estimate_query_cost_async()` method alongside existing sync version
- **Better Integration**: Seamless integration with the comprehensive Cost Estimation System

**Method Overview:**

```python
# New centralized cost estimation method
async def _estimate_task_cost(
    query: str,
    conversation_id: str,
    options: Optional[Dict[str, Any]] = None
) -> tuple[Dict[str, Any], bool, bool]

# Enhanced async estimation API
async def estimate_query_cost_async(
    query: str,
    single_agent_mode: bool = False
) -> Dict[str, Any]

# Backwards-compatible sync version
def estimate_query_cost(
    query: str,
    single_agent_mode: bool = False
) -> Dict[str, Any]
```

**Benefits:**

- **Maintainability**: Single source of truth for cost logic
- **Consistency**: Uniform cost estimation across all operations
- **Flexibility**: Easy to extend with new cost factors and optimizations
- **Testing**: Simplified testing and debugging of cost-related functionality

### Planned Features

1. **Advanced Cost Prediction**: Machine learning-based cost estimation using historical data
2. **Smart Agent Selection**: AI-powered agent routing optimization based on cost-performance analysis
3. **Result Caching**: Intelligent caching of research outputs to reduce redundant costs
4. **Batch Processing**: Support for multiple concurrent research tasks with cost pooling
5. **Enhanced Monitoring**: Real-time performance dashboards with cost analytics

### Integration Roadmap

1. **Additional AI Providers**: Support for more AI services
2. **External Data Sources**: Integration with research databases
3. **Collaboration Features**: Multi-user research coordination
4. **Mobile Support**: Mobile-optimized research interfaces
5. **API Enhancements**: GraphQL and advanced querying support

---

_For technical support or questions about the Research Manager, please refer to the source code documentation or contact the development team._
