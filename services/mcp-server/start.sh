#!/bin/bash
# Enhanced MCP Server Startup Script - Phase 3.1

set -e

echo "🚀 Starting Enhanced MCP Server - Phase 3.1"

# Docker paths for Docker Desktop
DOCKER_BIN="/Applications/Docker.app/Contents/Resources/bin/docker"
DOCKER_COMPOSE_BIN="/Applications/Docker.app/Contents/Resources/cli-plugins/docker-compose"

# Check if Docker Desktop is installed
if [ ! -f "$DOCKER_BIN" ]; then
    echo "❌ Docker Desktop is not installed at expected location"
    echo "   Please install Docker Desktop from https://www.docker.com/products/docker-desktop/"
    exit 1
fi

# Check if Docker Desktop is running
if ! "$DOCKER_BIN" version >/dev/null 2>&1; then
    echo "❌ Docker Desktop is not running"
    echo "   Please start Docker Desktop and wait for it to be ready"
    echo "   You can start it from Applications or by running:"
    echo "   open /Applications/Docker.app"
    exit 1
fi

# Create aliases for easier use
alias docker="$DOCKER_BIN"
alias docker-compose="$DOCKER_BIN compose"

echo "✅ Docker Desktop is running"

# Navigate to the MCP server directory
cd "$(dirname "$0")"

# Set default environment variables if not provided
export JWT_SECRET="${JWT_SECRET:-enhanced-mcp-server-jwt-secret-phase3.1}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-password}"

echo "📦 Building Enhanced MCP Server image..."
"$DOCKER_BIN" compose build mcp-server

echo "🔧 Starting infrastructure services..."
"$DOCKER_BIN" compose up -d postgres redis

echo "⏳ Waiting for database to be ready..."
sleep 10

# Check if PostgreSQL is ready
until "$DOCKER_BIN" compose exec postgres pg_isready -U postgres > /dev/null 2>&1; do
    echo "⏳ Waiting for PostgreSQL..."
    sleep 2
done

echo "✅ PostgreSQL is ready"

# Check if Redis is ready
until "$DOCKER_BIN" compose exec redis redis-cli ping > /dev/null 2>&1; do
    echo "⏳ Waiting for Redis..."
    sleep 2
done

echo "✅ Redis is ready"

echo "🔥 Starting Enhanced MCP Server..."
"$DOCKER_BIN" compose up -d mcp-server

echo "⏳ Waiting for MCP Server to start..."
sleep 5

# Health check
echo "🏥 Checking server health..."
max_retries=30
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    if curl -s -f http://localhost:8080/health > /dev/null; then
        echo "✅ Enhanced MCP Server is healthy!"
        break
    else
        echo "⏳ Waiting for server to be healthy... ($((retry_count + 1))/$max_retries)"
        sleep 2
        retry_count=$((retry_count + 1))
    fi
done

if [ $retry_count -eq $max_retries ]; then
    echo "❌ Server health check failed after $max_retries attempts"
    echo "📋 Server logs:"
    "$DOCKER_BIN" compose logs mcp-server
    exit 1
fi

echo ""
echo "🎉 Enhanced MCP Server Phase 3.1 is running successfully!"
echo ""
echo "📊 Service URLs:"
echo "   • MCP WebSocket:    ws://localhost:9000"
echo "   • Health Check:     http://localhost:8080/health"
echo "   • Metrics:          http://localhost:9090/metrics"
echo "   • PostgreSQL:       localhost:5432"
echo "   • Redis:            localhost:6379"
echo ""
echo "🔧 Management Commands:"
echo "   • View logs:        $DOCKER_BIN compose logs -f mcp-server"
echo "   • Stop services:    $DOCKER_BIN compose down"
echo "   • Restart server:   $DOCKER_BIN compose restart mcp-server"
echo "   • Test client:      python test_client.py"
echo ""
echo "🐛 Debug Services (optional):"
echo "   • Redis Commander:  $DOCKER_BIN compose --profile debug up -d redis-commander"
echo "   • Prometheus:       $DOCKER_BIN compose --profile monitoring up -d prometheus"
echo ""

# Show current status
echo "📋 Current Status:"
"$DOCKER_BIN" compose ps

echo ""
echo "🎯 Enhanced MCP Server Phase 3.1 is ready for agent connections!"
