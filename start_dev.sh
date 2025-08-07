#!/bin/bash

# ==============================================================================
# Eunice Platform - Development Start Script
# ==============================================================================
# 
# Quick start for development with Docker Compose development configuration
#
# This script provides a streamlined way to start the development environment
# for the Eunice Research Platform using Docker Compose with development
# features including file watching, hot-reloading, and debug logging.
#
# Development Features:
#   - File watching with watchfiles for hot-reloading
#   - Volume mounts for live code updates
#   - Debug logging and development environment variables
#   - Development build targets with additional tools
#
# Services Started:
#   - PostgreSQL (port 5433)      - Primary database  
#   - Docker Socket Proxy (internal) - Secure Docker API access for auth service
#   - MCP Server (port 9000)      - WebSocket communication hub
#   - Auth Service (port 8013)    - JWT authentication and user management
#   - Memory Service (port 8009)  - Knowledge graph and context management
#   - Research Manager (port 8002) - Research workflow coordination
#   - Database Service (internal)  - Database connection management
#   - Network Service (internal)   - Google search and web research
#   - API Gateway (port 8001)     - REST API and frontend communication
#   - Frontend Dev Server (5173)  - React web UI with hot-reload
#
# Prerequisites:
#   - Docker and Docker Compose installed
#   - 2GB+ RAM available
#   - Ports 5433, 8001-8002, 8009, 8013, 9000 available
#   - .env file with required environment variables:
#     * GOOGLE_API_KEY (for Google Custom Search via Network Service)
#     * GOOGLE_SEARCH_ENGINE_ID (for Google Custom Search)
#     * AUTH_SECRET_KEY (for Authentication Service)
#     * CORE_API_KEY (optional, for Literature research via Network Service)
#     * OPENALEX_EMAIL (optional, for Literature research via Network Service)
#
# Usage:
#   ./start_dev.sh
#
# To stop:
#   ./stop_dev.sh
#
# ==============================================================================

set -e  # Exit on any error

echo "🚀 Starting Eunice Development Environment"
echo "========================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Load environment variables from .env file (optional)
# This allows customization of database passwords, API keys, etc.
if [[ -f ".env" ]]; then
    source .env
    print_status "Environment loaded from .env file"
else
    print_warning ".env file not found, using container defaults"
fi

# Validate critical environment variables
print_info "Validating environment variables..."
missing_vars=()

# Check Google API credentials (required for Network Service)
if [[ -z "${GOOGLE_API_KEY}" ]]; then
    missing_vars+=("GOOGLE_API_KEY")
fi
if [[ -z "${GOOGLE_SEARCH_ENGINE_ID}" ]]; then
    missing_vars+=("GOOGLE_SEARCH_ENGINE_ID")
fi

# Check Auth secret key (required for Auth Service)
if [[ -z "${AUTH_SECRET_KEY}" ]]; then
    missing_vars+=("AUTH_SECRET_KEY")
fi

if [[ ${#missing_vars[@]} -gt 0 ]]; then
    print_warning "Missing required environment variables:"
    for var in "${missing_vars[@]}"; do
        echo "   ❌ $var"
    done
    echo
    echo "💡 Create a .env file in the project root with:"
    echo "   GOOGLE_API_KEY=your_google_api_key_here"
    echo "   GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id_here" 
    echo "   AUTH_SECRET_KEY=your_secure_secret_key_here"
    echo
    echo "Optional API keys for enhanced functionality:"
    echo "   CORE_API_KEY=your_core_api_key_here"
    echo "   OPENALEX_EMAIL=your_email@example.com"
    echo
    print_warning "Services will start but some features may not work without these API keys"
    echo
else
    print_status "All critical environment variables are set"
fi

# Ensure logs directory exists for container logging
mkdir -p logs

# Clean shutdown of any existing containers to ensure fresh start
print_info "Stopping existing services..."
docker compose -f docker-compose.yml -f docker-compose.dev.yml down --remove-orphans 2>/dev/null || true

# Phase 1: Start core infrastructure services
# PostgreSQL and Docker Socket Proxy must be ready before other services start
print_info "Starting infrastructure (PostgreSQL, Docker Socket Proxy)..."
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d postgres docker-socket-proxy

# Wait for infrastructure services to be fully ready
# Database connections require this initialization time
print_info "Waiting for infrastructure to be ready..."
sleep 10

# Phase 2: Start MCP server (Model Context Protocol)
# This is the central communication hub that all agents connect to
print_info "Starting MCP server..."
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d mcp-server

# Brief wait for MCP server WebSocket to be available
sleep 5

# Phase 3: Start authentication service
# This handles JWT tokens, user management, and RBAC
print_info "Starting authentication service..."
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d auth-service

# Brief wait for auth service to be ready
sleep 5

# Phase 4: Start core services
# Memory service and Database service provide core functionality
print_info "Starting core services (Memory, Database, Network)..."
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d memory-service database-service network-service

# Phase 5: Start research workflow agents
# Research Manager agent handles the research pipeline
print_info "Starting research workflow agents..."
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d research-manager-agent

# Phase 6: Start API Gateway 
# This provides the REST API interface and frontend communication
print_info "Starting API Gateway..."
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d api-gateway

# Phase 9: Start Frontend Development Server
# This starts the Vite dev server locally for hot-reload development
print_info "Starting Frontend Development Server..."
if command -v npm >/dev/null 2>&1; then
    cd frontend
    # Install dependencies if node_modules doesn't exist
    if [ ! -d "node_modules" ]; then
        print_info "Installing frontend dependencies..."
        npm install
    fi
    # Start Vite dev server in background
    npm run dev > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > ../logs/frontend.pid
    cd ..
    print_status "Frontend dev server started (PID: $FRONTEND_PID)"
else
    print_warning "npm not found - frontend dev server not started"
    print_warning "To start manually: cd frontend && npm run dev"
fi

# Final wait for all services to complete initialization
print_info "Waiting for services to initialize..."
sleep 20

# Health check phase - verify critical services are responding
print_info "Testing service health..."

services_ready=true

# Test API Gateway health endpoint (primary interface)
if curl -f -s http://localhost:8001/health >/dev/null 2>&1; then
    print_status "API Gateway is healthy"
else
    echo "❌ API Gateway health check failed"
    services_ready=false
fi

# Test Authentication Service health endpoint
if curl -f -s http://localhost:8013/health >/dev/null 2>&1; then
    print_status "Authentication Service is healthy"
else
    echo "❌ Authentication Service health check failed"
    services_ready=false
fi

# Test Memory Service health endpoint
if curl -f -s http://localhost:8009/health >/dev/null 2>&1; then
    print_status "Memory Service is healthy"
else
    echo "❌ Memory Service health check failed"
    services_ready=false
fi

# Test Research Manager Agent health endpoint
if curl -f -s http://localhost:8002/health >/dev/null 2>&1; then
    print_status "Research Manager Agent is healthy"
else
    echo "❌ Research Manager Agent health check failed"
    services_ready=false
fi

# Note: Docker Socket Proxy is an internal service (no external port exposed)
# Its health is managed by Docker Compose internal health checks
print_status "Docker Socket Proxy is running (internal service)"

# Note: Database service and Network service don't expose HTTP health endpoints (internal services)
print_status "Database Service and Network Service are running (internal services)"

# Note: MCP server uses WebSocket protocol, no HTTP health endpoint available
# Connection status will be verified through agent connections
print_status "MCP Server is running (WebSocket service)"

# Display comprehensive status information if services are healthy
if [ "$services_ready" = true ]; then
    print_status "Core services are ready!"
    echo
    echo "🎯 Development Environment Status:"
    echo "   🔧 MCP Server:        http://localhost:9000 (WebSocket)"
    echo "   🚪 API Gateway:       http://localhost:8001"
    echo "   🔐 Auth Service:      http://localhost:8013"
    echo "   🧠 Memory Service:    http://localhost:8009"
    echo "   🔍 Research Manager:  http://localhost:8002"
    echo "   🐳 Docker Socket Proxy: (Internal service - no external access)"
    echo "   💾 Database Service:  (Internal - no HTTP endpoint)"
    echo "   🌐 Network Service:   (Internal - no HTTP endpoint)"
    echo "   �️  PostgreSQL:        localhost:5433"
    echo
    echo "📊 Health & Documentation:"  
    echo "   Health Check:     http://localhost:8001/health"
    echo "   Auth Health:      http://localhost:8013/health"
    echo "   API Docs:         http://localhost:8001/docs"
    echo "   Auth API Docs:    http://localhost:8013/docs"
    echo "   Container Status: docker compose -f docker-compose.yml -f docker-compose.dev.yml ps"
    echo
    echo "🔧 Development Features:"
    echo "   File Watching:    Enabled for MCP Server and API Gateway"
    echo "   Volume Mounts:    Live code updates without rebuilds"
    echo "   Debug Logging:    Enhanced logging for all services"
    echo "   Hot Reload:       Code changes trigger automatic restarts"
    echo
    echo "📝 View Logs:"
    echo "   All services:     docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f"
    echo "   Specific service: docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f mcp-server"
    echo
    echo "🛑 To stop development environment:"
    echo "   ./stop_dev.sh"
    echo "   OR: docker compose -f docker-compose.yml -f docker-compose.dev.yml down"
    echo
    print_status "Development environment is ready for use!"
else
    echo "❌ Some services failed to start. Check logs:"
    echo "   docker compose -f docker-compose.yml -f docker-compose.dev.yml logs"
    echo "   docker compose -f docker-compose.yml -f docker-compose.dev.yml ps"
    echo
    echo "💡 Common issues:"
    echo "   - Port conflicts: Check if ports 8001-8002, 8009, 8013, 9000, 5433 are free"
    echo "   - Resource limits: Ensure at least 2GB RAM available"
    echo "   - Docker issues: Verify Docker daemon is running"
    exit 1
fi
