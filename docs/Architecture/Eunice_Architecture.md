# 🧠 Eunice Research Platform Architecture

## 📜 Overview

Eunice is a modular, AI-driven research platform designed for systematic literature reviews, research planning, and academic project management. It minimizes hardcoded business logic by delegating decision-making and data transformation to prompt-engineered AI models. System communication is orchestrated via a central **MCP server** with support for multi-agent tool use, database access, and external web/API integration.

The platform implements a hierarchical research structure: **Projects** → **Research Topics** → **Research Plans** → **Tasks**, enabling structured and scalable research workflows.

Each functional component runs in its own **Docker container** to support clean isolation, modular development, and scalable deployment.

---

## 🧱 System Components

### 1. 🧩 MCP Server (Central Hub)

- Acts as the communication bus between agents, tools, and services.
- Receives requests from MCP clients and routes them to registered services.
- Enforces message format standards (Task, ToolCall, ToolResult).
- Supports debugging, tracing, and agent context tracking.

### 2. 🌐 API Gateway (FastAPI)

- Provides comprehensive REST API endpoints for the frontend via **V2 Hierarchical API**.
- Implements an **MCP client** to communicate with the MCP server.
- Performs **direct reads** from the database for performance.
- Sends **writes and AI-related requests** through MCP.
- Supports complete CRUD operations for:
  - Projects (containers for research initiatives)
  - Research Topics (specific areas of investigation)
  - Research Plans (structured methodological approaches)
  - Tasks (individual work units)
  - Literature Records (academic papers and publications)
  - Search Term Optimizations (enhanced search strategies)
- Provides statistics, hierarchy views, and execution tracking.
- Handles authentication and session state.

### 3. 🖥️ Web Frontend (React + Vite)

- Modern browser-based interface built with React and Vite.
- Integrates with shadcn/ui component library for consistent UI/UX.
- Sends structured requests to the API Gateway.
- Displays:
  - Project hierarchies and research structures
  - Literature review results and analysis
  - Research plan generation and execution
  - Task progress and completion tracking
  - Real-time execution progress and statistics

### 4. 🧠 Research Manager Agent

- Coordinates complex research workflows and task orchestration.
- Implements:
  - MCP client for service communication
  - Prompt selection and templating engine
  - Multi-step research plan execution
- Loads AI prompts from JSON configuration files.
- Executes complex tool-chains via MCP (e.g. DB → LLM → Literature Search → Analysis → DB).
- Manages research execution context and progress tracking.
- Coordinates with Literature Agent for specialized literature tasks.

### 4.1. 📚 Literature Agent

- Specialized agent for literature review and analysis tasks.
- Handles systematic literature searches and screening.
- Manages academic database integrations.
- Performs literature synthesis and summarization.
- Works with Research Manager for comprehensive literature workflows.

### 5. 📦 Database Service

- MCP-compatible service that exposes **predefined database tools** for research data management:
  - `create_project`, `update_project`, `delete_project`
  - `create_research_topic`, `update_research_topic`, `delete_research_topic`
  - `create_research_plan`, `update_research_plan`, `delete_research_plan`
  - `create_task`, `update_task`, `delete_task`
  - `create_research_task`, `update_research_task`, `delete_research_task`
  - `create_literature_record`, `update_literature_record`, `delete_literature_record`
  - `create_search_term_optimization`, `update_search_term_optimization`, `delete_search_term_optimization`
- Uses a secure PostgreSQL connection with connection pooling.
- Supports only validated, parameterized queries for safety and reproducibility.
- Implements comprehensive database schema for research workflows.
- Handles hierarchical data relationships and referential integrity.

### 6. 🔎 Network Service

- Provides web-accessible tools to MCP clients for external data access:
  - Academic literature search (PubMed, Semantic Scholar, arXiv, CORE)
  - Web search capabilities (Google Custom Search, DuckDuckGo)
  - External API integrations (OpenAI, Anthropic, HuggingFace)
  - Research database connections (CrossRef, OpenAlex)
- Tools are exposed via function-style definitions with validated input schemas.
- Implements rate limiting and error handling for external services.
- Supports caching mechanisms for improved performance and reduced API costs.

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

- Stores structured research data in a hierarchical schema:
  - **Projects**: Top-level research initiatives with metadata and status tracking
  - **Research Topics**: Specific areas of investigation within projects
  - **Research Plans**: Structured methodological approaches with approval workflows
  - **Tasks & Research Tasks**: Individual work units with execution tracking
  - **Literature Records**: Academic papers with bibliographic data and categorization
  - **Search Term Optimizations**: Enhanced search strategies for literature discovery
- Directly accessed by the API Gateway for read-only queries with performance optimization.
- Write access is exclusively gated via the Database Service through validated MCP tool calls.
- Implements comprehensive indexing and foreign key relationships for data integrity.

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
        LA[Literature Agent]
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
    MCP --> LA
    RM -->|Tool Calls| MCP
    LA -->|Tool Calls| MCP
    MCP --> DBService
    MCP --> NetService
    MCP --> MemService
    DBService --> DB
    AuthService --> DockerProxy
    AuthService --> DB
```

---

## 🧠 Example: Task Flow – "Generate AI Research Plan"

1. UI sends: `POST /v2/topics/{topic_id}/ai-plans`
2. API Gateway:
   - Validates request and checks topic exists
   - Constructs MCP Task: `coordinate_research` with plan generation context
3. Task routed via MCP to **Research Manager**
4. Research Manager:
   - Calls DBService tool: `get_research_topic` to fetch topic details
   - Loads prompt configuration from JSON: `create_research_plan.json`
   - Processes AI model response using configured template
   - Calls DBService tool: `create_research_plan` with structured plan data
5. API Gateway receives plan creation confirmation
6. Returns ResearchPlanResponse with plan details, cost estimates, and approval status

## 🔄 Additional API Workflows

### Literature Record Management
- Create, update, delete academic papers and publications
- Store bibliographic metadata, abstracts, and categorizations  
- Support DOI resolution and citation tracking

### Research Execution Tracking
- Initiate research tasks with specified depth levels
- Monitor execution progress through multiple stages
- Provide real-time status updates and completion metrics

### Statistics and Analytics
- Project-level aggregated statistics across all topics and plans
- Topic-level metrics including plan counts and cost analysis
- Plan-level progress tracking with task completion rates

---

## 📁 Prompts (JSON-based)

Each AI prompt is a comprehensive JSON configuration file with complete AI model settings, e.g.:

```json
{
  "id": "create_research_plan",
  "description": "Generate a detailed research plan from a query and scope using a structured JSON format",
  "agent_type": "ai_service",
  "model": "grok-3-mini",
  "system_prompt": "You are a research planning assistant. Provide detailed, structured responses in JSON format.",
  "user_prompt_template": "Please create a comprehensive research plan for the following query:\n\nQuery: {query}\nScope: {scope}\nContext: {context_json}\n\n[Detailed template with specific output format requirements]",
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "google_search",
        "description": "Search the web using Google Custom Search to find recent research",
        "parameters": {
          "type": "object",
          "properties": {
            "query": {"type": "string", "description": "The search query"},
            "num_results": {"type": "integer", "default": 10, "maximum": 10}
          },
          "required": ["query"]
        }
      }
    }
  ],
  "tool_choice": "auto",
  "max_tokens": 3000,
  "temperature": 0.6,
  "created_at": "2025-08-08T12:00:00Z"
}
```

Prompt configurations include:
- Complete AI model parameters (temperature, max_tokens, tool_choice)
- Structured output format requirements
- Tool definitions with JSON schemas
- Template variables for dynamic content injection
- Metadata for versioning and tracking

---

## 🧰 Tools

Tools are registered functions callable via MCP, implementing the complete research workflow. Each tool has:

- A unique name (e.g. `create_research_plan`, `google_search`, `get_literature_records`)
- JSON Schema for input validation and type safety
- Execution logic in the owning service (Database, Network, Memory)
- Error handling and result formatting

### Database Tools
- CRUD operations for all research entities (projects, topics, plans, tasks, literature)
- Hierarchical data management with referential integrity
- Statistics and analytics aggregation

### Network Tools  
- Academic literature search across multiple databases
- Web search for general research context
- External API integrations for AI models and data sources

### Memory Tools
- Context tracking across research sessions
- Agent state management and persistence
- Historical interaction logging

Tools may be stateful (e.g. DB writes, memory updates) or stateless (e.g. web search, calculations).

---

## 🐳 Docker Containers

| Container            | Description                                           |
|----------------------|-------------------------------------------------------|
| `mcp-server`         | Central message router and coordination hub           |
| `api-gateway`        | FastAPI REST API + MCP client + V2 Hierarchical API  |
| `research-manager`   | Research orchestrator agent with prompt logic        |
| `literature`         | Specialized literature review and analysis agent     |
| `database-service`   | Database access tools via MCP with research schema   |
| `network-service`    | Web/API tools for literature search and AI models    |
| `memory-service`     | Context tracking and agent state management          |
| `auth-service`       | JWT authentication and user management               |
| `docker-socket-proxy`| Secure Docker API access layer                       |
| `nginx`              | Load balancer and reverse proxy (production)         |
| `postgres`           | PostgreSQL database with research data schema        |
| `frontend`           | React + Vite frontend with shadcn/ui components      |

---

## 🔐 Security Considerations

- **Database Security**: All DB writes go through validated, predefined tools with parameterized queries (no raw SQL injection possible)
- **API Security**: JWT authentication implemented at API Gateway level with user session management
- **Container Isolation**: Each service runs in isolated Docker containers with minimal attack surface
- **Secret Management**: External API keys stored securely via `.env` files or Docker secret volumes
- **Network Security**: Docker Socket Proxy provides controlled access to Docker daemon
- **Input Validation**: All API inputs validated against JSON schemas before processing
- **MCP Security**: Message validation and agent authentication through MCP protocol

---

## 🔄 Extensibility & Development

### Adding New Features:
1. **Define Data Model**: Add new entities to hierarchical data models if needed
2. **Create Database Tools**: Implement CRUD operations in Database Service
3. **Design API Endpoints**: Add REST endpoints to API Gateway V2 router
4. **Configure AI Prompts**: Create JSON prompt configurations for AI-driven features
5. **Update Frontend**: Add UI components using shadcn/ui library
6. **Register Tools**: Expose new capabilities via MCP tool registration

### Development Workflow:
- **Local Development**: Use `start_dev.sh` for development environment with hot reload
- **Container Management**: Individual services can be developed and tested in isolation
- **Database Migrations**: Schema changes managed through Database Service initialization
- **Prompt Engineering**: JSON-based prompt configurations enable rapid AI behavior iteration
- **Testing**: Each service includes health checks and validation endpoints

### No Controller/Business Logic Changes Required:
- New research workflows implemented through prompt engineering
- Database operations use existing tool patterns
- UI updates leverage existing component architecture
- Agent coordination handled through MCP message passing
