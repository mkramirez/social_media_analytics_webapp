"""Redis service for caching and session management."""

import redis
import json
from typing import Optional, Any
from datetime import timedelta
from app.config import settings

# Redis client (singleton)
redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """Get or create Redis client instance."""
    global redis_client

    if redis_client is None:
        try:
            redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            # Test connection
            redis_client.ping()
            print(f"✅ Redis connected: {settings.REDIS_URL}")
        except Exception as e:
            print(f"⚠️ Redis connection failed: {e}")
            print("⚠️ Continuing without Redis cache")
            redis_client = None

    return redis_client


def is_redis_available() -> bool:
    """Check if Redis is available."""
    client = get_redis_client()
    if client is None:
        return False

    try:
        client.ping()
        return True
    except:
        return False


class RedisCache:
    """Redis caching utility class."""

    def __init__(self, prefix: str = "cache"):
        """
        Initialize Redis cache with key prefix.

        Args:
            prefix: Key prefix for namespacing
        """
        self.prefix = prefix
        self.client = get_redis_client()

    def _make_key(self, key: str) -> str:
        """Create prefixed cache key."""
        return f"{self.prefix}:{key}"

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        if not self.client:
            return None

        try:
            value = self.client.get(self._make_key(key))
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"Redis GET error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (default 5 minutes)

        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False

        try:
            serialized = json.dumps(value)
            self.client.setex(
                self._make_key(key),
                ttl,
                serialized
            )
            return True
        except Exception as e:
            print(f"Redis SET error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if successful
        """
        if not self.client:
            return False

        try:
            self.client.delete(self._make_key(key))
            return True
        except Exception as e:
            print(f"Redis DELETE error: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.

        Args:
            pattern: Pattern to match (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        if not self.client:
            return 0

        try:
            full_pattern = self._make_key(pattern)
            keys = self.client.keys(full_pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            print(f"Redis DELETE_PATTERN error: {e}")
            return 0

    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists
        """
        if not self.client:
            return False

        try:
            return bool(self.client.exists(self._make_key(key)))
        except Exception as e:
            print(f"Redis EXISTS error: {e}")
            return False

    def increment(self, key: str, amount: int = 1, ttl: Optional[int] = None) -> Optional[int]:
        """
        Increment counter in cache.

        Args:
            key: Cache key
            amount: Amount to increment by
            ttl: Optional TTL for new keys

        Returns:
            New value or None
        """
        if not self.client:
            return None

        try:
            full_key = self._make_key(key)
            value = self.client.incrby(full_key, amount)

            if ttl and not self.client.ttl(full_key):
                self.client.expire(full_key, ttl)

            return value
        except Exception as e:
            print(f"Redis INCREMENT error: {e}")
            return None


class RateLimiter:
    """Redis-based rate limiter."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        self.cache = RedisCache(prefix="ratelimit")
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def is_allowed(self, identifier: str) -> bool:
        """
        Check if request is allowed for identifier.

        Args:
            identifier: Unique identifier (e.g., user_id, IP address)

        Returns:
            True if allowed, False if rate limited
        """
        if not self.cache.client:
            # No Redis, allow all requests
            return True

        current = self.cache.increment(identifier, ttl=self.window_seconds)

        if current is None:
            return True

        return current <= self.max_requests

    def get_remaining(self, identifier: str) -> int:
        """
        Get remaining requests for identifier.

        Args:
            identifier: Unique identifier

        Returns:
            Number of remaining requests
        """
        if not self.cache.client:
            return self.max_requests

        current = self.cache.get(identifier)
        if current is None:
            return self.max_requests

        return max(0, self.max_requests - int(current))


class SessionStore:
    """Redis-based session storage."""

    def __init__(self, ttl: int = 86400):
        """
        Initialize session store.

        Args:
            ttl: Session TTL in seconds (default 24 hours)
        """
        self.cache = RedisCache(prefix="session")
        self.ttl = ttl

    def create_session(self, session_id: str, data: dict) -> bool:
        """
        Create new session.

        Args:
            session_id: Unique session identifier
            data: Session data

        Returns:
            True if successful
        """
        return self.cache.set(session_id, data, ttl=self.ttl)

    def get_session(self, session_id: str) -> Optional[dict]:
        """
        Get session data.

        Args:
            session_id: Session identifier

        Returns:
            Session data or None
        """
        return self.cache.get(session_id)

    def update_session(self, session_id: str, data: dict) -> bool:
        """
        Update session data and refresh TTL.

        Args:
            session_id: Session identifier
            data: New session data

        Returns:
            True if successful
        """
        return self.cache.set(session_id, data, ttl=self.ttl)

    def delete_session(self, session_id: str) -> bool:
        """
        Delete session.

        Args:
            session_id: Session identifier

        Returns:
            True if successful
        """
        return self.cache.delete(session_id)

    def refresh_ttl(self, session_id: str) -> bool:
        """
        Refresh session TTL.

        Args:
            session_id: Session identifier

        Returns:
            True if successful
        """
        if not self.cache.client:
            return False

        try:
            self.cache.client.expire(self.cache._make_key(session_id), self.ttl)
            return True
        except:
            return False


# Initialize global instances
api_cache = RedisCache(prefix="api")
rate_limiter = RateLimiter(max_requests=settings.RATE_LIMIT_PER_MINUTE, window_seconds=60)
session_store = SessionStore(ttl=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
