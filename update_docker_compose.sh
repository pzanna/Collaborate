#!/bin/bash

# Update docker-compose.yml to remove agent port mappings
# Agents are now pure MCP clients - no HTTP endpoints needed

DOCKER_COMPOSE_FILE="/Users/paulzanna/Github/Eunice/docker-compose.yml"

echo "🔧 Updating docker-compose.yml for pure MCP agent architecture..."
echo "Removing port mappings for agents (8002-8009) - they now communicate via MCP only"

# Create backup
cp "$DOCKER_COMPOSE_FILE" "${DOCKER_COMPOSE_FILE}.backup"

# Remove agent port mappings using sed
sed -i '' '/- "800[2-9]:800[2-9]"/d' "$DOCKER_COMPOSE_FILE"

# Also remove any health check commands that use HTTP
sed -i '' '/curl.*localhost:800[2-9]/d' "$DOCKER_COMPOSE_FILE"
sed -i '' '/test:.*curl.*800[2-9]/d' "$DOCKER_COMPOSE_FILE"

# Update build contexts to use new agent files
sed -i '' 's/synthesis_service.py/synthesis_agent.py/g' "$DOCKER_COMPOSE_FILE"
sed -i '' 's/writer_service.py/writer_agent.py/g' "$DOCKER_COMPOSE_FILE"

echo "✅ Updated docker-compose.yml:"
echo "  - Removed port mappings for agents (8002-8009)"
echo "  - Removed HTTP health checks for agents"
echo "  - Updated service entry points"
echo ""
echo "📋 Architecture Summary:"
echo "  🔹 API Gateway (8001) - ✅ Keeps HTTP for client access"
echo "  🔹 MCP Server (9000) - ✅ Keeps HTTP for WebSocket connections"  
echo "  🔹 All Agents - ✅ No ports exposed (pure MCP clients)"
echo ""
echo "Architecture Compliance: ✅ ACHIEVED"
