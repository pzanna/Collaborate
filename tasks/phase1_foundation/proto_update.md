# Proto Update

## Description
Extend the MCP protocol definitions to include additional fields for enhanced task control.

## Subtasks
- [ ] Add `timeout` and `retry` fields to the `ResearchAction` message in `proto/github/mcp/mcp.proto`.
- [ ] Update message envelope: ensure `task_id`, `context_id`, and `priority` fields are defined.
- [ ] Run `protoc` to regenerate Go and Python bindings.
- [ ] Update Go server code to handle new fields in `ResearchAction`.
- [ ] Update Python `mcp_client.py` wrapper to include new fields.
- [ ] Write unit tests for serialization/deserialization of updated messages.

## Acceptance Criteria
- Protocol definitions compile without errors.
- Go and Python clients/servers handle new fields correctly.
- Unit tests cover new fields and pass.