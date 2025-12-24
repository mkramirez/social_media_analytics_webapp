"""Caching middleware for API responses."""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import hashlib
import json

from app.services.redis_service import api_cache, is_redis_available


class CacheMiddleware(BaseHTTPMiddleware):
    """
    Middleware to cache API responses in Redis.

    Only caches GET requests with 200 status codes.
    Uses URL and query parameters as cache key.
    """

    def __init__(
        self,
        app,
        default_ttl: int = 300,  # 5 minutes
        cache_prefixes: list = None
    ):
        """
        Initialize cache middleware.

        Args:
            app: FastAPI application
            default_ttl: Default TTL in seconds
            cache_prefixes: List of URL prefixes to cache (e.g., ["/api/analytics"])
        """
        super().__init__(app)
        self.default_ttl = default_ttl
        self.cache_prefixes = cache_prefixes or [
            "/api/analytics",
            "/api/export/summary",
        ]

    def _should_cache(self, request: Request) -> bool:
        """
        Determine if request should be cached.

        Args:
            request: HTTP request

        Returns:
            True if request should be cached
        """
        # Only cache GET requests
        if request.method != "GET":
            return False

        # Check if URL matches cache prefixes
        path = request.url.path
        return any(path.startswith(prefix) for prefix in self.cache_prefixes)

    def _make_cache_key(self, request: Request) -> str:
        """
        Generate cache key from request.

        Args:
            request: HTTP request

        Returns:
            Cache key string
        """
        # Include path and query parameters
        path = request.url.path
        query = str(request.url.query)

        # Get user ID from headers if available
        user_id = request.headers.get("user-id", "anonymous")

        # Create hash of key components
        key_data = f"{user_id}:{path}:{query}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()

        return f"response:{key_hash}"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with caching logic.

        Args:
            request: HTTP request
            call_next: Next middleware/handler

        Returns:
            HTTP response
        """
        # Skip if Redis not available or request shouldn't be cached
        if not is_redis_available() or not self._should_cache(request):
            return await call_next(request)

        # Generate cache key
        cache_key = self._make_cache_key(request)

        # Try to get from cache
        cached_response = api_cache.get(cache_key)

        if cached_response:
            # Return cached response
            return Response(
                content=cached_response["content"],
                status_code=cached_response["status_code"],
                headers={
                    **cached_response["headers"],
                    "X-Cache": "HIT"
                },
                media_type=cached_response["media_type"]
            )

        # Call next handler
        response = await call_next(request)

        # Cache successful responses
        if response.status_code == 200:
            # Read response body
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk

            # Store in cache
            cache_data = {
                "content": response_body.decode("utf-8"),
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "media_type": response.media_type
            }

            api_cache.set(cache_key, cache_data, ttl=self.default_ttl)

            # Return response with cache miss header
            return Response(
                content=response_body,
                status_code=response.status_code,
                headers={
                    **dict(response.headers),
                    "X-Cache": "MISS"
                },
                media_type=response.media_type
            )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis.

    Limits requests per user/IP address.
    """

    def __init__(
        self,
        app,
        max_requests: int = 60,
        window_seconds: int = 60
    ):
        """
        Initialize rate limit middleware.

        Args:
            app: FastAPI application
            max_requests: Max requests per window
            window_seconds: Time window in seconds
        """
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def _get_identifier(self, request: Request) -> str:
        """
        Get unique identifier for rate limiting.

        Args:
            request: HTTP request

        Returns:
            Identifier string (user ID or IP)
        """
        # Try to get user ID from headers
        user_id = request.headers.get("user-id")
        if user_id:
            return f"user:{user_id}"

        # Fallback to IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting.

        Args:
            request: HTTP request
            call_next: Next middleware/handler

        Returns:
            HTTP response (or 429 if rate limited)
        """
        # Skip if Redis not available
        if not is_redis_available():
            return await call_next(request)

        from app.services.redis_service import rate_limiter

        identifier = self._get_identifier(request)

        if not rate_limiter.is_allowed(identifier):
            # Rate limited
            remaining = rate_limiter.get_remaining(identifier)

            return Response(
                content=json.dumps({
                    "detail": "Rate limit exceeded",
                    "retry_after": self.window_seconds
                }),
                status_code=429,
                headers={
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(self.window_seconds),
                    "Retry-After": str(self.window_seconds)
                },
                media_type="application/json"
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining = rate_limiter.get_remaining(identifier)

        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(self.window_seconds)

        return response
