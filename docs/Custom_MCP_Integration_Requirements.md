# 📄 Requirements Document: Custom MCP Integration for Multi-AI Research System

**Project Name**: Multi-AI Research System  
**Author**: Paul  
**Date**: 18-07-2025  
**Version**: 1.0

---

## 1. 🧠 Objective

Develop and integrate a **Custom Message Control Protocol (MCP) Server**, using GitHub's `mcp-server` as a base, to enable robust task orchestration, agent communication, and context-aware coordination across multiple AI agents (e.g. Retriever, Reasoner, Executor, Memory).

---

## 2. 🧱 System Overview

![System Overview](Architecture.jpg)

The system will follow a modular, agent-based architecture where:

- A central **Research Manager AI** delegates tasks to specialised agents.
- Agents (Retriever, Reasoner, Executor, Memory) are loosely coupled and communicate via MCP.
- All interactions (task assignment, partial results, completions) pass through the **Custom MCP Server**, using structured gRPC messages.

---

## 3. 🔀 Architecture

### 3.1 Components

| Component        | Role                                               |
| ---------------- | -------------------------------------------------- |
| Research Manager | Orchestrates research goals into subtasks          |
| MCP Server       | Routes messages, maintains sessions and task flow  |
| Retriever Agent  | Searches and retrieves documents/data              |
| Reasoner Agent   | Performs CoT reasoning, summarisation, correlation |
| Execution Agent  | Executes tools, runs code, invokes APIs            |
| Memory Agent     | Maintains persistent memory and shared context     |

### 3.2 Communication Model

- Uses **gRPC** for all agent communication.
- Messages use custom `.proto` schemas.
- Each message includes `task_id`, `context_id`, `agent_type`, `action`, `payload`, and `status`.

---

## 4. ✅ Functional Requirements

### 4.1 Core Features

| ID  | Description                                                      |
| --- | ---------------------------------------------------------------- |
| FR1 | Implement a custom MCP server derived from GitHub's `mcp-server` |
| FR2 | Define and support custom message type: `ResearchAction`         |
| FR3 | Allow agent registration and capability declaration              |
| FR4 | Implement session and task routing logic                         |
| FR5 | Support streaming partial results from agents                    |
| FR6 | Track task status: `pending`, `working`, `completed`, `failed`   |
| FR7 | Maintain a persistent context ID across related messages         |
| FR8 | Allow Research Manager to cancel, retry, or reassign tasks       |

### 4.2 Protobuf Message Schema

```protobuf
message ResearchAction {
  string task_id = 1;
  string context_id = 2;
  string agent_type = 3;
  string action = 4;
  string payload = 5;
  string priority = 6;
}
```

---

## 5. 🛠 Technical Requirements

| ID  | Requirement                                                          |
| --- | -------------------------------------------------------------------- |
| TR1 | Fork `github-mcp-server` and rename project to `research-mcp-server` |
| TR2 | Add new `.proto` files for research-specific messages                |
| TR3 | Extend Go server logic to handle `ResearchAction` messages           |
| TR4 | Build CLI-compatible entry point (`cmd/research-mcp-server`)         |
| TR5 | Maintain compatibility with gRPC clients written in Python or Go     |
| TR6 | Implement structured JSON logging for all message traffic            |
| TR7 | (Optional) Log all message exchanges in SQLite for traceability      |

---

## 6. 🧪 Testing Requirements

| ID  | Description                                                                    |
| --- | ------------------------------------------------------------------------------ |
| TE1 | Simulate `ResearchManager` sending a `search_papers` task                      |
| TE2 | Validate that `RetrieverAgent` receives the correct payload                    |
| TE3 | Confirm partial and final responses are routed back to the correct session     |
| TE4 | Simulate failed agent and ensure retry is triggered correctly                  |
| TE5 | Confirm end-to-end task resolution pipeline: `Retriever → Reasoner → Executor` |

---

## 7. 🔐 Security Considerations

- Limit server exposure to local interfaces (`127.0.0.1`) for initial testing
- Use mTLS or access tokens if deploying across machines
- Audit incoming messages for malformed payloads or unsupported types

---

## 8. 📦 Deliverables

| Item | Description                                                                 |
| ---- | --------------------------------------------------------------------------- |
| 1    | Forked and renamed `research-mcp-server` with working build                 |
| 2    | Custom `.proto` definitions for `ResearchAction`, `AgentCapabilities`, etc. |
| 3    | Working Go server handling custom tasks                                     |
| 4    | Python/Go agent template clients                                            |
| 5    | Example `ResearchManager` task planner client                               |
| 6    | Minimal SQLite logger for tracing message flow (optional)                   |

---

## 9. 🗓 Project Milestones

| Phase | Description                                | Target Date |
| ----- | ------------------------------------------ | ----------- |
| P1    | Fork and compile GitHub MCP server         | Week 1      |
| P2    | Define custom `.proto` and task types      | Week 2      |
| P3    | Implement core routing and agent registry  | Week 3      |
| P4    | Integrate Research Manager and one agent   | Week 4      |
| P5    | End-to-end task test: `search + summarise` | Week 5      |
| P6    | Logging and context persistence            | Week 6      |

---

## 10. 🧩 Integration with Existing Application

Paul's existing application uses:

- **Backend**: Python with FastAPI
- **Frontend**: React

The MCP server, written in Go, will be integrated as a sidecar microservice.

### 🔁 Integration Strategy

1. **MCP Server as Sidecar**

   - Run the Go-based MCP server as a separate process or Docker container.
   - It listens for gRPC calls from the Python backend.

2. **Python gRPC Client in FastAPI**

   - Use `grpcio` and `grpcio-tools` to generate Python bindings from the `.proto` files.
   - Implement a `mcp_client.py` wrapper module to abstract gRPC interactions.
   - FastAPI endpoints invoke this wrapper to send and receive messages.

3. **Frontend Communication**

   - The React frontend continues to interact with FastAPI via REST.
   - No change is needed on the frontend side.

4. **Task Flow**
   - React → FastAPI (REST)
   - FastAPI → MCP Server (gRPC)
   - MCP Server → Agents (gRPC)
   - Agent Responses → MCP Server → FastAPI → React

### 🛠 Toolchain Summary

| Layer         | Technology                           |
| ------------- | ------------------------------------ |
| Frontend      | React                                |
| API Layer     | FastAPI (Python)                     |
| Orchestration | Custom MCP Server (Go)               |
| Messaging     | gRPC + Protobuf                      |
| Agents        | Language-agnostic (Python preferred) |
