# Enhanced MCP Server - Phase 3.1

The Enhanced MCP (Model Context Protocol) Server is the central coordination hub for all research agents in the Eunice Research Platform Phase 3 microservices architecture.

## Features

### Core Capabilities

- **WebSocket-based Agent Communication**: Real-time bidirectional communication with research agents
- **Agent Registry Management**: Dynamic agent registration, discovery, and health monitoring
- **Task Queue & Processing**: Intelligent task distribution and load balancing
- **Clustering Support**: Horizontal scaling with peer discovery and coordination
- **Enhanced Monitoring**: Prometheus metrics, structured logging, and health checks

### Architecture Enhancements

- **Containerized Deployment**: Docker-based service with proper resource management
- **Load Balancing**: Adaptive, weighted, and least-connections strategies
- **Circuit Breaker**: Fault tolerance and resilience patterns
- **Security**: JWT authentication and TLS support
- **Observability**: Comprehensive metrics, tracing, and logging

## Quick Start

### Using Docker Compose

1. **Start the Enhanced MCP Server**:

   ```bash
   cd services/mcp-server
   docker-compose up -d
   ```

2. **Verify Health**:

   ```bash
   curl http://localhost:8080/health
   ```

3. **View Logs**:

   ```bash
   docker-compose logs -f mcp-server
   ```

4. **Access Metrics** (if monitoring profile enabled):

   ```bash
   curl http://localhost:9090/metrics
   ```

### Using Python Directly

1. **Install Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**:

   ```bash
   export DATABASE_URL="postgresql://postgres:password@localhost:5432/eunice"
   export REDIS_URL="redis://localhost:6379"
   export LOG_LEVEL="INFO"
   ```

3. **Run the Server**:

   ```bash
   python mcp_server.py
   ```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_HOST` | `0.0.0.0` | Server host address |
| `MCP_PORT` | `9000` | WebSocket server port |
| `MCP_MAX_CONNECTIONS` | `1000` | Maximum concurrent connections |
| `DATABASE_URL` | Required | PostgreSQL connection string |
| `REDIS_URL` | Required | Redis connection string |
| `AGENT_REGISTRY_TTL` | `300` | Agent registration timeout (seconds) |
| `CLUSTER_ENABLED` | `false` | Enable clustering mode |
| `LOAD_BALANCE_STRATEGY` | `adaptive` | Load balancing strategy |
| `ENABLE_METRICS` | `true` | Enable Prometheus metrics |
| `LOG_LEVEL` | `INFO` | Logging level |

### Load Balancing Strategies

- **round_robin**: Simple round-robin distribution
- **weighted**: Weighted distribution based on agent capacity
- **adaptive**: Dynamic adjustment based on response times
- **least_connections**: Route to agent with fewest active tasks

### Clustering Configuration

```yaml
environment:
  - CLUSTER_ENABLED=true
  - CLUSTER_DISCOVERY=redis
  - CLUSTER_NODE_ID=mcp-server-1
```

## API Reference

### WebSocket Protocol

The Enhanced MCP Server uses JSON-RPC over WebSocket for agent communication.

#### Agent Registration

```json
{
  "type": "agent_register",
  "agent_id": "literature-agent-001",
  "agent_type": "literature_search",
  "capabilities": ["search", "retrieve", "summarize"]
}
```

#### Task Submission

```json
{
  "type": "task_submit",
  "task_id": "task-12345",
  "task_type": "literature_search",
  "task_data": {
    "query": "machine learning",
    "limit": 50
  }
}
```

#### Task Result

```json
{
  "type": "task_result",
  "task_id": "task-12345",
  "status": "completed",
  "result": {
    "papers": [...],
    "total_found": 47
  }
}
```

#### Heartbeat

```json
{
  "type": "heartbeat",
  "agent_id": "literature-agent-001",
  "timestamp": "2025-07-26T10:30:00Z"
}
```

### HTTP Endpoints

#### Health Check

```
GET /health
```

Response:

```json
{
  "status": "healthy",
  "server_id": "mcp-server-abc123",
  "uptime": 3600,
  "active_agents": 5,
  "active_tasks": 12,
  "total_connections": 150,
  "total_tasks_processed": 1234
}
```

#### Metrics (Prometheus format)

```
GET /metrics
```

## Monitoring & Observability

### Prometheus Metrics

- `mcp_connected_agents_total{agent_type}`: Number of connected agents by type
- `mcp_task_duration_seconds{task_type}`: Task processing duration histogram
- `mcp_messages_total{direction,type}`: Total messages processed
- `mcp_errors_total{error_type}`: Total errors by type

### Structured Logging

The server uses structured JSON logging with the following fields:

- `timestamp`: ISO 8601 timestamp
- `level`: Log level (INFO, WARNING, ERROR)
- `logger`: Logger name
- `message`: Log message
- `server_id`: Unique server identifier
- `client_id`: Client connection ID (if applicable)
- `agent_id`: Agent identifier (if applicable)
- `task_id`: Task identifier (if applicable)

### Health Checks

Health checks are available on port 8080:

- **Startup probe**: Checks if server has started
- **Liveness probe**: Checks if server is running
- **Readiness probe**: Checks if server can accept connections

## Testing

### Run Test Client

```bash
cd services/mcp-server
python test_client.py
```

The test client validates:

1. Server connectivity
2. Agent registration
3. Heartbeat mechanism
4. Task submission and processing
5. Health endpoint

### Integration Tests

```bash
# Start test environment
docker-compose --profile debug up -d

# Run integration tests
pytest tests/ -v

# Cleanup
docker-compose down
```

## Development

### Local Development Setup

1. **Clone and Setup**:

   ```bash
   git clone <repository>
   cd services/mcp-server
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Start Dependencies**:

   ```bash
   docker-compose up postgres redis -d
   ```

3. **Run Server**:

   ```bash
   python mcp_server.py
   ```

### Code Structure

```
services/mcp-server/
├── mcp_server.py          # Main server implementation
├── config.py              # Configuration management
├── requirements.txt       # Python dependencies
├── Dockerfile             # Container definition
├── docker-compose.yml     # Service orchestration
├── prometheus.yml         # Metrics configuration
├── test_client.py         # Test client
└── README.md             # This file
```

## Deployment

### Production Deployment

1. **Build and Tag Image**:

   ```bash
   docker build -t eunice/mcp-server:v3.1.0 .
   ```

2. **Deploy with Kubernetes**:

   ```bash
   kubectl apply -f k8s/
   ```

3. **Scale Horizontally**:

   ```bash
   kubectl scale deployment mcp-server --replicas=3
   ```

### Performance Tuning

- **Connection Limits**: Adjust `MCP_MAX_CONNECTIONS` based on load
- **Task Queue Size**: Configure `MCP_MAX_CONCURRENT_TASKS` for throughput
- **Resource Allocation**: Set appropriate CPU/memory limits
- **Load Balancing**: Choose strategy based on agent characteristics

## Troubleshooting

### Common Issues

1. **Connection Refused**:
   - Check if server is running: `docker-compose ps`
   - Verify port is exposed: `netstat -tlnp | grep 9000`
   - Check firewall settings

2. **Agent Registration Fails**:
   - Verify agent type is in `ALLOWED_AGENT_TYPES`
   - Check authentication configuration
   - Review server logs for errors

3. **High Memory Usage**:
   - Monitor active connections: `/health` endpoint
   - Check for connection leaks in logs
   - Adjust resource limits

4. **Task Processing Delays**:
   - Monitor queue depth in metrics
   - Check agent health and availability
   - Review load balancing strategy

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
docker-compose restart mcp-server
```

Access debug tools:

```bash
# Redis Commander (for queue inspection)
docker-compose --profile debug up redis-commander -d

# Prometheus (for metrics)
docker-compose --profile monitoring up prometheus -d
```

## Contributing

1. Follow the project's coding standards
2. Add tests for new features
3. Update documentation
4. Test with both Docker and local environments
5. Verify metrics and logging work correctly

## Security Considerations

- Use strong JWT secrets in production
- Enable TLS for production deployments
- Implement proper network policies
- Monitor for unusual connection patterns
- Regular security updates for dependencies

---

**Status**: Phase 3.1 Implementation Complete
**Next**: Agent Containerization (Week 2)
**Documentation**: Enhanced MCP Server Architecture
