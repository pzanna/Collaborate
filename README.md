# Eunice Research Platform

## Overview

Eunice is an advanced research platform named after the AI from William Gibson's novel [Agency](<https://en.wikipedia.org/wiki/Agency_(novel)>). It's designed to facilitate sophisticated research workflows through an integrated microservices architecture that supports collaborative research, project management, and intelligent agent coordination.

The platform specializes in hierarchical research organization, multi-agent collaboration, and provides comprehensive tools for managing complex research projects across multiple domains.

## 🚀 Key Features

### Core Functionality

- **Project Management**: Comprehensive project organization with hierarchical research topics
- **Conversation Tracking**: Advanced conversation management with persistent storage
- **Research Task Organization**: Structured task management with dependency tracking
- **Hierarchical Data Models**: Complex research structures with nested relationships
- **Multi-Agent Coordination**: Intelligent agent personas for specialized research domains

### Research Capabilities

- **Cost Estimation System**: Budget tracking and resource management
- **Dependency Management**: Automatic task dependency resolution
- **Parallelism Coordination**: Efficient multi-threaded research execution
- **Memory Management**: Persistent storage for research artifacts and conversations
- **Export Functionality**: Research data export in multiple formats (PDF, Markdown)

### Technical Features

- **MCP (Model Context Protocol) Server**: Advanced microservices coordination
- **Real-time WebSocket Communication**: Live updates and collaboration
- **RESTful API**: Comprehensive backend API for all platform operations
- **Modern React Frontend**: Responsive web interface with TypeScript
- **SQLite Database**: Reliable data persistence with asynchronous operations

## 🏗️ Architecture

Eunice follows a microservices architecture with the following key components:

- **Web Interface**: React/TypeScript frontend with Redux state management
- **API Gateway**: FastAPI-based backend with WebSocket support
- **MCP Server**: Microservices control plane for agent coordination
- **Research Manager**: Oversees research operations and agent coordination
- **Agent System**: Specialized AI agents for different research domains
- **Storage Layer**: SQLite databases for conversations, memory, and collaboration data

For detailed architecture information, see [Architecture Documentation](docs/Architecture.md).

## 🧬 Research Agent Personas

The platform includes specialized agent personas for interdisciplinary research:

- **Neurobiologist**: Brain mapping, neuron extraction, and viability assessments
- **Computational Neuroscientist**: Neural activity modeling and bio-digital interfacing
- **AI/ML Engineer & Data Scientist**: ANN development and experimental data analysis
- **Animal Biologist & Bioethics Specialist**: Animal welfare and regulatory compliance
- **Technical/Scientific Writer**: Documentation, manuscripts, and grant proposals

See [Research Team Documentation](docs/Research_team.md) for detailed role descriptions.

## 🛠️ Installation & Setup

### Prerequisites

- Python 3.8+
- Node.js 16+
- Git

### Quick Start

1. **Clone the repository**

   ```bash
   git clone https://github.com/pzanna/Eunice.git
   cd Eunice
   ```

2. **Backend Setup**

   ```bash
   # Install Python dependencies
   pip install -r requirements.txt

   # Set up environment
   python setup.py

   # Configure API keys in .env file
   # Add your OpenAI and xAI API keys
   ```

3. **Frontend Setup**

   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

4. **Start the Platform**

   ```bash
   # Start all services
   ./start_eunice.sh

   # Or start individually:
   # Backend: python web_server.py
   # MCP Server: python mcp_server.py
   # Frontend: cd frontend && npm start
   ```

### Alternative Setup Scripts

- `./setup.sh` - Basic Python environment setup
- `./setup_web.sh` - Web-specific setup with frontend build

## 📁 Project Structure

```text
Eunice/
├── src/                    # Python source code
│   ├── agents/            # AI agent implementations
│   ├── ai_clients/        # AI service integrations
│   ├── core/              # Core platform logic
│   ├── mcp/              # Model Context Protocol server
│   ├── models/           # Data models
│   ├── storage/          # Database and storage
│   └── utils/            # Utility functions
├── frontend/             # React TypeScript frontend
│   ├── src/components/   # UI components
│   ├── src/services/     # API services
│   └── src/store/        # Redux store
├── docs/                # Documentation
├── tests/               # Test suites
├── config/              # Configuration files
├── logs/                # Application logs
└── exports/             # Research exports
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/test_unit_*.py          # Unit tests
pytest tests/test_integration.py     # Integration tests
pytest tests/test_performance_e2e.py # Performance tests
```

## 📊 Monitoring & Logs

The platform generates detailed logs for monitoring:

- `logs/agents.log` - Agent coordination and activities
- `logs/ai_api.log` - AI service interactions
- `logs/eunice.log` - Collaboration events
- `logs/mcp_server.log` - MCP server operations

## 🔧 Configuration

Key configuration files:

- `.env` - API keys and environment variables
- `config/default_config.json` - Default platform settings
- `pytest.ini` - Test configuration

## 📚 Documentation

- [Architecture Overview](docs/Architecture.md)
- [Research Manager](docs/Research_Manager.md)
- [Research Team Roles](docs/Research_team.md)
- [Cost Estimation System](docs/Cost_Estimation_System.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Follow the [Python coding guidelines](.github/copilot-instructions.md)
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## 📄 License

This project is part of ongoing research and development. Please refer to the project maintainers for licensing information.

## 🙏 Acknowledgments

Named after Eunice, the AI character from William Gibson's "Agency" - a novel that explores themes of artificial intelligence, research collaboration, and the intersection of technology with human endeavor.
