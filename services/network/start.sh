#!/bin/bash

# Network Agent Service Production Startup Script
# This script starts the containerized Network Agent in production mode

set -e

echo "Starting Network Agent Service in Production Mode..."

# Set default values if not provided
export SERVICE_HOST=${SERVICE_HOST:-"0.0.0.0"}
export SERVICE_PORT=${SERVICE_PORT:-"8004"}
export MCP_SERVER_URL=${MCP_SERVER_URL:-"ws://mcp-server:9000"}
export AGENT_TYPE=${AGENT_TYPE:-"network"}
export LOG_LEVEL=${LOG_LEVEL:-"INFO"}

echo "Configuration:"
echo "  Service Host: ${SERVICE_HOST}"
echo "  Service Port: ${SERVICE_PORT}"
echo "  MCP Server URL: ${MCP_SERVER_URL}"
echo "  Agent Type: ${AGENT_TYPE}"
echo "  Log Level: ${LOG_LEVEL}"
echo "  Production Mode: ENABLED"

# Change to source directory
cd /app

# Start the Network Agent service
echo "Starting Network Agent Service..."
exec python -m src.network_service
