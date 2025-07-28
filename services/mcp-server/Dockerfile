# Enhanced MCP Server - Version 0.3.1 Container
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs data

# Set environment variables
ENV PYTHONPATH=/app
ENV EUNICE_ENV=production
ENV EUNICE_LOG_PATH=/app/logs
ENV EUNICE_LOG_LEVEL=INFO

# Expose MCP Server port
EXPOSE 9000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import socket; s = socket.socket(); s.connect(('localhost', 9000)); s.close()" || exit 1

# Run as non-root user
RUN useradd -r -s /bin/false mcp-server
RUN chown -R mcp-server:mcp-server /app
USER mcp-server

# Start the simple MCP server for testing
CMD ["python", "mcp_server.py"]
