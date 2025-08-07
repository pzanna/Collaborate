# Network Agent Container - SECURITY HARDENED with Alpine
FROM python:3.12-alpine AS base

# Security: Set build arguments for better control
ARG SERVICE_PORT=8004
ARG USER_ID=1000
ARG GROUP_ID=1000

# Security: Install security updates and minimal required packages
RUN apk update && apk upgrade && \
    apk add --no-cache \
    gcc \
    musl-dev \
    curl \
    ca-certificates \
    tini \
    bash \
    && rm -rf /var/cache/apk/* \
    && rm -rf /tmp/*

# Security: Create dedicated non-root user with minimal privileges
RUN addgroup -g ${GROUP_ID} -S network && \
    adduser -u ${USER_ID} -S network -G network -h /app -s /sbin/nologin

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
COPY config/ ./config/
COPY start.sh ./
COPY start-dev.sh ./

# Note: health_check.py is already in src/ directory

# Security: Set strict file permissions and ownership
RUN chown -R network:network /app && \
    chmod -R 750 /app && \
    chmod 750 /app/start-dev.sh && \
    chmod 640 /app/src/*.py /app/config/*.json 2>/dev/null || true && \
    find /app -type d -exec chmod 750 {} \; && \
    find /app -type f -exec chmod 640 {} \; && \
    chmod 750 /app/start-dev.sh

# Security: Create writable temp directory for application
RUN mkdir -p /app/tmp && \
    chown network:network /app/tmp && \
    chmod 750 /app/tmp

# Switch to non-root user
USER network

# Expose port
EXPOSE 8004

# Development stage
FROM base AS development

# Install development dependencies for file watching
USER root
RUN pip install --no-cache-dir watchfiles
USER network

# Development command with file watching
CMD ["./start-dev.sh"]

# Production stage (default)
FROM base AS production

# Security: Enhanced health check with timeout
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8004/health || exit 1

# Expose port
EXPOSE 8004

# Security: Use tini as init system and exec form
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["./start-dev.sh"]
