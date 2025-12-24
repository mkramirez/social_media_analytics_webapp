"""User model for authentication and authorization."""

from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))

    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    api_profiles = relationship("APIProfile", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

    # Platform relationships
    twitch_channels = relationship("TwitchChannel", back_populates="user", cascade="all, delete-orphan")
    twitter_users = relationship("TwitterUser", back_populates="user", cascade="all, delete-orphan")
    tweets = relationship("Tweet", back_populates="user", cascade="all, delete-orphan")
    youtube_channels = relationship("YouTubeChannel", back_populates="user", cascade="all, delete-orphan")
    youtube_videos = relationship("YouTubeVideo", back_populates="user", cascade="all, delete-orphan")
    youtube_comments = relationship("YouTubeComment", back_populates="user", cascade="all, delete-orphan")
    reddit_subreddits = relationship("RedditSubreddit", back_populates="user", cascade="all, delete-orphan")
    reddit_posts = relationship("RedditPost", back_populates="user", cascade="all, delete-orphan")
    reddit_comments = relationship("RedditComment", back_populates="user", cascade="all, delete-orphan")

    # Analytics relationships
    sentiment_cache = relationship("SentimentCache", back_populates="user", cascade="all, delete-orphan")
    analytics_reports = relationship("AnalyticsReport", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"
