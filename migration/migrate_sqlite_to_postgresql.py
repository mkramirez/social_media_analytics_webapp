"""
Data Migration Script: SQLite (Desktop App) → PostgreSQL (Web App)

This script migrates data from the desktop application's SQLite databases
to the web application's PostgreSQL database.

Usage:
    python migrate_sqlite_to_postgresql.py --user-email user@example.com --sqlite-dir /path/to/desktop/app/data

Prerequisites:
    - User must already be registered in the web app
    - User must have set up API credential profiles
    - SQLite database files must be accessible
"""

import sqlite3
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import psycopg2

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.database import Base
from app.models.user import User
from app.models.api_profile import APIProfile
from app.models.platforms.twitch import TwitchChannel, TwitchStreamRecord
from app.models.platforms.twitter import TwitterUser, Tweet
from app.models.platforms.youtube import YouTubeChannel, YouTubeVideo
from app.models.platforms.reddit import RedditSubreddit, RedditPost

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataMigration:
    """Handles migration from SQLite to PostgreSQL."""

    def __init__(self, postgres_url: str, sqlite_dir: Path, user_email: str):
        """
        Initialize migration.

        Args:
            postgres_url: PostgreSQL connection URL
            sqlite_dir: Directory containing SQLite databases
            user_email: Email of user to migrate data for
        """
        self.postgres_url = postgres_url
        self.sqlite_dir = Path(sqlite_dir)
        self.user_email = user_email

        # Connect to PostgreSQL
        self.pg_engine = create_engine(postgres_url)
        SessionLocal = sessionmaker(bind=self.pg_engine)
        self.pg_session: Session = SessionLocal()

        # Get user
        self.user = self.pg_session.query(User).filter(User.email == user_email).first()
        if not self.user:
            raise ValueError(f"User with email {user_email} not found in database")

        logger.info(f"Migrating data for user: {self.user.email} (ID: {self.user.id})")

        # Statistics
        self.stats = {
            "twitch_channels": 0,
            "twitch_records": 0,
            "twitter_users": 0,
            "tweets": 0,
            "youtube_channels": 0,
            "youtube_videos": 0,
            "reddit_subreddits": 0,
            "reddit_posts": 0
        }

    def connect_sqlite(self, db_name: str) -> sqlite3.Connection:
        """Connect to SQLite database."""
        db_path = self.sqlite_dir / f"{db_name}.db"
        if not db_path.exists():
            logger.warning(f"SQLite database not found: {db_path}")
            return None

        logger.info(f"Connecting to SQLite database: {db_path}")
        return sqlite3.connect(db_path)

    def get_profile_for_platform(self, platform: str) -> APIProfile:
        """Get user's API profile for platform."""
        profile = self.pg_session.query(APIProfile).filter(
            APIProfile.user_id == self.user.id,
            APIProfile.platform == platform
        ).first()

        if not profile:
            raise ValueError(
                f"No API profile found for platform '{platform}'. "
                f"Please create one in the web app first."
            )

        return profile

    def migrate_twitch_data(self):
        """Migrate Twitch data."""
        logger.info("Starting Twitch data migration...")

        conn = self.connect_sqlite("twitch_data")
        if not conn:
            return

        try:
            profile = self.get_profile_for_platform("twitch")

            # Get Twitch channels
            cursor = conn.execute("SELECT channel_name, broadcaster_id, added_at FROM channels")
            channels_map = {}

            for row in cursor:
                channel_name, broadcaster_id, added_at = row

                # Check if channel already exists
                existing = self.pg_session.query(TwitchChannel).filter(
                    TwitchChannel.user_id == self.user.id,
                    TwitchChannel.channel_name == channel_name
                ).first()

                if existing:
                    logger.info(f"Twitch channel already exists: {channel_name}")
                    channels_map[channel_name] = existing
                    continue

                # Create channel
                channel = TwitchChannel(
                    user_id=self.user.id,
                    profile_id=profile.id,
                    channel_name=channel_name,
                    broadcaster_id=broadcaster_id or "",
                    created_at=datetime.fromisoformat(added_at) if added_at else datetime.utcnow()
                )

                self.pg_session.add(channel)
                self.pg_session.flush()
                channels_map[channel_name] = channel
                self.stats["twitch_channels"] += 1
                logger.info(f"Migrated Twitch channel: {channel_name}")

            # Get stream records
            record_cursor = conn.execute("""
                SELECT channel_name, stream_id, title, game_name, viewer_count,
                       started_at, ended_at, recorded_at, is_live
                FROM stream_records
            """)

            for row in record_cursor:
                (channel_name, stream_id, title, game_name, viewer_count,
                 started_at, ended_at, recorded_at, is_live) = row

                if channel_name not in channels_map:
                    logger.warning(f"Channel not found for record: {channel_name}")
                    continue

                channel = channels_map[channel_name]

                # Check if record already exists
                existing = self.pg_session.query(TwitchStreamRecord).filter(
                    TwitchStreamRecord.channel_id == channel.id,
                    TwitchStreamRecord.stream_id == stream_id
                ).first()

                if existing:
                    continue

                # Create record
                record = TwitchStreamRecord(
                    channel_id=channel.id,
                    stream_id=stream_id or "",
                    title=title or "",
                    game_name=game_name or "",
                    viewer_count=viewer_count or 0,
                    started_at=datetime.fromisoformat(started_at) if started_at else datetime.utcnow(),
                    ended_at=datetime.fromisoformat(ended_at) if ended_at else None,
                    is_live=bool(is_live),
                    recorded_at=datetime.fromisoformat(recorded_at) if recorded_at else datetime.utcnow()
                )

                self.pg_session.add(record)
                self.stats["twitch_records"] += 1

            self.pg_session.commit()
            logger.info(f"Twitch migration complete: {self.stats['twitch_channels']} channels, "
                       f"{self.stats['twitch_records']} records")

        except Exception as e:
            logger.error(f"Error migrating Twitch data: {e}")
            self.pg_session.rollback()
            raise
        finally:
            conn.close()

    def migrate_twitter_data(self):
        """Migrate Twitter data."""
        logger.info("Starting Twitter data migration...")

        conn = self.connect_sqlite("twitter_data")
        if not conn:
            return

        try:
            profile = self.get_profile_for_platform("twitter")

            # Get Twitter users
            cursor = conn.execute("SELECT username, twitter_user_id, added_at FROM users")
            users_map = {}

            for row in cursor:
                username, twitter_user_id, added_at = row

                # Check if user already exists
                existing = self.pg_session.query(TwitterUser).filter(
                    TwitterUser.user_id == self.user.id,
                    TwitterUser.username == username
                ).first()

                if existing:
                    logger.info(f"Twitter user already exists: {username}")
                    users_map[username] = existing
                    continue

                # Create user
                twitter_user = TwitterUser(
                    user_id=self.user.id,
                    profile_id=profile.id,
                    username=username,
                    twitter_user_id=twitter_user_id or "",
                    created_at=datetime.fromisoformat(added_at) if added_at else datetime.utcnow()
                )

                self.pg_session.add(twitter_user)
                self.pg_session.flush()
                users_map[username] = twitter_user
                self.stats["twitter_users"] += 1
                logger.info(f"Migrated Twitter user: {username}")

            # Get tweets
            tweet_cursor = conn.execute("""
                SELECT username, tweet_id, text, created_at, likes, retweets, replies, fetched_at
                FROM tweets
            """)

            for row in tweet_cursor:
                (username, tweet_id, text, created_at, likes, retweets, replies, fetched_at) = row

                if username not in users_map:
                    logger.warning(f"Twitter user not found for tweet: {username}")
                    continue

                twitter_user = users_map[username]

                # Check if tweet already exists
                existing = self.pg_session.query(Tweet).filter(
                    Tweet.twitter_user_id == twitter_user.id,
                    Tweet.tweet_id == tweet_id
                ).first()

                if existing:
                    continue

                # Create tweet
                tweet = Tweet(
                    twitter_user_id=twitter_user.id,
                    tweet_id=tweet_id,
                    text=text or "",
                    created_at=datetime.fromisoformat(created_at) if created_at else datetime.utcnow(),
                    likes=likes or 0,
                    retweets=retweets or 0,
                    replies=replies or 0,
                    fetched_at=datetime.fromisoformat(fetched_at) if fetched_at else datetime.utcnow()
                )

                self.pg_session.add(tweet)
                self.stats["tweets"] += 1

            self.pg_session.commit()
            logger.info(f"Twitter migration complete: {self.stats['twitter_users']} users, "
                       f"{self.stats['tweets']} tweets")

        except Exception as e:
            logger.error(f"Error migrating Twitter data: {e}")
            self.pg_session.rollback()
            raise
        finally:
            conn.close()

    def migrate_youtube_data(self):
        """Migrate YouTube data."""
        logger.info("Starting YouTube data migration...")

        conn = self.connect_sqlite("youtube_data")
        if not conn:
            return

        try:
            profile = self.get_profile_for_platform("youtube")

            # Get YouTube channels
            cursor = conn.execute("SELECT channel_name, channel_id, added_at FROM channels")
            channels_map = {}

            for row in cursor:
                channel_name, channel_id_val, added_at = row

                # Check if channel already exists
                existing = self.pg_session.query(YouTubeChannel).filter(
                    YouTubeChannel.user_id == self.user.id,
                    YouTubeChannel.channel_id == channel_id_val
                ).first()

                if existing:
                    logger.info(f"YouTube channel already exists: {channel_name}")
                    channels_map[channel_id_val] = existing
                    continue

                # Create channel
                channel = YouTubeChannel(
                    user_id=self.user.id,
                    profile_id=profile.id,
                    channel_name=channel_name or "",
                    channel_id=channel_id_val,
                    created_at=datetime.fromisoformat(added_at) if added_at else datetime.utcnow()
                )

                self.pg_session.add(channel)
                self.pg_session.flush()
                channels_map[channel_id_val] = channel
                self.stats["youtube_channels"] += 1
                logger.info(f"Migrated YouTube channel: {channel_name}")

            # Get videos
            video_cursor = conn.execute("""
                SELECT channel_id, video_id, title, description, published_at,
                       view_count, like_count, comment_count, fetched_at
                FROM videos
            """)

            for row in video_cursor:
                (channel_id_val, video_id, title, description, published_at,
                 view_count, like_count, comment_count, fetched_at) = row

                if channel_id_val not in channels_map:
                    logger.warning(f"Channel not found for video: {channel_id_val}")
                    continue

                channel = channels_map[channel_id_val]

                # Check if video already exists
                existing = self.pg_session.query(YouTubeVideo).filter(
                    YouTubeVideo.channel_id == channel.id,
                    YouTubeVideo.video_id == video_id
                ).first()

                if existing:
                    continue

                # Create video
                video = YouTubeVideo(
                    channel_id=channel.id,
                    video_id=video_id,
                    title=title or "",
                    description=description or "",
                    published_at=datetime.fromisoformat(published_at) if published_at else datetime.utcnow(),
                    view_count=view_count or 0,
                    like_count=like_count or 0,
                    comment_count=comment_count or 0,
                    fetched_at=datetime.fromisoformat(fetched_at) if fetched_at else datetime.utcnow()
                )

                self.pg_session.add(video)
                self.stats["youtube_videos"] += 1

            self.pg_session.commit()
            logger.info(f"YouTube migration complete: {self.stats['youtube_channels']} channels, "
                       f"{self.stats['youtube_videos']} videos")

        except Exception as e:
            logger.error(f"Error migrating YouTube data: {e}")
            self.pg_session.rollback()
            raise
        finally:
            conn.close()

    def migrate_reddit_data(self):
        """Migrate Reddit data."""
        logger.info("Starting Reddit data migration...")

        conn = self.connect_sqlite("reddit_data")
        if not conn:
            return

        try:
            profile = self.get_profile_for_platform("reddit")

            # Get subreddits
            cursor = conn.execute("SELECT subreddit_name, added_at FROM subreddits")
            subreddits_map = {}

            for row in cursor:
                subreddit_name, added_at = row

                # Check if subreddit already exists
                existing = self.pg_session.query(RedditSubreddit).filter(
                    RedditSubreddit.user_id == self.user.id,
                    RedditSubreddit.subreddit_name == subreddit_name
                ).first()

                if existing:
                    logger.info(f"Reddit subreddit already exists: {subreddit_name}")
                    subreddits_map[subreddit_name] = existing
                    continue

                # Create subreddit
                subreddit = RedditSubreddit(
                    user_id=self.user.id,
                    profile_id=profile.id,
                    subreddit_name=subreddit_name,
                    created_at=datetime.fromisoformat(added_at) if added_at else datetime.utcnow()
                )

                self.pg_session.add(subreddit)
                self.pg_session.flush()
                subreddits_map[subreddit_name] = subreddit
                self.stats["reddit_subreddits"] += 1
                logger.info(f"Migrated Reddit subreddit: {subreddit_name}")

            # Get posts
            post_cursor = conn.execute("""
                SELECT subreddit_name, post_id, title, content, author, created_at,
                       score, num_comments, upvote_ratio, fetched_at
                FROM posts
            """)

            for row in post_cursor:
                (subreddit_name, post_id, title, content, author, created_at,
                 score, num_comments, upvote_ratio, fetched_at) = row

                if subreddit_name not in subreddits_map:
                    logger.warning(f"Subreddit not found for post: {subreddit_name}")
                    continue

                subreddit = subreddits_map[subreddit_name]

                # Check if post already exists
                existing = self.pg_session.query(RedditPost).filter(
                    RedditPost.subreddit_id == subreddit.id,
                    RedditPost.post_id == post_id
                ).first()

                if existing:
                    continue

                # Create post
                post = RedditPost(
                    subreddit_id=subreddit.id,
                    post_id=post_id,
                    title=title or "",
                    content=content or "",
                    author=author or "",
                    created_at=datetime.fromisoformat(created_at) if created_at else datetime.utcnow(),
                    score=score or 0,
                    num_comments=num_comments or 0,
                    upvote_ratio=upvote_ratio or 0.5,
                    fetched_at=datetime.fromisoformat(fetched_at) if fetched_at else datetime.utcnow()
                )

                self.pg_session.add(post)
                self.stats["reddit_posts"] += 1

            self.pg_session.commit()
            logger.info(f"Reddit migration complete: {self.stats['reddit_subreddits']} subreddits, "
                       f"{self.stats['reddit_posts']} posts")

        except Exception as e:
            logger.error(f"Error migrating Reddit data: {e}")
            self.pg_session.rollback()
            raise
        finally:
            conn.close()

    def run(self):
        """Run complete migration."""
        logger.info("=" * 60)
        logger.info("Starting Data Migration: SQLite → PostgreSQL")
        logger.info("=" * 60)

        start_time = datetime.now()

        try:
            self.migrate_twitch_data()
            self.migrate_twitter_data()
            self.migrate_youtube_data()
            self.migrate_reddit_data()

            duration = (datetime.now() - start_time).total_seconds()

            logger.info("=" * 60)
            logger.info("Migration Complete!")
            logger.info("=" * 60)
            logger.info(f"Duration: {duration:.2f} seconds")
            logger.info(f"Statistics:")
            logger.info(f"  Twitch: {self.stats['twitch_channels']} channels, {self.stats['twitch_records']} records")
            logger.info(f"  Twitter: {self.stats['twitter_users']} users, {self.stats['tweets']} tweets")
            logger.info(f"  YouTube: {self.stats['youtube_channels']} channels, {self.stats['youtube_videos']} videos")
            logger.info(f"  Reddit: {self.stats['reddit_subreddits']} subreddits, {self.stats['reddit_posts']} posts")

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise
        finally:
            self.pg_session.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Migrate data from SQLite to PostgreSQL")
    parser.add_argument("--user-email", required=True, help="User email address")
    parser.add_argument("--sqlite-dir", required=True, help="Directory containing SQLite databases")
    parser.add_argument("--postgres-url", help="PostgreSQL connection URL (or set DATABASE_URL env var)")

    args = parser.parse_args()

    # Get PostgreSQL URL
    postgres_url = args.postgres_url
    if not postgres_url:
        import os
        postgres_url = os.getenv("DATABASE_URL")
        if not postgres_url:
            logger.error("PostgreSQL URL not provided. Use --postgres-url or set DATABASE_URL environment variable")
            sys.exit(1)

    # Run migration
    migration = DataMigration(
        postgres_url=postgres_url,
        sqlite_dir=Path(args.sqlite_dir),
        user_email=args.user_email
    )

    migration.run()


if __name__ == "__main__":
    main()
