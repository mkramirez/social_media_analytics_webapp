"""Authentication middleware for protected routes."""

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.services.auth_service import AuthService
from app.utils.security import decode_access_token

# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user.

    Usage in routes:
        @app.get("/protected")
        def protected_route(current_user: User = Depends(get_current_user)):
            return {"user": current_user.username}

    Args:
        credentials: HTTP Authorization header with Bearer token
        db: Database session

    Returns:
        Current user

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials

    # Decode JWT token
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate session
    user, error = AuthService.validate_session(db, token)
    if error or not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error or "Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to get the current active user.

    Args:
        current_user: Current user from get_current_user

    Returns:
        Current active user

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Dependency to get the current superuser (admin).

    Args:
        current_user: Current active user

    Returns:
        Current superuser

    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


def get_optional_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Dependency to optionally get the current user.

    Returns None if no valid authentication is provided.
    Useful for routes that work with or without authentication.

    Args:
        authorization: Optional Authorization header
        db: Database session

    Returns:
        Current user or None
    """
    if not authorization:
        return None

    # Extract token from "Bearer <token>"
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None
    except ValueError:
        return None

    # Decode and validate
    payload = decode_access_token(token)
    if not payload:
        return None

    user, _ = AuthService.validate_session(db, token)
    return user
