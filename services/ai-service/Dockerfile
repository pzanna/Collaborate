# AI Service - SECURITY HARDENED with Alpine
FROM python:3.12-alpine

# Security: Set build arguments for better control
ARG SERVICE_PORT=8010
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
RUN addgroup -g ${GROUP_ID} -S aiservice && \
    adduser -u ${USER_ID} -S aiservice -G aiservice -h /app -s /sbin/nologin

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

# Security: Create necessary directories with proper permissions
RUN mkdir -p src config logs tmp && \
    chown -R aiservice:aiservice /app && \
    chmod -R 750 /app

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY start-dev.sh ./

# Security: Set strict file permissions and ownership
RUN chown -R aiservice:aiservice /app && \
    chmod -R 750 /app && \
    chmod 750 /app/start-dev.sh && \
    chmod 640 /app/src/*.py /app/config/*.json /app/health_check_service.py 2>/dev/null || true && \
    find /app -type d -exec chmod 750 {} \; && \
    find /app -type f -exec chmod 640 {} \; && \
    chmod 750 /app/start-dev.sh

# Set secure environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONNOUSERSITE=1
ENV HEALTH_PORT=8010

# Switch to non-root user
USER aiservice

# Security: Use tini as init system and exec form
ENTRYPOINT ["/sbin/tini", "--"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8010/health || exit 1

# Expose health check port
EXPOSE 8010

CMD ["python", "-u", "-m", "src.mcp_ai_service"]
