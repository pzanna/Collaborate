# Containerized API Gateway - Eunice Research Platform

## Overview

This is the containerized API Gateway service for Version 0.3 of the Eunice Research Platform. It provides a unified REST API interface that routes requests to research agents via the MCP (Message Control Protocol) server using WebSocket communication.

## Architecture

The API Gateway is designed for the Version 0.3 microservices architecture:

```
Client Requests → API Gateway Container → MCP Server Container → Research Agent Containers
```

### Key Features

- **Unified REST API**: Single endpoint for all research operations
- **MCP Protocol Integration**: WebSocket-based communication with MCP server
- **Container-Native**: Designed for Docker/Kubernetes deployment
- **Health Monitoring**: Built-in health checks and metrics
- **Auto-Reconnection**: Resilient MCP server connection handling
- **Type-Safe**: Full Pydantic model validation
- **Production-Ready**: Proper logging, error handling, and graceful shutdown

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Running MCP Server (from `/services/mcp-server/`)

### Building and Running

1. **Build the container:**

   ```bash
   docker build -t eunice/api-gateway:latest .
   ```

2. **Run with Docker Compose:**

   ```bash
   docker-compose up -d
   ```

3. **Verify deployment:**

   ```bash
   curl http://localhost:8001/health
   ```

### Testing

Run the test suite to verify everything is working:

```bash
python test_api_gateway.py
```

## API Endpoints

### Health and Status

- `GET /health` - Service health check
- `GET /status` - Detailed service status
- `GET /metrics` - Service metrics for monitoring

### Research Operations

- `POST /literature/search` - Search academic literature
- `POST /research/tasks` - Submit research tasks
- `GET /tasks/{task_id}/status` - Get task status
- `DELETE /tasks/{task_id}` - Cancel task (future)

### Documentation

- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation (ReDoc)

## Configuration

The service is configured via environment variables:

### Server Configuration

- `HOST` - Server host (default: 0.0.0.0)
- `PORT` - Server port (default: 8001)
- `LOG_LEVEL` - Logging level (default: INFO)

### MCP Server Configuration

- `MCP_SERVER_HOST` - MCP server hostname (default: mcp-server)
- `MCP_SERVER_PORT` - MCP server port (default: 9000)
- `MCP_CONNECTION_RETRY_ATTEMPTS` - Connection retry attempts (default: 3)
- `MCP_CONNECTION_RETRY_DELAY` - Retry delay in seconds (default: 5)

### CORS Configuration

- `CORS_ORIGINS` - Allowed origins (default: *)

## Development

### Local Development

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables:**

   ```bash
   export MCP_SERVER_HOST=localhost
   export LOG_LEVEL=DEBUG
   ```

3. **Run locally:**

   ```bash
   python main.py
   ```

### Adding New Endpoints

1. Define request/response models in `models.py`
2. Add handler method to `APIGateway` class in `main.py`
3. Register route in the FastAPI app
4. Add tests to `test_api_gateway.py`

## Monitoring and Operations

### Health Checks

The service provides comprehensive health checks:

```bash
# Basic health check
curl http://localhost:8001/health

# Detailed status
curl http://localhost:8001/status

# Metrics for monitoring
curl http://localhost:8001/metrics
```

### Logging

Logs are structured and written to stdout for container orchestration:

```bash
# View logs
docker logs eunice-api-gateway

# Follow logs
docker logs -f eunice-api-gateway
```

### Container Health Check

Docker health check is built-in:

```bash
docker inspect --format='{{.State.Health.Status}}' eunice-api-gateway
```

## Deployment

### Docker Compose (Development)

```yaml
services:
  api-gateway:
    build: .
    ports:
      - "8001:8001"
    environment:
      - MCP_SERVER_HOST=mcp-server
    depends_on:
      - mcp-server
```

### Kubernetes (Production)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
    spec:
      containers:
      - name: api-gateway
        image: eunice/api-gateway:latest
        ports:
        - containerPort: 8001
        env:
        - name: MCP_SERVER_HOST
          value: "mcp-server"
        - name: LOG_LEVEL
          value: "INFO"
        livenessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 5
          periodSeconds: 5
```

## Integration with MCP Server

The API Gateway communicates with the MCP server via WebSocket:

1. **Connection**: Establishes persistent WebSocket connection
2. **Registration**: Registers as "api-gateway" client type
3. **Request Routing**: Converts REST requests to MCP research actions
4. **Response Handling**: Converts MCP responses back to REST responses
5. **Status Tracking**: Maintains request status and provides status queries

### MCP Message Flow

```
REST Request → API Gateway → MCP Research Action → MCP Server → Agent
REST Response ← API Gateway ← MCP Response ← MCP Server ← Agent
```

## Error Handling

The service provides comprehensive error handling:

- **Connection Errors**: Automatic retry with exponential backoff
- **Validation Errors**: Proper HTTP 400 responses with details
- **Service Errors**: HTTP 503 when dependencies unavailable
- **Graceful Degradation**: Continues operating with reduced functionality

## Security Considerations

- **CORS**: Configurable cross-origin request handling
- **Input Validation**: All requests validated with Pydantic models
- **Error Sanitization**: Error messages don't expose internal details
- **Non-Root User**: Container runs as non-root user
- **Health Endpoints**: Publicly accessible for orchestration

## Troubleshooting

### Common Issues

1. **Cannot connect to MCP server:**
   - Check MCP server is running
   - Verify network connectivity
   - Check MCP_SERVER_HOST environment variable

2. **Health check failing:**
   - Check service logs: `docker logs eunice-api-gateway`
   - Verify all dependencies are running
   - Check resource constraints

3. **API requests timing out:**
   - Check MCP server capacity
   - Monitor request queue status
   - Verify agent availability

### Debug Mode

Enable debug logging:

```bash
docker run -e LOG_LEVEL=DEBUG eunice/api-gateway:latest
```

## Version History

- **v3.0.0**: Initial containerized release for Version 0.3
- **v2.0.0**: Enhanced MCP integration (Version 0.2)
- **v1.0.0**: Basic API Gateway implementation

## Contributing

1. Make changes to source files
2. Add/update tests as needed
3. Update documentation
4. Test with `docker-compose up`
5. Submit pull request

## License

Part of the Eunice Research Platform project.
