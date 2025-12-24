"""Pydantic schemas for Reddit API validation."""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# Reddit Subreddit Schemas
class RedditSubredditCreate(BaseModel):
    """Schema for creating a Reddit subreddit."""
    subreddit_name: str = Field(..., min_length=1, max_length=100, description="Subreddit name (without r/)")
    monitoring_interval_seconds: int = Field(default=1800, ge=600, le=86400, description="Collection interval (600-86400 seconds)")
    post_limit: int = Field(default=100, ge=1, le=500, description="Number of recent posts to track (1-500)")
    comment_limit: int = Field(default=50, ge=0, le=200, description="Comments per post (0-200)")

    @validator('subreddit_name')
    def clean_subreddit_name(cls, v):
        """Remove r/ prefix if present and validate."""
        name = v.strip().lower().replace('r/', '')
        if not name:
            raise ValueError('Subreddit name cannot be empty')
        if not name.replace('_', '').isalnum():
            raise ValueError('Subreddit name must be alphanumeric or underscore')
        return name


class RedditSubredditUpdate(BaseModel):
    """Schema for updating a Reddit subreddit."""
    monitoring_interval_seconds: Optional[int] = Field(None, ge=600, le=86400)
    post_limit: Optional[int] = Field(None, ge=1, le=500)
    comment_limit: Optional[int] = Field(None, ge=0, le=200)


class RedditSubredditResponse(BaseModel):
    """Schema for Reddit subreddit response."""
    id: UUID
    subreddit_name: str
    is_monitoring: bool
    monitoring_interval_seconds: int
    post_limit: int
    comment_limit: int
    total_posts: int
    total_comments: int
    last_collected: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Reddit Post Schemas
class RedditPostResponse(BaseModel):
    """Schema for Reddit post response."""
    id: UUID
    post_id: str
    title: str
    content: Optional[str]
    url: Optional[str]
    author: Optional[str]
    permalink: Optional[str]
    created_utc: datetime
    upvotes: int
    upvote_ratio: float
    num_comments: int
    is_self: bool
    collected_at: datetime

    class Config:
        from_attributes = True


class RedditCommentResponse(BaseModel):
    """Schema for Reddit comment response."""
    id: UUID
    comment_id: str
    parent_id: Optional[str]
    text: str
    author: Optional[str]
    created_utc: datetime
    upvotes: int
    is_submitter: bool
    depth: int
    collected_at: datetime

    class Config:
        from_attributes = True


class RedditSubredditWithPosts(RedditSubredditResponse):
    """Schema for Reddit subreddit with posts."""
    posts: List[RedditPostResponse] = []

    class Config:
        from_attributes = True


# Reddit Statistics Schemas
class RedditSubredditStats(BaseModel):
    """Schema for Reddit subreddit statistics."""
    total_posts: int
    total_upvotes: int
    total_comments: int
    avg_upvotes_per_post: float
    avg_comments_per_post: float
    avg_upvote_ratio: float
    most_upvoted_post_id: Optional[str]
    most_upvoted_post_title: Optional[str]
    most_upvoted_post_upvotes: Optional[int]
    most_commented_post_id: Optional[str]
    most_commented_post_title: Optional[str]
    most_commented_post_comments: Optional[int]
    recent_posts: List[RedditPostResponse] = []


# Monitoring Control Schemas
class MonitoringStatus(BaseModel):
    """Schema for monitoring status response."""
    message: str
    is_monitoring: bool
    subreddit_name: str


class BulkRedditSubredditCreate(BaseModel):
    """Schema for bulk creating Reddit subreddits."""
    subreddit_names: List[str] = Field(..., min_items=1, max_items=30, description="List of subreddit names (max 30)")
    monitoring_interval_seconds: int = Field(default=1800, ge=600, le=86400)
    post_limit: int = Field(default=100, ge=1, le=500)
    comment_limit: int = Field(default=50, ge=0, le=200)

    @validator('subreddit_names')
    def clean_subreddit_names(cls, v):
        """Clean and validate subreddit names."""
        cleaned = []
        for name in v:
            clean = name.strip().lower().replace('r/', '')
            if clean and clean.replace('_', '').isalnum():
                cleaned.append(clean)
        if not cleaned:
            raise ValueError('No valid subreddit names provided')
        return list(set(cleaned))  # Remove duplicates


class BulkCreateResult(BaseModel):
    """Schema for bulk create results."""
    created_count: int
    failed_count: int
    created_subreddits: List[RedditSubredditResponse] = []
    failed_subreddits: List[str] = []
    errors: List[str] = []
