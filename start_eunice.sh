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
