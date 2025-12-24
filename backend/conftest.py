"""
Pytest configuration and shared fixtures for Social Media Analytics Platform tests.
"""

import os
import pytest
from typing import Generator, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
import redis
from unittest.mock import Mock, MagicMock

from app.main import app
from app.database import Base, get_db
from app.models.user import User
from app.models.api_profile import APIProfile
from app.models.platforms.twitch import TwitchChannel, TwitchStreamRecord
from app.models.platforms.twitter import TwitterUser, Tweet
from app.models.platforms.youtube import YouTubeChannel, YouTubeVideo
from app.models.platforms.reddit import RedditSubreddit, RedditPost
from app.auth import get_password_hash, create_access_token
from app.services.redis_service import get_redis_client


# Database setup
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:
    """
    Create a fresh in-memory SQLite database for each test.
    """
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db: Session) -> TestClient:
    """
    Create a test client with overridden database dependency.
    """
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# User fixtures
@pytest.fixture
def test_user(test_db: Session) -> User:
    """
    Create a test user.
    """
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        is_active=True,
        is_verified=True,
        created_at=datetime.utcnow()
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_user2(test_db: Session) -> User:
    """
    Create a second test user for multi-user tests.
    """
    user = User(
        email="test2@example.com",
        hashed_password=get_password_hash("testpassword456"),
        is_active=True,
        is_verified=True,
        created_at=datetime.utcnow()
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> Dict[str, str]:
    """
    Create authentication headers with JWT token.
    """
    access_token = create_access_token(data={"sub": test_user.email})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def auth_headers2(test_user2: User) -> Dict[str, str]:
    """
    Create authentication headers for second user.
    """
    access_token = create_access_token(data={"sub": test_user2.email})
    return {"Authorization": f"Bearer {access_token}"}


# API Profile fixtures
@pytest.fixture
def twitch_profile(test_db: Session, test_user: User) -> APIProfile:
    """
    Create a Twitch API profile.
    """
    profile = APIProfile(
        user_id=test_user.id,
        platform="twitch",
        profile_name="Test Twitch Profile",
        client_id="test_client_id",
        client_secret="test_client_secret",
        created_at=datetime.utcnow()
    )
    test_db.add(profile)
    test_db.commit()
    test_db.refresh(profile)
    return profile


@pytest.fixture
def twitter_profile(test_db: Session, test_user: User) -> APIProfile:
    """
    Create a Twitter API profile.
    """
    profile = APIProfile(
        user_id=test_user.id,
        platform="twitter",
        profile_name="Test Twitter Profile",
        bearer_token="test_bearer_token",
        created_at=datetime.utcnow()
    )
    test_db.add(profile)
    test_db.commit()
    test_db.refresh(profile)
    return profile


@pytest.fixture
def youtube_profile(test_db: Session, test_user: User) -> APIProfile:
    """
    Create a YouTube API profile.
    """
    profile = APIProfile(
        user_id=test_user.id,
        platform="youtube",
        profile_name="Test YouTube Profile",
        api_key="test_api_key",
        created_at=datetime.utcnow()
    )
    test_db.add(profile)
    test_db.commit()
    test_db.refresh(profile)
    return profile


@pytest.fixture
def reddit_profile(test_db: Session, test_user: User) -> APIProfile:
    """
    Create a Reddit API profile.
    """
    profile = APIProfile(
        user_id=test_user.id,
        platform="reddit",
        profile_name="Test Reddit Profile",
        client_id="test_reddit_client_id",
        client_secret="test_reddit_client_secret",
        user_agent="test_user_agent",
        created_at=datetime.utcnow()
    )
    test_db.add(profile)
    test_db.commit()
    test_db.refresh(profile)
    return profile


# Platform entity fixtures
@pytest.fixture
def twitch_channel(test_db: Session, test_user: User, twitch_profile: APIProfile) -> TwitchChannel:
    """
    Create a Twitch channel.
    """
    channel = TwitchChannel(
        user_id=test_user.id,
        profile_id=twitch_profile.id,
        channel_name="test_streamer",
        broadcaster_id="12345",
        created_at=datetime.utcnow()
    )
    test_db.add(channel)
    test_db.commit()
    test_db.refresh(channel)
    return channel


@pytest.fixture
def twitch_stream_records(test_db: Session, twitch_channel: TwitchChannel) -> list:
    """
    Create sample Twitch stream records.
    """
    records = []
    for i in range(5):
        record = TwitchStreamRecord(
            channel_id=twitch_channel.id,
            stream_id=f"stream_{i}",
            title=f"Test Stream {i}",
            game_name="Test Game",
            viewer_count=100 + i * 10,
            started_at=datetime.utcnow() - timedelta(hours=i),
            is_live=(i == 0),
            recorded_at=datetime.utcnow()
        )
        records.append(record)
        test_db.add(record)

    test_db.commit()
    for record in records:
        test_db.refresh(record)

    return records


@pytest.fixture
def twitter_user_entity(test_db: Session, test_user: User, twitter_profile: APIProfile) -> TwitterUser:
    """
    Create a Twitter user entity.
    """
    twitter_user = TwitterUser(
        user_id=test_user.id,
        profile_id=twitter_profile.id,
        username="test_twitter_user",
        twitter_user_id="9876543210",
        created_at=datetime.utcnow()
    )
    test_db.add(twitter_user)
    test_db.commit()
    test_db.refresh(twitter_user)
    return twitter_user


@pytest.fixture
def tweets(test_db: Session, twitter_user_entity: TwitterUser) -> list:
    """
    Create sample tweets.
    """
    tweets = []
    for i in range(5):
        tweet = Tweet(
            twitter_user_id=twitter_user_entity.id,
            tweet_id=f"tweet_{i}",
            text=f"Test tweet {i} with some content",
            created_at=datetime.utcnow() - timedelta(days=i),
            likes=10 + i * 5,
            retweets=5 + i * 2,
            replies=2 + i,
            fetched_at=datetime.utcnow()
        )
        tweets.append(tweet)
        test_db.add(tweet)

    test_db.commit()
    for tweet in tweets:
        test_db.refresh(tweet)

    return tweets


@pytest.fixture
def youtube_channel_entity(test_db: Session, test_user: User, youtube_profile: APIProfile) -> YouTubeChannel:
    """
    Create a YouTube channel entity.
    """
    channel = YouTubeChannel(
        user_id=test_user.id,
        profile_id=youtube_profile.id,
        channel_name="Test YouTube Channel",
        channel_id="UC_test_channel_id",
        created_at=datetime.utcnow()
    )
    test_db.add(channel)
    test_db.commit()
    test_db.refresh(channel)
    return channel


@pytest.fixture
def youtube_videos(test_db: Session, youtube_channel_entity: YouTubeChannel) -> list:
    """
    Create sample YouTube videos.
    """
    videos = []
    for i in range(5):
        video = YouTubeVideo(
            channel_id=youtube_channel_entity.id,
            video_id=f"video_{i}",
            title=f"Test Video {i}",
            description=f"Test video description {i}",
            published_at=datetime.utcnow() - timedelta(days=i),
            view_count=1000 + i * 100,
            like_count=50 + i * 10,
            comment_count=20 + i * 5,
            fetched_at=datetime.utcnow()
        )
        videos.append(video)
        test_db.add(video)

    test_db.commit()
    for video in videos:
        test_db.refresh(video)

    return videos


@pytest.fixture
def reddit_subreddit_entity(test_db: Session, test_user: User, reddit_profile: APIProfile) -> RedditSubreddit:
    """
    Create a Reddit subreddit entity.
    """
    subreddit = RedditSubreddit(
        user_id=test_user.id,
        profile_id=reddit_profile.id,
        subreddit_name="test_subreddit",
        created_at=datetime.utcnow()
    )
    test_db.add(subreddit)
    test_db.commit()
    test_db.refresh(subreddit)
    return subreddit


@pytest.fixture
def reddit_posts(test_db: Session, reddit_subreddit_entity: RedditSubreddit) -> list:
    """
    Create sample Reddit posts.
    """
    posts = []
    for i in range(5):
        post = RedditPost(
            subreddit_id=reddit_subreddit_entity.id,
            post_id=f"post_{i}",
            title=f"Test Post {i}",
            content=f"Test post content {i}",
            author="test_author",
            created_at=datetime.utcnow() - timedelta(days=i),
            score=100 + i * 20,
            num_comments=10 + i * 3,
            upvote_ratio=0.85 + i * 0.02,
            fetched_at=datetime.utcnow()
        )
        posts.append(post)
        test_db.add(post)

    test_db.commit()
    for post in posts:
        test_db.refresh(post)

    return posts


# Mock services
@pytest.fixture
def mock_redis():
    """
    Mock Redis client for tests that don't need real Redis.
    """
    mock = MagicMock(spec=redis.Redis)
    mock.ping.return_value = True
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = 1
    mock.exists.return_value = False
    return mock


@pytest.fixture
def mock_scheduler():
    """
    Mock APScheduler for tests.
    """
    mock = Mock()
    mock.add_job.return_value = Mock(id="test_job_id")
    mock.get_job.return_value = None
    mock.remove_job.return_value = None
    return mock


@pytest.fixture
def mock_secrets_manager():
    """
    Mock AWS Secrets Manager for tests.
    """
    mock = Mock()
    mock.get_secret.return_value = {
        "client_id": "test_client_id",
        "client_secret": "test_client_secret"
    }
    mock.create_secret.return_value = True
    mock.update_secret.return_value = True
    mock.delete_secret.return_value = True
    return mock


# Environment setup
@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """
    Set up test environment variables.
    """
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("DATABASE_URL", SQLALCHEMY_TEST_DATABASE_URL)
    monkeypatch.setenv("SECRET_KEY", "test_secret_key_for_testing_only")
    monkeypatch.setenv("JWT_SECRET_KEY", "test_jwt_secret_key_for_testing_only")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("USE_AWS_SECRETS_MANAGER", "false")


# Helper functions
def create_test_monitoring_job(db: Session, user: User, platform: str, entity_id: int) -> Any:
    """
    Helper to create a monitoring job for testing.
    """
    from app.models.monitoring import MonitoringJob

    job = MonitoringJob(
        user_id=user.id,
        platform=platform,
        entity_id=entity_id,
        job_id=f"test_job_{platform}_{entity_id}",
        interval_minutes=60,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@pytest.fixture
def sample_sentiment_texts() -> list:
    """
    Sample texts for sentiment analysis testing.
    """
    return [
        "This is amazing! I love it!",
        "This is terrible, I hate it.",
        "This is okay, nothing special.",
        "Best product ever! Highly recommend!",
        "Worst experience of my life."
    ]
