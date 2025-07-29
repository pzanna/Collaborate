#!/bin/bash

# Eunice Authentication Service Startup Script

set -e

echo "Starting Eunice Authentication Service..."

# Set default environment variables if not provided
export HOST=${HOST:-0.0.0.0}
export PORT=${PORT:-8013}
export DATABASE_URL=${DATABASE_URL:-postgresql://postgres:password@eunice-postgres:5432/eunice}

# Start the service
exec python -m uvicorn src.main:app --host $HOST --port $PORT --reload
