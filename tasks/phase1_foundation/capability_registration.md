# Capability Registration

## Description
Enable agents to announce their capabilities to the MCP server for dynamic task routing.

## Subtasks
- [ ] Add a `RegisterCapabilities` RPC to the MCP `.proto`.
- [ ] Implement registration method in Go server to store agent capabilities.
- [ ] Update agent stubs (Python and Go) to call registration on startup.
- [ ] Modify RM AI prompt logic to query available capabilities before assigning tasks.
- [ ] Write tests to verify capabilities registration and querying.

## Acceptance Criteria
- Agents successfully register capabilities on connect.
- MCP server maintains an up-to-date registry.
- RM AI can inspect registry to route tasks correctly.