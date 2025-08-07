# Literature Agent - SECURITY HARDENED with Debian Slim
FROM python:3.12-slim

# Security: Set build arguments for better control
ARG SERVICE_PORT=8003
ARG USER_ID=1000
ARG GROUP_ID=1000

# Security: Install security updates and minimal required packages
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libc6-dev \
    curl \
    ca-certificates \
    tini \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/*

# Security: Create dedicated non-root user with minimal privileges
RUN groupadd -g ${GROUP_ID} literatureagent && \
    useradd -u ${USER_ID} -g literatureagent -m -d /home/literatureagent -s /sbin/nologin literatureagent

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
COPY onnx_models/ /app/onnx_models/
COPY start-dev.sh ./

# Security: Set strict file permissions and ownership
RUN chown -R literatureagent:literatureagent /app && \
    chmod -R 750 /app && \
    chmod 750 /app/start-dev.sh && \
    chmod 640 /app/src/*.py /app/config/*.json 2>/dev/null || true && \
    find /app -type d -not -path "/app/tmp" -exec chmod 750 {} \; && \
    find /app -type f -exec chmod 640 {} \; && \
    find /app -type d -exec chmod 750 {} \; && \
    chmod 750 /app/start-dev.sh

# Switch to non-root user
USER literatureagent

# Set environment variables for temporary directories
ENV TMPDIR=/app/tmp
ENV TMP=/app/tmp
ENV TEMP=/app/tmp

# Expose port
EXPOSE 8003

# Security: Enhanced health check with timeout
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Security: Use tini as init system and exec form
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-u", "src/literature_service.py"]
