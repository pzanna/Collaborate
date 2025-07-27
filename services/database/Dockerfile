FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make scripts executable
RUN chmod +x init_db.py startup.sh database_service.py

# Create non-root user
RUN useradd --create-home --shell /bin/bash dbservice && \
    chown -R dbservice:dbservice /app

USER dbservice

# Health check - removed since no API endpoints
# Database service health is monitored internally

# Start the pure database service
CMD ["./startup.sh"]
