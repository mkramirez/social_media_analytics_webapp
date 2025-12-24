"""Comprehensive logging and monitoring service."""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import traceback


class StructuredLogger:
    """
    Structured JSON logger for production environments.

    Outputs logs in JSON format for easy parsing by log aggregation systems.
    """

    def __init__(self, name: str, log_file: Optional[str] = None):
        """
        Initialize structured logger.

        Args:
            name: Logger name
            log_file: Optional file path for file logging
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Console handler with JSON formatting
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(self._get_json_formatter())
        self.logger.addHandler(console_handler)

        # File handler if specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(self._get_json_formatter())
            self.logger.addHandler(file_handler)

    def _get_json_formatter(self):
        """Get JSON formatter for log records."""
        return logging.Formatter('%(message)s')

    def _format_log(
        self,
        level: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Format log message as JSON.

        Args:
            level: Log level
            message: Log message
            extra: Additional context

        Returns:
            JSON-formatted log string
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "message": message,
            "logger": self.logger.name
        }

        if extra:
            log_entry.update(extra)

        return json.dumps(log_entry)

    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(self._format_log("INFO", message, kwargs))

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(self._format_log("WARNING", message, kwargs))

    def error(self, message: str, **kwargs):
        """Log error message."""
        self.logger.error(self._format_log("ERROR", message, kwargs))

    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.logger.critical(self._format_log("CRITICAL", message, kwargs))

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(self._format_log("DEBUG", message, kwargs))

    def exception(self, message: str, exc_info=True, **kwargs):
        """
        Log exception with traceback.

        Args:
            message: Error message
            exc_info: Include exception info
            **kwargs: Additional context
        """
        if exc_info:
            kwargs["traceback"] = traceback.format_exc()

        self.logger.error(self._format_log("ERROR", message, kwargs))


class ApplicationMetrics:
    """
    Track application metrics for monitoring.

    Stores metrics in memory for health check endpoints.
    """

    def __init__(self):
        """Initialize metrics tracker."""
        self.metrics = {
            "requests": {
                "total": 0,
                "success": 0,
                "error": 0,
                "by_endpoint": {}
            },
            "background_jobs": {
                "total_runs": 0,
                "successful_runs": 0,
                "failed_runs": 0,
                "by_platform": {
                    "twitch": {"success": 0, "failed": 0},
                    "twitter": {"success": 0, "failed": 0},
                    "youtube": {"success": 0, "failed": 0},
                    "reddit": {"success": 0, "failed": 0}
                }
            },
            "database": {
                "total_queries": 0,
                "slow_queries": 0
            },
            "cache": {
                "hits": 0,
                "misses": 0
            },
            "websocket": {
                "active_connections": 0,
                "total_messages_sent": 0
            },
            "uptime_seconds": 0,
            "last_updated": datetime.utcnow().isoformat()
        }
        self.start_time = datetime.utcnow()

    def increment_request(self, endpoint: str, success: bool = True):
        """
        Increment request counter.

        Args:
            endpoint: Endpoint path
            success: Whether request was successful
        """
        self.metrics["requests"]["total"] += 1

        if success:
            self.metrics["requests"]["success"] += 1
        else:
            self.metrics["requests"]["error"] += 1

        # Track by endpoint
        if endpoint not in self.metrics["requests"]["by_endpoint"]:
            self.metrics["requests"]["by_endpoint"][endpoint] = {"total": 0, "success": 0, "error": 0}

        self.metrics["requests"]["by_endpoint"][endpoint]["total"] += 1
        if success:
            self.metrics["requests"]["by_endpoint"][endpoint]["success"] += 1
        else:
            self.metrics["requests"]["by_endpoint"][endpoint]["error"] += 1

        self._update_timestamp()

    def increment_background_job(self, platform: str, success: bool = True):
        """
        Increment background job counter.

        Args:
            platform: Platform name
            success: Whether job was successful
        """
        self.metrics["background_jobs"]["total_runs"] += 1

        if success:
            self.metrics["background_jobs"]["successful_runs"] += 1
            if platform in self.metrics["background_jobs"]["by_platform"]:
                self.metrics["background_jobs"]["by_platform"][platform]["success"] += 1
        else:
            self.metrics["background_jobs"]["failed_runs"] += 1
            if platform in self.metrics["background_jobs"]["by_platform"]:
                self.metrics["background_jobs"]["by_platform"][platform]["failed"] += 1

        self._update_timestamp()

    def increment_cache(self, hit: bool = True):
        """
        Increment cache counter.

        Args:
            hit: Whether cache hit or miss
        """
        if hit:
            self.metrics["cache"]["hits"] += 1
        else:
            self.metrics["cache"]["misses"] += 1

        self._update_timestamp()

    def set_websocket_connections(self, count: int):
        """
        Update WebSocket connection count.

        Args:
            count: Number of active connections
        """
        self.metrics["websocket"]["active_connections"] = count
        self._update_timestamp()

    def increment_websocket_messages(self, count: int = 1):
        """
        Increment WebSocket message counter.

        Args:
            count: Number of messages sent
        """
        self.metrics["websocket"]["total_messages_sent"] += count
        self._update_timestamp()

    def _update_timestamp(self):
        """Update last_updated timestamp and uptime."""
        self.metrics["last_updated"] = datetime.utcnow().isoformat()
        self.metrics["uptime_seconds"] = (datetime.utcnow() - self.start_time).total_seconds()

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current metrics.

        Returns:
            Metrics dictionary
        """
        self._update_timestamp()
        return self.metrics

    def get_cache_hit_rate(self) -> float:
        """
        Calculate cache hit rate.

        Returns:
            Cache hit rate percentage
        """
        total = self.metrics["cache"]["hits"] + self.metrics["cache"]["misses"]
        if total == 0:
            return 0.0

        return (self.metrics["cache"]["hits"] / total) * 100

    def get_error_rate(self) -> float:
        """
        Calculate request error rate.

        Returns:
            Error rate percentage
        """
        total = self.metrics["requests"]["total"]
        if total == 0:
            return 0.0

        return (self.metrics["requests"]["error"] / total) * 100


class CloudWatchLogger:
    """
    AWS CloudWatch Logs integration.

    Sends logs to CloudWatch for centralized monitoring.
    """

    def __init__(self, log_group: str, log_stream: str):
        """
        Initialize CloudWatch logger.

        Args:
            log_group: CloudWatch log group name
            log_stream: CloudWatch log stream name
        """
        self.log_group = log_group
        self.log_stream = log_stream
        self.enabled = False

        try:
            import boto3
            from app.config import settings

            self.client = boto3.client(
                'logs',
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID if settings.AWS_ACCESS_KEY_ID else None,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY if settings.AWS_SECRET_ACCESS_KEY else None
            )

            # Create log group and stream if they don't exist
            self._ensure_log_group_exists()
            self._ensure_log_stream_exists()

            self.enabled = True
            print(f"✅ CloudWatch Logs enabled: {log_group}/{log_stream}")

        except Exception as e:
            print(f"⚠️ CloudWatch Logs initialization failed: {e}")
            self.client = None

    def _ensure_log_group_exists(self):
        """Create log group if it doesn't exist."""
        try:
            self.client.create_log_group(logGroupName=self.log_group)
        except self.client.exceptions.ResourceAlreadyExistsException:
            pass

    def _ensure_log_stream_exists(self):
        """Create log stream if it doesn't exist."""
        try:
            self.client.create_log_stream(
                logGroupName=self.log_group,
                logStreamName=self.log_stream
            )
        except self.client.exceptions.ResourceAlreadyExistsException:
            pass

    def log(self, message: str, level: str = "INFO"):
        """
        Send log message to CloudWatch.

        Args:
            message: Log message
            level: Log level
        """
        if not self.enabled or not self.client:
            return

        try:
            log_event = {
                "timestamp": int(datetime.utcnow().timestamp() * 1000),
                "message": json.dumps({
                    "level": level,
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat()
                })
            }

            self.client.put_log_events(
                logGroupName=self.log_group,
                logStreamName=self.log_stream,
                logEvents=[log_event]
            )

        except Exception as e:
            print(f"❌ Failed to send log to CloudWatch: {e}")


# Global instances
app_logger = StructuredLogger("social-analytics")
app_metrics = ApplicationMetrics()
