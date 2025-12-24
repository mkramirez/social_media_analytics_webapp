"""Analytics database models for caching and storing analysis results."""

from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
import uuid


class SentimentCache(Base):
    """Cache for sentiment analysis results to avoid recomputing."""

    __tablename__ = "sentiment_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    text_hash = Column(String(32), nullable=False, unique=True, index=True)  # MD5 hash of text
    text_preview = Column(String(200), nullable=True)  # First 200 chars for reference

    # Sentiment scores
    negative = Column(Float, default=0.0)
    neutral = Column(Float, default=0.0)
    positive = Column(Float, default=0.0)
    compound = Column(Float, default=0.0)
    sentiment_label = Column(String(20), nullable=True)  # Positive, Negative, Neutral

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    model_name = Column(String(100), default="cardiffnlp/twitter-roberta-base-sentiment-latest")

    # Relationships
    user = relationship("User", back_populates="sentiment_cache")


class AnalyticsReport(Base):
    """Store generated analytics reports for caching and historical reference."""

    __tablename__ = "analytics_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Report metadata
    report_type = Column(String(50), nullable=False, index=True)  # engagement, sentiment, trend, posting_times
    platform = Column(String(20), nullable=True, index=True)  # twitch, twitter, youtube, reddit, cross_platform

    # Report parameters
    date_from = Column(DateTime, nullable=True)
    date_to = Column(DateTime, nullable=True)
    entity_ids = Column(JSON, nullable=True)  # List of entity IDs included in report

    # Report data (JSON)
    report_data = Column(JSON, nullable=False)  # Complete analytics results
    summary = Column(Text, nullable=True)  # Human-readable summary

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=True)  # Optional expiration for cache cleanup

    # Relationships
    user = relationship("User", back_populates="analytics_reports")
