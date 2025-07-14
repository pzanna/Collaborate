# Collaborate - AI Collaboration Platform

An advanced Python platform for intelligent AI collaboration featuring multi-provider coordination, streaming responses, and sophisticated conversation management.

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

## 📚 Documentation

**👉 [Complete Documentation](docs/COMPREHENSIVE_DOCUMENTATION.md)**
* [Turn-Taking Guidelines](docs/TURN_TAKING_GUIDE.md)

The comprehensive guide covers:

- Architecture overview and core components
- Usage examples and best practices
- Configuration and setup instructions
- Advanced features (streaming, multi-round)
- API reference and development guides

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone <repository-url>
cd Collaborate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
export OPENAI_API_KEY="your_openai_key"
export XAI_API_KEY="your_xai_key"
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

## 🔧 Configuration

### API Keys

Add your API keys to the `.env` file:

```env
OPENAI_API_KEY=your_openai_api_key_here
XAI_API_KEY=your_xai_api_key_here
```

### AI Models

Configure AI models in `config/default_config.yaml`:

```yaml
ai_providers:
  openai:
    model: "gpt-4.1-mini"
    temperature: 0.7
    max_tokens: 2000
    system_prompt: "You are a helpful research assistant participating in a collaborative discussion."
    role_adaptation: true

  xai:
    model: "grok-3-mini"
    temperature: 0.7
    max_tokens: 2000
    system_prompt: "You are a knowledgeable AI assistant contributing to collaborative research."
    role_adaptation: true
```

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

```
├── src/
│   ├── config/          # Configuration management
│   ├── models/          # Data models
│   ├── storage/         # Database operations
│   ├── ai_clients/      # AI provider clients
│   ├── core/            # Core business logic
│   └── cli/             # Command-line interface
├── config/              # Configuration files
├── data/                # Local database storage
├── docs/                # Documentation files
├── logs/                # Application logs
├── tests/               # Test files
├── exports/             # Exported conversations
├── collaborate.py       # Main application entry point
├── setup.py            # Environment setup script
└── requirements.txt    # Python dependencies
```

├── exports/ # Exported conversations
├── tests/ # Test files
└── requirements.txt # Python dependencies

````

## 🧪 Testing

Run the test suite:

```bash
# Test basic functionality
python tests/test_foundation.py

# Test full functionality (including AI if keys are configured)
python tests/test_full_functionality.py

# Test with pytest
pytest tests/
````

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

1. **Import errors**:

   ```bash
   pip install -r requirements.txt
   ```

2. **Database errors**:

   ```bash
   rm data/collaborate.db
   python setup.py
   ```

3. **API connection issues**:
   - Check your API keys in `.env`
   - Verify network connectivity
   - Check API rate limits

### Debug Mode

Run with debug information:

```bash
export LOG_LEVEL=DEBUG
python collaborate.py
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

For questions or support, please create an issue in the repository.

## 🔧 Recent Updates

### xAI Integration Fix

The xAI client has been updated to use the correct API pattern:

- ✅ Uses `client.chat.create(model=...)` to create chat instances
- ✅ Uses `chat.append(system(...))`, `chat.append(user(...))` for messages
- ✅ Uses `chat.sample()` to get responses
- ✅ Updated to use the working model `grok-2`

The application now fully supports three-way collaboration with both OpenAI and xAI.
