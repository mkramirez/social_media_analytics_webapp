"""Authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    MessageResponse
)
from app.models.user import User
from app.services.auth_service import AuthService
from app.middleware.auth import get_current_active_user, security

router = APIRouter()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Register a new user.

    Requirements:
    - Unique email
    - Unique username (3-50 chars, alphanumeric + underscore)
    - Password (min 8 chars, uppercase, lowercase, digit, special char)

    Returns:
        JWT access token and user data
    """
    # Register user
    user, error = AuthService.register_user(db, user_data)

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )

    # Create session and generate token
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    access_token = AuthService.create_user_session(
        db=db,
        user=user,
        ip_address=ip_address,
        user_agent=user_agent
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.from_orm(user)
    )


@router.post("/login", response_model=Token)
async def login(
    login_data: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Login with username/email and password.

    Accepts either username or email in the username field.

    Returns:
        JWT access token and user data
    """
    # Authenticate user
    user, error = AuthService.authenticate_user(db, login_data)

    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create session and generate token
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    access_token = AuthService.create_user_session(
        db=db,
        user=user,
        ip_address=ip_address,
        user_agent=user_agent
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.from_orm(user)
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    credentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Logout current user by invalidating session.

    Requires:
        Authorization: Bearer <token>

    Returns:
        Success message
    """
    token = credentials.credentials
    success = AuthService.logout_user(db, token)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    return MessageResponse(message="Successfully logged out")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current authenticated user's information.

    Requires:
        Authorization: Bearer <token>

    Returns:
        Current user data
    """
    return UserResponse.from_orm(current_user)


@router.get("/verify", response_model=MessageResponse)
async def verify_token(
    current_user: User = Depends(get_current_active_user)
):
    """
    Verify if the current token is valid.

    Requires:
        Authorization: Bearer <token>

    Returns:
        Success message with username
    """
    return MessageResponse(
        message="Token is valid",
        detail=f"Authenticated as {current_user.username}"
    )
