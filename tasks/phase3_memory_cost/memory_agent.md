# Memory Agent Enhancement

## Description
Enhance MemoryAgent to store structured intermediate results and support queries.

## Subtasks
- [ ] Define memory storage schema (SQLite tables or vector DB).
- [ ] Implement `StoreMemory` and `QueryMemory` RPCs in `.proto`.
- [ ] Build storage backend accessible via MCP (Go or Python).
- [ ] Update RM AI to store key findings with metadata.
- [ ] Add tests for memory storage and retrieval.

## Acceptance Criteria
- MemoryAgent persists data across sessions.
- RM AI can query and retrieve relevant memory entries.