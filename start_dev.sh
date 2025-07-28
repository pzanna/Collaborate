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

# Phase 3: Start core research agents
# Memory agent handles knowledge graph, Executor handles task processing
print_info "Starting core agents (Memory, Executor)..."
docker compose -f docker-compose.secure.yml up -d memory-agent executor-agent

# Phase 4: Start API Gateway 
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

# Note: MCP server uses WebSocket protocol, no HTTP health endpoint available
# Connection status will be verified through agent connections

# Display comprehensive status information if services are healthy
if [ "$services_ready" = true ]; then
    print_status "Core services are ready!"
    echo
    echo "🎯 Development Environment Status:"
    echo "   🔧 MCP Server:    http://localhost:9000 (WebSocket)"
    echo "   🚪 API Gateway:   http://localhost:8001"
    echo "   🧠 Memory Agent:  http://localhost:8009"
    echo "   ⚡ Executor Agent: http://localhost:8008"
    echo "   🔍 PostgreSQL:    localhost:5433"
    echo "   📋 Redis:         localhost:6380"
    echo
    echo "📊 Health & Documentation:"  
    echo "   Health Check:     http://localhost:8001/health"
    echo "   API Docs:         http://localhost:8001/docs"
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
    echo "   - Port conflicts: Check if ports 8001, 8008, 8009, 9000, 5433, 6380 are free"
    echo "   - Resource limits: Ensure at least 2GB RAM available"
    echo "   - Docker issues: Verify Docker daemon is running"
    exit 1
fi
