#!/bin/bash

# ==============================================================================
# Eunice Platform - Development Stop Script
# ==============================================================================
#
# Cleanly stops all development services and performs cleanup
#
# This script stops all Docker Compose services started by start_dev.sh,
# removes orphaned containers, and cleans up any dangling resources.
# 
# Services Stopped:
#   - API Gateway (port 8001)
#   - Memory Agent (port 8009) 
#   - Executor Agent (port 8008)
#   - MCP Server (port 9000)
#   - PostgreSQL (port 5433)
#   - Redis (port 6380)
#
# What it does:
#   1. Stops all Docker Compose services gracefully
#   2. Removes orphaned containers
#   3. Cleans up dangling containers (optional)
#   4. Preserves data volumes and images
#
# Usage:
#   ./stop_dev.sh
#
# Note: This only stops containers, does not remove:
#   - Docker images (use: docker image prune)
#   - Data volumes (use: docker volume prune) 
#   - Networks (use: docker network prune)
#
# ==============================================================================

echo "🛑 Stopping Eunice Development Environment"
echo "=========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${RED}🛑 $1${NC}"
}

# Gracefully stop all Docker Compose services
# This sends SIGTERM to containers, allowing them to shutdown cleanly
print_info "Stopping all services..."
docker compose -f docker-compose.secure.yml down --remove-orphans

# Clean up any orphaned containers that might be left behind
# These can occur from previous failed starts or manual container operations
print_info "Cleaning up orphaned containers..."
docker container prune -f >/dev/null 2>&1 || true

print_status "Development environment stopped!"
echo
echo "🔄 To restart: ./start_dev.sh"
echo
echo "🧹 Optional cleanup commands:"
echo "   Remove unused images:  docker image prune -a"
echo "   Remove unused volumes: docker volume prune"  
echo "   Remove unused networks: docker network prune"
echo "   Complete cleanup:      docker system prune -a"
