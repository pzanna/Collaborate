FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project structure
COPY . .

# Create logs directory
RUN mkdir -p /app/logs

# Set Python path to include the project root
ENV PYTHONPATH=/app

# Make the service executable
RUN chmod +x planning_agent_service_integrated.py

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python health_check.py || exit 1

# Run the integrated planning agent service
CMD ["python", "planning_agent_service_integrated.py"]
