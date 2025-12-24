"""Analytics API endpoints for cross-platform analysis."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from app.database import get_db
from app.services.auth_service import get_current_user
from app.models.user import User
from app.models.analytics_models import SentimentCache, AnalyticsReport
from app.models.twitter_models import TwitterUser, Tweet
from app.models.youtube_models import YouTubeChannel, YouTubeVideo
from app.models.reddit_models import RedditSubreddit, RedditPost
from app.models.twitch_models import TwitchChannel, StreamRecord

from app.analytics.sentiment_analyzer import SentimentAnalyzer
from app.analytics.engagement_calculator import EngagementCalculator
from app.analytics.trend_analyzer import TrendAnalyzer

router = APIRouter()

# Initialize analytics engines (singleton pattern)
sentiment_analyzer = None
engagement_calculator = EngagementCalculator()
trend_analyzer = TrendAnalyzer()


def get_sentiment_analyzer():
    """Get or create sentiment analyzer instance."""
    global sentiment_analyzer
    if sentiment_analyzer is None:
        sentiment_analyzer = SentimentAnalyzer()
    return sentiment_analyzer


@router.get("/engagement")
async def get_cross_platform_engagement(
    days: int = Query(default=7, ge=1, le=90, description="Number of days to analyze"),
    platforms: Optional[str] = Query(default=None, description="Comma-separated platforms (twitter,youtube,reddit,twitch)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get cross-platform engagement summary.

    Returns engagement metrics for all monitored platforms.
    """
    date_from = datetime.utcnow() - timedelta(days=days)
    selected_platforms = platforms.split(',') if platforms else ['twitter', 'youtube', 'reddit', 'twitch']

    result = {}

    # Twitter engagement
    if 'twitter' in selected_platforms:
        tweets = db.query(Tweet).filter(
            and_(
                Tweet.user_id == current_user.id,
                Tweet.created_at >= date_from
            )
        ).all()

        twitter_data = [
            {
                'likes': t.likes,
                'retweets': t.retweets,
                'replies': t.replies,
                'impressions': max(t.likes + t.retweets + t.replies, 1)  # Fallback if no impressions
            }
            for t in tweets
        ]

        result['twitter'] = engagement_calculator.calculate_engagement_summary(twitter_data=twitter_data)['twitter']

    # YouTube engagement
    if 'youtube' in selected_platforms:
        videos = db.query(YouTubeVideo).filter(
            and_(
                YouTubeVideo.user_id == current_user.id,
                YouTubeVideo.published_at >= date_from
            )
        ).all()

        youtube_data = [
            {
                'likes': v.likes,
                'comments': v.comment_count,
                'views': v.views
            }
            for v in videos
        ]

        result['youtube'] = engagement_calculator.calculate_engagement_summary(youtube_data=youtube_data)['youtube']

    # Reddit engagement
    if 'reddit' in selected_platforms:
        posts = db.query(RedditPost).filter(
            and_(
                RedditPost.user_id == current_user.id,
                RedditPost.created_at >= date_from
            )
        ).all()

        reddit_data = [
            {
                'upvotes': p.upvotes,
                'comments': p.num_comments
            }
            for p in posts
        ]

        result['reddit'] = engagement_calculator.calculate_engagement_summary(reddit_data=reddit_data)['reddit']

    # Twitch engagement
    if 'twitch' in selected_platforms:
        streams = db.query(StreamRecord).filter(
            and_(
                StreamRecord.user_id == current_user.id,
                StreamRecord.recorded_at >= date_from
            )
        ).all()

        twitch_data = [
            {
                'messages_per_minute': s.chat_messages_per_minute or 0,
                'viewer_count': s.viewer_count or 0
            }
            for s in streams
        ]

        result['twitch'] = engagement_calculator.calculate_engagement_summary(twitch_data=twitch_data)['twitch']

    return {
        "date_from": date_from.isoformat(),
        "date_to": datetime.utcnow().isoformat(),
        "days": days,
        "engagement_summary": result
    }


@router.post("/sentiment/analyze")
async def analyze_sentiment(
    texts: List[str],
    use_cache: bool = Query(default=True, description="Use cached results if available"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analyze sentiment for one or more texts.

    Supports batch processing and caching for performance.
    """
    analyzer = get_sentiment_analyzer()
    results = []

    for text in texts:
        if not text or not text.strip():
            results.append({
                'text_preview': '',
                'sentiment': {
                    'negative': 0.0,
                    'neutral': 1.0,
                    'positive': 0.0,
                    'compound': 0.0,
                    'label': 'Neutral'
                },
                'cached': False
            })
            continue

        text_hash = analyzer.hash_text(text)

        # Check cache
        cached_result = None
        if use_cache:
            cached_result = db.query(SentimentCache).filter(
                and_(
                    SentimentCache.user_id == current_user.id,
                    SentimentCache.text_hash == text_hash
                )
            ).first()

        if cached_result:
            results.append({
                'text_preview': text[:100] + ('...' if len(text) > 100 else ''),
                'sentiment': {
                    'negative': cached_result.negative,
                    'neutral': cached_result.neutral,
                    'positive': cached_result.positive,
                    'compound': cached_result.compound,
                    'label': cached_result.sentiment_label
                },
                'cached': True
            })
        else:
            # Analyze sentiment
            sentiment = analyzer.analyze_text(text)
            label = analyzer.get_sentiment_label(sentiment['compound'])

            # Cache result
            cache_entry = SentimentCache(
                user_id=current_user.id,
                text_hash=text_hash,
                text_preview=text[:200],
                negative=sentiment['negative'],
                neutral=sentiment['neutral'],
                positive=sentiment['positive'],
                compound=sentiment['compound'],
                sentiment_label=label
            )

            try:
                db.add(cache_entry)
                db.commit()
            except Exception:
                db.rollback()  # Handle duplicate hash edge case

            results.append({
                'text_preview': text[:100] + ('...' if len(text) > 100 else ''),
                'sentiment': {
                    'negative': sentiment['negative'],
                    'neutral': sentiment['neutral'],
                    'positive': sentiment['positive'],
                    'compound': sentiment['compound'],
                    'label': label
                },
                'cached': False
            })

    return {
        "total_analyzed": len(texts),
        "results": results
    }


@router.get("/sentiment/platform/{platform}")
async def get_platform_sentiment(
    platform: str,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get sentiment analysis for platform content.

    Analyzes text content from specified platform.
    """
    analyzer = get_sentiment_analyzer()
    date_from = datetime.utcnow() - timedelta(days=days)

    texts_to_analyze = []
    content_metadata = []

    if platform == 'twitter':
        tweets = db.query(Tweet).filter(
            and_(
                Tweet.user_id == current_user.id,
                Tweet.created_at >= date_from
            )
        ).limit(limit).all()

        for tweet in tweets:
            texts_to_analyze.append(tweet.text)
            content_metadata.append({
                'id': str(tweet.id),
                'type': 'tweet',
                'created_at': tweet.created_at.isoformat(),
                'engagement': tweet.likes + tweet.retweets + tweet.replies
            })

    elif platform == 'reddit':
        posts = db.query(RedditPost).filter(
            and_(
                RedditPost.user_id == current_user.id,
                RedditPost.created_at >= date_from
            )
        ).limit(limit).all()

        for post in posts:
            if post.selftext:
                texts_to_analyze.append(f"{post.title} {post.selftext}")
            else:
                texts_to_analyze.append(post.title)

            content_metadata.append({
                'id': str(post.id),
                'type': 'reddit_post',
                'created_at': post.created_at.isoformat(),
                'engagement': post.upvotes + (post.num_comments * 2)
            })

    elif platform == 'youtube':
        videos = db.query(YouTubeVideo).filter(
            and_(
                YouTubeVideo.user_id == current_user.id,
                YouTubeVideo.published_at >= date_from
            )
        ).limit(limit).all()

        for video in videos:
            text = f"{video.title} {video.description or ''}"
            texts_to_analyze.append(text[:500])  # Limit to 500 chars

            content_metadata.append({
                'id': str(video.id),
                'type': 'youtube_video',
                'created_at': video.published_at.isoformat() if video.published_at else None,
                'engagement': video.likes + video.comment_count
            })

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported platform: {platform}. Use twitter, reddit, or youtube."
        )

    # Batch analyze sentiment
    sentiments = analyzer.analyze_batch(texts_to_analyze)

    # Combine results
    results = []
    sentiment_distribution = {'positive': 0, 'neutral': 0, 'negative': 0}

    for i, sentiment in enumerate(sentiments):
        label = analyzer.get_sentiment_label(sentiment['compound'])
        sentiment_distribution[label.lower()] += 1

        results.append({
            **content_metadata[i],
            'sentiment': {
                **sentiment,
                'label': label
            }
        })

    return {
        "platform": platform,
        "date_from": date_from.isoformat(),
        "date_to": datetime.utcnow().isoformat(),
        "total_items": len(results),
        "sentiment_distribution": sentiment_distribution,
        "average_compound": sum(r['sentiment']['compound'] for r in results) / len(results) if results else 0,
        "items": results
    }


@router.get("/trends/{platform}")
async def get_platform_trends(
    platform: str,
    metric: str = Query(default="engagement", description="Metric to analyze (engagement, views, likes, etc.)"),
    days: int = Query(default=30, ge=7, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get trend analysis for a platform metric.

    Analyzes growth, volatility, and forecasts.
    """
    date_from = datetime.utcnow() - timedelta(days=days)
    time_series = []

    if platform == 'twitter':
        tweets = db.query(Tweet).filter(
            and_(
                Tweet.user_id == current_user.id,
                Tweet.created_at >= date_from
            )
        ).order_by(Tweet.created_at).all()

        for tweet in tweets:
            if metric == 'engagement':
                value = tweet.likes + tweet.retweets + tweet.replies
            elif metric == 'likes':
                value = tweet.likes
            else:
                value = tweet.likes + tweet.retweets

            time_series.append({
                'timestamp': tweet.created_at.isoformat(),
                'value': value
            })

    elif platform == 'youtube':
        videos = db.query(YouTubeVideo).filter(
            and_(
                YouTubeVideo.user_id == current_user.id,
                YouTubeVideo.published_at >= date_from
            )
        ).order_by(YouTubeVideo.published_at).all()

        for video in videos:
            if metric == 'engagement':
                value = engagement_calculator.calculate_youtube_engagement(
                    video.likes, video.comment_count, video.views
                )
            elif metric == 'views':
                value = video.views
            elif metric == 'likes':
                value = video.likes
            else:
                value = video.views

            time_series.append({
                'timestamp': video.published_at.isoformat() if video.published_at else datetime.utcnow().isoformat(),
                'value': value
            })

    elif platform == 'reddit':
        posts = db.query(RedditPost).filter(
            and_(
                RedditPost.user_id == current_user.id,
                RedditPost.created_at >= date_from
            )
        ).order_by(RedditPost.created_at).all()

        for post in posts:
            if metric == 'engagement':
                value = engagement_calculator.calculate_reddit_engagement(post.upvotes, post.num_comments)
            elif metric == 'upvotes':
                value = post.upvotes
            else:
                value = post.upvotes + post.num_comments

            time_series.append({
                'timestamp': post.created_at.isoformat(),
                'value': value
            })

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported platform: {platform}"
        )

    # Analyze trend
    trend_analysis = trend_analyzer.analyze_time_series_trend(time_series, value_key='value')

    # Calculate moving average
    moving_avg = trend_analyzer.calculate_moving_average(time_series, value_key='value', window_size=min(7, len(time_series)))

    # Forecast
    forecast = trend_analyzer.forecast_next_period(time_series, value_key='value', periods_ahead=1)

    # Detect anomalies
    anomalies = trend_analyzer.detect_anomalies(time_series, value_key='value', threshold_std=2.0)

    return {
        "platform": platform,
        "metric": metric,
        "date_from": date_from.isoformat(),
        "date_to": datetime.utcnow().isoformat(),
        "trend_analysis": trend_analysis,
        "moving_average": moving_avg,
        "forecast": forecast,
        "anomalies": anomalies,
        "time_series": time_series
    }


@router.get("/posting-times/{platform}")
async def get_best_posting_times(
    platform: str,
    days: int = Query(default=30, ge=7, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analyze best times to post based on historical engagement.

    Returns hourly and daily patterns.
    """
    date_from = datetime.utcnow() - timedelta(days=days)
    posts_with_engagement = []

    if platform == 'twitter':
        tweets = db.query(Tweet).filter(
            and_(
                Tweet.user_id == current_user.id,
                Tweet.created_at >= date_from
            )
        ).all()

        for tweet in tweets:
            posts_with_engagement.append({
                'created_at': tweet.created_at.isoformat(),
                'engagement': tweet.likes + tweet.retweets + tweet.replies
            })

    elif platform == 'youtube':
        videos = db.query(YouTubeVideo).filter(
            and_(
                YouTubeVideo.user_id == current_user.id,
                YouTubeVideo.published_at >= date_from
            )
        ).all()

        for video in videos:
            rate = engagement_calculator.calculate_youtube_engagement(
                video.likes, video.comment_count, video.views
            )
            posts_with_engagement.append({
                'created_at': video.published_at.isoformat() if video.published_at else datetime.utcnow().isoformat(),
                'engagement': rate
            })

    elif platform == 'reddit':
        posts = db.query(RedditPost).filter(
            and_(
                RedditPost.user_id == current_user.id,
                RedditPost.created_at >= date_from
            )
        ).all()

        for post in posts:
            score = engagement_calculator.calculate_reddit_engagement(post.upvotes, post.num_comments)
            posts_with_engagement.append({
                'created_at': post.created_at.isoformat(),
                'engagement': score
            })

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported platform: {platform}"
        )

    # Analyze posting times
    analysis = trend_analyzer.calculate_best_posting_times(
        posts_with_engagement,
        timestamp_key='created_at',
        engagement_key='engagement'
    )

    return {
        "platform": platform,
        "date_from": date_from.isoformat(),
        "date_to": datetime.utcnow().isoformat(),
        "total_posts_analyzed": len(posts_with_engagement),
        **analysis
    }


@router.get("/dashboard")
async def get_analytics_dashboard(
    days: int = Query(default=7, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive analytics dashboard data.

    Returns cross-platform metrics, sentiment, and trends.
    """
    date_from = datetime.utcnow() - timedelta(days=days)

    # Get entity counts
    twitter_users_count = db.query(TwitterUser).filter(TwitterUser.user_id == current_user.id).count()
    youtube_channels_count = db.query(YouTubeChannel).filter(YouTubeChannel.user_id == current_user.id).count()
    reddit_subreddits_count = db.query(RedditSubreddit).filter(RedditSubreddit.user_id == current_user.id).count()
    twitch_channels_count = db.query(TwitchChannel).filter(TwitchChannel.user_id == current_user.id).count()

    # Get content counts
    tweets_count = db.query(Tweet).filter(
        and_(Tweet.user_id == current_user.id, Tweet.created_at >= date_from)
    ).count()
    videos_count = db.query(YouTubeVideo).filter(
        and_(YouTubeVideo.user_id == current_user.id, YouTubeVideo.published_at >= date_from)
    ).count()
    posts_count = db.query(RedditPost).filter(
        and_(RedditPost.user_id == current_user.id, RedditPost.created_at >= date_from)
    ).count()
    streams_count = db.query(StreamRecord).filter(
        and_(StreamRecord.user_id == current_user.id, StreamRecord.recorded_at >= date_from)
    ).count()

    return {
        "date_from": date_from.isoformat(),
        "date_to": datetime.utcnow().isoformat(),
        "days": days,
        "overview": {
            "monitored_entities": {
                "twitter_users": twitter_users_count,
                "youtube_channels": youtube_channels_count,
                "reddit_subreddits": reddit_subreddits_count,
                "twitch_channels": twitch_channels_count,
                "total": twitter_users_count + youtube_channels_count + reddit_subreddits_count + twitch_channels_count
            },
            "content_collected": {
                "tweets": tweets_count,
                "youtube_videos": videos_count,
                "reddit_posts": posts_count,
                "twitch_streams": streams_count,
                "total": tweets_count + videos_count + posts_count + streams_count
            }
        },
        "message": "Use specific endpoints for detailed analytics (engagement, sentiment, trends, posting-times)"
    }
