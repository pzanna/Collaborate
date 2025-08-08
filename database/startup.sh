#!/bin/bash
# Database Service Startup Script
#
# Pure Database Management Service
# - Database schema initialization and maintenance only
# - No API endpoints (handled by API Gateway)

set -e

echo "🚀 Starting Eunice Database Service..."

# Step 1: Initialize the database schema
echo "📊 Initializing database schema..."
python3 init_db.py

if [ $? -eq 0 ]; then
    echo "✅ Database initialization completed successfully!"
else
    echo "❌ Database initialization failed!"
    exit 1
fi

# Step 2: Start pure database service
echo "🔧 Starting Database Service"
echo "   → Database management and health monitoring only"
echo "   → API operations handled by API Gateway"
exec python3 database_service.py
