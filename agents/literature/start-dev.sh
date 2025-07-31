#!/bin/bash

# Literature Agent Service Development Startup Script
# This script starts the containerized Literature Agent with file watching for development

set -e

echo "Starting Literature Agent Service in Development Mode..."

# Set default values if not provided
export SERVICE_HOST=${SERVICE_HOST:-"0.0.0.0"}
export SERVICE_PORT=${SERVICE_PORT:-"8003"}
export MCP_SERVER_URL=${MCP_SERVER_URL:-"ws://mcp-server:9000"}
export AGENT_TYPE=${AGENT_TYPE:-"literature"}
export LOG_LEVEL=${LOG_LEVEL:-"INFO"}

echo "Configuration:"
echo "  Service Host: ${SERVICE_HOST}"
echo "  Service Port: ${SERVICE_PORT}"
echo "  MCP Server URL: ${MCP_SERVER_URL}"
echo "  Agent Type: ${AGENT_TYPE}"
echo "  Log Level: ${LOG_LEVEL}"
echo "  Development Mode: ENABLED"

# Check if watchfiles is available (should be pre-installed)
echo "Checking watchfiles availability..."
if ! python -c "import watchfiles" 2>/dev/null; then
    echo "ERROR: watchfiles not found. This should be pre-installed in requirements.txt"
    exit 1
fi
echo "watchfiles is available"

# Change to source directory
cd /app

# Start the Literature Agent service with file watching
echo "Starting Literature Agent Service with file watching..."
exec watchfiles --filter python 'python src/literature_service.py' /app/src