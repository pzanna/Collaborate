#!/bin/bash

# Research Manager Agent startup script
echo "Starting Research Manager Agent..."

# Check configuration
if [ ! -f "/app/config/config.json" ]; then
    echo "Warning: Configuration file not found, using defaults"
fi

# Start the service
cd /app
exec python src/research_manager_service.py
