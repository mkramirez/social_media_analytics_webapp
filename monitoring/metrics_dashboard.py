"""
Metrics Dashboard Generator

Fetches metrics from the application and generates visual dashboards.

Usage:
    python metrics_dashboard.py --url https://api.example.com --output dashboard.html
"""

import requests
import argparse
from datetime import datetime
from typing import Dict, Any, List
import json


class MetricsDashboard:
    """Generate metrics dashboard."""

    def __init__(self, base_url: str):
        """Initialize dashboard generator."""
        self.base_url = base_url.rstrip('/')
        self.metrics = {}

    def fetch_metrics(self):
        """Fetch metrics from application."""
        try:
            response = requests.get(f"{self.base_url}/metrics", timeout=10)
            if response.status_code == 200:
                self.metrics = response.json()
                print("✅ Metrics fetched successfully")
                return True
            else:
                print(f"⚠️  Failed to fetch metrics: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error fetching metrics: {e}")
            return False

    def generate_html_dashboard(self, output_file: str):
        """Generate HTML dashboard."""
        if not self.metrics:
            print("No metrics available to generate dashboard")
            return

        # Extract metric categories
        app_metrics = self.metrics.get("application", {})
        job_metrics = self.metrics.get("background_jobs", {})
        cache_metrics = self.metrics.get("cache", {})
        ws_metrics = self.metrics.get("websockets", {})

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Social Analytics - Metrics Dashboard</title>
    <meta http-equiv="refresh" content="30">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f9fafb;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .header {{
            background: white;
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 24px;
        }}
        .header h1 {{
            font-size: 28px;
            font-weight: 700;
            color: #111827;
            margin-bottom: 8px;
        }}
        .header p {{
            font-size: 14px;
            color: #6b7280;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 24px;
        }}
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .metric-card h3 {{
            font-size: 14px;
            font-weight: 600;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 12px;
        }}
        .metric-value {{
            font-size: 36px;
            font-weight: 700;
            color: #111827;
            margin-bottom: 4px;
        }}
        .metric-label {{
            font-size: 14px;
            color: #6b7280;
        }}
        .chart-container {{
            background: white;
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 24px;
        }}
        .chart-container h2 {{
            font-size: 18px;
            font-weight: 600;
            color: #111827;
            margin-bottom: 16px;
        }}
        .status-good {{
            color: #10b981;
        }}
        .status-warning {{
            color: #f59e0b;
        }}
        .status-error {{
            color: #ef4444;
        }}
        .timestamp {{
            text-align: center;
            font-size: 12px;
            color: #9ca3af;
            margin-top: 24px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Metrics Dashboard</h1>
            <p>Real-time application performance metrics</p>
        </div>

        <div class="grid">
            <div class="metric-card">
                <h3>Total Requests</h3>
                <div class="metric-value">{app_metrics.get('total_requests', 0):,}</div>
                <div class="metric-label">All-time requests</div>
            </div>

            <div class="metric-card">
                <h3>Success Rate</h3>
                <div class="metric-value status-good">{self._calculate_success_rate(app_metrics):.1f}%</div>
                <div class="metric-label">Request success rate</div>
            </div>

            <div class="metric-card">
                <h3>Active Jobs</h3>
                <div class="metric-value">{job_metrics.get('active_jobs', 0)}</div>
                <div class="metric-label">Background monitoring jobs</div>
            </div>

            <div class="metric-card">
                <h3>Cache Hit Rate</h3>
                <div class="metric-value status-good">{self._calculate_cache_hit_rate(cache_metrics):.1f}%</div>
                <div class="metric-label">Cache effectiveness</div>
            </div>

            <div class="metric-card">
                <h3>WebSocket Connections</h3>
                <div class="metric-value">{ws_metrics.get('active_connections', 0)}</div>
                <div class="metric-label">Real-time connections</div>
            </div>

            <div class="metric-card">
                <h3>Error Rate</h3>
                <div class="metric-value {self._get_error_rate_class(app_metrics)}">{self._calculate_error_rate(app_metrics):.2f}%</div>
                <div class="metric-label">Failed requests</div>
            </div>
        </div>

        <div class="chart-container">
            <h2>Request Status Distribution</h2>
            <canvas id="requestChart" width="400" height="200"></canvas>
        </div>

        <div class="chart-container">
            <h2>Background Jobs Status</h2>
            <canvas id="jobsChart" width="400" height="200"></canvas>
        </div>

        <p class="timestamp">
            Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} • Auto-refreshes every 30 seconds
        </p>
    </div>

    <script>
        // Request Status Chart
        const requestCtx = document.getElementById('requestChart').getContext('2d');
        new Chart(requestCtx, {{
            type: 'doughnut',
            data: {{
                labels: ['Success', 'Client Errors', 'Server Errors'],
                datasets: [{{
                    data: [
                        {app_metrics.get('successful_requests', 0)},
                        {app_metrics.get('client_errors', 0)},
                        {app_metrics.get('server_errors', 0)}
                    ],
                    backgroundColor: ['#10b981', '#f59e0b', '#ef4444']
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'bottom'
                    }}
                }}
            }}
        }});

        // Background Jobs Chart
        const jobsCtx = document.getElementById('jobsChart').getContext('2d');
        new Chart(jobsCtx, {{
            type: 'bar',
            data: {{
                labels: ['Successful', 'Failed', 'Rate Limited'],
                datasets: [{{
                    label: 'Job Executions',
                    data: [
                        {job_metrics.get('successful_jobs', 0)},
                        {job_metrics.get('failed_jobs', 0)},
                        {job_metrics.get('rate_limited_jobs', 0)}
                    ],
                    backgroundColor: ['#10b981', '#ef4444', '#f59e0b']
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        display: false
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
        """

        with open(output_file, 'w') as f:
            f.write(html)

        print(f"✅ Dashboard saved to {output_file}")

    def _calculate_success_rate(self, metrics: Dict) -> float:
        """Calculate success rate."""
        total = metrics.get('total_requests', 0)
        successful = metrics.get('successful_requests', 0)
        return (successful / total * 100) if total > 0 else 0

    def _calculate_error_rate(self, metrics: Dict) -> float:
        """Calculate error rate."""
        total = metrics.get('total_requests', 0)
        errors = metrics.get('server_errors', 0) + metrics.get('client_errors', 0)
        return (errors / total * 100) if total > 0 else 0

    def _calculate_cache_hit_rate(self, metrics: Dict) -> float:
        """Calculate cache hit rate."""
        hits = metrics.get('hits', 0)
        misses = metrics.get('misses', 0)
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0

    def _get_error_rate_class(self, metrics: Dict) -> str:
        """Get CSS class for error rate."""
        error_rate = self._calculate_error_rate(metrics)
        if error_rate < 1:
            return "status-good"
        elif error_rate < 5:
            return "status-warning"
        else:
            return "status-error"

    def print_summary(self):
        """Print metrics summary to console."""
        if not self.metrics:
            print("No metrics available")
            return

        print("\n" + "=" * 60)
        print("METRICS SUMMARY")
        print("=" * 60)

        app_metrics = self.metrics.get("application", {})
        print(f"\n📊 Application:")
        print(f"   Total Requests: {app_metrics.get('total_requests', 0):,}")
        print(f"   Success Rate: {self._calculate_success_rate(app_metrics):.1f}%")
        print(f"   Error Rate: {self._calculate_error_rate(app_metrics):.2f}%")

        job_metrics = self.metrics.get("background_jobs", {})
        print(f"\n⚙️  Background Jobs:")
        print(f"   Active Jobs: {job_metrics.get('active_jobs', 0)}")
        print(f"   Successful: {job_metrics.get('successful_jobs', 0)}")
        print(f"   Failed: {job_metrics.get('failed_jobs', 0)}")

        cache_metrics = self.metrics.get("cache", {})
        print(f"\n💾 Cache:")
        print(f"   Hit Rate: {self._calculate_cache_hit_rate(cache_metrics):.1f}%")
        print(f"   Hits: {cache_metrics.get('hits', 0):,}")
        print(f"   Misses: {cache_metrics.get('misses', 0):,}")

        ws_metrics = self.metrics.get("websockets", {})
        print(f"\n🔌 WebSockets:")
        print(f"   Active Connections: {ws_metrics.get('active_connections', 0)}")
        print(f"   Messages Sent: {ws_metrics.get('messages_sent', 0):,}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate metrics dashboard")
    parser.add_argument("--url", required=True, help="Base URL of the application")
    parser.add_argument("--output", default="dashboard.html", help="Output HTML file")
    parser.add_argument("--console-only", action="store_true", help="Print to console only")

    args = parser.parse_args()

    dashboard = MetricsDashboard(args.url)

    if dashboard.fetch_metrics():
        dashboard.print_summary()

        if not args.console_only:
            dashboard.generate_html_dashboard(args.output)


if __name__ == "__main__":
    main()
