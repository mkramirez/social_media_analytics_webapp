"""Pydantic schemas for YouTube API validation."""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# YouTube Channel Schemas
class YouTubeChannelCreate(BaseModel):
    """Schema for creating a YouTube channel."""
    channel_name: str = Field(..., min_length=1, max_length=255, description="Channel name or handle")
    channel_id: Optional[str] = Field(None, max_length=100, description="YouTube channel ID (UC...)")
    display_name: Optional[str] = Field(None, max_length=255, description="Display name")
    monitoring_interval_seconds: int = Field(default=3600, ge=300, le=86400, description="Collection interval (300-86400 seconds)")
    video_limit: int = Field(default=50, ge=1, le=200, description="Number of recent videos to track (1-200)")

    @validator('channel_name')
    def clean_channel_name(cls, v):
        """Clean and validate channel name."""
        name = v.strip()
        if not name:
            raise ValueError('Channel name cannot be empty')
        return name


class YouTubeChannelUpdate(BaseModel):
    """Schema for updating a YouTube channel."""
    display_name: Optional[str] = Field(None, max_length=255)
    monitoring_interval_seconds: Optional[int] = Field(None, ge=300, le=86400)
    video_limit: Optional[int] = Field(None, ge=1, le=200)


class YouTubeChannelResponse(BaseModel):
    """Schema for YouTube channel response."""
    id: UUID
    channel_name: str
    channel_id: Optional[str]
    display_name: Optional[str]
    is_monitoring: bool
    monitoring_interval_seconds: int
    video_limit: int
    total_videos: int
    total_comments: int
    last_collected: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# YouTube Video Schemas
class YouTubeVideoResponse(BaseModel):
    """Schema for YouTube video response."""
    id: UUID
    video_id: str
    title: str
    description: Optional[str]
    published_at: datetime
    view_count: int
    like_count: int
    comment_count: int
    collected_at: datetime

    class Config:
        from_attributes = True


class YouTubeCommentResponse(BaseModel):
    """Schema for YouTube comment response."""
    id: UUID
    comment_id: str
    text: str
    author: Optional[str]
    like_count: int
    reply_count: int
    published_at: datetime
    collected_at: datetime

    class Config:
        from_attributes = True


class YouTubeChannelWithVideos(YouTubeChannelResponse):
    """Schema for YouTube channel with videos."""
    videos: List[YouTubeVideoResponse] = []

    class Config:
        from_attributes = True


class YouTubeVideoWithComments(YouTubeVideoResponse):
    """Schema for YouTube video with comments."""
    comments: List[YouTubeCommentResponse] = []

    class Config:
        from_attributes = True


# YouTube Statistics Schemas
class YouTubeChannelStats(BaseModel):
    """Schema for YouTube channel statistics."""
    total_videos: int
    total_views: int
    total_likes: int
    total_comments: int
    avg_views_per_video: float
    avg_likes_per_video: float
    avg_comments_per_video: float
    avg_engagement_rate: float
    most_viewed_video_id: Optional[str]
    most_viewed_video_title: Optional[str]
    most_viewed_video_views: Optional[int]
    most_liked_video_id: Optional[str]
    most_liked_video_title: Optional[str]
    most_liked_video_likes: Optional[int]
    recent_videos: List[YouTubeVideoResponse] = []


# Monitoring Control Schemas
class MonitoringStatus(BaseModel):
    """Schema for monitoring status response."""
    message: str
    is_monitoring: bool
    channel_name: str


class BulkYouTubeChannelCreate(BaseModel):
    """Schema for bulk creating YouTube channels."""
    channel_names: List[str] = Field(..., min_items=1, max_items=20, description="List of channel names (max 20)")
    monitoring_interval_seconds: int = Field(default=3600, ge=300, le=86400)
    video_limit: int = Field(default=50, ge=1, le=200)

    @validator('channel_names')
    def clean_channel_names(cls, v):
        """Clean and validate channel names."""
        cleaned = []
        for name in v:
            clean = name.strip()
            if clean:
                cleaned.append(clean)
        if not cleaned:
            raise ValueError('No valid channel names provided')
        return list(set(cleaned))  # Remove duplicates


class BulkCreateResult(BaseModel):
    """Schema for bulk create results."""
    created_count: int
    failed_count: int
    created_channels: List[YouTubeChannelResponse] = []
    failed_channels: List[str] = []
    errors: List[str] = []
