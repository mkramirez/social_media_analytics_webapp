"""YouTube platform database models."""

from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class YouTubeChannel(Base):
    """YouTube channel being tracked."""
    __tablename__ = "youtube_channels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    channel_name = Column(String(255), nullable=False)  # Channel username or handle
    channel_id = Column(String(100))  # YouTube channel ID (UC...)
    display_name = Column(String(255))  # Channel display name

    # Monitoring configuration
    is_monitoring = Column(Boolean, default=False, index=True)
    monitoring_interval_seconds = Column(Integer, default=3600)  # Default 1 hour
    video_limit = Column(Integer, default=50)  # How many recent videos to track

    # Statistics
    total_videos = Column(Integer, default=0)
    total_comments = Column(Integer, default=0)
    last_collected = Column(DateTime)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="youtube_channels")
    videos = relationship("YouTubeVideo", back_populates="channel", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<YouTubeChannel(channel_name='{self.channel_name}', monitoring={self.is_monitoring})>"


class YouTubeVideo(Base):
    """Individual video from a YouTube channel."""
    __tablename__ = "youtube_videos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("youtube_channels.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Video identification
    video_id = Column(String(50), unique=True, nullable=False, index=True)  # YouTube video ID

    # Video content
    title = Column(Text, nullable=False)
    description = Column(Text)
    published_at = Column(DateTime, nullable=False, index=True)  # When video was published

    # Engagement metrics
    view_count = Column(BigInteger, default=0)
    like_count = Column(BigInteger, default=0)
    comment_count = Column(Integer, default=0)

    # Collection metadata
    collected_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    channel = relationship("YouTubeChannel", back_populates="videos")
    user = relationship("User", back_populates="youtube_videos")
    comments = relationship("YouTubeComment", back_populates="video", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<YouTubeVideo(video_id='{self.video_id}', views={self.view_count})>"


class YouTubeComment(Base):
    """Comment on a YouTube video."""
    __tablename__ = "youtube_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("youtube_videos.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Comment identification
    comment_id = Column(String(100), unique=True, nullable=False, index=True)  # YouTube comment ID

    # Comment content
    text = Column(Text, nullable=False)
    author = Column(String(255))
    like_count = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)
    published_at = Column(DateTime, nullable=False)

    # Collection metadata
    collected_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    video = relationship("YouTubeVideo", back_populates="comments")
    user = relationship("User", back_populates="youtube_comments")

    def __repr__(self):
        return f"<YouTubeComment(comment_id='{self.comment_id}', likes={self.like_count})>"


class YouTubeMetrics(Base):
    """Aggregated metrics for YouTube channels (calculated periodically)."""
    __tablename__ = "youtube_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("youtube_channels.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Time period for these metrics
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    period_days = Column(Integer, default=30)  # Metrics calculated for last N days

    # Aggregated metrics
    total_videos_in_period = Column(Integer, default=0)
    total_views = Column(BigInteger, default=0)
    total_likes = Column(BigInteger, default=0)
    total_comments = Column(BigInteger, default=0)

    # Averages
    avg_views_per_video = Column(BigInteger, default=0)
    avg_likes_per_video = Column(Integer, default=0)
    avg_comments_per_video = Column(Integer, default=0)
    avg_engagement_rate = Column(Integer, default=0)  # (likes + comments) / views * 100

    # Peak metrics
    most_viewed_video_id = Column(String(50))
    most_liked_video_id = Column(String(50))

    # Relationships
    channel = relationship("YouTubeChannel")
    user = relationship("User")

    def __repr__(self):
        return f"<YouTubeMetrics(period={self.period_days}d, videos={self.total_videos_in_period})>"
