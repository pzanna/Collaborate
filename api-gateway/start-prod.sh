#!/bin/sh

# API Gateway Production Startup Script
# This script starts the containerized API Gateway in production mode

set -e

echo "Starting API Gateway in Production Mode..."

# Set default values if not provided
export HOST=${HOST:-"0.0.0.0"}
export PORT=${PORT:-"8001"}
export LOG_LEVEL=${LOG_LEVEL:-"INFO"}

echo "Configuration:"
echo "  Host: ${HOST}"
echo "  Port: ${PORT}"
echo "  Log Level: ${LOG_LEVEL}"
echo "  Production Mode: ENABLED"

# Change to app directory
cd /app

# Start the API Gateway directly
echo "Starting API Gateway..."
exec python src/api_gateway.py
