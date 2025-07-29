# Eunice Authentication Service

JWT-based authentication and Role-Based Access Control (RBAC) service for the Eunice Research Platform.

## Features

- 🔐 **JWT Authentication**: Secure token-based authentication
- 👥 **User Registration & Login**: Complete user lifecycle management
- 🛡️ **Role-Based Access Control**: Granular permission system
- 🔄 **Token Refresh**: Automatic token renewal
- 🏥 **Health Checks**: Built-in monitoring endpoints
- 🐳 **Docker Ready**: Containerized deployment

## API Endpoints

### Authentication

- `POST /register` - Register new user
- `POST /token` - Login and get JWT tokens
- `POST /refresh` - Refresh access token
- `GET /users/me` - Get current user info
- `PATCH /users/me` - Update current user

### Service Integration

- `POST /validate-token` - Validate JWT token (for other services)
- `POST /check-permission` - Check user permissions (RBAC)

### Monitoring

- `GET /health` - Health check endpoint

## User Roles

### Admin

- Full system access (`*:*`)

### Researcher  

- Literature: read, search, create
- Research: read, create, update
- Planning: read, create, update
- Memory: read, create, update
- Executor: read, create
- Writer: read, create, update

### Collaborator

- Literature: read
- Research: read, comment
- Planning: read
- Memory: read
- Writer: read

## Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Database
DATABASE_URL=postgresql://postgres:password@eunice-postgres:5432/eunice

# JWT
SECRET_KEY=your-secure-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Service
HOST=0.0.0.0
PORT=8013
DEBUG=false
```

## Development

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Locally

```bash
# Start the service
./start.sh

# Or directly with uvicorn
python -m uvicorn src.main:app --host 0.0.0.0 --port 8013 --reload
```

### Run Tests

```bash
pytest test_auth.py -v
```

## Docker Deployment

### Build Image

```bash
docker build -t eunice-auth-service .
```

### Run Container

```bash
docker run -p 8013:8013 \
  -e DATABASE_URL=postgresql://postgres:password@eunice-postgres:5432/eunice \
  -e SECRET_KEY=your-secret-key \
  eunice-auth-service
```

### Docker Compose

The service is included in the main `docker-compose.yml`:

```bash
docker-compose up auth-service
```

## Usage Examples

### Register User

```bash
curl -X POST "http://localhost:8013/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "researcher1", "email": "researcher1@example.com", "full_name": "Research User", "password": "securepassword123", "role": "researcher"}'
```

### Login

```bash
curl -X POST "http://localhost:8013/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=researcher1&password=securepassword123"
```

### Get User Info

```bash
curl -X GET "http://localhost:8013/users/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Validate Token (Service-to-Service)

```bash
curl -X POST "http://localhost:8013/validate-token" \
  -H "Content-Type: application/json" \
  -d '{"token": "YOUR_ACCESS_TOKEN"}'
```

## Integration with Other Services

Other services can authenticate requests by calling the `/validate-token` endpoint:

```python
import httpx

async def authenticate_request(token: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://auth-service:8013/validate-token",
            json={"token": token}
        )
        if response.status_code == 200:
            return response.json()
        return None
```

## Architecture

The authentication service follows the microservices pattern:

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   Client    │───▶│ API Gateway  │───▶│ Auth Service│
└─────────────┘    └──────────────┘    └─────────────┘
                           │                     │
                           ▼                     ▼
                   ┌──────────────┐    ┌─────────────┐
                   │ Other Services│    │  Database   │
                   └──────────────┘    └─────────────┘
```

## Security

- Passwords are hashed using bcrypt
- JWT tokens use HMAC SHA-256 algorithm
- Tokens include expiration times
- Refresh tokens have longer expiration (7 days default)
- Failed authentication attempts are logged

## Version

**Version 0.3.2** - Part of Eunice Platform microservices architecture
