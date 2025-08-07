# Network Agent - Google Search Service

This is the Network Agent for the Eunice Research Platform, specialized in performing Google Custom Search Engine operations through the MCP (Model Context Protocol).

## Features

- **Google Custom Search Engine Integration**: Performs web searches using Google's Custom Search API
- **MCP Protocol Compliance**: Communicates exclusively through MCP JSON-RPC over WebSocket
- **Rate Limiting**: Built-in rate limiting to respect API quotas
- **Result Processing**: Parses and normalizes search results
- **Health Monitoring**: Standardized health check endpoint
- **Error Handling**: Robust error handling and retry logic

## Architecture Compliance

- ✅ **ONLY** exposes health check API endpoint (`/health`)
- ✅ **ALL** business operations via MCP protocol exclusively
- ✅ **NO** direct HTTP/REST endpoints for business logic
- ✅ Zero attack surface design

## Setup

### 1. Google Custom Search API Setup

1. **Get API Key**:
   - Go to [Google Custom Search API](https://developers.google.com/custom-search/v1/introduction)
   - Click "Get a Key"
   - Create a new project or select existing one
   - Copy your API key

2. **Create Search Engine**:
   - Go to [Google Custom Search Engine](https://cse.google.com/cse/)
   - Click "Add" to create a new search engine
   - Add websites to search (or enable "Search the entire web")
   - Copy your Search Engine ID from the control panel

3. **Configure Environment**:

   ```bash
   # Copy environment template
   cp .env.template .env
   
   # Edit .env file with your credentials
   GOOGLE_SEARCH_API_KEY=your_api_key_here
   GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id_here
   ```

### 2. Configuration

Edit `config/config.json` to customize:

- **Rate Limits**: Adjust daily/minute request limits
- **Search Parameters**: Default page size, timeout settings
- **MCP Connection**: Server URL and connection parameters

### 3. Testing

Run the test script to validate your setup:

```bash
python test_google_search.py
```

## Usage

### Docker Development

```bash
# Start in development mode with file watching
docker-compose up network-agent

# Or run directly
docker run -p 8004:8004 --env-file .env eunice/network-agent:dev
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start the service
python src/network_service.py
```

## API Endpoints

### Health Check (ONLY HTTP endpoint allowed)

```bash
# Check agent health
curl http://localhost:8004/health

# Alternative endpoints
curl http://localhost:8004/healthz
curl http://localhost:8004/status
```

Response:

```json
{
  "status": "healthy",
  "agent": "network-agent-001",
  "version": "1.0.0",
  "uptime": "2h15m30s",
  "ready": true,
  "mcp_connected": true,
  "last_heartbeat": "2025-08-06T10:30:00Z",
  "timestamp": "2025-08-06T10:30:00Z",
  "metadata": {
    "agent_type": "network",
    "protocol": "MCP-JSON-RPC",
    "api_compliance": "health_check_only",
    "search_engine": "google_custom_search",
    "search_capabilities": ["web_search", "google_custom_search", "result_parsing"],
    "api_configured": true
  }
}
```

## MCP Tasks

The agent handles the following MCP tasks:

### `google_search`

Perform a single-page Google search.

**Parameters:**

- `query` (string, required): Search query
- `page` (integer, optional): Page number (default: 1)
- `max_results` (integer, optional): Maximum results to return

**Example:**

```json
{
  "task_type": "google_search",
  "params": {
    "query": "machine learning tutorials",
    "page": 1,
    "max_results": 10
  }
}
```

### `web_search`

Alias for `google_search`.

### `multi_page_search`

Perform a multi-page Google search.

**Parameters:**

- `query` (string, required): Search query
- `max_results` (integer, optional): Total results across all pages (default: 50)

**Example:**

```json
{
  "task_type": "multi_page_search",
  "params": {
    "query": "python web scraping",
    "max_results": 100
  }
}
```

### `search_capabilities`

Get agent capabilities and current status.

**Example:**

```json
{
  "task_type": "search_capabilities",
  "params": {}
}
```

## Rate Limits

Default rate limits (configurable):

- **Daily**: 100 requests per day
- **Per minute**: 10 requests per minute

Google's free tier allows:

- **100 search queries per day**
- **10,000 queries per month** (with billing enabled)

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_SEARCH_API_KEY` | Google Custom Search API key | Required |
| `GOOGLE_SEARCH_ENGINE_ID` | Custom Search Engine ID | Required |
| `SERVICE_HOST` | Service bind host | `0.0.0.0` |
| `SERVICE_PORT` | Service port | `8004` |
| `MCP_SERVER_URL` | MCP server WebSocket URL | `ws://mcp-server:9000` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Troubleshooting

### Common Issues

1. **API not configured**
   - Check `.env` file has valid API key and search engine ID
   - Verify Google Cloud project has Custom Search API enabled

2. **Rate limit exceeded**
   - Check daily/minute quotas in configuration
   - Monitor API usage in Google Cloud Console

3. **MCP connection failed**
   - Verify MCP server is running and accessible
   - Check network connectivity and firewall settings

4. **Search results empty**
   - Verify search engine is configured to search the web
   - Check if query returns results in Google CSE control panel

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
python src/network_service.py
```

## Security

- **Zero attack surface**: Only health check endpoint exposed
- **Non-root container**: Runs as dedicated `network` user
- **Minimal privileges**: No unnecessary system access
- **Secrets management**: API keys via environment variables
- **Input validation**: All search parameters validated

## Dependencies

- **FastAPI**: Health check API
- **aiohttp**: Async HTTP client for Google API
- **websockets**: MCP protocol communication
- **requests**: Synchronous HTTP requests
- **tenacity**: Retry logic and error handling

## Contributing

1. Follow existing code patterns
2. Maintain MCP protocol compliance
3. Add tests for new functionality
4. Update documentation
5. Ensure security best practices
