# Memory Agent Service Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN groupadd -r memoryagent && useradd -r -g memoryagent memoryagent

# Install system dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Create data directory with proper permissions
RUN mkdir -p /tmp/memory_agent_data && \
    chown -R memoryagent:memoryagent /tmp/memory_agent_data && \
    chown -R memoryagent:memoryagent /app

# Switch to non-root user
USER memoryagent

# Expose service port
EXPOSE 8009

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8009/health || exit 1

# Start the service
CMD ["python", "-m", "uvicorn", "src.memory_service:app", "--host", "0.0.0.0", "--port", "8009"]
