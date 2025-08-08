#!/bin/sh

# api-gateway Service Development Startup Script
# This script starts the api-gateway service with file watching for development

set -e

echo "🚀 Starting api-gateway Service in development mode..."
echo "📁 Working directory: $(pwd)"

# Check if watchfiles is available and working
if python3 -c "import watchfiles; print('✅ watchfiles is available')" 2>/dev/null; then
    USE_WATCHFILES=true
else
    echo "⚠️  watchfiles not available or incompatible - falling back to direct execution"
    USE_WATCHFILES=false
fi

# Load environment variables if .env file exists
if [ -f .env ]; then
    echo "📝 Loading environment variables from .env"
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set development environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
export SERVICE_NAME="${SERVICE_NAME:-api-gateway}"
export SERVICE_HOST="${SERVICE_HOST:-0.0.0.0}"
export SERVICE_PORT="${SERVICE_PORT:-8001}"
export LOG_LEVEL="${LOG_LEVEL:-DEBUG}"
export DEVELOPMENT_MODE="${DEVELOPMENT_MODE:-true}"
export WATCHFILES_FORCE_POLLING="${WATCHFILES_FORCE_POLLING:-1}"

if [ "$USE_WATCHFILES" = true ]; then
    echo "🔍 File watching enabled for development"
else
    echo "⚠️  File watching disabled (watchfiles not available)"
fi
echo "🔧 Service: ${SERVICE_NAME}"
echo "🌐 Host: ${SERVICE_HOST}"
echo "🔌 Port: ${SERVICE_PORT}"
echo "📊 Log Level: ${LOG_LEVEL}"
echo "🛠️ Development Mode: ${DEVELOPMENT_MODE}"

# Health check
echo "🏥 Performing startup health checks..."

# Check if config file exists
if [ ! -f "config/config.json" ]; then
    echo "❌ Configuration file config/config.json not found"
    exit 1
fi

echo "✅ All health checks passed"

if [ "$USE_WATCHFILES" = true ]; then
    echo "🔍 Starting api-gateway service with file watching..."
    # Start with file watching using watchfiles
    exec python3 -m watchfiles --filter python src.main.sync_main
else
    echo "🎯 Starting api-gateway service in development mode (no file watching)..."
    # Start directly without file watching
    exec python3 src/main.py
fi
