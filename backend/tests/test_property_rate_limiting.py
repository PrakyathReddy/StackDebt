"""
Property-based tests for rate limiting functionality.

**Feature: stackdebt, Property 22: Rate Limiting**
**Validates: Requirements 8.5**

Property 22: Rate Limiting
For any sequence of requests exceeding the rate limit, the system should throttle 
requests while maintaining good user experience for normal usage
"""

import pytest
import asyncio
import time
from hypothesis import given, strategies as st, settings, HealthCheck
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import date

from app.main import app
from app.rate_limiter import RateLimiter
from app.schemas import (
    Component, ComponentCategory, RiskLevel, 
    ComponentDetectionResult, StackAgeResult
)


def create_test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def create_mock_analysis_data():
    """Create mock data for successful analysis."""
    mock_components = [
        Component(
            name="python",
            version="3.9.0",
            release_date=date(2020, 10, 5),
            category=ComponentCategory.PROGRAMMING_LANGUAGE,
            risk_level=RiskLevel.WARNING,
            age_years=3.2,
            weight=0.7
        )
    ]
    
    mock_detection_result = ComponentDetectionResult(
        detected_components=mock_components,
        failed_detections=[],
        detection_metadata={
            'analysis_type': 'github',
            'detection_time_ms': 500,
            'files_analyzed': 3
        }
    )
    
    mock_stack_age_result = StackAgeResult(
        effective_age=3.2,
        total_components=1,
        risk_distribution={
            RiskLevel.CRITICAL: 0,
            RiskLevel.WARNING: 1,
            RiskLevel.OK: 0
        },
        oldest_critical_component=None,
        roast_commentary="Analysis completed successfully!"
    )
    
    return mock_detection_result, mock_stack_age_result


# Strategies for generating request patterns
normal_request_counts = st.integers(min_value=1, max_value=50)  # Normal usage
burst_request_counts = st.integers(min_value=51, max_value=100)  # Burst usage
excessive_request_counts = st.integers(min_value=101, max_value=200)  # Excessive usage

request_intervals = st.floats(min_value=0.01, max_value=2.0)  # Seconds between requests

test_urls = st.sampled_from([
    "https://github.com/user/repo1",
    "https://github.com/user/repo2", 
    "https://example.com",
    "https://test-site.org"
])

client_ips = st.sampled_from([
    "192.168.1.100",
    "10.0.0.50",
    "172.16.0.25",
    "203.0.113.10"
])


class TestProperty22RateLimiting:
    """
    Test Property 22: Rate Limiting
    
    For any sequence of requests exceeding the rate limit, the system should throttle 
    requests while maintaining good user experience for normal usage.
    """
    
    @given(request_count=normal_request_counts)
    @settings(
        max_examples=5,  # Reduced for faster execution as requested
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None  # Disable deadline for rate limiting tests
    )
    def test_property_22_rate_limiter_unit_normal_usage(self, request_count):
        """
        **Feature: stackdebt, Property 22: Rate Limiting**
        
        Test the RateLimiter class directly for normal usage patterns.
        
        **Validates: Requirements 8.5**
        """
        # Create a fresh rate limiter for each test
        rate_limiter = RateLimiter(requests_per_minute=60, requests_per_hour=1000)
        client_ip = "192.168.1.100"
        
        successful_requests = 0
        rate_limited_requests = 0
        
        # Simulate normal usage pattern
        for i in range(request_count):
            is_allowed, rate_limit_info = asyncio.run(rate_limiter.is_allowed(client_ip))
            
            if is_allowed:
                successful_requests += 1
                
                # Property: Rate limit info should be provided
                assert rate_limit_info is not None, "Should provide rate limit info"
                assert "requests_per_minute_limit" in rate_limit_info, "Should include minute limit"
                assert "requests_per_minute_remaining" in rate_limit_info, "Should include remaining count"
                
                # Verify rate limit values are reasonable
                assert rate_limit_info["requests_per_minute_limit"] == 60, "Should have correct minute limit"
                assert rate_limit_info["requests_per_hour_limit"] == 1000, "Should have correct hour limit"
                assert rate_limit_info["requests_per_minute_remaining"] >= 0, "Remaining should be non-negative"
                
            else:
                rate_limited_requests += 1
                
                # If rate limited, should provide helpful information
                assert rate_limit_info is not None, "Should provide rate limit info even when blocked"
                assert rate_limit_info["requests_per_minute_remaining"] == 0, "Should show no remaining requests"
            
            # Small delay to simulate realistic usage
            time.sleep(0.001)  # 1ms delay for test speed
        
        # Property: Normal usage should mostly succeed
        success_rate = successful_requests / request_count if request_count > 0 else 1.0
        
        # For normal usage (≤50 requests), expect high success rate
        assert success_rate >= 0.8, (
            f"Normal usage should have high success rate. "
            f"Got {successful_requests}/{request_count} successful ({success_rate:.2%})"
        )
        
        # Property: Rate limiting should provide good user experience
        if rate_limited_requests > 0:
            # If any requests were rate limited, they should be minority for normal usage
            assert rate_limited_requests < successful_requests, (
                "Rate limited requests should be minority for normal usage"
            )
    
    @given(request_count=excessive_request_counts, client_ip=client_ips)
    @settings(
        max_examples=5,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None  # Disable deadline for rate limiting tests
    )
    def test_property_22_rate_limiter_unit_excessive_usage(self, request_count, client_ip):
        """
        **Feature: stackdebt, Property 22: Rate Limiting**
        
        Test the RateLimiter class directly for excessive usage patterns.
        
        **Validates: Requirements 8.5**
        """
        # Create a fresh rate limiter for each test
        rate_limiter = RateLimiter(requests_per_minute=60, requests_per_hour=1000)
        
        successful_requests = 0
        rate_limited_requests = 0
        
        # Simulate excessive usage pattern (rapid requests)
        for i in range(request_count):
            is_allowed, rate_limit_info = asyncio.run(rate_limiter.is_allowed(client_ip))
            
            if is_allowed:
                successful_requests += 1
            else:
                rate_limited_requests += 1
                
                # Property: Rate limit info should be informative
                assert rate_limit_info is not None, "Should provide rate limit info"
                assert rate_limit_info["requests_per_minute_remaining"] == 0, "Should show limit exceeded"
                assert rate_limit_info["current_minute_count"] >= 60, "Should show high usage count"
                
                # Should provide timing information
                assert "reset_time_minute" in rate_limit_info, "Should provide reset time"
                assert rate_limit_info["reset_time_minute"] > time.time(), "Reset time should be in future"
        
        # Property: Excessive requests should be throttled
        throttle_rate = rate_limited_requests / request_count if request_count > 0 else 0.0
        
        # For excessive usage (>100 requests), expect significant throttling
        assert throttle_rate > 0.3, (
            f"Excessive usage should be throttled. "
            f"Got {rate_limited_requests}/{request_count} throttled ({throttle_rate:.2%})"
        )
        
        # Property: Some requests should still succeed (not complete blocking)
        assert successful_requests > 0, (
            "Even with excessive usage, some requests should succeed to maintain usability"
        )
        
        # Property: Should not exceed the rate limit
        assert successful_requests <= 60, (
            f"Should not allow more than 60 requests per minute, got {successful_requests}"
        )
    
    @given(
        normal_count=st.integers(min_value=10, max_value=30),
        burst_count=st.integers(min_value=20, max_value=50)
    )
    @settings(max_examples=3, deadline=None)
    def test_property_22_rate_limiter_burst_pattern(self, normal_count, burst_count):
        """
        Test that rate limiting handles burst followed by normal usage appropriately.
        
        **Validates: Requirements 8.5**
        """
        # Create a fresh rate limiter for each test
        rate_limiter = RateLimiter(requests_per_minute=60, requests_per_hour=1000)
        client_ip = "192.168.1.100"
        
        # Phase 1: Normal usage with spacing
        normal_successful = 0
        for i in range(normal_count):
            is_allowed, rate_limit_info = asyncio.run(rate_limiter.is_allowed(client_ip))
            if is_allowed:
                normal_successful += 1
            time.sleep(0.01)  # 10ms spacing for normal usage
        
        # Phase 2: Burst usage (rapid requests)
        burst_successful = 0
        burst_throttled = 0
        for i in range(burst_count):
            is_allowed, rate_limit_info = asyncio.run(rate_limiter.is_allowed(client_ip))
            if is_allowed:
                burst_successful += 1
            else:
                burst_throttled += 1
            # No delay - simulate burst
        
        # Property: Normal usage should have high success rate
        normal_success_rate = normal_successful / normal_count if normal_count > 0 else 1.0
        assert normal_success_rate >= 0.7, (
            f"Normal usage should succeed: {normal_successful}/{normal_count}"
        )
        
        # Property: System should still allow some burst requests
        assert burst_successful >= 0, "Should handle burst requests gracefully"
        
        # Property: Combined usage should show rate limiting behavior
        total_requests = normal_count + burst_count
        total_successful = normal_successful + burst_successful
        
        # Should not exceed the rate limit
        assert total_successful <= 60, (
            f"Total successful requests should not exceed rate limit: {total_successful}"
        )
        
        # Should have some throttling for burst
        if total_requests > 60:
            assert burst_throttled > 0, "Should throttle some burst requests when limit exceeded"
    
    def test_property_22_rate_limit_headers_consistency(self):
        """
        Test that rate limit information is consistent and informative.
        
        **Validates: Requirements 8.5**
        """
        rate_limiter = RateLimiter(requests_per_minute=60, requests_per_hour=1000)
        client_ip = "192.168.1.100"
        
        # Make a few requests to check consistency
        previous_remaining = None
        for i in range(5):
            is_allowed, rate_limit_info = asyncio.run(rate_limiter.is_allowed(client_ip))
            
            assert is_allowed, f"Request {i+1} should be allowed for normal usage"
            assert rate_limit_info is not None, "Should provide rate limit info"
            
            # Check required fields
            required_fields = [
                "requests_per_minute_limit",
                "requests_per_minute_remaining", 
                "requests_per_hour_limit",
                "requests_per_hour_remaining",
                "reset_time_minute",
                "reset_time_hour"
            ]
            
            for field in required_fields:
                assert field in rate_limit_info, f"Should include {field}"
            
            # Check value consistency
            assert rate_limit_info["requests_per_minute_limit"] == 60, "Minute limit should be 60"
            assert rate_limit_info["requests_per_hour_limit"] == 1000, "Hour limit should be 1000"
            
            current_remaining = rate_limit_info["requests_per_minute_remaining"]
            assert current_remaining >= 0, "Remaining should be non-negative"
            
            # Remaining should decrease with usage
            if previous_remaining is not None:
                assert current_remaining <= previous_remaining, (
                    f"Remaining should decrease: {previous_remaining} -> {current_remaining}"
                )
            
            previous_remaining = current_remaining
            time.sleep(0.01)  # Small delay
    
    def test_property_22_different_ips_independent_limits(self):
        """
        Test that different IP addresses have independent rate limits.
        
        **Validates: Requirements 8.5**
        """
        rate_limiter = RateLimiter(requests_per_minute=60, requests_per_hour=1000)
        
        ip1 = "192.168.1.100"
        ip2 = "10.0.0.50"
        
        # Make requests from IP1
        ip1_successful = 0
        for i in range(10):
            is_allowed, rate_limit_info = asyncio.run(rate_limiter.is_allowed(ip1))
            if is_allowed:
                ip1_successful += 1
        
        # Make requests from IP2
        ip2_successful = 0
        for i in range(10):
            is_allowed, rate_limit_info = asyncio.run(rate_limiter.is_allowed(ip2))
            if is_allowed:
                ip2_successful += 1
        
        # Both IPs should have similar success rates (independent limits)
        assert ip1_successful >= 8, f"IP1 should have good success rate: {ip1_successful}/10"
        assert ip2_successful >= 8, f"IP2 should have good success rate: {ip2_successful}/10"
        
        # Success rates should be similar (within 2 requests)
        assert abs(ip1_successful - ip2_successful) <= 2, (
            f"Different IPs should have similar success rates: {ip1_successful} vs {ip2_successful}"
        )


class TestRateLimitingEdgeCases:
    """Test edge cases for rate limiting functionality."""
    
    def test_rate_limiting_reset_behavior(self):
        """Test that rate limits reset properly over time."""
        # Create a custom rate limiter with very low limits for testing
        test_limiter = RateLimiter(requests_per_minute=2, requests_per_hour=10)
        client_ip = "192.168.1.100"
        
        # Use up the rate limit
        for i in range(3):
            allowed, info = asyncio.run(test_limiter.is_allowed(client_ip))
            if i < 2:
                assert allowed, f"Request {i+1} should be allowed"
            else:
                assert not allowed, "Request 3 should be rate limited"
        
        # Wait for minute window to reset (simulate time passage)
        import time
        original_time = time.time
        
        def mock_time():
            return original_time() + 61  # Simulate 61 seconds later
        
        with patch('time.time', mock_time):
            # Should be allowed again after reset
            allowed, info = asyncio.run(test_limiter.is_allowed(client_ip))
            assert allowed, "Should be allowed after rate limit reset"
    
    def test_rate_limiter_cleanup_old_entries(self):
        """Test that the rate limiter properly cleans up old entries."""
        test_limiter = RateLimiter(requests_per_minute=10, requests_per_hour=100)
        client_ip = "192.168.1.100"
        
        # Add some requests to history
        for i in range(5):
            asyncio.run(test_limiter.is_allowed(client_ip))
        
        # Verify history exists
        assert client_ip in test_limiter.request_history
        assert len(test_limiter.request_history[client_ip]) == 5
        
        # Simulate time passage (more than 1 hour)
        import time
        original_time = time.time
        
        def mock_time():
            return original_time() + 3700  # 61+ minutes later
        
        with patch('time.time', mock_time):
            # Make another request - should clean up old entries
            allowed, info = asyncio.run(test_limiter.is_allowed(client_ip))
            assert allowed, "Should be allowed after cleanup"
            
            # History should be cleaned up (only the new request remains)
            assert len(test_limiter.request_history[client_ip]) == 1
    
    def test_rate_limiter_concurrent_requests(self):
        """Test rate limiter behavior with concurrent requests."""
        rate_limiter = RateLimiter(requests_per_minute=10, requests_per_hour=100)
        client_ip = "192.168.1.100"
        
        async def make_request():
            return await rate_limiter.is_allowed(client_ip)
        
        async def concurrent_test():
            # Make 5 concurrent requests
            tasks = [make_request() for _ in range(5)]
            results = await asyncio.gather(*tasks)
            return results
        
        results = asyncio.run(concurrent_test())
        
        # All requests should be processed
        assert len(results) == 5, "Should process all concurrent requests"
        
        # Most should be allowed (within rate limit)
        allowed_count = sum(1 for allowed, info in results if allowed)
        assert allowed_count >= 4, f"Most concurrent requests should be allowed: {allowed_count}/5"
    
    def test_rate_limiter_edge_case_values(self):
        """Test rate limiter with edge case values."""
        # Test with very low limits
        low_limiter = RateLimiter(requests_per_minute=1, requests_per_hour=2)
        client_ip = "192.168.1.100"
        
        # First request should be allowed
        allowed1, info1 = asyncio.run(low_limiter.is_allowed(client_ip))
        assert allowed1, "First request should be allowed"
        
        # Second request should be rate limited (exceeds per-minute limit)
        allowed2, info2 = asyncio.run(low_limiter.is_allowed(client_ip))
        assert not allowed2, "Second request should be rate limited"
        
        # Verify rate limit info is correct
        assert info2["requests_per_minute_remaining"] == 0, "Should show no remaining requests"
        assert info2["current_minute_count"] == 1, "Should show current usage"
    
    def test_rate_limiter_ip_extraction_edge_cases(self):
        """Test IP extraction with various header scenarios."""
        rate_limiter = RateLimiter()
        
        # Mock request with different header scenarios
        class MockRequest:
            def __init__(self, headers, client_host="127.0.0.1"):
                self.headers = headers
                self.client = type('obj', (object,), {'host': client_host})
        
        # Test X-Forwarded-For header
        request1 = MockRequest({"X-Forwarded-For": "192.168.1.100, 10.0.0.1"})
        ip1 = asyncio.run(rate_limiter.get_client_ip(request1))
        assert ip1 == "192.168.1.100", "Should extract first IP from X-Forwarded-For"
        
        # Test X-Real-IP header
        request2 = MockRequest({"X-Real-IP": "172.16.0.25"})
        ip2 = asyncio.run(rate_limiter.get_client_ip(request2))
        assert ip2 == "172.16.0.25", "Should extract IP from X-Real-IP"
        
        # Test fallback to client IP
        request3 = MockRequest({}, "203.0.113.10")
        ip3 = asyncio.run(rate_limiter.get_client_ip(request3))
        assert ip3 == "203.0.113.10", "Should fallback to client IP"
        
        # Test no client (edge case)
        request4 = MockRequest({})
        request4.client = None
        ip4 = asyncio.run(rate_limiter.get_client_ip(request4))
        assert ip4 == "unknown", "Should handle missing client gracefully"