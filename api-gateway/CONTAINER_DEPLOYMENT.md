# API Gateway Container Deployment Guide

## Overview

The API Gateway has been enhanced to work seamlessly in containerized environments with proper MCP (Model Context Protocol) client connectivity to other Eunice services.

## Container-Specific Features

### 1. **Automatic Environment Detection**

- Detects container environment via `DOCKER_HOST`, `KUBERNETES_SERVICE_HOST`, or `/.dockerenv`
- Automatically configures service-to-service networking using Docker Compose service names
- Falls back to manual configuration when available

### 2. **Flexible Configuration Loading**

Configuration is loaded in the following priority order:

1. `MCP_CFG_JSON` environment variable (JSON string)
2. `MCP_CFG_FILE` environment variable (file path)
3. `/app/config/mcp.json` (container volume mount)
4. `./config/mcp.json` (development)
5. Auto-detection based on container environment

### 3. **Connection Resilience**

- Exponential backoff retry logic for MCP server connections
- Configurable retry attempts (`MCP_MAX_RETRIES`)
- Graceful handling of failed connections
- Enhanced health checking with per-server status

### 4. **Service Discovery**

Uses Docker Compose service names for inter-service communication:

- `database-service:8010/mcp` - Database operations
- Future services can be added with MCP servers

## Container Configuration

### Docker Compose Setup

The `docker-compose.yml` has been updated with:

```yaml
api-gateway:
  environment:
    - MCP_CFG_FILE=/app/config/mcp.json
    - MCP_CONNECTION_TIMEOUT=30
    - MCP_MAX_RETRIES=3
  volumes:
    - ./api-gateway/config:/app/config:ro
  depends_on:
    - database-service
```

### MCP Configuration File (`config/mcp.json`)

```json
{
  "servers": {
    "database": {
      "transport": "http",
      "url": "http://database-service:8010/mcp",
      "description": "Database operations and data management",
      "timeout": 30
    }
  },
  "client": {
    "name": "eunice-api-gateway",
    "version": "v0.5.1",
    "max_retries": 3,
    "retry_delay": 2.0,
    "connection_timeout": 30.0
  },
  "environment": "container"
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_CFG_JSON` | - | JSON string with MCP configuration |
| `MCP_CFG_FILE` | `/etc/eunice/mcp.json` | Path to MCP config file |
| `MCP_MAX_RETRIES` | 3 | Max connection retry attempts |
| `MCP_RETRY_DELAY` | 2.0 | Base retry delay in seconds |
| `MCP_CONNECTION_TIMEOUT` | 30 | Connection timeout in seconds |

## Health Checking

The `/health` endpoint provides comprehensive status:

```json
{
  "ok": true,
  "service": "api-gateway",
  "environment": "container",
  "servers": ["database"],
  "servers_status": {
    "database": {
      "status": "healthy",
      "tools_count": 15,
      "tools": ["create_project", "update_project", ...]
    }
  },
  "tools": {...},
  "config_source": "/app/config/mcp.json",
  "mcp_version": "v0.5.1"
}
```

## Deployment Steps

1. **Build containers:**

   ```bash
   docker compose build api-gateway database-service
   ```

2. **Start services:**

   ```bash
   docker compose up -d postgres database-service
   docker compose up -d api-gateway
   ```

3. **Verify connectivity:**

   ```bash
   curl http://localhost:8001/health
   ```

## Adding New MCP Services

To add new services with MCP servers:

1. **Implement MCP server in the service** using FastMCP
2. **Expose MCP port** in docker-compose.yml
3. **Update MCP configuration** to include the new service
4. **Add health check** for the MCP endpoint

Example for adding a new service:

```yaml
# docker-compose.yml
new-service:
  ports:
    - "8011:8011"
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8011/mcp"]
```

```json
// config/mcp.json
{
  "servers": {
    "database": {...},
    "new-service": {
      "transport": "http",
      "url": "http://new-service:8011/mcp",
      "description": "New service operations"
    }
  }
}
```

## Troubleshooting

### Common Issues

1. **Connection refused errors:**
   - Check if target service is running and healthy
   - Verify port configuration matches between services
   - Check Docker network connectivity

2. **Configuration not loading:**
   - Verify volume mount for config directory
   - Check file permissions (should be readable by container user)
   - Review logs for configuration loading messages

3. **MCP server not responding:**
   - Check target service logs for MCP server startup
   - Verify MCP endpoint responds to direct curl requests
   - Check network policies and firewall rules

### Debug Commands

```bash
# Check API Gateway health
docker exec eunice-api-gateway curl -f http://localhost:8001/health

# Check database MCP server
docker exec eunice-database-service curl -f http://localhost:8010/mcp

# View API Gateway logs
docker logs eunice-api-gateway

# Test network connectivity
docker exec eunice-api-gateway ping database-service
```

## Security Considerations

- Config files are mounted read-only
- MCP connections use HTTP within trusted Docker network
- Services run as non-root users
- Network access is limited to required services only
- Secrets are managed via Docker secrets or environment variables

## Performance

- Connection pooling for MCP clients
- Retry logic with exponential backoff
- Health checks cache results for better performance
- Configurable timeouts for different deployment scenarios
