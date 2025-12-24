"""Performance testing script for the API."""

import requests
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict
import json


class PerformanceTest:
    """Performance testing utility for API endpoints."""

    def __init__(self, base_url: str = "http://localhost:8000", token: str = None):
        """
        Initialize performance tester.

        Args:
            base_url: API base URL
            token: JWT authentication token
        """
        self.base_url = base_url
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}

    def test_endpoint(self, method: str, path: str, **kwargs) -> Dict:
        """
        Test single API endpoint.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: Endpoint path
            **kwargs: Additional request arguments

        Returns:
            Dict with timing and status information
        """
        url = f"{self.base_url}{path}"
        start_time = time.time()

        try:
            response = requests.request(
                method,
                url,
                headers=self.headers,
                **kwargs
            )
            elapsed = time.time() - start_time

            return {
                "success": True,
                "status_code": response.status_code,
                "elapsed_ms": elapsed * 1000,
                "size_bytes": len(response.content)
            }

        except Exception as e:
            elapsed = time.time() - start_time

            return {
                "success": False,
                "error": str(e),
                "elapsed_ms": elapsed * 1000
            }

    def load_test(
        self,
        method: str,
        path: str,
        num_requests: int = 100,
        concurrent_users: int = 10,
        **kwargs
    ) -> Dict:
        """
        Perform load test on endpoint.

        Args:
            method: HTTP method
            path: Endpoint path
            num_requests: Total number of requests
            concurrent_users: Number of concurrent threads
            **kwargs: Additional request arguments

        Returns:
            Dict with performance statistics
        """
        print(f"\n🔥 Load Testing: {method} {path}")
        print(f"   Requests: {num_requests}, Concurrent: {concurrent_users}")

        results = []
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [
                executor.submit(self.test_endpoint, method, path, **kwargs)
                for _ in range(num_requests)
            ]

            for future in as_completed(futures):
                results.append(future.result())

        total_time = time.time() - start_time

        # Calculate statistics
        success_results = [r for r in results if r.get("success")]
        failed_results = [r for r in results if not r.get("success")]

        if success_results:
            response_times = [r["elapsed_ms"] for r in success_results]

            stats = {
                "total_requests": num_requests,
                "successful": len(success_results),
                "failed": len(failed_results),
                "total_time_s": round(total_time, 2),
                "requests_per_second": round(num_requests / total_time, 2),
                "response_times": {
                    "min_ms": round(min(response_times), 2),
                    "max_ms": round(max(response_times), 2),
                    "mean_ms": round(statistics.mean(response_times), 2),
                    "median_ms": round(statistics.median(response_times), 2),
                    "p95_ms": round(statistics.quantiles(response_times, n=20)[18], 2),
                    "p99_ms": round(statistics.quantiles(response_times, n=100)[98], 2)
                },
                "status_codes": {}
            }

            # Count status codes
            for result in success_results:
                code = result.get("status_code")
                stats["status_codes"][code] = stats["status_codes"].get(code, 0) + 1

            return stats
        else:
            return {
                "error": "All requests failed",
                "failed": len(failed_results),
                "errors": [r.get("error") for r in failed_results[:5]]
            }

    def print_results(self, stats: Dict):
        """
        Print formatted test results.

        Args:
            stats: Statistics dictionary from load_test
        """
        if "error" in stats:
            print(f"\n❌ Test Failed: {stats['error']}")
            return

        print(f"\n📊 Results:")
        print(f"   Total Requests: {stats['total_requests']}")
        print(f"   Successful: {stats['successful']} ({stats['successful']/stats['total_requests']*100:.1f}%)")
        print(f"   Failed: {stats['failed']}")
        print(f"   Total Time: {stats['total_time_s']}s")
        print(f"   Throughput: {stats['requests_per_second']} req/s")

        print(f"\n⏱️  Response Times:")
        rt = stats["response_times"]
        print(f"   Min: {rt['min_ms']}ms")
        print(f"   Max: {rt['max_ms']}ms")
        print(f"   Mean: {rt['mean_ms']}ms")
        print(f"   Median: {rt['median_ms']}ms")
        print(f"   P95: {rt['p95_ms']}ms")
        print(f"   P99: {rt['p99_ms']}ms")

        print(f"\n📈 Status Codes:")
        for code, count in stats["status_codes"].items():
            print(f"   {code}: {count}")


def run_performance_tests(token: str = None):
    """
    Run comprehensive performance tests.

    Args:
        token: JWT authentication token
    """
    tester = PerformanceTest(token=token)

    print("=" * 60)
    print("PERFORMANCE TEST SUITE")
    print("=" * 60)

    # Test 1: Health check (baseline)
    print("\n🔬 Test 1: Health Check (Baseline)")
    stats = tester.load_test("GET", "/health", num_requests=100, concurrent_users=10)
    tester.print_results(stats)

    if not token:
        print("\n⚠️  Skipping authenticated endpoint tests (no token provided)")
        return

    # Test 2: Analytics engagement endpoint (with caching)
    print("\n🔬 Test 2: Analytics Engagement (Cached)")
    stats = tester.load_test(
        "GET",
        "/api/analytics/engagement",
        num_requests=50,
        concurrent_users=5,
        params={"days": 7}
    )
    tester.print_results(stats)

    # Test 3: List platform entities
    print("\n🔬 Test 3: List Twitter Users")
    stats = tester.load_test(
        "GET",
        "/api/twitter/users",
        num_requests=50,
        concurrent_users=5
    )
    tester.print_results(stats)

    # Test 4: Export summary
    print("\n🔬 Test 4: Export Summary")
    stats = tester.load_test(
        "GET",
        "/api/export/summary",
        num_requests=50,
        concurrent_users=5
    )
    tester.print_results(stats)

    # Test 5: Profile listing
    print("\n🔬 Test 5: List Profiles")
    stats = tester.load_test(
        "GET",
        "/api/profiles",
        num_requests=50,
        concurrent_users=5
    )
    tester.print_results(stats)

    print("\n" + "=" * 60)
    print("✅ Performance Tests Complete")
    print("=" * 60)


def benchmark_cache_effectiveness(token: str):
    """
    Test cache effectiveness by comparing cached vs non-cached requests.

    Args:
        token: JWT authentication token
    """
    tester = PerformanceTest(token=token)

    print("\n" + "=" * 60)
    print("CACHE EFFECTIVENESS BENCHMARK")
    print("=" * 60)

    endpoint = "/api/analytics/engagement"
    params = {"days": 7}

    # First request (cache miss)
    print("\n🔥 First request (cache MISS):")
    result1 = tester.test_endpoint("GET", endpoint, params=params)
    print(f"   Time: {result1.get('elapsed_ms', 0):.2f}ms")
    print(f"   Cache Header: {result1.get('cache_header', 'N/A')}")

    # Second request (cache hit)
    time.sleep(0.5)
    print("\n⚡ Second request (cache HIT):")
    result2 = tester.test_endpoint("GET", endpoint, params=params)
    print(f"   Time: {result2.get('elapsed_ms', 0):.2f}ms")
    print(f"   Cache Header: {result2.get('cache_header', 'N/A')}")

    if result1.get('success') and result2.get('success'):
        speedup = result1['elapsed_ms'] / result2['elapsed_ms']
        print(f"\n📊 Cache Speedup: {speedup:.2f}x faster")

    print("=" * 60)


if __name__ == "__main__":
    import sys

    print("""
    Usage:
        python performance_test.py                    # Run basic tests
        python performance_test.py <jwt_token>        # Run with authentication

    To get JWT token:
        1. Login via API or frontend
        2. Copy token from response or session storage
        3. Pass as argument to this script
    """)

    token = sys.argv[1] if len(sys.argv) > 1 else None

    # Run performance tests
    run_performance_tests(token)

    # Test cache effectiveness (if authenticated)
    if token:
        benchmark_cache_effectiveness(token)
