"""Twitter platform database models."""

from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class TwitterUser(Base):
    """Twitter user being tracked."""
    __tablename__ = "twitter_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    username = Column(String(100), nullable=False)  # Twitter username (without @)
    display_name = Column(String(255))  # User's display name

    # Monitoring configuration
    is_monitoring = Column(Boolean, default=False, index=True)
    monitoring_interval_seconds = Column(Integer, default=300)  # Default 5 minutes
    days_to_collect = Column(Integer, default=7)  # How many days back to collect

    # Statistics
    total_tweets = Column(Integer, default=0)
    last_collected = Column(DateTime)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="twitter_users")
    tweets = relationship("Tweet", back_populates="twitter_user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TwitterUser(username='{self.username}', monitoring={self.is_monitoring})>"


class Tweet(Base):
    """Individual tweet collected from a Twitter user."""
    __tablename__ = "tweets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    twitter_user_id = Column(UUID(as_uuid=True), ForeignKey("twitter_users.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Tweet identification
    tweet_id = Column(String(50), unique=True, nullable=False, index=True)  # Twitter's tweet ID

    # Tweet content
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, index=True)  # When tweet was posted

    # Engagement metrics
    reply_count = Column(Integer, default=0)
    retweet_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    quote_count = Column(Integer, default=0)
    impression_count = Column(BigInteger, default=0)  # Views (if available)

    # Collection metadata
    collected_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    twitter_user = relationship("TwitterUser", back_populates="tweets")
    user = relationship("User", back_populates="tweets")

    def __repr__(self):
        return f"<Tweet(tweet_id='{self.tweet_id}', likes={self.like_count})>"


class TwitterMetrics(Base):
    """Aggregated metrics for Twitter users (calculated periodically)."""
    __tablename__ = "twitter_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    twitter_user_id = Column(UUID(as_uuid=True), ForeignKey("twitter_users.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Time period for these metrics
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    period_days = Column(Integer, default=7)  # Metrics calculated for last N days

    # Aggregated metrics
    total_tweets_in_period = Column(Integer, default=0)
    total_likes = Column(BigInteger, default=0)
    total_retweets = Column(BigInteger, default=0)
    total_replies = Column(BigInteger, default=0)
    total_impressions = Column(BigInteger, default=0)

    # Averages
    avg_likes_per_tweet = Column(Integer, default=0)
    avg_retweets_per_tweet = Column(Integer, default=0)
    avg_engagement_rate = Column(Integer, default=0)  # (likes + retweets + replies) / impressions * 100

    # Peak metrics
    most_liked_tweet_id = Column(String(50))
    most_retweeted_tweet_id = Column(String(50))

    # Relationships
    twitter_user = relationship("TwitterUser")
    user = relationship("User")

    def __repr__(self):
        return f"<TwitterMetrics(period={self.period_days}d, tweets={self.total_tweets_in_period})>"
