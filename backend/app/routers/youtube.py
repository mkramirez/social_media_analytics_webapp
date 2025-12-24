"""YouTube API router for channel monitoring and video collection."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User
from app.models.youtube_models import YouTubeChannel, YouTubeVideo, YouTubeComment
from app.models.youtube_schemas import (
    YouTubeChannelCreate,
    YouTubeChannelUpdate,
    YouTubeChannelResponse,
    YouTubeChannelWithVideos,
    YouTubeVideoResponse,
    YouTubeCommentResponse,
    YouTubeChannelStats,
    MonitoringStatus,
    BulkYouTubeChannelCreate,
    BulkCreateResult
)
from app.middleware.auth import get_current_user
from app.services.scheduler_service import (
    add_youtube_monitoring_job,
    remove_youtube_monitoring_job
)

router = APIRouter()


# ============================================
# YouTube Channel CRUD Operations
# ============================================

@router.post("/channels", response_model=YouTubeChannelResponse, status_code=201)
def create_youtube_channel(
    channel_data: YouTubeChannelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new YouTube channel to monitor.

    - **channel_name**: YouTube channel name or handle
    - **channel_id**: Optional YouTube channel ID (UC...)
    - **display_name**: Optional display name
    - **monitoring_interval_seconds**: Collection interval (300-86400 seconds)
    - **video_limit**: Number of recent videos to track (1-200)
    """
    # Check if channel already exists for this user
    existing = db.query(YouTubeChannel).filter(
        YouTubeChannel.user_id == current_user.id,
        YouTubeChannel.channel_name == channel_data.channel_name
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail=f"Channel {channel_data.channel_name} already exists")

    # Create new YouTube channel
    channel = YouTubeChannel(
        user_id=current_user.id,
        channel_name=channel_data.channel_name,
        channel_id=channel_data.channel_id,
        display_name=channel_data.display_name or channel_data.channel_name,
        monitoring_interval_seconds=channel_data.monitoring_interval_seconds,
        video_limit=channel_data.video_limit,
        is_monitoring=False
    )

    db.add(channel)
    db.commit()
    db.refresh(channel)

    return channel


@router.post("/channels/bulk", response_model=BulkCreateResult)
def create_youtube_channels_bulk(
    bulk_data: BulkYouTubeChannelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create multiple YouTube channels at once.

    - **channel_names**: List of channel names (max 20)
    - **monitoring_interval_seconds**: Collection interval for all
    - **video_limit**: Number of videos to track for all
    """
    created_channels = []
    failed_channels = []
    errors = []

    for channel_name in bulk_data.channel_names:
        try:
            # Check if already exists
            existing = db.query(YouTubeChannel).filter(
                YouTubeChannel.user_id == current_user.id,
                YouTubeChannel.channel_name == channel_name
            ).first()

            if existing:
                failed_channels.append(channel_name)
                errors.append(f"{channel_name} already exists")
                continue

            # Create new channel
            channel = YouTubeChannel(
                user_id=current_user.id,
                channel_name=channel_name,
                display_name=channel_name,
                monitoring_interval_seconds=bulk_data.monitoring_interval_seconds,
                video_limit=bulk_data.video_limit,
                is_monitoring=False
            )

            db.add(channel)
            db.flush()  # Get ID without committing
            created_channels.append(channel)

        except Exception as e:
            failed_channels.append(channel_name)
            errors.append(f"{channel_name}: {str(e)}")

    db.commit()

    # Refresh all created channels
    for channel in created_channels:
        db.refresh(channel)

    return BulkCreateResult(
        created_count=len(created_channels),
        failed_count=len(failed_channels),
        created_channels=created_channels,
        failed_channels=failed_channels,
        errors=errors
    )


@router.get("/channels", response_model=List[YouTubeChannelResponse])
def list_youtube_channels(
    monitoring_only: bool = Query(False, description="Only return channels being monitored"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all YouTube channels for the authenticated user.

    - **monitoring_only**: Filter to only show channels being monitored
    """
    query = db.query(YouTubeChannel).filter(YouTubeChannel.user_id == current_user.id)

    if monitoring_only:
        query = query.filter(YouTubeChannel.is_monitoring == True)

    channels = query.order_by(YouTubeChannel.channel_name).all()

    return channels


@router.get("/channels/{channel_id}", response_model=YouTubeChannelWithVideos)
def get_youtube_channel(
    channel_id: UUID,
    limit: int = Query(20, ge=1, le=100, description="Max videos to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific YouTube channel with recent videos.

    - **channel_id**: YouTube channel UUID
    - **limit**: Maximum number of videos to return (1-100)
    """
    channel = db.query(YouTubeChannel).filter(
        YouTubeChannel.id == channel_id,
        YouTubeChannel.user_id == current_user.id
    ).first()

    if not channel:
        raise HTTPException(status_code=404, detail="YouTube channel not found")

    # Get recent videos
    videos = db.query(YouTubeVideo).filter(
        YouTubeVideo.channel_id == channel_id
    ).order_by(desc(YouTubeVideo.published_at)).limit(limit).all()

    # Manually construct response
    response = YouTubeChannelWithVideos(
        id=channel.id,
        channel_name=channel.channel_name,
        channel_id=channel.channel_id,
        display_name=channel.display_name,
        is_monitoring=channel.is_monitoring,
        monitoring_interval_seconds=channel.monitoring_interval_seconds,
        video_limit=channel.video_limit,
        total_videos=channel.total_videos,
        total_comments=channel.total_comments,
        last_collected=channel.last_collected,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
        videos=videos
    )

    return response


@router.put("/channels/{channel_id}", response_model=YouTubeChannelResponse)
def update_youtube_channel(
    channel_id: UUID,
    update_data: YouTubeChannelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a YouTube channel's settings.

    - **display_name**: Update display name
    - **monitoring_interval_seconds**: Update collection interval
    - **video_limit**: Update video limit
    """
    channel = db.query(YouTubeChannel).filter(
        YouTubeChannel.id == channel_id,
        YouTubeChannel.user_id == current_user.id
    ).first()

    if not channel:
        raise HTTPException(status_code=404, detail="YouTube channel not found")

    # Update fields
    if update_data.display_name is not None:
        channel.display_name = update_data.display_name

    if update_data.monitoring_interval_seconds is not None:
        channel.monitoring_interval_seconds = update_data.monitoring_interval_seconds

        # Update job if monitoring
        if channel.is_monitoring:
            add_youtube_monitoring_job(
                channel.id,
                current_user.id,
                update_data.monitoring_interval_seconds
            )

    if update_data.video_limit is not None:
        channel.video_limit = update_data.video_limit

    channel.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(channel)

    return channel


@router.delete("/channels/{channel_id}")
def delete_youtube_channel(
    channel_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a YouTube channel and all associated videos and comments.

    - **channel_id**: YouTube channel UUID
    """
    channel = db.query(YouTubeChannel).filter(
        YouTubeChannel.id == channel_id,
        YouTubeChannel.user_id == current_user.id
    ).first()

    if not channel:
        raise HTTPException(status_code=404, detail="YouTube channel not found")

    # Stop monitoring if active
    if channel.is_monitoring:
        remove_youtube_monitoring_job(channel_id)

    db.delete(channel)
    db.commit()

    return {"message": f"YouTube channel {channel.channel_name} deleted successfully"}


# ============================================
# Monitoring Control
# ============================================

@router.post("/channels/{channel_id}/start-monitoring", response_model=MonitoringStatus)
def start_monitoring(
    channel_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start monitoring a YouTube channel.

    Begins background collection of videos at the configured interval.
    """
    channel = db.query(YouTubeChannel).filter(
        YouTubeChannel.id == channel_id,
        YouTubeChannel.user_id == current_user.id
    ).first()

    if not channel:
        raise HTTPException(status_code=404, detail="YouTube channel not found")

    if channel.is_monitoring:
        return MonitoringStatus(
            message=f"Already monitoring {channel.channel_name}",
            is_monitoring=True,
            channel_name=channel.channel_name
        )

    # Start monitoring job
    try:
        add_youtube_monitoring_job(
            channel.id,
            current_user.id,
            channel.monitoring_interval_seconds
        )

        channel.is_monitoring = True
        db.commit()

        return MonitoringStatus(
            message=f"Started monitoring {channel.channel_name}",
            is_monitoring=True,
            channel_name=channel.channel_name
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start monitoring: {str(e)}")


@router.post("/channels/{channel_id}/stop-monitoring", response_model=MonitoringStatus)
def stop_monitoring(
    channel_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Stop monitoring a YouTube channel.

    Stops the background collection job.
    """
    channel = db.query(YouTubeChannel).filter(
        YouTubeChannel.id == channel_id,
        YouTubeChannel.user_id == current_user.id
    ).first()

    if not channel:
        raise HTTPException(status_code=404, detail="YouTube channel not found")

    if not channel.is_monitoring:
        return MonitoringStatus(
            message=f"{channel.channel_name} is not being monitored",
            is_monitoring=False,
            channel_name=channel.channel_name
        )

    # Stop monitoring job
    remove_youtube_monitoring_job(channel.id)

    channel.is_monitoring = False
    db.commit()

    return MonitoringStatus(
        message=f"Stopped monitoring {channel.channel_name}",
        is_monitoring=False,
        channel_name=channel.channel_name
    )


@router.post("/channels/start-all")
def start_all_monitoring(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start monitoring all YouTube channels.

    Starts background collection for all channels owned by the authenticated user.
    """
    channels = db.query(YouTubeChannel).filter(
        YouTubeChannel.user_id == current_user.id,
        YouTubeChannel.is_monitoring == False
    ).all()

    started_count = 0
    for channel in channels:
        try:
            add_youtube_monitoring_job(
                channel.id,
                current_user.id,
                channel.monitoring_interval_seconds
            )
            channel.is_monitoring = True
            started_count += 1
        except Exception as e:
            print(f"Failed to start monitoring for {channel.channel_name}: {e}")

    db.commit()

    return {
        "message": f"Started monitoring {started_count} YouTube channel(s)",
        "started_count": started_count
    }


@router.post("/channels/stop-all")
def stop_all_monitoring(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Stop monitoring all YouTube channels.

    Stops all background collection jobs for the authenticated user.
    """
    channels = db.query(YouTubeChannel).filter(
        YouTubeChannel.user_id == current_user.id,
        YouTubeChannel.is_monitoring == True
    ).all()

    stopped_count = 0
    for channel in channels:
        remove_youtube_monitoring_job(channel.id)
        channel.is_monitoring = False
        stopped_count += 1

    db.commit()

    return {
        "message": f"Stopped monitoring {stopped_count} YouTube channel(s)",
        "stopped_count": stopped_count
    }


# ============================================
# Video and Comment Retrieval
# ============================================

@router.get("/channels/{channel_id}/videos", response_model=List[YouTubeVideoResponse])
def get_videos(
    channel_id: UUID,
    skip: int = Query(0, ge=0, description="Number of videos to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max videos to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get videos for a specific YouTube channel with pagination.

    - **channel_id**: YouTube channel UUID
    - **skip**: Number of videos to skip (for pagination)
    - **limit**: Maximum videos to return (1-100)
    """
    # Verify ownership
    channel = db.query(YouTubeChannel).filter(
        YouTubeChannel.id == channel_id,
        YouTubeChannel.user_id == current_user.id
    ).first()

    if not channel:
        raise HTTPException(status_code=404, detail="YouTube channel not found")

    # Get videos with pagination
    videos = db.query(YouTubeVideo).filter(
        YouTubeVideo.channel_id == channel_id
    ).order_by(desc(YouTubeVideo.published_at)).offset(skip).limit(limit).all()

    return videos


@router.get("/videos/{video_id}/comments", response_model=List[YouTubeCommentResponse])
def get_video_comments(
    video_id: UUID,
    skip: int = Query(0, ge=0, description="Number of comments to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max comments to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get comments for a specific video with pagination.

    - **video_id**: YouTube video UUID
    - **skip**: Number of comments to skip (for pagination)
    - **limit**: Maximum comments to return (1-100)
    """
    # Verify ownership
    video = db.query(YouTubeVideo).filter(
        YouTubeVideo.id == video_id,
        YouTubeVideo.user_id == current_user.id
    ).first()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Get comments with pagination
    comments = db.query(YouTubeComment).filter(
        YouTubeComment.video_id == video_id
    ).order_by(desc(YouTubeComment.like_count)).offset(skip).limit(limit).all()

    return comments


# ============================================
# Statistics
# ============================================

@router.get("/channels/{channel_id}/stats", response_model=YouTubeChannelStats)
def get_youtube_channel_stats(
    channel_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get statistics for a YouTube channel.

    - **channel_id**: YouTube channel UUID
    - **days**: Number of days to analyze (1-365)

    Returns engagement metrics, averages, and top videos.
    """
    # Verify ownership
    channel = db.query(YouTubeChannel).filter(
        YouTubeChannel.id == channel_id,
        YouTubeChannel.user_id == current_user.id
    ).first()

    if not channel:
        raise HTTPException(status_code=404, detail="YouTube channel not found")

    # Calculate date threshold
    since_date = datetime.utcnow() - timedelta(days=days)

    # Get aggregate statistics
    stats = db.query(
        func.count(YouTubeVideo.id).label('total_videos'),
        func.sum(YouTubeVideo.view_count).label('total_views'),
        func.sum(YouTubeVideo.like_count).label('total_likes'),
        func.sum(YouTubeVideo.comment_count).label('total_comments')
    ).filter(
        YouTubeVideo.channel_id == channel_id,
        YouTubeVideo.published_at >= since_date
    ).first()

    total_videos = stats.total_videos or 0
    total_views = stats.total_views or 0
    total_likes = stats.total_likes or 0
    total_comments = stats.total_comments or 0

    # Calculate averages
    avg_views = total_views / total_videos if total_videos > 0 else 0
    avg_likes = total_likes / total_videos if total_videos > 0 else 0
    avg_comments = total_comments / total_videos if total_videos > 0 else 0
    avg_engagement_rate = ((total_likes + total_comments) / total_views * 100) if total_views > 0 else 0

    # Get most viewed video
    most_viewed = db.query(YouTubeVideo).filter(
        YouTubeVideo.channel_id == channel_id,
        YouTubeVideo.published_at >= since_date
    ).order_by(desc(YouTubeVideo.view_count)).first()

    # Get most liked video
    most_liked = db.query(YouTubeVideo).filter(
        YouTubeVideo.channel_id == channel_id,
        YouTubeVideo.published_at >= since_date
    ).order_by(desc(YouTubeVideo.like_count)).first()

    # Get recent videos
    recent_videos = db.query(YouTubeVideo).filter(
        YouTubeVideo.channel_id == channel_id
    ).order_by(desc(YouTubeVideo.published_at)).limit(10).all()

    return YouTubeChannelStats(
        total_videos=total_videos,
        total_views=int(total_views),
        total_likes=int(total_likes),
        total_comments=int(total_comments),
        avg_views_per_video=round(avg_views, 2),
        avg_likes_per_video=round(avg_likes, 2),
        avg_comments_per_video=round(avg_comments, 2),
        avg_engagement_rate=round(avg_engagement_rate, 2),
        most_viewed_video_id=most_viewed.video_id if most_viewed else None,
        most_viewed_video_title=most_viewed.title if most_viewed else None,
        most_viewed_video_views=most_viewed.view_count if most_viewed else None,
        most_liked_video_id=most_liked.video_id if most_liked else None,
        most_liked_video_title=most_liked.title if most_liked else None,
        most_liked_video_likes=most_liked.like_count if most_liked else None,
        recent_videos=recent_videos
    )
