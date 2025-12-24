"""Twitch data collector for background jobs."""

from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID

from app.models.twitch_models import TwitchChannel, TwitchStreamRecord
from app.platforms.twitch.twitch_api import TwitchAPI


class TwitchCollector:
    """Collector for Twitch stream data."""

    def __init__(self, client_id: str, client_secret: str):
        """
        Initialize Twitch collector.

        Args:
            client_id: Twitch API client ID
            client_secret: Twitch API client secret
        """
        self.api = TwitchAPI(client_id, client_secret)

    def collect_stream_data(
        self,
        db: Session,
        channel_id: UUID,
        user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Collect stream data for a channel.

        Args:
            db: Database session
            channel_id: Channel UUID
            user_id: User UUID

        Returns:
            Collected data dictionary or None if collection failed
        """
        # Get channel from database
        channel = db.query(TwitchChannel).filter(TwitchChannel.id == channel_id).first()

        if not channel:
            return None

        try:
            # Get stream info from Twitch API
            stream_info = self.api.get_stream_info(channel.username)

            # Create stream record
            record = TwitchStreamRecord(
                channel_id=channel_id,
                user_id=user_id,
                timestamp=datetime.utcnow(),
                viewer_count=stream_info.get("viewer_count", 0),
                game_name=stream_info.get("game_name"),
                stream_title=stream_info.get("title"),
                is_live=stream_info.get("is_live", False),
                uptime_minutes=0  # Can be calculated from stream start time
            )

            db.add(record)

            # Update channel metadata
            channel.last_checked = datetime.utcnow()
            channel.total_records += 1

            # Update Twitch user ID if not set
            if not channel.channel_id and stream_info.get("user_id"):
                channel.channel_id = stream_info.get("user_id")

            # Update display name if not set
            if not channel.display_name and stream_info.get("user_name"):
                channel.display_name = stream_info.get("user_name")

            db.commit()

            return {
                "channel_id": str(channel_id),
                "username": channel.username,
                "is_live": stream_info.get("is_live", False),
                "viewer_count": stream_info.get("viewer_count", 0),
                "game_name": stream_info.get("game_name"),
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            db.rollback()
            print(f"Error collecting data for {channel.username}: {e}")
            return None

    def get_channel_stats(
        self,
        db: Session,
        channel_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a channel.

        Args:
            db: Database session
            channel_id: Channel UUID

        Returns:
            Statistics dictionary
        """
        channel = db.query(TwitchChannel).filter(TwitchChannel.id == channel_id).first()

        if not channel:
            return None

        # Get all records
        records = db.query(TwitchStreamRecord).filter(
            TwitchStreamRecord.channel_id == channel_id
        ).all()

        if not records:
            return {
                "channel_id": str(channel_id),
                "username": channel.username,
                "total_records": 0,
                "total_live_sessions": 0,
                "average_viewers": 0,
                "peak_viewers": 0
            }

        # Calculate stats
        live_records = [r for r in records if r.is_live]
        total_live_sessions = len(live_records)
        average_viewers = sum(r.viewer_count for r in records) / len(records) if records else 0
        peak_viewers = max(r.viewer_count for r in records) if records else 0

        # Get current status
        latest_record = max(records, key=lambda r: r.timestamp)

        return {
            "channel_id": str(channel_id),
            "username": channel.username,
            "total_records": len(records),
            "total_live_sessions": total_live_sessions,
            "average_viewers": round(average_viewers, 2),
            "peak_viewers": peak_viewers,
            "is_currently_live": latest_record.is_live,
            "current_viewers": latest_record.viewer_count if latest_record.is_live else None,
            "current_game": latest_record.game_name if latest_record.is_live else None
        }
