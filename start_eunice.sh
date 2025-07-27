#!/bin/bash

# Start script for Eunice Web UI
# This script starts the MCP server, agents, backend and frontend

echo "🚀 Starting Eunice Web UI..."

# Function to handle cleanup on exit
cleanup() {
    echo "Stopping services..."
    kill $MCP_PID $AGENTS_PID $BACKEND_PID $FRONTEND_PID $REDIS_PID $WORKER_PID $GATEWAY_PID 2>/dev/null
    
    # Also ensure all agent launchers are killed
    pkill -f "agent_launcher.py" 2>/dev/null
    
    # Stop Redis if we started it
    if [ ! -z "$REDIS_PID" ]; then
        kill $REDIS_PID 2>/dev/null
    fi
    
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Function to stop existing services
stop_existing_services() {
    echo "🛑 Checking for existing services..."
    
    # Stop any existing Python processes for this project
    pkill -f "python -m src.mcp" 2>/dev/null && echo "  ✓ Stopped existing MCP server"
    pkill -f "python agent_launcher.py" 2>/dev/null && echo "  ✓ Stopped existing agents"
    pkill -f "agent_launcher.py" 2>/dev/null && echo "  ✓ Stopped any remaining agent launchers"
    pkill -f "python web_server.py" 2>/dev/null && echo "  ✓ Stopped existing web server"
    
    # Kill processes using the ports we need
    lsof -ti:9000 2>/dev/null | xargs kill -9 2>/dev/null && echo "  ✓ Freed port 9000 (MCP server)"
    lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null && echo "  ✓ Freed port 8000 (web server)"
    lsof -ti:8001 2>/dev/null | xargs kill -9 2>/dev/null && echo "  ✓ Freed port 8001 (API gateway)"
    lsof -ti:3000 2>/dev/null | xargs kill -9 2>/dev/null && echo "  ✓ Freed port 3000 (frontend)"
    lsof -ti:6379 2>/dev/null | xargs kill -9 2>/dev/null && echo "  ✓ Freed port 6379 (Redis)"
    
    # Wait a moment for processes to fully terminate
    sleep 2
    echo "✓ Cleanup complete"
}

# Stop any existing services before starting
stop_existing_services

# Activate Python virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✓ Activated virtual environment"
fi

# Start Redis server
echo "📋 Starting Redis server..."
redis-server --daemonize yes --port 6379
REDIS_PID=$!
echo "✓ Redis server started on port 6379"

# Wait a moment for Redis to start
sleep 2

# Start MCP server
echo "🔧 Starting MCP server..."
python -m src.mcp &
MCP_PID=$!

# Wait a moment for MCP server to start
sleep 3

# Start research agents
echo "🤖 Starting research agents..."
python agent_launcher.py &
AGENTS_PID=$!

# Wait a moment for agents to connect
sleep 3

# Start task queue worker
echo "⚙️  Starting task queue worker..."
python start_worker.py &
WORKER_PID=$!

# Wait a moment for worker to start
sleep 2

# Start API Gateway
echo "🌐 Starting API Gateway..."
python start_api_gateway.py &
GATEWAY_PID=$!

# Wait a moment for gateway to start
sleep 3

# Start backend server
echo "🖥️  Starting backend server..."
python web_server.py --reload &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Start frontend development server
echo "⚛️  Starting frontend development server..."
cd frontend
npm start &
FRONTEND_PID=$!

# Wait for user to stop
echo ""
echo "✅ All services are running!"
echo "🔧 MCP Server:  http://localhost:9000"
echo "🤖 Agents:      4 research agents running"
echo "📋 Redis:       localhost:6379 (task queue)"
echo "⚙️  Workers:     1 task queue worker running"
echo "🌐 API Gateway: http://localhost:8001"
echo "🖥️  Backend API: http://localhost:8000"
echo "🌐 Frontend:    http://localhost:3000"
echo ""
echo "📚 API Documentation: http://localhost:8001/docs"
echo "📊 Queue Dashboard:   http://localhost:8001/queue/statistics"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for background processes
wait
