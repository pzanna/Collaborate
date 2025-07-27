# AI Service Security Configuration Guide

## Overview

The AI Service handles sensitive API keys for multiple AI providers. This guide covers secure deployment practices.

## Environment Variables

### Required API Keys

```bash
# OpenAI
OPENAI_API_KEY=sk-proj-...

# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-api03-...

# xAI (X.AI)
XAI_API_KEY=xai-...
```

### Service Configuration

```bash
# Service binding
SERVICE_HOST=0.0.0.0
SERVICE_PORT=8010

# Logging level
LOG_LEVEL=INFO

# Optional Redis caching
REDIS_URL=redis://redis:6379
```

## Security Best Practices

### 1. API Key Management

- **Never commit API keys to version control**
- Use environment variables or secure vaults
- Rotate keys regularly
- Monitor API usage for anomalies

### 2. Container Security

```yaml
# docker-compose.yml example
services:
  ai-service:
    build: ./services/ai-service
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - XAI_API_KEY=${XAI_API_KEY}
    # Use secrets for production
    secrets:
      - openai_key
      - anthropic_key
      - xai_key
```

### 3. Network Security

- Use internal networks for service communication
- Implement proper firewall rules
- Enable HTTPS in production
- Use API gateways for external access

### 4. Monitoring

- Log all API requests (without sensitive data)
- Monitor token usage and costs
- Set up alerts for unusual activity
- Track provider health status

## Production Deployment

### Using Docker Secrets

```yaml
secrets:
  openai_key:
    external: true
  anthropic_key:
    external: true
  xai_key:
    external: true

services:
  ai-service:
    secrets:
      - source: openai_key
        target: /run/secrets/openai_key
      - source: anthropic_key
        target: /run/secrets/anthropic_key
      - source: xai_key
        target: /run/secrets/xai_key
```

### Using Kubernetes Secrets

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: ai-service-secrets
type: Opaque
data:
  openai-key: <base64-encoded-key>
  anthropic-key: <base64-encoded-key>
  xai-key: <base64-encoded-key>
```

### Environment Files

```bash
# Development
cp .env.example .env
# Edit .env with your API keys

# Production
# Use external secret management
# - AWS Secrets Manager
# - Azure Key Vault  
# - Google Secret Manager
# - HashiCorp Vault
```

## Rate Limiting and Cost Control

### Configure per-provider limits in config.json

```json
{
  "providers": {
    "openai": {
      "rate_limit": {
        "requests_per_minute": 50,
        "tokens_per_minute": 30000
      }
    }
  }
}
```

## Health Checks

The service provides health endpoints:

- `GET /health` - Overall service health
- `GET /ai/usage/statistics` - Usage metrics

## Troubleshooting

### Common Issues

1. **Invalid API Key Format**
   - Check key starts with correct prefix
   - Ensure no whitespace or newlines

2. **Provider Unavailable**
   - Check network connectivity
   - Verify API key permissions
   - Review rate limits

3. **Container Startup Issues**
   - Verify environment variables are set
   - Check Docker networking
   - Review service logs

### Debug Commands

```bash
# Check environment variables
docker exec eunice-ai-service env | grep API_KEY

# View service logs
docker logs eunice-ai-service

# Test health endpoint
curl http://localhost:8010/health
```
