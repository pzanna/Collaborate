#!/bin/bash

# Quick validation script for production deployment
echo "🔍 Validating Production Deployment Setup"
echo "========================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"  
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

echo
echo "Prerequisites:"

# Check Docker
if command -v docker >/dev/null 2>&1; then
    print_status "Docker is installed ($(docker --version | cut -d' ' -f3 | tr -d ','))"
else
    print_error "Docker is not installed"
fi

# Check Docker Compose
if command -v docker compose >/dev/null 2>&1; then
    print_status "Docker Compose is available"
else
    print_error "Docker Compose is not available"
fi

# Check Node.js
if command -v node >/dev/null 2>&1; then
    print_status "Node.js is installed ($(node --version))"
else
    print_error "Node.js is not installed"
fi

# Check npm
if command -v npm >/dev/null 2>&1; then
    print_status "npm is available ($(npm --version))"
else
    print_error "npm is not available"
fi

echo
echo "Files and Directories:"

# Check essential files
files=(
    "./deploy_production.sh"
    "./docker-compose.yml"
    "./frontend/package.json"
    "./infrastructure/nginx/nginx.conf"
    "./.env.example"
)

for file in "${files[@]}"; do
    if [[ -f "$file" ]]; then
        print_status "Found: $file"
    else
        print_error "Missing: $file"
    fi
done

# Check .env file
if [[ -f ".env" ]]; then
    print_status "Environment file (.env) exists"
else
    print_warning "Environment file (.env) not found - create from .env.example"
fi

# Check frontend dependencies
if [[ -d "frontend/node_modules" ]]; then
    print_status "Frontend dependencies installed"
else
    print_warning "Frontend dependencies not installed - will be installed during deployment"
fi

echo
echo "Docker Services:"

# Check if Docker is running
if docker info >/dev/null 2>&1; then
    print_status "Docker daemon is running"
    
    # Check if any Eunice containers are running
    if docker ps --format "table {{.Names}}" | grep -q eunice; then
        print_warning "Some Eunice containers are already running:"
        docker ps --format "table {{.Names}}\t{{.Status}}" | grep eunice
    else
        print_status "No existing Eunice containers running"
    fi
else
    print_error "Docker daemon is not running"
fi

echo
echo "Ready to deploy? Run: ./deploy_production.sh"
