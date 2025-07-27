# AI Service

The AI Service is a pure MCP (Model Context Protocol) client that provides AI capabilities to the Eunice research system through WebSocket-based MCP communication.

## Architecture

The AI Service operates as a pure MCP client that:

- Connects to the MCP Server via WebSocket (no HTTP server)
- Registers as an agent with AI-related capabilities
- Processes AI tasks received through MCP protocol
- Integrates with multiple AI providers (OpenAI, Anthropic, XAI)
- Maintains zero HTTP attack surface (no REST endpoints)

## MCP Client Implementation

- **Protocol**: Pure MCP JSON-RPC over WebSocket
- **Agent Registration**: Registers with capabilities for chat completion, embeddings, model info, and usage stats
- **Task Processing**: Handles AI requests as MCP tasks, not HTTP requests
- **WebSocket Connection**: Persistent connection with heartbeat and reconnection logic
- **Zero HTTP**: No FastAPI server, no REST endpoints, no direct external access

## Features

### AI Providers

- **OpenAI**: GPT-4, GPT-3.5-turbo, text-embedding-ada-002
- **Anthropic**: Claude-3 family models
- **XAI**: Grok models

### Capabilities

- `ai_chat_completion`: Generate AI responses for research queries
- `ai_embedding`: Create embeddings for semantic search
- `ai_model_info`: Retrieve available model information
- `ai_usage_stats`: Track AI service usage statistics

## Configuration

The service is configured through environment variables:

```env
# MCP Connection
MCP_SERVER_URL=ws://mcp-server:9000
MCP_AUTH_TOKEN=mcp-dev-token-2024

# AI Provider Keys
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
XAI_API_KEY=your_xai_key

# Logging
LOG_LEVEL=INFO
```

## Security

- **Pure MCP Protocol**: No HTTP endpoints eliminate REST attack surface
- **Agent Authentication**: MCP agent registration with capabilities verification
- **Provider Security**: AI keys managed within secure service boundary
- **WebSocket Security**: Authenticated WebSocket connections only

## Deployment

The AI Service is deployed as a Docker container that connects to the MCP Server:

```bash
# Build
docker build -t eunice-ai-service .

# Run (with MCP Server dependency)
docker-compose up ai-service
```

## Development

### Testing

Run the security test to verify pure MCP client implementation:

```bash
python test_security.py
```

This test verifies that:

- No HTTP server is running
- No REST endpoints are accessible
- Service operates as pure MCP client

### MCP Communication Flow

1. **Connection**: AI Service connects to MCP Server via WebSocket
2. **Registration**: Registers as `ai_service` agent with AI capabilities
3. **Task Processing**: Receives AI tasks from other agents via MCP protocol
4. **Provider Routing**: Routes tasks to appropriate AI provider
5. **Response**: Returns results through MCP task completion

## Architecture Benefits

- **Pure Protocol**: Consistent MCP communication eliminates mixed architectures
- **Security**: Zero HTTP attack surface with WebSocket-only communication
- **Scalability**: Agent-based processing with task queuing
- **Maintainability**: Single protocol reduces complexity and debugging
- **Integration**: Seamless integration with other MCP agents
