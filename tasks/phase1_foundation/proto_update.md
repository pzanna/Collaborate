# Proto Update ✅ COMPLETED

## Description

Extend the MCP protocol definitions to include additional fields for enhanced task control.

## Subtasks

- [x] Add `timeout` and `retry` fields to the `ResearchAction` message in `proto/github/mcp/mcp.proto`.
- [x] Update message envelope: ensure `task_id`, `context_id`, and `priority` fields are defined.
- [x] Run `protoc` to regenerate MCP and Python bindings.
- [x] Update MCP server code to handle new fields in `ResearchAction`.
- [x] Update Python `mcp_client.py` wrapper to include new fields.
- [x] Write unit tests for serialization/deserialization of updated messages.

## Acceptance Criteria

- Protocol definitions compile without errors.
- MCP and Python clients/servers handle new fields correctly.
- Unit tests cover new fields and pass.
