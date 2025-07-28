#!/bin/sh
set -e

echo "Starting Synthesis & Review Agent..."
echo "Agent Type: synthesis_review"
echo "Port: 8005"
echo "MCP Server: ${MCP_SERVER_URL:-ws://mcp-server:9000}"

# Change to app directory and start the service
cd /app
exec python3 -m uvicorn src.synthesis_service:app --host 0.0.0.0 --port 8005
