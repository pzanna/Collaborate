# Executor Agent Container
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for secure execution environment
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY start.sh ./

# Create non-root user for security
RUN useradd -m -u 1000 executor && chown -R executor:executor /app
RUN chmod +x ./start.sh
USER executor

# Create work directory with proper permissions
RUN mkdir -p /tmp/executor_work && chmod 755 /tmp/executor_work

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8008/health || exit 1

# Expose port
EXPOSE 8008

# Start the executor agent service
CMD ["./start.sh"]
