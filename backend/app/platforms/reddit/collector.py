"""Reddit data collection service."""

from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from datetime import datetime
from uuid import UUID

from app.models.reddit_models import RedditSubreddit, RedditPost, RedditComment
from app.platforms.reddit.reddit_api import RedditAPI
import logging

logger = logging.getLogger(__name__)


class RedditCollector:
    """Collects posts and comments from Reddit subreddits."""

    def __init__(self, client_id: str, client_secret: str, user_agent: str):
        """
        Initialize Reddit collector.

        Args:
            client_id: Reddit API client ID
            client_secret: Reddit API client secret
            user_agent: Reddit API user agent
        """
        self.api = RedditAPI(client_id, client_secret, user_agent)

    def collect_posts(
        self,
        db: Session,
        subreddit_id: UUID,
        user_id: UUID
    ) -> Optional[Dict]:
        """
        Collect posts for a Reddit subreddit.

        Args:
            db: Database session
            subreddit_id: RedditSubreddit record ID
            user_id: User ID (for authorization)

        Returns:
            Collection summary dict or None on error
        """
        try:
            # Get the subreddit record
            subreddit = db.query(RedditSubreddit).filter(
                RedditSubreddit.id == subreddit_id,
                RedditSubreddit.user_id == user_id
            ).first()

            if not subreddit:
                logger.error(f"Subreddit {subreddit_id} not found")
                return None

            # Collect posts from API
            posts = self.api.get_subreddit_posts(
                subreddit=subreddit.subreddit_name,
                limit=subreddit.post_limit
            )

            if not posts:
                logger.info(f"No posts found for r/{subreddit.subreddit_name}")
                subreddit.last_collected = datetime.utcnow()
                db.commit()
                return {
                    "subreddit_name": subreddit.subreddit_name,
                    "posts_collected": 0,
                    "new_posts": 0,
                    "comments_collected": 0
                }

            # Store posts in database
            new_posts = 0
            total_comments = 0

            for post_data in posts:
                try:
                    # Check if post already exists
                    existing_post = db.query(RedditPost).filter(
                        RedditPost.post_id == post_data['post_id']
                    ).first()

                    if existing_post:
                        # Update existing post metrics
                        existing_post.upvotes = post_data.get('upvotes', 0)
                        existing_post.upvote_ratio = post_data.get('upvote_ratio', 0.0)
                        existing_post.num_comments = post_data.get('num_comments', 0)

                        post_record = existing_post
                    else:
                        # Create new post record
                        new_post = RedditPost(
                            subreddit_id=subreddit_id,
                            user_id=user_id,
                            post_id=post_data['post_id'],
                            title=post_data['title'],
                            content=post_data.get('content', ''),
                            url=post_data.get('url', ''),
                            author=post_data.get('author', '[deleted]'),
                            permalink=post_data.get('permalink', ''),
                            created_utc=datetime.utcfromtimestamp(post_data['created_utc']),
                            upvotes=post_data.get('upvotes', 0),
                            upvote_ratio=post_data.get('upvote_ratio', 0.0),
                            num_comments=post_data.get('num_comments', 0),
                            is_self=post_data.get('is_self', False)
                        )
                        db.add(new_post)
                        db.flush()  # Get ID
                        new_posts += 1
                        post_record = new_post

                    # Collect comments for this post if comment_limit > 0
                    if subreddit.comment_limit > 0:
                        comments = self.api.get_post_comments(
                            subreddit=subreddit.subreddit_name,
                            post_id=post_data['post_id'],
                            limit=subreddit.comment_limit
                        )

                        if comments:
                            for comment_data in comments:
                                try:
                                    # Check if comment already exists
                                    existing_comment = db.query(RedditComment).filter(
                                        RedditComment.comment_id == comment_data['comment_id']
                                    ).first()

                                    if existing_comment:
                                        # Update existing comment metrics
                                        existing_comment.upvotes = comment_data.get('upvotes', 0)
                                    else:
                                        # Create new comment record
                                        new_comment = RedditComment(
                                            post_id=post_record.id,
                                            user_id=user_id,
                                            comment_id=comment_data['comment_id'],
                                            parent_id=comment_data.get('parent_id', ''),
                                            text=comment_data['text'],
                                            author=comment_data.get('author', '[deleted]'),
                                            created_utc=datetime.utcfromtimestamp(comment_data['created_utc']),
                                            upvotes=comment_data.get('upvotes', 0),
                                            is_submitter=comment_data.get('is_submitter', False),
                                            depth=comment_data.get('depth', 0)
                                        )
                                        db.add(new_comment)
                                        total_comments += 1

                                except Exception as e:
                                    logger.error(f"Error storing comment {comment_data.get('comment_id')}: {e}")
                                    continue

                except Exception as e:
                    logger.error(f"Error storing post {post_data.get('post_id')}: {e}")
                    continue

            # Update subreddit statistics
            total_posts = db.query(RedditPost).filter(
                RedditPost.subreddit_id == subreddit_id
            ).count()

            total_comments_db = db.query(RedditComment).join(RedditPost).filter(
                RedditPost.subreddit_id == subreddit_id
            ).count()

            subreddit.total_posts = total_posts
            subreddit.total_comments = total_comments_db
            subreddit.last_collected = datetime.utcnow()

            db.commit()

            logger.info(f"Collected {new_posts} new posts and {total_comments} new comments for r/{subreddit.subreddit_name}")

            return {
                "subreddit_name": subreddit.subreddit_name,
                "posts_collected": len(posts),
                "new_posts": new_posts,
                "total_posts": total_posts,
                "comments_collected": total_comments
            }

        except Exception as e:
            logger.error(f"Error collecting posts for subreddit {subreddit_id}: {e}")
            db.rollback()
            return None

    def verify_subreddit_exists(self, subreddit_name: str) -> bool:
        """
        Verify that a subreddit exists.

        Args:
            subreddit_name: Subreddit name

        Returns:
            True if subreddit exists, False otherwise
        """
        try:
            posts = self.api.get_subreddit_posts(subreddit_name, limit=1)
            return posts is not None and len(posts) > 0
        except:
            return False

    def get_subreddit_info(self, subreddit_name: str) -> Optional[Dict]:
        """
        Get basic subreddit information.

        Args:
            subreddit_name: Subreddit name

        Returns:
            Subreddit info dict or None on error
        """
        try:
            posts = self.api.get_subreddit_posts(subreddit_name, limit=1)
            if posts and len(posts) > 0:
                return {
                    "subreddit_name": subreddit_name,
                    "exists": True
                }
            return None
        except Exception as e:
            logger.error(f"Error getting subreddit info for r/{subreddit_name}: {e}")
            return None
