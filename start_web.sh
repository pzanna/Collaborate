#!/bin/bash

# Start script for Collaborate Web UI
# This script starts both the backend and frontend in development mode

echo "🚀 Starting Collaborate Web UI..."

# Function to handle cleanup on exit
cleanup() {
    echo "Stopping services..."
    kill $MCP_PID $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Activate Python virtual environment
source .venv/bin/activate

# Start MCP server
echo "🔧 Starting MCP server..."
python -m src.mcp.server &
MCP_PID=$!

# Wait a moment for MCP server to start
sleep 2

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
echo "🌐 Backend API: http://localhost:8000"
echo "🌐 Frontend:    http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for background processes
wait
