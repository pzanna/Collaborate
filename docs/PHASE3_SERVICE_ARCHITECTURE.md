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
        Auth[Auth Service :8007]
        RBAC[RBAC Engine]
    end

    subgraph "Core Services"
        Orchestrator[Research Orchestrator :8002]
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
        FileStorage[File Storage Service :8013]
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
    Gateway --> LitSearch
    Gateway --> Screening
    Gateway --> Synthesis
    Gateway --> Writer
    Gateway --> Planning
    Gateway --> Executor
    Gateway --> Memory
    
    Auth --> RBAC
    Auth --> Database
    
    Orchestrator --> LitSearch
    Orchestrator --> Screening
    Orchestrator --> Synthesis
    Orchestrator --> Writer
    Orchestrator --> Planning
    Orchestrator --> Executor
    Orchestrator --> Memory
    
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

    All_Services --> Monitoring
```

## 🔧 Service Specifications

### 1. API Gateway Service

**Purpose**: Unified entry point for all client requests with routing, authentication, and rate limiting.

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
```

### 2. Research Orchestrator Service

**Purpose**: Workflow coordination and task delegation across all research agents.

```yaml
Service: research-orchestrator
Port: 8002
Image: eunice/research-orchestrator:latest
Resources:
  CPU: 1000m
  Memory: 2Gi
Environment:
  - DATABASE_URL=postgresql://postgres:5432/eunice
  - LITERATURE_SEARCH_URL=http://literature-search:8003
  - SCREENING_PRISMA_URL=http://screening-prisma:8004
  - SYNTHESIS_REVIEW_URL=http://synthesis-review:8005
  - WRITER_AGENT_URL=http://writer-agent:8006
  - PLANNING_AGENT_URL=http://planning-agent:8007
  - EXECUTOR_AGENT_URL=http://executor-agent:8008
Endpoints:
  - POST /workflows/create
  - GET  /workflows/{id}/status
  - POST /workflows/{id}/execute
  - DELETE /workflows/{id}/cancel
Dependencies:
  - database-service
  - literature-search
  - screening-prisma
  - synthesis-review
  - writer-agent
  - planning-agent
  - executor-agent
```

### 3. Literature Search Agent Service

**Purpose**: Discovery and collection of bibliographic records from multiple academic sources.

```yaml
Service: literature-search
Port: 8003
Image: eunice/literature-search:latest
Resources:
  CPU: 800m
  Memory: 1.5Gi
Environment:
  - SEMANTIC_SCHOLAR_API_KEY=${SEMANTIC_SCHOLAR_KEY}
  - PUBMED_API_KEY=${PUBMED_KEY}
  - ARXIV_API_KEY=${ARXIV_KEY}
  - DATABASE_URL=postgresql://postgres:5432/eunice
Endpoints:
  - POST /search/execute
  - GET  /search/{id}/report
  - POST /search/deduplicate
  - GET  /sources/available
Dependencies:
  - database-service
```

### 4. Screening & PRISMA Agent Service

**Purpose**: Systematic review screening and PRISMA-compliant audit trails.

```yaml
Service: screening-prisma
Port: 8004
Image: eunice/screening-prisma:latest
Resources:
  CPU: 1000m
  Memory: 2Gi
Environment:
  - AI_SERVICE_URL=http://ai-service:8010
  - DATABASE_URL=postgresql://postgres:5432/eunice
Endpoints:
  - POST /prisma/sessions/create
  - POST /screening/batch
  - GET  /prisma/{session_id}/flowchart
  - GET  /screening/{session_id}/decisions
Dependencies:
  - ai-service
  - database-service
```

### 5. Synthesis & Review Agent Service

**Purpose**: Data extraction, meta-analysis, and evidence synthesis.

```yaml
Service: synthesis-review
Port: 8005
Image: eunice/synthesis-review:latest
Resources:
  CPU: 1200m
  Memory: 3Gi
Environment:
  - AI_SERVICE_URL=http://ai-service:8010
  - MEMORY_SERVICE_URL=http://memory-agent:8009
  - DATABASE_URL=postgresql://postgres:5432/eunice
Endpoints:
  - POST /outcomes/extract
  - POST /meta-analysis/perform
  - POST /evidence-tables/generate
  - POST /synthesis/narrative
Dependencies:
  - ai-service
  - memory-agent
  - database-service
```

### 6. Writer Agent Service

**Purpose**: Manuscript generation and formatting for scholarly publications.

```yaml
Service: writer-agent
Port: 8006
Image: eunice/writer-agent:latest
Resources:
  CPU: 800m
  Memory: 2Gi
Environment:
  - DATABASE_URL=postgresql://postgres:5432/eunice
  - FILE_STORAGE_URL=http://file-storage:8013
Endpoints:
  - POST /manuscripts/draft
  - PUT  /manuscripts/{id}/revise
  - GET  /manuscripts/{id}/export
  - POST /citations/validate
Dependencies:
  - database-service
  - file-storage-service
```

### 7. Planning Agent Service

**Purpose**: Research planning, task synthesis, and resource requirement analysis.

```yaml
Service: planning-agent
Port: 8007
Image: eunice/planning-agent:latest
Resources:
  CPU: 1000m
  Memory: 2Gi
Environment:
  - AI_SERVICE_URL=http://ai-service:8010
  - MEMORY_SERVICE_URL=http://memory-agent:8009
  - DATABASE_URL=postgresql://postgres:5432/eunice
Endpoints:
  - POST /plans/create
  - GET  /plans/{id}/details
  - POST /plans/{id}/execute
  - GET  /plans/{id}/progress
Dependencies:
  - ai-service
  - memory-agent
  - database-service
```

### 8. Executor Agent Service

**Purpose**: Code execution, data processing, and automated task execution.

```yaml
Service: executor-agent
Port: 8008
Image: eunice/executor-agent:latest
Resources:
  CPU: 2000m
  Memory: 4Gi
Environment:
  - SANDBOX_MODE=enabled
  - FILE_STORAGE_URL=http://file-storage:8013
  - MAX_EXECUTION_TIME=300
Security:
  - runAsNonRoot: true
  - readOnlyRootFilesystem: true
  - allowPrivilegeEscalation: false
Endpoints:
  - POST /execute/code
  - GET  /execute/{id}/status
  - GET  /execute/{id}/results
  - DELETE /execute/{id}/cancel
Dependencies:
  - file-storage-service
```

### 9. Memory Agent Service

**Purpose**: Knowledge base management, document storage, and semantic search.

```yaml
Service: memory-agent
Port: 8009
Image: eunice/memory-agent:latest
Resources:
  CPU: 800m
  Memory: 2Gi
Environment:
  - VECTOR_DB_URL=http://vector-database:8080
  - FILE_STORAGE_URL=http://file-storage:8013
  - DATABASE_URL=postgresql://postgres:5432/eunice
Endpoints:
  - POST /knowledge/store
  - GET  /knowledge/search
  - POST /documents/upload
  - GET  /documents/{id}/content
Dependencies:
  - vector-database
  - file-storage-service
  - database-service
```

### 7. Authentication Service

**Purpose**: User authentication, authorization, and session management.

```yaml
Service: auth-service
Port: 8007
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

### 8. Database Service

**Purpose**: Centralized data access layer with transaction management.

```yaml
Service: database-service
Port: 8008
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
  - GET  /data/read
  - PUT  /data/update
  - DELETE /data/delete
  - GET  /health/database
Dependencies:
  - postgres-cluster
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

### 10. Notification Service

**Purpose**: Real-time notifications, WebSocket management, and team collaboration.

```yaml
Service: notification-service
Port: 8010
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

### 1. Synchronous Communication (HTTP/REST)

```mermaid
sequenceDiagram
    participant Client
    participant Gateway as API Gateway
    participant Auth as Auth Service
    participant Orchestrator as Research Orchestrator
    participant Literature as Literature Agent

    Client->>Gateway: POST /research/search
    Gateway->>Auth: Validate JWT token
    Auth-->>Gateway: Token valid + user permissions
    Gateway->>Orchestrator: Route search request
    Orchestrator->>Literature: Execute literature search
    Literature-->>Orchestrator: Search results
    Orchestrator-->>Gateway: Formatted response
    Gateway-->>Client: Search results
```

### 2. Asynchronous Communication (Message Queue)

```mermaid
sequenceDiagram
    participant Orchestrator as Research Orchestrator
    participant Queue as Redis Queue
    participant Literature as Literature Agent
    participant Database as Database Service

    Orchestrator->>Queue: Enqueue literature search task
    Literature->>Queue: Dequeue task
    Literature->>Literature: Process search
    Literature->>Database: Store results
    Literature->>Queue: Publish completion event
    Orchestrator->>Queue: Receive completion notification
```

### 3. Real-time Communication (WebSocket)

```mermaid
sequenceDiagram
    participant Client
    participant Notification as Notification Service
    participant Orchestrator as Research Orchestrator
    participant Literature as Literature Agent

    Client->>Notification: Connect WebSocket
    Orchestrator->>Literature: Start long-running search
    Literature->>Notification: Progress update (25%)
    Notification-->>Client: WebSocket: "Search 25% complete"
    Literature->>Notification: Progress update (75%)
    Notification-->>Client: WebSocket: "Search 75% complete"
    Literature->>Notification: Task complete
    Notification-->>Client: WebSocket: "Search complete"
```

## 🐳 Docker Compose Configuration

```yaml
version: '3.8'

services:
  # API Gateway Layer
  api-gateway:
    build: ./services/api-gateway
    ports: ["8001:8001"]
    environment:
      - AUTH_SERVICE_URL=http://auth-service:8007
      - ORCHESTRATOR_URL=http://research-orchestrator:8002
    depends_on: [auth-service, research-orchestrator]
    networks: [eunice-network]

  # Authentication
  auth-service:
    build: ./services/auth-service
    ports: ["8007:8007"]
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/eunice
      - REDIS_URL=redis://redis:6379
    depends_on: [postgres, redis]
    networks: [eunice-network]

  # Core Services
  research-orchestrator:
    build: ./services/research-orchestrator
    ports: ["8002:8002"]
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/eunice
      - LITERATURE_SEARCH_URL=http://literature-search:8003
      - SCREENING_PRISMA_URL=http://screening-prisma:8004
      - SYNTHESIS_REVIEW_URL=http://synthesis-review:8005
      - WRITER_AGENT_URL=http://writer-agent:8006
    depends_on: [postgres, literature-search, screening-prisma, synthesis-review, writer-agent]
    networks: [eunice-network]

  literature-search:
    build: ./services/literature-search
    ports: ["8003:8003"]
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/eunice
    depends_on: [postgres]
    networks: [eunice-network]

  screening-prisma:
    build: ./services/screening-prisma
    ports: ["8004:8004"]
    environment:
      - AI_SERVICE_URL=http://ai-service:8010
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/eunice
    depends_on: [ai-service, postgres]
    networks: [eunice-network]

  synthesis-review:
    build: ./services/synthesis-review
    ports: ["8005:8005"]
    environment:
      - AI_SERVICE_URL=http://ai-service:8010
      - MEMORY_SERVICE_URL=http://memory-agent:8009
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/eunice
    depends_on: [ai-service, memory-agent, postgres]
    networks: [eunice-network]

  writer-agent:
    build: ./services/writer-agent
    ports: ["8006:8006"]
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/eunice
      - FILE_STORAGE_URL=http://file-storage:8013
    depends_on: [postgres, file-storage]
    networks: [eunice-network]

  planning-agent:
    build: ./services/planning-agent
    ports: ["8007:8007"]
    environment:
      - AI_SERVICE_URL=http://ai-service:8010
      - MEMORY_SERVICE_URL=http://memory-agent:8009
    depends_on: [ai-service, memory-agent]
    networks: [eunice-network]

  executor-agent:
    build: ./services/executor-agent
    ports: ["8008:8008"]
    environment:
      - FILE_STORAGE_URL=http://file-storage:8013
      - SANDBOX_MODE=enabled
    depends_on: [file-storage]
    networks: [eunice-network]

  memory-agent:
    build: ./services/memory-agent
    ports: ["8009:8009"]
    environment:
      - VECTOR_DB_URL=http://vector-database:8080
      - FILE_STORAGE_URL=http://file-storage:8013
    depends_on: [vector-database, file-storage]
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
      - AUTH_SERVICE_URL=http://auth-service:8007
    depends_on: [redis, auth-service]
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
