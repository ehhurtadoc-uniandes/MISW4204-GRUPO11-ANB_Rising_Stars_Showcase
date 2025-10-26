#!/usr/bin/env python3
"""
ANB Rising Stars Showcase - Load Testing Script
This script performs load testing on the deployed AWS application
"""

import asyncio
import aiohttp
import time
import json
import statistics
from datetime import datetime
from typing import List, Dict, Any
import argparse


class LoadTester:
    def __init__(self, base_url: str, concurrent_users: int = 10, duration_seconds: int = 60):
        self.base_url = base_url.rstrip('/')
        self.concurrent_users = concurrent_users
        self.duration_seconds = duration_seconds
        self.results = []
        self.start_time = None
        self.end_time = None
    
    async def make_request(self, session: aiohttp.ClientSession, endpoint: str, method: str = "GET") -> Dict[str, Any]:
        """Make a single HTTP request and record metrics"""
        start_time = time.time()
        try:
            async with session.request(method, f"{self.base_url}{endpoint}") as response:
                response_text = await response.text()
                end_time = time.time()
                
                return {
                    "endpoint": endpoint,
                    "method": method,
                    "status_code": response.status,
                    "response_time": end_time - start_time,
                    "success": 200 <= response.status < 400,
                    "timestamp": datetime.now().isoformat(),
                    "response_size": len(response_text)
                }
        except Exception as e:
            end_time = time.time()
            return {
                "endpoint": endpoint,
                "method": method,
                "status_code": 0,
                "response_time": end_time - start_time,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "response_size": 0
            }
    
    async def user_simulation(self, session: aiohttp.ClientSession, user_id: int):
        """Simulate a single user's behavior"""
        user_results = []
        end_time = time.time() + self.duration_seconds
        
        # Test endpoints to simulate user behavior
        endpoints = [
            "/",
            "/health",
            "/docs",
            "/api/public/videos",
            "/api/public/videos/featured"
        ]
        
        while time.time() < end_time:
            for endpoint in endpoints:
                result = await self.make_request(session, endpoint)
                result["user_id"] = user_id
                user_results.append(result)
                
                # Small delay between requests
                await asyncio.sleep(0.1)
        
        return user_results
    
    async def run_load_test(self):
        """Run the load test"""
        print(f"Starting load test with {self.concurrent_users} concurrent users for {self.duration_seconds} seconds")
        print(f"Target URL: {self.base_url}")
        
        self.start_time = time.time()
        
        # Create HTTP session with connection pooling
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Create tasks for concurrent users
            tasks = []
            for user_id in range(self.concurrent_users):
                task = asyncio.create_task(self.user_simulation(session, user_id))
                tasks.append(task)
            
            # Wait for all tasks to complete
            user_results = await asyncio.gather(*tasks)
            
            # Flatten results
            for user_result in user_results:
                self.results.extend(user_result)
        
        self.end_time = time.time()
        
        print(f"Load test completed. Total requests: {len(self.results)}")
    
    def analyze_results(self) -> Dict[str, Any]:
        """Analyze the test results"""
        if not self.results:
            return {"error": "No results to analyze"}
        
        # Separate successful and failed requests
        successful_requests = [r for r in self.results if r["success"]]
        failed_requests = [r for r in self.results if not r["success"]]
        
        # Calculate response times
        response_times = [r["response_time"] for r in successful_requests]
        
        # Calculate statistics
        analysis = {
            "test_duration": self.end_time - self.start_time,
            "total_requests": len(self.results),
            "successful_requests": len(successful_requests),
            "failed_requests": len(failed_requests),
            "success_rate": len(successful_requests) / len(self.results) * 100 if self.results else 0,
            "requests_per_second": len(self.results) / (self.end_time - self.start_time),
            "response_times": {
                "min": min(response_times) if response_times else 0,
                "max": max(response_times) if response_times else 0,
                "mean": statistics.mean(response_times) if response_times else 0,
                "median": statistics.median(response_times) if response_times else 0,
                "p95": self._percentile(response_times, 95) if response_times else 0,
                "p99": self._percentile(response_times, 99) if response_times else 0
            },
            "status_codes": self._count_status_codes(),
            "endpoint_performance": self._analyze_endpoints(),
            "errors": [r for r in failed_requests if "error" in r]
        }
        
        return analysis
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def _count_status_codes(self) -> Dict[int, int]:
        """Count status codes"""
        status_counts = {}
        for result in self.results:
            status = result["status_code"]
            status_counts[status] = status_counts.get(status, 0) + 1
        return status_counts
    
    def _analyze_endpoints(self) -> Dict[str, Dict[str, Any]]:
        """Analyze performance by endpoint"""
        endpoint_stats = {}
        
        for result in self.results:
            endpoint = result["endpoint"]
            if endpoint not in endpoint_stats:
                endpoint_stats[endpoint] = {
                    "total_requests": 0,
                    "successful_requests": 0,
                    "response_times": []
                }
            
            endpoint_stats[endpoint]["total_requests"] += 1
            if result["success"]:
                endpoint_stats[endpoint]["successful_requests"] += 1
                endpoint_stats[endpoint]["response_times"].append(result["response_time"])
        
        # Calculate statistics for each endpoint
        for endpoint, stats in endpoint_stats.items():
            response_times = stats["response_times"]
            stats["success_rate"] = stats["successful_requests"] / stats["total_requests"] * 100
            stats["avg_response_time"] = statistics.mean(response_times) if response_times else 0
            stats["min_response_time"] = min(response_times) if response_times else 0
            stats["max_response_time"] = max(response_times) if response_times else 0
            stats["p95_response_time"] = self._percentile(response_times, 95) if response_times else 0
        
        return endpoint_stats
    
    def save_results(self, filename: str = None):
        """Save results to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"load_test_results_{timestamp}.json"
        
        results_data = {
            "test_config": {
                "base_url": self.base_url,
                "concurrent_users": self.concurrent_users,
                "duration_seconds": self.duration_seconds
            },
            "analysis": self.analyze_results(),
            "raw_results": self.results
        }
        
        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"Results saved to {filename}")
        return filename
    
    def print_summary(self):
        """Print a summary of the test results"""
        analysis = self.analyze_results()
        
        print("\n" + "="*60)
        print("LOAD TEST SUMMARY")
        print("="*60)
        print(f"Test Duration: {analysis['test_duration']:.2f} seconds")
        print(f"Total Requests: {analysis['total_requests']}")
        print(f"Successful Requests: {analysis['successful_requests']}")
        print(f"Failed Requests: {analysis['failed_requests']}")
        print(f"Success Rate: {analysis['success_rate']:.2f}%")
        print(f"Requests per Second: {analysis['requests_per_second']:.2f}")
        
        print("\nResponse Times:")
        rt = analysis['response_times']
        print(f"  Min: {rt['min']:.3f}s")
        print(f"  Max: {rt['max']:.3f}s")
        print(f"  Mean: {rt['mean']:.3f}s")
        print(f"  Median: {rt['median']:.3f}s")
        print(f"  95th Percentile: {rt['p95']:.3f}s")
        print(f"  99th Percentile: {rt['p99']:.3f}s")
        
        print("\nStatus Codes:")
        for status, count in analysis['status_codes'].items():
            print(f"  {status}: {count}")
        
        print("\nEndpoint Performance:")
        for endpoint, stats in analysis['endpoint_performance'].items():
            print(f"  {endpoint}:")
            print(f"    Requests: {stats['total_requests']}")
            print(f"    Success Rate: {stats['success_rate']:.2f}%")
            print(f"    Avg Response Time: {stats['avg_response_time']:.3f}s")
            print(f"    95th Percentile: {stats['p95_response_time']:.3f}s")
        
        if analysis['errors']:
            print(f"\nErrors ({len(analysis['errors'])}):")
            for error in analysis['errors'][:5]:  # Show first 5 errors
                print(f"  {error.get('error', 'Unknown error')}")


async def main():
    parser = argparse.ArgumentParser(description="Load test the ANB Rising Stars Showcase API")
    parser.add_argument("--url", required=True, help="Base URL of the API")
    parser.add_argument("--users", type=int, default=10, help="Number of concurrent users")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("--output", help="Output file for results")
    
    args = parser.parse_args()
    
    # Create and run load tester
    tester = LoadTester(
        base_url=args.url,
        concurrent_users=args.users,
        duration_seconds=args.duration
    )
    
    try:
        await tester.run_load_test()
        tester.print_summary()
        tester.save_results(args.output)
    except KeyboardInterrupt:
        print("\nLoad test interrupted by user")
    except Exception as e:
        print(f"Error during load test: {e}")


if __name__ == "__main__":
    asyncio.run(main())
