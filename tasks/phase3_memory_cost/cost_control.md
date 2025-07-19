# Cost Control

## Description
Implement cost-awareness in RM AI to manage token usage and operational cost.

## Subtasks
- [ ] Update system prompt with cost-control guidelines.
- [ ] Instrument RM AI client to measure tokens per task.
- [ ] Implement cost estimator in `mcp_client.py`.
- [ ] Add logic to choose single-agent mode for simple tasks.
- [ ] Log token usage and trigger alerts on high consumption.

## Acceptance Criteria
- RM AI selects strategy based on cost estimations.
- Token usage is logged per session.
- Alerts fire when cost thresholds are exceeded.