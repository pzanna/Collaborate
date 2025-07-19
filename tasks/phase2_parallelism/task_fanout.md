# Task Fan-out

## Description
Enable parallel dispatch of subtasks to multiple agent instances for improved throughput.

## Subtasks
- [ ] Update MCP server to support fan-out: submit one logical task to multiple agents.
- [ ] Define a `parallelism` field in the task envelope.
- [ ] Implement fan-out logic in Go server: spawn sub-tasks with distinct `task_id`s.
- [ ] Collect partial responses and aggregate results.
- [ ] Write tests demonstrating parallel execution and aggregation.

## Acceptance Criteria
- MCP server splits tasks correctly according to `parallelism`.
- Partial and final results from multiple agents are aggregated accurately.