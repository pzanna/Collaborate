#!/bin/sh

# MCP Server Development Startup Script
# This script starts the containerized MCP Server with file watching for development

set -e

echo "Starting MCP Server in Development Mode..."

# Set default values if not provided
export HOST=${HOST:-"0.0.0.0"}
export PORT=${PORT:-"9000"}
export LOG_LEVEL=${LOG_LEVEL:-"INFO"}

echo "Configuration:"
echo "  Host: ${HOST}"
echo "  Port: ${PORT}"
echo "  Log Level: ${LOG_LEVEL}"
echo "  Development Mode: ENABLED"

# Check if watchfiles is available (should be pre-installed)
echo "Checking watchfiles availability..."
if ! python -c "import watchfiles" 2>/dev/null; then
    echo "ERROR: watchfiles not found. Installing..."
    pip install watchfiles
fi
echo "watchfiles is available"

# Change to app directory
cd /app

# Start the MCP Server with file watching
# Watch only specific files to avoid permission issues
echo "Starting MCP Server with file watching..."
exec watchfiles 'python mcp_server.py' /app/mcp_server.py /app/config.py
