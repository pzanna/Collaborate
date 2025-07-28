# Memory Agent Service - SECURITY HARDENED with Alpine
FROM python:3.12-alpine

# Security: Set build arguments for better control
ARG SERVICE_PORT=8009
ARG USER_ID=1000
ARG GROUP_ID=1000

# Security: Install security updates and minimal required packages for Python dependencies
RUN apk update && apk upgrade && \
    apk add --no-cache \
    gcc \
    musl-dev \
    g++ \
    sqlite \
    curl \
    ca-certificates \
    tini \
    libffi-dev \
    openssl-dev \
    linux-headers \
    make \
    && rm -rf /var/cache/apk/* \
    && rm -rf /tmp/*

# Security: Create dedicated non-root user with minimal privileges
RUN addgroup -g ${GROUP_ID} -S memoryagent && \
    adduser -u ${USER_ID} -S memoryagent -G memoryagent -h /app -s /sbin/nologin

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
COPY src/ ./src/
COPY config/ ./config/

# Copy shared health check service
COPY health_check_service.py ./health_check_service.py

# Security: Create secure data directory with proper permissions
RUN mkdir -p /app/data /app/tmp && \
    chown -R memoryagent:memoryagent /app && \
    chmod -R 750 /app && \
    chmod 640 /app/src/*.py /app/config/*.json /app/health_check_service.py 2>/dev/null || true && \
    find /app -type d -exec chmod 750 {} \; && \
    find /app -type f -exec chmod 640 {} \;

# Switch to non-root user
USER memoryagent

# Expose service port
EXPOSE 8009

# Security: Enhanced health check with timeout
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8009/health || exit 1

# Security: Use tini as init system and exec form
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["python", "-m", "uvicorn", "src.memory_service:app", "--host", "0.0.0.0", "--port", "8009"]
