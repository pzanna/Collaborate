#!/bin/bash

# Database Agent Service Startup Script
# This script starts the containerized Database Agent as an MCP client

set -e

echo "Starting Database Agent Service..."

# Set default values if not provided
export SERVICE_HOST=${SERVICE_HOST:-"0.0.0.0"}
export SERVICE_PORT=${SERVICE_PORT:-"8011"}
export MCP_SERVER_URL=${MCP_SERVER_URL:-"ws://mcp-server:9000"}
export AGENT_TYPE=${AGENT_TYPE:-"database"}
export LOG_LEVEL=${LOG_LEVEL:-"INFO"}
export DATABASE_URL=${DATABASE_URL:-"postgresql://postgres:password@postgres:5432/eunice"}

echo "Configuration:"
echo "  Service Host: ${SERVICE_HOST}"
echo "  Service Port: ${SERVICE_PORT}"
echo "  MCP Server URL: ${MCP_SERVER_URL}"
echo "  Agent Type: ${AGENT_TYPE}"
echo "  Log Level: ${LOG_LEVEL}"
echo "  Database URL: ${DATABASE_URL}"

# Change to source directory
cd /app

# Start the Database Agent service
echo "Starting Database Agent Service..."
exec python -m src.database_service
