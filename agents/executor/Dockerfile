# Executor Agent Container - SECURITY HARDENED with Alpine
FROM python:3.12-alpine

# Security: Set build arguments for better control
ARG SERVICE_PORT=8008
ARG USER_ID=1000
ARG GROUP_ID=1000

# Security: Install security updates and minimal required packages for Python dependencies
RUN apk update && apk upgrade && \
    apk add --no-cache \
    gcc \
    musl-dev \
    g++ \
    curl \
    ca-certificates \
    tini \
    bash \
    libffi-dev \
    openssl-dev \
    linux-headers \
    make \
    && rm -rf /var/cache/apk/* \
    && rm -rf /tmp/*

# Security: Create dedicated non-root user with minimal privileges
RUN addgroup -g ${GROUP_ID} -S executor && \
    adduser -u ${USER_ID} -S executor -G executor -h /app -s /sbin/nologin

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
COPY start.sh ./

# Copy shared health check service
COPY health_check_service.py ./health_check_service.py

# Security: Create secure work directory and set strict permissions
RUN mkdir -p /app/work /app/tmp && \
    chown -R executor:executor /app && \
    chmod -R 750 /app && \
    chmod 750 /app/start.sh && \
    chmod 640 /app/src/*.py /app/config/*.json /app/health_check_service.py 2>/dev/null || true && \
    find /app -type d -exec chmod 750 {} \; && \
    find /app -type f -exec chmod 640 {} \; && \
    chmod 750 /app/start.sh

# Switch to non-root user
USER executor

# Security: Enhanced health check with timeout
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8008/health || exit 1

# Expose port
EXPOSE 8008

# Security: Use tini as init system and exec form
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["./start.sh"]
