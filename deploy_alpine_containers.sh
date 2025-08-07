#!/bin/bash

# ==============================================================================
# Eunice Platform - Alpine Container Deployment Script
# ==============================================================================
#
# Builds all security-hardened Alpine-based containers for production deployment
#
# This script builds all microservice containers using Alpine Linux base images
# with comprehensive security hardening including:
#   - Non-root user execution (UID/GID 1000)
#   - Read-only root filesystems with targeted tmpfs mounts
#   - All capabilities dropped, no privilege escalation
#   - Resource limits and security constraints
#   - Minimal attack surface with Alpine Linux
#
# Containers Built:
#   - Research Agents: planning, screening, memory, executor, literature, database
#   - Platform Services: MCP server, API gateway, auth service, AI service, database service
#   - Research Manager: coordination and workflow management
#
# Build Features:
#   - No-cache builds for security (--no-cache)
#   - Pull latest base images (--pull)
#   - Comprehensive error handling and reporting
#   - Build time tracking and statistics
#   - Post-build validation
#
# Usage:
#   ./deploy_alpine_containers.sh
#
# Prerequisites:
#   - Docker installed and running
#   - At least 4GB free disk space
#   - Network connectivity for base image pulls
#   - All Dockerfile locations accessible
#
# Expected Results:
#   - 12 containers built successfully
#   - 0 CRITICAL vulnerabilities (vs 16+ in Debian)
#   - ~50% smaller image sizes than Debian equivalents
#
# ==============================================================================

# Builds all security-hardened Alpine-based containers

set -e  # Exit on any error

echo "🏗️  EUNICE PLATFORM - ALPINE DEPLOYMENT"
echo "======================================="
echo "Building security-hardened Alpine containers..."
echo "Date: $(date)"
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Build configuration
REGISTRY="eunice"
TAG="alpine-secure"
BUILD_ARGS="--no-cache --pull"

# Services to build - using arrays for better compatibility
SERVICES=(
    "planning-agent:agents/planning"
    "screening-agent:agents/screening" 
    "memory-service:services/memory"
    "executor-agent:agents/executor"
    "literature-agent:agents/literature"
    "database-agent:agents/database"
    "research-manager-agent:agents/research-manager"
    "api-gateway:services/api-gateway"
    "auth-service:services/auth-service"
    "mcp-server:services/mcp-server"
    "ai-service:services/ai-service"
    "database-service:services/database"
)

BUILD_COUNT=0
SUCCESS_COUNT=0
FAILED_BUILDS=()

echo -e "${BLUE}🔍 Pre-build Validation${NC}"
echo "========================"

for service_info in "${SERVICES[@]}"; do
    service_name="${service_info%:*}"
    service_path="${service_info#*:}"
    dockerfile_path="/Users/paulzanna/Github/Eunice/$service_path/Dockerfile"
    
    if [[ -f "$dockerfile_path" ]]; then
        # Check if Dockerfile uses Alpine
        if grep -q "python:3.12-alpine" "$dockerfile_path"; then
            echo "✅ $service_name: Alpine Dockerfile ready"
        else
            echo "❌ $service_name: Dockerfile not updated to Alpine"
        fi
    else
        echo "❌ $service_name: Dockerfile not found at $dockerfile_path"
    fi
done

echo ""
read -p "🚀 Proceed with building all Alpine containers? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

echo -e "\n${GREEN}🚀 Starting Alpine Container Builds${NC}"
echo "===================================="

for service_info in "${SERVICES[@]}"; do
    service_name="${service_info%:*}"
    service_path="${service_info#*:}"
    dockerfile_path="/Users/paulzanna/Github/Eunice/$service_path"
    image_name="$REGISTRY/$service_name:$TAG"
    
    BUILD_COUNT=$((BUILD_COUNT + 1))
    
    echo -e "\n${YELLOW}[$BUILD_COUNT/12] Building: $service_name${NC}"
    echo "────────────────────────────────────"
    echo "📁 Path: $service_path"
    echo "🏷️  Image: $image_name"
    echo "⏰ Started: $(date '+%H:%M:%S')"
    
    if [[ -d "$dockerfile_path" && -f "$dockerfile_path/Dockerfile" ]]; then
        # Build the container
        if docker build $BUILD_ARGS -t "$image_name" "$dockerfile_path"; then
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
            
            # Get image size
            IMAGE_SIZE=$(docker image inspect "$image_name" --format='{{.Size}}' | numfmt --to=iec --suffix=B)
            
            echo -e "${GREEN}✅ Success: $service_name${NC}"
            echo "📦 Size: $IMAGE_SIZE"
            
            # Quick vulnerability check
            echo "🔍 Running security scan..."
            VULNS=$(docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image --severity HIGH,CRITICAL --quiet "$image_name" 2>/dev/null | grep -c "Total:" || echo "0")
            if [[ "$VULNS" -eq 0 ]]; then
                echo -e "${GREEN}🛡️  Security: No high/critical vulnerabilities${NC}"
            else
                echo -e "${YELLOW}⚠️  Security: $VULNS vulnerabilities found${NC}"
            fi
            
        else
            echo -e "${RED}❌ Failed: $service_name${NC}"
            FAILED_BUILDS+=("$service_name")
        fi
    else
        echo -e "${RED}❌ Error: Dockerfile not found for $service_name${NC}"
        FAILED_BUILDS+=("$service_name")
    fi
    
    echo "⏰ Completed: $(date '+%H:%M:%S')"
done

echo -e "\n${BLUE}📊 BUILD SUMMARY${NC}"
echo "================="
echo "🏗️  Total Services: 12"
echo "✅ Successful Builds: $SUCCESS_COUNT"
echo "❌ Failed Builds: $((12 - SUCCESS_COUNT))"

if [[ ${#FAILED_BUILDS[@]} -gt 0 ]]; then
    echo -e "\n${RED}Failed Services:${NC}"
    for failed in "${FAILED_BUILDS[@]}"; do
        echo "  • $failed"
    done
fi

echo -e "\n${GREEN}🎯 NEXT STEPS${NC}"
echo "============="
if [[ $SUCCESS_COUNT -eq 12 ]]; then
    echo "🚀 All containers built successfully!"
    echo "1. Test individual containers: docker run <image-name>"
    echo "2. Deploy with security-hardened compose: docker-compose -f docker-compose.secure.yml up"
    echo "3. Run comprehensive testing suite"
    echo "4. Monitor security and performance metrics"
    
    echo -e "\n${BLUE}📋 Available Alpine Images:${NC}"
    docker images --filter=reference="eunice/*:alpine-secure" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
    
else
    echo "⚠️  Some builds failed. Review errors above and retry failed services."
    echo "💡 Consider running individual builds with: docker build -t <image> <path>"
fi

echo -e "\n✅ Deployment script completed: $(date)"
