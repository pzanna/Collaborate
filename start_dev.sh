#!/bin/bash

# Eunice Research Platform - Quick Development Start
# Starts essential services for development testing

set -e

echo "🚀 Quick Development Start - Eunice AI Service"
echo "============================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Load environment
if [[ -f ".env" ]]; then
    source .env
    print_status "Environment loaded"
else
    echo "❌ .env file not found"
    exit 1
fi

# Stop any existing containers
print_info "Stopping existing containers..."
docker compose down --remove-orphans 2>/dev/null || true

# Start minimal infrastructure
print_info "Starting infrastructure..."
docker compose up -d redis postgres

# Wait for infrastructure
sleep 8

# Start AI service only for testing
print_info "Starting AI service..."
docker compose up -d ai-service

# Wait for AI service
sleep 10

# Test AI service
print_info "Testing AI service..."
if curl -f http://localhost:8010/health >/dev/null 2>&1; then
    print_status "AI service is ready!"
    echo
    echo "🎯 AI Service is running at: http://localhost:8010"
    echo "📊 Health endpoint: http://localhost:8010/health"
    echo "🧪 Run integration tests: python test_integration.py"
    echo "🛑 Stop services: docker compose down"
else
    echo "❌ AI service failed to start. Check logs:"
    echo "   docker compose logs ai-service"
fi
