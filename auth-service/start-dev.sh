#!/bin/sh

# auth-service Service Development Startup Script
# This script starts the auth-service service with file watching for development

set -e

echo "🚀 Starting auth-service Service in development mode..."
echo "📁 Working directory: $(pwd)"

# Check if watchfiles is available
python3 -c "import watchfiles; print('✅ watchfiles is available')" 2>/dev/null || {
    echo "❌ watchfiles not found. Installing..."
    pip install watchfiles
}

# Load environment variables if .env file exists
if [ -f .env ]; then
    echo "📝 Loading environment variables from .env"
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set development environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
export SERVICE_NAME="${SERVICE_NAME:-auth-service}"
export SERVICE_HOST="${SERVICE_HOST:-0.0.0.0}"
export SERVICE_PORT="${SERVICE_PORT:-8013}"
export LOG_LEVEL="${LOG_LEVEL:-DEBUG}"
export DEVELOPMENT_MODE="${DEVELOPMENT_MODE:-true}"
export WATCHFILES_FORCE_POLLING="${WATCHFILES_FORCE_POLLING:-1}"

echo "🔍 File watching enabled for development"
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
echo "🔍 Starting auth-service service with file watching..."

# Start with file watching using watchfiles
exec python3 -m watchfiles src.main.main --args src/main.py
