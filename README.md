# Collaborate - AI Collaboration Platform

An advanced Python platform for intelligent AI collaboration featuring multi-provider coordination, streaming responses, and sophisticated conversation management with both CLI and modern web interfaces.

## 🌟 Key Features

- **🤖 Multi-AI Coordination**: Smart provider selection with OpenAI and xAI
- **🔄 Multi-Round Collaboration**: Extended AI conversations with iteration logic
- **🌊 Streaming Responses**: Real-time response generation with live updates
- **💬 Mention System**: Direct AI targeting with `@openai` and `@xai` syntax
- **🧠 Context Awareness**: AIs build upon each other's responses
- **🤝 Cross-Talk Hints**: Models are prompted to address each other directly and summarize recent points
- **🛡️ Robust Error Handling**: Automatic retries and intelligent fallbacks
- **📊 Performance Monitoring**: Provider health tracking and optimization
- **💾 Persistent Storage**: Conversation history with export capabilities
- **🌐 Modern Web UI**: Slack/Teams-style chat interface with real-time streaming
- **📱 Project Management**: Organize conversations into projects with full CRUD operations
- **🔍 System Health Monitoring**: Real-time AI provider status and performance metrics
- **🎨 Responsive Design**: Works seamlessly on desktop and mobile devices
- **⚡ WebSocket Integration**: Real-time messaging with typing indicators and live updates

## 🖥️ Interfaces

### 🌐 Web UI (Recommended)

Modern chat interface with real-time AI streaming, project management, and system health monitoring.

### 🖥️ Command Line Interface (CLI)

Full-featured terminal interface for power users and automation.

## 📚 Documentation

**👉 [Complete Documentation](docs/COMPREHENSIVE_DOCUMENTATION.md)**

- [Turn-Taking Guidelines](docs/TURN_TAKING_GUIDE.md)

The comprehensive guide covers:

- Architecture overview and core components
- Usage examples and best practices
- Configuration and setup instructions
- Advanced features (streaming, multi-round)
- API reference and development guides

## 🚀 Quick Start

### 🌐 Web UI Setup (Recommended)

1. **Clone and setup**:

   ```bash
   git clone <repository-url>
   cd Collaborate
   ./setup_web.sh
   ```

2. **Configure API keys**:

   ```bash
   export OPENAI_API_KEY="your_openai_key"
   export XAI_API_KEY="your_xai_key"
   ```

3. **Start the web interface**:

   ```bash
   ./start_web.sh
   ```

4. **Open your browser**:
   - Frontend: <http://localhost:3000>
   - Backend API: <http://localhost:8000>

### 🖥️ CLI Setup

1. **Clone repository**:

   ```bash
   git clone <repository-url>
   cd Collaborate
   ```

2. **Set up Python environment**:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Run setup**:

   ```bash
   python setup.py
   ```

5. **Configure API keys**:

   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

6. **Run the web interface**:

   ```bash
   streamlit run app.py
   ```

## 🌐 Web UI Features

### Modern Chat Interface

- **Slack/Teams-inspired design** with intuitive navigation
- **Real-time messaging** with WebSocket streaming
- **Project management** with create, read, update, delete operations
- **Conversation organization** within projects
- **Responsive layout** that works on all devices
- **System health monitoring** with AI provider status

### User Experience

- **Instant messaging feel** with typing indicators
- **Real-time AI responses** streaming word by word
- **Visual feedback** for connection status and AI activity
- **Mobile-friendly** responsive design
- **Dark/light theme** support (coming soon)

### Technical Features

- **TypeScript** throughout for type safety
- **Redux** state management for predictable updates
- **Tailwind CSS** for modern styling
- **WebSocket** integration for real-time updates
- **Hot reload** development environment

## 🔧 Recent Updates & Improvements

### Version 2.0 - Web UI Launch

**🌐 Modern Web Interface**

- Complete React TypeScript web application
- Real-time WebSocket messaging with streaming responses
- Slack/Teams-inspired chat interface
- Mobile-responsive design with Tailwind CSS

**📱 Enhanced Project Management**

- Full CRUD operations for projects (Create, Read, Update, Delete)
- Organize conversations within projects
- Visual project overview with conversation counts
- Intuitive project creation and management workflows

**🏥 System Health Monitoring**

- Real-time AI provider status monitoring
- Performance metrics and response times
- Connection status indicators
- Health dashboard with system overview

**🛠️ Developer Experience**

- Hot reload development environment
- TypeScript throughout for type safety
- Redux state management for predictable updates
- Comprehensive error handling and graceful fallbacks

**🧹 Code Cleanup**

- Removed unused backup files and duplicate code
- Streamlined core architecture
- Updated dependencies and security patches
- Improved performance and reliability

### Previous Updates

**xAI Integration Enhancement**

- ✅ Updated xAI client to use correct API pattern
- ✅ Fixed chat.create() and chat.sample() implementation
- ✅ Upgraded to working model `grok-2`
- ✅ Improved three-way collaboration stability

**Turn-Taking System**

- Enhanced multi-agent conversation coordination
- Natural turn-taking based on Sacks et al. research
- Context-aware response selection
- Improved cross-talk and collaboration hints

## 🎮 Usage Examples

### Getting Started

Once you've set up the environment and configured your API keys:

1. **Access the web interface**:

   Open your browser and go to <http://localhost:3000> for the modern web UI, or <http://localhost:8000> for the API documentation.

### Web UI (Recommended)

The modern web interface provides the best user experience:

1. **Create or select a project** for your research topic
2. **Start a new conversation** or continue an existing one
3. **Chat with AI systems** using natural language
4. **Monitor system health** and AI provider status
5. **Export conversations** in multiple formats

### CLI Interface

For power users and automation:

1. **Start the CLI application**:

   ```bash
   python collaborate.py
   ```

2. **Use interactive commands**:
   - `1` - List Projects
   - `2` - Create Project
   - `3` - List Conversations
   - `4` - Start Conversation
   - `5` - Resume Conversation
   - `6` - Test AI Connections
   - `7` - Show Configuration
   - `0` - Exit

### Typical Workflow

1. **Create a project** for your research topic
2. **Start a conversation** within the project
3. **Ask questions** and engage with both AI systems
4. **Export conversations** for reference

## 🎮 Usage

### Quick Start

1. **Test the installation**:

   ```bash
   python test_full_functionality.py
   ```

2. **Start the application**:

   ```bash
   python collaborate.py
   ```

3. **Or use the shortcut**:

   ```bash
   python run_collaborate.py
   ```

4. **Access the web interface**:

   Open `http://localhost:8501` in your web browser.

### Basic Workflow

1. **Create a project** for your research topic
2. **Start a conversation** within the project
3. **Ask questions** and engage with both AI systems
4. **Export conversations** for reference

### CLI Commands

The interactive CLI provides these options:

- `1` - List Projects
- `2` - Create Project
- `3` - List Conversations
- `4` - Start Conversation
- `5` - Resume Conversation
- `6` - Test AI Connections
- `7` - Show Configuration
- `0` - Exit

### Conversation Commands

Within a conversation:

- Type your message and press Enter
- Type `history` to see conversation history
- Type `exit` to end the conversation

## 📁 Project Structure

```text
├── src/
│   ├── config/          # Configuration management
│   ├── models/          # Data models
│   ├── storage/         # Database operations
│   ├── ai_clients/      # AI provider clients
│   ├── core/            # Core business logic
│   ├── cli/             # Command-line interface
│   └── utils/           # Utilities and helpers
├── frontend/            # React TypeScript web UI
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── services/    # API services
│   │   ├── store/       # Redux state management
│   │   └── styles/      # Tailwind CSS styles
│   ├── public/          # Static assets
│   └── package.json     # Frontend dependencies
├── config/              # Configuration files
├── data/                # Local database storage
├── docs/                # Documentation files
├── logs/                # Application logs
├── exports/             # Exported conversations
├── web_server.py        # FastAPI web server
├── collaborate.py       # Main CLI application
├── setup.py            # Environment setup script
├── requirements.txt    # Python dependencies
├── setup_web.sh        # Web UI setup script
└── start_web.sh        # Web UI start script
```

## 🧪 Testing

Run the test suite:

```bash
# Test basic functionality
python tests/test_foundation.py

# Test full functionality (including AI if keys are configured)
python tests/test_full_functionality.py

# Test with pytest
pytest tests/
```

## 🔄 API Usage

### Without API Keys

The application works without API keys for:

- Project management
- Conversation organization
- Message storage
- Configuration management

### With API Keys

With valid API keys, you get:

- Real AI responses from OpenAI and xAI
- Three-way collaborative conversations
- Context-aware AI interactions
- Role-adapted responses

## 📊 Data Management

### Local Storage

- **Database**: SQLite database in `data/collaborate.db`
- **Conversations**: Persistent storage with full history
- **Projects**: Organized by research topics
- **Messages**: Timestamped with metadata

### Export Options

Export conversations in multiple formats:

- **JSON**: Structured data
- **Markdown**: Readable format
- **PDF**: Formatted documents
- **HTML**: Web-friendly format

## 🛡️ Privacy & Security

- **Local storage**: All data stored locally
- **No cloud dependencies**: Works offline (except AI calls)
- **API key security**: Stored in environment variables
- **Data control**: Full control over your conversations

## 🔧 Advanced Configuration

### Custom AI Providers

Extend the system by adding custom AI providers:

1. Create a new client in `src/ai_clients/`
2. Register it in `AIClientManager`
3. Add configuration to `default_config.yaml`

### Database Customization

- **File database**: Default storage in `data/collaborate.db`
- **In-memory database**: For testing with `:memory:`
- **Custom path**: Configure in `config/default_config.yaml`

## 🐛 Troubleshooting

### Common Issues

1. **Web UI not loading**:

   ```bash
   # Check if both servers are running
   # Backend should be on port 8000
   # Frontend should be on port 3000
   ./start_web.sh
   ```

2. **Import errors**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Database errors**:

   ```bash
   rm data/collaborate.db
   python setup.py
   ```

4. **API connection issues**:

   - Check your API keys in `.env`
   - Verify network connectivity
   - Check API rate limits

5. **WebSocket connection failed**:
   - Ensure the backend server is running on port 8000
   - Check browser console for connection errors
   - Verify firewall settings

### Debug Mode

Run with debug information:

```bash
export LOG_LEVEL=DEBUG
python collaborate.py
```

For web server debugging:

```bash
python web_server.py --reload --log-level debug
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- OpenAI for providing the GPT models
- xAI for providing the Grok models
- Python community for excellent libraries

## 🔗 Links

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [xAI Documentation](https://docs.x.ai/)
- [Python Documentation](https://docs.python.org/)

---

**Happy Collaborating!** 🎉

Experience the next generation of AI collaboration through our modern web interface or powerful CLI. Create projects, engage in multi-AI conversations, and export your research - all with enterprise-grade reliability and user-friendly design.

For questions, support, or feature requests, please create an issue in the repository.
