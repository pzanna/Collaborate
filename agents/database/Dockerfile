# Database Agent - MCP Client for Database Operations
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent source code
COPY src/ ./src/

# Create health check script
RUN echo '#!/bin/bash\ncurl -f http://localhost:8008/health || exit 1' > /app/health_check.sh && \
    chmod +x /app/health_check.sh

# Expose port for health checks
EXPOSE 8008

# Set environment variables
ENV PYTHONPATH=/app
ENV SERVICE_HOST=0.0.0.0
ENV SERVICE_PORT=8008
ENV MCP_SERVER_URL=ws://mcp-server:9000
ENV AGENT_TYPE=database
ENV LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /app/health_check.sh

# Run the database agent service
CMD ["python", "src/database_service.py"]
