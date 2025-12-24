"""
Performance Profiling and Monitoring Tools

Profiles application performance, identifies bottlenecks, and generates reports.

Usage:
    python performance_profiler.py --url https://api.example.com --duration 300
"""

import requests
import argparse
import time
import statistics
import json
from datetime import datetime
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import matplotlib.pyplot as plt
import pandas as pd


class PerformanceProfiler:
    """Profile application performance."""

    def __init__(self, base_url: str):
        """
        Initialize profiler.

        Args:
            base_url: Base URL of the application
        """
        self.base_url = base_url.rstrip('/')
        self.results = {
            "endpoints": {},
            "summary": {},
            "slow_queries": [],
            "errors": []
        }

    def profile_endpoint(self, endpoint: str, method: str = "GET",
                        iterations: int = 100, headers: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Profile a specific endpoint.

        Args:
            endpoint: Endpoint path
            method: HTTP method
            iterations: Number of requests
            headers: Optional headers

        Returns:
            Profiling results
        """
        url = f"{self.base_url}{endpoint}"
        response_times = []
        status_codes = []
        errors = 0

        print(f"Profiling {method} {endpoint} ({iterations} iterations)...")

        for i in range(iterations):
            start_time = time.time()
            try:
                if method == "GET":
                    response = requests.get(url, headers=headers, timeout=30)
                elif method == "POST":
                    response = requests.post(url, headers=headers, timeout=30)

                duration = (time.time() - start_time) * 1000  # ms
                response_times.append(duration)
                status_codes.append(response.status_code)

                if response.status_code >= 500:
                    errors += 1

            except Exception as e:
                errors += 1
                self.results["errors"].append({
                    "endpoint": endpoint,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })

            # Progress indicator
            if (i + 1) % 10 == 0:
                print(f"  Progress: {i + 1}/{iterations}")

        # Calculate statistics
        if response_times:
            results = {
                "endpoint": endpoint,
                "method": method,
                "iterations": iterations,
                "successful": iterations - errors,
                "failed": errors,
                "success_rate": ((iterations - errors) / iterations) * 100,
                "response_times": {
                    "min": min(response_times),
                    "max": max(response_times),
                    "mean": statistics.mean(response_times),
                    "median": statistics.median(response_times),
                    "p95": self._percentile(response_times, 95),
                    "p99": self._percentile(response_times, 99)
                },
                "status_codes": dict((code, status_codes.count(code)) for code in set(status_codes))
            }
        else:
            results = {
                "endpoint": endpoint,
                "method": method,
                "iterations": iterations,
                "successful": 0,
                "failed": iterations,
                "success_rate": 0,
                "error": "All requests failed"
            }

        self.results["endpoints"][endpoint] = results
        return results

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile."""
        sorted_data = sorted(data)
        index = (percentile / 100) * len(sorted_data)
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1] if int(index) + 1 < len(sorted_data) else lower
            return (lower + upper) / 2

    def load_test(self, endpoint: str, duration: int = 60, concurrent_users: int = 10,
                  headers: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Perform load testing.

        Args:
            endpoint: Endpoint to test
            duration: Test duration in seconds
            concurrent_users: Number of concurrent users
            headers: Optional headers

        Returns:
            Load test results
        """
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        end_time = start_time + duration

        print(f"\n🔥 Load testing {endpoint}")
        print(f"   Duration: {duration}s")
        print(f"   Concurrent users: {concurrent_users}")

        total_requests = 0
        successful_requests = 0
        failed_requests = 0
        response_times = []

        def make_request():
            nonlocal total_requests, successful_requests, failed_requests

            request_start = time.time()
            try:
                response = requests.get(url, headers=headers, timeout=30)
                duration_ms = (time.time() - request_start) * 1000

                total_requests += 1
                if response.status_code < 400:
                    successful_requests += 1
                else:
                    failed_requests += 1

                response_times.append(duration_ms)

            except:
                total_requests += 1
                failed_requests += 1

        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            while time.time() < end_time:
                futures = [executor.submit(make_request) for _ in range(concurrent_users)]
                for future in as_completed(futures):
                    pass  # Just wait for completion

        elapsed = time.time() - start_time
        throughput = total_requests / elapsed

        results = {
            "endpoint": endpoint,
            "duration_seconds": elapsed,
            "concurrent_users": concurrent_users,
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": (successful_requests / total_requests) * 100 if total_requests > 0 else 0,
            "throughput_rps": throughput,
            "response_times": {
                "min": min(response_times) if response_times else 0,
                "max": max(response_times) if response_times else 0,
                "mean": statistics.mean(response_times) if response_times else 0,
                "median": statistics.median(response_times) if response_times else 0,
                "p95": self._percentile(response_times, 95) if response_times else 0,
                "p99": self._percentile(response_times, 99) if response_times else 0
            }
        }

        print(f"\n✅ Load test complete:")
        print(f"   Total requests: {total_requests}")
        print(f"   Success rate: {results['success_rate']:.2f}%")
        print(f"   Throughput: {throughput:.2f} req/s")
        print(f"   Mean response time: {results['response_times']['mean']:.2f}ms")
        print(f"   P99 response time: {results['response_times']['p99']:.2f}ms")

        return results

    def profile_critical_endpoints(self, auth_token: str = None):
        """Profile all critical endpoints."""
        headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else None

        critical_endpoints = [
            ("/health", "GET", 50),
            ("/health/ready", "GET", 50),
            ("/metrics", "GET", 50),
            ("/api/auth/login", "POST", 20),  # Slower endpoint
        ]

        print("\n🔍 Profiling critical endpoints...")
        print("=" * 60)

        for endpoint, method, iterations in critical_endpoints:
            self.profile_endpoint(endpoint, method, iterations)
            time.sleep(1)  # Cool down between tests

    def identify_slow_endpoints(self, threshold_ms: float = 1000) -> List[Dict[str, Any]]:
        """Identify endpoints slower than threshold."""
        slow_endpoints = []

        for endpoint, results in self.results["endpoints"].items():
            if "response_times" in results:
                p99 = results["response_times"]["p99"]
                if p99 > threshold_ms:
                    slow_endpoints.append({
                        "endpoint": endpoint,
                        "p99_ms": p99,
                        "mean_ms": results["response_times"]["mean"]
                    })

        self.results["slow_queries"] = sorted(slow_endpoints, key=lambda x: x["p99_ms"], reverse=True)
        return slow_endpoints

    def generate_report(self, output_file: str = None):
        """Generate performance report."""
        print("\n" + "=" * 60)
        print("PERFORMANCE REPORT")
        print("=" * 60)

        # Summary
        total_endpoints = len(self.results["endpoints"])
        total_errors = len(self.results["errors"])

        print(f"\n📊 Summary:")
        print(f"   Endpoints profiled: {total_endpoints}")
        print(f"   Total errors: {total_errors}")

        # Slow endpoints
        if self.results["slow_queries"]:
            print(f"\n⚠️  Slow Endpoints (P99 > 1000ms):")
            for endpoint in self.results["slow_queries"]:
                print(f"   {endpoint['endpoint']}: {endpoint['p99_ms']:.2f}ms (P99)")

        # Fastest/Slowest
        if self.results["endpoints"]:
            sorted_by_p99 = sorted(
                [(e, r) for e, r in self.results["endpoints"].items() if "response_times" in r],
                key=lambda x: x[1]["response_times"]["p99"]
            )

            if sorted_by_p99:
                print(f"\n✅ Fastest Endpoint:")
                fastest = sorted_by_p99[0]
                print(f"   {fastest[0]}: {fastest[1]['response_times']['p99']:.2f}ms (P99)")

                print(f"\n🐌 Slowest Endpoint:")
                slowest = sorted_by_p99[-1]
                print(f"   {slowest[0]}: {slowest[1]['response_times']['p99']:.2f}ms (P99)")

        # Errors
        if self.results["errors"]:
            print(f"\n❌ Recent Errors:")
            for error in self.results["errors"][:5]:
                print(f"   {error['endpoint']}: {error['error']}")

        # Save to file
        if output_file:
            self.save_report(output_file)

    def save_report(self, output_file: str):
        """Save report to JSON file."""
        report_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_endpoints": len(self.results["endpoints"]),
                "total_errors": len(self.results["errors"]),
                "slow_endpoints_count": len(self.results["slow_queries"])
            },
            "endpoints": self.results["endpoints"],
            "slow_queries": self.results["slow_queries"],
            "errors": self.results["errors"]
        }

        with open(output_file, 'w') as f:
            json.dump(report_data, f, indent=2)

        print(f"\n📝 Report saved to {output_file}")

    def plot_response_times(self, output_file: str = "response_times.png"):
        """Plot response time comparison."""
        if not self.results["endpoints"]:
            print("No data to plot")
            return

        endpoints = []
        means = []
        p95s = []
        p99s = []

        for endpoint, results in self.results["endpoints"].items():
            if "response_times" in results:
                endpoints.append(endpoint)
                means.append(results["response_times"]["mean"])
                p95s.append(results["response_times"]["p95"])
                p99s.append(results["response_times"]["p99"])

        if not endpoints:
            return

        # Create plot
        fig, ax = plt.subplots(figsize=(12, 6))

        x = range(len(endpoints))
        width = 0.25

        ax.bar([i - width for i in x], means, width, label='Mean', color='#3b82f6')
        ax.bar(x, p95s, width, label='P95', color='#f59e0b')
        ax.bar([i + width for i in x], p99s, width, label='P99', color='#ef4444')

        ax.set_ylabel('Response Time (ms)')
        ax.set_title('Endpoint Response Times')
        ax.set_xticks(x)
        ax.set_xticklabels(endpoints, rotation=45, ha='right')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_file, dpi=150)
        print(f"\n📊 Response time plot saved to {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Performance profiling tool")
    parser.add_argument("--url", required=True, help="Base URL of the application")
    parser.add_argument("--iterations", type=int, default=100, help="Iterations per endpoint")
    parser.add_argument("--load-test", action="store_true", help="Run load test")
    parser.add_argument("--duration", type=int, default=60, help="Load test duration (seconds)")
    parser.add_argument("--concurrent-users", type=int, default=10, help="Concurrent users for load test")
    parser.add_argument("--output", help="Output file for report")
    parser.add_argument("--plot", action="store_true", help="Generate response time plot")

    args = parser.parse_args()

    profiler = PerformanceProfiler(args.url)

    # Profile critical endpoints
    profiler.profile_critical_endpoints()

    # Run load test if requested
    if args.load_test:
        profiler.load_test("/health", duration=args.duration, concurrent_users=args.concurrent_users)

    # Identify slow endpoints
    profiler.identify_slow_endpoints()

    # Generate report
    profiler.generate_report(output_file=args.output)

    # Plot if requested
    if args.plot:
        try:
            profiler.plot_response_times()
        except ImportError:
            print("⚠️  matplotlib not installed. Install it to generate plots.")


if __name__ == "__main__":
    main()
