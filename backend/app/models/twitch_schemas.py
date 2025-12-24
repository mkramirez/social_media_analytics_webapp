"""Pydantic schemas for Twitch API."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# ============================================
# Twitch Channel Schemas
# ============================================

class TwitchChannelBase(BaseModel):
    """Base Twitch channel schema."""
    username: str = Field(..., min_length=1, max_length=100)
    monitoring_interval_seconds: int = Field(default=30, ge=10, le=300)


class TwitchChannelCreate(TwitchChannelBase):
    """Schema for creating a Twitch channel."""
    pass


class TwitchChannelUpdate(BaseModel):
    """Schema for updating a Twitch channel."""
    monitoring_interval_seconds: Optional[int] = Field(None, ge=10, le=300)
    is_monitoring: Optional[bool] = None


class TwitchChannelResponse(TwitchChannelBase):
    """Schema for Twitch channel response."""
    id: UUID
    user_id: UUID
    display_name: Optional[str]
    channel_id: Optional[str]
    is_monitoring: bool
    created_at: datetime
    last_checked: Optional[datetime]
    total_records: int

    class Config:
        from_attributes = True


# ============================================
# Twitch Stream Record Schemas
# ============================================

class TwitchStreamRecordBase(BaseModel):
    """Base stream record schema."""
    timestamp: datetime
    viewer_count: int = 0
    game_name: Optional[str] = None
    stream_title: Optional[str] = None
    is_live: bool = False
    uptime_minutes: int = 0


class TwitchStreamRecordResponse(TwitchStreamRecordBase):
    """Schema for stream record response."""
    id: UUID
    channel_id: UUID
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# Twitch Chat Stats Schemas
# ============================================

class TwitchChatStatsBase(BaseModel):
    """Base chat stats schema."""
    timestamp: datetime
    message_count: int = 0
    messages_per_minute: int = 0
    unique_chatters: int = 0


class TwitchChatStatsResponse(TwitchChatStatsBase):
    """Schema for chat stats response."""
    id: UUID
    channel_id: UUID
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# Combined Schemas
# ============================================

class TwitchChannelWithRecords(TwitchChannelResponse):
    """Channel with recent stream records."""
    recent_records: List[TwitchStreamRecordResponse] = []


class TwitchChannelStats(BaseModel):
    """Channel statistics summary."""
    channel_id: UUID
    username: str
    total_records: int
    total_live_sessions: int
    average_viewers: float
    peak_viewers: int
    total_monitoring_time_minutes: int
    is_currently_live: bool
    current_viewers: Optional[int] = None
    current_game: Optional[str] = None


# ============================================
# Monitoring Control Schemas
# ============================================

class StartMonitoringRequest(BaseModel):
    """Request to start monitoring."""
    channel_ids: List[UUID] = Field(..., min_items=1)


class StopMonitoringRequest(BaseModel):
    """Request to stop monitoring."""
    channel_ids: List[UUID] = Field(..., min_items=1)


class MonitoringStatusResponse(BaseModel):
    """Monitoring status response."""
    channel_id: UUID
    username: str
    is_monitoring: bool
    job_id: Optional[str] = None
    message: str


# ============================================
# Bulk Operations
# ============================================

class BulkChannelCreate(BaseModel):
    """Schema for bulk channel creation."""
    usernames: List[str] = Field(..., min_items=1, max_items=100)
    monitoring_interval_seconds: int = Field(default=30, ge=10, le=300)


class BulkOperationResponse(BaseModel):
    """Response for bulk operations."""
    total: int
    successful: int
    failed: int
    results: List[dict]
