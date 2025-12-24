"""Twitter API v2 client for fetching tweet data."""

import tweepy
from datetime import datetime, timezone


class TwitterAPI:
    """Client for interacting with the Twitter API v2."""

    def __init__(self, bearer_token):
        """Initialize the Twitter API client.

        Args:
            bearer_token: Your Twitter API v2 Bearer Token
        """
        self.bearer_token = bearer_token
        self.client = tweepy.Client(bearer_token=bearer_token, wait_on_rate_limit=True)

    def get_user_id(self, username):
        """Get user ID from username.

        Args:
            username: Twitter username (without @)

        Returns:
            User ID string or None if not found
        """
        try:
            # Remove @ if user included it
            username = username.lstrip('@')

            user = self.client.get_user(username=username)
            if user and user.data:
                return user.data.id
            return None
        except tweepy.errors.Forbidden as e:
            print(f"Twitter API Access Error: {e}")
            print("This usually means your API access level doesn't support this endpoint.")
            print("You may need to upgrade to Essential or higher access on Twitter Developer Portal.")
            raise Exception(f"API Access Forbidden: {e}. You may need Essential access or higher.")
        except tweepy.errors.Unauthorized as e:
            print(f"Twitter API Authentication Error: {e}")
            print("Your Bearer Token may be invalid or expired.")
            raise Exception(f"Authentication Failed: {e}. Check your Bearer Token.")
        except tweepy.errors.TooManyRequests as e:
            print(f"Twitter API Rate Limit: {e}")
            raise Exception(f"Rate limit exceeded: {e}. Please wait before trying again.")
        except tweepy.TweepyException as e:
            print(f"Error fetching user: {e}")
            raise Exception(f"Twitter API Error: {e}")

    def get_user_tweets(self, username, start_date, end_date, max_results=100):
        """Get tweets from a user within a date range.

        Args:
            username: Twitter username (without @)
            start_date: Start date (datetime object or string YYYY-MM-DD)
            end_date: End date (datetime object or string YYYY-MM-DD)
            max_results: Maximum tweets per request (10-100, default 100)

        Returns:
            List of tweet dictionaries with metrics
        """
        try:
            # Get user ID first
            user_id = self.get_user_id(username)
            if not user_id:
                print(f"User '{username}' not found")
                return []

            # Convert string dates to datetime if needed
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)

            # Ensure dates have timezone info
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)

            print(f"Fetching tweets from {start_date.date()} to {end_date.date()}...")

            tweets_data = []
            pagination_token = None

            # Paginate through all tweets in date range
            while True:
                response = self.client.get_users_tweets(
                    id=user_id,
                    start_time=start_date,
                    end_time=end_date,
                    max_results=max_results,
                    tweet_fields=['created_at', 'public_metrics', 'text'],
                    pagination_token=pagination_token
                )

                if response.data:
                    for tweet in response.data:
                        tweet_data = {
                            'tweet_id': tweet.id,
                            'text': tweet.text,
                            'created_at': tweet.created_at.isoformat(),
                            'reply_count': tweet.public_metrics['reply_count'],
                            'retweet_count': tweet.public_metrics['retweet_count'],
                            'like_count': tweet.public_metrics['like_count'],
                            'quote_count': tweet.public_metrics['quote_count'],
                            'impression_count': tweet.public_metrics.get('impression_count', 0)
                        }
                        tweets_data.append(tweet_data)

                    print(f"Fetched {len(response.data)} tweets (Total: {len(tweets_data)})")

                # Check if there are more pages
                if response.meta and 'next_token' in response.meta:
                    pagination_token = response.meta['next_token']
                else:
                    break

            print(f"Total tweets collected: {len(tweets_data)}")
            return tweets_data

        except tweepy.TweepyException as e:
            print(f"Error fetching tweets: {e}")
            return []

    def verify_credentials(self):
        """Verify that the API credentials are valid.

        Returns:
            Boolean indicating if credentials are valid
        """
        try:
            # Try to get authenticated user info (only works with OAuth 2.0 User Context)
            # For Bearer Token, we'll just try a simple request
            self.client.get_user(username="twitter")
            return True
        except tweepy.TweepyException as e:
            print(f"Credential verification failed: {e}")
            return False
