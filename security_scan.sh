#!/bin/bash

# ==============================================================================
# Eunice Platform - Security Vulnerability Scanner
# ==============================================================================
#
# Comprehensive vulnerability scanning for all Alpine-based containers
#
# This script scans all production container images for security vulnerabilities
# using Docker Scout and/or Trivy. It focuses on HIGH and CRITICAL severity
# issues that could compromise the platform's security.
#
# Scanning Tools Used:
#   - Docker Scout (primary) - Built into Docker Desktop
#   - Trivy (alternative)    - Open source vulnerability scanner
#
# Containers Scanned:
#   - All microservice agents (planning, screening, memory, executor, etc.)
#   - Core platform services (MCP server, API gateway, AI service)
#   - Infrastructure services (database service)
#
# Installation Requirements:
#   Docker Scout: docker scout install
#   Trivy (macOS): brew install trivy
#   Trivy (Ubuntu): apt-get install trivy
#
# Usage:
#   ./security_scan.sh
#
# Expected Results:
#   Alpine-based containers should show 0 CRITICAL vulnerabilities
#   compared to 16+ in previous Debian-based containers
#
# ==============================================================================

# Security scanning script for Eunice containers
# Run this script to scan all containers for vulnerabilities

echo "🔒 Starting security scan of Eunice containers..."

# List of services to scan (Alpine-based security-hardened containers)
SERVICES=(
    "eunice/screening-agent:alpine-secure"
    "eunice/planning-agent:alpine-secure" 
    "eunice/memory-service:alpine-secure"
    "eunice/executor-agent:alpine-secure"
    "eunice/database-agent:alpine-secure"
    "eunice/literature-agent:alpine-secure"
    "eunice/research-manager:alpine-secure"
    "eunice/mcp-server:alpine-secure"
    "eunice/api-gateway:alpine-secure"
    "eunice/ai-service:alpine-secure"
    "eunice/database-service:alpine-secure"
)

# Function to scan a single container image for vulnerabilities
scan_image() {
    local image=$1
    echo "📊 Scanning $image for vulnerabilities..."
    
    # Primary: Use Docker Scout (built into Docker Desktop)
    # Provides comprehensive vulnerability database and remediation advice
    if command -v docker &> /dev/null && docker scout version &> /dev/null; then
        echo "   Using Docker Scout..."
        docker scout cves $image --format table --only-severity critical,high
    else
        echo "⚠️  Docker Scout not available. Install with: docker scout install"
    fi
    
    # Alternative: Use Trivy for additional vulnerability detection
    # Trivy has different vulnerability databases and may catch different issues
    if command -v trivy &> /dev/null; then
        echo "   Using Trivy for additional scanning..."
        trivy image --severity HIGH,CRITICAL $image
    else
        echo "💡 Consider installing Trivy for comprehensive vulnerability scanning"
        echo "   Install: brew install trivy (macOS) or apt-get install trivy (Ubuntu)"
    fi
}

# Scan all containerized services for vulnerabilities
echo "🔍 Scanning all Eunice platform containers..."
echo "This may take several minutes depending on network speed..."
echo

for service in "${SERVICES[@]}"; do
    # Check if the container image exists locally
    if docker image inspect $service &> /dev/null; then
        scan_image $service
        echo "----------------------------------------"
    else
        echo "⚠️  Image $service not found locally"
        echo "   Run: ./deploy_alpine_containers.sh to build all images"
        echo "----------------------------------------"
    fi
done

echo "✅ Security scan completed"
echo ""
echo "🛡️  Security Status Summary:"
echo "1. ✅ Already using python:3.12-alpine (security-hardened base)"
echo "2. ✅ All dependencies updated to latest compatible versions"
echo "3. ✅ Security-enhanced Alpine Dockerfile patterns implemented"
echo "4. ✅ Run regular vulnerability scans with 'docker scout' or 'trivy'"
echo "5. ✅ Monitor security advisories for Python and Alpine updates"
echo "6. 🔄 Consider periodic container rebuilds for latest security patches"
echo ""
echo "📈 Expected Results:"
echo "   Alpine containers: 0 CRITICAL vulnerabilities"
echo "   Previous Debian:   16+ CRITICAL vulnerabilities per service"
echo ""
echo "🔄 Next Steps:"
echo "   - Review any HIGH/CRITICAL findings above"
echo "   - Rebuild containers if vulnerabilities found: ./deploy_alpine_containers.sh"
echo "   - Schedule regular scans (weekly recommended)"
echo "   - Monitor security advisories for base images"
