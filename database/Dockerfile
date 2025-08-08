# database-service Service - SECURITY HARDENED with Alpine
FROM python:3.12-alpine AS base

# Security: Set build arguments for better control
ARG SERVICE_PORT=8000
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
    libffi-dev \
    && rm -rf /var/cache/apk/* \
    && rm -rf /tmp/*

# Security: Create dedicated non-root user with minimal privileges
RUN addgroup -g ${GROUP_ID} -S dbuser && \
    adduser -u ${USER_ID} -S dbuser -G dbuser -h /app -s /sbin/nologin

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
COPY start.sh ./start.sh
COPY start-dev.sh ./start-dev.sh

# Security: Set strict file permissions and ownership
RUN chown -R dbuser:dbuser /app && \
    chmod -R 750 /app && \
    chmod +x /app/start.sh /app/start-dev.sh && \
    find /app -type d -exec chmod 750 {} \; && \
    find /app -name "*.py" -exec chmod 640 {} \; && \
    find /app -name "*.json" -exec chmod 640 {} \;

# Security: Create secure data directory with proper permissions
RUN mkdir -p /app/data /app/logs && \
    chown -R dbuser:dbuser /app/data /app/logs && \
    chmod 750 /app/data /app/logs

# Set secure environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONNOUSERSITE=1
ENV PYTHONPATH=/app/src

# Development target
FROM base AS development

# Install development dependencies
RUN pip install --no-cache-dir watchfiles pytest pytest-asyncio pytest-cov

# Switch to non-root user
USER dbuser

# Expose service port
EXPOSE ${SERVICE_PORT}

# Development entry point
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["./start-dev.sh"]

# Production target
FROM base AS production

# Security: Remove build dependencies to minimize attack surface
RUN apk del gcc musl-dev libffi-dev && \
    rm -rf /var/cache/apk/* /tmp/*

# Switch to non-root user
USER dbuser

# Expose service port
EXPOSE ${SERVICE_PORT}

# Security: Use tini as init system and exec form
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["./start.sh"]
