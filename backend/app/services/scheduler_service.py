"""APScheduler service for background monitoring jobs."""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from typing import Dict, Any
from uuid import UUID
import logging

from app.config import settings
from app.database import SessionLocal
from app.models.twitch_models import TwitchChannel
from app.models.twitter_models import TwitterUser
from app.models.youtube_models import YouTubeChannel
from app.models.reddit_models import RedditSubreddit
from app.models.profile import APIProfile
from app.platforms.twitch.collector import TwitchCollector
from app.platforms.twitter.collector import TwitterCollector
from app.platforms.youtube.collector import YouTubeCollector
from app.platforms.reddit.collector import RedditCollector
from app.services.credential_service import CredentialService

# Configure logging
logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.INFO)

# Global scheduler instance
scheduler: BackgroundScheduler = None
credential_service = CredentialService()


def get_scheduler() -> BackgroundScheduler:
    """Get the global scheduler instance."""
    global scheduler
    return scheduler


def twitch_monitoring_job(channel_id: str, user_id: str):
    """
    Background job to monitor a Twitch channel.

    Args:
        channel_id: Channel UUID as string
        user_id: User UUID as string
    """
    db = SessionLocal()
    try:
        # Convert string UUIDs to UUID objects
        channel_uuid = UUID(channel_id)
        user_uuid = UUID(user_id)

        # Get channel
        channel = db.query(TwitchChannel).filter(TwitchChannel.id == channel_uuid).first()
        if not channel or not channel.is_monitoring:
            return

        # Get user's active Twitch profile
        profile = db.query(APIProfile).filter(
            APIProfile.user_id == user_uuid,
            APIProfile.platform == "twitch",
            APIProfile.is_active == True
        ).first()

        if not profile:
            print(f"No active Twitch profile for user {user_id}")
            return

        # Decrypt credentials
        try:
            credentials = credential_service.decrypt_credentials(profile.encrypted_credentials)
        except Exception as e:
            print(f"Failed to decrypt credentials: {e}")
            return

        # Create collector and collect data
        collector = TwitchCollector(
            client_id=credentials["client_id"],
            client_secret=credentials["client_secret"]
        )

        result = collector.collect_stream_data(db, channel_uuid, user_uuid)

        if result:
            print(f"✓ Collected data for {result['username']}: Live={result['is_live']}, Viewers={result['viewer_count']}")
        else:
            print(f"✗ Failed to collect data for channel {channel_id}")

    except Exception as e:
        print(f"Error in monitoring job: {e}")
    finally:
        db.close()


def twitter_monitoring_job(twitter_user_id: str, user_id: str):
    """
    Background job to monitor a Twitter user.

    Args:
        twitter_user_id: TwitterUser UUID as string
        user_id: User UUID as string
    """
    db = SessionLocal()
    try:
        # Convert string UUIDs to UUID objects
        twitter_user_uuid = UUID(twitter_user_id)
        user_uuid = UUID(user_id)

        # Get Twitter user
        twitter_user = db.query(TwitterUser).filter(TwitterUser.id == twitter_user_uuid).first()
        if not twitter_user or not twitter_user.is_monitoring:
            return

        # Get user's active Twitter profile
        profile = db.query(APIProfile).filter(
            APIProfile.user_id == user_uuid,
            APIProfile.platform == "twitter",
            APIProfile.is_active == True
        ).first()

        if not profile:
            print(f"No active Twitter profile for user {user_id}")
            return

        # Decrypt credentials
        try:
            credentials = credential_service.decrypt_credentials(profile.encrypted_credentials)
        except Exception as e:
            print(f"Failed to decrypt credentials: {e}")
            return

        # Create collector and collect tweets
        collector = TwitterCollector(bearer_token=credentials["bearer_token"])

        result = collector.collect_tweets(db, twitter_user_uuid, user_uuid)

        if result:
            print(f"✓ Collected tweets for @{result['username']}: New={result['new_tweets']}, Total={result['total_tweets']}")
        else:
            print(f"✗ Failed to collect tweets for user {twitter_user_id}")

    except Exception as e:
        print(f"Error in Twitter monitoring job: {e}")
    finally:
        db.close()


def start_scheduler():
    """Initialize and start the APScheduler."""
    global scheduler

    if scheduler is not None:
        print("Scheduler already running")
        return

    # Configure job stores
    jobstores = {
        'default': SQLAlchemyJobStore(url=settings.DATABASE_URL)
    }

    # Configure executors
    executors = {
        'default': ThreadPoolExecutor(settings.SCHEDULER_EXECUTORS_DEFAULT_MAX_WORKERS)
    }

    # Configure job defaults
    job_defaults = {
        'coalesce': settings.SCHEDULER_JOB_DEFAULTS_COALESCE,
        'max_instances': settings.SCHEDULER_JOB_DEFAULTS_MAX_INSTANCES
    }

    # Create scheduler
    scheduler = BackgroundScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone='UTC'
    )

    # Start scheduler
    scheduler.start()
    print("✓ APScheduler started successfully")


def shutdown_scheduler():
    """Shutdown the APScheduler."""
    global scheduler

    if scheduler is not None:
        scheduler.shutdown()
        scheduler = None
        print("✓ APScheduler shut down successfully")


def add_twitch_monitoring_job(
    channel_id: UUID,
    user_id: UUID,
    interval_seconds: int = 30
) -> str:
    """
    Add a monitoring job for a Twitch channel.

    Args:
        channel_id: Channel UUID
        user_id: User UUID
        interval_seconds: Monitoring interval in seconds

    Returns:
        Job ID
    """
    global scheduler

    if scheduler is None:
        raise RuntimeError("Scheduler not started")

    job_id = f"twitch_monitor_{channel_id}"

    # Remove existing job if any
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    # Add new job
    scheduler.add_job(
        func=twitch_monitoring_job,
        trigger='interval',
        seconds=interval_seconds,
        args=[str(channel_id), str(user_id)],
        id=job_id,
        replace_existing=True
    )

    print(f"✓ Added monitoring job for channel {channel_id} (interval: {interval_seconds}s)")

    return job_id


def remove_twitch_monitoring_job(channel_id: UUID) -> bool:
    """
    Remove a monitoring job for a Twitch channel.

    Args:
        channel_id: Channel UUID

    Returns:
        True if job was removed, False if job didn't exist
    """
    global scheduler

    if scheduler is None:
        return False

    job_id = f"twitch_monitor_{channel_id}"

    try:
        scheduler.remove_job(job_id)
        print(f"✓ Removed monitoring job for channel {channel_id}")
        return True
    except:
        return False


def pause_twitch_monitoring_job(channel_id: UUID) -> bool:
    """
    Pause a monitoring job.

    Args:
        channel_id: Channel UUID

    Returns:
        True if job was paused, False otherwise
    """
    global scheduler

    if scheduler is None:
        return False

    job_id = f"twitch_monitor_{channel_id}"

    try:
        scheduler.pause_job(job_id)
        print(f"✓ Paused monitoring job for channel {channel_id}")
        return True
    except:
        return False


def resume_twitch_monitoring_job(channel_id: UUID) -> bool:
    """
    Resume a paused monitoring job.

    Args:
        channel_id: Channel UUID

    Returns:
        True if job was resumed, False otherwise
    """
    global scheduler

    if scheduler is None:
        return False

    job_id = f"twitch_monitor_{channel_id}"

    try:
        scheduler.resume_job(job_id)
        print(f"✓ Resumed monitoring job for channel {channel_id}")
        return True
    except:
        return False


def get_job_status(channel_id: UUID) -> Dict[str, Any]:
    """
    Get status of a monitoring job.

    Args:
        channel_id: Channel UUID

    Returns:
        Job status dictionary
    """
    global scheduler

    if scheduler is None:
        return {"exists": False, "error": "Scheduler not running"}

    job_id = f"twitch_monitor_{channel_id}"
    job = scheduler.get_job(job_id)

    if not job:
        return {"exists": False}

    return {
        "exists": True,
        "job_id": job.id,
        "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
        "trigger": str(job.trigger)
    }


# ============================================
# Twitter Monitoring Job Management
# ============================================

def add_twitter_monitoring_job(
    twitter_user_id: UUID,
    user_id: UUID,
    interval_seconds: int = 300
) -> str:
    """
    Add a monitoring job for a Twitter user.

    Args:
        twitter_user_id: TwitterUser UUID
        user_id: User UUID
        interval_seconds: Monitoring interval in seconds

    Returns:
        Job ID
    """
    global scheduler

    if scheduler is None:
        raise RuntimeError("Scheduler not started")

    job_id = f"twitter_monitor_{twitter_user_id}"

    # Remove existing job if any
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    # Add new job
    scheduler.add_job(
        func=twitter_monitoring_job,
        trigger='interval',
        seconds=interval_seconds,
        args=[str(twitter_user_id), str(user_id)],
        id=job_id,
        replace_existing=True
    )

    print(f"✓ Added Twitter monitoring job for user {twitter_user_id} (interval: {interval_seconds}s)")

    return job_id


def remove_twitter_monitoring_job(twitter_user_id: UUID) -> bool:
    """
    Remove a monitoring job for a Twitter user.

    Args:
        twitter_user_id: TwitterUser UUID

    Returns:
        True if job was removed, False if job didn't exist
    """
    global scheduler

    if scheduler is None:
        return False

    job_id = f"twitter_monitor_{twitter_user_id}"

    try:
        scheduler.remove_job(job_id)
        print(f"✓ Removed Twitter monitoring job for user {twitter_user_id}")
        return True
    except:
        return False


# ============================================
# YouTube Monitoring Job Management
# ============================================

def youtube_monitoring_job(channel_id: str, user_id: str):
    """
    Background job to monitor a YouTube channel.

    Args:
        channel_id: YouTubeChannel UUID as string
        user_id: User UUID as string
    """
    db = SessionLocal()
    try:
        # Convert string UUIDs to UUID objects
        channel_uuid = UUID(channel_id)
        user_uuid = UUID(user_id)

        # Get YouTube channel
        channel = db.query(YouTubeChannel).filter(YouTubeChannel.id == channel_uuid).first()
        if not channel or not channel.is_monitoring:
            return

        # Get user's active YouTube profile
        profile = db.query(APIProfile).filter(
            APIProfile.user_id == user_uuid,
            APIProfile.platform == "youtube",
            APIProfile.is_active == True
        ).first()

        if not profile:
            print(f"No active YouTube profile for user {user_id}")
            return

        # Decrypt credentials
        try:
            credentials = credential_service.decrypt_credentials(profile.encrypted_credentials)
        except Exception as e:
            print(f"Failed to decrypt credentials: {e}")
            return

        # Create collector and collect videos
        collector = YouTubeCollector(api_key=credentials["api_key"])

        result = collector.collect_videos(db, channel_uuid, user_uuid)

        if result:
            print(f"✓ Collected videos for {result['channel_name']}: New={result['new_videos']}, Total={result['total_videos']}, Comments={result['comments_collected']}")
        else:
            print(f"✗ Failed to collect videos for channel {channel_id}")

    except Exception as e:
        print(f"Error in YouTube monitoring job: {e}")
    finally:
        db.close()


def add_youtube_monitoring_job(
    channel_id: UUID,
    user_id: UUID,
    interval_seconds: int = 3600
) -> str:
    """
    Add a monitoring job for a YouTube channel.

    Args:
        channel_id: YouTubeChannel UUID
        user_id: User UUID
        interval_seconds: Monitoring interval in seconds

    Returns:
        Job ID
    """
    global scheduler

    if scheduler is None:
        raise RuntimeError("Scheduler not started")

    job_id = f"youtube_monitor_{channel_id}"

    # Remove existing job if any
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    # Add new job
    scheduler.add_job(
        func=youtube_monitoring_job,
        trigger='interval',
        seconds=interval_seconds,
        args=[str(channel_id), str(user_id)],
        id=job_id,
        replace_existing=True
    )

    print(f"✓ Added YouTube monitoring job for channel {channel_id} (interval: {interval_seconds}s)")

    return job_id


def remove_youtube_monitoring_job(channel_id: UUID) -> bool:
    """
    Remove a monitoring job for a YouTube channel.

    Args:
        channel_id: YouTubeChannel UUID

    Returns:
        True if job was removed, False if job didn't exist
    """
    global scheduler

    if scheduler is None:
        return False

    job_id = f"youtube_monitor_{channel_id}"

    try:
        scheduler.remove_job(job_id)
        print(f"✓ Removed YouTube monitoring job for channel {channel_id}")
        return True
    except:
        return False


# ============================================
# Reddit Monitoring Job Management
# ============================================

def reddit_monitoring_job(subreddit_id: str, user_id: str):
    """
    Background job to monitor a Reddit subreddit.

    Args:
        subreddit_id: RedditSubreddit UUID as string
        user_id: User UUID as string
    """
    db = SessionLocal()
    try:
        # Convert string UUIDs to UUID objects
        subreddit_uuid = UUID(subreddit_id)
        user_uuid = UUID(user_id)

        # Get Reddit subreddit
        subreddit = db.query(RedditSubreddit).filter(RedditSubreddit.id == subreddit_uuid).first()
        if not subreddit or not subreddit.is_monitoring:
            return

        # Get user's active Reddit profile
        profile = db.query(APIProfile).filter(
            APIProfile.user_id == user_uuid,
            APIProfile.platform == "reddit",
            APIProfile.is_active == True
        ).first()

        if not profile:
            print(f"No active Reddit profile for user {user_id}")
            return

        # Decrypt credentials
        try:
            credentials = credential_service.decrypt_credentials(profile.encrypted_credentials)
        except Exception as e:
            print(f"Failed to decrypt credentials: {e}")
            return

        # Create collector and collect posts
        collector = RedditCollector(
            client_id=credentials["client_id"],
            client_secret=credentials["client_secret"],
            user_agent=credentials["user_agent"]
        )

        result = collector.collect_posts(db, subreddit_uuid, user_uuid)

        if result:
            print(f"✓ Collected posts for r/{result['subreddit_name']}: New={result['new_posts']}, Total={result['total_posts']}, Comments={result['comments_collected']}")
        else:
            print(f"✗ Failed to collect posts for subreddit {subreddit_id}")

    except Exception as e:
        print(f"Error in Reddit monitoring job: {e}")
    finally:
        db.close()


def add_reddit_monitoring_job(
    subreddit_id: UUID,
    user_id: UUID,
    interval_seconds: int = 1800
) -> str:
    """
    Add a monitoring job for a Reddit subreddit.

    Args:
        subreddit_id: RedditSubreddit UUID
        user_id: User UUID
        interval_seconds: Monitoring interval in seconds

    Returns:
        Job ID
    """
    global scheduler

    if scheduler is None:
        raise RuntimeError("Scheduler not started")

    job_id = f"reddit_monitor_{subreddit_id}"

    # Remove existing job if any
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    # Add new job
    scheduler.add_job(
        func=reddit_monitoring_job,
        trigger='interval',
        seconds=interval_seconds,
        args=[str(subreddit_id), str(user_id)],
        id=job_id,
        replace_existing=True
    )

    print(f"✓ Added Reddit monitoring job for subreddit {subreddit_id} (interval: {interval_seconds}s)")

    return job_id


def remove_reddit_monitoring_job(subreddit_id: UUID) -> bool:
    """
    Remove a monitoring job for a Reddit subreddit.

    Args:
        subreddit_id: RedditSubreddit UUID

    Returns:
        True if job was removed, False if job didn't exist
    """
    global scheduler

    if scheduler is None:
        return False

    job_id = f"reddit_monitor_{subreddit_id}"

    try:
        scheduler.remove_job(job_id)
        print(f"✓ Removed Reddit monitoring job for subreddit {subreddit_id}")
        return True
    except:
        return False
