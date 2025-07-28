#!/bin/sh
set -e

echo "Starting Writer Agent..."
echo "Agent Type: writer"
echo "Port: 8006"
echo "MCP Server: ${MCP_SERVER_URL:-ws://mcp-server:9000}"

# Change to app directory and start the service
cd /app
exec python3 -m uvicorn src.writer_service:app --host 0.0.0.0 --port 8006
