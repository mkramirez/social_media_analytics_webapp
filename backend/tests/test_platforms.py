"""
Unit tests for platform endpoints (Twitch, Twitter, YouTube, Reddit).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from app.models.user import User
from app.models.api_profile import APIProfile
from app.models.platforms.twitch import TwitchChannel, TwitchStreamRecord
from app.models.platforms.twitter import TwitterUser, Tweet
from app.models.platforms.youtube import YouTubeChannel, YouTubeVideo
from app.models.platforms.reddit import RedditSubreddit, RedditPost


@pytest.mark.unit
@pytest.mark.platform
class TestTwitchEndpoints:
    """Test Twitch platform endpoints."""

    def test_add_twitch_channel_success(
        self, client: TestClient, auth_headers: dict, twitch_profile: APIProfile, test_db: Session
    ):
        """Test adding a Twitch channel."""
        response = client.post(
            "/api/twitch/channels",
            headers=auth_headers,
            json={
                "profile_id": twitch_profile.id,
                "channel_name": "test_streamer"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["channel_name"] == "test_streamer"
        assert "id" in data

        # Verify in database
        channel = test_db.query(TwitchChannel).filter(
            TwitchChannel.channel_name == "test_streamer"
        ).first()
        assert channel is not None

    def test_add_twitch_channel_duplicate(
        self, client: TestClient, auth_headers: dict, twitch_channel: TwitchChannel
    ):
        """Test adding duplicate Twitch channel fails."""
        response = client.post(
            "/api/twitch/channels",
            headers=auth_headers,
            json={
                "profile_id": twitch_channel.profile_id,
                "channel_name": twitch_channel.channel_name
            }
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_get_twitch_channels(
        self, client: TestClient, auth_headers: dict, twitch_channel: TwitchChannel
    ):
        """Test getting user's Twitch channels."""
        response = client.get("/api/twitch/channels", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["channel_name"] == twitch_channel.channel_name

    def test_get_twitch_channels_isolation(
        self, client: TestClient, auth_headers: dict, auth_headers2: dict,
        twitch_channel: TwitchChannel, test_db: Session, test_user2: User
    ):
        """Test that users can only see their own channels."""
        # User 1's channel already exists (twitch_channel fixture)

        # User 2 should see empty list
        response = client.get("/api/twitch/channels", headers=auth_headers2)
        assert response.status_code == 200
        assert len(response.json()) == 0

    def test_get_twitch_channel_by_id(
        self, client: TestClient, auth_headers: dict, twitch_channel: TwitchChannel
    ):
        """Test getting specific Twitch channel."""
        response = client.get(
            f"/api/twitch/channels/{twitch_channel.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == twitch_channel.id
        assert data["channel_name"] == twitch_channel.channel_name

    def test_get_twitch_channel_not_found(
        self, client: TestClient, auth_headers: dict
    ):
        """Test getting nonexistent channel returns 404."""
        response = client.get("/api/twitch/channels/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_twitch_channel(
        self, client: TestClient, auth_headers: dict, twitch_channel: TwitchChannel, test_db: Session
    ):
        """Test deleting Twitch channel."""
        response = client.delete(
            f"/api/twitch/channels/{twitch_channel.id}",
            headers=auth_headers
        )

        assert response.status_code == 200

        # Verify deleted from database
        channel = test_db.query(TwitchChannel).filter(
            TwitchChannel.id == twitch_channel.id
        ).first()
        assert channel is None

    def test_get_twitch_stream_records(
        self, client: TestClient, auth_headers: dict, twitch_stream_records: list
    ):
        """Test getting stream records for a channel."""
        channel_id = twitch_stream_records[0].channel_id

        response = client.get(
            f"/api/twitch/channels/{channel_id}/records",
            headers=auth_headers,
            params={"days": 7}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
        assert data[0]["stream_id"] == twitch_stream_records[0].stream_id

    @patch("app.services.scheduler_service.scheduler")
    def test_start_twitch_monitoring(
        self, mock_scheduler, client: TestClient, auth_headers: dict,
        twitch_channel: TwitchChannel
    ):
        """Test starting monitoring job for Twitch channel."""
        mock_scheduler.add_job.return_value = Mock(id="test_job_123")

        response = client.post(
            f"/api/twitch/channels/{twitch_channel.id}/start-monitoring",
            headers=auth_headers,
            json={"interval_minutes": 60}
        )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert mock_scheduler.add_job.called

    @patch("app.services.scheduler_service.scheduler")
    def test_stop_twitch_monitoring(
        self, mock_scheduler, client: TestClient, auth_headers: dict,
        twitch_channel: TwitchChannel, test_db: Session
    ):
        """Test stopping monitoring job for Twitch channel."""
        from app.models.monitoring import MonitoringJob

        # Create monitoring job
        job = MonitoringJob(
            user_id=twitch_channel.user_id,
            platform="twitch",
            entity_id=twitch_channel.id,
            job_id="test_job_123",
            interval_minutes=60,
            is_active=True,
            created_at=datetime.utcnow()
        )
        test_db.add(job)
        test_db.commit()

        response = client.post(
            f"/api/twitch/channels/{twitch_channel.id}/stop-monitoring",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert mock_scheduler.remove_job.called


@pytest.mark.unit
@pytest.mark.platform
class TestTwitterEndpoints:
    """Test Twitter platform endpoints."""

    def test_add_twitter_user_success(
        self, client: TestClient, auth_headers: dict, twitter_profile: APIProfile, test_db: Session
    ):
        """Test adding a Twitter user."""
        response = client.post(
            "/api/twitter/users",
            headers=auth_headers,
            json={
                "profile_id": twitter_profile.id,
                "username": "test_twitter_user"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "test_twitter_user"

    def test_get_twitter_users(
        self, client: TestClient, auth_headers: dict, twitter_user_entity: TwitterUser
    ):
        """Test getting user's Twitter users."""
        response = client.get("/api/twitter/users", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["username"] == twitter_user_entity.username

    def test_get_twitter_tweets(
        self, client: TestClient, auth_headers: dict, tweets: list
    ):
        """Test getting tweets for a Twitter user."""
        user_id = tweets[0].twitter_user_id

        response = client.get(
            f"/api/twitter/users/{user_id}/tweets",
            headers=auth_headers,
            params={"days": 7}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
        assert data[0]["tweet_id"] == tweets[0].tweet_id

    def test_get_twitter_engagement_metrics(
        self, client: TestClient, auth_headers: dict, tweets: list
    ):
        """Test getting engagement metrics for tweets."""
        user_id = tweets[0].twitter_user_id

        response = client.get(
            f"/api/twitter/users/{user_id}/engagement",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_likes" in data
        assert "total_retweets" in data
        assert "total_replies" in data
        assert data["total_likes"] > 0

    def test_delete_twitter_user(
        self, client: TestClient, auth_headers: dict, twitter_user_entity: TwitterUser, test_db: Session
    ):
        """Test deleting Twitter user."""
        response = client.delete(
            f"/api/twitter/users/{twitter_user_entity.id}",
            headers=auth_headers
        )

        assert response.status_code == 200

        # Verify deleted (including cascaded tweets)
        user = test_db.query(TwitterUser).filter(
            TwitterUser.id == twitter_user_entity.id
        ).first()
        assert user is None


@pytest.mark.unit
@pytest.mark.platform
class TestYouTubeEndpoints:
    """Test YouTube platform endpoints."""

    def test_add_youtube_channel_success(
        self, client: TestClient, auth_headers: dict, youtube_profile: APIProfile, test_db: Session
    ):
        """Test adding a YouTube channel."""
        response = client.post(
            "/api/youtube/channels",
            headers=auth_headers,
            json={
                "profile_id": youtube_profile.id,
                "channel_id": "UC_test_channel"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["channel_id"] == "UC_test_channel"

    def test_get_youtube_channels(
        self, client: TestClient, auth_headers: dict, youtube_channel_entity: YouTubeChannel
    ):
        """Test getting user's YouTube channels."""
        response = client.get("/api/youtube/channels", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["channel_name"] == youtube_channel_entity.channel_name

    def test_get_youtube_videos(
        self, client: TestClient, auth_headers: dict, youtube_videos: list
    ):
        """Test getting videos for a YouTube channel."""
        channel_id = youtube_videos[0].channel_id

        response = client.get(
            f"/api/youtube/channels/{channel_id}/videos",
            headers=auth_headers,
            params={"days": 30}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
        assert data[0]["video_id"] == youtube_videos[0].video_id

    def test_get_youtube_analytics(
        self, client: TestClient, auth_headers: dict, youtube_videos: list
    ):
        """Test getting analytics for YouTube channel."""
        channel_id = youtube_videos[0].channel_id

        response = client.get(
            f"/api/youtube/channels/{channel_id}/analytics",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_views" in data
        assert "total_likes" in data
        assert "total_comments" in data
        assert data["total_views"] > 0

    def test_get_youtube_top_videos(
        self, client: TestClient, auth_headers: dict, youtube_videos: list
    ):
        """Test getting top videos by views."""
        channel_id = youtube_videos[0].channel_id

        response = client.get(
            f"/api/youtube/channels/{channel_id}/top-videos",
            headers=auth_headers,
            params={"limit": 3}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 3
        # Should be sorted by views descending
        if len(data) > 1:
            assert data[0]["view_count"] >= data[1]["view_count"]


@pytest.mark.unit
@pytest.mark.platform
class TestRedditEndpoints:
    """Test Reddit platform endpoints."""

    def test_add_reddit_subreddit_success(
        self, client: TestClient, auth_headers: dict, reddit_profile: APIProfile, test_db: Session
    ):
        """Test adding a Reddit subreddit."""
        response = client.post(
            "/api/reddit/subreddits",
            headers=auth_headers,
            json={
                "profile_id": reddit_profile.id,
                "subreddit_name": "test_subreddit"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["subreddit_name"] == "test_subreddit"

    def test_get_reddit_subreddits(
        self, client: TestClient, auth_headers: dict, reddit_subreddit_entity: RedditSubreddit
    ):
        """Test getting user's Reddit subreddits."""
        response = client.get("/api/reddit/subreddits", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["subreddit_name"] == reddit_subreddit_entity.subreddit_name

    def test_get_reddit_posts(
        self, client: TestClient, auth_headers: dict, reddit_posts: list
    ):
        """Test getting posts for a subreddit."""
        subreddit_id = reddit_posts[0].subreddit_id

        response = client.get(
            f"/api/reddit/subreddits/{subreddit_id}/posts",
            headers=auth_headers,
            params={"days": 7}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
        assert data[0]["post_id"] == reddit_posts[0].post_id

    def test_get_reddit_top_posts(
        self, client: TestClient, auth_headers: dict, reddit_posts: list
    ):
        """Test getting top posts by score."""
        subreddit_id = reddit_posts[0].subreddit_id

        response = client.get(
            f"/api/reddit/subreddits/{subreddit_id}/top-posts",
            headers=auth_headers,
            params={"limit": 3}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 3
        # Should be sorted by score descending
        if len(data) > 1:
            assert data[0]["score"] >= data[1]["score"]

    def test_get_reddit_statistics(
        self, client: TestClient, auth_headers: dict, reddit_posts: list
    ):
        """Test getting subreddit statistics."""
        subreddit_id = reddit_posts[0].subreddit_id

        response = client.get(
            f"/api/reddit/subreddits/{subreddit_id}/statistics",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_posts" in data
        assert "total_score" in data
        assert "total_comments" in data
        assert "average_upvote_ratio" in data
        assert data["total_posts"] == 5


@pytest.mark.unit
@pytest.mark.platform
class TestAPIProfiles:
    """Test API profile management endpoints."""

    def test_create_api_profile_success(
        self, client: TestClient, auth_headers: dict, test_db: Session
    ):
        """Test creating an API profile."""
        response = client.post(
            "/api/profiles",
            headers=auth_headers,
            json={
                "platform": "twitch",
                "profile_name": "My Twitch Profile",
                "client_id": "test_client_id",
                "client_secret": "test_client_secret"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["platform"] == "twitch"
        assert data["profile_name"] == "My Twitch Profile"
        assert "client_secret" not in data  # Should not expose secrets

    def test_get_api_profiles(
        self, client: TestClient, auth_headers: dict, twitch_profile: APIProfile,
        twitter_profile: APIProfile
    ):
        """Test getting user's API profiles."""
        response = client.get("/api/profiles", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        platforms = [p["platform"] for p in data]
        assert "twitch" in platforms
        assert "twitter" in platforms

    def test_get_api_profile_by_platform(
        self, client: TestClient, auth_headers: dict, twitch_profile: APIProfile
    ):
        """Test getting profiles for specific platform."""
        response = client.get(
            "/api/profiles",
            headers=auth_headers,
            params={"platform": "twitch"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["platform"] == "twitch"

    def test_update_api_profile(
        self, client: TestClient, auth_headers: dict, twitch_profile: APIProfile, test_db: Session
    ):
        """Test updating an API profile."""
        response = client.put(
            f"/api/profiles/{twitch_profile.id}",
            headers=auth_headers,
            json={
                "profile_name": "Updated Profile Name",
                "client_id": "new_client_id"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["profile_name"] == "Updated Profile Name"

        # Verify in database
        test_db.refresh(twitch_profile)
        assert twitch_profile.profile_name == "Updated Profile Name"

    def test_delete_api_profile(
        self, client: TestClient, auth_headers: dict, twitch_profile: APIProfile, test_db: Session
    ):
        """Test deleting an API profile."""
        response = client.delete(
            f"/api/profiles/{twitch_profile.id}",
            headers=auth_headers
        )

        assert response.status_code == 200

        # Verify deleted
        profile = test_db.query(APIProfile).filter(
            APIProfile.id == twitch_profile.id
        ).first()
        assert profile is None

    def test_api_profile_isolation(
        self, client: TestClient, auth_headers: dict, auth_headers2: dict,
        twitch_profile: APIProfile
    ):
        """Test that users can only access their own profiles."""
        # User 1's profile exists (twitch_profile)

        # User 2 tries to access User 1's profile
        response = client.get(
            f"/api/profiles/{twitch_profile.id}",
            headers=auth_headers2
        )

        assert response.status_code == 404  # Not found (for user 2)


@pytest.mark.unit
@pytest.mark.platform
class TestBulkOperations:
    """Test bulk operations for platforms."""

    def test_bulk_add_twitter_users(
        self, client: TestClient, auth_headers: dict, twitter_profile: APIProfile, test_db: Session
    ):
        """Test bulk adding Twitter users."""
        response = client.post(
            "/api/twitter/users/bulk",
            headers=auth_headers,
            json={
                "profile_id": twitter_profile.id,
                "usernames": ["user1", "user2", "user3"]
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["created"]) == 3
        assert len(data["failed"]) == 0

    def test_bulk_add_with_duplicates(
        self, client: TestClient, auth_headers: dict, twitter_user_entity: TwitterUser,
        twitter_profile: APIProfile
    ):
        """Test bulk adding with some duplicates."""
        response = client.post(
            "/api/twitter/users/bulk",
            headers=auth_headers,
            json={
                "profile_id": twitter_profile.id,
                "usernames": [twitter_user_entity.username, "new_user1", "new_user2"]
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["created"]) == 2  # Only new users
        assert len(data["failed"]) == 1  # Duplicate

    def test_bulk_delete_reddit_posts(
        self, client: TestClient, auth_headers: dict, reddit_posts: list, test_db: Session
    ):
        """Test bulk deleting Reddit posts."""
        post_ids = [post.id for post in reddit_posts[:3]]

        response = client.post(
            "/api/reddit/posts/bulk-delete",
            headers=auth_headers,
            json={"post_ids": post_ids}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 3

        # Verify deleted
        remaining = test_db.query(RedditPost).filter(
            RedditPost.id.in_(post_ids)
        ).count()
        assert remaining == 0
