"""Security middleware for production deployment."""

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import secrets
import hashlib
from app.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.

    Implements OWASP recommended security headers.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add security headers to response.

        Args:
            request: HTTP request
            call_next: Next middleware/handler

        Returns:
            HTTP response with security headers
        """
        response = await call_next(request)

        # Strict Transport Security (HSTS)
        # Force HTTPS for 1 year
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content Security Policy (CSP)
        # Restrict resource loading to prevent XSS
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Needed for some JS frameworks
            "style-src 'self' 'unsafe-inline'",  # Needed for inline styles
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self' ws: wss:",  # Allow WebSocket
            "frame-ancestors 'none'",  # Prevent clickjacking
            "base-uri 'self'",
            "form-action 'self'"
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # X-Frame-Options
        # Prevent clickjacking attacks
        response.headers["X-Frame-Options"] = "DENY"

        # X-Content-Type-Options
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-XSS-Protection
        # Enable XSS filtering in older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy
        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy (formerly Feature-Policy)
        # Disable unnecessary browser features
        permissions = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "payment=()",
            "usb=()",
            "magnetometer=()"
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions)

        # X-Permitted-Cross-Domain-Policies
        # Restrict Adobe Flash/PDF cross-domain policies
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

        # Cache-Control for sensitive endpoints
        if any(path in request.url.path for path in ["/api/auth", "/api/profiles"]):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"

        return response


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Redirect HTTP requests to HTTPS in production.

    Only enforces in production environment.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Redirect to HTTPS if needed.

        Args:
            request: HTTP request
            call_next: Next middleware/handler

        Returns:
            Redirect response or normal response
        """
        # Only enforce HTTPS in production
        if settings.ENVIRONMENT == "production":
            # Check if request is over HTTP
            if request.url.scheme == "http":
                # Build HTTPS URL
                https_url = request.url.replace(scheme="https")

                return JSONResponse(
                    status_code=status.HTTP_301_MOVED_PERMANENTLY,
                    content={"detail": "Please use HTTPS"},
                    headers={"Location": str(https_url)}
                )

        return await call_next(request)


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Validate and sanitize incoming requests.

    Protects against common attacks.
    """

    def __init__(self, app, max_content_length: int = 10 * 1024 * 1024):
        """
        Initialize request validation middleware.

        Args:
            app: FastAPI application
            max_content_length: Maximum request body size (default 10MB)
        """
        super().__init__(app)
        self.max_content_length = max_content_length

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Validate request before processing.

        Args:
            request: HTTP request
            call_next: Next middleware/handler

        Returns:
            Error response or normal response
        """
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.max_content_length:
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={"detail": f"Request body too large. Maximum: {self.max_content_length} bytes"}
                    )
            except ValueError:
                pass

        # Validate Host header (prevent Host header injection)
        host = request.headers.get("host", "")
        allowed_hosts = [
            "localhost",
            "127.0.0.1",
            settings.API_BASE_URL.replace("http://", "").replace("https://", ""),
        ]

        # In production, add your actual domain
        if settings.ENVIRONMENT == "production":
            # Add production domains here
            allowed_hosts.extend([
                "api.yourdomain.com",
                "yourdomain.com"
            ])

        host_name = host.split(":")[0]  # Remove port
        if host_name and host_name not in allowed_hosts:
            # Be lenient in development
            if settings.ENVIRONMENT == "production":
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid host header"}
                )

        # Check for suspicious patterns in URL
        suspicious_patterns = [
            "../",  # Path traversal
            "..\\",  # Path traversal (Windows)
            "<script",  # XSS attempt
            "javascript:",  # XSS attempt
            "vbscript:",  # XSS attempt
        ]

        path_lower = request.url.path.lower()
        for pattern in suspicious_patterns:
            if pattern in path_lower:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid request path"}
                )

        return await call_next(request)


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection for state-changing requests.

    Validates CSRF tokens on POST/PUT/DELETE requests.
    """

    def __init__(self, app, exempt_paths: list = None):
        """
        Initialize CSRF protection middleware.

        Args:
            app: FastAPI application
            exempt_paths: List of paths exempt from CSRF protection
        """
        super().__init__(app)
        self.exempt_paths = exempt_paths or [
            "/api/auth/login",
            "/api/auth/register",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]

    def _is_exempt(self, path: str) -> bool:
        """
        Check if path is exempt from CSRF protection.

        Args:
            path: Request path

        Returns:
            True if exempt
        """
        return any(path.startswith(exempt) for exempt in self.exempt_paths)

    def _generate_csrf_token(self) -> str:
        """
        Generate a new CSRF token.

        Returns:
            CSRF token string
        """
        return secrets.token_urlsafe(32)

    def _validate_csrf_token(self, request: Request) -> bool:
        """
        Validate CSRF token from request.

        Args:
            request: HTTP request

        Returns:
            True if valid
        """
        # Get token from header
        token = request.headers.get("X-CSRF-Token")

        if not token:
            return False

        # In production, validate against session-stored token
        # For now, just check if token exists and is valid format
        return len(token) >= 32

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Validate CSRF token on state-changing requests.

        Args:
            request: HTTP request
            call_next: Next middleware/handler

        Returns:
            Error response or normal response
        """
        # Skip CSRF check for safe methods
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            response = await call_next(request)
            # Add CSRF token to response for future requests
            response.headers["X-CSRF-Token"] = self._generate_csrf_token()
            return response

        # Skip exempt paths
        if self._is_exempt(request.url.path):
            return await call_next(request)

        # Validate CSRF token for state-changing methods
        if not self._validate_csrf_token(request):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "CSRF token validation failed"}
            )

        return await call_next(request)


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Log security-relevant events for audit trail.

    Logs authentication, authorization, and sensitive operations.
    """

    def __init__(self, app):
        """Initialize audit log middleware."""
        super().__init__(app)
        self.sensitive_paths = [
            "/api/auth",
            "/api/profiles",
            "/api/export"
        ]

    def _should_log(self, path: str, method: str) -> bool:
        """
        Determine if request should be logged.

        Args:
            path: Request path
            method: HTTP method

        Returns:
            True if should log
        """
        # Log all authentication requests
        if "/api/auth" in path:
            return True

        # Log state-changing operations on sensitive paths
        if method in ["POST", "PUT", "DELETE"]:
            return any(sensitive in path for sensitive in self.sensitive_paths)

        return False

    def _mask_sensitive_data(self, data: str) -> str:
        """
        Mask sensitive data in logs.

        Args:
            data: Data to mask

        Returns:
            Masked data
        """
        # Mask passwords, tokens, etc.
        sensitive_fields = ["password", "token", "secret", "key"]

        for field in sensitive_fields:
            if field in data.lower():
                return "[REDACTED]"

        return data

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Log request and response for audit trail.

        Args:
            request: HTTP request
            call_next: Next middleware/handler

        Returns:
            HTTP response
        """
        if self._should_log(request.url.path, request.method):
            # Get user identifier if available
            user_id = request.headers.get("user-id", "anonymous")

            # Log request
            print(f"🔒 AUDIT: {request.method} {request.url.path} | User: {user_id} | IP: {request.client.host if request.client else 'unknown'}")

        response = await call_next(request)

        if self._should_log(request.url.path, request.method):
            # Log response status
            print(f"🔒 AUDIT RESULT: {response.status_code}")

        return response
