#!/bin/bash

# Eunice Research Platform - Production Deployment Script
# Version 0.3 Microservices Architecture with Secure AI Service

set -e  # Exit on any error

echo "🚀 Eunice Research Platform - Production Deployment"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"
LOG_DIR="logs"

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Pre-deployment checks
echo
print_info "Running pre-deployment checks..."

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker Desktop."
    exit 1
fi
print_status "Docker is running"

# Check if Node.js is available for frontend build
if ! command -v node >/dev/null 2>&1; then
    print_error "Node.js is not installed. Please install Node.js to build the frontend."
    exit 1
fi
print_status "Node.js is available ($(node --version))"

# Check if npm is available
if ! command -v npm >/dev/null 2>&1; then
    print_error "npm is not installed. Please install npm to build the frontend."
    exit 1
fi
print_status "npm is available ($(npm --version))"

# Check if .env file exists
if [[ ! -f "$ENV_FILE" ]]; then
    print_error ".env file not found. Please create it with your API keys."
    print_info "Use .env.example as a template"
    exit 1
fi
print_status ".env file found"

# Load environment variables
source "$ENV_FILE"

# Validate API keys are present
if [[ -z "$OPENAI_API_KEY" || -z "$ANTHROPIC_API_KEY" || -z "$XAI_API_KEY" ]]; then
    print_error "One or more API keys are missing from .env file"
    print_info "Required: OPENAI_API_KEY, ANTHROPIC_API_KEY, XAI_API_KEY"
    exit 1
fi

# Mask keys for logging
OPENAI_MASKED="${OPENAI_API_KEY:0:10}...${OPENAI_API_KEY: -4}"
ANTHROPIC_MASKED="${ANTHROPIC_API_KEY:0:10}...${ANTHROPIC_API_KEY: -4}"
XAI_MASKED="${XAI_API_KEY:0:10}...${XAI_API_KEY: -4}"

print_status "API keys loaded: OpenAI ($OPENAI_MASKED), Anthropic ($ANTHROPIC_MASKED), XAI ($XAI_MASKED)"

# Create logs directory
mkdir -p "$LOG_DIR"
print_status "Log directory created: $LOG_DIR"

echo
print_info "Building and starting services..."

# Build React Frontend
print_info "Building React frontend..."
cd frontend

# Install frontend dependencies if node_modules doesn't exist
if [[ ! -d "node_modules" ]]; then
    print_info "Installing frontend dependencies..."
    npm install
fi

# Build the frontend for production
print_info "Building frontend for production..."
npm run build

# Verify build was successful
if [[ ! -d "dist" ]]; then
    print_error "Frontend build failed - dist directory not found"
    exit 1
fi
print_status "Frontend built successfully"

cd ..

# Stop any existing containers
print_info "Stopping existing containers..."
docker compose down --remove-orphans 2>/dev/null || true

# Build all services
print_info "Building Docker images..."
docker compose build --no-cache

# Start infrastructure services first
print_info "Starting infrastructure services..."
docker compose up -d redis postgres

# Wait for infrastructure to be ready
print_info "Waiting for infrastructure to be ready..."
sleep 10

# Verify infrastructure health
print_info "Checking infrastructure health..."
if ! docker compose exec redis redis-cli ping | grep -q PONG; then
    print_error "Redis is not responding"
    exit 1
fi
print_status "Redis is healthy"

if ! docker compose exec postgres pg_isready -U postgres | grep -q "accepting connections"; then
    print_error "PostgreSQL is not responding"
    exit 1
fi
print_status "PostgreSQL is healthy"

# Start core services
print_info "Starting core services..."
docker compose up -d mcp-server database-service

# Wait for core services
sleep 15

# Start AI service
print_info "Starting AI service..."
docker compose up -d ai-service

# Wait for AI service to initialize
sleep 10

# Test AI service
print_info "Testing AI service health..."
if curl -f http://localhost:8010/health >/dev/null 2>&1; then
    print_status "AI service is healthy"
else
    print_warning "AI service health check failed, checking logs..."
    docker compose logs ai-service --tail=20
fi

# Start Planning Agent
print_info "Starting Planning Agent..."
docker compose up -d planning-agent

# Wait for Planning Agent
sleep 10

# Start API Gateway
print_info "Starting API Gateway..."
docker compose up -d api-gateway

# Wait for API Gateway to initialize
sleep 15

# Final health checks
echo
print_info "Performing comprehensive health checks..."

# Infrastructure health checks
print_info "Checking infrastructure services..."
INFRA_SERVICES=(
    "Redis:redis-cli ping"
    "PostgreSQL:pg_isready -U postgres"
)

ALL_HEALTHY=true

for service_info in "${INFRA_SERVICES[@]}"; do
    IFS=':' read -r service_name service_cmd <<< "$service_info"
    
    if docker compose exec $(echo $service_name | tr '[:upper:]' '[:lower:]') $service_cmd >/dev/null 2>&1; then
        print_status "$service_name is healthy"
    else
        print_error "$service_name health check failed"
        ALL_HEALTHY=false
    fi
done

# Application service endpoints
print_info "Checking application services..."
SERVICES=(
    "MCP Server:http://localhost:9000/health"
    "AI Service:http://localhost:8010/health"
    "Planning Agent:http://localhost:8007/health"
    "API Gateway:http://localhost:8001/health"
)

for service_info in "${SERVICES[@]}"; do
    IFS=':' read -r service_name service_url <<< "$service_info"
    
    if curl -f "$service_url" >/dev/null 2>&1; then
        print_status "$service_name is healthy"
    else
        print_error "$service_name health check failed"
        ALL_HEALTHY=false
    fi
done

# Start nginx with frontend
print_info "Starting nginx with React frontend..."
docker compose up -d nginx --profile production

# Wait for nginx to start
sleep 5

# Check nginx and frontend
print_info "Checking frontend deployment..."
if curl -f "http://localhost/nginx-health" >/dev/null 2>&1; then
    print_status "Nginx is healthy"
else
    print_error "Nginx health check failed"
    ALL_HEALTHY=false
fi

if curl -f "http://localhost/" >/dev/null 2>&1; then
    print_status "Frontend is accessible"
else
    print_error "Frontend is not accessible"
    ALL_HEALTHY=false
fi

echo
if [ "$ALL_HEALTHY" = true ]; then
    print_status "🎉 All services are healthy! Deployment successful!"
    echo
    print_info "🌐 Frontend Application:"
    echo "  • React Frontend: http://localhost/"
    echo "  • Frontend Health: http://localhost/nginx-health"
    echo
    print_info "🔗 Backend API endpoints:"
    echo "  • API Gateway: http://localhost:8001"
    echo "  • MCP Server: http://localhost:9000"
    echo "  • AI Service: http://localhost:8010"
    echo "  • Planning Agent: http://localhost:8007"
    echo
    print_info "📡 API Access (via nginx proxy):"
    echo "  • Frontend API calls: http://localhost/api/*"
    echo "  • Direct API access: http://localhost:8001/*"
    echo
    print_info "🗄️  Infrastructure endpoints:"
    echo "  • Redis: localhost:6380"
    echo "  • PostgreSQL: localhost:5433"
    echo
    print_info "📊 Container status:"
    docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
    echo
    print_info "🔍 Monitoring:"
    echo "  • Container logs: docker compose logs -f [service-name]"
    echo "  • Service status: docker compose ps"
    echo "  • Stop all: docker compose down"
else
    print_warning "Some services failed health checks. Check logs with:"
    echo "  docker compose logs [service-name]"
    echo
    print_info "🔧 Common troubleshooting commands:"
    echo "  • Check all container status: docker compose ps"
    echo "  • View recent logs: docker compose logs --tail=50"
    echo "  • Restart failed service: docker compose restart [service-name]"
    echo "  • Rebuild and restart: docker compose up -d --build [service-name]"
    echo
    print_info "🐛 Service-specific logs:"
    echo "  • Frontend (nginx): docker compose logs nginx"
    echo "  • API Gateway: docker compose logs api-gateway"
    echo "  • MCP Server: docker compose logs mcp-server"
    echo "  • AI Service: docker compose logs ai-service"
    echo "  • Planning Agent: docker compose logs planning-agent"
    echo
    print_info "🌐 Frontend troubleshooting:"
    echo "  • Rebuild frontend: cd frontend && npm run build"
    echo "  • Check nginx config: docker compose exec nginx nginx -t"
    echo "  • Access frontend files: docker compose exec nginx ls -la /usr/share/nginx/html"
fi

echo
print_info "Deployment complete! Check the logs directory for detailed logs."
