"""
Error Tracking and Alerting Service

Integrates with Sentry for error tracking and PagerDuty for critical alerts.
"""

import os
from typing import Optional, Dict, Any
from datetime import datetime
import requests
import traceback
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from app.services.logging_service import logger


class ErrorTracker:
    """Centralized error tracking and alerting."""

    def __init__(self):
        """Initialize error tracking."""
        self.sentry_enabled = False
        self.pagerduty_enabled = False

        # Initialize Sentry
        sentry_dsn = os.getenv("SENTRY_DSN")
        if sentry_dsn:
            self._initialize_sentry(sentry_dsn)

        # Initialize PagerDuty
        self.pagerduty_key = os.getenv("PAGERDUTY_INTEGRATION_KEY")
        if self.pagerduty_key:
            self.pagerduty_enabled = True
            logger.info("PagerDuty alerting enabled")

    def _initialize_sentry(self, dsn: str):
        """Initialize Sentry SDK."""
        environment = os.getenv("ENVIRONMENT", "production")
        release = os.getenv("APP_VERSION", "unknown")

        try:
            sentry_sdk.init(
                dsn=dsn,
                environment=environment,
                release=release,
                traces_sample_rate=0.1,  # 10% of transactions
                profiles_sample_rate=0.1,  # 10% profiling
                integrations=[
                    FastApiIntegration(),
                    SqlalchemyIntegration(),
                    RedisIntegration()
                ],
                before_send=self._filter_before_send,
                attach_stacktrace=True,
                send_default_pii=False  # Don't send personally identifiable information
            )

            self.sentry_enabled = True
            logger.info(f"Sentry error tracking enabled (environment: {environment}, release: {release})")

        except Exception as e:
            logger.error(f"Failed to initialize Sentry: {e}")

    def _filter_before_send(self, event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Filter events before sending to Sentry.

        Returns None to drop the event, or the modified event to send it.
        """
        # Don't send health check errors
        if 'request' in event:
            url = event['request'].get('url', '')
            if any(path in url for path in ['/health', '/metrics', '/status']):
                return None

        # Don't send 404 errors
        if 'exception' in event:
            for exception in event['exception'].get('values', []):
                if 'HTTPException' in exception.get('type', ''):
                    return None

        return event

    def capture_exception(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        level: str = "error",
        tags: Optional[Dict[str, str]] = None
    ):
        """
        Capture an exception.

        Args:
            exception: The exception to capture
            context: Additional context data
            level: Severity level (debug, info, warning, error, fatal)
            tags: Custom tags for filtering
        """
        # Log locally
        logger.error(f"Exception captured: {str(exception)}", exc_info=exception)

        # Send to Sentry
        if self.sentry_enabled:
            with sentry_sdk.push_scope() as scope:
                # Add context
                if context:
                    for key, value in context.items():
                        scope.set_context(key, value)

                # Add tags
                if tags:
                    for key, value in tags.items():
                        scope.set_tag(key, value)

                # Set level
                scope.level = level

                # Capture exception
                sentry_sdk.capture_exception(exception)

    def capture_message(
        self,
        message: str,
        level: str = "info",
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None
    ):
        """
        Capture a message (non-exception event).

        Args:
            message: Message to capture
            level: Severity level
            context: Additional context
            tags: Custom tags
        """
        if self.sentry_enabled:
            with sentry_sdk.push_scope() as scope:
                if context:
                    for key, value in context.items():
                        scope.set_context(key, value)

                if tags:
                    for key, value in tags.items():
                        scope.set_tag(key, value)

                scope.level = level
                sentry_sdk.capture_message(message)

    def trigger_pagerduty_alert(
        self,
        title: str,
        description: str,
        severity: str = "error",
        component: Optional[str] = None,
        custom_details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Trigger a PagerDuty alert for critical issues.

        Args:
            title: Alert title
            description: Detailed description
            severity: Severity level (critical, error, warning, info)
            component: Component name (e.g., "database", "scheduler")
            custom_details: Additional details

        Returns:
            True if alert was sent successfully
        """
        if not self.pagerduty_enabled:
            logger.warning(f"PagerDuty alert would be triggered: {title}")
            return False

        # Map severity to PagerDuty
        severity_map = {
            "critical": "critical",
            "error": "error",
            "warning": "warning",
            "info": "info"
        }

        pagerduty_severity = severity_map.get(severity, "error")

        payload = {
            "routing_key": self.pagerduty_key,
            "event_action": "trigger",
            "payload": {
                "summary": title,
                "severity": pagerduty_severity,
                "source": component or "social-analytics-platform",
                "timestamp": datetime.utcnow().isoformat(),
                "component": component,
                "custom_details": custom_details or {}
            }
        }

        try:
            response = requests.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            if response.status_code == 202:
                logger.info(f"PagerDuty alert sent: {title}")
                return True
            else:
                logger.error(f"Failed to send PagerDuty alert: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error sending PagerDuty alert: {e}")
            return False

    def record_breadcrumb(
        self,
        message: str,
        category: str = "default",
        level: str = "info",
        data: Optional[Dict[str, Any]] = None
    ):
        """
        Record a breadcrumb (for debugging context).

        Args:
            message: Breadcrumb message
            category: Category (e.g., "http", "db", "user")
            level: Level (debug, info, warning, error)
            data: Additional data
        """
        if self.sentry_enabled:
            sentry_sdk.add_breadcrumb(
                message=message,
                category=category,
                level=level,
                data=data or {}
            )

    def set_user_context(self, user_id: str, email: Optional[str] = None):
        """
        Set user context for error tracking.

        Args:
            user_id: User ID
            email: User email (optional, will be hashed)
        """
        if self.sentry_enabled:
            sentry_sdk.set_user({
                "id": user_id,
                "email": email
            })

    def clear_user_context(self):
        """Clear user context."""
        if self.sentry_enabled:
            sentry_sdk.set_user(None)

    def start_transaction(self, name: str, op: str = "http.server") -> Optional[Any]:
        """
        Start a performance transaction.

        Args:
            name: Transaction name
            op: Operation type

        Returns:
            Transaction object (or None if Sentry disabled)
        """
        if self.sentry_enabled:
            return sentry_sdk.start_transaction(name=name, op=op)
        return None


# Global instance
error_tracker = ErrorTracker()


# Convenience functions
def capture_exception(exception: Exception, **kwargs):
    """Capture an exception."""
    error_tracker.capture_exception(exception, **kwargs)


def capture_message(message: str, **kwargs):
    """Capture a message."""
    error_tracker.capture_message(message, **kwargs)


def trigger_critical_alert(title: str, description: str, **kwargs):
    """Trigger a critical PagerDuty alert."""
    error_tracker.trigger_pagerduty_alert(
        title=title,
        description=description,
        severity="critical",
        **kwargs
    )


def record_breadcrumb(message: str, **kwargs):
    """Record a breadcrumb."""
    error_tracker.record_breadcrumb(message, **kwargs)
