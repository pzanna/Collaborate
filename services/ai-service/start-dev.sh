#!/bin/bash

# AI Service Development Startup Script
# This script starts the containerized AI Service with file watching for development

set -e

echo "Starting AI Service in Development Mode..."

# Set default values if not provided
export SERVICE_HOST=${SERVICE_HOST:-"0.0.0.0"}
export SERVICE_PORT=${SERVICE_PORT:-"8007"}
export MCP_SERVER_URL=${MCP_SERVER_URL:-"ws://mcp-server:9000"}
export LOG_LEVEL=${LOG_LEVEL:-"INFO"}

echo "Configuration:"
echo "  Service Host: ${SERVICE_HOST}"
echo "  Service Port: ${SERVICE_PORT}"
echo "  MCP Server URL: ${MCP_SERVER_URL}"
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

# Start the AI Service with file watching
echo "Starting AI Service with file watching..."
exec watchfiles --filter python 'python -m src.mcp_ai_service' /app/src
