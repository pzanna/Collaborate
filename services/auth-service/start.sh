#!/bin/bash

# Eunice Authentication Service Startup Script

set -e

echo "Starting Eunice Authentication Service..."

# Set default environment variables if not provided
export HOST=${HOST:-0.0.0.0}
export PORT=${PORT:-8013}
export DATABASE_URL=${DATABASE_URL:-sqlite:///./auth.db}

# Start the service
exec python -m uvicorn src.main:app --host $HOST --port $PORT --reload
