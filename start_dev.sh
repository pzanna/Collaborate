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

# Start API Gateway for frontend communication
print_info "Starting API Gateway..."
docker compose up -d api-gateway

# Wait for API Gateway
sleep 5

# Test backend services
print_info "Testing backend services..."
backend_ready=true

if ! curl -f http://localhost:8001/health >/dev/null 2>&1; then
    echo "❌ API Gateway failed to start"
    backend_ready=false
fi

if [ "$backend_ready" = true ]; then
    print_status "Backend services are ready!"
    
    # Start React frontend
    print_info "Starting React frontend..."
    cd frontend
    
    # Check if node_modules exists, install if not
    if [ ! -d "node_modules" ]; then
        print_info "Installing frontend dependencies..."
        npm install
    fi
    
    # Start the React dev server in background
    print_info "Launching React development server..."
    nohup node /Users/paulzanna/Github/Eunice/frontend/node_modules/.bin/vite > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    
    # Wait for frontend to start
    sleep 5
    
    # Test frontend
    if curl -f http://localhost:5173/ >/dev/null 2>&1; then
        print_status "Frontend is ready!"
        echo
        echo "🎯 Services are running:"
        echo "   📱 React Frontend: http://localhost:5173/"
        echo "   🚪 API Gateway: http://localhost:8001"
        echo "   📊 Health check: http://localhost:8001/health"
        echo
        echo "📝 Logs:"
        echo "   Frontend: tail -f logs/frontend.log"
        echo "   Backend: docker compose logs -f"
        echo
        echo "🛑 To stop:"
        echo "   Frontend: kill $FRONTEND_PID"
        echo "   Backend: docker compose down"
        echo
        echo "   Or use: ./stop_dev.sh"
    else
        echo "❌ Frontend failed to start. Check logs: tail -f logs/frontend.log"
    fi
    
    cd ..
else
    echo "❌ Backend services failed to start. Check logs:"
    echo "   docker compose logs"
fi
