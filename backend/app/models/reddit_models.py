"""Reddit platform database models."""

from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class RedditSubreddit(Base):
    """Reddit subreddit being tracked."""
    __tablename__ = "reddit_subreddits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subreddit_name = Column(String(100), nullable=False)  # Subreddit name (without r/)

    # Monitoring configuration
    is_monitoring = Column(Boolean, default=False, index=True)
    monitoring_interval_seconds = Column(Integer, default=1800)  # Default 30 minutes
    post_limit = Column(Integer, default=100)  # How many recent posts to track
    comment_limit = Column(Integer, default=50)  # Comments per post

    # Statistics
    total_posts = Column(Integer, default=0)
    total_comments = Column(Integer, default=0)
    last_collected = Column(DateTime)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="reddit_subreddits")
    posts = relationship("RedditPost", back_populates="subreddit", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<RedditSubreddit(name='r/{self.subreddit_name}', monitoring={self.is_monitoring})>"


class RedditPost(Base):
    """Individual post from a subreddit."""
    __tablename__ = "reddit_posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subreddit_id = Column(UUID(as_uuid=True), ForeignKey("reddit_subreddits.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Post identification
    post_id = Column(String(50), unique=True, nullable=False, index=True)  # Reddit post ID

    # Post content
    title = Column(Text, nullable=False)
    content = Column(Text)  # Selftext for text posts
    url = Column(Text)  # URL for link posts
    author = Column(String(255))
    permalink = Column(Text)  # Reddit permalink
    created_utc = Column(DateTime, nullable=False, index=True)  # When post was created

    # Engagement metrics
    upvotes = Column(Integer, default=0)
    upvote_ratio = Column(Float, default=0.0)  # Reddit's upvote ratio (0.0-1.0)
    num_comments = Column(Integer, default=0)
    is_self = Column(Boolean, default=False)  # True for text posts, False for links

    # Collection metadata
    collected_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    subreddit = relationship("RedditSubreddit", back_populates="posts")
    user = relationship("User", back_populates="reddit_posts")
    comments = relationship("RedditComment", back_populates="post", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<RedditPost(post_id='{self.post_id}', upvotes={self.upvotes})>"


class RedditComment(Base):
    """Comment on a Reddit post."""
    __tablename__ = "reddit_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("reddit_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Comment identification
    comment_id = Column(String(50), unique=True, nullable=False, index=True)  # Reddit comment ID
    parent_id = Column(String(50))  # Parent comment/post ID

    # Comment content
    text = Column(Text, nullable=False)
    author = Column(String(255))
    created_utc = Column(DateTime, nullable=False)

    # Engagement metrics
    upvotes = Column(Integer, default=0)
    is_submitter = Column(Boolean, default=False)  # True if commenter is the post author
    depth = Column(Integer, default=0)  # Comment depth (0 = top-level)

    # Collection metadata
    collected_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    post = relationship("RedditPost", back_populates="comments")
    user = relationship("User", back_populates="reddit_comments")

    def __repr__(self):
        return f"<RedditComment(comment_id='{self.comment_id}', upvotes={self.upvotes})>"


class RedditMetrics(Base):
    """Aggregated metrics for subreddits (calculated periodically)."""
    __tablename__ = "reddit_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subreddit_id = Column(UUID(as_uuid=True), ForeignKey("reddit_subreddits.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Time period for these metrics
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    period_days = Column(Integer, default=7)  # Metrics calculated for last N days

    # Aggregated metrics
    total_posts_in_period = Column(Integer, default=0)
    total_upvotes = Column(Integer, default=0)
    total_comments = Column(Integer, default=0)

    # Averages
    avg_upvotes_per_post = Column(Integer, default=0)
    avg_comments_per_post = Column(Integer, default=0)
    avg_upvote_ratio = Column(Float, default=0.0)

    # Peak metrics
    most_upvoted_post_id = Column(String(50))
    most_commented_post_id = Column(String(50))

    # Relationships
    subreddit = relationship("RedditSubreddit")
    user = relationship("User")

    def __repr__(self):
        return f"<RedditMetrics(period={self.period_days}d, posts={self.total_posts_in_period})>"
