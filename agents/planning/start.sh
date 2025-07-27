#!/bin/bash

# Planning Agent Service Startup Script
# This script starts the containerized Planning Agent as an MCP client

set -e

echo "Starting Planning Agent Service..."

# Set default values if not provided
export SERVICE_HOST=${SERVICE_HOST:-"0.0.0.0"}
export SERVICE_PORT=${SERVICE_PORT:-"8007"}
export MCP_SERVER_URL=${MCP_SERVER_URL:-"ws://mcp-server:9000"}
export AGENT_TYPE=${AGENT_TYPE:-"planning"}
export LOG_LEVEL=${LOG_LEVEL:-"INFO"}

echo "Configuration:"
echo "  Service Host: ${SERVICE_HOST}"
echo "  Service Port: ${SERVICE_PORT}"
echo "  MCP Server URL: ${MCP_SERVER_URL}"
echo "  Agent Type: ${AGENT_TYPE}"
echo "  Log Level: ${LOG_LEVEL}"

# Change to source directory
cd /app

# Start the Planning Agent service
echo "Starting Planning Agent Service..."
exec python -m src.planning_service
