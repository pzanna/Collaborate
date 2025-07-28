# Pure MCP Client Dockerfile - Synthesis Agent
# Architecture-compliant: No HTTP server, WebSocket-only communication

FROM python:3.12-alpine

# Security: Create non-root user
RUN addgroup -g 1001 -S eunice && \
    adduser -u 1001 -S eunice -G eunice

# Install system dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    tini

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy base MCP agent
COPY ./base_mcp_agent.py ./base_mcp_agent.py

# Copy source code
COPY src/ ./src/
COPY config/ ./config/

# Set ownership and permissions
RUN chown -R eunice:eunice /app
USER eunice

# Environment variables
ENV PYTHONPATH=/app:/app/src
ENV PYTHONUNBUFFERED=1

# No health check via HTTP - MCP connection is monitored by MCP server
# Health is determined by successful WebSocket connection and registration

# Use tini for proper signal handling
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["python", "/app/src/synthesis_agent.py"]
