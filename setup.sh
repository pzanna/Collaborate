#!/bin/bash

# Setup script for Eunice AI Platform
# This script sets up the Python environment and installs all dependencies

echo "🚀 Setting up Eunice AI Platform..."

# Check if Python 3.8+ is available
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "🐍 Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
else
    echo "📦 Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "📥 Installing Python dependencies..."
pip install -r requirements.txt

# Check if Node.js is installed for frontend
if command -v node &> /dev/null; then
    node_version=$(node --version)
    echo "🟢 Node.js version: $node_version"
    
    # Install frontend dependencies
    if [ -d "frontend" ]; then
        echo "⚛️  Installing frontend dependencies..."
        cd frontend
        npm install
        cd ..
    fi
else
    echo "⚠️  Node.js not found. Please install Node.js to run the frontend."
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p logs
mkdir -p data
mkdir -p exports

# Set executable permissions
echo "🔑 Setting executable permissions..."
chmod +x start_web.sh
chmod +x mcp_server.py
chmod +x agent_launcher.py
chmod +x test_research.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 To start the application:"
echo "   ./start_eunice.sh"
echo ""
echo "🧪 To test research functionality:"
echo "   python test_research.py"
echo ""
echo "📚 For more information, see README.md"
