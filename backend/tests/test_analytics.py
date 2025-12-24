"""
Unit tests for analytics and export endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import io
import csv

from app.models.user import User
from app.models.platforms.twitter import Tweet
from app.models.platforms.youtube import YouTubeVideo
from app.models.platforms.reddit import RedditPost
from app.models.platforms.twitch import TwitchStreamRecord


@pytest.mark.unit
@pytest.mark.analytics
class TestSentimentAnalysis:
    """Test sentiment analysis endpoints."""

    @patch("app.analytics.sentiment_analyzer.SentimentAnalyzer.analyze_sentiment")
    def test_analyze_sentiment_single_text(self, mock_analyze, client: TestClient, auth_headers: dict):
        """Test analyzing sentiment of single text."""
        mock_analyze.return_value = {
            "negative": 0.1,
            "neutral": 0.2,
            "positive": 0.7,
            "compound": 0.6
        }

        response = client.post(
            "/api/analytics/sentiment/analyze",
            headers=auth_headers,
            json={"text": "This is amazing! I love it!"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["positive"] == 0.7
        assert data["compound"] == 0.6
        assert mock_analyze.called

    @patch("app.analytics.sentiment_analyzer.SentimentAnalyzer.analyze_batch")
    def test_analyze_sentiment_batch(self, mock_analyze, client: TestClient, auth_headers: dict):
        """Test batch sentiment analysis."""
        mock_analyze.return_value = [
            {"negative": 0.1, "neutral": 0.2, "positive": 0.7, "compound": 0.6},
            {"negative": 0.8, "neutral": 0.1, "positive": 0.1, "compound": -0.5}
        ]

        response = client.post(
            "/api/analytics/sentiment/batch",
            headers=auth_headers,
            json={
                "texts": [
                    "This is amazing!",
                    "This is terrible."
                ]
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["positive"] > data[1]["positive"]

    def test_get_tweet_sentiment(
        self, client: TestClient, auth_headers: dict, tweets: list, test_db: Session
    ):
        """Test getting sentiment analysis for tweets."""
        user_id = tweets[0].twitter_user_id

        with patch("app.analytics.sentiment_analyzer.SentimentAnalyzer.analyze_batch") as mock:
            mock.return_value = [
                {"negative": 0.1, "neutral": 0.3, "positive": 0.6, "compound": 0.5}
                for _ in range(5)
            ]

            response = client.get(
                f"/api/analytics/sentiment/twitter/{user_id}",
                headers=auth_headers,
                params={"days": 7}
            )

        assert response.status_code == 200
        data = response.json()
        assert "average_sentiment" in data
        assert "sentiment_distribution" in data
        assert "tweets" in data
        assert len(data["tweets"]) == 5

    def test_get_platform_sentiment(
        self, client: TestClient, auth_headers: dict, tweets: list
    ):
        """Test getting platform-wide sentiment."""
        with patch("app.analytics.sentiment_analyzer.SentimentAnalyzer.analyze_batch") as mock:
            mock.return_value = [
                {"negative": 0.1, "neutral": 0.3, "positive": 0.6, "compound": 0.5}
                for _ in range(5)
            ]

            response = client.get(
                "/api/analytics/sentiment/platform/twitter",
                headers=auth_headers,
                params={"days": 7}
            )

        assert response.status_code == 200
        data = response.json()
        assert "average_sentiment" in data
        assert "total_analyzed" in data
        assert data["total_analyzed"] == 5


@pytest.mark.unit
@pytest.mark.analytics
class TestEngagementAnalytics:
    """Test engagement analytics endpoints."""

    def test_get_twitter_engagement(
        self, client: TestClient, auth_headers: dict, tweets: list
    ):
        """Test getting Twitter engagement metrics."""
        user_id = tweets[0].twitter_user_id

        response = client.get(
            f"/api/analytics/engagement/twitter/{user_id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_likes" in data
        assert "total_retweets" in data
        assert "total_replies" in data
        assert "average_engagement" in data
        assert "engagement_rate" in data
        assert data["total_likes"] > 0

    def test_get_youtube_engagement(
        self, client: TestClient, auth_headers: dict, youtube_videos: list
    ):
        """Test getting YouTube engagement metrics."""
        channel_id = youtube_videos[0].channel_id

        response = client.get(
            f"/api/analytics/engagement/youtube/{channel_id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_views" in data
        assert "total_likes" in data
        assert "total_comments" in data
        assert "average_views" in data
        assert "like_ratio" in data

    def test_get_reddit_engagement(
        self, client: TestClient, auth_headers: dict, reddit_posts: list
    ):
        """Test getting Reddit engagement metrics."""
        subreddit_id = reddit_posts[0].subreddit_id

        response = client.get(
            f"/api/analytics/engagement/reddit/{subreddit_id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_score" in data
        assert "total_comments" in data
        assert "average_upvote_ratio" in data
        assert "top_posts" in data

    def test_get_cross_platform_engagement(
        self, client: TestClient, auth_headers: dict, tweets: list,
        youtube_videos: list, reddit_posts: list
    ):
        """Test getting cross-platform engagement comparison."""
        response = client.get(
            "/api/analytics/engagement",
            headers=auth_headers,
            params={"days": 30, "platforms": "twitter,youtube,reddit"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "platforms" in data
        platforms = data["platforms"]
        assert "twitter" in platforms
        assert "youtube" in platforms
        assert "reddit" in platforms


@pytest.mark.unit
@pytest.mark.analytics
class TestTrendAnalysis:
    """Test trend analysis endpoints."""

    def test_get_twitter_trends(
        self, client: TestClient, auth_headers: dict, tweets: list
    ):
        """Test getting Twitter trends."""
        user_id = tweets[0].twitter_user_id

        response = client.get(
            f"/api/analytics/trends/twitter/{user_id}",
            headers=auth_headers,
            params={"days": 30}
        )

        assert response.status_code == 200
        data = response.json()
        assert "engagement_trend" in data
        assert "posting_frequency" in data
        assert "growth_rate" in data

    def test_get_youtube_trends(
        self, client: TestClient, auth_headers: dict, youtube_videos: list
    ):
        """Test getting YouTube trends."""
        channel_id = youtube_videos[0].channel_id

        response = client.get(
            f"/api/analytics/trends/youtube/{channel_id}",
            headers=auth_headers,
            params={"days": 30}
        )

        assert response.status_code == 200
        data = response.json()
        assert "view_trend" in data
        assert "subscriber_growth" in data
        assert "upload_frequency" in data

    @patch("app.analytics.trend_analyzer.TrendAnalyzer.forecast")
    def test_get_trend_forecast(
        self, mock_forecast, client: TestClient, auth_headers: dict, tweets: list
    ):
        """Test getting trend forecast."""
        mock_forecast.return_value = {
            "forecast": [100, 110, 120, 130],
            "confidence_interval": [(90, 110), (100, 120), (110, 130), (120, 140)]
        }

        user_id = tweets[0].twitter_user_id

        response = client.get(
            f"/api/analytics/trends/twitter/{user_id}/forecast",
            headers=auth_headers,
            params={"days": 7}
        )

        assert response.status_code == 200
        data = response.json()
        assert "forecast" in data
        assert "confidence_interval" in data
        assert len(data["forecast"]) == 4


@pytest.mark.unit
@pytest.mark.analytics
class TestPostingTimeAnalysis:
    """Test posting time analysis endpoints."""

    def test_get_best_posting_times(
        self, client: TestClient, auth_headers: dict, tweets: list
    ):
        """Test getting best posting times."""
        user_id = tweets[0].twitter_user_id

        response = client.get(
            f"/api/analytics/posting-times/twitter/{user_id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "best_hours" in data
        assert "best_days" in data
        assert "heatmap" in data
        assert len(data["best_hours"]) > 0

    def test_get_posting_time_heatmap(
        self, client: TestClient, auth_headers: dict, tweets: list
    ):
        """Test getting posting time heatmap data."""
        user_id = tweets[0].twitter_user_id

        response = client.get(
            f"/api/analytics/posting-times/twitter/{user_id}/heatmap",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Heatmap should have 7 days × 24 hours = 168 data points
        assert len(data) == 7
        assert all(len(day) == 24 for day in data)


@pytest.mark.unit
@pytest.mark.analytics
class TestAnalyticsDashboard:
    """Test analytics dashboard endpoints."""

    def test_get_dashboard_overview(
        self, client: TestClient, auth_headers: dict, tweets: list,
        youtube_videos: list, reddit_posts: list, twitch_stream_records: list
    ):
        """Test getting dashboard overview with all metrics."""
        with patch("app.analytics.sentiment_analyzer.SentimentAnalyzer.analyze_batch") as mock:
            mock.return_value = [
                {"negative": 0.1, "neutral": 0.3, "positive": 0.6, "compound": 0.5}
                for _ in range(20)
            ]

            response = client.get(
                "/api/analytics/dashboard",
                headers=auth_headers,
                params={"days": 7}
            )

        assert response.status_code == 200
        data = response.json()
        assert "platforms" in data
        assert "total_engagement" in data
        assert "average_sentiment" in data
        assert "top_performers" in data

    def test_get_platform_comparison(
        self, client: TestClient, auth_headers: dict, tweets: list,
        youtube_videos: list, reddit_posts: list
    ):
        """Test getting platform comparison metrics."""
        response = client.get(
            "/api/analytics/comparison",
            headers=auth_headers,
            params={"platforms": "twitter,youtube,reddit", "days": 30}
        )

        assert response.status_code == 200
        data = response.json()
        assert "comparison" in data
        assert len(data["comparison"]) == 3


@pytest.mark.unit
@pytest.mark.analytics
class TestExportEndpoints:
    """Test data export endpoints."""

    def test_export_twitter_csv(
        self, client: TestClient, auth_headers: dict, tweets: list
    ):
        """Test exporting Twitter data to CSV."""
        user_id = tweets[0].twitter_user_id

        response = client.get(
            f"/api/export/csv/twitter/{user_id}",
            headers=auth_headers,
            params={"days": 30}
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"

        # Parse CSV content
        content = response.content.decode("utf-8")
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        assert len(rows) > 1  # Header + data rows
        assert "tweet_id" in rows[0][0].lower() or "Tweet ID" in rows[0]

    def test_export_youtube_csv(
        self, client: TestClient, auth_headers: dict, youtube_videos: list
    ):
        """Test exporting YouTube data to CSV."""
        channel_id = youtube_videos[0].channel_id

        response = client.get(
            f"/api/export/csv/youtube/{channel_id}",
            headers=auth_headers,
            params={"days": 30}
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]

        content = response.content.decode("utf-8")
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        assert len(rows) > 1
        # Check for YouTube-specific columns
        header = rows[0]
        assert any("video" in col.lower() for col in header)
        assert any("view" in col.lower() for col in header)

    def test_export_reddit_csv(
        self, client: TestClient, auth_headers: dict, reddit_posts: list
    ):
        """Test exporting Reddit data to CSV."""
        subreddit_id = reddit_posts[0].subreddit_id

        response = client.get(
            f"/api/export/csv/reddit/{subreddit_id}",
            headers=auth_headers,
            params={"days": 30}
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]

    def test_export_twitch_csv(
        self, client: TestClient, auth_headers: dict, twitch_stream_records: list
    ):
        """Test exporting Twitch data to CSV."""
        channel_id = twitch_stream_records[0].channel_id

        response = client.get(
            f"/api/export/csv/twitch/{channel_id}",
            headers=auth_headers,
            params={"days": 30}
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]

    def test_export_all_platforms_csv(
        self, client: TestClient, auth_headers: dict, tweets: list,
        youtube_videos: list, reddit_posts: list, twitch_stream_records: list
    ):
        """Test exporting all platforms to CSV."""
        response = client.get(
            "/api/export/csv/all",
            headers=auth_headers,
            params={"days": 30}
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]

        # Should include data from all platforms
        content = response.content.decode("utf-8")
        assert len(content) > 100  # Non-empty export

    def test_export_summary_report(
        self, client: TestClient, auth_headers: dict, tweets: list,
        youtube_videos: list
    ):
        """Test exporting summary report."""
        with patch("app.analytics.sentiment_analyzer.SentimentAnalyzer.analyze_batch") as mock:
            mock.return_value = [
                {"negative": 0.1, "neutral": 0.3, "positive": 0.6, "compound": 0.5}
                for _ in range(10)
            ]

            response = client.get(
                "/api/export/summary",
                headers=auth_headers,
                params={"days": 7, "platforms": "twitter,youtube"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "platforms" in data
        assert "total_items" in data
        assert "date_range" in data

    def test_export_analytics_json(
        self, client: TestClient, auth_headers: dict, tweets: list
    ):
        """Test exporting analytics as JSON."""
        user_id = tweets[0].twitter_user_id

        with patch("app.analytics.sentiment_analyzer.SentimentAnalyzer.analyze_batch") as mock:
            mock.return_value = [
                {"negative": 0.1, "neutral": 0.3, "positive": 0.6, "compound": 0.5}
                for _ in range(5)
            ]

            response = client.get(
                f"/api/export/json/twitter/{user_id}",
                headers=auth_headers,
                params={"days": 7, "include_analytics": True}
            )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "analytics" in data
        assert "engagement" in data["analytics"]
        assert "sentiment" in data["analytics"]


@pytest.mark.unit
@pytest.mark.analytics
class TestCachingBehavior:
    """Test analytics caching behavior."""

    def test_sentiment_cache_hit(
        self, client: TestClient, auth_headers: dict, test_db: Session
    ):
        """Test that sentiment results are cached."""
        from app.models.analytics_models import SentimentCache
        import hashlib

        text = "This is a test text for caching"
        text_hash = hashlib.md5(text.encode()).hexdigest()

        # Create cached result
        cached = SentimentCache(
            text_hash=text_hash,
            negative=0.1,
            neutral=0.3,
            positive=0.6,
            compound=0.5,
            created_at=datetime.utcnow()
        )
        test_db.add(cached)
        test_db.commit()

        # Request sentiment analysis
        with patch("app.analytics.sentiment_analyzer.SentimentAnalyzer.analyze_sentiment") as mock:
            response = client.post(
                "/api/analytics/sentiment/analyze",
                headers=auth_headers,
                json={"text": text}
            )

            # Should not call analyzer if cache hit
            assert not mock.called

        assert response.status_code == 200
        data = response.json()
        assert data["positive"] == 0.6

    def test_sentiment_cache_miss(
        self, client: TestClient, auth_headers: dict
    ):
        """Test sentiment analysis when cache misses."""
        with patch("app.analytics.sentiment_analyzer.SentimentAnalyzer.analyze_sentiment") as mock:
            mock.return_value = {
                "negative": 0.2,
                "neutral": 0.3,
                "positive": 0.5,
                "compound": 0.3
            }

            response = client.post(
                "/api/analytics/sentiment/analyze",
                headers=auth_headers,
                json={"text": "New text not in cache"}
            )

            # Should call analyzer on cache miss
            assert mock.called

        assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.analytics
class TestAnalyticsErrorHandling:
    """Test error handling in analytics endpoints."""

    def test_analytics_no_data(
        self, client: TestClient, auth_headers: dict, test_user: User, twitter_profile
    ):
        """Test analytics when no data available."""
        # Create Twitter user with no tweets
        from app.models.platforms.twitter import TwitterUser

        twitter_user = TwitterUser(
            user_id=test_user.id,
            profile_id=twitter_profile.id,
            username="empty_user",
            twitter_user_id="999999",
            created_at=datetime.utcnow()
        )

        response = client.get(
            f"/api/analytics/engagement/twitter/{twitter_user.id}",
            headers=auth_headers
        )

        # Should handle gracefully
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert data["total_likes"] == 0

    def test_analytics_invalid_platform(
        self, client: TestClient, auth_headers: dict
    ):
        """Test analytics with invalid platform."""
        response = client.get(
            "/api/analytics/engagement/invalid_platform/123",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_export_invalid_format(
        self, client: TestClient, auth_headers: dict
    ):
        """Test export with invalid format."""
        response = client.get(
            "/api/export/invalid_format/twitter/123",
            headers=auth_headers
        )

        assert response.status_code == 404
