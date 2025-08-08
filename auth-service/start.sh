#!/bin/sh

# auth-service Service Production Startup Script
# This script starts the auth-service service in production mode

set -e

echo "🚀 Starting auth-service Service in production mode..."
echo "📁 Working directory: $(pwd)"

# Load environment variables if .env file exists
if [ -f .env ]; then
    echo "📝 Loading environment variables from .env"
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set default environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
export SERVICE_NAME="${SERVICE_NAME:-auth-service}"
export SERVICE_HOST="${SERVICE_HOST:-0.0.0.0}"
export SERVICE_PORT="${SERVICE_PORT:-8013}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

echo "🔧 Service: ${SERVICE_NAME}"
echo "🌐 Host: ${SERVICE_HOST}"
echo "🔌 Port: ${SERVICE_PORT}"
echo "📊 Log Level: ${LOG_LEVEL}"

# Health check
echo "🏥 Performing startup health checks..."

# Check if required environment variables are set
if [ -z "$SERVICE_NAME" ]; then
    echo "❌ SERVICE_NAME environment variable is not set"
    exit 1
fi

# Check if config file exists
if [ ! -f "config/config.json" ]; then
    echo "❌ Configuration file config/config.json not found"
    exit 1
fi

# Check Python dependencies
python3 -c "import sys; print(f'✅ Python {sys.version}')"

echo "✅ All health checks passed"
echo "🎯 Starting auth-service service..."

# Start the service
exec python3 -m src.main
