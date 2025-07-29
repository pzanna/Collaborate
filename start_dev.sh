#!/bin/bash

# ==============================================================================
# Eunice Platform - Development Start Script
# ==============================================================================
# 
# Quick start for development with security-hardened Alpine containers
#
# This script provides a streamlined way to start the core development 
# environment for the Eunice Research Platform using Docker Compose with
# security-hardened Alpine Linux containers.
#
# Services Started:
#   - Redis (port 6380)           - Message queue and caching
#   - PostgreSQL (port 5433)      - Primary database  
#   - MCP Server (port 9000)      - WebSocket communication hub
#   - Memory Agent (port 8009)    - Knowledge graph and context management
#   - Executor Agent (port 8008)  - Task execution and workflow management
#   - API Gateway (port 8001)     - REST API and frontend communication
#
# Prerequisites:
#   - Docker and Docker Compose installed
#   - 2GB+ RAM available
#   - Ports 5433, 6380, 8001, 8008, 8009, 9000 available
#   - .env file (optional, defaults will be used if missing)
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

# Ensure logs directory exists for container logging
mkdir -p logs

# Clean shutdown of any existing containers to ensure fresh start
print_info "Stopping existing services..."
docker compose -f docker-compose.secure.yml down --remove-orphans 2>/dev/null || true

# Phase 1: Start core infrastructure services
# Redis and PostgreSQL must be ready before other services start
print_info "Starting infrastructure (Redis, PostgreSQL)..."
docker compose -f docker-compose.secure.yml up -d redis postgres

# Wait for infrastructure services to be fully ready
# Database connections require this initialization time
print_info "Waiting for infrastructure to be ready..."
sleep 10

# Phase 2: Start MCP server (Model Context Protocol)
# This is the central communication hub that all agents connect to
print_info "Starting MCP server..."
docker compose -f docker-compose.secure.yml up -d mcp-server

# Brief wait for MCP server WebSocket to be available
sleep 5

# Phase 3: Start authentication service
# This handles JWT tokens, user management, and RBAC
print_info "Starting authentication service..."
docker compose -f docker-compose.secure.yml up -d auth-service

# Brief wait for auth service to be ready
sleep 5

# Phase 4: Start core research agents
# Memory agent handles knowledge graph, Executor handles task processing
print_info "Starting core agents (Memory, Executor)..."
docker compose -f docker-compose.secure.yml up -d memory-agent executor-agent

# Phase 5: Start AI service
# This provides LLM integration and handles AI API calls
print_info "Starting AI service..."
docker compose -f docker-compose.secure.yml up -d ai-service

# Phase 6: Start all research workflow agents
# These agents handle the complete research pipeline
print_info "Starting research workflow agents..."
docker compose -f docker-compose.secure.yml up -d \
    planning-agent \
    research-manager-agent \
    literature-agent \
    screening-agent \
    synthesis-agent \
    writer-agent

# Phase 7: Start database service
# This provides database management and maintenance
print_info "Starting database service..."
docker compose -f docker-compose.secure.yml up -d database-service database-agent

# Phase 8: Start API Gateway 
# This provides the REST API interface and frontend communication
print_info "Starting API Gateway..."
docker compose -f docker-compose.secure.yml up -d api-gateway

# Final wait for all services to complete initialization
print_info "Waiting for services to initialize..."
sleep 10

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

# Test Memory Agent health endpoint
if curl -f -s http://localhost:8009/health >/dev/null 2>&1; then
    print_status "Memory Agent is healthy"
else
    echo "❌ Memory Agent health check failed"
    services_ready=false
fi

# Test Executor Agent health endpoint
if curl -f -s http://localhost:8008/health >/dev/null 2>&1; then
    print_status "Executor Agent is healthy"
else
    echo "❌ Executor Agent health check failed"
    services_ready=false
fi

# Test Planning Agent health endpoint
if curl -f -s http://localhost:8007/health >/dev/null 2>&1; then
    print_status "Planning Agent is healthy"
else
    echo "❌ Planning Agent health check failed"
    services_ready=false
fi

# Test Research Manager Agent health endpoint
if curl -f -s http://localhost:8002/health >/dev/null 2>&1; then
    print_status "Research Manager Agent is healthy"
else
    echo "❌ Research Manager Agent health check failed"
    services_ready=false
fi

# Test Literature Agent health endpoint
if curl -f -s http://localhost:8003/health >/dev/null 2>&1; then
    print_status "Literature Agent is healthy"
else
    echo "❌ Literature Agent health check failed"
    services_ready=false
fi

# Test Screening Agent health endpoint
if curl -f -s http://localhost:8004/health >/dev/null 2>&1; then
    print_status "Screening Agent is healthy"
else
    echo "❌ Screening Agent health check failed"
    services_ready=false
fi

# Test Synthesis Agent health endpoint
if curl -f -s http://localhost:8005/health >/dev/null 2>&1; then
    print_status "Synthesis Agent is healthy"
else
    echo "❌ Synthesis Agent health check failed"
    services_ready=false
fi

# Test Writer Agent health endpoint
if curl -f -s http://localhost:8006/health >/dev/null 2>&1; then
    print_status "Writer Agent is healthy"
else
    echo "❌ Writer Agent health check failed"
    services_ready=false
fi

# Test Database Agent health endpoint
if curl -f -s http://localhost:8011/health >/dev/null 2>&1; then
    print_status "Database Agent is healthy"
else
    echo "❌ Database Agent health check failed"
    services_ready=false
fi

# Note: AI service doesn't expose HTTP health endpoint (internal service)
# Note: Database service doesn't expose HTTP health endpoint (internal service)

# Note: MCP server uses WebSocket protocol, no HTTP health endpoint available
# Connection status will be verified through agent connections

# Display comprehensive status information if services are healthy
if [ "$services_ready" = true ]; then
    print_status "Core services are ready!"
    echo
    echo "🎯 Development Environment Status:"
    echo "   🔧 MCP Server:        http://localhost:9000 (WebSocket)"
    echo "   🚪 API Gateway:       http://localhost:8001"
    echo "   🔐 Auth Service:      http://localhost:8013"
    echo "   🧠 Memory Agent:      http://localhost:8009"
    echo "   ⚡ Executor Agent:     http://localhost:8008"
    echo "   � Planning Agent:    http://localhost:8007"
    echo "   �🔍 Research Manager:  http://localhost:8002"
    echo "   📚 Literature Agent:  http://localhost:8003"
    echo "   🔬 Screening Agent:   http://localhost:8004"
    echo "   📝 Synthesis Agent:   http://localhost:8005"
    echo "   ✍️  Writer Agent:      http://localhost:8006"
    echo "   🗄️  Database Agent:    http://localhost:8011"
    echo "   🤖 AI Service:        (Internal - no HTTP endpoint)"
    echo "   💾 Database Service:  (Internal - no HTTP endpoint)"
    echo "   🔍 PostgreSQL:        localhost:5433"
    echo "   📋 Redis:             localhost:6380"
    echo
    echo "📊 Health & Documentation:"  
    echo "   Health Check:     http://localhost:8001/health"
    echo "   Auth Health:      http://localhost:8013/health"
    echo "   API Docs:         http://localhost:8001/docs"
    echo "   Auth API Docs:    http://localhost:8013/docs"
    echo "   Container Status: docker compose -f docker-compose.secure.yml ps"
    echo
    echo "📝 View Logs:"
    echo "   All services:     docker compose -f docker-compose.secure.yml logs -f"
    echo "   Specific service: docker compose -f docker-compose.secure.yml logs -f mcp-server"
    echo
    echo "🛑 To stop development environment:"
    echo "   ./stop_dev.sh"
    echo "   OR: docker compose -f docker-compose.secure.yml down"
    echo
    print_status "Development environment is ready for use!"
else
    echo "❌ Some services failed to start. Check logs:"
    echo "   docker compose -f docker-compose.secure.yml logs"
    echo "   docker compose -f docker-compose.secure.yml ps"
    echo
    echo "💡 Common issues:"
    echo "   - Port conflicts: Check if ports 8001, 8008, 8009, 8013, 9000, 5433, 6380 are free"
    echo "   - Resource limits: Ensure at least 2GB RAM available"
    echo "   - Docker issues: Verify Docker daemon is running"
    exit 1
fi
