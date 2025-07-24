# Eunice Research Platform

## Overview

Eunice is an advanced research platform named after the AI from William Gibson's novel [Agency](https://en.wikipedia.org/wiki/Agency_(novel)). It is designed to facilitate sophisticated research workflows through an integrated microservices architecture supporting collaborative research, project management, intelligent agent coordination, and **PhD-quality thesis generation**.

The platform specializes in hierarchical research organization, multi-agent collaboration, systematic literature reviews, and provides comprehensive tools for managing complex research projects across multiple domains.

## 🚀 Key Features

### Multi-Agent Coordination - **Project Management**: Comprehensive project organization with hierarchical research topics
- **Conversation Tracking**: Advanced conversation management with persistent storage
- **Research Task Organization**: Structured task management with dependency tracking
- **Hierarchical Data Models**: Complex research structures with nested relationships
- **Multi-Agent Coordination**: Intelligent agent personas for specialized research domains
- **Persona Consultation System**: Real-time expert consultation through specialized AI personas

### Research Capabilities - **Enhanced Academic Search**: Semantic Scholar API integration for high-quality academic papers
- **Multi-Source Research**: Web search across Google, Bing, Yahoo with academic source prioritization
- **Systematic Literature Reviews**: PRISMA-compliant systematic review generation
- **Thesis Generation**: Transform systematic reviews into PhD-quality literature review chapters
- **Cost Estimation System**: Budget tracking and resource management
- **Dependency Management**: Automatic task dependency resolution
- **Parallelism Coordination**: Efficient multi-threaded research execution
- **Memory Management**: Persistent storage for research artifacts and conversations
- **Export Functionality**: Research data export in multiple formats (PDF, Markdown, LaTeX, HTML, DOCX)

### Thesis Generation System 🎓 - **AI-Powered Analysis**: GPT-4 integration for intelligent theme extraction and gap analysis
- **Multiple Output Formats**: Markdown, LaTeX, HTML, PDF, DOCX
- **Deterministic Generation**: Reproducible outputs with SHA-256 caching (temp=0, top_p=1)
- **Academic Quality**: PhD-level literature reviews with proper citations and formatting
- **Research Questions**: Automatic generation of testable hypotheses and research questions
- **Conceptual Frameworks**: Visual diagrams and theoretical models with Mermaid integration
- **Human Checkpoints**: Interactive review points for quality control
- **Template System**: Jinja2 templates for consistent academic formatting

### Technical Features - **MCP (Model Context Protocol) Server**: Advanced microservices coordination with persona integration
- **Real-time WebSocket Communication**: Live updates, collaboration, and expert consultations
- **RESTful API**: Comprehensive backend API for all platform operations
- **Modern React Frontend**: Responsive web interface with TypeScript
- **SQLite Database**: Reliable data persistence with asynchronous operations
- **Persona System**: AI-powered expert consultation with domain-specific knowledge

## 🏗️ Architecture

Eunice follows a microservices architecture with the following key components:

- **Web Interface**: React/TypeScript frontend with Redux state management
- **API Gateway**: FastAPI-based backend with WebSocket support
- **MCP Server**: Microservices control plane for agent coordination and persona consultations
- **Research Manager**: Oversees research operations and agent coordination
- **Agent System**: Specialized AI agents for different research domains
- **Persona System**: Expert consultation agents with domain-specific knowledge
- **Storage Layer**: SQLite databases for conversations, memory, and collaboration data

For detailed architecture information, see [Architecture Overview](docs/Architecture.md).

## 🧬 Research Agent Personas

The platform includes specialized agent personas for interdisciplinary research consultation:

- **Neurobiologist**: Brain mapping, neuron extraction, viability assessments, and culture maintenance
- **Computational Neuroscientist**: Neural activity modeling and bio-digital interfacing protocols
- **AI/ML Engineer & Data Scientist**: ANN development and experimental data analysis
- **Biomedical Systems Engineer**: Hardware/software interface development and integration
- **Animal Biologist & Bioethics Specialist**: Animal welfare and regulatory compliance
- **Technical/Scientific Writer**: Documentation, manuscripts, and grant proposals

### 🎯 Persona Consultation System

The platform provides an advanced persona consultation system through the MCP server:

- **Expert Consultation**: Request specialized advice from domain experts
- **Multi-Persona Support**: Automatic routing to appropriate expertise areas
- **Real-time Responses**: WebSocket-based consultation with immediate feedback
- **Consultation History**: Persistent tracking of all expert interactions
- **Confidence Scoring**: AI-generated confidence metrics for consultation quality

**Example Usage:**

```python
# Request neurobiologist consultation
consultation_response = await mcp_client.request_persona_consultation(
    expertise_area="neuron_preparation",
    query="What are optimal conditions for hippocampal neuron culture?",
    context={"experiment_type": "LTP", "culture_duration": "21+ days"},
    preferred_persona="neurobiologist"
)
```

See [Persona Documentation](docs/Personas/README.md) for detailed role descriptions and consultation capabilities.

## 🛠️ Installation & Setup

### Prerequisites - **Python 3.11+** (recommended for optimal performance)
- **Node.js 18+** (for frontend development)
- **Git** (for version control)
- **Virtual Environment** (strongly recommended)

### 🚀 Quick Start (Optimized Setup)

#### 1. **Clone and Setup Virtual Environment**

```bash
git clone https://github.com/pzanna/Eunice.git
cd Eunice

# Create and activate virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

#### 2. **Install Dependencies (ARM64/Apple Silicon Compatible)**

```bash
# Upgrade pip first
pip install --upgrade pip

# Install Python dependencies
pip install -r requirements.txt

# For Apple Silicon users, if you encounter architecture errors:
python -m pip install --upgrade --force-reinstall black isort autoflake
```

#### 3. **Environment Configuration**

```bash
# Set up environment
python setup.py

# Configure API keys in .env file
# Add your OpenAI and xAI API keys:
# OPENAI_API_KEY=your_openai_key_here  
# XAI_API_KEY=your_xai_key_here
```

#### 4. **Frontend Setup**

```bash
cd frontend
npm install
npm run build
cd ..
```

#### 5. **Verify Installation (Optional)**

```bash
# Run code quality check to verify setup
python -m flake8 src/ --count --statistics --max-line-length=120

# Should show ~515 issues (93.7% improvement from original 8,212)
# This confirms the optimized codebase is working correctly
```

#### 6. **Start the Platform**

```bash
# Start all services (recommended)
./start_eunice.sh

# Or start services individually:
# Backend API: python web_server.py
# MCP Server: python mcp_server.py  
# Frontend Dev: cd frontend && npm start
```

### 🔧 Code Quality Tools (For Developers)

The platform includes professional code optimization tools:

```bash
# Apply automatic code fixes (8,212 fixes applied)
python fix_code_quality.py

# Advanced optimization for remaining issues  
python advanced_optimizer.py

# Professional formatting (use python -m for compatibility)
python -m black src/ --line-length 120
python -m isort src/ --profile black
python -m autoflake --remove-all-unused-imports --recursive src/
```

### ⚠️ Troubleshooting

**Common Issues:**

- **ARM64 Architecture Errors**: Use `python -m <command>` instead of global commands
- **Virtual Environment Issues**: Delete `.venv` and recreate: `python -m venv .venv`-**Import Errors**: Ensure you're in the activated virtual environment
- **API Errors**: Check your `.env` file has valid API keys

**For detailed troubleshooting**: See `docs/Troubleshooting.md` (coming soon)

### Thesis Generation Quick Start 🎓

Generate PhD-quality literature review chapters from PRISMA systematic reviews:

```bash
# Setup thesis generation dependencies
python thesis_cli.py --setup

# Generate thesis chapter from systematic review
python thesis_cli.py tests/literature/comprehensive_literature_review.json

# Advanced usage with custom configuration
python thesis_cli.py data/review.json -c src/thesis/config/thesis_config.yaml --formats latex pdf

# Automated processing (skip human checkpoints)
python thesis_cli.py data/review.json --no-checkpoints -o my_thesis_output
```

**What it generates:**

- 5 academic themes with evidence synthesis
- Research gaps with priority scoring (impact, feasibility, novelty)
- Conceptual framework with theoretical relationships
- Testable research questions and hypotheses
- Publication-ready LaTeX documents
- Interactive HTML and clean Markdown formats

### Alternative Setup Scripts - `./setup.sh` - Basic Python environment setup
- `./setup_web.sh` - Web-specific setup with frontend build

## 📁 Project Structure

```text
Eunice/
├── src/                    # Python source code
│   ├── agents/            # AI agent implementations
│   ├── ai_clients/        # AI service integrations
│   ├── core/              # Core platform logic
│   ├── mcp/               # Model Context Protocol server with persona integration
│   ├── models/            # Data models
│   ├── personas/          # Expert consultation persona agents
│   ├── storage/           # Database and storage
│   └── utils/             # Utility functions
├── frontend/               # React TypeScript frontend
│   ├── src/components/     # UI components
│   ├── src/services/       # API services
│   └── src/store/          # Redux store
├── docs/                   # Documentation
├── tests/                  # Test suites
├── config/                 # Configuration files
├── logs/                   # Application logs
└── exports/                # Research exports
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

# Test persona consultation system
python tests/test_mcp_persona_client.py
```

## 📊 Monitoring & Logs

The platform generates detailed logs for monitoring:

- `logs/agents.log` - Agent coordination and activities
- `logs/ai_api.log` - AI service interactions
- `logs/eunice.log` - Collaboration events
- `logs/mcp_server.log` - MCP server operations and persona consultations
- `logs/mcp_tasks.log` - Task processing and persona integration

## 🔧 Configuration

### Environment Variables

Create a `.env` file with your API keys:

```bash
# Required AI API Keys
OPENAI_API_KEY=your_openai_api_key_here
XAI_API_KEY=your_xai_api_key_here

# Optional: Semantic Scholar API Key (recommended for better academic search)
SEMANTIC_SCHOLAR_API_KEY=your_semantic_scholar_api_key_here
```

**Semantic Scholar API Key Benefits:**

- Higher rate limits for academic searches
- Better performance and reliability
- Priority access during high traffic
- Get your free API key at: [https://www.semanticscholar.org/product/api#api-key](https://www.semanticscholar.org/product/api#api-key)

### Configuration Files - `.env` - API keys and environment variables
- `config/default_config.json` - Default platform settings
- `pytest.ini` - Test configuration

## 📚 Documentation - [Architecture Overview](docs/Architecture.md)
- [Research Manager](docs/Research_Manager.md)
- [MCP Persona System](docs/MCP_Persona_System.md)
- [Persona Quick Start](docs/Persona_Quick_Start.md)
- [Persona Roles](docs/Personas/README.md)
- [Cost Estimation System](docs/Cost_Estimation_System.md)-[Hierarchical Research Structure](docs/Hierarchical_Research_Structure.md)

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

Named after Eunice, the AI character from William Gibson's "Agency"—a novel that explores themes of artificial intelligence, research collaboration, and the intersection of technology with human endeavor.
