# Timeouts ✅ COMPLETED

## Description

Implement timeout handling for tasks that exceed expected execution duration.

## Subtasks

- [x] Define default timeout value (e.g., 30 seconds) in MCP server configuration.
- [x] Modify MCP server to track task start times and enforce timeouts.
- [x] On timeout, mark task as `failed` and emit a timeout event.
- [x] Update RM AI prompt logic to detect timeout failures and retry accordingly.
- [x] Add unit tests simulating long-running tasks to verify timeout behavior.

## Acceptance Criteria

- Long-running tasks are cancelled after timeout.
- Timeout events are logged and visible to RM AI.
- RM AI retries timed-out tasks according to policy.
