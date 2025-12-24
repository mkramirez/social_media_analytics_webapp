"""Twitch platform models."""

from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class TwitchChannel(Base):
    """Twitch channel being monitored."""

    __tablename__ = "twitch_channels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    username = Column(String(100), nullable=False)
    display_name = Column(String(100), nullable=True)
    channel_id = Column(String(100), nullable=True)  # Twitch user ID

    is_monitoring = Column(Boolean, default=False, nullable=False, index=True)
    monitoring_interval_seconds = Column(Integer, default=30, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_checked = Column(DateTime, nullable=True)
    total_records = Column(Integer, default=0, nullable=False)

    # Relationships
    user = relationship("User", back_populates="twitch_channels")
    stream_records = relationship("TwitchStreamRecord", back_populates="channel", cascade="all, delete-orphan")
    chat_stats = relationship("TwitchChatStats", back_populates="channel", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TwitchChannel(id={self.id}, username={self.username}, user_id={self.user_id})>"


class TwitchStreamRecord(Base):
    """Twitch stream data record."""

    __tablename__ = "twitch_stream_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("twitch_channels.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    timestamp = Column(DateTime, nullable=False, index=True)
    viewer_count = Column(Integer, default=0, nullable=False)
    game_name = Column(String(200), nullable=True)
    stream_title = Column(String(500), nullable=True)
    is_live = Column(Boolean, default=False, nullable=False)
    uptime_minutes = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    channel = relationship("TwitchChannel", back_populates="stream_records")
    user = relationship("User")

    def __repr__(self):
        return f"<TwitchStreamRecord(id={self.id}, channel_id={self.channel_id}, is_live={self.is_live})>"


class TwitchChatStats(Base):
    """Twitch chat statistics."""

    __tablename__ = "twitch_chat_stats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("twitch_channels.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    timestamp = Column(DateTime, nullable=False, index=True)
    message_count = Column(Integer, default=0, nullable=False)
    messages_per_minute = Column(Integer, default=0, nullable=False)
    unique_chatters = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    channel = relationship("TwitchChannel", back_populates="chat_stats")
    user = relationship("User")

    def __repr__(self):
        return f"<TwitchChatStats(id={self.id}, channel_id={self.channel_id}, messages={self.message_count})>"
