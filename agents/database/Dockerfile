# Database Agent - SECURITY HARDENED with Alpine
FROM python:3.12-alpine

# Security: Set build arguments for better control
ARG SERVICE_PORT=8011
ARG USER_ID=1000
ARG GROUP_ID=1000

# Security: Install security updates and minimal required packages
RUN apk update && apk upgrade && \
    apk add --no-cache \
    curl \
    ca-certificates \
    tini \
    bash \
    && rm -rf /var/cache/apk/* \
    && rm -rf /tmp/*

# Security: Create dedicated non-root user with minimal privileges
RUN addgroup -g ${GROUP_ID} -S databaseagent && \
    adduser -u ${USER_ID} -S databaseagent -G databaseagent -h /app -s /sbin/nologin

# Set secure working directory
WORKDIR /app

# Security: Copy requirements first for better layer caching
COPY requirements.txt .

# Security: Install Python packages with verification and cleanup
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --no-compile -r requirements.txt && \
    pip cache purge && \
    find /usr/local -name '*.pyc' -delete && \
    find /usr/local -name '*.pyo' -delete && \
    find /usr/local -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true

# Copy application code
COPY src/ ./src/

# Security: Create secure health check script
RUN echo -e '#!/bin/bash\ncurl -f http://localhost:8011/health || exit 1' > /app/health_check.sh && \
    chown databaseagent:databaseagent /app/health_check.sh && \
    chmod 750 /app/health_check.sh

# Security: Set strict file permissions and ownership
RUN chown -R databaseagent:databaseagent /app && \
    chmod -R 750 /app && \
    chmod 640 /app/src/*.py 2>/dev/null || true && \
    find /app -type d -exec chmod 750 {} \; && \
    find /app -type f -exec chmod 640 {} \; && \
    chmod 750 /app/health_check.sh

# Security: Create writable temp directory for application
RUN mkdir -p /app/tmp && \
    chown databaseagent:databaseagent /app/tmp && \
    chmod 750 /app/tmp

# Switch to non-root user
USER databaseagent

# Expose port for health checks
EXPOSE 8011

# Set secure environment variables
ENV PYTHONPATH=/app
ENV SERVICE_HOST=0.0.0.0
ENV SERVICE_PORT=8011
ENV MCP_SERVER_URL=ws://mcp-server:9000
ENV AGENT_TYPE=database
ENV LOG_LEVEL=INFO
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Security: Enhanced health check with timeout
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD /app/health_check.sh

# Security: Use tini as init system and exec form
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["python", "-u", "src/database_service.py"]
