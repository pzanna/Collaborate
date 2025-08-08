# 🧠 Eunice Research Platform — v0.5.1 Architecture (MCP-Standard Compliant)

**Status**: Proposed  
**Last Updated**: 08-08-2025  
**Audience**: Developers, System Architects

---

## Why this update?
Your earlier design used an **MCP hub**. That pattern is **not part of the MCP spec**. MCP defines **point‑to‑point client ↔ server sessions** (stdio / socket / WebSocket). Each **client connects directly** to one or more servers; there is no broker defined by the standard.

This revision removes the hub and replaces it with **client‑side multiplexing** and **server composition** that remain compliant.

---

## Key Principles (per MCP)
- **Direct sessions**: One MCP session per server (independent transport).
- **Capability discovery**: The client discovers tools from each server via standard introspection.
- **No message brokering**: If you want a “router”, implement it as a *client* that calls multiple servers, or as a *composite server* that exposes its own tools and calls others internally (opaque to the outside).
- **Clear trust boundaries**: Secrets and policies live on the client side; servers expose tools with parameter contracts.

---

## High-Level Architecture (Compliant)

```mermaid
graph TB
  subgraph "Frontend"
    UI[React/Vite]
  end

  subgraph "API Layer (MCP Client Multiplexer)"
    GW[API Gateway (FastAPI)]:::client
    Auth[Auth Service]
  end

  subgraph "Agents (run inside GW workers)"
    Planner[Research Manager (Planner)]:::agent
    Critic[Critic]:::agent
    LitAgent[Literature Agent]:::agent
  end

  subgraph "MCP Servers (Direct Sessions)"
    DBsrv[Database Service]:::server
    Netsrv[Network Service]:::server
    Storesrv[Storage Service<br/>(CAS, Extractor, Embeddings)]:::server
    Memorysrv[Memory Service]:::server
  end

  subgraph "Infra"
    PG[(PostgreSQL)]
    Nginx[Nginx]
  end

  UI-->Nginx-->GW
  GW-->PG
  GW-->Planner
  GW-->Critic
  GW-->LitAgent

  %% Direct client->server sessions (no hub):
  GW-. stdio/ws sessions .->DBsrv
  GW-. stdio/ws sessions .->Netsrv
  GW-. stdio/ws sessions .->Storesrv
  GW-. stdio/ws sessions .->Memorysrv

  classDef client fill:#e8f7ff,stroke:#1e90ff;
  classDef server fill:#f0f5e6,stroke:#5f8a00;
  classDef agent fill:#fff3e6,stroke:#f59e0b;
```

**What changed**
- Removed the “MCP Hub”.  
- **Gateway is the sole MCP client** maintaining **N independent sessions**, one per server.  
- Agents (Planner/Critic/Lit) execute *inside the Gateway* (or separate worker entrypoint) and call tools via the Gateway’s client API—still standard, because they are not brokering, just *using* clients.

---

## Connection Manager (inside Gateway)
- Start up: read config → open one session per server (`stdio|tcp|ws`).
- On connection: do capability discovery → cache tool schemas with `server_id` prefix.
- Tool call: route by `server_id.tool_name`, add correlation IDs, enforce policy.
- Health: heartbeat per session, auto‑reconnect with backoff, circuit‑breaker per server.

**Example logical names**
- `db.create_research_plan` → Database Service
- `net.web_search` → Network Service
- `store.extract_pdfs` / `store.embeddings_upsert` → Storage Service
- `mem.context_get` / `mem.context_put` → Memory Service

---

## Data & Governance Additions (unchanged conceptually)
Add **agentic** entities (unchanged from v0.5):
- `runs`, `actions`, `approvals`, `artefacts`, `citations`

These power reproducibility and human‑in‑the‑loop control while staying orthogonal to MCP transport.

---

## API Additions
- `POST /v2/runs` — enqueue a run from a task/topic/plan
- `GET /v2/runs/{id}` — status and summary
- `GET /v2/runs/{id}/actions` — step log
- `GET /v2/events?run_id=…` — SSE live log
- `POST /v2/approvals/{id}:approve|reject` — human gates
- `GET /v2/artefacts?...` — browse/download CAS outputs

---

## Planner/Critic Loop (inside Gateway worker)
1. Planner proposes steps (server.tool + input).
2. Critic validates (citations present, unit sanity, policy).
3. Gateway executes steps via **direct MCP sessions**.
4. Violations require approval → pause run → resume after decision.
5. Artefacts are stored in CAS (Storage Service); citations recorded.

**Stop conditions**: `max_steps`, `max_cost`, `max_walltime`, `no_new_results_k`.

---

## Storage Service (Extractor & Embeddings)
- `store.extract_pdfs({ pdf_refs, schema }) → artefacts[]`
- `store.embeddings_upsert({ artefact_id, chunks[] }) → counts`
- `store.embeddings_query({ query, k }) → hits[]`

All tools are **exposed by a single MCP server** (Storage). Internally it may call other processes, but externally it is a normal MCP server.

---

## Security Model
- **Policy before execution** in Gateway (client side): allowlist domains, rate/price caps per run, role‑based tool access.
- **Secrets** remain in the Gateway/Network Service; servers never receive raw API keys unless they own the integration.
- **CAS + citations** ensure provenance and reproducibility.

---

## Migration from “hub” to standard
1. **Delete hub** container and config.
2. In Gateway, implement a **Connection Manager**: open N MCP sessions from config.
3. Replace hub RPCs with **direct tool calls** to the correct session.
4. Update diagrams and docs to reflect client multiplexing.
5. Keep your agents; just call the Gateway’s internal `mcp_client.invoke(server, tool, params)`.

---

## Decision Rationale
- **Standards compliance**: no broker; pure client‑server sessions.
- **Simplicity**: one place (Gateway) owns policy, auth, sessions, and logs.
- **Isolation**: each server has its own transport, backoff, and quotas.
- **Future‑proof**: easy to run agents in a separate worker entrypoint without architectural change.

---

## Appendix: Minimal DB DDL (same as v0.5)
```sql
-- runs/actions/approvals/artefacts/citations as in v0.5
-- (intentionally omitted here for brevity; use your v0.5 migration files)
```
