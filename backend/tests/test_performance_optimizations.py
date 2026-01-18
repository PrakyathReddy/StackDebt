"""
Tests for performance optimizations including caching, monitoring, and database indexing.

These tests verify that the performance optimizations meet the requirements
for analysis timing, caching effectiveness, and rate limiting.

Validates: Requirements 8.1, 8.2, 8.5
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.cache import AnalysisCache, get_cached_analysis, cache_analysis_result
from app.performance_monitor import PerformanceMonitor, PerformanceMetric
from app.schemas import AnalysisResponse, StackAgeResult, Component, ComponentCategory, RiskLevel
from app.rate_limiter import RateLimiter


class TestAnalysisCache:
    """Test the analysis caching system."""
    
    @pytest.fixture
    def cache(self):
        """Create a fresh cache instance for testing."""
        return AnalysisCache(max_size=10, default_ttl_minutes=1)
    
    @pytest.fixture
    def sample_response(self):
        """Create a sample analysis response for testing."""
        return AnalysisResponse(
            stack_age_result=StackAgeResult(
                effective_age=3.2,
                total_components=2,
                risk_distribution={RiskLevel.WARNING: 1, RiskLevel.OK: 1},
                oldest_critical_component=None,
                roast_commentary="Your stack is showing its age!"
            ),
            components=[
                Component(
                    name="Python",
                    version="3.9.0",
                    release_date=datetime(2020, 10, 5).date(),
                    end_of_life_date=None,
                    category=ComponentCategory.PROGRAMMING_LANGUAGE,
                    risk_level=RiskLevel.WARNING,
                    age_years=3.2,
                    weight=0.7
                )
            ],
            analysis_metadata={"test": True},
            generated_at=datetime.now()
        )
    
    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self, cache):
        """Test that cache miss returns None."""
        result = await cache.get("https://example.com", "website")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_result(self, cache, sample_response):
        """Test that cache hit returns the cached result."""
        url = "https://example.com"
        analysis_type = "website"
        
        # Store in cache
        await cache.set(url, analysis_type, sample_response)
        
        # Retrieve from cache
        result = await cache.get(url, analysis_type)
        
        assert result is not None
        assert result.stack_age_result.effective_age == 3.2
        assert len(result.components) == 1
        assert result.components[0].name == "Python"
    
    @pytest.mark.asyncio
    async def test_cache_expiry(self, sample_response):
        """Test that cache entries expire after TTL."""
        # Create cache with very short TTL
        cache = AnalysisCache(max_size=10, default_ttl_minutes=0.01)  # ~0.6 seconds
        
        url = "https://example.com"
        analysis_type = "website"
        
        # Store in cache
        await cache.set(url, analysis_type, sample_response)
        
        # Should be available immediately
        result = await cache.get(url, analysis_type)
        assert result is not None
        
        # Wait for expiry
        await asyncio.sleep(1)
        
        # Should be expired now
        result = await cache.get(url, analysis_type)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_eviction_lru(self, cache, sample_response):
        """Test that cache evicts least recently used entries when full."""
        # Fill cache to capacity
        for i in range(10):
            await cache.set(f"https://example{i}.com", "website", sample_response)
        
        # Access first entry to make it recently used
        await cache.get("https://example0.com", "website")
        
        # Add one more entry to trigger eviction
        await cache.set("https://new-example.com", "website", sample_response)
        
        # First entry should still be there (recently accessed)
        result = await cache.get("https://example0.com", "website")
        assert result is not None
        
        # Second entry should be evicted (least recently used)
        result = await cache.get("https://example1.com", "website")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_stats(self, cache, sample_response):
        """Test cache statistics tracking."""
        url = "https://example.com"
        analysis_type = "website"
        
        # Initial stats
        stats = await cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate_percent"] == 0
        
        # Cache miss
        await cache.get(url, analysis_type)
        stats = await cache.get_stats()
        assert stats["misses"] == 1
        
        # Cache set and hit
        await cache.set(url, analysis_type, sample_response)
        await cache.get(url, analysis_type)
        stats = await cache.get_stats()
        assert stats["hits"] == 1
        assert stats["hit_rate_percent"] == 50.0  # 1 hit out of 2 total requests
    
    @pytest.mark.asyncio
    async def test_cache_key_normalization(self, cache, sample_response):
        """Test that cache keys are normalized consistently."""
        # These should all generate the same cache key
        urls = [
            "https://example.com",
            "https://example.com/",
            "HTTPS://EXAMPLE.COM",
            "https://example.com "
        ]
        
        # Store with first URL
        await cache.set(urls[0], "website", sample_response)
        
        # All variations should hit the cache
        for url in urls:
            result = await cache.get(url, "website")
            assert result is not None, f"Cache miss for URL: {url}"


class TestPerformanceMonitor:
    """Test the performance monitoring system."""
    
    @pytest.fixture
    def monitor(self):
        """Create a fresh performance monitor for testing."""
        return PerformanceMonitor(max_metrics_per_operation=100)
    
    @pytest.mark.asyncio
    async def test_track_operation_success(self, monitor):
        """Test tracking successful operations."""
        async with monitor.track_operation("test_operation"):
            await asyncio.sleep(0.1)  # Simulate work
        
        stats = await monitor.get_stats("test_operation")
        assert "test_operation" in stats
        
        stat = stats["test_operation"]
        assert stat.total_calls == 1
        assert stat.successful_calls == 1
        assert stat.failed_calls == 0
        assert stat.success_rate_percent == 100.0
        assert stat.avg_duration_ms >= 100  # At least 100ms due to sleep
    
    @pytest.mark.asyncio
    async def test_track_operation_failure(self, monitor):
        """Test tracking failed operations."""
        try:
            async with monitor.track_operation("test_operation"):
                raise ValueError("Test error")
        except ValueError:
            pass  # Expected
        
        stats = await monitor.get_stats("test_operation")
        stat = stats["test_operation"]
        assert stat.total_calls == 1
        assert stat.successful_calls == 0
        assert stat.failed_calls == 1
        assert stat.success_rate_percent == 0.0
    
    @pytest.mark.asyncio
    async def test_performance_requirements_checking(self, monitor):
        """Test performance requirement compliance checking."""
        # Record a fast operation (should be compliant)
        await monitor.record_metric("website_analysis", 5000, True)  # 5 seconds
        
        # Record a slow operation (should violate requirement)
        await monitor.record_metric("website_analysis", 15000, True)  # 15 seconds
        
        compliance = await monitor.check_performance_requirements()
        
        assert "website_analysis" in compliance
        website_compliance = compliance["website_analysis"]
        
        assert website_compliance["requirement_ms"] == 10000  # 10 second requirement
        assert website_compliance["avg_duration_ms"] == 10000  # Average of 5s and 15s
        # The average is exactly at the requirement, so it should be compliant
        # But P95 should be non-compliant since the slow request exceeds the requirement
        assert website_compliance["avg_compliant"]  # Average equals requirement
        assert not website_compliance["p95_compliant"]  # P95 exceeds requirement * 1.2
    
    @pytest.mark.asyncio
    async def test_recent_failures_tracking(self, monitor):
        """Test tracking of recent failures for debugging."""
        # Record some successful operations
        await monitor.record_metric("test_op", 100, True)
        await monitor.record_metric("test_op", 200, True)
        
        # Record some failures
        await monitor.record_metric("test_op", 300, False, {"error": "Test error 1"})
        await monitor.record_metric("test_op", 400, False, {"error": "Test error 2"})
        
        failures = await monitor.get_recent_failures("test_op", limit=5)
        
        assert len(failures) == 2
        assert all(not f.success for f in failures)
        assert failures[0].metadata["error"] == "Test error 2"  # Most recent first
        assert failures[1].metadata["error"] == "Test error 1"
    
    @pytest.mark.asyncio
    async def test_performance_summary(self, monitor):
        """Test comprehensive performance summary generation."""
        # Record various operations
        await monitor.record_metric("website_analysis", 8000, True)  # Compliant
        await monitor.record_metric("github_analysis", 25000, True)  # Compliant
        await monitor.record_metric("database_query", 1500, False)   # Non-compliant (too slow + failed)
        
        summary = await monitor.get_performance_summary()
        
        assert "summary" in summary
        assert "operation_stats" in summary
        assert "compliance_status" in summary
        assert "recent_failures" in summary
        
        # Check overall metrics
        assert summary["summary"]["total_calls_last_hour"] == 3
        assert summary["summary"]["overall_success_rate_percent"] < 100  # Due to one failure
        
        # Check that we have stats for each operation
        assert "website_analysis" in summary["operation_stats"]
        assert "github_analysis" in summary["operation_stats"]
        assert "database_query" in summary["operation_stats"]


class TestRateLimiter:
    """Test the rate limiting system."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create a rate limiter for testing."""
        return RateLimiter(requests_per_minute=5, requests_per_hour=20)
    
    @pytest.mark.asyncio
    async def test_rate_limit_allows_normal_usage(self, rate_limiter):
        """Test that normal usage is allowed."""
        client_ip = "192.168.1.1"
        
        # Should allow first few requests
        for i in range(3):
            allowed, info = await rate_limiter.is_allowed(client_ip)
            assert allowed
            # The remaining count is calculated BEFORE recording the current request
            # So after i requests, we should have (5 - i) remaining before this request
            expected_remaining = 5 - i
            assert info["requests_per_minute_remaining"] == expected_remaining
    
    @pytest.mark.asyncio
    async def test_rate_limit_blocks_excessive_requests(self, rate_limiter):
        """Test that excessive requests are blocked."""
        client_ip = "192.168.1.1"
        
        # Use up the minute limit
        for i in range(5):
            allowed, info = await rate_limiter.is_allowed(client_ip)
            assert allowed
        
        # Next request should be blocked
        allowed, info = await rate_limiter.is_allowed(client_ip)
        assert not allowed
        assert info["requests_per_minute_remaining"] == 0
    
    @pytest.mark.asyncio
    async def test_rate_limit_per_ip_isolation(self, rate_limiter):
        """Test that rate limits are isolated per IP address."""
        ip1 = "192.168.1.1"
        ip2 = "192.168.1.2"
        
        # Use up limit for IP1
        for i in range(5):
            allowed, info = await rate_limiter.is_allowed(ip1)
            assert allowed
        
        # IP1 should be blocked
        allowed, info = await rate_limiter.is_allowed(ip1)
        assert not allowed
        
        # IP2 should still be allowed
        allowed, info = await rate_limiter.is_allowed(ip2)
        assert allowed
    
    @pytest.mark.asyncio
    async def test_rate_limit_cleanup(self, rate_limiter):
        """Test that old entries are cleaned up properly."""
        client_ip = "192.168.1.1"
        
        # Make some requests
        for i in range(3):
            await rate_limiter.is_allowed(client_ip)
        
        # Manually trigger cleanup (simulate time passing)
        current_time = time.time()
        minute_count, hour_count = await rate_limiter._cleanup_and_count(client_ip, current_time + 3700)  # 1 hour + 1 minute later
        
        # All entries should be cleaned up
        assert minute_count == 0
        assert hour_count == 0


class TestIntegratedPerformanceOptimizations:
    """Test integrated performance optimizations in realistic scenarios."""
    
    @pytest.mark.asyncio
    async def test_cache_improves_response_time(self):
        """Test that caching significantly improves response times."""
        cache = AnalysisCache(max_size=100, default_ttl_minutes=60)
        
        # Create a sample response
        sample_response = AnalysisResponse(
            stack_age_result=StackAgeResult(
                effective_age=2.5,
                total_components=1,
                risk_distribution={RiskLevel.OK: 1},
                oldest_critical_component=None,
                roast_commentary="Looking good!"
            ),
            components=[],
            analysis_metadata={"cached": True},
            generated_at=datetime.now()
        )
        
        url = "https://github.com/test/repo"
        analysis_type = "github"
        
        # First request - cache miss (simulate slow analysis)
        start_time = time.time()
        await asyncio.sleep(0.1)  # Simulate analysis time
        await cache.set(url, analysis_type, sample_response)
        first_request_time = time.time() - start_time
        
        # Second request - cache hit (should be much faster)
        start_time = time.time()
        cached_result = await cache.get(url, analysis_type)
        second_request_time = time.time() - start_time
        
        assert cached_result is not None
        assert second_request_time < first_request_time / 10  # At least 10x faster
    
    @pytest.mark.asyncio
    async def test_performance_monitoring_tracks_cache_effectiveness(self):
        """Test that performance monitoring can track cache effectiveness."""
        monitor = PerformanceMonitor()
        cache = AnalysisCache(max_size=10, default_ttl_minutes=60)
        
        # Simulate analysis with cache miss
        async with monitor.track_operation("github_analysis", {"cache_hit": False}):
            await asyncio.sleep(0.05)  # Simulate slower analysis
        
        # Simulate analysis with cache hit
        async with monitor.track_operation("github_analysis", {"cache_hit": True}):
            await asyncio.sleep(0.01)  # Simulate faster cached response
        
        stats = await monitor.get_stats("github_analysis")
        github_stats = stats["github_analysis"]
        
        assert github_stats.total_calls == 2
        assert github_stats.successful_calls == 2
        assert github_stats.avg_duration_ms > 0
    
    @pytest.mark.asyncio
    async def test_performance_requirements_compliance(self):
        """Test that the system can track compliance with performance requirements."""
        monitor = PerformanceMonitor()
        
        # Record operations that meet requirements
        await monitor.record_metric("website_analysis", 8000, True)    # 8s < 10s requirement
        await monitor.record_metric("github_analysis", 25000, True)    # 25s < 30s requirement
        await monitor.record_metric("database_query", 500, True)       # 0.5s < 1s requirement
        
        # Record operations that violate requirements - make them clearly non-compliant
        await monitor.record_metric("website_analysis", 15000, True)   # 15s > 10s requirement
        await monitor.record_metric("website_analysis", 16000, True)   # 16s > 10s requirement (make avg > 10s)
        await monitor.record_metric("database_query", 1500, False)     # 1.5s > 1s requirement + failed
        
        compliance = await monitor.check_performance_requirements()
        
        # Website analysis should be non-compliant (average > 10s)
        website_compliance = compliance["website_analysis"]
        assert not website_compliance["overall_compliant"]
        # Average should be (8000 + 15000 + 16000) / 3 = 13000ms > 10000ms
        assert website_compliance["avg_duration_ms"] > 10000
        
        # GitHub analysis should be compliant
        github_compliance = compliance["github_analysis"]
        assert github_compliance["overall_compliant"]
        
        # Database query should be non-compliant (slow + failed)
        db_compliance = compliance["database_query"]
        assert not db_compliance["overall_compliant"]
        assert not db_compliance["success_rate_ok"]  # 50% success rate < 95% requirement


@pytest.mark.asyncio
async def test_end_to_end_performance_optimization():
    """
    End-to-end test of performance optimizations working together.
    
    This test simulates a realistic scenario where caching, performance monitoring,
    and rate limiting all work together to provide optimal performance.
    """
    # Initialize components
    cache = AnalysisCache(max_size=100, default_ttl_minutes=30)
    monitor = PerformanceMonitor()
    rate_limiter = RateLimiter(requests_per_minute=10, requests_per_hour=100)
    
    client_ip = "192.168.1.100"
    url = "https://github.com/example/repo"
    analysis_type = "github"
    
    # Create sample response
    sample_response = AnalysisResponse(
        stack_age_result=StackAgeResult(
            effective_age=4.1,
            total_components=3,
            risk_distribution={RiskLevel.WARNING: 2, RiskLevel.OK: 1},
            oldest_critical_component=None,
            roast_commentary="Time for some updates!"
        ),
        components=[],
        analysis_metadata={"test": "end_to_end"},
        generated_at=datetime.now()
    )
    
    # First request - should be allowed by rate limiter, cache miss, slow analysis
    allowed, rate_info = await rate_limiter.is_allowed(client_ip)
    assert allowed
    
    # Check cache first (this will be a miss)
    cached_result = await cache.get(url, analysis_type)
    assert cached_result is None  # Cache miss
    
    async with monitor.track_operation("github_analysis", {"cache_hit": False, "client_ip": client_ip}):
        await asyncio.sleep(0.02)  # Simulate analysis time
        await cache.set(url, analysis_type, sample_response)
    
    # Second request - should be allowed, cache hit, fast response
    allowed, rate_info = await rate_limiter.is_allowed(client_ip)
    assert allowed
    
    async with monitor.track_operation("github_analysis", {"cache_hit": True, "client_ip": client_ip}):
        cached_result = await cache.get(url, analysis_type)
        assert cached_result is not None
    
    # Verify performance monitoring tracked both requests
    stats = await monitor.get_stats("github_analysis")
    github_stats = stats["github_analysis"]
    assert github_stats.total_calls == 2
    assert github_stats.successful_calls == 2
    
    # Verify cache statistics
    cache_stats = await cache.get_stats()
    assert cache_stats["hits"] == 1
    assert cache_stats["misses"] == 1
    assert cache_stats["hit_rate_percent"] == 50.0
    
    # Verify rate limiting is tracking requests
    assert rate_info["requests_per_minute_remaining"] == 9  # 10 - 1 request (before the second request)
    
    print("End-to-end performance optimization test completed successfully")


if __name__ == "__main__":
    # Run the end-to-end test
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    asyncio.run(test_end_to_end_performance_optimization())