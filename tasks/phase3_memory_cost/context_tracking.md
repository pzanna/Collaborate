# Context Tracking

## Description
Ensure `context_id` is consistently included and tracked across tasks and sessions.

## Subtasks
- [ ] Review all MCP message flows for `context_id` usage.
- [ ] Implement context persistence in FastAPI session store.
- [ ] Expose an endpoint to resume or inspect session contexts.
- [ ] Add tests for context continuity across interactions.

## Acceptance Criteria
- `context_id` flows correctly through all tasks.
- Sessions can be resumed with preserved context.