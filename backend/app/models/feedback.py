"""
User Feedback Model

Stores user feedback and feature requests.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class FeedbackType(str, enum.Enum):
    """Feedback type enumeration."""
    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    IMPROVEMENT = "improvement"
    QUESTION = "question"
    OTHER = "other"


class FeedbackStatus(str, enum.Enum):
    """Feedback status enumeration."""
    NEW = "new"
    REVIEWING = "reviewing"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    WONT_FIX = "wont_fix"


class Feedback(Base):
    """User feedback and feature requests."""

    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(SQLEnum(FeedbackType), nullable=False, index=True)
    status = Column(SQLEnum(FeedbackStatus), default=FeedbackStatus.NEW, index=True)

    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)

    # Optional fields
    page_url = Column(String(500), nullable=True)  # Page where feedback was submitted
    browser_info = Column(String(200), nullable=True)
    screenshot_url = Column(String(500), nullable=True)

    # Admin fields
    admin_notes = Column(Text, nullable=True)
    assigned_to = Column(String(100), nullable=True)

    # Ratings (1-5 scale)
    satisfaction_rating = Column(Integer, nullable=True)  # Overall satisfaction
    feature_rating = Column(Integer, nullable=True)  # Specific feature rating

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="feedback")

    def __repr__(self):
        return f"<Feedback(id={self.id}, type={self.type}, title='{self.title[:30]}...')>"
