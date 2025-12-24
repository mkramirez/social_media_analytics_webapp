"""Twitch monitoring endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User
from app.models.twitch_models import TwitchChannel, TwitchStreamRecord
from app.models.twitch_schemas import (
    TwitchChannelCreate,
    TwitchChannelResponse,
    TwitchChannelUpdate,
    TwitchStreamRecordResponse,
    TwitchChannelWithRecords,
    TwitchChannelStats,
    BulkChannelCreate,
    BulkOperationResponse,
    MonitoringStatusResponse
)
from app.models.schemas import MessageResponse
from app.middleware.auth import get_current_active_user
from app.services.scheduler_service import (
    add_twitch_monitoring_job,
    remove_twitch_monitoring_job,
    get_job_status
)
from app.platforms.twitch.collector import TwitchCollector
from app.models.profile import APIProfile
from app.services.credential_service import CredentialService

router = APIRouter()
credential_service = CredentialService()


# ============================================
# Channel CRUD Operations
# ============================================

@router.post("/channels", response_model=TwitchChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_channel(
    channel_data: TwitchChannelCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Add a Twitch channel to monitor.

    Args:
        channel_data: Channel creation data
        current_user: Authenticated user
        db: Database session

    Returns:
        Created channel
    """
    # Check if channel already exists for this user
    existing = db.query(TwitchChannel).filter(
        TwitchChannel.user_id == current_user.id,
        TwitchChannel.username == channel_data.username.lower()
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Channel '{channel_data.username}' already exists"
        )

    # Create channel
    new_channel = TwitchChannel(
        user_id=current_user.id,
        username=channel_data.username.lower(),
        monitoring_interval_seconds=channel_data.monitoring_interval_seconds,
        is_monitoring=False
    )

    db.add(new_channel)
    db.commit()
    db.refresh(new_channel)

    return TwitchChannelResponse.from_orm(new_channel)


@router.post("/channels/bulk", response_model=BulkOperationResponse)
async def create_channels_bulk(
    bulk_data: BulkChannelCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Add multiple Twitch channels at once.

    Args:
        bulk_data: Bulk channel creation data
        current_user: Authenticated user
        db: Database session

    Returns:
        Bulk operation results
    """
    results = []
    successful = 0
    failed = 0

    for username in bulk_data.usernames:
        try:
            # Check if channel already exists
            existing = db.query(TwitchChannel).filter(
                TwitchChannel.user_id == current_user.id,
                TwitchChannel.username == username.lower()
            ).first()

            if existing:
                results.append({
                    "username": username,
                    "success": False,
                    "error": "Channel already exists"
                })
                failed += 1
                continue

            # Create channel
            new_channel = TwitchChannel(
                user_id=current_user.id,
                username=username.lower(),
                monitoring_interval_seconds=bulk_data.monitoring_interval_seconds,
                is_monitoring=False
            )

            db.add(new_channel)
            db.flush()

            results.append({
                "username": username,
                "success": True,
                "channel_id": str(new_channel.id)
            })
            successful += 1

        except Exception as e:
            results.append({
                "username": username,
                "success": False,
                "error": str(e)
            })
            failed += 1

    db.commit()

    return BulkOperationResponse(
        total=len(bulk_data.usernames),
        successful=successful,
        failed=failed,
        results=results
    )


@router.get("/channels", response_model=List[TwitchChannelResponse])
async def list_channels(
    monitoring_only: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all Twitch channels for the current user.

    Args:
        monitoring_only: Filter to only show monitoring channels
        current_user: Authenticated user
        db: Database session

    Returns:
        List of channels
    """
    query = db.query(TwitchChannel).filter(TwitchChannel.user_id == current_user.id)

    if monitoring_only:
        query = query.filter(TwitchChannel.is_monitoring == True)

    channels = query.order_by(TwitchChannel.created_at.desc()).all()

    return [TwitchChannelResponse.from_orm(c) for c in channels]


@router.get("/channels/{channel_id}", response_model=TwitchChannelWithRecords)
async def get_channel(
    channel_id: UUID,
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific channel with recent records.

    Args:
        channel_id: Channel UUID
        limit: Number of recent records to include
        current_user: Authenticated user
        db: Database session

    Returns:
        Channel with recent records
    """
    channel = db.query(TwitchChannel).filter(
        TwitchChannel.id == channel_id,
        TwitchChannel.user_id == current_user.id
    ).first()

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )

    # Get recent records
    records = db.query(TwitchStreamRecord).filter(
        TwitchStreamRecord.channel_id == channel_id
    ).order_by(TwitchStreamRecord.timestamp.desc()).limit(limit).all()

    # Create response
    response_data = TwitchChannelResponse.from_orm(channel).dict()
    response_data["recent_records"] = [TwitchStreamRecordResponse.from_orm(r) for r in records]

    return TwitchChannelWithRecords(**response_data)


@router.put("/channels/{channel_id}", response_model=TwitchChannelResponse)
async def update_channel(
    channel_id: UUID,
    channel_data: TwitchChannelUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update a channel's settings.

    Args:
        channel_id: Channel UUID
        channel_data: Update data
        current_user: Authenticated user
        db: Database session

    Returns:
        Updated channel
    """
    channel = db.query(TwitchChannel).filter(
        TwitchChannel.id == channel_id,
        TwitchChannel.user_id == current_user.id
    ).first()

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )

    # Update monitoring interval
    if channel_data.monitoring_interval_seconds:
        channel.monitoring_interval_seconds = channel_data.monitoring_interval_seconds

        # If channel is monitoring, restart job with new interval
        if channel.is_monitoring:
            remove_twitch_monitoring_job(channel_id)
            add_twitch_monitoring_job(
                channel_id,
                current_user.id,
                channel_data.monitoring_interval_seconds
            )

    db.commit()
    db.refresh(channel)

    return TwitchChannelResponse.from_orm(channel)


@router.delete("/channels/{channel_id}", response_model=MessageResponse)
async def delete_channel(
    channel_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a channel and all its data.

    Args:
        channel_id: Channel UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Success message
    """
    channel = db.query(TwitchChannel).filter(
        TwitchChannel.id == channel_id,
        TwitchChannel.user_id == current_user.id
    ).first()

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )

    # Stop monitoring if active
    if channel.is_monitoring:
        remove_twitch_monitoring_job(channel_id)

    username = channel.username
    db.delete(channel)
    db.commit()

    return MessageResponse(
        message="Channel deleted successfully",
        detail=f"Deleted channel: {username}"
    )


# ============================================
# Monitoring Control
# ============================================

@router.post("/channels/{channel_id}/start-monitoring", response_model=MonitoringStatusResponse)
async def start_monitoring(
    channel_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Start monitoring a channel.

    Args:
        channel_id: Channel UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Monitoring status
    """
    channel = db.query(TwitchChannel).filter(
        TwitchChannel.id == channel_id,
        TwitchChannel.user_id == current_user.id
    ).first()

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )

    # Check if user has active Twitch profile
    profile = db.query(APIProfile).filter(
        APIProfile.user_id == current_user.id,
        APIProfile.platform == "twitch",
        APIProfile.is_active == True
    ).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active Twitch API profile. Please create one first."
        )

    # Start monitoring
    channel.is_monitoring = True
    db.commit()

    # Add scheduler job
    try:
        job_id = add_twitch_monitoring_job(
            channel_id,
            current_user.id,
            channel.monitoring_interval_seconds
        )

        return MonitoringStatusResponse(
            channel_id=channel_id,
            username=channel.username,
            is_monitoring=True,
            job_id=job_id,
            message="Monitoring started successfully"
        )
    except Exception as e:
        channel.is_monitoring = False
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start monitoring: {str(e)}"
        )


@router.post("/channels/{channel_id}/stop-monitoring", response_model=MonitoringStatusResponse)
async def stop_monitoring(
    channel_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Stop monitoring a channel.

    Args:
        channel_id: Channel UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Monitoring status
    """
    channel = db.query(TwitchChannel).filter(
        TwitchChannel.id == channel_id,
        TwitchChannel.user_id == current_user.id
    ).first()

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )

    # Stop monitoring
    channel.is_monitoring = False
    db.commit()

    # Remove scheduler job
    remove_twitch_monitoring_job(channel_id)

    return MonitoringStatusResponse(
        channel_id=channel_id,
        username=channel.username,
        is_monitoring=False,
        message="Monitoring stopped successfully"
    )


@router.post("/channels/start-all", response_model=List[MonitoringStatusResponse])
async def start_all_monitoring(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Start monitoring all channels.

    Args:
        current_user: Authenticated user
        db: Database session

    Returns:
        List of monitoring statuses
    """
    # Check if user has active Twitch profile
    profile = db.query(APIProfile).filter(
        APIProfile.user_id == current_user.id,
        APIProfile.platform == "twitch",
        APIProfile.is_active == True
    ).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active Twitch API profile. Please create one first."
        )

    # Get all channels
    channels = db.query(TwitchChannel).filter(
        TwitchChannel.user_id == current_user.id
    ).all()

    results = []

    for channel in channels:
        if channel.is_monitoring:
            results.append(MonitoringStatusResponse(
                channel_id=channel.id,
                username=channel.username,
                is_monitoring=True,
                message="Already monitoring"
            ))
            continue

        try:
            channel.is_monitoring = True
            job_id = add_twitch_monitoring_job(
                channel.id,
                current_user.id,
                channel.monitoring_interval_seconds
            )

            results.append(MonitoringStatusResponse(
                channel_id=channel.id,
                username=channel.username,
                is_monitoring=True,
                job_id=job_id,
                message="Monitoring started"
            ))
        except Exception as e:
            channel.is_monitoring = False
            results.append(MonitoringStatusResponse(
                channel_id=channel.id,
                username=channel.username,
                is_monitoring=False,
                message=f"Failed: {str(e)}"
            ))

    db.commit()

    return results


@router.post("/channels/stop-all", response_model=MessageResponse)
async def stop_all_monitoring(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Stop monitoring all channels.

    Args:
        current_user: Authenticated user
        db: Database session

    Returns:
        Success message
    """
    # Get all monitoring channels
    channels = db.query(TwitchChannel).filter(
        TwitchChannel.user_id == current_user.id,
        TwitchChannel.is_monitoring == True
    ).all()

    count = 0
    for channel in channels:
        channel.is_monitoring = False
        remove_twitch_monitoring_job(channel.id)
        count += 1

    db.commit()

    return MessageResponse(
        message=f"Stopped monitoring {count} channel(s)"
    )


# ============================================
# Data Retrieval
# ============================================

@router.get("/channels/{channel_id}/records", response_model=List[TwitchStreamRecordResponse])
async def get_channel_records(
    channel_id: UUID,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get stream records for a channel.

    Args:
        channel_id: Channel UUID
        limit: Maximum number of records
        offset: Offset for pagination
        start_date: Optional start date filter
        end_date: Optional end date filter
        current_user: Authenticated user
        db: Database session

    Returns:
        List of stream records
    """
    # Verify channel ownership
    channel = db.query(TwitchChannel).filter(
        TwitchChannel.id == channel_id,
        TwitchChannel.user_id == current_user.id
    ).first()

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )

    # Build query
    query = db.query(TwitchStreamRecord).filter(TwitchStreamRecord.channel_id == channel_id)

    if start_date:
        query = query.filter(TwitchStreamRecord.timestamp >= start_date)

    if end_date:
        query = query.filter(TwitchStreamRecord.timestamp <= end_date)

    records = query.order_by(TwitchStreamRecord.timestamp.desc()).offset(offset).limit(limit).all()

    return [TwitchStreamRecordResponse.from_orm(r) for r in records]


@router.get("/channels/{channel_id}/stats", response_model=TwitchChannelStats)
async def get_channel_stats(
    channel_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get statistics for a channel.

    Args:
        channel_id: Channel UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Channel statistics
    """
    # Verify channel ownership
    channel = db.query(TwitchChannel).filter(
        TwitchChannel.id == channel_id,
        TwitchChannel.user_id == current_user.id
    ).first()

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )

    # Get collector with user's credentials
    profile = db.query(APIProfile).filter(
        APIProfile.user_id == current_user.id,
        APIProfile.platform == "twitch",
        APIProfile.is_active == True
    ).first()

    if profile:
        try:
            credentials = credential_service.decrypt_credentials(profile.encrypted_credentials)
            collector = TwitchCollector(
                client_id=credentials["client_id"],
                client_secret=credentials["client_secret"]
            )
            stats = collector.get_channel_stats(db, channel_id)

            if stats:
                return TwitchChannelStats(**stats)
        except Exception as e:
            print(f"Error getting stats: {e}")

    # Fallback to basic stats
    records = db.query(TwitchStreamRecord).filter(TwitchStreamRecord.channel_id == channel_id).all()

    if not records:
        return TwitchChannelStats(
            channel_id=channel_id,
            username=channel.username,
            total_records=0,
            total_live_sessions=0,
            average_viewers=0,
            peak_viewers=0,
            total_monitoring_time_minutes=0,
            is_currently_live=False
        )

    live_records = [r for r in records if r.is_live]
    avg_viewers = sum(r.viewer_count for r in records) / len(records) if records else 0
    peak_viewers = max(r.viewer_count for r in records) if records else 0
    latest = max(records, key=lambda r: r.timestamp)

    return TwitchChannelStats(
        channel_id=channel_id,
        username=channel.username,
        total_records=len(records),
        total_live_sessions=len(live_records),
        average_viewers=round(avg_viewers, 2),
        peak_viewers=peak_viewers,
        total_monitoring_time_minutes=0,
        is_currently_live=latest.is_live,
        current_viewers=latest.viewer_count if latest.is_live else None,
        current_game=latest.game_name if latest.is_live else None
    )
