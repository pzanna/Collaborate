# 🧠 Eunice Research Platform Architecture

## 📜 Overview

Eunice is a modular, AI-driven research platform. It is designed to minimise hardcoded business logic by delegating decision-making and data transformation to prompt-engineered AI models. System communication is orchestrated via a central **MCP server** with support for multi-agent tool use, database access, and external web/API integration.

Each functional component runs in its own **Docker container** to support clean isolation, modular development, and scalable deployment.

---

## 🧱 System Components

### 1. 🧩 MCP Server (Central Hub)

- Acts as the communication bus between agents, tools, and services.
- Receives requests from MCP clients and routes them to registered services.
- Enforces message format standards (Task, ToolCall, ToolResult).
- Supports debugging, tracing, and agent context tracking.

### 2. 🌐 API Gateway (FastAPI)

- Provides REST API endpoints for the frontend.
- Implements an **MCP client** to communicate with the MCP server.
- Performs **direct reads** from the database for performance.
- Sends **writes and AI-related requests** through MCP.
- Handles authentication and session state (if applicable).

### 3. 🖥️ Web Frontend (React)

- Browser-based interface for users.
- Sends JSON-based tasks to the API Gateway.
- Displays:
  - LLM results
  - Search results
  - Structured experiment data
  - Prompt execution history

### 4. 🧠 Research Manager Agent

- Coordinates complex task flows (e.g. summarising experiments).
- Implements:
  - MCP client
  - Prompt selection and templating engine
- Loads AI prompts from JSON files.
- Executes tool-chains via MCP (e.g. DB → LLM → Web → DB).
- May use memory/context tracking per session.

### 5. 📦 Database Service

- MCP-compatible service that exposes **predefined database tools**:
  - `get_experiment_by_id`
  - `store_summary`
  - `log_tool_result`
- Uses a secure PostgreSQL connection.
- Supports only approved queries for safety and reproducibility.

### 6. 🔎 Network Service

- Provides web-accessible tools to MCP clients:
  - Web search (e.g. DuckDuckGo, Bing, PubMed)
  - External API calling (e.g. OpenAI, HuggingFace)
  - Literature database access (Semantic Scholar, arXiv)
- Tools are exposed via function-style definitions and validated input schemas.

### 7. 🧠 Memory Service

- Provides memory and context tracking for agents and sessions.
- Stores conversation history, agent state, and contextual information.
- Enables persistent memory across multiple interactions.
- Integrates with MCP for agent memory management.

### 8. 🗄 Authentication Service

- Manages user authentication and authorization.
- Issues JWT tokens for API access.
- Integrates with external identity providers (e.g. OAuth, SAML).

### 9. 🐳 Docker Socket Proxy

- Security layer for Docker API access.
- Provides controlled access to Docker daemon for container management.
- Used by authentication service for secure Docker operations.
- Implements read-only access patterns for enhanced security.

### 10. 🌐 Nginx (Load Balancer/Reverse Proxy)

- Load balancer and reverse proxy for production deployments.
- Serves static frontend files.
- Routes traffic to appropriate backend services.
- Provides SSL termination and caching.

### 11. 🗄 PostgreSQL Database

- Stores structured data:
  - Experiments
  - Prompts and transactions
  - Logs and tool results
- Directly accessed by the API Gateway for read-only queries.
- Write access is gated via the Database Service (MCP tool calls only).

---

## 🔄 Data & Message Flow

```mermaid
flowchart TD
    subgraph UI
        UI[React Web UI]
    end

    subgraph API
        GW[FastAPI API Gateway]
    end

    subgraph Agents
        RM[Research Manager Agent]
    end

    subgraph Services
        DBService[Database Service]
        NetService[Network Service]
        MemService[Memory Service]
        AuthService[Auth Service]
    end

    subgraph Infra
        MCP[MCP Server]
        DB[(PostgreSQL DB)]
        DockerProxy[Docker Socket Proxy]
        Nginx[Nginx Load Balancer]
    end

    UI -->|REST| Nginx
    Nginx -->|Proxy| GW
    GW -->|MCP Task| MCP
    GW -->|Direct Read| DB
    MCP --> RM
    RM -->|Tool Calls| MCP
    MCP --> DBService
    MCP --> NetService
    MCP --> MemService
    DBService --> DB
    AuthService --> DockerProxy
    AuthService --> DB
```

---

## 🧠 Example: Task Flow – "Summarise Experiment"

1. UI sends: `POST /api/summarise?experiment_id=42`
2. API Gateway:
   - Reads experiment data from DB
   - Constructs MCP Task: `summarise_experiment_42`
3. Task routed via MCP to **Research Manager**
4. Research Manager:
   - Loads prompt from JSON
   - Calls DBService tool: `get_experiment_by_id`
   - Calls AI model (via NetService tool)
   - Calls DBService tool: `store_summary`
5. Final result returned to API Gateway and back to the user

---

## 📁 Prompts (JSON-based)

Each AI prompt is a standalone JSON file, e.g.:

```json
{
  "id": "summarise_experiment",
  "description": "Summarise an experiment for the lab log",
  "tools": ["get_experiment_by_id", "store_summary"],
  "system_prompt": "You are a lab assistant...",
  "output_format": "markdown"
}
```

Prompt selection is managed by the Research Manager, based on `transaction_type`.

---

## 🧰 Tools

Tools are registered functions callable via MCP. Each tool has:

- A unique name (e.g. `get_experiment_by_id`)
- JSON Schema for input validation
- Execution logic in the owning service

Tools may be stateful (e.g. DB writes) or stateless (e.g. web search).

---

## 🐳 Docker Containers

| Container            | Description                              |
|----------------------|------------------------------------------|
| `mcp-server`         | Central message router                   |
| `api-gateway`        | FastAPI REST API + MCP client            |
| `research-manager`   | Orchestrator agent, prompt logic         |
| `database-service`   | Database access tools via MCP            |
| `network-service`    | Web/API tool calls for LLMs, search, etc |
| `memory-service`     | Memory and context tracking              |
| `auth-service`       | JWT authentication and user management   |
| `docker-socket-proxy`| Secure Docker API access layer           |
| `nginx`              | Load balancer and reverse proxy          |
| `postgres`           | PostgreSQL database                      |
| `frontend`           | React frontend (development)             |

---

## 🔐 Security Considerations

- All DB writes go through **validated, predefined tools** (no raw SQL).
- External API keys stored securely via `.env` or secret volumes.
- Future: Add authentication (JWT, OAuth) at the API Gateway.

---

## 🔄 Extensibility

- To add a new feature:
  1. Define prompt JSON
  2. Register new tool (if needed)
  3. Add UI element (optional)
- No controller/business logic needs to change
