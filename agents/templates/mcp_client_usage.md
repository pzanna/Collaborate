# MCP Client Usage Documentation

**Version**: 1.0.0  
**Last Updated**: August 7, 2025  
**Target Audience**: Application Developers, Research Agent Implementers

## Overview

The `BaseMCPAgent` class in `mcp_client.py` is a WebSocket-based client implementation for the Eunice Research Platform, designed to communicate exclusively with the MCP (Model Context Protocol) server using JSON-RPC over WebSocket. This document provides comprehensive guidance on using the improved MCP client to create specialized research agents (e.g., Literature Search, Synthesis, Planning) that integrate with the platform’s microservices architecture.

### Key Features

- **Robust Connection Management**: Supports automatic reconnection with exponential backoff and jitter.
- **Task Handling**: Processes tasks from the MCP server with timeout management.
- **Error Handling**: Comprehensive logging and error recovery for reliable operation.
- **Dynamic Configuration**: Allows runtime configuration updates without restarting.
- **Pending Message Support**: Handles buffered messages from the MCP server upon reconnection.
- **Compliance**: Adheres to the platform’s zero attack surface policy (no HTTP/REST endpoints).

## Prerequisites

- **Python**: Version 3.8 or higher.
- **Dependencies**: `websockets`, `asyncio`, `logging`, `uuid`, `pathlib`.
- **MCP Server**: A running instance of the improved MCP server (`mcp_server.py`) at `ws://mcp-server:9000` or a custom URL.
- **Docker**: Recommended for deployment (see `docker-compose.yml` in the platform’s architecture).
- **Configuration**: A JSON config file or default configuration.

## Installation

1. **Install Dependencies**:
   ```bash
   pip install websockets
   ```

2. **Copy `mcp_client.py`**:
   Place the `mcp_client.py` file in your project directory (e.g., `/app/agents/`).

3. **Prepare Configuration**:
   Create a JSON configuration file (e.g., `/app/config/config.json`):
   ```json
   {
       "mcp_server_url": "ws://mcp-server:9000",
       "heartbeat_interval": 30,
       "ping_timeout": 10,
       "max_retries": 15,
       "base_retry_delay": 5,
       "task_timeout": 3600
   }
   ```

## Creating a Custom Agent

To create a research agent, subclass `BaseMCPAgent` and implement the required abstract methods.

### Example: Literature Search Agent

```python
import asyncio
from mcp_client import BaseMCPAgent

class LiteratureAgent(BaseMCPAgent):
    def __init__(self, agent_type: str, config: dict):
        super().__init__(agent_type, config)
        # Add agent-specific initialization (e.g., API keys for external services)

    def get_capabilities(self):
        """Return list of agent capabilities."""
        return ["search_literature", "normalize_records"]

    def setup_task_handlers(self):
        """Setup task handlers for this agent."""
        return {
            "search_literature": self._handle_search,
            "normalize_records": self._handle_normalize
        }

    async def _handle_search(self, data: dict):
        """Handle literature search task."""
        query = data.get("query", "")
        self.logger.info(f"Searching literature for query: {query}")
        # Simulate search (replace with actual API call to PubMed, arXiv, etc.)
        await asyncio.sleep(1)  # Simulate async work
        return {"results": [{"title": "Sample Paper", "doi": "10.1000/xyz123"}]}

    async def _handle_normalize(self, data: dict):
        """Handle record normalization task."""
        records = data.get("records", [])
        self.logger.info(f"Normalizing {len(records)} records")
        # Simulate normalization
        return {"normalized": [{"title": r.get("title", ""), "doi": r.get("doi", "")} for r in records]}

# Main entry point
if __name__ == "__main__":
    main = create_agent_main(LiteratureAgent, "literature", "/app/config/config.json")
    asyncio.run(main())
```

### Steps to Create an Agent

1. **Subclass `BaseMCPAgent`**:
   - Initialize with `agent_type` (e.g., `"literature"`) and `config` (loaded from file or defaults).
   - Add agent-specific initialization (e.g., external service credentials).

2. **Implement `get_capabilities`**:
   - Return a list of strings representing the tasks the agent can handle (e.g., `["search_literature", "normalize_records"]`).

3. **Implement `setup_task_handlers`**:
   - Return a dictionary mapping task types to async handler methods (e.g., `{"search_literature": self._handle_search}`).
   - Each handler should process task data and return a result dictionary.

4. **Define Task Handlers**:
   - Create async methods (e.g., `_handle_search`) to process task data.
   - Log task execution and handle errors gracefully.
   - Return results in a dictionary format for the MCP server.

5. **Create Main Entry Point**:
   - Use `create_agent_main` to generate the agent’s main function.
   - Specify the agent class, type, and config path.

## Configuration

The agent uses a JSON configuration file with the following fields:

| Field                | Type   | Default Value            | Description                                      |
|----------------------|--------|--------------------------|--------------------------------------------------|
| `mcp_server_url`     | String | `ws://mcp-server:9000`  | URL of the MCP server.                           |
| `heartbeat_interval`  | Integer| 30                      | Seconds between heartbeats.                      |
| `ping_timeout`       | Integer| 10                      | Seconds to wait for ping response.               |
| `max_retries`        | Integer| 15                      | Maximum reconnection attempts.                   |
| `base_retry_delay`   | Integer| 5                       | Base delay (seconds) for reconnection backoff.   |
| `task_timeout`       | Integer| 3600                    | Task timeout in seconds (default: 1 hour).       |

### Dynamic Configuration Update

Update configuration at runtime using `update_config`:

```python
new_config = {
    "mcp_server_url": "ws://new-mcp-server:9000",
    "heartbeat_interval": 60
}
await agent.update_config(new_config)
```

This updates the agent’s settings and reconnects if `mcp_server_url` changes.

## Running the Agent

### Standalone

Run the agent directly:

```bash
python literature_agent.py
```

### Docker

Add to `docker-compose.yml`:

```yaml
services:
  literature-agent:
    build: ./agents/literature
    environment:
      - MCP_SERVER_URL=ws://mcp-server:9000
    depends_on:
      - mcp-server
    networks:
      - eunice-network
```

Build and run:

```bash
docker-compose up --build
```

## Task Handling

The agent processes tasks received from the MCP server as `task_request` messages with the format:

```json
{
    "type": "task_request",
    "task_id": "uuid",
    "task_type": "search_literature",
    "data": {"query": "AI ethics"},
    "context_id": "context-uuid",
    "timestamp": "2025-08-07T15:05:00Z"
}
```

The agent responds with a `task_result` message:

```json
{
    "type": "task_result",
    "task_id": "uuid",
    "status": "completed",
    "result": {"results": [...]},
    "agent_id": "literature-abc123",
    "timestamp": "2025-08-07T15:05:02Z"
}
```

### Error Handling

If a task fails or is unknown, the agent sends an error response:

```json
{
    "type": "task_result",
    "task_id": "uuid",
    "status": "error",
    "error": "Unknown task type: invalid_task",
    "agent_id": "literature-abc123",
    "timestamp": "2025-08-07T15:05:02Z"
}
```

Tasks exceeding the `task_timeout` (default: 3600 seconds) are automatically cleaned up with a timeout response.

## Testing

### Unit Tests

Test key methods using `pytest` and `pytest-asyncio`:

```python
import pytest
from literature_agent import LiteratureAgent

@pytest.mark.asyncio
async def test_search_literature():
    agent = LiteratureAgent("literature", {})
    result = await agent._handle_search({"query": "AI ethics"})
    assert "results" in result
    assert len(result["results"]) > 0

@pytest.mark.asyncio
async def test_capabilities():
    agent = LiteratureAgent("literature", {})
    assert "search_literature" in agent.get_capabilities()
```

### Integration Tests

1. **Setup**: Deploy the MCP server and agent in a Docker Compose environment.
2. **Reconnection Test**:
   - Stop the MCP server temporarily and verify the agent reconnects within `max_retries`.
   - Check logs for reconnection attempts and success.
3. **Task Test**:
   - Send a `task_request` via the MCP server and verify the agent’s response.
   - Simulate an unknown task type and check for error response.
4. **Timeout Test**:
   - Modify `task_timeout` to 10 seconds, send a task, and verify timeout response after delay.

### Logging Analysis

- Monitor logs for connection status, task execution, and errors.
- Example log entries:
  ```
  2025-08-07 15:05:00,123 - literature-agent - INFO - Successfully connected to MCP server
  2025-08-07 15:05:01,456 - literature-agent - INFO - Executing task: search_literature (ID: uuid123)
  2025-08-07 15:05:02,789 - literature-agent - ERROR - Error processing message: Invalid JSON
  ```

## Troubleshooting

- **Connection Failures**:
  - Check `mcp_server_url` in the config.
  - Verify the MCP server is running and accessible.
  - Increase `max_retries` or `base_retry_delay` for flaky networks.
- **Task Failures**:
  - Ensure `task_type` matches a handler in `setup_task_handlers`.
  - Check logs for error details and verify task data format.
- **Timeout Issues**:
  - Adjust `task_timeout` if tasks require more time.
  - Verify server’s task timeout aligns with the client’s.
- **Pending Messages**:
  - On reconnection, the server delivers buffered messages; ensure handlers process `task_result` or `error` messages correctly.

## Best Practices

- **Logging**: Use the agent’s logger for all task-related logging to aid debugging.
- **Error Handling**: Implement robust error handling in task handlers to prevent crashes.
- **Configuration**: Store sensitive data (e.g., API keys) in environment variables or a secure secrets manager, not in the config file.
- **Testing**: Maintain at least 80% test coverage for task handlers and capabilities.
- **Monitoring**: Integrate with the platform’s Prometheus/Grafana stack to monitor agent health and task metrics.

## Example Usage in Eunice Platform

To integrate with the Eunice Research Platform:

1. **Deploy Agent**:
   - Add to `docker-compose.yml` as shown above.
   - Ensure `depends_on: mcp-server` and network configuration.

2. **Register Capabilities**:
   - Update `get_capabilities` to match the agent’s role (e.g., `"search_literature"` for Literature Search Agent).
   - Register with the MCP server to receive relevant tasks.

3. **Handle Tasks**:
   - Implement task handlers to interact with other services (e.g., Internet Access Service for literature searches) via MCP messages.
   - Example: Route external API calls through the MCP server’s `internet_request` message type (if implemented).

4. **Monitor**:
   - Expose `/health` endpoint if required by the platform’s monitoring stack.
   - Use `status_response` messages to report agent status to the MCP server.

## Future Enhancements

- **gRPC Support**: Add gRPC client capabilities for high-throughput tasks (if the MCP server adopts gRPC).
- **Task Prioritization**: Implement priority queues for tasks based on urgency or complexity.
- **Dynamic Capabilities**: Allow runtime updates to `capabilities` without restarting the agent.
- **Metrics**: Integrate Prometheus metrics for task execution time and connection stability.

## Conclusion

The improved `BaseMCPAgent` provides a robust, scalable foundation for building research agents in the Eunice Research Platform. By following this documentation, developers can create specialized agents that leverage the MCP server’s enhanced features, ensuring reliable communication, task handling, and error recovery.

For further assistance, refer to the platform’s master architecture documentation (`MASTER_ARCHITECTURE.md`) or contact the development team.