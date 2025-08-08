# Development Environment with File Watching

This document describes how to use the development environment with file watching capabilities for the Eunice Research Platform.

## Overview

All containerized services and agents in the Eunice platform now have comprehensive file watching functionality enabled through the `watchfiles` library. This allows for automatic reloading of services when code changes are detected during development.

## Services with File Watching

✅ **All services have file watching configured:**

### Services:
- `api-gateway` - API Gateway service with REST endpoints
- `mcp-server` - Model Context Protocol server
- `database-service` - Database management service  
- `memory-service` - Knowledge base and memory management
- `network-service` - Network communication service
- `auth-service` - Authentication and authorization service

### Agents:
- `research-manager-agent` - Research management agent

## Usage

### Starting Development Environment

To start all services with file watching enabled:

```bash
# Start all services in development mode
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Start specific service in development mode
docker compose -f docker-compose.yml -f docker-compose.dev.yml up api-gateway

# Build and start a service
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build database-service
```

### Development Features

Each service includes:

1. **File Watching**: Automatic service restart when source code changes
2. **Debug Logging**: Enhanced logging with `LOG_LEVEL=DEBUG`
3. **Development Environment Variables**: Service-specific development settings
4. **Source Code Mounting**: Live code updates without rebuilding containers
5. **Fast Feedback Loop**: Immediate reflection of code changes

### File Watching Implementation

#### Python Services
- Services using `watchfiles` library for file monitoring
- Automatic restart on `.py` file changes
- Example: `database-service`, `memory-service`

#### FastAPI Services  
- Services using `uvicorn --reload` for automatic reloading
- Hot reload on code changes
- Example: `auth-service`

#### Agents
- Research agents with `watchfiles` integration
- Configuration and source code monitoring

## Environment Variables

Development-specific environment variables are set automatically:

```bash
LOG_LEVEL=DEBUG                    # Enhanced logging
DEVELOPMENT_MODE=true              # Development flag
WATCHFILES_FORCE_POLLING=1         # Force polling for file changes
```

Service-specific variables:
- `AUTH_DB_PATH=/tmp/auth_dev.db` (auth-service)
- `MEMORY_DB_PATH=/tmp/memory_dev.db` (memory-service)
- `HEALTH_CHECK_INTERVAL=10` (reduced for development)

## File Structure

Each service includes:
- `start-dev.sh` - Development startup script with file watching
- `Dockerfile` with `development` target
- Development configuration in `docker-compose.dev.yml`

## Benefits

1. **Faster Development**: No need to manually restart services
2. **Immediate Feedback**: See changes reflected instantly
3. **Consistent Environment**: All services use the same development patterns
4. **Production Safety**: Development configurations are separate from production

## Troubleshooting

If file watching isn't working:

1. **Check file mounting**: Ensure source files are properly mounted in containers
2. **Verify watchfiles installation**: Development targets install watchfiles automatically  
3. **Check file permissions**: Ensure files are readable by the container user
4. **Use polling**: `WATCHFILES_FORCE_POLLING=1` forces polling mode if needed

## Production vs Development

- **Production**: Uses optimized builds without file watching overhead
- **Development**: Includes file watching, debug logging, and live reloading
- **Separation**: Complete separation ensures no development code reaches production

This development environment provides a seamless, efficient workflow for Eunice platform development with comprehensive file watching across all services.
