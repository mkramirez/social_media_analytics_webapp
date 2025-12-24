"""Pydantic schemas for Twitter API validation."""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# Twitter User Schemas
class TwitterUserCreate(BaseModel):
    """Schema for creating a Twitter user."""
    username: str = Field(..., min_length=1, max_length=100, description="Twitter username (without @)")
    display_name: Optional[str] = Field(None, max_length=255, description="Display name")
    monitoring_interval_seconds: int = Field(default=300, ge=60, le=3600, description="Collection interval (60-3600 seconds)")
    days_to_collect: int = Field(default=7, ge=1, le=30, description="Days of tweets to collect (1-30)")

    @validator('username')
    def clean_username(cls, v):
        """Remove @ symbol if present and validate."""
        username = v.strip().replace('@', '')
        if not username:
            raise ValueError('Username cannot be empty')
        if not username.replace('_', '').isalnum():
            raise ValueError('Username must be alphanumeric or underscore')
        return username.lower()


class TwitterUserUpdate(BaseModel):
    """Schema for updating a Twitter user."""
    display_name: Optional[str] = Field(None, max_length=255)
    monitoring_interval_seconds: Optional[int] = Field(None, ge=60, le=3600)
    days_to_collect: Optional[int] = Field(None, ge=1, le=30)


class TwitterUserResponse(BaseModel):
    """Schema for Twitter user response."""
    id: UUID
    username: str
    display_name: Optional[str]
    is_monitoring: bool
    monitoring_interval_seconds: int
    days_to_collect: int
    total_tweets: int
    last_collected: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Tweet Schemas
class TweetResponse(BaseModel):
    """Schema for tweet response."""
    id: UUID
    tweet_id: str
    text: str
    created_at: datetime
    reply_count: int
    retweet_count: int
    like_count: int
    quote_count: int
    impression_count: int
    collected_at: datetime

    class Config:
        from_attributes = True


class TwitterUserWithTweets(TwitterUserResponse):
    """Schema for Twitter user with tweets."""
    tweets: List[TweetResponse] = []

    class Config:
        from_attributes = True


# Twitter Metrics Schemas
class TwitterMetricsResponse(BaseModel):
    """Schema for Twitter metrics response."""
    id: UUID
    calculated_at: datetime
    period_days: int
    total_tweets_in_period: int
    total_likes: int
    total_retweets: int
    total_replies: int
    total_impressions: int
    avg_likes_per_tweet: int
    avg_retweets_per_tweet: int
    avg_engagement_rate: int
    most_liked_tweet_id: Optional[str]
    most_retweeted_tweet_id: Optional[str]

    class Config:
        from_attributes = True


# Statistics Schema
class TwitterUserStats(BaseModel):
    """Schema for Twitter user statistics."""
    total_tweets: int
    total_likes: int
    total_retweets: int
    total_replies: int
    total_impressions: int
    avg_likes_per_tweet: float
    avg_retweets_per_tweet: float
    avg_engagement_rate: float
    most_liked_tweet_id: Optional[str]
    most_liked_tweet_likes: Optional[int]
    most_retweeted_tweet_id: Optional[str]
    most_retweeted_tweet_retweets: Optional[int]
    recent_tweets: List[TweetResponse] = []


# Monitoring Control Schemas
class MonitoringStatus(BaseModel):
    """Schema for monitoring status response."""
    message: str
    is_monitoring: bool
    username: str


class BulkTwitterUserCreate(BaseModel):
    """Schema for bulk creating Twitter users."""
    usernames: List[str] = Field(..., min_items=1, max_items=50, description="List of usernames (max 50)")
    monitoring_interval_seconds: int = Field(default=300, ge=60, le=3600)
    days_to_collect: int = Field(default=7, ge=1, le=30)

    @validator('usernames')
    def clean_usernames(cls, v):
        """Clean and validate usernames."""
        cleaned = []
        for username in v:
            clean = username.strip().replace('@', '').lower()
            if clean and clean.replace('_', '').isalnum():
                cleaned.append(clean)
        if not cleaned:
            raise ValueError('No valid usernames provided')
        return list(set(cleaned))  # Remove duplicates


class BulkCreateResult(BaseModel):
    """Schema for bulk create results."""
    created_count: int
    failed_count: int
    created_users: List[TwitterUserResponse] = []
    failed_usernames: List[str] = []
    errors: List[str] = []
