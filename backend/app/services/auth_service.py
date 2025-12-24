"""Authentication service with business logic."""

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, Tuple
from uuid import UUID

from app.models.user import User
from app.models.profile import UserSession
from app.models.schemas import UserCreate, UserLogin
from app.utils.security import hash_password, verify_password, create_access_token, validate_password_strength
from app.utils.validators import validate_email, validate_username
from app.config import settings


class AuthService:
    """Service for authentication operations."""

    @staticmethod
    def register_user(db: Session, user_data: UserCreate) -> Tuple[Optional[User], Optional[str]]:
        """
        Register a new user.

        Args:
            db: Database session
            user_data: User registration data

        Returns:
            Tuple of (user, error_message)
        """
        # Validate email
        is_valid, error = validate_email(user_data.email)
        if not is_valid:
            return None, error

        # Validate username
        is_valid, error = validate_username(user_data.username)
        if not is_valid:
            return None, error

        # Validate password strength
        is_valid, error = validate_password_strength(user_data.password)
        if not is_valid:
            return None, error

        # Check if email already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            return None, "Email already registered"

        # Check if username already exists
        existing_user = db.query(User).filter(User.username == user_data.username).first()
        if existing_user:
            return None, "Username already taken"

        # Create user
        hashed_pwd = hash_password(user_data.password)
        new_user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_pwd,
            full_name=user_data.full_name,
            is_active=True,
            is_superuser=False,
            email_verified=False  # In production, send verification email
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return new_user, None

    @staticmethod
    def authenticate_user(db: Session, login_data: UserLogin) -> Tuple[Optional[User], Optional[str]]:
        """
        Authenticate a user with username/password.

        Args:
            db: Database session
            login_data: Login credentials

        Returns:
            Tuple of (user, error_message)
        """
        # Find user by username or email
        user = db.query(User).filter(
            (User.username == login_data.username) | (User.email == login_data.username)
        ).first()

        if not user:
            return None, "Invalid credentials"

        if not user.is_active:
            return None, "Account is deactivated"

        if not verify_password(login_data.password, user.hashed_password):
            return None, "Invalid credentials"

        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()

        return user, None

    @staticmethod
    def create_user_session(
        db: Session,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """
        Create a new user session and JWT token.

        Args:
            db: Database session
            user: User object
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            JWT access token
        """
        # Create JWT token
        token_data = {
            "sub": str(user.id),
            "username": user.username
        }
        access_token = create_access_token(token_data)

        # Create session record
        expires_at = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        session = UserSession(
            user_id=user.id,
            session_token=access_token,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at
        )

        db.add(session)
        db.commit()

        return access_token

    @staticmethod
    def get_user_by_id(db: Session, user_id: UUID) -> Optional[User]:
        """
        Get user by ID.

        Args:
            db: Database session
            user_id: User UUID

        Returns:
            User object or None
        """
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """
        Get user by username.

        Args:
            db: Database session
            username: Username

        Returns:
            User object or None
        """
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def validate_session(db: Session, token: str) -> Tuple[Optional[User], Optional[str]]:
        """
        Validate a session token.

        Args:
            db: Database session
            token: JWT token

        Returns:
            Tuple of (user, error_message)
        """
        # Find session
        session = db.query(UserSession).filter(UserSession.session_token == token).first()

        if not session:
            return None, "Invalid session"

        # Check if session expired
        if session.expires_at < datetime.utcnow():
            db.delete(session)
            db.commit()
            return None, "Session expired"

        # Update last activity
        session.last_activity = datetime.utcnow()
        db.commit()

        # Get user
        user = db.query(User).filter(User.id == session.user_id).first()
        if not user or not user.is_active:
            return None, "User not found or inactive"

        return user, None

    @staticmethod
    def logout_user(db: Session, token: str) -> bool:
        """
        Logout user by deleting session.

        Args:
            db: Database session
            token: JWT token

        Returns:
            True if successful, False otherwise
        """
        session = db.query(UserSession).filter(UserSession.session_token == token).first()
        if session:
            db.delete(session)
            db.commit()
            return True
        return False

    @staticmethod
    def cleanup_expired_sessions(db: Session) -> int:
        """
        Clean up expired sessions.

        Args:
            db: Database session

        Returns:
            Number of sessions deleted
        """
        count = db.query(UserSession).filter(
            UserSession.expires_at < datetime.utcnow()
        ).delete()
        db.commit()
        return count
