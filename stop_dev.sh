#!/bin/bash

# ==============================================================================
# Eunice Platform - Development Stop Script
# ==============================================================================
#
# Cleanly stops all development services and performs cleanup
#
# This script stops all Docker Compose services started by start_dev.sh using
# the development configuration with file watching and debug features,
# removes orphaned containers, and cleans up any dangling resources.
# 
# Services Stopped:
#   - API Gateway (port 8001)
#   - Auth Service (port 8013)
#   - Memory Service (port 8009) 
#   - Research Manager Agent (port 8002)
#   - Database Service (internal)
#   - Docker Socket Proxy (port 2375)
#   - PostgreSQL (port 5433)
#   - Frontend Dev Server (port 5173)
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
docker compose -f docker-compose.secure.yml -f docker-compose.dev.yml down --remove-orphans

# Stop any remaining Eunice containers that might be running independently
print_info "Stopping any remaining Eunice containers..."
REMAINING_CONTAINERS=$(docker ps -q --filter "name=eunice-*" 2>/dev/null || true)
if [ -n "$REMAINING_CONTAINERS" ]; then
    docker stop $REMAINING_CONTAINERS >/dev/null 2>&1 || true
    docker rm $REMAINING_CONTAINERS >/dev/null 2>&1 || true
    print_status "Stopped remaining Eunice containers"
else
    print_info "No additional Eunice containers found"
fi

# Stop frontend development server if running
print_info "Stopping frontend development server..."
if [ -f "logs/frontend.pid" ]; then
    FRONTEND_PID=$(cat logs/frontend.pid)
    if kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID"
        print_status "Frontend development server stopped (PID: $FRONTEND_PID)"
    else
        print_info "Frontend development server was not running"
    fi
    rm -f logs/frontend.pid
else
    print_info "No frontend PID file found"
fi

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
