#!/bin/bash

# Memory Agent Service Startup Script

set -e

echo "Starting Memory Agent Service..."

# Set environment variables
export PYTHONPATH="/app:$PYTHONPATH"
export AGENT_TYPE="memory"
export SERVICE_PORT=8009

# Create data directory if it doesn't exist
mkdir -p /tmp/memory_agent_data

# Wait for MCP server to be available
echo "Waiting for MCP server..."
for i in {1..30}; do
    if nc -z mcp-server 9000; then
        echo "MCP server is ready!"
        break
    fi
    echo "Waiting for MCP server... ($i/30)"
    sleep 2
done

# Start the Memory Agent Service
echo "Starting Memory Agent Service on port 8009..."
exec python src/memory_service.py
