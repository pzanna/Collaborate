FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p src config logs

# Copy source code
COPY src/ src/
COPY config/ config/

# Run the MCP AI service client
CMD ["python", "-m", "src.mcp_ai_service"]
