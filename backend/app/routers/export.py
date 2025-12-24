"""Export API endpoints for generating CSV and PDF reports."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional
from datetime import datetime, timedelta
from uuid import UUID
import csv
import io
import os
import tempfile

from app.database import get_db
from app.services.auth_service import get_current_user
from app.models.user import User
from app.models.twitter_models import TwitterUser, Tweet
from app.models.youtube_models import YouTubeChannel, YouTubeVideo
from app.models.reddit_models import RedditSubreddit, RedditPost
from app.models.twitch_models import TwitchChannel, StreamRecord

router = APIRouter()


@router.get("/csv/twitter")
async def export_twitter_csv(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export Twitter data to CSV format.

    Returns all tweets from monitored users.
    """
    date_from = datetime.utcnow() - timedelta(days=days)

    # Get tweets
    tweets = db.query(Tweet).join(TwitterUser).filter(
        and_(
            Tweet.user_id == current_user.id,
            Tweet.created_at >= date_from
        )
    ).all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        'Tweet ID', 'Username', 'Text', 'Created At', 'Likes', 'Retweets',
        'Replies', 'Language', 'Is Retweet'
    ])

    # Write data
    for tweet in tweets:
        twitter_user = db.query(TwitterUser).filter(TwitterUser.id == tweet.twitter_user_id).first()
        writer.writerow([
            tweet.tweet_id,
            twitter_user.username if twitter_user else 'Unknown',
            tweet.text,
            tweet.created_at.isoformat(),
            tweet.likes,
            tweet.retweets,
            tweet.replies,
            tweet.language,
            tweet.is_retweet
        ])

    # Prepare response
    output.seek(0)
    filename = f"twitter_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/csv/youtube")
async def export_youtube_csv(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export YouTube data to CSV format.

    Returns all videos from monitored channels.
    """
    date_from = datetime.utcnow() - timedelta(days=days)

    # Get videos
    videos = db.query(YouTubeVideo).join(YouTubeChannel).filter(
        and_(
            YouTubeVideo.user_id == current_user.id,
            YouTubeVideo.published_at >= date_from
        )
    ).all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        'Video ID', 'Channel Name', 'Title', 'Description', 'Published At',
        'Views', 'Likes', 'Comments', 'Duration', 'Tags'
    ])

    # Write data
    for video in videos:
        channel = db.query(YouTubeChannel).filter(YouTubeChannel.id == video.youtube_channel_id).first()
        writer.writerow([
            video.video_id,
            channel.channel_name if channel else 'Unknown',
            video.title,
            (video.description or '')[:500],  # Truncate description
            video.published_at.isoformat() if video.published_at else '',
            video.views,
            video.likes,
            video.comment_count,
            video.duration,
            video.tags or ''
        ])

    # Prepare response
    output.seek(0)
    filename = f"youtube_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/csv/reddit")
async def export_reddit_csv(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export Reddit data to CSV format.

    Returns all posts from monitored subreddits.
    """
    date_from = datetime.utcnow() - timedelta(days=days)

    # Get posts
    posts = db.query(RedditPost).join(RedditSubreddit).filter(
        and_(
            RedditPost.user_id == current_user.id,
            RedditPost.created_at >= date_from
        )
    ).all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        'Post ID', 'Subreddit', 'Title', 'Selftext', 'Created At',
        'Upvotes', 'Upvote Ratio', 'Comments', 'URL', 'Author'
    ])

    # Write data
    for post in posts:
        subreddit = db.query(RedditSubreddit).filter(RedditSubreddit.id == post.reddit_subreddit_id).first()
        writer.writerow([
            post.post_id,
            subreddit.subreddit_name if subreddit else 'Unknown',
            post.title,
            (post.selftext or '')[:500],  # Truncate selftext
            post.created_at.isoformat(),
            post.upvotes,
            post.upvote_ratio,
            post.num_comments,
            post.url,
            post.author
        ])

    # Prepare response
    output.seek(0)
    filename = f"reddit_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/csv/twitch")
async def export_twitch_csv(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export Twitch data to CSV format.

    Returns all stream records from monitored channels.
    """
    date_from = datetime.utcnow() - timedelta(days=days)

    # Get stream records
    streams = db.query(StreamRecord).join(TwitchChannel).filter(
        and_(
            StreamRecord.user_id == current_user.id,
            StreamRecord.recorded_at >= date_from
        )
    ).all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        'Stream ID', 'Channel Name', 'Title', 'Game', 'Recorded At',
        'Viewers', 'Is Live', 'Language', 'Started At', 'Chat Msgs/Min'
    ])

    # Write data
    for stream in streams:
        channel = db.query(TwitchChannel).filter(TwitchChannel.id == stream.twitch_channel_id).first()
        writer.writerow([
            stream.stream_id or '',
            channel.channel_name if channel else 'Unknown',
            stream.title or '',
            stream.game_name or '',
            stream.recorded_at.isoformat(),
            stream.viewer_count or 0,
            stream.is_live,
            stream.language or '',
            stream.started_at.isoformat() if stream.started_at else '',
            stream.chat_messages_per_minute or 0.0
        ])

    # Prepare response
    output.seek(0)
    filename = f"twitch_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/csv/all")
async def export_all_platforms_csv(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export data from all platforms to a single CSV.

    Combines data with platform identifier.
    """
    date_from = datetime.utcnow() - timedelta(days=days)

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        'Platform', 'Content ID', 'Entity Name', 'Content', 'Created At',
        'Primary Metric', 'Secondary Metric', 'Tertiary Metric'
    ])

    # Twitter data
    tweets = db.query(Tweet).join(TwitterUser).filter(
        and_(
            Tweet.user_id == current_user.id,
            Tweet.created_at >= date_from
        )
    ).all()

    for tweet in tweets:
        twitter_user = db.query(TwitterUser).filter(TwitterUser.id == tweet.twitter_user_id).first()
        writer.writerow([
            'Twitter',
            tweet.tweet_id,
            twitter_user.username if twitter_user else 'Unknown',
            tweet.text[:100],
            tweet.created_at.isoformat(),
            f"{tweet.likes} likes",
            f"{tweet.retweets} retweets",
            f"{tweet.replies} replies"
        ])

    # YouTube data
    videos = db.query(YouTubeVideo).join(YouTubeChannel).filter(
        and_(
            YouTubeVideo.user_id == current_user.id,
            YouTubeVideo.published_at >= date_from
        )
    ).all()

    for video in videos:
        channel = db.query(YouTubeChannel).filter(YouTubeChannel.id == video.youtube_channel_id).first()
        writer.writerow([
            'YouTube',
            video.video_id,
            channel.channel_name if channel else 'Unknown',
            video.title[:100],
            video.published_at.isoformat() if video.published_at else '',
            f"{video.views} views",
            f"{video.likes} likes",
            f"{video.comment_count} comments"
        ])

    # Reddit data
    posts = db.query(RedditPost).join(RedditSubreddit).filter(
        and_(
            RedditPost.user_id == current_user.id,
            RedditPost.created_at >= date_from
        )
    ).all()

    for post in posts:
        subreddit = db.query(RedditSubreddit).filter(RedditSubreddit.id == post.reddit_subreddit_id).first()
        writer.writerow([
            'Reddit',
            post.post_id,
            f"r/{subreddit.subreddit_name}" if subreddit else 'Unknown',
            post.title[:100],
            post.created_at.isoformat(),
            f"{post.upvotes} upvotes",
            f"{post.num_comments} comments",
            f"{post.upvote_ratio:.2f} ratio"
        ])

    # Twitch data
    streams = db.query(StreamRecord).join(TwitchChannel).filter(
        and_(
            StreamRecord.user_id == current_user.id,
            StreamRecord.recorded_at >= date_from
        )
    ).all()

    for stream in streams:
        channel = db.query(TwitchChannel).filter(TwitchChannel.id == stream.twitch_channel_id).first()
        writer.writerow([
            'Twitch',
            stream.stream_id or 'N/A',
            channel.channel_name if channel else 'Unknown',
            (stream.title or 'No title')[:100],
            stream.recorded_at.isoformat(),
            f"{stream.viewer_count or 0} viewers",
            f"Live: {stream.is_live}",
            f"{stream.chat_messages_per_minute or 0:.1f} msgs/min"
        ])

    # Prepare response
    output.seek(0)
    filename = f"all_platforms_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/summary")
async def get_export_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get summary of available data for export.

    Shows counts of data available per platform.
    """
    # Count data
    twitter_count = db.query(Tweet).filter(Tweet.user_id == current_user.id).count()
    youtube_count = db.query(YouTubeVideo).filter(YouTubeVideo.user_id == current_user.id).count()
    reddit_count = db.query(RedditPost).filter(RedditPost.user_id == current_user.id).count()
    twitch_count = db.query(StreamRecord).filter(StreamRecord.user_id == current_user.id).count()

    # Get date ranges
    earliest_tweet = db.query(Tweet).filter(Tweet.user_id == current_user.id).order_by(Tweet.created_at).first()
    earliest_video = db.query(YouTubeVideo).filter(YouTubeVideo.user_id == current_user.id).order_by(YouTubeVideo.published_at).first()
    earliest_post = db.query(RedditPost).filter(RedditPost.user_id == current_user.id).order_by(RedditPost.created_at).first()
    earliest_stream = db.query(StreamRecord).filter(StreamRecord.user_id == current_user.id).order_by(StreamRecord.recorded_at).first()

    return {
        "available_data": {
            "twitter": {
                "count": twitter_count,
                "earliest_date": earliest_tweet.created_at.isoformat() if earliest_tweet else None
            },
            "youtube": {
                "count": youtube_count,
                "earliest_date": earliest_video.published_at.isoformat() if earliest_video and earliest_video.published_at else None
            },
            "reddit": {
                "count": reddit_count,
                "earliest_date": earliest_post.created_at.isoformat() if earliest_post else None
            },
            "twitch": {
                "count": twitch_count,
                "earliest_date": earliest_stream.recorded_at.isoformat() if earliest_stream else None
            }
        },
        "total_records": twitter_count + youtube_count + reddit_count + twitch_count,
        "export_formats": ["CSV"],
        "message": "Use /export/csv/{platform} endpoints to download data"
    }
