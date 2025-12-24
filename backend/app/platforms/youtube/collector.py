"""YouTube data collection service."""

from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from datetime import datetime
from uuid import UUID

from app.models.youtube_models import YouTubeChannel, YouTubeVideo, YouTubeComment
from app.platforms.youtube.youtube_api import YouTubeAPI
import logging

logger = logging.getLogger(__name__)


class YouTubeCollector:
    """Collects videos and comments from YouTube channels."""

    def __init__(self, api_key: str):
        """
        Initialize YouTube collector.

        Args:
            api_key: YouTube Data API key
        """
        self.api = YouTubeAPI(api_key)

    def collect_videos(
        self,
        db: Session,
        channel_id: UUID,
        user_id: UUID
    ) -> Optional[Dict]:
        """
        Collect videos for a YouTube channel.

        Args:
            db: Database session
            channel_id: YouTubeChannel record ID
            user_id: User ID (for authorization)

        Returns:
            Collection summary dict or None on error
        """
        try:
            # Get the YouTube channel record
            channel = db.query(YouTubeChannel).filter(
                YouTubeChannel.id == channel_id,
                YouTubeChannel.user_id == user_id
            ).first()

            if not channel:
                logger.error(f"YouTube channel {channel_id} not found")
                return None

            # Collect videos from API
            videos = self.api.get_channel_videos(
                channel_name=channel.channel_name,
                max_results=channel.video_limit
            )

            if not videos:
                logger.info(f"No videos found for {channel.channel_name}")
                channel.last_collected = datetime.utcnow()
                db.commit()
                return {
                    "channel_name": channel.channel_name,
                    "videos_collected": 0,
                    "new_videos": 0,
                    "comments_collected": 0
                }

            # Store videos in database
            new_videos = 0
            total_comments = 0

            for video_data in videos:
                try:
                    # Check if video already exists
                    existing_video = db.query(YouTubeVideo).filter(
                        YouTubeVideo.video_id == video_data['video_id']
                    ).first()

                    if existing_video:
                        # Update existing video metrics
                        existing_video.view_count = video_data.get('view_count', 0)
                        existing_video.like_count = video_data.get('like_count', 0)
                        existing_video.comment_count = video_data.get('comment_count', 0)
                        existing_video.description = video_data.get('description', '')

                        video_record = existing_video
                    else:
                        # Create new video record
                        new_video = YouTubeVideo(
                            channel_id=channel_id,
                            user_id=user_id,
                            video_id=video_data['video_id'],
                            title=video_data['title'],
                            description=video_data.get('description', ''),
                            published_at=datetime.fromisoformat(video_data['published_at'].replace('Z', '+00:00')),
                            view_count=video_data.get('view_count', 0),
                            like_count=video_data.get('like_count', 0),
                            comment_count=video_data.get('comment_count', 0)
                        )
                        db.add(new_video)
                        db.flush()  # Get ID
                        new_videos += 1
                        video_record = new_video

                    # Collect top comments for this video
                    comments = self.api.get_video_comments(
                        video_id=video_data['video_id'],
                        max_results=20  # Collect top 20 comments
                    )

                    if comments:
                        for comment_data in comments:
                            try:
                                # Check if comment already exists
                                existing_comment = db.query(YouTubeComment).filter(
                                    YouTubeComment.comment_id == comment_data['comment_id']
                                ).first()

                                if existing_comment:
                                    # Update existing comment metrics
                                    existing_comment.like_count = comment_data.get('like_count', 0)
                                    existing_comment.reply_count = comment_data.get('reply_count', 0)
                                else:
                                    # Create new comment record
                                    new_comment = YouTubeComment(
                                        video_id=video_record.id,
                                        user_id=user_id,
                                        comment_id=comment_data['comment_id'],
                                        text=comment_data['text'],
                                        author=comment_data.get('author', 'Unknown'),
                                        like_count=comment_data.get('like_count', 0),
                                        reply_count=comment_data.get('reply_count', 0),
                                        published_at=datetime.fromisoformat(comment_data['published_at'].replace('Z', '+00:00'))
                                    )
                                    db.add(new_comment)
                                    total_comments += 1

                            except Exception as e:
                                logger.error(f"Error storing comment {comment_data.get('comment_id')}: {e}")
                                continue

                except Exception as e:
                    logger.error(f"Error storing video {video_data.get('video_id')}: {e}")
                    continue

            # Update channel statistics
            total_videos = db.query(YouTubeVideo).filter(
                YouTubeVideo.channel_id == channel_id
            ).count()

            total_comments_db = db.query(YouTubeComment).join(YouTubeVideo).filter(
                YouTubeVideo.channel_id == channel_id
            ).count()

            channel.total_videos = total_videos
            channel.total_comments = total_comments_db
            channel.last_collected = datetime.utcnow()

            db.commit()

            logger.info(f"Collected {new_videos} new videos and {total_comments} new comments for {channel.channel_name}")

            return {
                "channel_name": channel.channel_name,
                "videos_collected": len(videos),
                "new_videos": new_videos,
                "total_videos": total_videos,
                "comments_collected": total_comments
            }

        except Exception as e:
            logger.error(f"Error collecting videos for channel {channel_id}: {e}")
            db.rollback()
            return None

    def verify_channel_exists(self, channel_name: str) -> bool:
        """
        Verify that a YouTube channel exists.

        Args:
            channel_name: YouTube channel name

        Returns:
            True if channel exists, False otherwise
        """
        try:
            videos = self.api.get_channel_videos(channel_name, max_results=1)
            return videos is not None and len(videos) > 0
        except:
            return False

    def get_channel_info(self, channel_name: str) -> Optional[Dict]:
        """
        Get basic channel information.

        Args:
            channel_name: YouTube channel name

        Returns:
            Channel info dict or None on error
        """
        try:
            videos = self.api.get_channel_videos(channel_name, max_results=1)
            if videos and len(videos) > 0:
                # Extract channel info from first video
                return {
                    "channel_name": channel_name,
                    "exists": True
                }
            return None
        except Exception as e:
            logger.error(f"Error getting channel info for {channel_name}: {e}")
            return None
