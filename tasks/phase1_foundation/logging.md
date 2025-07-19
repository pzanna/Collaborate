# Logging

## Description
Implement structured JSON logging for all MCP server events to improve observability.

## Subtasks
- [ ] Select a logging framework (e.g., `logrus` or built-in `log` with JSON formatter).
- [ ] Instrument MCP server to log key events: agent registration, task dispatch, completion, and errors.
- [ ] Define log schema: fields should include `timestamp`, `level`, `component`, `event`, `task_id`, `context_id`, `details`.
- [ ] Implement logging in Go: ensure logs are JSON-formatted.
- [ ] Add Python client logging in `mcp_client.py` for gRPC calls.
- [ ] Write integration tests to verify log output format.

## Acceptance Criteria
- Logs are output as valid JSON.
- Logs contain required fields and can be ingested by log analysis tools.