#!/bin/bash

echo "🚀 Setting up Collaborate Web UI..."

# Check if Python virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt
pip install -r requirements-web.txt

# Install Node.js dependencies for frontend
echo "📦 Installing Node.js dependencies..."
cd frontend
npm install

echo "✅ Setup complete!"
echo ""
echo "🎯 To start the application:"
echo "1. Backend:  python web_server.py"
echo "2. Frontend: cd frontend && npm start"
echo ""
echo "🌐 Web UI will be available at:"
echo "   • Backend API: http://localhost:8000"
echo "   • Frontend:    http://localhost:3000"
