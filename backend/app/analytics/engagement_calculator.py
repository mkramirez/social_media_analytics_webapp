"""Engagement rate calculator for social media analytics."""

from typing import Dict, List, Optional


class EngagementCalculator:
    """Calculate engagement metrics for different social media platforms."""

    @staticmethod
    def calculate_twitter_engagement(
        likes: int,
        retweets: int,
        replies: int,
        impressions: int
    ) -> float:
        """Calculate Twitter engagement rate.

        Formula: (likes + retweets + replies) / impressions × 100

        Args:
            likes: Number of likes
            retweets: Number of retweets
            replies: Number of replies
            impressions: Number of impressions

        Returns:
            Engagement rate as percentage (0-100+)
        """
        if impressions == 0:
            return 0.0

        total_engagement = likes + retweets + replies
        return (total_engagement / impressions) * 100

    @staticmethod
    def calculate_reddit_engagement(
        upvotes: int,
        comments: int,
        comment_weight: float = 2.0
    ) -> float:
        """Calculate Reddit engagement score.

        Formula: (upvotes + comments × weight)
        Note: Reddit doesn't provide view counts, so we use an engagement score

        Args:
            upvotes: Number of upvotes
            comments: Number of comments
            comment_weight: Weight multiplier for comments (default 2.0)

        Returns:
            Engagement score
        """
        return upvotes + (comments * comment_weight)

    @staticmethod
    def calculate_youtube_engagement(
        likes: int,
        comments: int,
        views: int
    ) -> float:
        """Calculate YouTube engagement rate.

        Formula: (likes + comments) / views × 100

        Args:
            likes: Number of likes
            comments: Number of comments
            views: Number of views

        Returns:
            Engagement rate as percentage (0-100+)
        """
        if views == 0:
            return 0.0

        total_engagement = likes + comments
        return (total_engagement / views) * 100

    @staticmethod
    def calculate_twitch_engagement(
        messages_per_minute: float,
        viewer_count: int
    ) -> float:
        """Calculate Twitch chat engagement rate.

        Formula: messages_per_minute / viewer_count × 100

        Args:
            messages_per_minute: Chat messages per minute
            viewer_count: Current viewer count

        Returns:
            Engagement rate as percentage (0-100+)
        """
        if viewer_count == 0:
            return 0.0

        return (messages_per_minute / viewer_count) * 100

    @staticmethod
    def calculate_average_engagement(engagement_rates: List[float]) -> float:
        """Calculate average engagement rate from a list.

        Args:
            engagement_rates: List of engagement rate values

        Returns:
            Average engagement rate
        """
        if not engagement_rates:
            return 0.0

        return sum(engagement_rates) / len(engagement_rates)

    @staticmethod
    def get_engagement_trend(
        current_rate: float,
        previous_rate: float
    ) -> Dict[str, any]:
        """Calculate engagement trend.

        Args:
            current_rate: Current period engagement rate
            previous_rate: Previous period engagement rate

        Returns:
            Dict with 'change', 'percent_change', and 'direction'
        """
        if previous_rate == 0:
            if current_rate > 0:
                return {
                    'change': current_rate,
                    'percent_change': 100.0,
                    'direction': 'up'
                }
            return {
                'change': 0.0,
                'percent_change': 0.0,
                'direction': 'stable'
            }

        change = current_rate - previous_rate
        percent_change = (change / previous_rate) * 100

        direction = 'stable'
        if change > 0:
            direction = 'up'
        elif change < 0:
            direction = 'down'

        return {
            'change': change,
            'percent_change': percent_change,
            'direction': direction
        }

    @staticmethod
    def categorize_engagement(rate: float, platform: str) -> str:
        """Categorize engagement rate as Low, Medium, High, or Excellent.

        Thresholds vary by platform based on industry standards.

        Args:
            rate: Engagement rate percentage
            platform: Platform name (twitter, reddit, youtube, twitch)

        Returns:
            Category string: 'Low', 'Medium', 'High', or 'Excellent'
        """
        platform = platform.lower()

        # Platform-specific thresholds
        thresholds = {
            'twitter': {'medium': 0.5, 'high': 1.5, 'excellent': 3.0},
            'youtube': {'medium': 2.0, 'high': 5.0, 'excellent': 10.0},
            'twitch': {'medium': 1.0, 'high': 3.0, 'excellent': 5.0},
            'reddit': {'medium': 50, 'high': 200, 'excellent': 500}
        }

        if platform not in thresholds:
            # Default thresholds
            thresholds[platform] = {'medium': 1.0, 'high': 3.0, 'excellent': 5.0}

        t = thresholds[platform]

        if rate >= t['excellent']:
            return 'Excellent'
        elif rate >= t['high']:
            return 'High'
        elif rate >= t['medium']:
            return 'Medium'
        else:
            return 'Low'

    @staticmethod
    def calculate_engagement_summary(
        twitter_data: Optional[List[Dict]] = None,
        reddit_data: Optional[List[Dict]] = None,
        youtube_data: Optional[List[Dict]] = None,
        twitch_data: Optional[List[Dict]] = None
    ) -> Dict[str, any]:
        """Calculate cross-platform engagement summary.

        Args:
            twitter_data: List of Twitter engagement dicts
            reddit_data: List of Reddit engagement dicts
            youtube_data: List of YouTube engagement dicts
            twitch_data: List of Twitch engagement dicts

        Returns:
            Summary dict with engagement metrics per platform
        """
        summary = {
            'twitter': {'average_rate': 0.0, 'total_items': 0, 'category': 'N/A'},
            'reddit': {'average_score': 0.0, 'total_items': 0, 'category': 'N/A'},
            'youtube': {'average_rate': 0.0, 'total_items': 0, 'category': 'N/A'},
            'twitch': {'average_rate': 0.0, 'total_items': 0, 'category': 'N/A'}
        }

        calc = EngagementCalculator()

        # Twitter
        if twitter_data:
            rates = [
                calc.calculate_twitter_engagement(
                    d.get('likes', 0),
                    d.get('retweets', 0),
                    d.get('replies', 0),
                    d.get('impressions', 0)
                )
                for d in twitter_data
            ]
            avg_rate = calc.calculate_average_engagement(rates)
            summary['twitter'] = {
                'average_rate': round(avg_rate, 2),
                'total_items': len(twitter_data),
                'category': calc.categorize_engagement(avg_rate, 'twitter')
            }

        # Reddit
        if reddit_data:
            scores = [
                calc.calculate_reddit_engagement(
                    d.get('upvotes', 0),
                    d.get('comments', 0)
                )
                for d in reddit_data
            ]
            avg_score = calc.calculate_average_engagement(scores)
            summary['reddit'] = {
                'average_score': round(avg_score, 2),
                'total_items': len(reddit_data),
                'category': calc.categorize_engagement(avg_score, 'reddit')
            }

        # YouTube
        if youtube_data:
            rates = [
                calc.calculate_youtube_engagement(
                    d.get('likes', 0),
                    d.get('comments', 0),
                    d.get('views', 0)
                )
                for d in youtube_data
            ]
            avg_rate = calc.calculate_average_engagement(rates)
            summary['youtube'] = {
                'average_rate': round(avg_rate, 2),
                'total_items': len(youtube_data),
                'category': calc.categorize_engagement(avg_rate, 'youtube')
            }

        # Twitch
        if twitch_data:
            rates = [
                calc.calculate_twitch_engagement(
                    d.get('messages_per_minute', 0),
                    d.get('viewer_count', 0)
                )
                for d in twitch_data
            ]
            avg_rate = calc.calculate_average_engagement(rates)
            summary['twitch'] = {
                'average_rate': round(avg_rate, 2),
                'total_items': len(twitch_data),
                'category': calc.categorize_engagement(avg_rate, 'twitch')
            }

        return summary
