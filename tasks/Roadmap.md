# 🧭 Roadmap: Multi-AI Research System Improvements

## Phase 1: Foundation Hardening ✅ COMPLETED

### Goals

- Standardise protocols
- Improve logging/debugging
- Establish reliable agent execution

### Tasks

- [x] Update MCP `.proto` with task envelope, timeout, retry fields
- [x] Implement structured JSON logging in MCP server
- [x] Add task timeouts and failure tracking
- [x] Add agent capability registration
- [x] Update RM system prompt for new schema

---

## Phase 2: Intelligence Scaling ✅ COMPLETED

### Goals

- Improve performance with parallelism
- Smarter Research Manager task planning

### Tasks

- [x] Enable parallel task dispatch in MCP server
- [x] Implement task dependency tracking (parent/child)
- [x] Teach RM AI to decompose complex tasks
- [x] Collate parallel results through ReasonerAgent

---

## Phase 3: Memory & Cost Optimisation

### Goals

- Persist context
- Control token and compute usage

### Tasks

- [ ] Enhance MemoryAgent with storage + query
- [ ] Teach RM AI to avoid redundant agent calls
- [ ] Add cost-aware decision making to prompt
- [ ] Store context traces with context_id

---

## Phase 4: Frontend Integration & Visual Tools

### Goals

- Increase system observability
- Add task viewer and prompt planner

### Tasks

- [ ] Build live task viewer UI in React
- [ ] Add MCP session visualisation (task graph)
- [ ] Expose RM internal plan as readable summary
- [ ] Add user control over RM decisions (optional)

---

## Priorities

| Priority | Task Area                  |
| -------- | -------------------------- |
| High     | MCP reliability & logging  |
| High     | RM Prompt Planning Upgrade |
| Medium   | Parallelism                |
| Medium   | Memory Agent               |
| Low      | Frontend tools             |
