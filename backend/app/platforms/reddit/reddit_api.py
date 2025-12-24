"""Reddit API client using PRAW."""

import praw
from datetime import datetime
from typing import List, Dict, Optional


class RedditAPI:
    """Reddit API client for fetching posts and comments."""

    def __init__(self, client_id: str, client_secret: str, user_agent: str):
        """Initialize Reddit API client.

        Args:
            client_id: Reddit app client ID
            client_secret: Reddit app client secret
            user_agent: User agent string
        """
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )

    def get_subreddit_posts(
        self,
        subreddit_name: str,
        start_date: datetime,
        end_date: datetime,
        limit: int = 100
    ) -> List[Dict]:
        """Get posts from a subreddit within a date range.

        Args:
            subreddit_name: Name of the subreddit (without r/)
            start_date: Start date for filtering
            end_date: End date for filtering
            limit: Maximum number of posts to fetch

        Returns:
            List of post dictionaries
        """
        posts = []
        subreddit = self.reddit.subreddit(subreddit_name)

        # Convert dates to Unix timestamps
        start_timestamp = int(start_date.timestamp())
        end_timestamp = int(end_date.timestamp())

        # Fetch posts using 'new' to get chronological order
        for submission in subreddit.new(limit=limit):
            created_utc = int(submission.created_utc)

            # Filter by date range
            if start_timestamp <= created_utc <= end_timestamp:
                post_data = {
                    'post_id': submission.id,
                    'subreddit': subreddit_name,
                    'title': submission.title,
                    'content': submission.selftext if submission.is_self else '',
                    'url': submission.url,
                    'author': str(submission.author) if submission.author else '[deleted]',
                    'created_utc': datetime.fromtimestamp(created_utc).isoformat(),
                    'upvotes': submission.score,
                    'upvote_ratio': submission.upvote_ratio,
                    'num_comments': submission.num_comments,
                    'is_self': submission.is_self,
                    'permalink': f"https://reddit.com{submission.permalink}"
                }
                posts.append(post_data)

            # Stop if we've gone past the date range
            elif created_utc < start_timestamp:
                break

        return posts

    def get_subreddit_posts_by_count(
        self,
        subreddit_name: str,
        limit: int = 100
    ) -> List[Dict]:
        """Get the most recent posts from a subreddit.

        Args:
            subreddit_name: Name of the subreddit (without r/)
            limit: Maximum number of posts to fetch

        Returns:
            List of post dictionaries
        """
        posts = []
        subreddit = self.reddit.subreddit(subreddit_name)

        for submission in subreddit.new(limit=limit):
            created_utc = int(submission.created_utc)

            post_data = {
                'post_id': submission.id,
                'subreddit': subreddit_name,
                'title': submission.title,
                'content': submission.selftext if submission.is_self else '',
                'url': submission.url,
                'author': str(submission.author) if submission.author else '[deleted]',
                'created_utc': datetime.fromtimestamp(created_utc).isoformat(),
                'upvotes': submission.score,
                'upvote_ratio': submission.upvote_ratio,
                'num_comments': submission.num_comments,
                'is_self': submission.is_self,
                'permalink': f"https://reddit.com{submission.permalink}"
            }
            posts.append(post_data)

        return posts

    def get_post_comments(
        self,
        post_id: str,
        limit: int = 100
    ) -> List[Dict]:
        """Get comments from a specific post.

        Args:
            post_id: Reddit post ID
            limit: Maximum number of comments to fetch

        Returns:
            List of comment dictionaries
        """
        comments = []
        submission = self.reddit.submission(id=post_id)

        # Replace MoreComments objects with actual comments
        submission.comments.replace_more(limit=0)

        # Flatten all comments (including nested replies)
        all_comments = submission.comments.list()

        for idx, comment in enumerate(all_comments):
            if idx >= limit:
                break

            # Get parent ID (either post or another comment)
            parent_id = None
            if comment.parent_id.startswith('t1_'):  # t1_ = comment
                parent_id = comment.parent_id[3:]  # Remove prefix
            elif comment.parent_id.startswith('t3_'):  # t3_ = post
                parent_id = post_id

            comment_data = {
                'comment_id': comment.id,
                'post_id': post_id,
                'parent_id': parent_id,
                'text': comment.body,
                'author': str(comment.author) if comment.author else '[deleted]',
                'created_utc': datetime.fromtimestamp(int(comment.created_utc)).isoformat(),
                'upvotes': comment.score,
                'is_submitter': comment.is_submitter,
                'depth': comment.depth  # Nesting level
            }
            comments.append(comment_data)

        return comments

    def test_connection(self) -> bool:
        """Test if the Reddit API connection is working.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to access the front page
            list(self.reddit.subreddit('all').hot(limit=1))
            return True
        except Exception as e:
            print(f"Reddit API connection test failed: {e}")
            return False
