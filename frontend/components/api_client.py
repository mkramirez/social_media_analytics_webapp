"""API client for backend communication."""

import requests
import streamlit as st
from typing import Optional, Dict, Any
import os


class APIClient:
    """Client for communicating with FastAPI backend."""

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize API client.

        Args:
            base_url: Base URL of the API (default: from environment or localhost)
        """
        self.base_url = base_url or os.getenv("API_BASE_URL", "http://localhost:8000")

    def _get_headers(self) -> Dict[str, str]:
        """
        Get request headers with authorization token if available.

        Returns:
            Headers dictionary
        """
        headers = {
            "Content-Type": "application/json"
        }

        # Add authorization token if available in session
        if "token" in st.session_state:
            headers["Authorization"] = f"Bearer {st.session_state.token}"

        return headers

    def register(self, email: str, username: str, password: str, full_name: Optional[str] = None) -> tuple[bool, Any]:
        """
        Register a new user.

        Args:
            email: User email
            username: Username
            password: Password
            full_name: Optional full name

        Returns:
            Tuple of (success, data or error_message)
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/auth/register",
                json={
                    "email": email,
                    "username": username,
                    "password": password,
                    "full_name": full_name
                },
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 201:
                return True, response.json()
            else:
                error = response.json().get("detail", "Registration failed")
                return False, error

        except requests.exceptions.ConnectionError:
            return False, "Cannot connect to server. Make sure the backend is running."
        except Exception as e:
            return False, f"Error: {str(e)}"

    def login(self, username: str, password: str) -> tuple[bool, Any]:
        """
        Login with username/email and password.

        Args:
            username: Username or email
            password: Password

        Returns:
            Tuple of (success, data or error_message)
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/auth/login",
                json={
                    "username": username,
                    "password": password
                },
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                error = response.json().get("detail", "Login failed")
                return False, error

        except requests.exceptions.ConnectionError:
            return False, "Cannot connect to server. Make sure the backend is running."
        except Exception as e:
            return False, f"Error: {str(e)}"

    def logout(self) -> tuple[bool, str]:
        """
        Logout current user.

        Returns:
            Tuple of (success, message)
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/auth/logout",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, "Logged out successfully"
            else:
                return False, "Logout failed"

        except Exception as e:
            return False, f"Error: {str(e)}"

    def get_current_user(self) -> tuple[bool, Any]:
        """
        Get current authenticated user information.

        Returns:
            Tuple of (success, user_data or error_message)
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/auth/me",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, "Failed to get user information"

        except Exception as e:
            return False, f"Error: {str(e)}"

    def verify_token(self) -> bool:
        """
        Verify if the current token is valid.

        Returns:
            True if token is valid, False otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/auth/verify",
                headers=self._get_headers()
            )
            return response.status_code == 200
        except:
            return False

    def health_check(self) -> bool:
        """
        Check if the API is healthy.

        Returns:
            True if API is accessible, False otherwise
        """
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False

    # ============================================
    # Profile Management
    # ============================================

    def create_profile(self, profile_name: str, platform: str, credentials: dict) -> tuple[bool, Any]:
        """Create an API profile."""
        try:
            response = requests.post(
                f"{self.base_url}/api/profiles/",
                json={
                    "profile_name": profile_name,
                    "platform": platform,
                    "credentials": credentials
                },
                headers=self._get_headers()
            )

            if response.status_code == 201:
                return True, response.json()
            else:
                error = response.json().get("detail", "Failed to create profile")
                return False, error
        except Exception as e:
            return False, str(e)

    def list_profiles(self, platform: str = None) -> tuple[bool, Any]:
        """List API profiles."""
        try:
            params = {"platform": platform} if platform else {}
            response = requests.get(
                f"{self.base_url}/api/profiles/",
                params=params,
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, "Failed to list profiles"
        except Exception as e:
            return False, str(e)

    def get_profile(self, profile_id: str) -> tuple[bool, Any]:
        """Get a specific profile with credentials."""
        try:
            response = requests.get(
                f"{self.base_url}/api/profiles/{profile_id}",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, "Profile not found"
        except Exception as e:
            return False, str(e)

    def update_profile(self, profile_id: str, update_data: dict) -> tuple[bool, Any]:
        """Update a profile."""
        try:
            response = requests.put(
                f"{self.base_url}/api/profiles/{profile_id}",
                json=update_data,
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                error = response.json().get("detail", "Update failed")
                return False, error
        except Exception as e:
            return False, str(e)

    def delete_profile(self, profile_id: str) -> tuple[bool, str]:
        """Delete a profile."""
        try:
            response = requests.delete(
                f"{self.base_url}/api/profiles/{profile_id}",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, "Profile deleted"
            else:
                return False, "Delete failed"
        except Exception as e:
            return False, str(e)

    # ============================================
    # Twitch Operations
    # ============================================

    def create_twitch_channel(self, username: str, interval: int = 30) -> tuple[bool, Any]:
        """Add a Twitch channel."""
        try:
            response = requests.post(
                f"{self.base_url}/api/twitch/channels",
                json={"username": username, "monitoring_interval_seconds": interval},
                headers=self._get_headers()
            )

            if response.status_code == 201:
                return True, response.json()
            else:
                error = response.json().get("detail", "Failed to add channel")
                return False, error
        except Exception as e:
            return False, str(e)

    def list_twitch_channels(self, monitoring_only: bool = False) -> tuple[bool, Any]:
        """List Twitch channels."""
        try:
            params = {"monitoring_only": monitoring_only}
            response = requests.get(
                f"{self.base_url}/api/twitch/channels",
                params=params,
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, []
        except Exception as e:
            return False, str(e)

    def get_twitch_channel(self, channel_id: str) -> tuple[bool, Any]:
        """Get a Twitch channel with records."""
        try:
            response = requests.get(
                f"{self.base_url}/api/twitch/channels/{channel_id}",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, None
        except Exception as e:
            return False, str(e)

    def start_monitoring(self, channel_id: str) -> tuple[bool, str]:
        """Start monitoring a channel."""
        try:
            response = requests.post(
                f"{self.base_url}/api/twitch/channels/{channel_id}/start-monitoring",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                data = response.json()
                return True, data.get("message", "Monitoring started")
            else:
                error = response.json().get("detail", "Failed to start monitoring")
                return False, error
        except Exception as e:
            return False, str(e)

    def stop_monitoring(self, channel_id: str) -> tuple[bool, str]:
        """Stop monitoring a channel."""
        try:
            response = requests.post(
                f"{self.base_url}/api/twitch/channels/{channel_id}/stop-monitoring",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, "Monitoring stopped"
            else:
                return False, "Failed to stop monitoring"
        except Exception as e:
            return False, str(e)

    def start_all_monitoring(self) -> tuple[bool, Any]:
        """Start monitoring all channels."""
        try:
            response = requests.post(
                f"{self.base_url}/api/twitch/channels/start-all",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                error = response.json().get("detail", "Failed")
                return False, error
        except Exception as e:
            return False, str(e)

    def stop_all_monitoring(self) -> tuple[bool, str]:
        """Stop monitoring all channels."""
        try:
            response = requests.post(
                f"{self.base_url}/api/twitch/channels/stop-all",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                data = response.json()
                return True, data.get("message", "Stopped all")
            else:
                return False, "Failed"
        except Exception as e:
            return False, str(e)

    def delete_twitch_channel(self, channel_id: str) -> tuple[bool, str]:
        """Delete a Twitch channel."""
        try:
            response = requests.delete(
                f"{self.base_url}/api/twitch/channels/{channel_id}",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, "Channel deleted"
            else:
                return False, "Delete failed"
        except Exception as e:
            return False, str(e)

    def get_twitch_stats(self, channel_id: str) -> tuple[bool, Any]:
        """Get channel statistics."""
        try:
            response = requests.get(
                f"{self.base_url}/api/twitch/channels/{channel_id}/stats",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, None
        except Exception as e:
            return False, str(e)

    # ============================================
    # Twitter Operations
    # ============================================

    def create_twitter_user(self, username: str, interval: int = 300, days_to_collect: int = 7) -> tuple[bool, Any]:
        """Add a Twitter user."""
        try:
            response = requests.post(
                f"{self.base_url}/api/twitter/users",
                json={
                    "username": username,
                    "monitoring_interval_seconds": interval,
                    "days_to_collect": days_to_collect
                },
                headers=self._get_headers()
            )

            if response.status_code == 201:
                return True, response.json()
            else:
                error = response.json().get("detail", "Failed to add user")
                return False, error
        except Exception as e:
            return False, str(e)

    def create_twitter_users_bulk(self, usernames: list, interval: int = 300, days_to_collect: int = 7) -> tuple[bool, Any]:
        """Add multiple Twitter users."""
        try:
            response = requests.post(
                f"{self.base_url}/api/twitter/users/bulk",
                json={
                    "usernames": usernames,
                    "monitoring_interval_seconds": interval,
                    "days_to_collect": days_to_collect
                },
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                error = response.json().get("detail", "Failed to add users")
                return False, error
        except Exception as e:
            return False, str(e)

    def list_twitter_users(self, monitoring_only: bool = False) -> tuple[bool, Any]:
        """List Twitter users."""
        try:
            params = {"monitoring_only": monitoring_only}
            response = requests.get(
                f"{self.base_url}/api/twitter/users",
                params=params,
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, []
        except Exception as e:
            return False, str(e)

    def get_twitter_user(self, user_id: str, limit: int = 50) -> tuple[bool, Any]:
        """Get a Twitter user with tweets."""
        try:
            response = requests.get(
                f"{self.base_url}/api/twitter/users/{user_id}",
                params={"limit": limit},
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, None
        except Exception as e:
            return False, str(e)

    def start_twitter_monitoring(self, user_id: str) -> tuple[bool, str]:
        """Start monitoring a Twitter user."""
        try:
            response = requests.post(
                f"{self.base_url}/api/twitter/users/{user_id}/start-monitoring",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                data = response.json()
                return True, data.get("message", "Monitoring started")
            else:
                error = response.json().get("detail", "Failed to start monitoring")
                return False, error
        except Exception as e:
            return False, str(e)

    def stop_twitter_monitoring(self, user_id: str) -> tuple[bool, str]:
        """Stop monitoring a Twitter user."""
        try:
            response = requests.post(
                f"{self.base_url}/api/twitter/users/{user_id}/stop-monitoring",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, "Monitoring stopped"
            else:
                return False, "Failed to stop monitoring"
        except Exception as e:
            return False, str(e)

    def start_all_twitter_monitoring(self) -> tuple[bool, Any]:
        """Start monitoring all Twitter users."""
        try:
            response = requests.post(
                f"{self.base_url}/api/twitter/users/start-all",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                error = response.json().get("detail", "Failed")
                return False, error
        except Exception as e:
            return False, str(e)

    def stop_all_twitter_monitoring(self) -> tuple[bool, str]:
        """Stop monitoring all Twitter users."""
        try:
            response = requests.post(
                f"{self.base_url}/api/twitter/users/stop-all",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                data = response.json()
                return True, data.get("message", "Stopped all")
            else:
                return False, "Failed"
        except Exception as e:
            return False, str(e)

    def delete_twitter_user(self, user_id: str) -> tuple[bool, str]:
        """Delete a Twitter user."""
        try:
            response = requests.delete(
                f"{self.base_url}/api/twitter/users/{user_id}",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, "User deleted"
            else:
                return False, "Delete failed"
        except Exception as e:
            return False, str(e)

    def get_twitter_stats(self, user_id: str, days: int = 30) -> tuple[bool, Any]:
        """Get Twitter user statistics."""
        try:
            response = requests.get(
                f"{self.base_url}/api/twitter/users/{user_id}/stats",
                params={"days": days},
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, None
        except Exception as e:
            return False, str(e)

    def get_twitter_tweets(self, user_id: str, skip: int = 0, limit: int = 50) -> tuple[bool, Any]:
        """Get tweets for a Twitter user."""
        try:
            response = requests.get(
                f"{self.base_url}/api/twitter/users/{user_id}/tweets",
                params={"skip": skip, "limit": limit},
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, []
        except Exception as e:
            return False, str(e)

    # ============================================
    # YouTube Operations
    # ============================================

    def create_youtube_channel(self, channel_name: str, interval: int = 3600, video_limit: int = 50) -> tuple[bool, Any]:
        """Add a YouTube channel."""
        try:
            response = requests.post(
                f"{self.base_url}/api/youtube/channels",
                json={
                    "channel_name": channel_name,
                    "monitoring_interval_seconds": interval,
                    "video_limit": video_limit
                },
                headers=self._get_headers()
            )

            if response.status_code == 201:
                return True, response.json()
            else:
                error = response.json().get("detail", "Failed to add channel")
                return False, error
        except Exception as e:
            return False, str(e)

    def create_youtube_channels_bulk(self, channel_names: list, interval: int = 3600, video_limit: int = 50) -> tuple[bool, Any]:
        """Add multiple YouTube channels."""
        try:
            response = requests.post(
                f"{self.base_url}/api/youtube/channels/bulk",
                json={
                    "channel_names": channel_names,
                    "monitoring_interval_seconds": interval,
                    "video_limit": video_limit
                },
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                error = response.json().get("detail", "Failed to add channels")
                return False, error
        except Exception as e:
            return False, str(e)

    def list_youtube_channels(self, monitoring_only: bool = False) -> tuple[bool, Any]:
        """List YouTube channels."""
        try:
            params = {"monitoring_only": monitoring_only}
            response = requests.get(
                f"{self.base_url}/api/youtube/channels",
                params=params,
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, []
        except Exception as e:
            return False, str(e)

    def get_youtube_channel(self, channel_id: str, limit: int = 20) -> tuple[bool, Any]:
        """Get a YouTube channel with videos."""
        try:
            response = requests.get(
                f"{self.base_url}/api/youtube/channels/{channel_id}",
                params={"limit": limit},
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, None
        except Exception as e:
            return False, str(e)

    def start_youtube_monitoring(self, channel_id: str) -> tuple[bool, str]:
        """Start monitoring a YouTube channel."""
        try:
            response = requests.post(
                f"{self.base_url}/api/youtube/channels/{channel_id}/start-monitoring",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                data = response.json()
                return True, data.get("message", "Monitoring started")
            else:
                error = response.json().get("detail", "Failed to start monitoring")
                return False, error
        except Exception as e:
            return False, str(e)

    def stop_youtube_monitoring(self, channel_id: str) -> tuple[bool, str]:
        """Stop monitoring a YouTube channel."""
        try:
            response = requests.post(
                f"{self.base_url}/api/youtube/channels/{channel_id}/stop-monitoring",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, "Monitoring stopped"
            else:
                return False, "Failed to stop monitoring"
        except Exception as e:
            return False, str(e)

    def start_all_youtube_monitoring(self) -> tuple[bool, Any]:
        """Start monitoring all YouTube channels."""
        try:
            response = requests.post(
                f"{self.base_url}/api/youtube/channels/start-all",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                error = response.json().get("detail", "Failed")
                return False, error
        except Exception as e:
            return False, str(e)

    def stop_all_youtube_monitoring(self) -> tuple[bool, str]:
        """Stop monitoring all YouTube channels."""
        try:
            response = requests.post(
                f"{self.base_url}/api/youtube/channels/stop-all",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                data = response.json()
                return True, data.get("message", "Stopped all")
            else:
                return False, "Failed"
        except Exception as e:
            return False, str(e)

    def delete_youtube_channel(self, channel_id: str) -> tuple[bool, str]:
        """Delete a YouTube channel."""
        try:
            response = requests.delete(
                f"{self.base_url}/api/youtube/channels/{channel_id}",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, "Channel deleted"
            else:
                return False, "Delete failed"
        except Exception as e:
            return False, str(e)

    def get_youtube_stats(self, channel_id: str, days: int = 30) -> tuple[bool, Any]:
        """Get YouTube channel statistics."""
        try:
            response = requests.get(
                f"{self.base_url}/api/youtube/channels/{channel_id}/stats",
                params={"days": days},
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, None
        except Exception as e:
            return False, str(e)

    def get_youtube_videos(self, channel_id: str, skip: int = 0, limit: int = 20) -> tuple[bool, Any]:
        """Get videos for a YouTube channel."""
        try:
            response = requests.get(
                f"{self.base_url}/api/youtube/channels/{channel_id}/videos",
                params={"skip": skip, "limit": limit},
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, []
        except Exception as e:
            return False, str(e)

    # ============================================
    # Reddit Operations
    # ============================================

    def create_reddit_subreddit(self, subreddit_name: str, interval: int = 1800, post_limit: int = 100, comment_limit: int = 50) -> tuple[bool, Any]:
        """Add a Reddit subreddit."""
        try:
            response = requests.post(
                f"{self.base_url}/api/reddit/subreddits",
                json={
                    "subreddit_name": subreddit_name,
                    "monitoring_interval_seconds": interval,
                    "post_limit": post_limit,
                    "comment_limit": comment_limit
                },
                headers=self._get_headers()
            )

            if response.status_code == 201:
                return True, response.json()
            else:
                error = response.json().get("detail", "Failed to add subreddit")
                return False, error
        except Exception as e:
            return False, str(e)

    def create_reddit_subreddits_bulk(self, subreddit_names: list, interval: int = 1800, post_limit: int = 100, comment_limit: int = 50) -> tuple[bool, Any]:
        """Add multiple Reddit subreddits."""
        try:
            response = requests.post(
                f"{self.base_url}/api/reddit/subreddits/bulk",
                json={
                    "subreddit_names": subreddit_names,
                    "monitoring_interval_seconds": interval,
                    "post_limit": post_limit,
                    "comment_limit": comment_limit
                },
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                error = response.json().get("detail", "Failed to add subreddits")
                return False, error
        except Exception as e:
            return False, str(e)

    def list_reddit_subreddits(self, monitoring_only: bool = False) -> tuple[bool, Any]:
        """List Reddit subreddits."""
        try:
            params = {"monitoring_only": monitoring_only}
            response = requests.get(
                f"{self.base_url}/api/reddit/subreddits",
                params=params,
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, []
        except Exception as e:
            return False, str(e)

    def get_reddit_subreddit(self, subreddit_id: str, limit: int = 25) -> tuple[bool, Any]:
        """Get a Reddit subreddit with posts."""
        try:
            response = requests.get(
                f"{self.base_url}/api/reddit/subreddits/{subreddit_id}",
                params={"limit": limit},
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, None
        except Exception as e:
            return False, str(e)

    def start_reddit_monitoring(self, subreddit_id: str) -> tuple[bool, str]:
        """Start monitoring a Reddit subreddit."""
        try:
            response = requests.post(
                f"{self.base_url}/api/reddit/subreddits/{subreddit_id}/start-monitoring",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                data = response.json()
                return True, data.get("message", "Monitoring started")
            else:
                error = response.json().get("detail", "Failed to start monitoring")
                return False, error
        except Exception as e:
            return False, str(e)

    def stop_reddit_monitoring(self, subreddit_id: str) -> tuple[bool, str]:
        """Stop monitoring a Reddit subreddit."""
        try:
            response = requests.post(
                f"{self.base_url}/api/reddit/subreddits/{subreddit_id}/stop-monitoring",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, "Monitoring stopped"
            else:
                return False, "Failed to stop monitoring"
        except Exception as e:
            return False, str(e)

    def start_all_reddit_monitoring(self) -> tuple[bool, Any]:
        """Start monitoring all Reddit subreddits."""
        try:
            response = requests.post(
                f"{self.base_url}/api/reddit/subreddits/start-all",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                error = response.json().get("detail", "Failed")
                return False, error
        except Exception as e:
            return False, str(e)

    def stop_all_reddit_monitoring(self) -> tuple[bool, str]:
        """Stop monitoring all Reddit subreddits."""
        try:
            response = requests.post(
                f"{self.base_url}/api/reddit/subreddits/stop-all",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                data = response.json()
                return True, data.get("message", "Stopped all")
            else:
                return False, "Failed"
        except Exception as e:
            return False, str(e)

    def delete_reddit_subreddit(self, subreddit_id: str) -> tuple[bool, str]:
        """Delete a Reddit subreddit."""
        try:
            response = requests.delete(
                f"{self.base_url}/api/reddit/subreddits/{subreddit_id}",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, "Subreddit deleted"
            else:
                return False, "Delete failed"
        except Exception as e:
            return False, str(e)

    def get_reddit_stats(self, subreddit_id: str, days: int = 7) -> tuple[bool, Any]:
        """Get Reddit subreddit statistics."""
        try:
            response = requests.get(
                f"{self.base_url}/api/reddit/subreddits/{subreddit_id}/stats",
                params={"days": days},
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, None
        except Exception as e:
            return False, str(e)

    def get_reddit_posts(self, subreddit_id: str, skip: int = 0, limit: int = 25) -> tuple[bool, Any]:
        """Get posts for a Reddit subreddit."""
        try:
            response = requests.get(
                f"{self.base_url}/api/reddit/subreddits/{subreddit_id}/posts",
                params={"skip": skip, "limit": limit},
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, []
        except Exception as e:
            return False, str(e)

    # ==================== Analytics Operations ====================

    def get_cross_platform_engagement(self, days: int = 7, platforms: str = None) -> tuple[bool, Any]:
        """Get cross-platform engagement summary."""
        try:
            params = {"days": days}
            if platforms:
                params["platforms"] = platforms

            response = requests.get(
                f"{self.base_url}/api/analytics/engagement",
                params=params,
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, None
        except Exception as e:
            return False, str(e)

    def analyze_sentiment(self, texts: list[str], use_cache: bool = True) -> tuple[bool, Any]:
        """Analyze sentiment for texts."""
        try:
            response = requests.post(
                f"{self.base_url}/api/analytics/sentiment/analyze",
                json=texts,
                params={"use_cache": use_cache},
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, None
        except Exception as e:
            return False, str(e)

    def get_platform_sentiment(self, platform: str, days: int = 7, limit: int = 100) -> tuple[bool, Any]:
        """Get sentiment analysis for platform content."""
        try:
            response = requests.get(
                f"{self.base_url}/api/analytics/sentiment/platform/{platform}",
                params={"days": days, "limit": limit},
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, None
        except Exception as e:
            return False, str(e)

    def get_platform_trends(self, platform: str, metric: str = "engagement", days: int = 30) -> tuple[bool, Any]:
        """Get trend analysis for a platform metric."""
        try:
            response = requests.get(
                f"{self.base_url}/api/analytics/trends/{platform}",
                params={"metric": metric, "days": days},
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, None
        except Exception as e:
            return False, str(e)

    def get_best_posting_times(self, platform: str, days: int = 30) -> tuple[bool, Any]:
        """Get best posting times analysis."""
        try:
            response = requests.get(
                f"{self.base_url}/api/analytics/posting-times/{platform}",
                params={"days": days},
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, None
        except Exception as e:
            return False, str(e)

    def get_analytics_dashboard(self, days: int = 7) -> tuple[bool, Any]:
        """Get comprehensive analytics dashboard data."""
        try:
            response = requests.get(
                f"{self.base_url}/api/analytics/dashboard",
                params={"days": days},
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, None
        except Exception as e:
            return False, str(e)

    # ==================== Export Operations ====================

    def export_csv(self, platform: str, days: int = 30) -> tuple[bool, Any]:
        """Export platform data to CSV."""
        try:
            response = requests.get(
                f"{self.base_url}/api/export/csv/{platform}",
                params={"days": days},
                headers=self._get_headers()
            )

            if response.status_code == 200:
                # Return the raw content for file download
                return True, response.content
            else:
                return False, "Export failed"
        except Exception as e:
            return False, str(e)

    def get_export_summary(self) -> tuple[bool, Any]:
        """Get summary of available data for export."""
        try:
            response = requests.get(
                f"{self.base_url}/api/export/summary",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, None
        except Exception as e:
            return False, str(e)
