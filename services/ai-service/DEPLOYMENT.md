# Eunice AI Service - Secure Deployment Guide

## 🔐 Secure API Key Management for Containerized AI Service

The Eunice AI Service now includes secure API key handling for containerized deployment with multiple AI providers.

## ✅ Current Status

- **✅ Multi-provider support**: OpenAI, Anthropic Claude, and xAI Grok
- **✅ Secure key validation**: Format checking and placeholder detection
- **✅ Container-ready**: Proper environment variable handling
- **✅ Health monitoring**: Provider status tracking and error handling
- **✅ Production security**: Key masking, validation, and secure logging

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Load environment variables
cd /Users/paulzanna/Github/Eunice
source .env

# Verify keys are loaded
echo "API keys loaded: $(if [ -n "$OPENAI_API_KEY" ]; then echo "OpenAI ✅"; fi) $(if [ -n "$ANTHROPIC_API_KEY" ]; then echo "Anthropic ✅"; fi) $(if [ -n "$XAI_API_KEY" ]; then echo "xAI ✅"; fi)"
```

### 2. Container Deployment

```bash
# Using Docker directly
docker run -d \
  --name eunice-ai-service \
  -p 8010:8010 \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  -e XAI_API_KEY="$XAI_API_KEY" \
  -e SERVICE_HOST=0.0.0.0 \
  -e SERVICE_PORT=8010 \
  -e LOG_LEVEL=INFO \
  eunice-ai-service-secure

# Using Docker Compose (recommended)
docker-compose up ai-service
```

### 3. Health Verification

```bash
# Check service health
curl http://localhost:8010/health

# Expected response
{
  "status": "healthy",
  "providers": {
    "openai": {"status": "healthy"},
    "anthropic": {"status": "healthy"}, 
    "xai": {"status": "healthy"}
  },
  "uptime_seconds": 10,
  "total_requests": 0
}
```

## 🔧 Configuration

### AI Service Configuration (`services/ai-service/config/config.json`)

```json
{
  "service": {
    "name": "ai-service",
    "host": "0.0.0.0",
    "port": 8010
  },
  "providers": {
    "openai": {
      "enabled": true,
      "models": ["gpt-4o-mini", "gpt-4", "gpt-3.5-turbo"],
      "rate_limit": {
        "requests_per_minute": 50,
        "tokens_per_minute": 30000
      }
    },
    "anthropic": {
      "enabled": true,
      "models": ["claude-3-haiku-20240307", "claude-3-sonnet-20240229"],
      "rate_limit": {
        "requests_per_minute": 30,
        "tokens_per_minute": 20000
      }
    },
    "xai": {
      "enabled": true,
      "models": ["grok-3-mini", "grok-3"],
      "rate_limit": {
        "requests_per_minute": 40,
        "tokens_per_minute": 25000
      }
    }
  }
}
```

### Docker Compose Configuration

```yaml
ai-service:
  build: ./services/ai-service
  container_name: eunice-ai-service
  ports:
    - "8010:8010"
  environment:
    - SERVICE_HOST=0.0.0.0
    - SERVICE_PORT=8010
    - OPENAI_API_KEY=${OPENAI_API_KEY}
    - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    - XAI_API_KEY=${XAI_API_KEY}
    - LOG_LEVEL=INFO
  networks:
    - eunice-microservices
  restart: unless-stopped
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8010/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

## 🔒 Security Features

### API Key Validation

- **Format validation**: Checks proper key prefixes (`sk-`, `sk-ant-`, `xai-`)
- **Length validation**: Ensures keys meet minimum length requirements
- **Placeholder detection**: Rejects test/example keys
- **Error handling**: Graceful degradation when keys are invalid

### Secure Logging

- API keys are never logged in plaintext
- Only key presence/absence is logged
- Client initialization status is tracked
- Provider health monitoring without exposing credentials

### Container Security

- Environment variables for key passing
- No keys in image layers
- Runtime key validation
- Secure client initialization with error handling

## 📊 API Endpoints

### Health Check

```bash
GET /health
# Returns service and provider health status
```

### Chat Completions

```bash
POST /ai/chat/completions
Content-Type: application/json

{
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "user", "content": "Hello, how are you?"}
  ],
  "temperature": 0.7,
  "max_tokens": 2000
}
```

### Text Embeddings

```bash
POST /ai/embeddings
Content-Type: application/json

{
  "input": "Text to embed",
  "model": "text-embedding-ada-002"
}
```

### Available Models

```bash
GET /ai/models/available
# Returns available models by provider
```

### Usage Statistics

```bash
GET /ai/usage/statistics
# Returns usage metrics and provider status
```

## 🚀 Integration with Planning Agent

The Planning Agent is configured to use the AI service:

```yaml
planning-agent:
  environment:
    - AI_SERVICE_URL=http://ai-service:8010
  depends_on:
    - ai-service
```

The Planning Agent will:

1. **Primary**: Call AI service via HTTP API
2. **Fallback**: Direct OpenAI API calls if service unavailable
3. **Error handling**: Use mock responses if all AI calls fail

## 🔍 Testing

### Container Test

```bash
# Test container with real API keys
cd /Users/paulzanna/Github/Eunice
source .env
docker run --rm \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  -e XAI_API_KEY="$XAI_API_KEY" \
  eunice-ai-service-secure \
  python test_security.py
```

### Local Development Test

```bash
cd services/ai-service
python test_security.py
```

## 🛡️ Production Considerations

### Secrets Management

- Use Docker secrets or Kubernetes secrets for production
- Rotate API keys regularly
- Monitor API usage and costs
- Set up proper rate limiting

### Monitoring

- Health check endpoints for load balancers
- Usage statistics for cost tracking
- Provider status monitoring
- Error rate alerting

### Scaling

- Load balancing across multiple containers
- Provider failover and redundancy
- Caching for frequently used responses
- Rate limiting to prevent quota exhaustion

## ✅ Deployment Checklist

- [ ] API keys loaded in environment
- [ ] Container builds successfully
- [ ] Health endpoint returns healthy status
- [ ] All 3 providers initialize correctly
- [ ] Planning Agent can communicate with AI service
- [ ] Docker Compose orchestration works
- [ ] Rate limiting configured appropriately
- [ ] Monitoring and logging configured
- [ ] Security validation passes

The AI service is now ready for secure production deployment with proper API key management and multi-provider support!
