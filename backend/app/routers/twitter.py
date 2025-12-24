"""Twitter API router for user monitoring and tweet collection."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User
from app.models.twitter_models import TwitterUser, Tweet, TwitterMetrics
from app.models.twitter_schemas import (
    TwitterUserCreate,
    TwitterUserUpdate,
    TwitterUserResponse,
    TwitterUserWithTweets,
    TweetResponse,
    TwitterUserStats,
    MonitoringStatus,
    BulkTwitterUserCreate,
    BulkCreateResult
)
from app.middleware.auth import get_current_user
from app.services.scheduler_service import (
    add_twitter_monitoring_job,
    remove_twitter_monitoring_job
)

router = APIRouter()


# ============================================
# Twitter User CRUD Operations
# ============================================

@router.post("/users", response_model=TwitterUserResponse, status_code=201)
def create_twitter_user(
    user_data: TwitterUserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new Twitter user to monitor.

    - **username**: Twitter username (without @)
    - **display_name**: Optional display name
    - **monitoring_interval_seconds**: Collection interval (60-3600 seconds)
    - **days_to_collect**: How many days of tweets to collect (1-30)
    """
    # Check if user already exists for this user
    existing = db.query(TwitterUser).filter(
        TwitterUser.user_id == current_user.id,
        TwitterUser.username == user_data.username
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail=f"Twitter user @{user_data.username} already exists")

    # Create new Twitter user
    twitter_user = TwitterUser(
        user_id=current_user.id,
        username=user_data.username,
        display_name=user_data.display_name or user_data.username,
        monitoring_interval_seconds=user_data.monitoring_interval_seconds,
        days_to_collect=user_data.days_to_collect,
        is_monitoring=False
    )

    db.add(twitter_user)
    db.commit()
    db.refresh(twitter_user)

    return twitter_user


@router.post("/users/bulk", response_model=BulkCreateResult)
def create_twitter_users_bulk(
    bulk_data: BulkTwitterUserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create multiple Twitter users at once.

    - **usernames**: List of Twitter usernames (max 50)
    - **monitoring_interval_seconds**: Collection interval for all
    - **days_to_collect**: Days of tweets to collect for all
    """
    created_users = []
    failed_usernames = []
    errors = []

    for username in bulk_data.usernames:
        try:
            # Check if already exists
            existing = db.query(TwitterUser).filter(
                TwitterUser.user_id == current_user.id,
                TwitterUser.username == username
            ).first()

            if existing:
                failed_usernames.append(username)
                errors.append(f"@{username} already exists")
                continue

            # Create new user
            twitter_user = TwitterUser(
                user_id=current_user.id,
                username=username,
                display_name=username,
                monitoring_interval_seconds=bulk_data.monitoring_interval_seconds,
                days_to_collect=bulk_data.days_to_collect,
                is_monitoring=False
            )

            db.add(twitter_user)
            db.flush()  # Get ID without committing
            created_users.append(twitter_user)

        except Exception as e:
            failed_usernames.append(username)
            errors.append(f"@{username}: {str(e)}")

    db.commit()

    # Refresh all created users
    for user in created_users:
        db.refresh(user)

    return BulkCreateResult(
        created_count=len(created_users),
        failed_count=len(failed_usernames),
        created_users=created_users,
        failed_usernames=failed_usernames,
        errors=errors
    )


@router.get("/users", response_model=List[TwitterUserResponse])
def list_twitter_users(
    monitoring_only: bool = Query(False, description="Only return users being monitored"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all Twitter users for the authenticated user.

    - **monitoring_only**: Filter to only show users being monitored
    """
    query = db.query(TwitterUser).filter(TwitterUser.user_id == current_user.id)

    if monitoring_only:
        query = query.filter(TwitterUser.is_monitoring == True)

    users = query.order_by(TwitterUser.username).all()

    return users


@router.get("/users/{twitter_user_id}", response_model=TwitterUserWithTweets)
def get_twitter_user(
    twitter_user_id: UUID,
    limit: int = Query(50, ge=1, le=1000, description="Max tweets to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific Twitter user with recent tweets.

    - **twitter_user_id**: Twitter user UUID
    - **limit**: Maximum number of tweets to return (1-1000)
    """
    twitter_user = db.query(TwitterUser).filter(
        TwitterUser.id == twitter_user_id,
        TwitterUser.user_id == current_user.id
    ).first()

    if not twitter_user:
        raise HTTPException(status_code=404, detail="Twitter user not found")

    # Get recent tweets
    tweets = db.query(Tweet).filter(
        Tweet.twitter_user_id == twitter_user_id
    ).order_by(desc(Tweet.created_at)).limit(limit).all()

    # Manually construct response
    response = TwitterUserWithTweets(
        id=twitter_user.id,
        username=twitter_user.username,
        display_name=twitter_user.display_name,
        is_monitoring=twitter_user.is_monitoring,
        monitoring_interval_seconds=twitter_user.monitoring_interval_seconds,
        days_to_collect=twitter_user.days_to_collect,
        total_tweets=twitter_user.total_tweets,
        last_collected=twitter_user.last_collected,
        created_at=twitter_user.created_at,
        updated_at=twitter_user.updated_at,
        tweets=tweets
    )

    return response


@router.put("/users/{twitter_user_id}", response_model=TwitterUserResponse)
def update_twitter_user(
    twitter_user_id: UUID,
    update_data: TwitterUserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a Twitter user's settings.

    - **display_name**: Update display name
    - **monitoring_interval_seconds**: Update collection interval
    - **days_to_collect**: Update days to collect
    """
    twitter_user = db.query(TwitterUser).filter(
        TwitterUser.id == twitter_user_id,
        TwitterUser.user_id == current_user.id
    ).first()

    if not twitter_user:
        raise HTTPException(status_code=404, detail="Twitter user not found")

    # Update fields
    if update_data.display_name is not None:
        twitter_user.display_name = update_data.display_name

    if update_data.monitoring_interval_seconds is not None:
        twitter_user.monitoring_interval_seconds = update_data.monitoring_interval_seconds

        # Update job if monitoring
        if twitter_user.is_monitoring:
            add_twitter_monitoring_job(
                twitter_user.id,
                current_user.id,
                update_data.monitoring_interval_seconds
            )

    if update_data.days_to_collect is not None:
        twitter_user.days_to_collect = update_data.days_to_collect

    twitter_user.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(twitter_user)

    return twitter_user


@router.delete("/users/{twitter_user_id}")
def delete_twitter_user(
    twitter_user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a Twitter user and all associated tweets.

    - **twitter_user_id**: Twitter user UUID
    """
    twitter_user = db.query(TwitterUser).filter(
        TwitterUser.id == twitter_user_id,
        TwitterUser.user_id == current_user.id
    ).first()

    if not twitter_user:
        raise HTTPException(status_code=404, detail="Twitter user not found")

    # Stop monitoring if active
    if twitter_user.is_monitoring:
        remove_twitter_monitoring_job(twitter_user_id)

    db.delete(twitter_user)
    db.commit()

    return {"message": f"Twitter user @{twitter_user.username} deleted successfully"}


# ============================================
# Monitoring Control
# ============================================

@router.post("/users/{twitter_user_id}/start-monitoring", response_model=MonitoringStatus)
def start_monitoring(
    twitter_user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start monitoring a Twitter user.

    Begins background collection of tweets at the configured interval.
    """
    twitter_user = db.query(TwitterUser).filter(
        TwitterUser.id == twitter_user_id,
        TwitterUser.user_id == current_user.id
    ).first()

    if not twitter_user:
        raise HTTPException(status_code=404, detail="Twitter user not found")

    if twitter_user.is_monitoring:
        return MonitoringStatus(
            message=f"Already monitoring @{twitter_user.username}",
            is_monitoring=True,
            username=twitter_user.username
        )

    # Start monitoring job
    try:
        add_twitter_monitoring_job(
            twitter_user.id,
            current_user.id,
            twitter_user.monitoring_interval_seconds
        )

        twitter_user.is_monitoring = True
        db.commit()

        return MonitoringStatus(
            message=f"Started monitoring @{twitter_user.username}",
            is_monitoring=True,
            username=twitter_user.username
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start monitoring: {str(e)}")


@router.post("/users/{twitter_user_id}/stop-monitoring", response_model=MonitoringStatus)
def stop_monitoring(
    twitter_user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Stop monitoring a Twitter user.

    Stops the background collection job.
    """
    twitter_user = db.query(TwitterUser).filter(
        TwitterUser.id == twitter_user_id,
        TwitterUser.user_id == current_user.id
    ).first()

    if not twitter_user:
        raise HTTPException(status_code=404, detail="Twitter user not found")

    if not twitter_user.is_monitoring:
        return MonitoringStatus(
            message=f"@{twitter_user.username} is not being monitored",
            is_monitoring=False,
            username=twitter_user.username
        )

    # Stop monitoring job
    remove_twitter_monitoring_job(twitter_user.id)

    twitter_user.is_monitoring = False
    db.commit()

    return MonitoringStatus(
        message=f"Stopped monitoring @{twitter_user.username}",
        is_monitoring=False,
        username=twitter_user.username
    )


@router.post("/users/start-all")
def start_all_monitoring(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start monitoring all Twitter users.

    Starts background collection for all users owned by the authenticated user.
    """
    users = db.query(TwitterUser).filter(
        TwitterUser.user_id == current_user.id,
        TwitterUser.is_monitoring == False
    ).all()

    started_count = 0
    for user in users:
        try:
            add_twitter_monitoring_job(
                user.id,
                current_user.id,
                user.monitoring_interval_seconds
            )
            user.is_monitoring = True
            started_count += 1
        except Exception as e:
            print(f"Failed to start monitoring for @{user.username}: {e}")

    db.commit()

    return {
        "message": f"Started monitoring {started_count} Twitter user(s)",
        "started_count": started_count
    }


@router.post("/users/stop-all")
def stop_all_monitoring(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Stop monitoring all Twitter users.

    Stops all background collection jobs for the authenticated user.
    """
    users = db.query(TwitterUser).filter(
        TwitterUser.user_id == current_user.id,
        TwitterUser.is_monitoring == True
    ).all()

    stopped_count = 0
    for user in users:
        remove_twitter_monitoring_job(user.id)
        user.is_monitoring = False
        stopped_count += 1

    db.commit()

    return {
        "message": f"Stopped monitoring {stopped_count} Twitter user(s)",
        "stopped_count": stopped_count
    }


# ============================================
# Tweet Retrieval
# ============================================

@router.get("/users/{twitter_user_id}/tweets", response_model=List[TweetResponse])
def get_tweets(
    twitter_user_id: UUID,
    skip: int = Query(0, ge=0, description="Number of tweets to skip"),
    limit: int = Query(50, ge=1, le=1000, description="Max tweets to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get tweets for a specific Twitter user with pagination.

    - **twitter_user_id**: Twitter user UUID
    - **skip**: Number of tweets to skip (for pagination)
    - **limit**: Maximum tweets to return (1-1000)
    """
    # Verify ownership
    twitter_user = db.query(TwitterUser).filter(
        TwitterUser.id == twitter_user_id,
        TwitterUser.user_id == current_user.id
    ).first()

    if not twitter_user:
        raise HTTPException(status_code=404, detail="Twitter user not found")

    # Get tweets with pagination
    tweets = db.query(Tweet).filter(
        Tweet.twitter_user_id == twitter_user_id
    ).order_by(desc(Tweet.created_at)).offset(skip).limit(limit).all()

    return tweets


# ============================================
# Statistics
# ============================================

@router.get("/users/{twitter_user_id}/stats", response_model=TwitterUserStats)
def get_twitter_user_stats(
    twitter_user_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get statistics for a Twitter user.

    - **twitter_user_id**: Twitter user UUID
    - **days**: Number of days to analyze (1-365)

    Returns engagement metrics, averages, and top tweets.
    """
    # Verify ownership
    twitter_user = db.query(TwitterUser).filter(
        TwitterUser.id == twitter_user_id,
        TwitterUser.user_id == current_user.id
    ).first()

    if not twitter_user:
        raise HTTPException(status_code=404, detail="Twitter user not found")

    # Calculate date threshold
    since_date = datetime.utcnow() - timedelta(days=days)

    # Get aggregate statistics
    stats = db.query(
        func.count(Tweet.id).label('total_tweets'),
        func.sum(Tweet.like_count).label('total_likes'),
        func.sum(Tweet.retweet_count).label('total_retweets'),
        func.sum(Tweet.reply_count).label('total_replies'),
        func.sum(Tweet.impression_count).label('total_impressions')
    ).filter(
        Tweet.twitter_user_id == twitter_user_id,
        Tweet.created_at >= since_date
    ).first()

    total_tweets = stats.total_tweets or 0
    total_likes = stats.total_likes or 0
    total_retweets = stats.total_retweets or 0
    total_replies = stats.total_replies or 0
    total_impressions = stats.total_impressions or 0

    # Calculate averages
    avg_likes = total_likes / total_tweets if total_tweets > 0 else 0
    avg_retweets = total_retweets / total_tweets if total_tweets > 0 else 0
    total_engagement = total_likes + total_retweets + total_replies
    avg_engagement_rate = (total_engagement / total_impressions * 100) if total_impressions > 0 else 0

    # Get most liked tweet
    most_liked = db.query(Tweet).filter(
        Tweet.twitter_user_id == twitter_user_id,
        Tweet.created_at >= since_date
    ).order_by(desc(Tweet.like_count)).first()

    # Get most retweeted tweet
    most_retweeted = db.query(Tweet).filter(
        Tweet.twitter_user_id == twitter_user_id,
        Tweet.created_at >= since_date
    ).order_by(desc(Tweet.retweet_count)).first()

    # Get recent tweets
    recent_tweets = db.query(Tweet).filter(
        Tweet.twitter_user_id == twitter_user_id
    ).order_by(desc(Tweet.created_at)).limit(10).all()

    return TwitterUserStats(
        total_tweets=total_tweets,
        total_likes=int(total_likes),
        total_retweets=int(total_retweets),
        total_replies=int(total_replies),
        total_impressions=int(total_impressions),
        avg_likes_per_tweet=round(avg_likes, 2),
        avg_retweets_per_tweet=round(avg_retweets, 2),
        avg_engagement_rate=round(avg_engagement_rate, 2),
        most_liked_tweet_id=most_liked.tweet_id if most_liked else None,
        most_liked_tweet_likes=most_liked.like_count if most_liked else None,
        most_retweeted_tweet_id=most_retweeted.tweet_id if most_retweeted else None,
        most_retweeted_tweet_retweets=most_retweeted.retweet_count if most_retweeted else None,
        recent_tweets=recent_tweets
    )
