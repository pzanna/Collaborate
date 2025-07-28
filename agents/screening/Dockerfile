# Screening Agent Container - SECURITY HARDENED with Alpine
FROM python:3.12-alpine

# Security: Set build arguments for better control
ARG SERVICE_PORT=8004
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
RUN addgroup -g ${GROUP_ID} -S screeningagent && \
    adduser -u ${USER_ID} -S screeningagent -G screeningagent -h /app -s /sbin/nologin

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

# Copy shared health check service
COPY health_check_service.py ./health_check_service.py

# Security: Set strict file permissions and ownership
RUN chown -R screeningagent:screeningagent /app && \
    chmod -R 750 /app && \
    chmod 640 /app/src/*.py /app/config/*.json /app/health_check_service.py && \
    find /app -type d -exec chmod 750 {} \; && \
    find /app -type f -exec chmod 640 {} \;

# Security: Create writable temp directory for application
RUN mkdir -p /app/tmp && \
    chown screeningagent:screeningagent /app/tmp && \
    chmod 750 /app/tmp

# Switch to non-root user
USER screeningagent

# Security: Use tini as init system to handle signals properly
ENTRYPOINT ["/sbin/tini", "--"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8004/health || exit 1

# Expose port
EXPOSE 8004

# Start the screening agent service
CMD ["python", "src/screening_service.py"]
