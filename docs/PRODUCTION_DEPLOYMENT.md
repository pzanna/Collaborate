# Eunice Production Deployment Guide

## Overview

The production deployment includes both the backend microservices and the React frontend, served through nginx as a reverse proxy and static file server.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   React App     │    │      nginx       │    │  Backend APIs   │
│  (Static Files) │◄───┤  (Port 80)       ├───►│  (Port 8001)    │ 
│                 │    │ - Serves Frontend │    │ - API Gateway   │
└─────────────────┘    │ - Proxies /api/*  │    │ - MCP Server    │
                       └──────────────────┘    │ - AI Service    │
                                              │ - Planning Agent │
                                              └─────────────────┘
```

## Quick Deployment

1. **Prerequisites:**

   ```bash
   # Ensure you have:
   - Docker & Docker Compose
   - Node.js & npm
   - Valid API keys in .env file
   ```

2. **Deploy:**

   ```bash
   ./deploy_production.sh
   ```

3. **Access:**
   - **Frontend:** <http://localhost/>
   - **API:** <http://localhost/api/>*

## Services Deployed

### Frontend

- **React Application** served via nginx on port 80
- **Static Assets** cached and optimized
- **API Proxy** routes `/api/*` requests to backend

### Backend Services

- **API Gateway** (Port 8001) - Main API endpoint
- **MCP Server** (Port 9000) - Message coordination
- **AI Service** - AI model integration
- **Planning Agent** (Port 8007) - Task planning
- **Database Agent** (Port 8008) - Database operations

### Infrastructure

- **PostgreSQL** (Port 5433) - Primary database
- **Redis** (Port 6380) - Caching and messaging
- **nginx** (Port 80) - Reverse proxy & frontend server

## Configuration Files

- **`deploy_production.sh`** - Main deployment script
- **`infrastructure/nginx/nginx.conf`** - nginx configuration
- **`docker-compose.yml`** - Service orchestration
- **`.env`** - Environment variables and API keys

## Frontend Build Process

The deployment script automatically:

1. Installs frontend dependencies (`npm install`)
2. Builds React app for production (`npm run build`)
3. Serves static files through nginx
4. Configures API proxy to backend

## Monitoring & Troubleshooting

### Health Checks

```bash
# Frontend
curl http://localhost/nginx-health

# Backend services
curl http://localhost:8001/health
curl http://localhost:8007/health
curl http://localhost:9000/health
```

### Logs

```bash
# All services
docker compose logs -f

# Specific services
docker compose logs -f nginx
docker compose logs -f api-gateway
docker compose logs -f mcp-server
```

### Common Issues

1. **Frontend not loading:**

   ```bash
   # Check nginx logs
   docker compose logs nginx
   
   # Verify frontend build
   ls -la frontend/dist/
   ```

2. **API requests failing:**

   ```bash
   # Check API Gateway
   curl http://localhost:8001/health
   
   # Check nginx proxy config
   docker compose exec nginx nginx -t
   ```

3. **Service startup failures:**

   ```bash
   # Check container status
   docker compose ps
   
   # Restart specific service
   docker compose restart [service-name]
   ```

## Security Features

- **Rate limiting** on API endpoints
- **CORS headers** properly configured
- **Security headers** (XSS, CSRF protection)
- **Static asset caching** with proper headers

## Scaling Considerations

- nginx can be configured for load balancing
- Backend services can be scaled horizontally
- Database connection pooling is configured
- Redis handles session/cache management

## Shutdown

```bash
docker compose down
```

This stops all services and cleans up containers while preserving data volumes.
