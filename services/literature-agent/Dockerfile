# Literature Agent Service - Enhanced MCP Client
# Phase 3.2 - Literature Agent Container Integration

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create logs directory
RUN mkdir -p /app/logs

# Set environment variables
ENV PYTHONPATH=/app
ENV AGENT_TYPE=literature_search
ENV AGENT_ID=literature-agent-001
ENV MCP_SERVER_URL=ws://mcp-server:9000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python health_check.py || exit 1

# Run the Literature Agent
CMD ["python", "literature_agent_service.py"]
