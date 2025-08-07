# Eunice Research Platform - Architecture Recommendations

**Version**: 0.1  
**Date**: August 07, 2025  
**Target Audience**: Application Architects, Senior Software Developers  
**Purpose**: Recommendations to enhance the Eunice Research Platform (v0.3.1) architecture, addressing component grouping, communication patterns, and outstanding issues.

## Executive Summary

The Eunice Research Platform is a robust microservices-based system with a strong foundation for research automation. These recommendations address outstanding issues (routing and persistence), optimize component grouping, and enhance communication patterns. Key proposals include splitting the MCP Server, adding an Internet Access Service, and adopting gRPC and Kafka for scalability.

## Strengths of Current Architecture

1. **Modular Microservices**: 10+ containerized services ensure scalability and independent development.
2. **MCP Protocol**: WebSocket-based JSON-RPC 2.0 enables real-time agent coordination.
3. **Dual Database Access**: Direct PostgreSQL READs and MCP-routed WRITEs balance performance and integrity.
4. **Security**: JWT with 2FA and RBAC provides enterprise-grade protection.
5. **Hierarchical Data Model**: Projects → Topics → Plans → Tasks supports complex research workflows.
6. **Monitoring and Scalability**: Health checks, circuit breakers, and Kubernetes HPA ensure reliability.
7. **Persona System**: Specialized personas enhance domain-specific reasoning.

## Recommendations

### 1. Component Grouping and Function Allocation

#### MCP Server
- **Current**: Handles task decomposition, agent coordination, AI routing, and result aggregation.
- **Recommendation**: Split into two sub-components:
  - **MCP Orchestrator**: Manages task decomposition, workflow orchestration, and result aggregation.
  - **MCP Router**: Handles WebSocket communication, agent registration, and AI service routing.
- **Rationale**: Reduces complexity and prevents bottlenecks under high load (e.g., 1000+ messages/second).
- **Implementation**:
  - Deploy as separate Docker containers:
    - Orchestrator: `eunice/mcp-orchestrator:latest`, 1000m CPU, 2Gi Memory, port 9000.
    - Router: `eunice/mcp-router:latest`, 500m CPU, 1Gi Memory, port 9001.
  - Use Redis channel for internal communication.
  - Update Docker Compose and Kubernetes configs.

#### Research Agents
- **Current**: Eight specialized agents (e.g., Research Manager, Literature Search) operate independently via MCP.
- **Recommendation**: Add an **Agent Coordinator Service** to manage cross-agent dependencies (e.g., Literature Search before Screening & PRISMA).
- **Rationale**: Offloads dependency management from Research Manager, improving scalability for complex workflows.
- **Implementation**:
  - Deploy as `eunice/agent-coordinator:latest`, 500m CPU, 512Mi Memory.
  - Use Kafka topics (e.g., `literature-tasks`, `synthesis-tasks`) for dependency tracking.
  - Update Research Manager to delegate dependency logic to Coordinator.

#### Utility Services
- **Current**: Includes Database, Notification, File Storage, and Authentication Services.
- **Recommendation**: Add an **Internet Access Service** for external API calls (e.g., Semantic Scholar, PubMed).
- **Rationale**: Centralizes rate limiting, caching, and error handling, aligning with security policies.
- **Implementation**:
  - Deploy as `eunice/internet-access:latest`, port 8015.
  - Route requests via MCP (`internet_request` message type).
  - Cache responses in Redis (24-hour TTL).
  - Use `httpx` for async HTTP requests and `redis-py` for caching.

#### Database Service
- **Current**: Handles WRITE operations via MCP with a hierarchical data model.
- **Recommendation**: Add a **Schema Validation Layer** to address persistence issues.
- **Rationale**: Ensures data integrity and logs validation errors for debugging.
- **Implementation**:
  - Use FastAPI middleware to validate JSONB metadata.
  - Log errors to Monitoring Stack (e.g., ELK).
  - Example validation:
    ```python
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel

    class MetadataSchema(BaseModel):
        key: str
        value: str

    async def validate_metadata(metadata: dict):
        try:
            [MetadataSchema(**item) for item in metadata]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    ```

### 2. Communication Patterns

#### Optimize WebSocket Usage
- **Current**: WebSocket for all agent communication.
- **Recommendation**: Introduce gRPC for high-throughput tasks (e.g., task delegation, result aggregation).
- **Rationale**: gRPC reduces WebSocket overhead and supports bidirectional streaming.
- **Implementation**:
  - Add gRPC server to MCP Router (`mcp-router:9001`).
  - Update agents with gRPC clients (e.g., `grpcio` in Python).
  - Example gRPC proto:
    ```proto
    service MCPRouter {
        rpc DelegateTask(TaskRequest) returns (TaskResponse);
    }
    message TaskRequest {
        string task_id = 1;
        string agent_type = 2;
        string payload = 3;
    }
    message TaskResponse {
        string status = 1;
        string result = 2;
    }
    ```

#### Internet Access Communication
- **Current**: Literature Search Agent directly accesses external APIs.
- **Recommendation**: Route all external API calls through Internet Access Service via MCP.
- **Rationale**: Ensures compliance with security policies and centralizes rate limiting.
- **Implementation**:
  - Define MCP `internet_request` message:
    ```json
    {
      "type": "internet_request",
      "url": "https://api.semanticscholar.org/v1/paper",
      "method": "GET",
      "headers": {"Authorization": "Bearer <token>"},
      "cache_ttl": 86400
    }
    ```
  - Internet Access Service processes requests and caches responses in Redis.

#### Asynchronous Task Handling
- **Current**: Task Queue uses Redis, but queue technology is unspecified.
- **Recommendation**: Adopt Kafka for long-running tasks (e.g., literature searches).
- **Rationale**: Kafka’s durability and partitioning support high-throughput, event-driven workflows.
- **Implementation**:
  - Deploy Kafka cluster (`kafka:9092`) with topics per agent.
  - Update MCP Orchestrator to produce/consume Kafka messages.
  - Example Kafka producer:
    ```python
    from kafka import KafkaProducer
    producer = KafkaProducer(bootstrap_servers='kafka:9092')
    producer.send('literature-tasks', value=b'{"task_id": "123", "query": "AI ethics"}')
    ```

### 3. Addressing Outstanding Issues

#### Individual Resource Routing
- **Issue**: GET/PUT/DELETE operations for Research Plans and Tasks affected by routing patterns.
- **Recommendation**:
  - Audit API Gateway routes for `/research/plans/{id}` and `/research/tasks/{id}`.
  - Validate `id` parameters (UUID format).
  - Add debug endpoint (`/debug/routes`) to trace request paths.
- **Implementation**:
  - Update FastAPI routes:
    ```python
    from fastapi import APIRouter, HTTPException
    router = APIRouter()
    
    @router.get("/research/plans/{plan_id}")
    async def get_plan(plan_id: str):
        if not is_valid_uuid(plan_id):
            raise HTTPException(status_code=400, detail="Invalid UUID")
        # Route to MCP
    ```

#### Update/Delete Persistence
- **Issue**: Success responses returned, but changes don’t persist.
- **Recommendation**:
  - Add transaction validation in Database Service.
  - Log transaction outcomes to ELK or Redis.
  - Implement retries for transient failures.
- **Implementation**:
  - Use explicit transactions:
    ```python
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("UPDATE research_plans SET status = $1 WHERE id = $2", "updated", plan_id)
    ```
  - Log failures:
    ```python
    import logging
    logging.error(f"Transaction failed for plan_id {plan_id}: {str(e)}")
    ```

### 4. Additional Enhancements

#### Vector Database Integration
- **Current**: Memory Service uses Qdrant for semantic search.
- **Recommendation**: Expand vector search to Literature and Synthesis Agents.
- **Implementation**:
  - Store paper abstracts as embeddings in Qdrant.
  - Define MCP `vector_search` message:
    ```json
    {
      "type": "vector_search",
      "query": "AI ethics implications",
      "top_k": 10
    }
    ```

#### Monitoring Improvements
- **Current**: Monitoring Stack exists but lacks detail.
- **Recommendation**: Deploy Prometheus/Grafana for metrics and dashboards.
- **Implementation**:
  - Configure Prometheus to scrape `/health` endpoints every 10s.
  - Create Grafana dashboards for API response times, MCP throughput, and query latency.

#### Persona System Integration
- **Current**: Personas are standalone.
- **Recommendation**: Integrate into Research Manager for dynamic task assignment.
- **Implementation**:
  - Add `persona` field to MCP task messages:
    ```json
    {
      "task_id": "123",
      "persona": "Bioethics Specialist",
      "query": "Ethical implications of AI"
    }
    ```

## Revised Architecture Diagram

```mermaid
graph TB
    subgraph "Client Layer"
        UI[React Frontend :3000]
        Mobile[Mobile Apps]
        API_Client[External Integrations]
    end

    subgraph "API & Security Layer"
        Gateway[API Gateway :8001]
        Auth[Auth Service :8013]
        LoadBalancer[Load Balancer]
    end

    subgraph "MCP Coordination Layer"
        MCP_Orch[MCP Orchestrator :9000]
        MCP_Router[MCP Router :9001]
        TaskQueue[Task Queue & Registry (Kafka)]
        AI[AI Service :9002]
    end

    subgraph "Research Agents (MCP Clients)"
        ResearchMgr[Research Manager :8002]
        Literature[Literature Search :8003]
        Screening[Screening & PRISMA :8004]
        Synthesis[Synthesis & Review :8005]
        Writer[Writer Agent :8006]
        Planning[Planning Agent :8007]
        Executor[Executor Agent :8008]
        Memory[Memory Service :8009]
        Coordinator[Agent Coordinator :8010]
    end

    subgraph "Supporting Services"
        Database[Database Service :8011]
        Notification[Notification Service :8012]
        FileStorage[File Storage :8014]
        Internet[Internet Access Service :8015]
    end

    subgraph "Infrastructure"
        Redis[(Redis Cluster)]
        Postgres[(PostgreSQL)]
        Vector[(Qdrant)]
        Kafka[(Kafka Cluster)]
        Monitor[Prometheus/Grafana]
    end

    UI --> Gateway
    Mobile --> Gateway
    API_Client --> Gateway
    
    Gateway --> Auth
    Gateway --> MCP_Orch
    Gateway -.Direct SQL.-> Postgres
    
    Auth --> Database
    MCP_Orch --> TaskQueue
    MCP_Orch <--> MCP_Router
    MCP_Router <--> AI
    MCP_Router -.WebSocket/gRPC.-> ResearchMgr
    MCP_Router -.WebSocket/gRPC.-> Literature
    MCP_Router -.WebSocket/gRPC.-> Screening
    MCP_Router -.WebSocket/gRPC.-> Synthesis
    MCP_Router -.WebSocket/gRPC.-> Writer
    MCP_Router -.WebSocket/gRPC.-> Planning
    MCP_Router -.WebSocket/gRPC.-> Executor
    MCP_Router -.WebSocket/gRPC.-> Memory
    MCP_Router -.WebSocket/gRPC.-> Coordinator
    MCP_Router --> Internet
    
    All_Agents --> Database
    Literature --> Internet
    Writer --> FileStorage
    Executor --> FileStorage
    Memory --> Vector
    
    Database --> Postgres
    AI --> Redis
    Notification --> Redis
    MCP_Orch --> Redis
    TaskQueue --> Kafka
    All_Services --> Monitor
```

## Implementation Plan

### Short-Term (1-2 Weeks)
- **Fix Routing Issues**:
  - Audit API Gateway routes for `/research/plans/{id}` and `/research/tasks/{id}`.
  - Add debug endpoint (`/debug/routes`).
- **Fix Persistence Issues**:
  - Implement transaction validation in Database Service.
  - Log failures to ELK/Redis.
  - Add retry mechanism (3 attempts).
- **Deploy Internet Access Service**:
  - Create Docker container (`eunice/internet-access:latest`).
  - Define `internet_request` MCP message.
  - Update Literature Search Agent to use MCP routing.

### Medium-Term (3-4 Weeks)
- **Split MCP Server**:
  - Deploy Orchestrator and Router containers.
  - Update Docker Compose/Kubernetes configs.
- **Introduce gRPC**:
  - Add gRPC server to MCP Router.
  - Update agents with gRPC clients.
- **Deploy Kafka**:
  - Set up Kafka cluster with agent-specific topics.
  - Update MCP Orchestrator for Kafka integration.

### Long-Term (1-2 Months)
- **Vector Search Expansion**: Enable for Literature and Synthesis Agents.
- **Monitoring**: Deploy Prometheus/Grafana with dashboards.
- **Persona Integration**: Add `persona` field to MCP tasks for dynamic assignment.

## Conclusion

These recommendations enhance the Eunice Research Platform by addressing routing and persistence issues, optimizing communication with gRPC and Kafka, and introducing an Internet Access Service. Splitting the MCP Server and adding an Agent Coordinator improve scalability, while vector search and monitoring enhancements boost functionality. These changes align with the platform’s goals of robust agent coordination, secure external access, and reliable data management.