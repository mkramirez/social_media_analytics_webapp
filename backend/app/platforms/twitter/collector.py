"""Twitter data collection service."""

from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from uuid import UUID

from app.models.twitter_models import TwitterUser, Tweet
from app.platforms.twitter.twitter_api import TwitterAPI
import logging

logger = logging.getLogger(__name__)


class TwitterCollector:
    """Collects tweets from Twitter users."""

    def __init__(self, bearer_token: str):
        """
        Initialize Twitter collector.

        Args:
            bearer_token: Twitter API bearer token
        """
        self.api = TwitterAPI(bearer_token)

    def collect_tweets(
        self,
        db: Session,
        twitter_user_id: UUID,
        user_id: UUID
    ) -> Optional[Dict]:
        """
        Collect tweets for a Twitter user.

        Args:
            db: Database session
            twitter_user_id: TwitterUser record ID
            user_id: User ID (for authorization)

        Returns:
            Collection summary dict or None on error
        """
        try:
            # Get the Twitter user record
            twitter_user = db.query(TwitterUser).filter(
                TwitterUser.id == twitter_user_id,
                TwitterUser.user_id == user_id
            ).first()

            if not twitter_user:
                logger.error(f"Twitter user {twitter_user_id} not found")
                return None

            # Calculate date range for collection
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=twitter_user.days_to_collect)

            # Collect tweets from API
            tweets = self.api.get_user_tweets(
                username=twitter_user.username,
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
                max_results=100  # Limit per collection cycle
            )

            if not tweets:
                logger.info(f"No tweets found for @{twitter_user.username}")
                twitter_user.last_collected = datetime.utcnow()
                db.commit()
                return {
                    "username": twitter_user.username,
                    "tweets_collected": 0,
                    "new_tweets": 0
                }

            # Store tweets in database
            new_tweets = 0
            for tweet_data in tweets:
                try:
                    # Check if tweet already exists
                    existing_tweet = db.query(Tweet).filter(
                        Tweet.tweet_id == tweet_data['tweet_id']
                    ).first()

                    if existing_tweet:
                        # Update existing tweet metrics
                        existing_tweet.reply_count = tweet_data.get('reply_count', 0)
                        existing_tweet.retweet_count = tweet_data.get('retweet_count', 0)
                        existing_tweet.like_count = tweet_data.get('like_count', 0)
                        existing_tweet.quote_count = tweet_data.get('quote_count', 0)
                        existing_tweet.impression_count = tweet_data.get('impression_count', 0)
                    else:
                        # Create new tweet record
                        new_tweet = Tweet(
                            twitter_user_id=twitter_user_id,
                            user_id=user_id,
                            tweet_id=tweet_data['tweet_id'],
                            text=tweet_data['text'],
                            created_at=datetime.fromisoformat(tweet_data['created_at'].replace('Z', '+00:00')),
                            reply_count=tweet_data.get('reply_count', 0),
                            retweet_count=tweet_data.get('retweet_count', 0),
                            like_count=tweet_data.get('like_count', 0),
                            quote_count=tweet_data.get('quote_count', 0),
                            impression_count=tweet_data.get('impression_count', 0)
                        )
                        db.add(new_tweet)
                        new_tweets += 1

                except Exception as e:
                    logger.error(f"Error storing tweet {tweet_data.get('tweet_id')}: {e}")
                    continue

            # Update twitter_user statistics
            total_tweets = db.query(Tweet).filter(
                Tweet.twitter_user_id == twitter_user_id
            ).count()

            twitter_user.total_tweets = total_tweets
            twitter_user.last_collected = datetime.utcnow()

            db.commit()

            logger.info(f"Collected {new_tweets} new tweets for @{twitter_user.username} (total: {total_tweets})")

            return {
                "username": twitter_user.username,
                "tweets_collected": len(tweets),
                "new_tweets": new_tweets,
                "total_tweets": total_tweets
            }

        except Exception as e:
            logger.error(f"Error collecting tweets for user {twitter_user_id}: {e}")
            db.rollback()
            return None

    def collect_user_info(self, username: str) -> Optional[Dict]:
        """
        Collect basic user information from Twitter.

        Args:
            username: Twitter username

        Returns:
            User info dict or None on error
        """
        try:
            user_info = self.api.get_user_info(username)
            return user_info
        except Exception as e:
            logger.error(f"Error collecting user info for @{username}: {e}")
            return None

    def verify_user_exists(self, username: str) -> bool:
        """
        Verify that a Twitter user exists.

        Args:
            username: Twitter username

        Returns:
            True if user exists, False otherwise
        """
        try:
            user_info = self.api.get_user_info(username)
            return user_info is not None
        except:
            return False
