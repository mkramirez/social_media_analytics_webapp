"""YouTube API client for fetching video and comment data."""

from googleapiclient.discovery import build
from datetime import datetime


class YouTubeAPI:
    """Client for interacting with the YouTube Data API v3."""

    def __init__(self, api_key):
        """Initialize the YouTube API client.

        Args:
            api_key: Your YouTube Data API v3 key
        """
        self.api_key = api_key
        self.youtube = build('youtube', 'v3', developerKey=api_key)

    def get_channel_id(self, channel_name):
        """Get channel ID from channel name.

        Args:
            channel_name: YouTube channel name or handle

        Returns:
            Channel ID string or None if not found
        """
        try:
            # Try searching for the channel
            request = self.youtube.search().list(
                part='snippet',
                q=channel_name,
                type='channel',
                maxResults=1
            )
            response = request.execute()

            if response['items']:
                return response['items'][0]['snippet']['channelId']
            return None

        except Exception as e:
            print(f"Error fetching channel: {e}")
            return None

    def get_channel_info(self, channel_id):
        """Get channel information.

        Args:
            channel_id: YouTube channel ID

        Returns:
            Dictionary with channel info
        """
        try:
            request = self.youtube.channels().list(
                part='snippet,statistics',
                id=channel_id
            )
            response = request.execute()

            if response['items']:
                channel = response['items'][0]
                return {
                    'channel_id': channel_id,
                    'title': channel['snippet']['title'],
                    'description': channel['snippet']['description'],
                    'subscriber_count': int(channel['statistics'].get('subscriberCount', 0)),
                    'video_count': int(channel['statistics'].get('videoCount', 0)),
                    'view_count': int(channel['statistics'].get('viewCount', 0))
                }
            return None

        except Exception as e:
            print(f"Error fetching channel info: {e}")
            return None

    def get_channel_videos(self, channel_id, max_results=None, published_after=None, published_before=None):
        """Get videos from a channel.

        Args:
            channel_id: YouTube channel ID
            max_results: Maximum number of videos to fetch (None for all)
            published_after: datetime object for start date
            published_before: datetime object for end date

        Returns:
            List of video dictionaries
        """
        videos = []
        page_token = None

        try:
            while True:
                # Build request parameters
                request_params = {
                    'part': 'snippet',
                    'channelId': channel_id,
                    'order': 'date',
                    'type': 'video',
                    'maxResults': min(50, max_results) if max_results else 50
                }

                if published_after:
                    request_params['publishedAfter'] = published_after.isoformat() + 'Z'
                if published_before:
                    request_params['publishedBefore'] = published_before.isoformat() + 'Z'
                if page_token:
                    request_params['pageToken'] = page_token

                # Execute request
                request = self.youtube.search().list(**request_params)
                response = request.execute()

                # Extract video IDs
                video_ids = [item['id']['videoId'] for item in response['items']]

                if video_ids:
                    # Get detailed video stats
                    video_details = self._get_video_details(video_ids)
                    videos.extend(video_details)

                    print(f"Fetched {len(videos)} videos...")

                # Check if we should continue
                if max_results and len(videos) >= max_results:
                    videos = videos[:max_results]
                    break

                page_token = response.get('nextPageToken')
                if not page_token:
                    break

            return videos

        except Exception as e:
            print(f"Error fetching videos: {e}")
            return videos

    def _get_video_details(self, video_ids):
        """Get detailed information for videos.

        Args:
            video_ids: List of video IDs

        Returns:
            List of video detail dictionaries
        """
        try:
            request = self.youtube.videos().list(
                part='snippet,statistics',
                id=','.join(video_ids)
            )
            response = request.execute()

            videos = []
            for item in response['items']:
                video = {
                    'video_id': item['id'],
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description'],
                    'published_at': item['snippet']['publishedAt'],
                    'view_count': int(item['statistics'].get('viewCount', 0)),
                    'like_count': int(item['statistics'].get('likeCount', 0)),
                    'comment_count': int(item['statistics'].get('commentCount', 0))
                }
                videos.append(video)

            return videos

        except Exception as e:
            print(f"Error fetching video details: {e}")
            return []

    def get_video_comments(self, video_id, max_results=100):
        """Get comments for a video.

        Args:
            video_id: YouTube video ID
            max_results: Maximum number of comments to fetch

        Returns:
            List of comment dictionaries
        """
        comments = []
        page_token = None

        try:
            while len(comments) < max_results:
                request_params = {
                    'part': 'snippet',
                    'videoId': video_id,
                    'maxResults': min(100, max_results - len(comments)),
                    'order': 'relevance',
                    'textFormat': 'plainText'
                }

                if page_token:
                    request_params['pageToken'] = page_token

                request = self.youtube.commentThreads().list(**request_params)
                response = request.execute()

                for item in response['items']:
                    top_comment = item['snippet']['topLevelComment']['snippet']
                    comment = {
                        'comment_id': item['id'],
                        'video_id': video_id,
                        'text': top_comment['textDisplay'],
                        'author': top_comment['authorDisplayName'],
                        'like_count': int(top_comment.get('likeCount', 0)),
                        'published_at': top_comment['publishedAt'],
                        'reply_count': int(item['snippet'].get('totalReplyCount', 0))
                    }
                    comments.append(comment)

                print(f"Fetched {len(comments)} comments...")

                page_token = response.get('nextPageToken')
                if not page_token or len(comments) >= max_results:
                    break

            return comments[:max_results]

        except Exception as e:
            print(f"Error fetching comments: {e}")
            return comments

    def verify_api_key(self):
        """Verify that the API key is valid.

        Returns:
            Boolean indicating if API key is valid
        """
        try:
            # Try a simple request
            request = self.youtube.search().list(
                part='snippet',
                q='test',
                maxResults=1
            )
            request.execute()
            return True
        except Exception as e:
            print(f"API key verification failed: {e}")
            return False
