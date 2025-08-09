#!/bin/sh

# API Gateway Development Startup Script
# This script starts the containerized API Gateway with file watching for development

set -e

echo "Starting API Gateway in Development Mode..."

# Set default values if not provided
export HOST=${HOST:-"0.0.0.0"}
export PORT=${PORT:-"8001"}
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

# Start the API Gateway with file watching
echo "Starting API Gateway with file watching..."
exec watchfiles --filter python 'python src/api_gateway.py' .