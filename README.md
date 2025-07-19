# Collaborate - Multi-AI Research Collaboration Platform

A comprehensive AI collaboration platform that enables coordinated conversations between multiple AI providers (OpenAI and xAI) with real-time streaming, research management, and intelligent agent coordination.

## 🌟 Key Features

### Core AI Collaboration

- **Multi-AI Coordination**: Seamless collaboration between OpenAI (GPT-4.1-mini) and xAI (Grok-3-mini)
- **Real-Time Streaming**: Word-by-word streaming responses with interruption detection
- **Smart Response Coordination**: Intelligent handoffs and conversation repair
- **Context-Aware Conversations**: Persistent memory across conversations and projects

### Research Management System

- **Research Agents**: Specialized agents for Retrieval, Reasoning, Execution, and Memory
- **MCP Integration**: Model Context Protocol for agent coordination
- **Task Management**: Asynchronous task processing with priority queuing
- **Knowledge Graph**: Interconnected knowledge storage and retrieval

### Web Interface

- **Modern React UI**: Slack/Teams-style chat interface
- **Real-Time Updates**: WebSocket connections for live collaboration
- **Mobile Responsive**: Touch-optimized for mobile and tablet usage
- **Export Capabilities**: Multiple formats (JSON, Markdown, PDF, HTML)

### CLI Interface

- **Interactive Chat**: Terminal-based real-time conversations
- **Project Management**: Organize conversations by projects
- **Health Monitoring**: System status and performance metrics
- **Data Export**: Comprehensive conversation export tools

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Node.js 18+ (for web interface)
- API Keys for OpenAI and xAI

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-username/Collaborate.git
   cd Collaborate
   ```

2. **Set up Python environment**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment**

   ```bash
   python setup.py
   ```

   This will create necessary directories and a `.env` file template.

4. **Add API keys**
   Edit `.env` file and add your API keys:

   ```
   OPENAI_API_KEY=your_openai_key_here
   XAI_API_KEY=your_xai_key_here
   ```

5. **Install frontend dependencies** (optional, for web interface)
   ```bash
   cd frontend
   npm install
   cd ..
   ```

### Running the Application

#### CLI Interface

```bash
# Interactive chat
python collaborate.py

# Show streaming demo
python collaborate.py --demo

# Check system health
python collaborate.py --health
```

#### Web Interface

```bash
# Start the web server
python web_server.py

# Or using uvicorn
uvicorn web_server:app --reload --host 0.0.0.0 --port 8000
```

Then open your browser to `http://localhost:8000`

For the full web experience with the React frontend:

```bash
# In one terminal - start backend
python web_server.py

# In another terminal - start frontend
cd frontend
npm start
```

Then visit `http://localhost:3000`

## 📚 Usage Guide

### Basic Conversation Flow

1. **Start a new project**

   ```bash
   python collaborate.py
   # Follow prompts to create or select a project
   ```

2. **Begin conversing**

   - Type your questions or topics
   - Both AI providers will respond with their perspectives
   - Responses stream in real-time word by word
   - Conversation context is preserved across sessions

3. **Use special commands**
   - `/help` - Show available commands
   - `/export` - Export conversation
   - `/health` - Check system status
   - `/switch` - Switch projects

### Web Interface Usage

1. **Navigation**

   - Left sidebar: Projects and conversations
   - Main area: Chat interface
   - Right panel: AI status and settings

2. **Creating conversations**

   - Click "New Chat" or use the "+" button
   - Select project or create new one
   - Start typing to begin conversation

3. **Real-time features**
   - See typing indicators when AIs are responding
   - Interruption detection (stop mid-response)
   - Live response streaming

### Research Management

The platform includes advanced research capabilities:

1. **Research Queries**

   ```bash
   # Research mode
   python collaborate.py --research
   ```

2. **Agent Coordination**

   - Retriever: Searches and gathers information
   - Reasoner: Analyzes and synthesizes results
   - Executor: Performs actions and computations
   - Memory: Stores and retrieves knowledge

3. **Task Management**
   - Asynchronous task processing
   - Priority-based queue management
   - Progress tracking and status updates

## 🏗️ Architecture

### Core Components

```
├── src/
│   ├── core/                    # Core business logic
│   │   ├── ai_client_manager.py # AI provider coordination
│   │   ├── streaming_coordinator.py # Real-time streaming
│   │   └── research_manager.py  # Research orchestration
│   ├── agents/                  # Research agents
│   │   ├── retriever_agent.py   # Information retrieval
│   │   ├── reasoner_agent.py    # Analysis and reasoning
│   │   ├── executor_agent.py    # Action execution
│   │   └── memory_agent.py      # Knowledge management
│   ├── ai_clients/              # AI provider clients
│   │   ├── openai_client.py     # OpenAI integration
│   │   └── xai_client.py        # xAI integration
│   ├── mcp/                     # MCP protocol implementation
│   ├── models/                  # Data models
│   ├── storage/                 # Database management
│   └── utils/                   # Utilities and helpers
├── frontend/                    # React web interface
├── tests/                       # Test suite
└── docs/                        # Documentation
```

### Technology Stack

**Backend:**

- Python 3.11+
- FastAPI for web APIs
- WebSocket for real-time communication
- SQLite for data storage
- Pydantic for data validation

**Frontend:**

- React 18 with TypeScript
- Redux Toolkit for state management
- Tailwind CSS for styling
- WebSocket client for real-time updates

**AI Integration:**

- OpenAI Python SDK
- xAI Python SDK
- Custom streaming implementations

## 🔧 Configuration

### Environment Variables

Create a `.env` file with:

```env
# API Keys
OPENAI_API_KEY=your_openai_key_here
XAI_API_KEY=your_xai_key_here

# Database
DATABASE_PATH=data/collaborate.db

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/collaborate.log

# Web Server
HOST=0.0.0.0
PORT=8000

# MCP Server
MCP_HOST=127.0.0.1
MCP_PORT=9000
```

### Configuration Files

The application uses `config/default_config.json` for default settings:

```json
{
  "ai_providers": {
    "openai": {
      "model": "gpt-4.1-mini",
      "temperature": 0.7,
      "max_tokens": 2000
    },
    "xai": {
      "model": "grok-3-mini-beta",
      "temperature": 0.7,
      "max_tokens": 2000
    }
  },
  "storage": {
    "database_path": "data/collaborate.db",
    "export_path": "exports/"
  },
  "research": {
    "max_concurrent_tasks": 10,
    "default_priority": "normal",
    "task_timeout": 300
  }
}
```

## 🧪 Testing

### Test Suite Execution

```bash
# Run all tests
python -m pytest

# Run specific test categories
python -m pytest tests/test_unit_ai_clients.py -v      # AI client tests
python -m pytest tests/test_unit_mcp.py -v            # MCP protocol tests
python -m pytest tests/test_unit_storage.py -v        # Storage/database tests
python -m pytest tests/test_unit_debug.py -v          # Debug function tests
python -m pytest tests/test_integration.py -v         # Integration tests
python -m pytest tests/test_performance_e2e.py -v     # Performance tests

# Run by markers
python -m pytest -m unit                              # Unit tests only
python -m pytest -m integration                       # Integration tests only
python -m pytest -m performance                       # Performance tests only

# Run with coverage
python -m pytest --cov=src tests/
```

### Test Suite Overview

- **Unit Tests**: Individual component testing (105 tests across 5 files)
  - AI Clients: 13 tests
  - MCP Protocol: 35 tests (24 + 11 simplified)
  - Storage/Database: 29 tests
  - Debug Functions: 28 tests
- **Integration Tests**: Cross-component functionality (11 tests)
- **Performance Tests**: Load and stress testing (9 tests)
- **E2E Tests**: End-to-end workflow testing (included in performance suite)

**Total**: 126+ comprehensive test cases covering all major components

## 📊 Performance

### System Requirements

**Minimum:**

- 2GB RAM
- 1GB free disk space
- Internet connection for AI API calls

**Recommended:**

- 8GB RAM
- 5GB free disk space
- High-speed internet connection

### Performance Metrics

- **Response Time**: <1 second for AI coordination
- **Streaming Latency**: <100ms for real-time updates
- **Concurrent Users**: Supports 100+ simultaneous connections
- **Database Operations**: 1000+ ops/second

## 🛠️ Development

### Setting Up Development Environment

1. **Clone and install**

   ```bash
   git clone https://github.com/your-username/Collaborate.git
   cd Collaborate
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Install development dependencies**

   ```bash
   pip install -e .
   npm install  # In frontend directory
   ```

3. **Run in development mode**

   ```bash
   # Backend with auto-reload
   uvicorn web_server:app --reload

   # Frontend with hot reload
   cd frontend && npm start
   ```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Code Style

- Follow PEP 8 for Python code
- Use type hints throughout
- Document all public methods
- Write comprehensive tests

## 🔐 Security

### API Key Management

- Store API keys in environment variables
- Never commit keys to version control
- Use different keys for development/production

### Data Security

- Local-only data storage by default
- Encrypted exports available
- No data sent to third parties (except AI providers)

## 🧪 Testing Framework

### Overview

Collaborate includes a comprehensive testing framework that ensures all components function correctly and meet performance requirements. The testing framework provides:

- **Unit Tests**: Individual component testing
- **Integration Tests**: Cross-component workflow testing
- **Performance Tests**: Load testing and benchmarking
- **End-to-End Tests**: Complete application workflow validation

### Running Tests

#### Quick Test Commands

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit                    # Unit tests only
pytest -m integration            # Integration tests only
pytest -m performance           # Performance tests only
pytest -m e2e                   # End-to-end tests only

# Run fast tests (excluding slow performance tests)
pytest -m "not slow"

# Run with coverage reporting
pytest --cov=src --cov-report=html
```

#### Test Categories

**Unit Tests** - Test individual components:

```bash
pytest tests/test_unit_ai_clients.py    # AI client testing
pytest tests/test_unit_mcp.py          # MCP protocol testing
pytest tests/test_unit_storage.py      # Database/storage testing
```

**Integration Tests** - Test component interactions:

```bash
pytest tests/test_integration.py       # Cross-component testing
```

**Performance Tests** - Load and stress testing:

```bash
pytest tests/test_performance_e2e.py   # Performance benchmarks
pytest -m "performance and not slow"   # Fast performance tests only
```

### Test Configuration

The testing framework uses `pytest.ini` for configuration:

- **Test Discovery**: Automatically finds `test_*.py` files
- **Markers**: Categorize tests by type (unit, integration, performance, etc.)
- **Coverage**: Integrated coverage reporting
- **Async Support**: Full async/await test support

### Test Environment Setup

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Set test environment variables (optional)
export TEST_DATABASE_PATH="/tmp/test.db"
export LOG_LEVEL="DEBUG"

# Run tests with verbose output
pytest -v
```

### Performance Benchmarks

The performance tests establish these benchmarks:

- **Database Operations**:

  - 100 conversations created in < 5 seconds
  - 500 messages created in < 10 seconds
  - Concurrent operations complete in < 15 seconds

- **Memory Usage**:

  - < 100MB increase for 1000 messages
  - Proper resource cleanup validation

- **AI Client Response**:
  - Mock response times < 0.1 seconds
  - Graceful error handling

### Test Data Management

Tests use isolated test data and temporary databases:

- **Fixtures**: Shared test configuration and data
- **Factories**: Dynamic test data generation
- **Cleanup**: Automatic resource cleanup after tests
- **Isolation**: Each test runs with fresh data

### Continuous Integration

For CI/CD integration, use these commands:

```bash
# Fast CI test suite
pytest -m "unit and fast" --cov=src

# Full CI test suite (excluding very slow tests)
pytest -m "not slow" --cov=src --junitxml=test-results.xml
```

### Troubleshooting Tests

**Common Test Issues**:

1. **Database Lock Errors**: Tests use isolated temporary databases
2. **MCP Connection Warnings**: Expected when MCP server not running
3. **API Key Requirements**: Some tests need valid API keys
4. **Async Test Issues**: Ensure proper `@pytest.mark.asyncio` usage

**Debug Commands**:

```bash
# Verbose test output
pytest -vvv --tb=long

# Debug specific test
pytest --pdb tests/test_file.py::test_function

# Show print statements
pytest -s
```

For comprehensive testing documentation, see [docs/TESTING_FRAMEWORK.md](docs/TESTING_FRAMEWORK.md).

## 🚨 Troubleshooting

### Common Issues

1. **API Key Errors**

   ```bash
   # Check if keys are set
   echo $OPENAI_API_KEY
   echo $XAI_API_KEY
   ```

2. **Database Issues**

   ```bash
   # Reset database
   rm data/collaborate.db
   python collaborate.py  # Will recreate
   ```

3. **MCP Connection Errors**

   ```bash
   # Check MCP server status
   python collaborate.py --health
   ```

   Note: Many tests will show MCP connection errors as warnings but still pass. This is expected when the MCP server is not running for testing.

4. **Test Failures**

   ```bash
   # Run only unit tests (most reliable)
   python -m pytest tests/test_phase6_unit.py -v

   # Some integration tests may fail if MCP server is not running
   # This is expected and doesn't affect core functionality
   ```

5. **Web Interface Issues**

   ```bash
   # Clear browser cache
   # Check browser console for errors
   # Verify API endpoints are accessible
   ```

### Logging

Logs are stored in `logs/`:

- `collaborate.log` - Main application log
- `ai_api.log` - AI provider interactions
- `mcp_server.log` - MCP protocol logs

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Acknowledgments

- OpenAI for GPT-4.1-mini API
- xAI for Grok-3-mini API
- FastAPI team for the excellent web framework
- React team for the frontend framework

## 📞 Support

For questions, issues, or contributions:

- Open an issue on GitHub
- Check the documentation in the `docs/` directory
- Review the test files for usage examples

---

**Happy Collaborating!** 🎉
