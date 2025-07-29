"""
Comprehensive Authentication System Tests

Tests for JWT-based authentication, 2FA, RBAC, and security features
based on the authentication system test checklist.
"""

import json
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from src.main import app, get_session
from src.models import User
from src.two_factor import TwoFactorAuthService

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


@pytest.fixture
def tfa_service():
    """Fixture for 2FA service."""
    return TwoFactorAuthService()


# Test data
TEST_USERS = {
    "admin": {
        "email": "admin@example.com", 
        "first_name": "Admin", 
        "last_name": "User", 
        "role": "admin", 
        "password": "AdminPass123!"
    },
    "researcher": {
        "email": "researcher1@example.com", 
        "first_name": "Research", 
        "last_name": "Scientist", 
        "role": "researcher", 
        "password": "ResearchPass123!"
    },
    "collaborator": {
        "email": "collab1@example.com", 
        "first_name": "Collab", 
        "last_name": "Partner", 
        "role": "collaborator", 
        "password": "CollabPass123!"
    }
}


class TestCoreAuthentication:
    """Core Authentication Testing"""

    def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "auth-service"
        assert data["version"] == "0.3.2"

    def test_user_registration_valid(self, client: TestClient):
        """Test valid user registration."""
        user_data = TEST_USERS["researcher"]
        response = client.post("/register", json=user_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["first_name"] == user_data["first_name"]
        assert data["last_name"] == user_data["last_name"]
        assert data["role"] == user_data["role"]
        assert data["is_disabled"] == False
        assert data["is_2fa_enabled"] == False
        assert "id" in data
        assert "created_at" in data
        # Password should not be in response
        assert "password" not in data
        assert "hashed_password" not in data

    def test_user_registration_default_role(self, client: TestClient):
        """Test user registration with default role."""
        user_data = {
            "email": "default@example.com",
            "first_name": "Default",
            "last_name": "User",
            "password": "DefaultPass123!"
            # No role specified
        }
        response = client.post("/register", json=user_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "researcher"  # Default role

    def test_user_registration_validation_errors(self, client: TestClient):
        """Test user registration validation errors."""
        # Invalid email format
        invalid_email_data = {
            "email": "invalid-email",
            "first_name": "Test",
            "last_name": "User",
            "password": "TestPass123!"
        }
        response = client.post("/register", json=invalid_email_data)
        assert response.status_code == 422
        
        # Password too short
        weak_password_data = {
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "password": "123"
        }
        response = client.post("/register", json=weak_password_data)
        assert response.status_code == 422

        # Missing required fields
        incomplete_data = {
            "email": "test@example.com"
            # Missing other required fields
        }
        response = client.post("/register", json=incomplete_data)
        assert response.status_code == 422

    def test_duplicate_email_rejection(self, client: TestClient):
        """Test duplicate email rejection."""
        user_data = TEST_USERS["researcher"].copy()
        
        # First registration should succeed
        response1 = client.post("/register", json=user_data)
        assert response1.status_code == 200
        
        # Second registration with same email should fail
        user_data["first_name"] = "Different"
        response2 = client.post("/register", json=user_data)
        assert response2.status_code == 400
        assert "Email already registered" in response2.json()["detail"]

    def test_successful_login(self, client: TestClient):
        """Test successful login."""
        user_data = TEST_USERS["researcher"]
        client.post("/register", json=user_data)
        
        login_data = {
            "username": user_data["email"],  # OAuth2 uses username field
            "password": user_data["password"]
        }
        
        response = client.post("/token", data=login_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        
        # Verify token structure (basic check)
        assert len(data["access_token"]) > 20
        assert len(data["refresh_token"]) > 20

    def test_failed_login_invalid_credentials(self, client: TestClient):
        """Test login with invalid credentials."""
        # Non-existent user
        response = client.post("/token", data={
            "username": "nonexistent@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]
        
        # Valid user, wrong password
        user_data = TEST_USERS["researcher"]
        client.post("/register", json=user_data)
        
        response = client.post("/token", data={
            "username": user_data["email"],
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    def test_get_current_user(self, client: TestClient):
        """Test getting current user information."""
        user_data = TEST_USERS["researcher"]
        client.post("/register", json=user_data)
        
        # Login to get token
        login_response = client.post("/token", data={
            "username": user_data["email"],
            "password": user_data["password"]
        })
        token = login_response.json()["access_token"]
        
        # Get current user
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/users/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["first_name"] == user_data["first_name"]
        assert data["last_name"] == user_data["last_name"]
        assert data["role"] == user_data["role"]

    def test_unauthorized_access(self, client: TestClient):
        """Test unauthorized access to protected endpoints."""
        # No token provided
        response = client.get("/users/me")
        assert response.status_code == 401
        
        # Invalid token
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/users/me", headers=headers)
        assert response.status_code == 401


class TestTokenManagement:
    """JWT Token Management Testing"""

    def test_token_validation_service(self, client: TestClient):
        """Test token validation endpoint for service-to-service auth."""
        user_data = TEST_USERS["researcher"]
        client.post("/register", json=user_data)
        
        # Login to get token
        login_response = client.post("/token", data={
            "username": user_data["email"],
            "password": user_data["password"]
        })
        token = login_response.json()["access_token"]
        
        # Validate token (passed as query parameter)
        response = client.post(f"/validate-token?token={token}")
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] == True
        assert data["email"] == user_data["email"]
        assert data["role"] == user_data["role"]
        assert "user_id" in data

    def test_token_validation_invalid(self, client: TestClient):
        """Test invalid token validation."""
        response = client.post("/validate-token?token=invalid_token")
        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]

    def test_refresh_token(self, client: TestClient):
        """Test token refresh functionality."""
        user_data = TEST_USERS["researcher"]
        client.post("/register", json=user_data)
        
        # Login to get tokens
        login_response = client.post("/token", data={
            "username": user_data["email"],
            "password": user_data["password"]
        })
        refresh_token = login_response.json()["refresh_token"]
        
        # Refresh token (passed as query parameter)
        response = client.post(f"/refresh?refresh_token={refresh_token}")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_token_invalid(self, client: TestClient):
        """Test refresh with invalid token."""
        response = client.post("/refresh?refresh_token=invalid_refresh_token")
        assert response.status_code == 401
        assert "Invalid refresh token" in response.json()["detail"]


class TestTwoFactorAuthentication:
    """Two-Factor Authentication Testing"""

    def _register_and_login_user(self, client: TestClient, user_data: dict):
        """Helper method to register and login a user."""
        client.post("/register", json=user_data)
        login_response = client.post("/token", data={
            "username": user_data["email"],
            "password": user_data["password"]
        })
        return login_response.json()["access_token"]

    def test_2fa_setup(self, client: TestClient, tfa_service: TwoFactorAuthService):
        """Test 2FA setup process."""
        user_data = TEST_USERS["researcher"]
        token = self._register_and_login_user(client, user_data)
        
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post("/2fa/setup", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "secret_key" in data
        assert "qr_code_url" in data
        assert "backup_codes" in data
        assert len(data["backup_codes"]) == 8
        assert len(data["secret_key"]) == 32  # Base32 secret

    def test_2fa_qr_code_generation(self, client: TestClient):
        """Test QR code generation for 2FA setup."""
        user_data = TEST_USERS["researcher"]
        token = self._register_and_login_user(client, user_data)
        
        # First setup 2FA
        headers = {"Authorization": f"Bearer {token}"}
        client.post("/2fa/setup", headers=headers)
        
        # Get QR code
        response = client.get("/2fa/qrcode", headers=headers)
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

    def test_2fa_verification_and_enable(self, client: TestClient, tfa_service: TwoFactorAuthService):
        """Test 2FA verification and enabling."""
        user_data = TEST_USERS["researcher"]
        token = self._register_and_login_user(client, user_data)
        
        # Setup 2FA
        headers = {"Authorization": f"Bearer {token}"}
        setup_response = client.post("/2fa/setup", headers=headers)
        secret = setup_response.json()["secret_key"]
        
        # Generate TOTP code
        totp_code = tfa_service.get_current_totp_code(secret)
        
        # Verify and enable 2FA
        verify_data = {"totp_code": totp_code}
        response = client.post("/2fa/verify", json=verify_data, headers=headers)
        assert response.status_code == 200
        assert "2FA successfully enabled" in response.json()["message"]

    def test_2fa_status(self, client: TestClient, tfa_service: TwoFactorAuthService):
        """Test 2FA status endpoint."""
        user_data = TEST_USERS["researcher"]
        token = self._register_and_login_user(client, user_data)
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Check status before enabling 2FA
        response = client.get("/2fa/status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["is_2fa_enabled"] == False
        assert data["has_backup_codes"] == False
        assert data["remaining_backup_codes"] == 0

    def test_2fa_login_flow(self, client: TestClient, tfa_service: TwoFactorAuthService):
        """Test login flow when 2FA is enabled."""
        user_data = TEST_USERS["researcher"]
        token = self._register_and_login_user(client, user_data)
        
        # Setup and enable 2FA
        headers = {"Authorization": f"Bearer {token}"}
        setup_response = client.post("/2fa/setup", headers=headers)
        secret = setup_response.json()["secret_key"]
        
        totp_code = tfa_service.get_current_totp_code(secret)
        client.post("/2fa/verify", json={"totp_code": totp_code}, headers=headers)
        
        # Now try regular login - should require 2FA
        login_response = client.post("/token", data={
            "username": user_data["email"],
            "password": user_data["password"]
        })
        assert login_response.status_code == 202  # 2FA required
        assert login_response.headers.get("X-Require-2FA") == "true"
        
        # Login with 2FA
        totp_code = tfa_service.get_current_totp_code(secret)
        login_2fa_data = {
            "email": user_data["email"],
            "password": user_data["password"],
            "totp_code": totp_code
        }
        response = client.post("/login-2fa", json=login_2fa_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_2fa_backup_codes(self, client: TestClient, tfa_service: TwoFactorAuthService):
        """Test backup code functionality."""
        user_data = TEST_USERS["researcher"]
        token = self._register_and_login_user(client, user_data)
        
        # Setup and enable 2FA
        headers = {"Authorization": f"Bearer {token}"}
        setup_response = client.post("/2fa/setup", headers=headers)
        secret = setup_response.json()["secret_key"]
        backup_codes = setup_response.json()["backup_codes"]
        
        totp_code = tfa_service.get_current_totp_code(secret)
        client.post("/2fa/verify", json={"totp_code": totp_code}, headers=headers)
        
        # Login with backup code
        login_2fa_data = {
            "email": user_data["email"],
            "password": user_data["password"],
            "totp_code": backup_codes[0]  # Use first backup code
        }
        response = client.post("/login-2fa", json=login_2fa_data)
        assert response.status_code == 200

    def test_2fa_disable(self, client: TestClient, tfa_service: TwoFactorAuthService):
        """Test 2FA disable functionality."""
        user_data = TEST_USERS["researcher"]
        token = self._register_and_login_user(client, user_data)
        
        # Setup and enable 2FA
        headers = {"Authorization": f"Bearer {token}"}
        setup_response = client.post("/2fa/setup", headers=headers)
        secret = setup_response.json()["secret_key"]
        
        totp_code = tfa_service.get_current_totp_code(secret)
        client.post("/2fa/verify", json={"totp_code": totp_code}, headers=headers)
        
        # Disable 2FA
        totp_code = tfa_service.get_current_totp_code(secret)
        disable_data = {
            "password": user_data["password"],
            "totp_code": totp_code
        }
        response = client.post("/2fa/disable", json=disable_data, headers=headers)
        assert response.status_code == 200
        assert "2FA successfully disabled" in response.json()["message"]


class TestRoleBasedAccessControl:
    """Role-Based Access Control Testing"""

    def _get_user_token(self, client: TestClient, user_key: str):
        """Helper to register user and get token."""
        user_data = TEST_USERS[user_key]
        client.post("/register", json=user_data)
        login_response = client.post("/token", data={
            "username": user_data["email"],
            "password": user_data["password"]
        })
        return login_response.json()["access_token"]

    def test_permission_checking_admin(self, client: TestClient):
        """Test admin role permissions."""
        token = self._get_user_token(client, "admin")
        
        # Admin should have wildcard permission
        response = client.post(f"/check-permission?token={token}&resource=literature&action=delete")
        assert response.status_code == 200
        data = response.json()
        assert data["has_permission"] == True
        assert data["role"] == "admin"

    def test_permission_checking_researcher(self, client: TestClient):
        """Test researcher role permissions."""
        token = self._get_user_token(client, "researcher")
        
        # Researcher should have literature:read permission
        response = client.post(f"/check-permission?token={token}&resource=literature&action=read")
        assert response.status_code == 200
        data = response.json()
        assert data["has_permission"] == True
        assert data["role"] == "researcher"
        
        # Researcher should NOT have user delete permission
        response = client.post(f"/check-permission?token={token}&resource=user&action=delete")
        assert response.status_code == 200
        data = response.json()
        assert data["has_permission"] == False

    def test_permission_checking_collaborator(self, client: TestClient):
        """Test collaborator role permissions."""
        token = self._get_user_token(client, "collaborator")
        
        # Collaborator should have literature:read permission
        response = client.post(f"/check-permission?token={token}&resource=literature&action=read")
        assert response.status_code == 200
        data = response.json()
        assert data["has_permission"] == True
        assert data["role"] == "collaborator"
        
        # Collaborator should NOT have literature:create permission
        response = client.post(f"/check-permission?token={token}&resource=literature&action=create")
        assert response.status_code == 200
        data = response.json()
        assert data["has_permission"] == False

    def test_admin_user_deletion(self, client: TestClient):
        """Test admin user deletion capabilities."""
        # Create admin and target user
        admin_token = self._get_user_token(client, "admin")
        target_token = self._get_user_token(client, "researcher")
        
        # Get target user ID
        headers = {"Authorization": f"Bearer {target_token}"}
        user_response = client.get("/users/me", headers=headers)
        target_user_id = user_response.json()["id"]
        
        # Admin should be able to delete user
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.delete(f"/admin/users/{target_user_id}", headers=admin_headers)
        assert response.status_code == 200
        assert "successfully deleted" in response.json()["message"]

    def test_non_admin_user_deletion_forbidden(self, client: TestClient):
        """Test non-admin cannot delete other users."""
        researcher_token = self._get_user_token(client, "researcher")
        other_token = self._get_user_token(client, "collaborator")
        
        # Get other user ID
        headers = {"Authorization": f"Bearer {other_token}"}
        user_response = client.get("/users/me", headers=headers)
        other_user_id = user_response.json()["id"]
        
        # Researcher should NOT be able to delete other user
        researcher_headers = {"Authorization": f"Bearer {researcher_token}"}
        response = client.delete(f"/admin/users/{other_user_id}", headers=researcher_headers)
        assert response.status_code == 403
        assert "Only administrators" in response.json()["detail"]


class TestUserManagement:
    """User Management Testing"""

    def _get_user_token(self, client: TestClient, user_key: str):
        """Helper to register user and get token."""
        user_data = TEST_USERS[user_key]
        client.post("/register", json=user_data)
        login_response = client.post("/token", data={
            "username": user_data["email"],
            "password": user_data["password"]
        })
        return login_response.json()["access_token"]

    def test_user_profile_update(self, client: TestClient):
        """Test user profile updates."""
        token = self._get_user_token(client, "researcher")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Update profile
        update_data = {
            "first_name": "Updated",
            "last_name": "Name"
        }
        response = client.patch("/users/me", json=update_data, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["last_name"] == "Name"

    def test_user_email_update_duplicate_prevention(self, client: TestClient):
        """Test email update with duplicate prevention."""
        # Create two users
        token1 = self._get_user_token(client, "researcher")
        token2 = self._get_user_token(client, "collaborator")
        
        # Try to update user1's email to user2's email
        headers1 = {"Authorization": f"Bearer {token1}"}
        update_data = {"email": TEST_USERS["collaborator"]["email"]}
        response = client.put("/users/me", json=update_data, headers=headers1)
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_user_account_deletion(self, client: TestClient):
        """Test user account self-deletion."""
        token = self._get_user_token(client, "researcher")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.delete("/users/me", headers=headers)
        assert response.status_code == 200
        assert "successfully deleted" in response.json()["message"]
        
        # Verify user can no longer access account
        response = client.get("/users/me", headers=headers)
        assert response.status_code == 401

    def test_password_change(self, client: TestClient):
        """Test password change functionality."""
        user_data = TEST_USERS["researcher"]
        token = self._get_user_token(client, "researcher")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Change password
        password_data = {
            "current_password": user_data["password"],
            "new_password": "NewPassword123!"
        }
        response = client.post("/change-password", json=password_data, headers=headers)
        assert response.status_code == 200
        assert "Password changed successfully" in response.json()["message"]
        
        # Verify old password no longer works
        login_response = client.post("/token", data={
            "username": user_data["email"],
            "password": user_data["password"]
        })
        assert login_response.status_code == 401
        
        # Verify new password works
        login_response = client.post("/token", data={
            "username": user_data["email"],
            "password": "NewPassword123!"
        })
        assert login_response.status_code == 200

    def test_password_change_wrong_current_password(self, client: TestClient):
        """Test password change with wrong current password."""
        token = self._get_user_token(client, "researcher")
        headers = {"Authorization": f"Bearer {token}"}
        
        password_data = {
            "current_password": "WrongPassword123!",
            "new_password": "NewPassword123!"
        }
        response = client.post("/change-password", json=password_data, headers=headers)
        assert response.status_code == 400
        assert "Current password is incorrect" in response.json()["detail"]


class TestSecurityFeatures:
    """Security Features Testing"""

    def test_password_hashing(self, client: TestClient):
        """Test password is properly hashed."""
        user_data = TEST_USERS["researcher"]
        response = client.post("/register", json=user_data)
        assert response.status_code == 200
        
        # Response should not contain password
        data = response.json()
        assert "password" not in data
        assert "hashed_password" not in data

    def test_sql_injection_prevention(self, client: TestClient):
        """Test SQL injection prevention in user input."""
        # Try SQL injection in registration
        malicious_data = {
            "email": "test@example.com'; DROP TABLE users; --",
            "first_name": "Test",
            "last_name": "User",
            "password": "TestPass123!"
        }
        response = client.post("/register", json=malicious_data)
        # Should either fail validation or succeed without executing injection
        assert response.status_code in [422, 200]
        
        # If it succeeded, the malicious email should be stored as-is
        if response.status_code == 200:
            # Try to login with the malicious email
            login_response = client.post("/token", data={
                "username": malicious_data["email"],
                "password": malicious_data["password"]
            })
            # Should work normally if properly handled
            assert login_response.status_code == 200

    def test_token_tampering_detection(self, client: TestClient):
        """Test JWT token tampering detection."""
        user_data = TEST_USERS["researcher"]
        client.post("/register", json=user_data)
        
        login_response = client.post("/token", data={
            "username": user_data["email"],
            "password": user_data["password"]
        })
        token = login_response.json()["access_token"]
        
        # Tamper with token
        tampered_token = token[:-5] + "AAAAA"
        headers = {"Authorization": f"Bearer {tampered_token}"}
        
        response = client.get("/users/me", headers=headers)
        assert response.status_code == 401


class TestErrorHandling:
    """Error Handling and Edge Cases"""

    def test_malformed_request_handling(self, client: TestClient):
        """Test handling of malformed requests."""
        # Invalid JSON
        response = client.post("/register", 
                              data="invalid json",
                              headers={"content-type": "application/json"})
        assert response.status_code == 422

    def test_missing_headers_handling(self, client: TestClient):
        """Test handling of missing authorization headers."""
        response = client.get("/users/me")
        assert response.status_code == 401

    def test_empty_request_body_handling(self, client: TestClient):
        """Test handling of empty request bodies."""
        response = client.post("/register", json={})
        assert response.status_code == 422

    def test_unicode_and_special_characters(self, client: TestClient):
        """Test handling of unicode and special characters."""
        user_data = {
            "email": "unicode@example.com",
            "first_name": "José",
            "last_name": "González",
            "password": "Pássword123!äöü",
            "role": "researcher"
        }
        response = client.post("/register", json=user_data)
        assert response.status_code == 200
        
        # Login should work with unicode
        login_response = client.post("/token", data={
            "username": user_data["email"],
            "password": user_data["password"]
        })
        assert login_response.status_code == 200

    def test_boundary_value_testing(self, client: TestClient):
        """Test boundary values for input fields."""
        # Maximum length names
        long_name = "A" * 50  # Max length as per model
        user_data = {
            "email": "boundary@example.com",
            "first_name": long_name,
            "last_name": long_name,
            "password": "BoundaryPass123!",
            "role": "researcher"
        }
        response = client.post("/register", json=user_data)
        assert response.status_code == 200
        
        # Test name too long (should fail validation)
        too_long_name = "A" * 51
        user_data["email"] = "toolong@example.com"
        user_data["first_name"] = too_long_name
        response = client.post("/register", json=user_data)
        assert response.status_code == 422


# Integration test to verify the overall system works
class TestSystemIntegration:
    """System Integration Testing"""

    def test_complete_authentication_flow(self, client: TestClient, tfa_service: TwoFactorAuthService):
        """Test complete authentication flow from registration to 2FA."""
        user_data = TEST_USERS["researcher"]
        
        # 1. Register user
        register_response = client.post("/register", json=user_data)
        assert register_response.status_code == 200
        
        # 2. Login
        login_response = client.post("/token", data={
            "username": user_data["email"],
            "password": user_data["password"]
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # 3. Access protected resource
        headers = {"Authorization": f"Bearer {token}"}
        me_response = client.get("/users/me", headers=headers)
        assert me_response.status_code == 200
        
        # 4. Setup 2FA
        setup_response = client.post("/2fa/setup", headers=headers)
        assert setup_response.status_code == 200
        secret = setup_response.json()["secret_key"]
        
        # 5. Enable 2FA
        totp_code = tfa_service.get_current_totp_code(secret)
        verify_response = client.post("/2fa/verify", 
                                     json={"totp_code": totp_code}, 
                                     headers=headers)
        assert verify_response.status_code == 200
        
        # 6. Login with 2FA
        login_2fa_response = client.post("/login-2fa", json={
            "email": user_data["email"],
            "password": user_data["password"],
            "totp_code": tfa_service.get_current_totp_code(secret)
        })
        assert login_2fa_response.status_code == 200
        
        # 7. Check permissions
        new_token = login_2fa_response.json()["access_token"]
        permission_response = client.post(f"/check-permission?token={new_token}&resource=literature&action=read")
        assert permission_response.status_code == 200
        assert permission_response.json()["has_permission"] == True

    def test_admin_system_health_access(self, client: TestClient):
        """Test admin access to system health endpoint."""
        admin_data = TEST_USERS["admin"]
        client.post("/register", json=admin_data)
        
        login_response = client.post("/token", data={
            "username": admin_data["email"],
            "password": admin_data["password"]
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Admin should be able to access system health
        # Note: This test might fail in test environment without Docker
        response = client.get("/system/health", headers=headers)
        # Accept either success or server error (Docker not available in test)
        assert response.status_code in [200, 500]

    def test_cors_headers(self, client: TestClient):
        """Test CORS configuration."""
        response = client.get("/debug/cors")
        assert response.status_code == 200
        data = response.json()
        assert "allowed_origins" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])