# Standard Service Template

This template provides the standardized structure for all Eunice services and agents.

## Directory Structure

```
service-name/
├── README.md                    # Service-specific documentation  
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Multi-stage Docker build
├── .env.example                 # Environment variables template
├── start.sh                     # Production startup script
├── start-dev.sh                 # Development startup script
├── config/
│   ├── config.json             # Service configuration
│   └── logging.json            # Logging configuration
├── src/
│   ├── __init__.py             # Package initialization
│   ├── main.py                 # Main service entry point
│   ├── config.py               # Configuration management
│   ├── models.py               # Data models/schemas
│   ├── health_check.py         # Health check endpoints
│   └── service_name/           # Service-specific modules
│       ├── __init__.py
│       ├── service.py          # Core service logic
│       ├── handlers.py         # Request/task handlers
│       └── mcp_client.py       # MCP communication (if needed)
├── tests/                      # Unit and integration tests
│   ├── __init__.py
│   ├── test_main.py
│   └── test_service_name.py
└── docs/                       # Service documentation
    └── api.md
```

## Usage

1. Copy this template to create a new service
2. Replace `service_name` with your actual service name
3. Update configuration files with service-specific values
4. Implement service logic in the appropriate modules
