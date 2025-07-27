#!/bin/bash
export DATABASE_SERVICE_URL="http://localhost:8011"
echo "🚀 Starting API Gateway on port 8001..."
echo "📊 Database Service URL: $DATABASE_SERVICE_URL"
python main.py
