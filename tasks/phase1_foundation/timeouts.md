# Timeouts

## Description
Implement timeout handling for tasks that exceed expected execution duration.

## Subtasks
- [ ] Define default timeout value (e.g., 30 seconds) in MCP server configuration.
- [ ] Modify Go server to track task start times and enforce timeouts.
- [ ] On timeout, mark task as `failed` and emit a timeout event.
- [ ] Update RM AI prompt logic to detect timeout failures and retry accordingly.
- [ ] Add unit tests simulating long-running tasks to verify timeout behavior.

## Acceptance Criteria
- Long-running tasks are cancelled after timeout.
- Timeout events are logged and visible to RM AI.
- RM AI retries timed-out tasks according to policy.