# Literature Agent Service - Phase 3.2

This service provides a containerized Literature Agent that connects to the Enhanced MCP Server as an MCP client for coordinated literature search tasks.

## Features

- **MCP Client Integration**: Connects to Enhanced MCP Server via WebSocket
- **Literature Search**: Academic paper search and web search capabilities  
- **Result Processing**: Content extraction and relevance ranking
- **Health Monitoring**: Built-in health checks and status reporting
- **Containerized Deployment**: Docker-based deployment with compose orchestration

## Quick Start

### Build and Run

```bash
# Build and start the service
docker-compose up --build -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f literature-agent

# Health check
docker-compose exec literature-agent python health_check.py
```

### Test Literature Search

```bash
# Connect to the Enhanced MCP Server and submit a literature search task
# (This would be done through the Research Manager or web interface)
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_ID` | `literature-agent-001` | Unique agent identifier |
| `AGENT_TYPE` | `literature` | Agent type for MCP registration |
| `MCP_SERVER_URL` | `ws://mcp-server:9000` | Enhanced MCP Server WebSocket URL |
| `LOG_LEVEL` | `INFO` | Logging level |

### Capabilities

The Literature Agent provides these capabilities:

- `academic_search`: Academic paper and journal search
- `web_search`: General web content search  
- `content_extraction`: Extract and clean web content
- `result_ranking`: Rank search results by relevance

## MCP Protocol

### Agent Registration

```json
{
  "type": "agent_register",
  "agent_id": "literature-agent-001",
  "agent_type": "literature",
  "capabilities": ["academic_search", "web_search", "content_extraction", "result_ranking"],
  "max_concurrent": 3,
  "timeout": 300
}
```

### Task Processing

```json
{
  "type": "task_submit",
  "task_id": "lit_search_001",
  "task_type": "literature_search",
  "agent_type": "literature",
  "payload": {
    "query": "machine learning transformers",
    "max_results": 10
  }
}
```

### Task Results

```json
{
  "type": "task_result",
  "task_id": "lit_search_001",
  "agent_id": "literature-agent-001",
  "status": "completed",
  "result": {
    "query": "machine learning transformers",
    "results_count": 10,
    "results": [...],
    "processing_time": "2.1s"
  }
}
```

## Architecture

```
Literature Agent Service
├── literature_agent_service.py    # Main service implementation
├── health_check.py                # Health check script
├── requirements.txt               # Python dependencies
├── Dockerfile                     # Container configuration
└── docker-compose.yml            # Multi-service orchestration
```

## Integration with Enhanced MCP Server

This Literature Agent integrates with the Enhanced MCP Server (Phase 3.1) by:

1. **Registration**: Automatically registers capabilities on startup
2. **Task Processing**: Receives and processes literature search tasks
3. **Heartbeat**: Sends periodic status updates
4. **Results**: Returns structured search results via MCP protocol

## Next Steps

- **Production Search APIs**: Integrate real academic search APIs (Semantic Scholar, PubMed, etc.)
- **Content Extraction**: Implement full HTML content extraction and parsing
- **Relevance Ranking**: Add machine learning-based relevance scoring
- **Caching**: Implement Redis-based result caching
- **Monitoring**: Add detailed metrics and performance monitoring

## Status

**Phase 3.2 Implementation**: ✅ Complete  
**MCP Integration**: ✅ Working  
**Container Deployment**: ✅ Ready  
**Next**: Production API integration and enhanced search capabilities
