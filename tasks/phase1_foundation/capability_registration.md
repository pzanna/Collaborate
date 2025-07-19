# Capability Registration ✅ COMPLETED

## Description

Enable agents to announce their capabilities to the MCP server for dynamic task routing.

## Subtasks

- [x] Add a `RegisterCapabilities` RPC to the MCP `.proto`.
- [x] Implement registration method in MCP server to store agent capabilities.
- [x] Update agent stubs to call registration on startup.
- [x] Modify RM AI prompt logic to query available capabilities before assigning tasks.
- [x] Write tests to verify capabilities registration and querying.

## Acceptance Criteria

- Agents successfully register capabilities on connect.
- MCP server maintains an up-to-date registry.
- RM AI can inspect registry to route tasks correctly.
