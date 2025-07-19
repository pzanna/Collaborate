# Task Dependency Tracking

## Description
Implement parent/child relationships for tasks to manage dependencies and ordering.

## Subtasks
- [ ] Extend `ResearchAction` message to include optional `parent_task_id`.
- [ ] Modify MCP server to maintain a dependency graph.
- [ ] Ensure child tasks wait for the parent to complete.
- [ ] Update logging to include parent/child relationships.
- [ ] Write integration tests for dependency scenarios.

## Acceptance Criteria
- Tasks respect dependencies during execution.
- Dependency graph can be queried via MCP or logs.