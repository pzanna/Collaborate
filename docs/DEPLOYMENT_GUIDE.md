# Eunice Research Platform - Deployment and Operations Guide

**Version**: v0.3.1  
**Last Updated**: January 31, 2025  
**Target Audience**: DevOps Engineers, System Administrators, Application Architects

## Overview

This comprehensive deployment guide provides step-by-step instructions for deploying the Eunice Research Platform in development, staging, and production environments. The platform uses Docker Compose for container orchestration and supports horizontal scaling through Kubernetes.

## 🚀 Quick Deployment

### Prerequisites

**System Requirements**:

- **OS**: Linux (Ubuntu 20.04+), macOS (10.15+), Windows with WSL2
- **Memory**: 8GB RAM minimum, 16GB recommended for production
- **Storage**: 50GB available disk space
- **CPU**: 4 cores minimum, 8 cores recommended
- **Network**: Outbound internet access for AI provider APIs

**Software Dependencies**:

- Docker Engine 20.10+ and Docker Compose 2.0+
- Git 2.30+
- Node.js 18+ (for frontend development)
- Python 3.11+ (for backend development)

### Environment Setup

1. **Clone the repository**:

   ```bash
   git clone https://github.com/your-org/eunice.git
   cd eunice
   ```

2. **Configure environment variables**:

   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` with your configuration**:

   ```bash
   # AI Provider Configuration (Required)
   OPENAI_API_KEY=sk-your-openai-key
   ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
   XAI_API_KEY=xai-your-xai-key

   # Database Configuration
   POSTGRES_DB=eunice
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=your-secure-password

   # Authentication Configuration (Generate secure keys)
   AUTH_SECRET_KEY=your-jwt-secret-key-minimum-32-characters
   
   # Environment Type
   ENVIRONMENT=development  # development, staging, production
   ```

### Development Deployment

**Quick Start**:

```bash
# Start development environment
./start_dev.sh

# Or manual startup
docker-compose -f docker-compose.dev.yml up --build
```

**Development Services**:

- **Frontend**: <http://localhost:3000> (React development server)
- **API Gateway**: <http://localhost:8001> (FastAPI with hot reload)
- **API Documentation**: <http://localhost:8001/docs>
- **MCP Server**: <http://localhost:9000>
- **Auth Service**: <http://localhost:8013>
- **Database**: PostgreSQL on port 5432
- **Redis**: Port 6379

### Production Deployment

**Security-Hardened Production**:

```bash
# Start production environment
./deploy_production.sh

# Or manual production startup
docker-compose -f docker-compose.secure.yml up --build -d
```

**Production Features**:

- Security-hardened containers with non-root users
- Read-only filesystems where applicable
- Resource limits and health checks
- Production-grade logging configuration
- Encrypted inter-service communication ready

## 🐳 Container Architecture

### Service Overview

```yaml
Core Services:
  api-gateway:          # Port 8001 - Unified REST API
  auth-service:         # Port 8013 - JWT authentication with 2FA
  mcp-server:           # Port 9000 - Agent coordination hub
  database-service:     # Port 8011 - Database abstraction layer

Research Agents (MCP Clients):
  research-manager:     # Port 8002 - Workflow orchestration
  literature-search:    # Port 8003 - Academic search
  screening-prisma:     # Port 8004 - Systematic review screening
  synthesis-review:     # Port 8005 - Evidence synthesis
  writer-agent:         # Port 8006 - Manuscript generation
  planning-agent:       # Port 8007 - Research planning
  executor-agent:       # Port 8008 - Code execution
  memory-service:       # Port 8009 - Knowledge management

Infrastructure:
  postgres:             # Port 5432 - Primary database
  redis:                # Port 6379 - Message broker and cache
  frontend:             # Port 3000 - React user interface
```

### Container Health Monitoring

Each service includes comprehensive health checks:

```yaml
Health Check Endpoints:
  - GET /health         # Basic service health
  - GET /status         # Detailed service status
  - GET /ready          # Readiness probe for Kubernetes

Health Check Response Format:
{
  "status": "healthy",
  "service": "service-name",
  "version": "1.0.0",
  "uptime": "72h34m12s",
  "ready": true,
  "dependencies": {
    "database": "healthy",
    "redis": "healthy",
    "mcp_server": "connected"
  }
}
```

## 🔧 Environment Configuration

### Development Environment

**Configuration**: `docker-compose.dev.yml`

**Features**:

- Hot reloading for frontend and backend
- Debug logging enabled
- Development-specific environment variables
- Local volume mounts for code changes
- Non-persistent data (containers can be reset)

**Usage**:

```bash
# Start development environment
./start_dev.sh

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Reset environment
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up --build
```

### Staging Environment

**Configuration**: `docker-compose.yml`

**Features**:

- Production-like configuration
- Performance monitoring enabled
- Persistent data volumes
- Load testing capabilities
- Integration testing environment

**Usage**:

```bash
# Start staging environment
docker-compose up --build -d

# Monitor services
docker-compose ps
docker-compose logs -f api-gateway
```

### Production Environment

**Configuration**: `docker-compose.secure.yml`

**Features**:

- Security-hardened containers
- Resource limits and constraints
- Production logging configuration
- Health monitoring and alerting
- Backup and recovery procedures

**Usage**:

```bash
# Deploy production environment
./deploy_production.sh

# Monitor production services
./validate_platform_security.sh
./validate_deployment.sh
```

## 🔐 Security Configuration

### Authentication Setup

**JWT Configuration**:

```bash
# Generate secure JWT secret (minimum 32 characters)
openssl rand -base64 32

# Configure in .env file
AUTH_SECRET_KEY=your-generated-secret-key
```

**2FA Setup**:

- TOTP-based authentication supported
- Google Authenticator, Microsoft Authenticator compatible
- Backup codes generated automatically
- QR code generation for easy setup

### Container Security

**Security Features**:

- Non-root user execution in all containers
- Read-only filesystems where applicable
- Dropped Linux capabilities
- Resource limits to prevent resource exhaustion
- Network isolation between services

**Security Validation**:

```bash
# Run security validation
./validate_platform_security.sh

# Check container security configuration
./security_scan.sh
```

## 📊 Monitoring and Logging

### Service Monitoring

**Health Check Monitoring**:

```bash
# Check all service health
curl http://localhost:8001/health

# Check individual service status
curl http://localhost:8013/health  # Auth service
curl http://localhost:9000/health  # MCP server
```

**Container Status Monitoring**:

```bash
# Check container status
docker-compose ps

# View resource usage
docker stats

# Check container logs
docker-compose logs -f [service-name]
```

### Performance Monitoring

**Response Time Monitoring**:

- API Gateway: Target < 500ms average response time
- Authentication: Target < 100ms JWT validation
- Database: Target < 50ms query response time
- Literature Search: Target < 10s comprehensive search

**Resource Monitoring**:

```bash
# Monitor resource usage
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Check disk usage
df -h
docker system df
```

### Logging Configuration

**Log Locations**:

- Application Logs: `logs/` directory
- Container Logs: `docker-compose logs`
- System Logs: `/var/log/` (Linux)

**Log Retention**:

- Development: 7 days
- Staging: 30 days  
- Production: 90 days with rotation

## 🚀 Scaling and Performance

### Horizontal Scaling

**Agent Scaling**:

```bash
# Scale literature search agents
docker-compose up --scale literature-search=3

# Scale multiple agents
docker-compose up --scale literature-search=2 --scale planning-agent=2
```

**Database Performance**:

- Connection pooling: 20 connections per service
- Query optimization with indexes
- Read replica support ready for implementation

### Performance Optimization

**Response Time Optimization**:

- Direct PostgreSQL connections for READ operations
- Redis caching for frequently accessed data
- WebSocket connections for real-time updates
- Async processing for long-running tasks

**Resource Optimization**:

```bash
# Optimize container resources
docker system prune -f
docker volume prune -f
docker image prune -a -f
```

## 🔄 Backup and Recovery

### Database Backup

**Automated Backup**:

```bash
# Create database backup
docker exec eunice-postgres pg_dump -U postgres eunice > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
docker exec -i eunice-postgres psql -U postgres eunice < backup_file.sql
```

**Backup Schedule**:

- Development: Manual backups
- Staging: Daily automated backups
- Production: Daily backups with weekly full backups

### Container Data Backup

**Volume Backup**:

```bash
# Backup persistent volumes
docker run --rm -v eunice_postgres_data:/data -v $(pwd):/backup ubuntu tar czf /backup/postgres_backup.tar.gz /data

# Restore volume
docker run --rm -v eunice_postgres_data:/data -v $(pwd):/backup ubuntu tar xzf /backup/postgres_backup.tar.gz -C /
```

## 🐛 Troubleshooting

### Common Issues

#### Container Startup Issues

**Problem**: Services fail to start

```bash
# Check container status
docker-compose ps

# View startup logs
docker-compose logs [service-name]

# Check resource usage
docker stats
```

**Solutions**:

- Verify environment variables are set correctly
- Ensure sufficient system resources (memory, disk)
- Check port availability
- Validate Docker Compose file syntax

#### Database Connection Issues

**Problem**: Services cannot connect to PostgreSQL

```bash
# Check database container status
docker-compose logs postgres

# Test database connection
docker exec -it eunice-postgres psql -U postgres -d eunice
```

**Solutions**:

- Verify database credentials in environment variables
- Check database container health
- Ensure database initialization completed
- Validate network connectivity between containers

#### Authentication Issues

**Problem**: JWT authentication failing

```bash
# Check auth service logs
docker-compose logs auth-service

# Test auth service directly
curl http://localhost:8013/health
```

**Solutions**:

- Verify AUTH_SECRET_KEY is configured
- Check database connection for user data
- Validate JWT token format and expiration
- Ensure CORS configuration for frontend

#### MCP Server Issues

**Problem**: Agents cannot connect to MCP server

```bash
# Check MCP server logs
docker-compose logs mcp-server

# Test MCP server health
curl http://localhost:9000/health
```

**Solutions**:

- Verify WebSocket connections are allowed
- Check agent registration in MCP server logs
- Validate network connectivity between containers
- Ensure MCP server has sufficient resources

### Performance Issues

#### Slow Response Times

**Diagnostics**:

```bash
# Check API response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8001/health

# Monitor database performance
docker exec eunice-postgres psql -U postgres -d eunice -c "SELECT * FROM pg_stat_activity;"
```

**Solutions**:

- Increase container resource limits
- Add database indexes for slow queries
- Enable Redis caching
- Scale agent instances horizontally

#### High Memory Usage

**Diagnostics**:

```bash
# Monitor memory usage
docker stats --format "table {{.Container}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Check for memory leaks
docker logs [container-name] | grep -i memory
```

**Solutions**:

- Increase container memory limits
- Optimize application code for memory efficiency
- Implement garbage collection tuning
- Scale services across multiple containers

## 📋 Deployment Checklist

### Pre-Deployment

- [ ] System requirements verified
- [ ] Environment variables configured
- [ ] API keys obtained and tested
- [ ] Security configurations reviewed
- [ ] Backup procedures tested

### Deployment

- [ ] Repository cloned and updated
- [ ] Docker Compose configuration validated
- [ ] Services started successfully
- [ ] Health checks passing
- [ ] Database schema initialized
- [ ] Authentication system functional

### Post-Deployment

- [ ] All services responding to health checks
- [ ] API documentation accessible
- [ ] Frontend loading correctly
- [ ] Authentication flow working
- [ ] Sample research task execution tested
- [ ] Monitoring and logging configured
- [ ] Backup procedures scheduled

### Production Readiness

- [ ] Security hardening applied
- [ ] Performance benchmarking completed
- [ ] Load testing performed
- [ ] Disaster recovery procedures documented
- [ ] Monitoring and alerting configured
- [ ] Documentation updated and accessible

## 📞 Support and Maintenance

### Regular Maintenance

**Daily Tasks**:

- Monitor service health and performance
- Check log files for errors or warnings
- Verify backup completion
- Monitor resource usage trends

**Weekly Tasks**:

- Update container images if security patches available
- Review and rotate log files
- Performance analysis and optimization
- Security scan execution

**Monthly Tasks**:

- Comprehensive backup testing
- Disaster recovery procedure testing
- Documentation review and updates
- Security audit and vulnerability assessment

### Getting Help

**Documentation Resources**:

- [Master Architecture](Architecture/MASTER_ARCHITECTURE.md): Complete system architecture
- [Testing Documentation](Testing/TESTING_CONSOLIDATED.md): Validation and troubleshooting
- [API Documentation](API%20Gateway/API_DOCUMENTATION.md): REST API specifications

**Community Support**:

- GitHub Issues: Bug reports and feature requests
- GitHub Discussions: Questions and community support
- Documentation: Comprehensive guides and troubleshooting

---

**This deployment guide provides comprehensive instructions for deploying and maintaining the Eunice Research Platform across all environments, ensuring optimal performance, security, and reliability.**

---

*For technical architecture details, see [Master Architecture Documentation](Architecture/MASTER_ARCHITECTURE.md). For API integration, refer to [API Documentation](API%20Gateway/API_DOCUMENTATION.md).*
