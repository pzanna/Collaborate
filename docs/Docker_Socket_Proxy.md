# Docker Socket Proxy Configuration

## Overview

The Docker Socket Proxy is a security layer that provides controlled access to the Docker daemon socket for the Eunice platform services. This component is essential for secure Docker API access from within containers.

## Purpose

- **Security**: Provides controlled, limited access to Docker API instead of mounting the raw socket
- **Access Control**: Restricts which Docker API endpoints can be accessed
- **Audit Trail**: Logs all Docker API requests for security monitoring
- **Production Safety**: Prevents unauthorized container operations

## Configuration

### Container Settings

- **Image**: `lscr.io/linuxserver/socket-proxy:latest`
- **Container Name**: `eunice-docker-socket-proxy`
- **Port**: `2375` (internal Docker API proxy)
- **Network**: `eunice-microservices`

### Security Permissions

```bash
# Allowed Operations
CONTAINERS=1    # List and manage containers
SERVICES=1      # List and manage services
NETWORKS=1      # List networks
VOLUMES=1       # List volumes
IMAGES=1        # List images
INFO=1          # System info
VERSION=1       # Version info
PING=1          # Health checks
EVENTS=1        # Event monitoring

# Disabled for Security
EXEC=0          # No container exec access
SYSTEM=0        # No system-level API access
BUILD=0         # No build operations
COMMIT=0        # No commit operations
POST=0          # Read-only API access
```

## Services That Use Docker Socket Proxy

### Auth Service

The authentication service uses the Docker socket proxy to:

- Query container status for service health monitoring
- Validate service availability for authentication flows
- Monitor container events for security logging

**Environment Variable**: `DOCKER_HOST=tcp://docker-socket-proxy:2375`

## Deployment

### Development Environment

Included in `start_dev.sh`:

```bash
# Phase 1: Start infrastructure
docker compose -f docker-compose.secure.yml up -d redis postgres docker-socket-proxy
```

### Production Environment  

Included in `deploy_production.sh`:

```bash
# Start infrastructure services
docker compose -f docker-compose.secure.yml up -d redis postgres docker-socket-proxy
```

## Health Monitoring

### Health Check Endpoint

```bash
curl http://localhost:2375/_ping
```

### Status Verification

```bash
# Development
curl -f -s http://localhost:2375/_ping >/dev/null && echo "Docker Socket Proxy is healthy"

# Production  
curl -f http://localhost:2375/_ping && echo "Docker Socket Proxy is healthy"
```

## Security Considerations

### Read-Only Mode

- API is configured as read-only (`POST=0`)
- Prevents unauthorized container modifications
- Allows monitoring and status queries only

### Capability Restrictions

- Runs with minimal Linux capabilities
- `no-new-privileges` security option enabled
- Read-only root filesystem with tmpfs for runtime data

### Network Isolation

- Runs on isolated `eunice-microservices` network
- Only accessible by authorized Eunice services
- Not exposed to external networks

## Troubleshooting

### Common Issues

1. **Connection Refused**

   ```bash
   # Check if container is running
   docker ps | grep socket-proxy
   
   # Check container logs
   docker logs eunice-docker-socket-proxy
   ```

2. **Permission Denied**

   ```bash
   # Verify socket mount permissions
   docker inspect eunice-docker-socket-proxy | grep -A5 Mounts
   ```

3. **Service Health Check Failures**

   ```bash
   # Test direct connection
   curl -v http://localhost:2375/_ping
   
   # Check network connectivity
   docker network inspect eunice-microservices
   ```

### Log Analysis

```bash
# View proxy logs
docker logs eunice-docker-socket-proxy -f

# View auth service logs for Docker API calls
docker logs eunice-auth-service | grep docker
```

## Files Modified

- `docker-compose.yml` - Contains proxy service definition
- `docker-compose.secure.yml` - Added proxy with security hardening  
- `start_dev.sh` - Includes proxy in startup sequence
- `deploy_production.sh` - Includes proxy in production deployment
- `stop_dev.sh` - Updated service documentation

## Security Best Practices

1. **Minimal Permissions**: Only enable required Docker API endpoints
2. **Network Isolation**: Keep proxy on internal networks only
3. **Regular Updates**: Update proxy image regularly for security patches
4. **Monitoring**: Log and monitor all Docker API access
5. **Backup Strategy**: Include proxy configuration in backup procedures

## References

- [Docker Socket Proxy Documentation](https://github.com/Tecnativa/docker-socket-proxy)
- [LinuxServer Docker Socket Proxy](https://docs.linuxserver.io/images/docker-socket-proxy)
- [Docker API Security](https://docs.docker.com/engine/security/security/)
