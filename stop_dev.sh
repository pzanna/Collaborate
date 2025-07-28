#!/bin/bash

# Eunice Research Platform - Stop Development Services
# Stops both frontend and backend services

echo "🛑 Stopping Eunice Development Services"
echo "======================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${RED}🛑 $1${NC}"
}

# Stop React frontend (find and kill vite processes)
print_info "Stopping React frontend..."
pkill -f "vite" 2>/dev/null || true
pkill -f "node.*vite" 2>/dev/null || true

# Stop Docker services
print_info "Stopping Docker services..."
docker compose down --remove-orphans

# Clean up logs if they exist
if [ -f "logs/frontend.log" ]; then
    rm logs/frontend.log
fi

print_status "All services stopped!"
echo
echo "To restart: ./start_dev.sh"
