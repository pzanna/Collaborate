# Enhanced MCP Server - SECURITY HARDENED with Alpine
FROM python:3.12-alpine

# Security: Set build arguments for better control
ARG SERVICE_PORT=9000
ARG USER_ID=1000
ARG GROUP_ID=1000

# Security: Install security updates and all required packages for Python dependencies
RUN apk update && apk upgrade && \
    apk add --no-cache \
    gcc \
    musl-dev \
    g++ \
    curl \
    ca-certificates \
    tini \
    libffi-dev \
    openssl-dev \
    postgresql-dev \
    linux-headers \
    make \
    && rm -rf /var/cache/apk/* \
    && rm -rf /tmp/*

# Security: Create dedicated non-root user with minimal privileges
RUN addgroup -g ${GROUP_ID} -S mcpserver && \
    adduser -u ${USER_ID} -S mcpserver -G mcpserver -h /app -s /sbin/nologin

# Set secure working directory
WORKDIR /app

# Security: Copy requirements first for better layer caching
COPY requirements.txt .

# Security: Install Python packages with verification and cleanup
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --no-compile -r requirements.txt && \
    pip cache purge && \
    find /usr/local -name '*.pyc' -delete && \
    find /usr/local -name '*.pyo' -delete && \
    find /usr/local -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true

# Security: Remove build dependencies to minimize attack surface
RUN apk del gcc musl-dev g++ make linux-headers && \
    rm -rf /var/cache/apk/* /tmp/*

# Copy application code
COPY . .

# Security: Create necessary directories with proper permissions
RUN mkdir -p logs data tmp && \
    chown -R mcpserver:mcpserver /app && \
    chmod -R 750 /app && \
    chmod 640 /app/*.py 2>/dev/null || true && \
    find /app -type d -exec chmod 750 {} \; && \
    find /app -type f -exec chmod 640 {} \;

# Set secure environment variables
ENV PYTHONPATH=/app
ENV EUNICE_ENV=production
ENV EUNICE_LOG_PATH=/app/logs
ENV EUNICE_LOG_LEVEL=INFO
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONNOUSERSITE=1

# Switch to non-root user
USER mcpserver

# Expose MCP Server port
EXPOSE 9000

# Security: Enhanced health check with timeout
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import socket; s = socket.socket(); s.connect(('localhost', 9000)); s.close()" || exit 1

# Security: Use tini as init system and exec form
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["python", "-u", "mcp_server.py"]
