# Phase 3 Service Architecture Documentation

## 🏗️ Microservices Architecture Overview

This document provides detailed architectural diagrams and service specifications for Phase 3 of the Eunice Research Platform.

## 📊 High-Level Architecture Diagram

```mermaid
graph TB
    subgraph "Client Layer"
        UI[React Frontend :3000]
        Mobile[Mobile App]
        API_Client[External API Clients]
    end

    subgraph "API Gateway Layer"
        Gateway[API Gateway :8001]
        LoadBalancer[Load Balancer]
    end

    subgraph "Authentication & Security"
        Auth[Auth Service :8013]
        RBAC[RBAC Engine]
    end

    subgraph "MCP Coordination Layer"
        MCPServer[Enhanced MCP Server :9000]
        TaskQueue[Task Queue & Registry]
    end

    subgraph "Research Agents (Containerized MCP Clients)"
        ResearchMgr[Research Manager Agent :8002]
        LitSearch[Literature Search Agent :8003]
        Screening[Screening & PRISMA Agent :8004]
        Synthesis[Synthesis & Review Agent :8005]
        Writer[Writer Agent :8006]
        Planning[Planning Agent :8007]
        Executor[Executor Agent :8008]
        Memory[Memory Agent :8009]
    end

    subgraph "Supporting Services"
        Database[Database Service :8011]
        AI[AI Service :8010]
        Notification[Notification Service :8012]
        FileStorage[File Storage Service :8014]
    end

    subgraph "Infrastructure"
        Redis[(Redis Cluster)]
        Postgres[(PostgreSQL Cluster)]
        Vector[(Vector Database)]
        Monitoring[Monitoring Stack]
    end

    UI --> Gateway
    Mobile --> Gateway
    API_Client --> Gateway
    
    Gateway --> Auth
    Gateway --> MCPServer
    Gateway -.Native SQL.-> Postgres
    
    Auth --> RBAC
    Auth --> Database
    
    MCPServer --> TaskQueue
    MCPServer -.WebSocket.-> ResearchMgr
    MCPServer -.WebSocket.-> LitSearch
    MCPServer -.WebSocket.-> Screening
    MCPServer -.WebSocket.-> Synthesis
    MCPServer -.WebSocket.-> Writer
    MCPServer -.WebSocket.-> Planning
    MCPServer -.WebSocket.-> Executor
    MCPServer -.WebSocket.-> Memory
    
    LitSearch --> AI
    LitSearch --> Database
    Screening --> AI
    Screening --> Database
    Synthesis --> AI
    Synthesis --> Memory
    Writer --> Database
    Writer --> FileStorage
    Planning --> AI
    Planning --> Memory
    Executor --> FileStorage
    Memory --> Vector
    
    Database --> Postgres
    AI --> Redis
    Notification --> Redis
    MCPServer --> Redis

    All_Services --> Monitoring
```

## 🔧 Service Specifications

### 1. API Gateway Service

**Purpose**: Unified entry point for all client requests with routing, authentication, and rate limiting. Direct native PostgreSQL connection for READ operations.

```yaml
Service: api-gateway
Port: 8001
Image: eunice/api-gateway:latest
Resources:
  CPU: 500m
  Memory: 1Gi
Environment:
  - AUTH_SERVICE_URL=http://auth-service:8007
  - ORCHESTRATOR_URL=http://research-orchestrator:8002
  - REDIS_URL=redis://redis-cluster:6379
  - DATABASE_READ_URL=postgresql://postgres:password@postgres:5432/eunice
  - CONNECTION_POOL_SIZE=20
Endpoints:
  - GET  /health
  - POST /auth/login
  - GET  /research/projects
  - POST /research/search
  - GET  /queue/status
Dependencies:
  - auth-service
  - research-orchestrator
  - redis-cluster
  - postgres-cluster
Database_Access:
  - READ: Direct native PostgreSQL connection
  - WRITE: Via MCP Server → Database Service
```

### 2. Enhanced MCP Server Service

**Purpose**: Central coordination hub for all research agents with WebSocket communication.

```yaml
Service: mcp-server
Port: 9000
Image: eunice/mcp-server:latest
Resources:
  CPU: 1000m
  Memory: 2Gi
Environment:
  - DATABASE_URL=postgresql://postgres:5432/eunice
  - REDIS_URL=redis://redis-cluster:6379
  - AGENT_REGISTRY_TTL=300
  - WEBSOCKET_MAX_CONNECTIONS=1000
Endpoints:
  - WebSocket /ws (agent connections)
  - GET  /health
  - GET  /agents/status
  - GET  /tasks/queue
  - POST /tasks/dispatch
Dependencies:
  - database-service
  - redis-cluster
```

### 3. Research Manager Agent

**Purpose**: Complex workflow orchestration as containerized MCP client agent.

```yaml
Container: research-manager-agent
Port: 8002
Image: eunice/research-manager-agent:latest
Resources:
  CPU: 800m
  Memory: 1.5Gi
Environment:
  - MCP_SERVER_URL=ws://mcp-server:9000
  - AGENT_TYPE=research_manager
  - DATABASE_URL=postgresql://postgres:5432/eunice
Endpoints:
  - GET  /health
  - GET  /status
Dependencies:
  - mcp-server
  - database-service
MCP_Connection: WebSocket to mcp-server:9000
```

### 4. Literature Search Agent

**Purpose**: Academic literature discovery as containerized MCP client agent.

```yaml
Container: literature-search-agent
Port: 8003
Image: eunice/literature-search-agent:latest
Resources:
  CPU: 800m
  Memory: 1.5Gi
Environment:
  - MCP_SERVER_URL=ws://mcp-server:9000
  - AGENT_TYPE=literature_search
  - SEMANTIC_SCHOLAR_API_KEY=${SEMANTIC_SCHOLAR_KEY}
  - PUBMED_API_KEY=${PUBMED_KEY}
  - ARXIV_API_KEY=${ARXIV_KEY}
Endpoints:
  - GET  /health
  - GET  /status
Dependencies:
  - mcp-server
  - database-service
MCP_Connection: WebSocket to mcp-server:9000
```

### 5. Screening & PRISMA Agent

**Purpose**: Systematic review screening as containerized MCP client agent.

```yaml
Container: screening-prisma-agent
Port: 8004
Image: eunice/screening-prisma-agent:latest
Resources:
  CPU: 1000m
  Memory: 2Gi
Environment:
  - MCP_SERVER_URL=ws://mcp-server:9000
  - AGENT_TYPE=screening_prisma
  - AI_SERVICE_URL=http://ai-service:8010
Endpoints:
  - GET  /health
  - GET  /status
Dependencies:
  - mcp-server
  - ai-service
  - database-service
MCP_Connection: WebSocket to mcp-server:9000
```

### 6. Synthesis & Review Agent

**Purpose**: Evidence synthesis and meta-analysis as containerized MCP client agent.

```yaml
Container: synthesis-review-agent
Port: 8005
Image: eunice/synthesis-review-agent:latest
Resources:
  CPU: 1200m
  Memory: 3Gi
Environment:
  - MCP_SERVER_URL=ws://mcp-server:9000
  - AGENT_TYPE=synthesis_review
  - AI_SERVICE_URL=http://ai-service:8010
  - MEMORY_SERVICE_URL=http://memory-agent:8009
Endpoints:
  - GET  /health
  - GET  /status
Dependencies:
  - mcp-server
  - ai-service
  - memory-agent
  - database-service
MCP_Connection: WebSocket to mcp-server:9000
```

### 7. Writer Agent

**Purpose**: Manuscript generation as containerized MCP client agent.

```yaml
Container: writer-agent
Port: 8006
Image: eunice/writer-agent:latest
Resources:
  CPU: 800m
  Memory: 2Gi
Environment:
  - MCP_SERVER_URL=ws://mcp-server:9000
  - AGENT_TYPE=writer
  - FILE_STORAGE_URL=http://file-storage:8014
Endpoints:
  - GET  /health
  - GET  /status
Dependencies:
  - mcp-server
  - database-service
  - file-storage-service
MCP_Connection: WebSocket to mcp-server:9000
```

### 8. Planning Agent

**Purpose**: Research planning and strategy as containerized MCP client agent.

```yaml
Container: planning-agent
Port: 8007
Image: eunice/planning-agent:latest
Resources:
  CPU: 1000m
  Memory: 2Gi
Environment:
  - MCP_SERVER_URL=ws://mcp-server:9000
  - AGENT_TYPE=planning
  - AI_SERVICE_URL=http://ai-service:8010
  - MEMORY_SERVICE_URL=http://memory-agent:8009
Endpoints:
  - GET  /health
  - GET  /status
Dependencies:
  - mcp-server
  - ai-service
  - memory-agent
  - database-service
MCP_Connection: WebSocket to mcp-server:9000
```

### 9. Executor Agent

**Purpose**: Code execution and data processing as containerized MCP client agent.

```yaml
Container: executor-agent
Port: 8008
Image: eunice/executor-agent:latest
Resources:
  CPU: 2000m
  Memory: 4Gi
Environment:
  - MCP_SERVER_URL=ws://mcp-server:9000
  - AGENT_TYPE=executor
  - SANDBOX_MODE=enabled
  - MAX_EXECUTION_TIME=300
Security:
  - runAsNonRoot: true
  - readOnlyRootFilesystem: true
  - allowPrivilegeEscalation: false
Endpoints:
  - GET  /health
  - GET  /status
Dependencies:
  - mcp-server
  - file-storage-service
MCP_Connection: WebSocket to mcp-server:9000
```

### 10. Memory Agent

**Purpose**: Knowledge base management as containerized MCP client agent.

```yaml
Container: memory-agent
Port: 8009
Image: eunice/memory-agent:latest
Resources:
  CPU: 800m
  Memory: 2Gi
Environment:
  - MCP_SERVER_URL=ws://mcp-server:9000
  - AGENT_TYPE=memory
  - VECTOR_DB_URL=http://vector-database:8080
  - FILE_STORAGE_URL=http://file-storage:8014
Endpoints:
  - GET  /health
  - GET  /status
Dependencies:
  - mcp-server
  - vector-database
  - file-storage-service
  - database-service
MCP_Connection: WebSocket to mcp-server:9000
```

### 11. Authentication Service

**Purpose**: User authentication, authorization, and session management.

```yaml
Service: auth-service
Port: 8013
Image: eunice/auth-service:latest
Resources:
  CPU: 500m
  Memory: 1Gi
Environment:
  - JWT_SECRET=${JWT_SECRET_KEY}
  - DATABASE_URL=postgresql://postgres:5432/eunice
  - REDIS_URL=redis://redis-cluster:6379
  - MFA_ENABLED=true
Endpoints:
  - POST /auth/login
  - POST /auth/logout
  - POST /auth/refresh
  - POST /auth/mfa/setup
  - POST /auth/mfa/verify
Dependencies:
  - database-service
  - redis-cluster
```

### 12. Database Service

**Purpose**: Centralized data access layer with transaction management for WRITE operations. API Gateway connects directly to PostgreSQL for READ operations.

```yaml
Service: database-service
Port: 8011
Image: eunice/database-service:latest
Resources:
  CPU: 1000m
  Memory: 2Gi
Environment:
  - POSTGRES_MASTER_URL=postgresql://postgres-master:5432/eunice
  - POSTGRES_REPLICA_URL=postgresql://postgres-replica:5432/eunice
  - CONNECTION_POOL_SIZE=20
Endpoints:
  - POST /data/create
  - PUT  /data/update
  - DELETE /data/delete
  - GET  /health/database
Dependencies:
  - postgres-cluster
Access_Pattern:
  - PRIMARY: WRITE operations via MCP Server
  - SECONDARY: Complex transactions and data integrity operations
  - NOTE: API Gateway uses direct PostgreSQL connection for READ operations
```

### 10. AI Service

**Purpose**: Multi-provider AI model access with load balancing and cost optimization.

```yaml
Service: ai-service
Port: 8010
Image: eunice/ai-service:latest
Resources:
  CPU: 800m
  Memory: 1.5Gi
Environment:
  - OPENAI_API_KEY=${OPENAI_KEY}
  - ANTHROPIC_API_KEY=${ANTHROPIC_KEY}
  - XAI_API_KEY=${XAI_KEY}
  - REDIS_URL=redis://redis-cluster:6379
Endpoints:
  - POST /ai/chat/completions
  - POST /ai/embeddings
  - GET  /ai/models/available
  - GET  /ai/usage/statistics
Dependencies:
  - redis-cluster
```

### 13. Notification Service

**Purpose**: Real-time notifications, WebSocket management, and team collaboration.

```yaml
Service: notification-service
Port: 8012
Image: eunice/notification-service:latest
Resources:
  CPU: 500m
  Memory: 1Gi
Environment:
  - REDIS_URL=redis://redis-cluster:6379
  - AUTH_SERVICE_URL=http://auth-service:8007
  - EMAIL_SMTP_HOST=${SMTP_HOST}
Endpoints:
  - WebSocket /ws/notifications
  - POST /notifications/send
  - GET  /notifications/history
  - POST /notifications/preferences
Dependencies:
  - redis-cluster
  - auth-service
```

## 🔄 Service Communication Patterns

### 1. MCP-Based Agent Communication (WebSocket)

```mermaid
sequenceDiagram
    participant Client
    participant Gateway as API Gateway
    participant Auth as Auth Service
    participant MCP as MCP Server
    participant ResearchMgr as Research Manager Agent
    participant Literature as Literature Agent

    Client->>Gateway: POST /research/search
    Gateway->>Auth: Validate JWT token
    Auth-->>Gateway: Token valid + user permissions
    Gateway->>MCP: Send research request
    MCP->>ResearchMgr: Delegate to Research Manager Agent
    ResearchMgr->>MCP: Request literature search task
    MCP->>Literature: Route to Literature Agent
    Literature-->>MCP: Search results
    MCP-->>ResearchMgr: Forward results
    ResearchMgr-->>MCP: Formatted response
    MCP-->>Gateway: Complete response
    Gateway-->>Client: Search results
```

### 2. Asynchronous Task Processing (MCP + Redis)

```mermaid
sequenceDiagram
    participant MCP as MCP Server
    participant Queue as Redis Task Queue
    participant Literature as Literature Agent
    participant Database as Database Service

    MCP->>Queue: Enqueue literature search task
    MCP->>Literature: Notify via WebSocket
    Literature->>Queue: Dequeue task details
    Literature->>Literature: Process search
    Literature->>Database: Store results
    Literature->>MCP: Send completion via WebSocket
    MCP->>Queue: Update task status
```

### 3. Real-time Status Updates (WebSocket)

```mermaid
sequenceDiagram
    participant Client
    participant Gateway as API Gateway
    participant MCP as MCP Server
    participant Literature as Literature Agent

    Client->>Gateway: Connect WebSocket for updates
    Gateway->>MCP: Subscribe to task updates
    MCP->>Literature: Start long-running search task
    Literature->>MCP: Progress update (25%) via WebSocket
    MCP-->>Gateway: Forward progress update
    Gateway-->>Client: WebSocket: "Search 25% complete"
    Literature->>MCP: Progress update (75%) via WebSocket
    MCP-->>Gateway: Forward progress update
    Gateway-->>Client: WebSocket: "Search 75% complete"
    Literature->>MCP: Task complete via WebSocket
    MCP-->>Gateway: Forward completion
    Gateway-->>Client: WebSocket: "Search complete"
```

## � Inter-Service Communication Protocols

### Database Access Patterns

#### READ Operations (API Gateway → PostgreSQL)

- **Protocol**: Native PostgreSQL wire protocol (TCP/5432)
- **Connection**: Direct asyncpg connection pool (20 connections)
- **Purpose**: High-performance read queries, user-facing data retrieval
- **Authentication**: Database credentials via environment variables
- **Connection Management**: Connection pooling with health checks
- **Transaction Isolation**: Read Committed for consistency

**Performance Benefits:**

- Eliminates HTTP REST API overhead for read operations
- Reduces latency by 50-70% compared to HTTP intermediary
- Native PostgreSQL binary protocol is more efficient
- Direct connection pooling with configurable pool sizes
- Optimized for high-frequency read operations

#### WRITE Operations (MCP Server → Database Service → PostgreSQL)

- **Protocol**: HTTP REST API → Native PostgreSQL
- **Purpose**: Data integrity, complex transactions, audit trails
- **Flow**: Agent → MCP Server → Database Service → PostgreSQL
- **Transaction Management**: ACID compliance with rollback support
- **Validation**: Schema validation and business rule enforcement

**Architecture Benefits:**

- Centralized write validation and business logic
- Audit trail and transaction logging
- Schema migration management
- Data consistency enforcement
- Rollback and recovery capabilities

### MCP Protocol (Model Context Protocol)

- **Primary Channel**: WebSocket connections between MCP Server and Agent containers
- **Protocol**: MCP JSON-RPC over WebSocket
- **Message Format**: JSON-RPC 2.0 with MCP extensions
- **Connection Management**: Persistent WebSocket with automatic reconnection
- **Load Balancing**: Round-robin across agent instances
- **Timeout**: 30 seconds for standard operations, 300 seconds for long-running tasks

#### Example MCP Message Flow

```json
// Request from MCP Server to Literature Agent
{
  "jsonrpc": "2.0",
  "id": "task_12345",
  "method": "literature/search",
  "params": {
    "query": "neural networks attention mechanisms",
    "max_results": 50,
    "databases": ["arxiv", "pubmed", "google_scholar"]
  }
}

// Response from Literature Agent to MCP Server
{
  "jsonrpc": "2.0",
  "id": "task_12345",
  "result": {
    "status": "completed",
    "results_count": 47,
    "cache_key": "lit_search_abc123",
    "next_action": "summary_generation"
  }
}
```

### HTTP/REST (External API Access)

- **Purpose**: Client-facing API Gateway and external service integration
- **Format**: JSON API with OpenAPI 3.0 specification
- **Authentication**: JWT tokens with role-based access control
- **Rate Limiting**: 1000 requests per hour per user
- **Versioning**: URI versioning (/api/v1/, /api/v2/)

### Redis Message Queue

- **Purpose**: Asynchronous task coordination and status updates
- **Pattern**: Pub/Sub for real-time updates, Task Queue for work distribution
- **Serialization**: JSON with compression for large payloads
- **Persistence**: Redis AOF for task durability
- **Clustering**: Redis Sentinel for high availability

### WebSocket (Real-time Updates)

- **Client Communication**: Real-time progress updates and notifications
- **Message Format**: JSON with event types and data payloads
- **Connection Management**: Automatic reconnection with exponential backoff
- **Authentication**: JWT token in connection header
- **Heartbeat**: 30-second ping/pong for connection health

## �🐳 Docker Compose Configuration

```yaml
version: '3.8'

services:
  # API Gateway Layer
  api-gateway:
    build: ./services/api-gateway
    ports: ["8001:8001"]
    environment:
      - AUTH_SERVICE_URL=http://auth-service:8013
      - MCP_SERVER_URL=ws://mcp-server:9000
      - DATABASE_READ_URL=postgresql://postgres:password@postgres:5432/eunice
      - CONNECTION_POOL_SIZE=20
      - CONNECTION_POOL_MIN_SIZE=5
    depends_on: [auth-service, mcp-server, postgres]
    networks: [eunice-network]

  # Authentication
  auth-service:
    build: ./services/auth-service
    ports: ["8013:8013"]
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/eunice
      - REDIS_URL=redis://redis:6379
    depends_on: [postgres, redis]
    networks: [eunice-network]

  # Core MCP Server
  mcp-server:
    build: ./services/mcp-server
    ports: ["9000:9000"]
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/eunice
      - REDIS_URL=redis://redis:6379
      - AUTH_SERVICE_URL=http://auth-service:8013
    depends_on: [postgres, redis, auth-service]
    networks: [eunice-network]

  # Agent Services (MCP Clients)
  literature-agent:
    build: ./services/literature-agent
    environment:
      - MCP_SERVER_URL=ws://mcp-server:9000
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/eunice
    depends_on: [mcp-server, postgres]
    networks: [eunice-network]

  screening-agent:
    build: ./services/screening-agent
    environment:
      - MCP_SERVER_URL=ws://mcp-server:9000
      - AI_SERVICE_URL=http://ai-service:8010
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/eunice
    depends_on: [mcp-server, ai-service, postgres]
    networks: [eunice-network]

  synthesis-agent:
    build: ./services/synthesis-agent
    environment:
      - MCP_SERVER_URL=ws://mcp-server:9000
      - AI_SERVICE_URL=http://ai-service:8010
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/eunice
    depends_on: [mcp-server, ai-service, postgres]
    networks: [eunice-network]

  writer-agent:
    build: ./services/writer-agent
    environment:
      - MCP_SERVER_URL=ws://mcp-server:9000
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/eunice
      - FILE_STORAGE_URL=http://file-storage:8014
    depends_on: [mcp-server, postgres, file-storage]
    networks: [eunice-network]

  planning-agent:
    build: ./services/planning-agent
    environment:
      - MCP_SERVER_URL=ws://mcp-server:9000
      - AI_SERVICE_URL=http://ai-service:8010
    depends_on: [mcp-server, ai-service]
    networks: [eunice-network]

  executor-agent:
    build: ./services/executor-agent
    environment:
      - MCP_SERVER_URL=ws://mcp-server:9000
      - FILE_STORAGE_URL=http://file-storage:8014
      - SANDBOX_MODE=enabled
    depends_on: [mcp-server, file-storage]
    networks: [eunice-network]

  memory-agent:
    build: ./services/memory-agent
    environment:
      - MCP_SERVER_URL=ws://mcp-server:9000
      - VECTOR_DB_URL=http://vector-database:8080
      - FILE_STORAGE_URL=http://file-storage:8014
    depends_on: [mcp-server, vector-database, file-storage]
    networks: [eunice-network]

  research-manager-agent:
    build: ./services/research-manager-agent
    environment:
      - MCP_SERVER_URL=ws://mcp-server:9000
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/eunice
    depends_on: [mcp-server, postgres]
    networks: [eunice-network]

  # Supporting Services
  database-service:
    build: ./services/database-service
    ports: ["8011:8011"]
    environment:
      - POSTGRES_URL=postgresql://postgres:password@postgres:5432/eunice
    depends_on: [postgres]
    networks: [eunice-network]

  ai-service:
    build: ./services/ai-service
    ports: ["8010:8010"]
    environment:
      - REDIS_URL=redis://redis:6379
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on: [redis]
    networks: [eunice-network]

  notification-service:
    build: ./services/notification-service
    ports: ["8012:8012"]
    environment:
      - REDIS_URL=redis://redis:6379
      - AUTH_SERVICE_URL=http://auth-service:8013
    depends_on: [redis, auth-service]
    networks: [eunice-network]

  file-storage:
    build: ./services/file-storage
    ports: ["8014:8014"]
    environment:
      - STORAGE_PATH=/app/storage
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/eunice
    volumes: ["file_storage:/app/storage"]
    depends_on: [postgres]
    networks: [eunice-network]

  # Infrastructure
  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=eunice
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes: ["postgres_data:/var/lib/postgresql/data"]
    networks: [eunice-network]

  redis:
    image: redis:7-alpine
    volumes: ["redis_data:/data"]
    networks: [eunice-network]

  vector-database:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]
    volumes: ["qdrant_data:/qdrant/storage"]
    networks: [eunice-network]

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
  file_storage:

networks:
  eunice-network:
    driver: bridge
```

## 🎯 Service Scaling Configuration

### Horizontal Pod Autoscaler (HPA) for Kubernetes

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: literature-agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: literature-agent
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Load Balancing Strategy

```yaml
apiVersion: v1
kind: Service
metadata:
  name: literature-agent-service
spec:
  selector:
    app: literature-agent
  ports:
  - port: 8003
    targetPort: 8003
  type: LoadBalancer
  sessionAffinity: None  # Round-robin load balancing
```

## 📊 Performance Monitoring Configuration

### Prometheus Metrics Configuration

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
    scrape_configs:
    - job_name: 'eunice-services'
      static_configs:
      - targets:
        - 'api-gateway:8001'
        - 'research-orchestrator:8002'
        - 'literature-search:8003'
        - 'screening-prisma:8004'
        - 'synthesis-review:8005'
        - 'writer-agent:8006'
        - 'planning-agent:8007'
        - 'executor-agent:8008'
        - 'memory-agent:8009'
      metrics_path: /metrics
      scrape_interval: 10s
```

### Grafana Dashboard Configuration

```json
{
  "dashboard": {
    "title": "Eunice Microservices Overview",
    "panels": [
      {
        "title": "Service Response Times",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, http_request_duration_seconds_bucket)",
            "legendFormat": "95th Percentile"
          }
        ]
      },
      {
        "title": "Service Availability",
        "type": "stat",
        "targets": [
          {
            "expr": "up{job='eunice-services'}",
            "legendFormat": "{{instance}}"
          }
        ]
      },
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{service}}"
          }
        ]
      }
    ]
  }
}
```

---

**Architecture Status**: Phase 3 Design Complete  
**Implementation**: Ready for Development  
**Services**: 10 microservices + infrastructure  
**Scalability**: Kubernetes-ready with auto-scaling

---

*This architecture documentation provides the technical foundation for implementing Phase 3 microservices transition.*
