# Database Service

Direct PostgreSQL interface providing core database operations for the Eunice Research Platform.

## Features

- **PostgreSQL Integration**: Native asyncpg connection with connection pooling
- **Health Monitoring**: Built-in health checks and status reporting
- **Transaction Support**: ACID-compliant database operations
- **Connection Management**: Automatic connection pooling and lifecycle management
- **Error Handling**: Comprehensive error handling with detailed logging

## Architecture

The Database Service provides a direct interface to PostgreSQL, complementing the API Gateway's native database client for high-performance operations.

### Current Implementation Status

✅ **Core Infrastructure**

- PostgreSQL connection management
- Health check endpoints
- Transaction support
- Logging and monitoring

⚠️ **Entity Operations**

- Projects: Basic operations available via API Gateway
- Research Topics: Schema ready, endpoints pending
- Research Plans: Schema ready, endpoints pending  
- Tasks: Schema ready, endpoints pending

## Database Schema

The service manages the following core entities:

```sql
-- Projects (implemented)
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Research Topics (schema ready)
CREATE TABLE research_topics (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    priority INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Research Plans (schema ready)
CREATE TABLE research_plans (
    id SERIAL PRIMARY KEY,
    topic_id INTEGER REFERENCES research_topics(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tasks (schema ready)
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER REFERENCES research_plans(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Configuration

### Environment Variables

```bash
# Database Connection
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=eunice
POSTGRES_USER=eunice_user
POSTGRES_PASSWORD=your_password

# Service Configuration
PORT=8001
HOST=0.0.0.0
LOG_LEVEL=INFO

# Connection Pool Settings
DB_POOL_MIN_SIZE=1
DB_POOL_MAX_SIZE=10
```

## Development

### Local Setup

1. **Clone and navigate to service directory**:

   ```bash
   cd services/database
   ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up database**:

   ```bash
   # Initialize database schema
   python init_db.py
   ```

4. **Configure environment**:

   ```bash
   export POSTGRES_HOST=localhost
   export POSTGRES_PORT=5432
   export POSTGRES_DB=eunice
   export POSTGRES_USER=eunice_user
   export POSTGRES_PASSWORD=your_password
   ```

5. **Start the service**:

   ```bash
   python database_service.py
   ```

### Docker Deployment

**Build the image**:

```bash
docker build -t eunice/database-service:latest .
```

**Run the container**:

```bash
docker run -d \
  --name database-service \
  -p 8001:8001 \
  -e POSTGRES_HOST=postgres \
  -e POSTGRES_DB=eunice \
  -e POSTGRES_USER=eunice_user \
  -e POSTGRES_PASSWORD=your_password \
  eunice/database-service:latest
```

## API Reference

### Health Check

**GET** `/health`

Returns service health and database connection status.

**Response**:

```json
{
  "status": "healthy",
  "timestamp": "2025-01-11T12:00:00Z",
  "database": "connected",
  "version": "1.0.0"
}
```

### Service Info

**GET** `/info`

Returns service information and configuration details.

**Response**:

```json
{
  "service": "database-service",
  "version": "1.0.0",
  "database": {
    "host": "localhost",
    "port": 5432,
    "database": "eunice"
  },
  "pool": {
    "min_size": 1,
    "max_size": 10,
    "current_size": 5
  }
}
```

## Integration

The Database Service integrates with:

- **API Gateway**: Via native database client for high-performance operations
- **MCP Server**: For task queue management and agent coordination
- **Database Agent**: For MCP-based database operations

## Monitoring

### Health Checks

The service provides comprehensive health monitoring:

- Database connection status
- Connection pool metrics
- Query performance statistics
- Error rates and logging

### Logging

Structured logging includes:

- Connection lifecycle events
- Query execution metrics
- Error details and stack traces
- Performance monitoring data

## Troubleshooting

### Common Issues

**Connection refused**:

- Verify PostgreSQL is running
- Check connection parameters
- Ensure network connectivity

**Pool exhaustion**:

- Monitor connection pool usage
- Adjust pool size settings
- Check for connection leaks

**Slow queries**:

- Enable query logging
- Analyze query performance
- Add appropriate indexes

### Debug Mode

Enable detailed logging:

```bash
export LOG_LEVEL=DEBUG
python database_service.py
```

## Contributing

1. Follow the established database patterns
2. Add appropriate indexes for new queries
3. Include comprehensive error handling
4. Update this documentation for new features
5. Add tests for new functionality

## License

Part of the Eunice Research Platform - see main project LICENSE file.
