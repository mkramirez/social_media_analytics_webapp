"""Reddit API router for subreddit monitoring and post collection."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User
from app.models.reddit_models import RedditSubreddit, RedditPost, RedditComment
from app.models.reddit_schemas import (
    RedditSubredditCreate,
    RedditSubredditUpdate,
    RedditSubredditResponse,
    RedditSubredditWithPosts,
    RedditPostResponse,
    RedditCommentResponse,
    RedditSubredditStats,
    MonitoringStatus,
    BulkRedditSubredditCreate,
    BulkCreateResult
)
from app.middleware.auth import get_current_user
from app.services.scheduler_service import (
    add_reddit_monitoring_job,
    remove_reddit_monitoring_job
)

router = APIRouter()


# ============================================
# Reddit Subreddit CRUD Operations
# ============================================

@router.post("/subreddits", response_model=RedditSubredditResponse, status_code=201)
def create_reddit_subreddit(
    subreddit_data: RedditSubredditCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new Reddit subreddit to monitor.

    - **subreddit_name**: Subreddit name (without r/)
    - **monitoring_interval_seconds**: Collection interval (600-86400 seconds)
    - **post_limit**: Number of recent posts to track (1-500)
    - **comment_limit**: Comments per post (0-200)
    """
    # Check if subreddit already exists for this user
    existing = db.query(RedditSubreddit).filter(
        RedditSubreddit.user_id == current_user.id,
        RedditSubreddit.subreddit_name == subreddit_data.subreddit_name
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail=f"Subreddit r/{subreddit_data.subreddit_name} already exists")

    # Create new subreddit
    subreddit = RedditSubreddit(
        user_id=current_user.id,
        subreddit_name=subreddit_data.subreddit_name,
        monitoring_interval_seconds=subreddit_data.monitoring_interval_seconds,
        post_limit=subreddit_data.post_limit,
        comment_limit=subreddit_data.comment_limit,
        is_monitoring=False
    )

    db.add(subreddit)
    db.commit()
    db.refresh(subreddit)

    return subreddit


@router.post("/subreddits/bulk", response_model=BulkCreateResult)
def create_reddit_subreddits_bulk(
    bulk_data: BulkRedditSubredditCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create multiple Reddit subreddits at once.

    - **subreddit_names**: List of subreddit names (max 30)
    - **monitoring_interval_seconds**: Collection interval for all
    - **post_limit**: Number of posts to track for all
    - **comment_limit**: Comments per post for all
    """
    created_subreddits = []
    failed_subreddits = []
    errors = []

    for subreddit_name in bulk_data.subreddit_names:
        try:
            # Check if already exists
            existing = db.query(RedditSubreddit).filter(
                RedditSubreddit.user_id == current_user.id,
                RedditSubreddit.subreddit_name == subreddit_name
            ).first()

            if existing:
                failed_subreddits.append(subreddit_name)
                errors.append(f"r/{subreddit_name} already exists")
                continue

            # Create new subreddit
            subreddit = RedditSubreddit(
                user_id=current_user.id,
                subreddit_name=subreddit_name,
                monitoring_interval_seconds=bulk_data.monitoring_interval_seconds,
                post_limit=bulk_data.post_limit,
                comment_limit=bulk_data.comment_limit,
                is_monitoring=False
            )

            db.add(subreddit)
            db.flush()  # Get ID without committing
            created_subreddits.append(subreddit)

        except Exception as e:
            failed_subreddits.append(subreddit_name)
            errors.append(f"r/{subreddit_name}: {str(e)}")

    db.commit()

    # Refresh all created subreddits
    for subreddit in created_subreddits:
        db.refresh(subreddit)

    return BulkCreateResult(
        created_count=len(created_subreddits),
        failed_count=len(failed_subreddits),
        created_subreddits=created_subreddits,
        failed_subreddits=failed_subreddits,
        errors=errors
    )


@router.get("/subreddits", response_model=List[RedditSubredditResponse])
def list_reddit_subreddits(
    monitoring_only: bool = Query(False, description="Only return subreddits being monitored"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all Reddit subreddits for the authenticated user.

    - **monitoring_only**: Filter to only show subreddits being monitored
    """
    query = db.query(RedditSubreddit).filter(RedditSubreddit.user_id == current_user.id)

    if monitoring_only:
        query = query.filter(RedditSubreddit.is_monitoring == True)

    subreddits = query.order_by(RedditSubreddit.subreddit_name).all()

    return subreddits


@router.get("/subreddits/{subreddit_id}", response_model=RedditSubredditWithPosts)
def get_reddit_subreddit(
    subreddit_id: UUID,
    limit: int = Query(25, ge=1, le=100, description="Max posts to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific Reddit subreddit with recent posts.

    - **subreddit_id**: Reddit subreddit UUID
    - **limit**: Maximum number of posts to return (1-100)
    """
    subreddit = db.query(RedditSubreddit).filter(
        RedditSubreddit.id == subreddit_id,
        RedditSubreddit.user_id == current_user.id
    ).first()

    if not subreddit:
        raise HTTPException(status_code=404, detail="Reddit subreddit not found")

    # Get recent posts
    posts = db.query(RedditPost).filter(
        RedditPost.subreddit_id == subreddit_id
    ).order_by(desc(RedditPost.created_utc)).limit(limit).all()

    # Manually construct response
    response = RedditSubredditWithPosts(
        id=subreddit.id,
        subreddit_name=subreddit.subreddit_name,
        is_monitoring=subreddit.is_monitoring,
        monitoring_interval_seconds=subreddit.monitoring_interval_seconds,
        post_limit=subreddit.post_limit,
        comment_limit=subreddit.comment_limit,
        total_posts=subreddit.total_posts,
        total_comments=subreddit.total_comments,
        last_collected=subreddit.last_collected,
        created_at=subreddit.created_at,
        updated_at=subreddit.updated_at,
        posts=posts
    )

    return response


@router.put("/subreddits/{subreddit_id}", response_model=RedditSubredditResponse)
def update_reddit_subreddit(
    subreddit_id: UUID,
    update_data: RedditSubredditUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a Reddit subreddit's settings.

    - **monitoring_interval_seconds**: Update collection interval
    - **post_limit**: Update post limit
    - **comment_limit**: Update comment limit
    """
    subreddit = db.query(RedditSubreddit).filter(
        RedditSubreddit.id == subreddit_id,
        RedditSubreddit.user_id == current_user.id
    ).first()

    if not subreddit:
        raise HTTPException(status_code=404, detail="Reddit subreddit not found")

    # Update fields
    if update_data.monitoring_interval_seconds is not None:
        subreddit.monitoring_interval_seconds = update_data.monitoring_interval_seconds

        # Update job if monitoring
        if subreddit.is_monitoring:
            add_reddit_monitoring_job(
                subreddit.id,
                current_user.id,
                update_data.monitoring_interval_seconds
            )

    if update_data.post_limit is not None:
        subreddit.post_limit = update_data.post_limit

    if update_data.comment_limit is not None:
        subreddit.comment_limit = update_data.comment_limit

    subreddit.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(subreddit)

    return subreddit


@router.delete("/subreddits/{subreddit_id}")
def delete_reddit_subreddit(
    subreddit_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a Reddit subreddit and all associated posts and comments.

    - **subreddit_id**: Reddit subreddit UUID
    """
    subreddit = db.query(RedditSubreddit).filter(
        RedditSubreddit.id == subreddit_id,
        RedditSubreddit.user_id == current_user.id
    ).first()

    if not subreddit:
        raise HTTPException(status_code=404, detail="Reddit subreddit not found")

    # Stop monitoring if active
    if subreddit.is_monitoring:
        remove_reddit_monitoring_job(subreddit_id)

    db.delete(subreddit)
    db.commit()

    return {"message": f"Subreddit r/{subreddit.subreddit_name} deleted successfully"}


# ============================================
# Monitoring Control
# ============================================

@router.post("/subreddits/{subreddit_id}/start-monitoring", response_model=MonitoringStatus)
def start_monitoring(
    subreddit_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start monitoring a Reddit subreddit.

    Begins background collection of posts at the configured interval.
    """
    subreddit = db.query(RedditSubreddit).filter(
        RedditSubreddit.id == subreddit_id,
        RedditSubreddit.user_id == current_user.id
    ).first()

    if not subreddit:
        raise HTTPException(status_code=404, detail="Reddit subreddit not found")

    if subreddit.is_monitoring:
        return MonitoringStatus(
            message=f"Already monitoring r/{subreddit.subreddit_name}",
            is_monitoring=True,
            subreddit_name=subreddit.subreddit_name
        )

    # Start monitoring job
    try:
        add_reddit_monitoring_job(
            subreddit.id,
            current_user.id,
            subreddit.monitoring_interval_seconds
        )

        subreddit.is_monitoring = True
        db.commit()

        return MonitoringStatus(
            message=f"Started monitoring r/{subreddit.subreddit_name}",
            is_monitoring=True,
            subreddit_name=subreddit.subreddit_name
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start monitoring: {str(e)}")


@router.post("/subreddits/{subreddit_id}/stop-monitoring", response_model=MonitoringStatus)
def stop_monitoring(
    subreddit_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Stop monitoring a Reddit subreddit.

    Stops the background collection job.
    """
    subreddit = db.query(RedditSubreddit).filter(
        RedditSubreddit.id == subreddit_id,
        RedditSubreddit.user_id == current_user.id
    ).first()

    if not subreddit:
        raise HTTPException(status_code=404, detail="Reddit subreddit not found")

    if not subreddit.is_monitoring:
        return MonitoringStatus(
            message=f"r/{subreddit.subreddit_name} is not being monitored",
            is_monitoring=False,
            subreddit_name=subreddit.subreddit_name
        )

    # Stop monitoring job
    remove_reddit_monitoring_job(subreddit.id)

    subreddit.is_monitoring = False
    db.commit()

    return MonitoringStatus(
        message=f"Stopped monitoring r/{subreddit.subreddit_name}",
        is_monitoring=False,
        subreddit_name=subreddit.subreddit_name
    )


@router.post("/subreddits/start-all")
def start_all_monitoring(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start monitoring all Reddit subreddits.

    Starts background collection for all subreddits owned by the authenticated user.
    """
    subreddits = db.query(RedditSubreddit).filter(
        RedditSubreddit.user_id == current_user.id,
        RedditSubreddit.is_monitoring == False
    ).all()

    started_count = 0
    for subreddit in subreddits:
        try:
            add_reddit_monitoring_job(
                subreddit.id,
                current_user.id,
                subreddit.monitoring_interval_seconds
            )
            subreddit.is_monitoring = True
            started_count += 1
        except Exception as e:
            print(f"Failed to start monitoring for r/{subreddit.subreddit_name}: {e}")

    db.commit()

    return {
        "message": f"Started monitoring {started_count} subreddit(s)",
        "started_count": started_count
    }


@router.post("/subreddits/stop-all")
def stop_all_monitoring(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Stop monitoring all Reddit subreddits.

    Stops all background collection jobs for the authenticated user.
    """
    subreddits = db.query(RedditSubreddit).filter(
        RedditSubreddit.user_id == current_user.id,
        RedditSubreddit.is_monitoring == True
    ).all()

    stopped_count = 0
    for subreddit in subreddits:
        remove_reddit_monitoring_job(subreddit.id)
        subreddit.is_monitoring = False
        stopped_count += 1

    db.commit()

    return {
        "message": f"Stopped monitoring {stopped_count} subreddit(s)",
        "stopped_count": stopped_count
    }


# ============================================
# Post and Comment Retrieval
# ============================================

@router.get("/subreddits/{subreddit_id}/posts", response_model=List[RedditPostResponse])
def get_posts(
    subreddit_id: UUID,
    skip: int = Query(0, ge=0, description="Number of posts to skip"),
    limit: int = Query(25, ge=1, le=100, description="Max posts to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get posts for a specific subreddit with pagination.

    - **subreddit_id**: Reddit subreddit UUID
    - **skip**: Number of posts to skip (for pagination)
    - **limit**: Maximum posts to return (1-100)
    """
    # Verify ownership
    subreddit = db.query(RedditSubreddit).filter(
        RedditSubreddit.id == subreddit_id,
        RedditSubreddit.user_id == current_user.id
    ).first()

    if not subreddit:
        raise HTTPException(status_code=404, detail="Reddit subreddit not found")

    # Get posts with pagination
    posts = db.query(RedditPost).filter(
        RedditPost.subreddit_id == subreddit_id
    ).order_by(desc(RedditPost.created_utc)).offset(skip).limit(limit).all()

    return posts


@router.get("/posts/{post_id}/comments", response_model=List[RedditCommentResponse])
def get_post_comments(
    post_id: UUID,
    skip: int = Query(0, ge=0, description="Number of comments to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max comments to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get comments for a specific post with pagination.

    - **post_id**: Reddit post UUID
    - **skip**: Number of comments to skip (for pagination)
    - **limit**: Maximum comments to return (1-100)
    """
    # Verify ownership
    post = db.query(RedditPost).filter(
        RedditPost.id == post_id,
        RedditPost.user_id == current_user.id
    ).first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Get comments with pagination
    comments = db.query(RedditComment).filter(
        RedditComment.post_id == post_id
    ).order_by(desc(RedditComment.upvotes)).offset(skip).limit(limit).all()

    return comments


# ============================================
# Statistics
# ============================================

@router.get("/subreddits/{subreddit_id}/stats", response_model=RedditSubredditStats)
def get_reddit_subreddit_stats(
    subreddit_id: UUID,
    days: int = Query(7, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get statistics for a Reddit subreddit.

    - **subreddit_id**: Reddit subreddit UUID
    - **days**: Number of days to analyze (1-365)

    Returns engagement metrics, averages, and top posts.
    """
    # Verify ownership
    subreddit = db.query(RedditSubreddit).filter(
        RedditSubreddit.id == subreddit_id,
        RedditSubreddit.user_id == current_user.id
    ).first()

    if not subreddit:
        raise HTTPException(status_code=404, detail="Reddit subreddit not found")

    # Calculate date threshold
    since_date = datetime.utcnow() - timedelta(days=days)

    # Get aggregate statistics
    stats = db.query(
        func.count(RedditPost.id).label('total_posts'),
        func.sum(RedditPost.upvotes).label('total_upvotes'),
        func.sum(RedditPost.num_comments).label('total_comments'),
        func.avg(RedditPost.upvote_ratio).label('avg_upvote_ratio')
    ).filter(
        RedditPost.subreddit_id == subreddit_id,
        RedditPost.created_utc >= since_date
    ).first()

    total_posts = stats.total_posts or 0
    total_upvotes = stats.total_upvotes or 0
    total_comments = stats.total_comments or 0
    avg_upvote_ratio = stats.avg_upvote_ratio or 0.0

    # Calculate averages
    avg_upvotes = total_upvotes / total_posts if total_posts > 0 else 0
    avg_comments = total_comments / total_posts if total_posts > 0 else 0

    # Get most upvoted post
    most_upvoted = db.query(RedditPost).filter(
        RedditPost.subreddit_id == subreddit_id,
        RedditPost.created_utc >= since_date
    ).order_by(desc(RedditPost.upvotes)).first()

    # Get most commented post
    most_commented = db.query(RedditPost).filter(
        RedditPost.subreddit_id == subreddit_id,
        RedditPost.created_utc >= since_date
    ).order_by(desc(RedditPost.num_comments)).first()

    # Get recent posts
    recent_posts = db.query(RedditPost).filter(
        RedditPost.subreddit_id == subreddit_id
    ).order_by(desc(RedditPost.created_utc)).limit(10).all()

    return RedditSubredditStats(
        total_posts=total_posts,
        total_upvotes=int(total_upvotes),
        total_comments=int(total_comments),
        avg_upvotes_per_post=round(avg_upvotes, 2),
        avg_comments_per_post=round(avg_comments, 2),
        avg_upvote_ratio=round(avg_upvote_ratio, 2),
        most_upvoted_post_id=most_upvoted.post_id if most_upvoted else None,
        most_upvoted_post_title=most_upvoted.title if most_upvoted else None,
        most_upvoted_post_upvotes=most_upvoted.upvotes if most_upvoted else None,
        most_commented_post_id=most_commented.post_id if most_commented else None,
        most_commented_post_title=most_commented.title if most_commented else None,
        most_commented_post_comments=most_commented.num_comments if most_commented else None,
        recent_posts=recent_posts
    )
