"""
Automated Health Check Script

Performs comprehensive health checks on all system components
and reports status to monitoring systems.

Usage:
    python health_check.py --url https://api.example.com --slack-webhook URL
"""

import requests
import argparse
import time
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import sys


class HealthChecker:
    """Comprehensive health checking for the application."""

    def __init__(self, base_url: str, timeout: int = 10):
        """
        Initialize health checker.

        Args:
            base_url: Base URL of the application
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.results = []

    def check_api_health(self) -> Dict[str, Any]:
        """Check main API health endpoint."""
        endpoint = f"{self.base_url}/health"
        start_time = time.time()

        try:
            response = requests.get(endpoint, timeout=self.timeout)
            duration = (time.time() - start_time) * 1000  # ms

            return {
                "service": "API",
                "endpoint": endpoint,
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "status_code": response.status_code,
                "response_time_ms": round(duration, 2),
                "details": response.json() if response.status_code == 200 else None,
                "error": None
            }
        except requests.exceptions.Timeout:
            return {
                "service": "API",
                "endpoint": endpoint,
                "status": "unhealthy",
                "status_code": None,
                "response_time_ms": self.timeout * 1000,
                "details": None,
                "error": "Request timeout"
            }
        except Exception as e:
            return {
                "service": "API",
                "endpoint": endpoint,
                "status": "unhealthy",
                "status_code": None,
                "response_time_ms": None,
                "details": None,
                "error": str(e)
            }

    def check_database(self) -> Dict[str, Any]:
        """Check database health."""
        endpoint = f"{self.base_url}/health/ready"
        start_time = time.time()

        try:
            response = requests.get(endpoint, timeout=self.timeout)
            duration = (time.time() - start_time) * 1000

            data = response.json() if response.status_code == 200 else {}
            db_healthy = data.get("checks", {}).get("database", False)

            return {
                "service": "Database",
                "endpoint": endpoint,
                "status": "healthy" if db_healthy else "unhealthy",
                "status_code": response.status_code,
                "response_time_ms": round(duration, 2),
                "details": data.get("checks", {}).get("database_details"),
                "error": None if db_healthy else "Database connection failed"
            }
        except Exception as e:
            return {
                "service": "Database",
                "endpoint": endpoint,
                "status": "unhealthy",
                "status_code": None,
                "response_time_ms": None,
                "details": None,
                "error": str(e)
            }

    def check_redis(self) -> Dict[str, Any]:
        """Check Redis health."""
        endpoint = f"{self.base_url}/health/ready"
        start_time = time.time()

        try:
            response = requests.get(endpoint, timeout=self.timeout)
            duration = (time.time() - start_time) * 1000

            data = response.json() if response.status_code == 200 else {}
            redis_healthy = data.get("checks", {}).get("redis", False)

            return {
                "service": "Redis",
                "endpoint": endpoint,
                "status": "healthy" if redis_healthy else "degraded",
                "status_code": response.status_code,
                "response_time_ms": round(duration, 2),
                "details": data.get("checks", {}).get("redis_details"),
                "error": None if redis_healthy else "Redis connection degraded (non-critical)"
            }
        except Exception as e:
            return {
                "service": "Redis",
                "endpoint": endpoint,
                "status": "degraded",
                "status_code": None,
                "response_time_ms": None,
                "details": None,
                "error": str(e)
            }

    def check_scheduler(self) -> Dict[str, Any]:
        """Check background scheduler health."""
        endpoint = f"{self.base_url}/health/ready"
        start_time = time.time()

        try:
            response = requests.get(endpoint, timeout=self.timeout)
            duration = (time.time() - start_time) * 1000

            data = response.json() if response.status_code == 200 else {}
            scheduler_healthy = data.get("checks", {}).get("scheduler", False)

            return {
                "service": "Scheduler",
                "endpoint": endpoint,
                "status": "healthy" if scheduler_healthy else "unhealthy",
                "status_code": response.status_code,
                "response_time_ms": round(duration, 2),
                "details": data.get("checks", {}).get("scheduler_details"),
                "error": None if scheduler_healthy else "Scheduler not running"
            }
        except Exception as e:
            return {
                "service": "Scheduler",
                "endpoint": endpoint,
                "status": "unhealthy",
                "status_code": None,
                "response_time_ms": None,
                "details": None,
                "error": str(e)
            }

    def check_metrics_endpoint(self) -> Dict[str, Any]:
        """Check metrics collection."""
        endpoint = f"{self.base_url}/metrics"
        start_time = time.time()

        try:
            response = requests.get(endpoint, timeout=self.timeout)
            duration = (time.time() - start_time) * 1000

            return {
                "service": "Metrics",
                "endpoint": endpoint,
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "status_code": response.status_code,
                "response_time_ms": round(duration, 2),
                "details": response.json() if response.status_code == 200 else None,
                "error": None
            }
        except Exception as e:
            return {
                "service": "Metrics",
                "endpoint": endpoint,
                "status": "unhealthy",
                "status_code": None,
                "response_time_ms": None,
                "details": None,
                "error": str(e)
            }

    def check_authentication(self) -> Dict[str, Any]:
        """Check authentication endpoint."""
        endpoint = f"{self.base_url}/api/auth/login"
        start_time = time.time()

        try:
            # Try with invalid credentials (should return 401, not 500)
            response = requests.post(
                endpoint,
                data={"username": "test@example.com", "password": "wrong"},
                timeout=self.timeout
            )
            duration = (time.time() - start_time) * 1000

            # 401 is expected for wrong credentials, anything else is a problem
            healthy = response.status_code in [401, 422]

            return {
                "service": "Authentication",
                "endpoint": endpoint,
                "status": "healthy" if healthy else "unhealthy",
                "status_code": response.status_code,
                "response_time_ms": round(duration, 2),
                "details": "Auth endpoint responding correctly",
                "error": None if healthy else "Unexpected status code"
            }
        except Exception as e:
            return {
                "service": "Authentication",
                "endpoint": endpoint,
                "status": "unhealthy",
                "status_code": None,
                "response_time_ms": None,
                "details": None,
                "error": str(e)
            }

    def run_all_checks(self) -> List[Dict[str, Any]]:
        """Run all health checks."""
        print(f"🏥 Running health checks for {self.base_url}...")
        print("=" * 60)

        checks = [
            self.check_api_health(),
            self.check_database(),
            self.check_redis(),
            self.check_scheduler(),
            self.check_metrics_endpoint(),
            self.check_authentication()
        ]

        self.results = checks
        return checks

    def print_results(self):
        """Print health check results."""
        all_healthy = True

        for check in self.results:
            status_emoji = {
                "healthy": "✅",
                "degraded": "⚠️ ",
                "unhealthy": "❌"
            }.get(check["status"], "❓")

            print(f"\n{status_emoji} {check['service']}")
            print(f"   Status: {check['status']}")
            if check['response_time_ms']:
                print(f"   Response Time: {check['response_time_ms']}ms")
            if check['error']:
                print(f"   Error: {check['error']}")
                all_healthy = False

        print("\n" + "=" * 60)
        if all_healthy:
            print("✅ All systems operational")
        else:
            print("❌ Some systems are experiencing issues")

        return all_healthy

    def get_overall_status(self) -> str:
        """Get overall system status."""
        statuses = [check["status"] for check in self.results]

        if all(s == "healthy" for s in statuses):
            return "operational"
        elif any(s == "unhealthy" for s in statuses):
            return "degraded"
        else:
            return "partial_outage"

    def send_slack_notification(self, webhook_url: str):
        """Send results to Slack."""
        overall_status = self.get_overall_status()

        color = {
            "operational": "good",
            "degraded": "warning",
            "partial_outage": "danger"
        }.get(overall_status, "warning")

        status_text = {
            "operational": "✅ All Systems Operational",
            "degraded": "⚠️ Degraded Performance",
            "partial_outage": "❌ Partial Outage"
        }.get(overall_status, "Status Unknown")

        # Build attachment fields
        fields = []
        for check in self.results:
            status_emoji = {
                "healthy": "✅",
                "degraded": "⚠️",
                "unhealthy": "❌"
            }.get(check["status"], "❓")

            value = f"{status_emoji} {check['status']}"
            if check['response_time_ms']:
                value += f" ({check['response_time_ms']}ms)"
            if check['error']:
                value += f"\n{check['error']}"

            fields.append({
                "title": check['service'],
                "value": value,
                "short": True
            })

        payload = {
            "text": status_text,
            "attachments": [{
                "color": color,
                "fields": fields,
                "footer": "Social Analytics Health Check",
                "ts": int(time.time())
            }]
        }

        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            if response.status_code == 200:
                print("\n📬 Slack notification sent successfully")
            else:
                print(f"\n⚠️  Failed to send Slack notification: {response.status_code}")
        except Exception as e:
            print(f"\n⚠️  Failed to send Slack notification: {e}")

    def write_status_file(self, output_file: str):
        """Write status to JSON file for status page."""
        status_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": self.get_overall_status(),
            "checks": self.results
        }

        try:
            with open(output_file, 'w') as f:
                json.dump(status_data, f, indent=2)
            print(f"\n📝 Status written to {output_file}")
        except Exception as e:
            print(f"\n⚠️  Failed to write status file: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run health checks")
    parser.add_argument(
        "--url",
        required=True,
        help="Base URL of the application"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Request timeout in seconds"
    )
    parser.add_argument(
        "--slack-webhook",
        help="Slack webhook URL for notifications"
    )
    parser.add_argument(
        "--output-file",
        help="Output file for status JSON"
    )
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Exit with error code if any check fails"
    )

    args = parser.parse_args()

    checker = HealthChecker(args.url, args.timeout)
    checker.run_all_checks()
    all_healthy = checker.print_results()

    if args.slack_webhook:
        checker.send_slack_notification(args.slack_webhook)

    if args.output_file:
        checker.write_status_file(args.output_file)

    if args.fail_on_error and not all_healthy:
        sys.exit(1)


if __name__ == "__main__":
    main()
