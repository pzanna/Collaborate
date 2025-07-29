"""
Basic tests for the Authentication Service
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from src.main import app, get_session
from src.models import User


# Test database setup
@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite:///:memory:", 
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_health_check(client: TestClient):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "auth-service"


def test_register_user(client: TestClient):
    """Test user registration."""
    user_data = {
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "password": "testpassword123",
        "role": "researcher"
    }
    
    response = client.post("/register", json=user_data)
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Test"
    assert data["last_name"] == "User"
    assert data["email"] == "test@example.com"
    assert "id" in data


def test_login_user(client: TestClient):
    """Test user login."""
    # First register a user
    user_data = {
        "email": "login@example.com",
        "first_name": "Login",
        "last_name": "Test",
        "password": "testpassword123",
        "role": "researcher"
    }
    client.post("/register", json=user_data)
    
    # Then login (using email as username per OAuth2PasswordRequestForm)
    login_data = {
        "username": "login@example.com",  # OAuth2 uses username field but we pass email
        "password": "testpassword123"
    }
    
    response = client.post("/token", data=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_get_current_user(client: TestClient):
    """Test getting current user information."""
    # Register and login
    user_data = {
        "email": "current@example.com",
        "first_name": "Current",
        "last_name": "User",
        "password": "testpassword123",
        "role": "researcher"
    }
    client.post("/register", json=user_data)
    
    login_data = {
        "username": "current@example.com",  # OAuth2 uses username field but we pass email
        "password": "testpassword123"
    }
    login_response = client.post("/token", data=login_data)
    token = login_response.json()["access_token"]
    
    # Get current user
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/users/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Current"
    assert data["last_name"] == "User"
    assert data["email"] == "current@example.com"


def test_duplicate_username(client: TestClient):
    """Test that duplicate emails are rejected (username field removed)."""
    user_data = {
        "email": "duplicate@example.com",
        "first_name": "First",
        "last_name": "User",
        "password": "testpassword123",
        "role": "researcher"
    }
    
    # First registration should succeed
    response1 = client.post("/register", json=user_data)
    assert response1.status_code == 200
    
    # Second registration with same email should fail
    user_data["first_name"] = "Second"
    response2 = client.post("/register", json=user_data)
    assert response2.status_code == 400
    assert "Email already registered" in response2.json()["detail"]


def test_duplicate_email(client: TestClient):
    """Test that duplicate emails are rejected."""
    user_data = {
        "email": "duplicate@example.com",
        "first_name": "First",
        "last_name": "User",
        "password": "testpassword123",
        "role": "researcher"
    }
    
    # First registration should succeed
    response1 = client.post("/register", json=user_data)
    assert response1.status_code == 200
    
    # Second registration with same email should fail
    user_data["first_name"] = "Second"
    response2 = client.post("/register", json=user_data)
    assert response2.status_code == 400
    assert "Email already registered" in response2.json()["detail"]


def test_invalid_login(client: TestClient):
    """Test login with invalid credentials."""
    login_data = {
        "username": "nonexistent@example.com",  # OAuth2 uses username field but we pass email
        "password": "wrongpassword"
    }
    
    response = client.post("/token", data=login_data)
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]
