"""Pydantic schemas for request/response validation."""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
from uuid import UUID


# ============================================
# User Schemas
# ============================================

class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=8)

    @validator('username')
    def username_alphanumeric(cls, v):
        """Validate username is alphanumeric with underscores."""
        if not v[0].isalpha():
            raise ValueError('Username must start with a letter')
        if not all(c.isalnum() or c == '_' for c in v):
            raise ValueError('Username can only contain letters, numbers, and underscores')
        return v


class UserLogin(BaseModel):
    """Schema for user login."""
    username: str
    password: str


class UserResponse(UserBase):
    """Schema for user response."""
    id: UUID
    is_active: bool
    is_superuser: bool
    email_verified: bool
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    full_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None


class PasswordChange(BaseModel):
    """Schema for password change."""
    old_password: str
    new_password: str = Field(..., min_length=8)


# ============================================
# Authentication Schemas
# ============================================

class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    """Schema for decoded token data."""
    user_id: Optional[UUID] = None
    username: Optional[str] = None


# ============================================
# API Profile Schemas
# ============================================

class APIProfileBase(BaseModel):
    """Base API profile schema."""
    profile_name: str = Field(..., min_length=1, max_length=100)
    platform: str = Field(..., regex="^(twitch|twitter|youtube|reddit)$")


class APIProfileCreate(APIProfileBase):
    """Schema for creating API profile."""
    credentials: dict  # Will be encrypted before storage


class APIProfileUpdate(BaseModel):
    """Schema for updating API profile."""
    profile_name: Optional[str] = Field(None, min_length=1, max_length=100)
    credentials: Optional[dict] = None
    is_active: Optional[bool] = None


class APIProfileResponse(APIProfileBase):
    """Schema for API profile response (credentials not included)."""
    id: UUID
    user_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class APIProfileWithCredentials(APIProfileResponse):
    """Schema for API profile with decrypted credentials."""
    credentials: dict  # Decrypted credentials


# ============================================
# Generic Response Schemas
# ============================================

class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    detail: Optional[str] = None


class ErrorResponse(BaseModel):
    """Generic error response."""
    error: str
    detail: Optional[str] = None
    status_code: int
