#!/bin/bash
# Startup script for containerized API Gateway service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[API Gateway]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[API Gateway]${NC} ✅ $1"
}

print_warning() {
    echo -e "${YELLOW}[API Gateway]${NC} ⚠️  $1"
}

print_error() {
    echo -e "${RED}[API Gateway]${NC} ❌ $1"
}

# Configuration
CONTAINER_NAME="eunice-api-gateway"
IMAGE_NAME="eunice/api-gateway:latest"
NETWORK_NAME="eunice-network"
SERVICE_PORT="8001"

# Command line argument handling
COMMAND=${1:-"start"}

case $COMMAND in
    "build")
        print_status "Building API Gateway container..."
        docker build -t $IMAGE_NAME .
        if [ $? -eq 0 ]; then
            print_success "Container built successfully"
        else
            print_error "Container build failed"
            exit 1
        fi
        ;;
    
    "start")
        print_status "Starting API Gateway service..."
        
        # Check if MCP server is running
        if ! docker ps | grep -q "eunice-mcp-server"; then
            print_warning "MCP server not detected. Starting it first..."
            cd ../mcp-server
            ./start.sh
            cd ../api-gateway
            sleep 5
        fi
        
        # Start with docker-compose
        docker-compose up -d
        
        if [ $? -eq 0 ]; then
            print_success "API Gateway started successfully"
            print_status "Service available at: http://localhost:$SERVICE_PORT"
            print_status "API Documentation: http://localhost:$SERVICE_PORT/docs"
            print_status "Health Check: http://localhost:$SERVICE_PORT/health"
        else
            print_error "Failed to start API Gateway"
            exit 1
        fi
        ;;
    
    "stop")
        print_status "Stopping API Gateway service..."
        docker-compose down
        if [ $? -eq 0 ]; then
            print_success "API Gateway stopped"
        else
            print_error "Failed to stop API Gateway"
            exit 1
        fi
        ;;
    
    "restart")
        print_status "Restarting API Gateway service..."
        $0 stop
        sleep 2
        $0 start
        ;;
    
    "test")
        print_status "Running API Gateway tests..."
        
        # Check if service is running
        if ! docker ps | grep -q $CONTAINER_NAME; then
            print_error "API Gateway is not running. Start it first with: $0 start"
            exit 1
        fi
        
        # Wait for service to be ready
        print_status "Waiting for service to be ready..."
        for i in {1..30}; do
            if curl -f -s http://localhost:$SERVICE_PORT/health > /dev/null; then
                break
            fi
            if [ $i -eq 30 ]; then
                print_error "Service failed to become ready within 30 seconds"
                exit 1
            fi
            sleep 1
        done
        
        # Run tests
        python test_api_gateway.py
        if [ $? -eq 0 ]; then
            print_success "All tests passed"
        else
            print_error "Some tests failed"
            exit 1
        fi
        ;;
    
    "logs")
        print_status "Showing API Gateway logs..."
        docker logs -f $CONTAINER_NAME
        ;;
    
    "health")
        print_status "Checking API Gateway health..."
        
        if ! docker ps | grep -q $CONTAINER_NAME; then
            print_error "API Gateway container is not running"
            exit 1
        fi
        
        # Check Docker health status
        HEALTH_STATUS=$(docker inspect --format='{{.State.Health.Status}}' $CONTAINER_NAME 2>/dev/null || echo "no-health-check")
        
        if [ "$HEALTH_STATUS" = "healthy" ]; then
            print_success "Container health check: $HEALTH_STATUS"
        elif [ "$HEALTH_STATUS" = "no-health-check" ]; then
            print_warning "No health check configured"
        else
            print_warning "Container health check: $HEALTH_STATUS"
        fi
        
        # Check API health endpoint
        if curl -f -s http://localhost:$SERVICE_PORT/health > /dev/null; then
            print_success "API health endpoint responding"
            curl -s http://localhost:$SERVICE_PORT/health | python -m json.tool
        else
            print_error "API health endpoint not responding"
            exit 1
        fi
        ;;
    
    "status")
        print_status "API Gateway service status:"
        
        # Container status
        if docker ps | grep -q $CONTAINER_NAME; then
            print_success "Container: Running"
            CONTAINER_ID=$(docker ps -q -f name=$CONTAINER_NAME)
            CONTAINER_INFO=$(docker inspect --format='{{.State.Status}} ({{.State.StartedAt}})' $CONTAINER_ID)
            echo "  Status: $CONTAINER_INFO"
        else
            print_error "Container: Not running"
        fi
        
        # Port status
        if netstat -ln 2>/dev/null | grep -q ":$SERVICE_PORT "; then
            print_success "Port $SERVICE_PORT: Listening"
        else
            print_warning "Port $SERVICE_PORT: Not listening"
        fi
        
        # API status
        if curl -f -s http://localhost:$SERVICE_PORT/status > /dev/null; then
            print_success "API: Responding"
            curl -s http://localhost:$SERVICE_PORT/status | python -m json.tool
        else
            print_warning "API: Not responding"
        fi
        ;;
    
    "clean")
        print_status "Cleaning up API Gateway resources..."
        
        # Stop and remove containers
        docker-compose down --volumes --remove-orphans
        
        # Remove image
        if docker images | grep -q $IMAGE_NAME; then
            print_status "Removing image: $IMAGE_NAME"
            docker rmi $IMAGE_NAME
        fi
        
        # Clean up volumes
        if docker volume ls | grep -q "eunice-api-gateway"; then
            print_status "Removing volumes..."
            docker volume ls | grep "eunice-api-gateway" | awk '{print $2}' | xargs docker volume rm
        fi
        
        print_success "Cleanup complete"
        ;;
    
    "shell")
        print_status "Opening shell in API Gateway container..."
        if docker ps | grep -q $CONTAINER_NAME; then
            docker exec -it $CONTAINER_NAME /bin/bash
        else
            print_error "Container is not running. Start it first with: $0 start"
            exit 1
        fi
        ;;
    
    "help"|"--help"|"-h")
        echo "API Gateway Service Management Script"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  build     - Build the container image"
        echo "  start     - Start the API Gateway service (default)"
        echo "  stop      - Stop the API Gateway service"
        echo "  restart   - Restart the API Gateway service"
        echo "  test      - Run the test suite"
        echo "  logs      - Show service logs"
        echo "  health    - Check service health"
        echo "  status    - Show detailed service status"
        echo "  clean     - Clean up all resources"
        echo "  shell     - Open shell in container"
        echo "  help      - Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 start          # Start the service"
        echo "  $0 test           # Run tests"
        echo "  $0 health         # Check health"
        echo "  $0 logs           # View logs"
        ;;
    
    *)
        print_error "Unknown command: $COMMAND"
        echo "Use '$0 help' to see available commands"
        exit 1
        ;;
esac
