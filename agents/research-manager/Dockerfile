# Research Manager Agent - SECURITY HARDENED with Alpine
# Base stage
FROM python:3.12-alpine AS base

# Security: Set build arguments for better control
ARG SERVICE_PORT=8002
ARG USER_ID=1000
ARG GROUP_ID=1000

# Security: Install security updates and minimal required packages
RUN apk update && apk upgrade && \
    apk add --no-cache \
    curl \
    ca-certificates \
    tini \
    && rm -rf /var/cache/apk/* \
    && rm -rf /tmp/*

# Security: Create dedicated non-root user with minimal privileges
RUN addgroup -g ${GROUP_ID} -S researchmanager && \
    adduser -u ${USER_ID} -S researchmanager -G researchmanager -h /app -s /sbin/nologin

# Set secure working directory
WORKDIR /app

# Set secure environment variables
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONNOUSERSITE=1

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

# Copy shared health check service
COPY health_check_service.py ./health_check_service.py

# Copy startup scripts
COPY start.sh ./start.sh
COPY start-dev.sh ./start-dev.sh

# Security: Set strict file permissions and ownership
RUN chown -R researchmanager:researchmanager /app && \
    chmod -R 750 /app && \
    chmod 640 /app/src/*.py /app/config/*.json /app/health_check_service.py 2>/dev/null || true && \
    find /app -type d -exec chmod 750 {} \; && \
    find /app -type f -exec chmod 640 {} \; && \
    chmod 750 /app/start.sh /app/start-dev.sh

# Security: Create writable temp directory for application
RUN mkdir -p /app/tmp && \
    chown researchmanager:researchmanager /app/tmp && \
    chmod 750 /app/tmp

# Switch to non-root user
USER researchmanager

# Expose port
EXPOSE 8002

# Production stage (default)
FROM base AS production
# Security: Enhanced health check with timeout
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Security: Use tini as init system with child subreaper and exec form
ENTRYPOINT ["/sbin/tini", "-s", "-g", "--"]
CMD ["python", "-u", "src/research_manager_service.py"]

# Development stage
FROM base AS development
# Relaxed health check for development
HEALTHCHECK --interval=60s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Security: Use tini as init system with child subreaper and exec form
ENTRYPOINT ["/sbin/tini", "-s", "-g", "--"]
CMD ["./start-dev.sh"]
