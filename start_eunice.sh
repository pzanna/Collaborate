#!/bin/bash

# Start script for Eunice Web UI
# This script starts the MCP server, agents, backend and frontend

echo "🚀 Starting Eunice Web UI..."

# Function to handle cleanup on exit
cleanup() {
    echo "Stopping services..."
    kill $MCP_PID $AGENTS_PID $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Function to stop existing services
stop_existing_services() {
    echo "🛑 Checking for existing services..."
    
    # Stop any existing Python processes for this project
    pkill -f "python mcp_server.py" 2>/dev/null && echo "  ✓ Stopped existing MCP server"
    pkill -f "python agent_launcher.py" 2>/dev/null && echo "  ✓ Stopped existing agents"
    pkill -f "python web_server.py" 2>/dev/null && echo "  ✓ Stopped existing web server"
    
    # Kill processes using the ports we need
    lsof -ti:9000 2>/dev/null | xargs kill -9 2>/dev/null && echo "  ✓ Freed port 9000 (MCP server)"
    lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null && echo "  ✓ Freed port 8000 (web server)"
    lsof -ti:3000 2>/dev/null | xargs kill -9 2>/dev/null && echo "  ✓ Freed port 3000 (frontend)"
    
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

# Start MCP server
echo "🔧 Starting MCP server..."
python mcp_server.py &
MCP_PID=$!

# Wait a moment for MCP server to start
sleep 3

# Start research agents
echo "🤖 Starting research agents..."
python agent_launcher.py &
AGENTS_PID=$!

# Wait a moment for agents to connect
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
echo "🌐 Backend API: http://localhost:8000"
echo "🌐 Frontend:    http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for background processes
wait
