"""API Profile model for storing platform credentials."""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class APIProfile(Base):
    """API credential profile for a specific platform."""

    __tablename__ = "api_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    profile_name = Column(String(100), nullable=False)
    platform = Column(String(50), nullable=False, index=True)  # 'twitch', 'twitter', 'youtube', 'reddit'

    # Encrypted credentials stored as JSON
    encrypted_credentials = Column(Text, nullable=False)
    encryption_key_id = Column(String(100), nullable=True)  # Reference to AWS Secrets Manager key

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="api_profiles")

    def __repr__(self):
        return f"<APIProfile(id={self.id}, user_id={self.user_id}, platform={self.platform}, name={self.profile_name})>"


class UserSession(Base):
    """User session model for JWT token management."""

    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    session_token = Column(String(500), unique=True, nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    user_agent = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    last_activity = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at})>"
