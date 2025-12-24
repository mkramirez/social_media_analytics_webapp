"""
Unit tests for authentication endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import jwt

from app.models.user import User
from app.auth import get_password_hash, verify_password, create_access_token, decode_token


@pytest.mark.unit
@pytest.mark.auth
class TestUserRegistration:
    """Test user registration endpoint."""

    def test_register_new_user_success(self, client: TestClient, test_db: Session):
        """Test successful user registration."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePassword123!",
                "password_confirm": "SecurePassword123!"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert "id" in data
        assert "hashed_password" not in data  # Should not expose password
        assert "access_token" in data

        # Verify user was created in database
        user = test_db.query(User).filter(User.email == "newuser@example.com").first()
        assert user is not None
        assert user.is_active is True
        assert user.is_verified is False  # Not verified yet

    def test_register_duplicate_email(self, client: TestClient, test_user: User):
        """Test registration with existing email fails."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": test_user.email,
                "password": "SecurePassword123!",
                "password_confirm": "SecurePassword123!"
            }
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_password_mismatch(self, client: TestClient):
        """Test registration with mismatched passwords fails."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePassword123!",
                "password_confirm": "DifferentPassword456!"
            }
        )

        assert response.status_code == 400
        assert "passwords do not match" in response.json()["detail"].lower()

    def test_register_weak_password(self, client: TestClient):
        """Test registration with weak password fails."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "weak",
                "password_confirm": "weak"
            }
        )

        assert response.status_code == 400
        assert "password" in response.json()["detail"].lower()

    def test_register_invalid_email(self, client: TestClient):
        """Test registration with invalid email fails."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePassword123!",
                "password_confirm": "SecurePassword123!"
            }
        )

        assert response.status_code == 422  # Validation error


@pytest.mark.unit
@pytest.mark.auth
class TestUserLogin:
    """Test user login endpoint."""

    def test_login_success(self, client: TestClient, test_user: User):
        """Test successful login."""
        response = client.post(
            "/api/auth/login",
            data={
                "username": test_user.email,  # OAuth2 uses 'username' field
                "password": "testpassword123"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

        # Verify token is valid
        token = data["access_token"]
        payload = decode_token(token)
        assert payload["sub"] == test_user.email

    def test_login_wrong_password(self, client: TestClient, test_user: User):
        """Test login with incorrect password fails."""
        response = client.post(
            "/api/auth/login",
            data={
                "username": test_user.email,
                "password": "wrongpassword"
            }
        )

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with nonexistent user fails."""
        response = client.post(
            "/api/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "anypassword"
            }
        )

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_inactive_user(self, client: TestClient, test_db: Session):
        """Test login with inactive user fails."""
        # Create inactive user
        inactive_user = User(
            email="inactive@example.com",
            hashed_password=get_password_hash("testpassword123"),
            is_active=False,
            created_at=datetime.utcnow()
        )
        test_db.add(inactive_user)
        test_db.commit()

        response = client.post(
            "/api/auth/login",
            data={
                "username": "inactive@example.com",
                "password": "testpassword123"
            }
        )

        assert response.status_code == 401
        assert "inactive" in response.json()["detail"].lower()


@pytest.mark.unit
@pytest.mark.auth
class TestCurrentUser:
    """Test current user endpoint."""

    def test_get_current_user_success(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test getting current user with valid token."""
        response = client.get("/api/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["id"] == test_user.id
        assert data["is_active"] is True

    def test_get_current_user_no_token(self, client: TestClient):
        """Test getting current user without token fails."""
        response = client.get("/api/auth/me")

        assert response.status_code == 401
        assert "not authenticated" in response.json()["detail"].lower()

    def test_get_current_user_invalid_token(self, client: TestClient):
        """Test getting current user with invalid token fails."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )

        assert response.status_code == 401

    def test_get_current_user_expired_token(self, client: TestClient, test_user: User):
        """Test getting current user with expired token fails."""
        # Create expired token
        expired_token = create_access_token(
            data={"sub": test_user.email},
            expires_delta=timedelta(minutes=-30)  # Already expired
        )

        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()


@pytest.mark.unit
@pytest.mark.auth
class TestLogout:
    """Test user logout endpoint."""

    def test_logout_success(self, client: TestClient, auth_headers: dict):
        """Test successful logout."""
        response = client.post("/api/auth/logout", headers=auth_headers)

        assert response.status_code == 200
        assert "success" in response.json()["message"].lower()

    def test_logout_no_token(self, client: TestClient):
        """Test logout without token fails."""
        response = client.post("/api/auth/logout")

        assert response.status_code == 401


@pytest.mark.unit
@pytest.mark.auth
class TestPasswordHashing:
    """Test password hashing utilities."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 50  # Bcrypt hashes are long

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)

        assert verify_password("WrongPassword456!", hashed) is False

    def test_hash_password_different_salts(self):
        """Test that same password gets different hashes (different salts)."""
        password = "SecurePassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2  # Different salts
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


@pytest.mark.unit
@pytest.mark.auth
class TestJWTToken:
    """Test JWT token utilities."""

    def test_create_access_token(self, test_user: User):
        """Test creating access token."""
        token = create_access_token(data={"sub": test_user.email})

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50

    def test_decode_token_valid(self, test_user: User):
        """Test decoding valid token."""
        token = create_access_token(data={"sub": test_user.email})
        payload = decode_token(token)

        assert payload["sub"] == test_user.email
        assert "exp" in payload

    def test_decode_token_invalid(self):
        """Test decoding invalid token raises error."""
        with pytest.raises(jwt.InvalidTokenError):
            decode_token("invalid_token_here")

    def test_decode_token_expired(self, test_user: User):
        """Test decoding expired token raises error."""
        expired_token = create_access_token(
            data={"sub": test_user.email},
            expires_delta=timedelta(minutes=-30)
        )

        with pytest.raises(jwt.ExpiredSignatureError):
            decode_token(expired_token)

    def test_token_expiration_custom(self, test_user: User):
        """Test creating token with custom expiration."""
        token = create_access_token(
            data={"sub": test_user.email},
            expires_delta=timedelta(hours=1)
        )
        payload = decode_token(token)

        exp_time = datetime.fromtimestamp(payload["exp"])
        now = datetime.utcnow()
        time_diff = exp_time - now

        # Should expire in about 1 hour (with small margin for test execution)
        assert timedelta(minutes=59) < time_diff < timedelta(minutes=61)


@pytest.mark.unit
@pytest.mark.auth
class TestEmailVerification:
    """Test email verification functionality."""

    def test_verify_email_success(self, client: TestClient, test_db: Session):
        """Test email verification."""
        # Create unverified user
        user = User(
            email="unverified@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_verified=False,
            created_at=datetime.utcnow()
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        # Create verification token
        token = create_access_token(
            data={"sub": user.email, "type": "email_verification"},
            expires_delta=timedelta(hours=24)
        )

        response = client.post(f"/api/auth/verify-email?token={token}")

        assert response.status_code == 200
        assert "verified" in response.json()["message"].lower()

        # Check user is now verified
        test_db.refresh(user)
        assert user.is_verified is True

    def test_verify_email_invalid_token(self, client: TestClient):
        """Test email verification with invalid token fails."""
        response = client.post("/api/auth/verify-email?token=invalid_token")

        assert response.status_code == 400

    def test_verify_email_already_verified(self, client: TestClient, test_user: User):
        """Test verifying already verified email."""
        token = create_access_token(
            data={"sub": test_user.email, "type": "email_verification"}
        )

        response = client.post(f"/api/auth/verify-email?token={token}")

        assert response.status_code == 200
        # Should succeed but indicate already verified


@pytest.mark.unit
@pytest.mark.auth
class TestPasswordReset:
    """Test password reset functionality."""

    def test_request_password_reset(self, client: TestClient, test_user: User):
        """Test requesting password reset."""
        response = client.post(
            "/api/auth/password-reset/request",
            json={"email": test_user.email}
        )

        assert response.status_code == 200
        assert "email sent" in response.json()["message"].lower()

    def test_request_password_reset_nonexistent_user(self, client: TestClient):
        """Test requesting password reset for nonexistent user."""
        response = client.post(
            "/api/auth/password-reset/request",
            json={"email": "nonexistent@example.com"}
        )

        # Should return 200 to avoid user enumeration
        assert response.status_code == 200

    def test_reset_password_success(self, client: TestClient, test_user: User, test_db: Session):
        """Test successful password reset."""
        # Create reset token
        token = create_access_token(
            data={"sub": test_user.email, "type": "password_reset"},
            expires_delta=timedelta(hours=1)
        )

        new_password = "NewSecurePassword123!"
        response = client.post(
            "/api/auth/password-reset/confirm",
            json={
                "token": token,
                "new_password": new_password,
                "new_password_confirm": new_password
            }
        )

        assert response.status_code == 200
        assert "reset" in response.json()["message"].lower()

        # Verify can login with new password
        login_response = client.post(
            "/api/auth/login",
            data={
                "username": test_user.email,
                "password": new_password
            }
        )
        assert login_response.status_code == 200

    def test_reset_password_mismatch(self, client: TestClient, test_user: User):
        """Test password reset with mismatched passwords."""
        token = create_access_token(
            data={"sub": test_user.email, "type": "password_reset"}
        )

        response = client.post(
            "/api/auth/password-reset/confirm",
            json={
                "token": token,
                "new_password": "NewPassword123!",
                "new_password_confirm": "DifferentPassword456!"
            }
        )

        assert response.status_code == 400
        assert "do not match" in response.json()["detail"].lower()

    def test_reset_password_expired_token(self, client: TestClient, test_user: User):
        """Test password reset with expired token."""
        token = create_access_token(
            data={"sub": test_user.email, "type": "password_reset"},
            expires_delta=timedelta(hours=-1)  # Expired
        )

        response = client.post(
            "/api/auth/password-reset/confirm",
            json={
                "token": token,
                "new_password": "NewPassword123!",
                "new_password_confirm": "NewPassword123!"
            }
        )

        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()
