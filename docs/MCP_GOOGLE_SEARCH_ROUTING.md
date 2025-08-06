# MCP Server Google Search Routing - Complete Implementation

## Overview

The MCP (Model Context Protocol) server has been successfully updated to handle Google search routing from the AI service to the network agent. This enables AI models to perform real-time web searches during conversations.

## Message Flow Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   AI Service    │────│   MCP Server     │────│ Network Agent   │
│   (Port 8000)   │    │   (Port 9000)    │    │ (Port 8004)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
        │                        │                        │
        │ 1. task_request        │                        │
        │   agent_type=network   │                        │
        │   action=google_search │                        │
        │━━━━━━━━━━━━━━━━━━━━━━━━▶│                        │
        │                        │ 2. Route to agent     │
        │                        │   with capability     │
        │                        │━━━━━━━━━━━━━━━━━━━━━━━━▶│
        │                        │                        │ 3. Execute
        │                        │                        │    Google
        │                        │                        │    Search
        │                        │◀━━━━━━━━━━━━━━━━━━━━━━━━│
        │                        │ 4. task_result        │
        │◀━━━━━━━━━━━━━━━━━━━━━━━━│                        │
        │ 5. Return to OpenAI    │                        │
        │    function call       │                        │
```

## Key Components Updated

### 1. MCP Server (`services/mcp-server/mcp_server.py`)

**New Handler Added:**

```python
async def _handle_task_request_from_ai(self, client_id: str, data: Dict[str, Any]):
    """Handle task request from AI service"""
    # Extracts agent_type and action from request
    # Routes to appropriate agent based on capabilities
    # Stores task for result tracking
```

**Message Types Handled:**

- `"research_action"` - Original gateway requests
- `"task_request"` - **NEW** - AI service requests
- `"task_result"` - Agent responses
- `"agent_register"` - Agent registration
- `"heartbeat"` - Keep-alive messages

### 2. Network Agent (`agents/network/src/network_mcp_agent.py`)

**Registration Format:**

```python
registration_message = {
    "type": "agent_register",
    "agent_id": self.agent_id,
    "agent_type": "network", 
    "capabilities": ["google_search", "web_search", "multi_page_search"],
    "timestamp": datetime.now(timezone.utc).isoformat()
}
```

**Task Handling:**

```python
async def _handle_message(self, data: Dict[str, Any]):
    message_type = data.get("type")
    
    if message_type == "task_request":
        await self._handle_task_request(data)
    # Handles google_search, web_search, multi_page_search
```

### 3. AI Service (`services/ai-service/src/mcp_ai_service.py`)

**Google Search Tool Call:**

```python
async def _execute_google_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
    search_request = {
        "type": "task_request",
        "data": {
            "agent_type": "network",
            "action": "google_search", 
            "payload": {"query": query, "num_results": num_results}
        }
    }
    # Sends via MCP and waits for response
```

## Routing Logic

The MCP server routes messages based on:

1. **Agent Type**: `"network"` for web search requests
2. **Action/Capability**: `"google_search"` capability matching
3. **Agent Status**: Only routes to `"active"` agents
4. **Capability Matching**: Ensures agent has required capability

## Capabilities Configuration

**Network Agent Capabilities** (`agents/network/config/config.json`):

```json
"capabilities": [
    "google_search",
    "web_search", 
    "multi_page_search",
    "search_capabilities",
    "google_custom_search",
    "search_result_parsing"
]
```

## Error Handling

- **No Agent Available**: Returns error if no network agent with google_search capability
- **Task Timeout**: 30-second timeout for search requests
- **API Failures**: Proper error propagation from Google Search API
- **Connection Issues**: Automatic reconnection with exponential backoff

## Testing Validation

✅ **Message Flow Tests Passed:**

- AI Service sends `task_request` ✓
- MCP Server handles `task_request` ✓  
- Network Agent handles `task_request` ✓
- Complete bidirectional flow ✓

✅ **Capability Matching:**

- Network agent registers with `google_search` capability ✓
- MCP server routes based on capabilities ✓
- AI service targets `agent_type: "network"` ✓

✅ **Protocol Compliance:**

- Standard MCP message format ✓
- Proper agent registration ✓
- Task result response format ✓

## Usage Example

When an AI model calls the `google_search` function:

1. **OpenAI API Call**: Model decides to use google_search tool
2. **AI Service**: Executes `_execute_google_search()`
3. **MCP Request**: Sends task_request to MCP server
4. **Routing**: MCP server routes to network agent
5. **Execution**: Network agent performs Google Custom Search
6. **Response**: Results flow back through MCP to AI service
7. **Integration**: AI model receives search results for context

## Environment Requirements

Required environment variables:

```bash
GOOGLE_API_KEY=your_google_api_key
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id
```

## Status: Production Ready ✅

The MCP server Google search routing is fully implemented and tested. AI models can now perform real-time web searches seamlessly through the OpenAI function calling interface.
