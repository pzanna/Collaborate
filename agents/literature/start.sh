#!/bin/bash

# Literature Search Agent startup script
echo "Starting Literature Search Agent..."

# Check configuration
if [ ! -f "/app/config/config.json" ]; then
    echo "Warning: Configuration file not found, using defaults"
fi

# Start the service
cd /app
exec python src/literature_service.py
