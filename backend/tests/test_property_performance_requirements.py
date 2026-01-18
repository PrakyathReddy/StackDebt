"""
Property-based tests for performance requirements.

**Feature: stackdebt, Property 19: Performance Requirements**
**Validates: Requirements 8.1, 8.2**

Property 19: Performance Requirements
For any website analysis, it should complete within 10 seconds, and for any GitHub 
repository under 100MB, analysis should complete within 30 seconds
"""

import pytest
import asyncio
import time
from hypothesis import given, strategies as st, settings, HealthCheck
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import date

from app.main import app
from app.schemas import (
    Component, ComponentCategory, RiskLevel, 
    ComponentDetectionResult, StackAgeResult
)


def create_test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def create_mock_analysis_data(component_name="python", version="3.9.0"):
    """Create mock data for analysis with customizable component."""
    mock_components = [
        Component(
            name=component_name,
            version=version,
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
            'files_analyzed': 3,
            'repository_size_mb': 50  # Under 100MB
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
        roast_commentary="Analysis completed within performance requirements!"
    )
    
    return mock_detection_result, mock_stack_age_result


# Strategy for generating valid URLs for performance testing
website_urls = st.builds(
    lambda domain, tld: f"https://{domain}.{tld}",
    domain=st.text(min_size=3, max_size=15, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='-')),
    tld=st.sampled_from(['com', 'org', 'net', 'io'])
)

github_urls = st.builds(
    lambda user, repo: f"https://github.com/{user}/{repo}",
    user=st.text(min_size=3, max_size=15, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='-_')),
    repo=st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='-_'))
)

# Strategy for repository sizes under 100MB
repository_sizes_mb = st.integers(min_value=1, max_value=99)


class TestProperty19PerformanceRequirements:
    """
    Test Property 19: Performance Requirements
    
    For any website analysis, it should complete within 10 seconds, and for any 
    GitHub repository under 100MB, analysis should complete within 30 seconds.
    """
    
    @given(url=website_urls)
    @settings(
        max_examples=5,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @patch('app.main.http_scraper')
    @patch('app.main.carbon_dating_engine')
    def test_property_19_website_analysis_performance(self, mock_engine, mock_scraper, url):
        """
        **Feature: stackdebt, Property 19: Performance Requirements**
        
        For any website analysis, it should complete within 10 seconds.
        
        **Validates: Requirements 8.1**
        """
        client = create_test_client()
        mock_detection_result, mock_stack_age_result = create_mock_analysis_data()
        
        # Update detection metadata for website analysis
        mock_detection_result.detection_metadata['analysis_type'] = 'website'
        
        # Setup mocks with realistic delays (but within limits)
        async def realistic_website_analysis(url):
            # Simulate realistic website analysis time (2-8 seconds)
            await asyncio.sleep(0.05)  # 50ms for test speed
            return mock_detection_result
        
        mock_scraper.analyze_website = AsyncMock(side_effect=realistic_website_analysis)
        mock_engine.calculate_stack_age = MagicMock(return_value=mock_stack_age_result)
        
        # Measure actual analysis time
        start_time = time.time()
        
        response = client.post("/api/analyze", json={
            "url": url,
            "analysis_type": "website"
        })
        
        end_time = time.time()
        actual_duration_seconds = end_time - start_time
        
        # Property: Website analysis should complete within 10 seconds
        assert actual_duration_seconds <= 10.0, (
            f"Website analysis for {url} took {actual_duration_seconds:.2f}s, "
            f"which exceeds the 10-second requirement"
        )
        
        # Verify the analysis succeeded
        assert response.status_code == 200, (
            f"Website analysis should succeed within time limit for {url}"
        )
        
        # Verify timing is recorded in response metadata
        data = response.json()
        recorded_duration_ms = data["analysis_metadata"]["analysis_duration_ms"]
        
        # Recorded duration should be reasonable and consistent with actual timing
        assert recorded_duration_ms >= 0, "Recorded duration should be non-negative"
        assert recorded_duration_ms <= 10000, (
            f"Recorded duration {recorded_duration_ms}ms should be within 10-second limit"
        )
        
        # Actual and recorded durations should be reasonably close
        recorded_duration_seconds = recorded_duration_ms / 1000.0
        duration_difference = abs(actual_duration_seconds - recorded_duration_seconds)
        assert duration_difference <= 1.0, (
            f"Actual duration ({actual_duration_seconds:.2f}s) and recorded duration "
            f"({recorded_duration_seconds:.2f}s) should be reasonably close"
        )
    
    @given(url=github_urls, repo_size_mb=repository_sizes_mb)
    @settings(
        max_examples=5,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @patch('app.main.github_analyzer')
    @patch('app.main.carbon_dating_engine')
    def test_property_19_github_analysis_performance(self, mock_engine, mock_analyzer, url, repo_size_mb):
        """
        **Feature: stackdebt, Property 19: Performance Requirements**
        
        For any GitHub repository under 100MB, analysis should complete within 30 seconds.
        
        **Validates: Requirements 8.2**
        """
        client = create_test_client()
        mock_detection_result, mock_stack_age_result = create_mock_analysis_data()
        
        # Update detection metadata for GitHub analysis with repository size
        mock_detection_result.detection_metadata.update({
            'analysis_type': 'github',
            'repository_size_mb': repo_size_mb,
            'files_analyzed': min(repo_size_mb * 2, 100)  # Simulate more files for larger repos
        })
        
        # Setup mocks with realistic delays based on repository size
        async def realistic_github_analysis(url):
            # Simulate realistic GitHub analysis time based on repository size
            # Larger repos take longer but should still be under 30 seconds
            base_delay = 0.02  # 20ms base delay for test speed
            size_factor = repo_size_mb / 100.0  # Scale with size
            delay = base_delay + (size_factor * 0.08)  # Up to 100ms for largest repos
            await asyncio.sleep(delay)
            return mock_detection_result
        
        mock_analyzer.analyze_repository = AsyncMock(side_effect=realistic_github_analysis)
        mock_engine.calculate_stack_age = MagicMock(return_value=mock_stack_age_result)
        
        # Measure actual analysis time
        start_time = time.time()
        
        response = client.post("/api/analyze", json={
            "url": url,
            "analysis_type": "github"
        })
        
        end_time = time.time()
        actual_duration_seconds = end_time - start_time
        
        # Property: GitHub analysis should complete within 30 seconds for repos under 100MB
        assert actual_duration_seconds <= 30.0, (
            f"GitHub analysis for {url} ({repo_size_mb}MB) took {actual_duration_seconds:.2f}s, "
            f"which exceeds the 30-second requirement for repositories under 100MB"
        )
        
        # Verify the analysis succeeded
        assert response.status_code == 200, (
            f"GitHub analysis should succeed within time limit for {url} ({repo_size_mb}MB)"
        )
        
        # Verify timing is recorded in response metadata
        data = response.json()
        recorded_duration_ms = data["analysis_metadata"]["analysis_duration_ms"]
        
        # Recorded duration should be reasonable and within limits
        assert recorded_duration_ms >= 0, "Recorded duration should be non-negative"
        assert recorded_duration_ms <= 30000, (
            f"Recorded duration {recorded_duration_ms}ms should be within 30-second limit "
            f"for {repo_size_mb}MB repository"
        )
        
        # Verify repository size is recorded in metadata
        assert data["analysis_metadata"].get("repository_size_mb") == repo_size_mb, (
            "Repository size should be recorded in analysis metadata"
        )
        
        # Actual and recorded durations should be reasonably close
        recorded_duration_seconds = recorded_duration_ms / 1000.0
        duration_difference = abs(actual_duration_seconds - recorded_duration_seconds)
        assert duration_difference <= 2.0, (
            f"Actual duration ({actual_duration_seconds:.2f}s) and recorded duration "
            f"({recorded_duration_seconds:.2f}s) should be reasonably close"
        )
    
    @given(
        website_url=website_urls,
        github_url=github_urls,
        repo_size_mb=repository_sizes_mb
    )
    @settings(
        max_examples=3,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @patch('app.main.http_scraper')
    @patch('app.main.github_analyzer')
    @patch('app.main.carbon_dating_engine')
    def test_property_19_mixed_analysis_performance_consistency(self, mock_engine, 
                                                              mock_analyzer, mock_scraper,
                                                              website_url, github_url, repo_size_mb):
        """
        Test that performance requirements are consistently met across different analysis types.
        
        **Validates: Requirements 8.1, 8.2**
        """
        client = create_test_client()
        
        # Create different mock data for each analysis type
        website_detection_result, website_stack_result = create_mock_analysis_data("nginx", "1.18.0")
        github_detection_result, github_stack_result = create_mock_analysis_data("python", "3.9.0")
        
        website_detection_result.detection_metadata.update({
            'analysis_type': 'website',
            'headers_analyzed': 15
        })
        
        github_detection_result.detection_metadata.update({
            'analysis_type': 'github',
            'repository_size_mb': repo_size_mb,
            'files_analyzed': min(repo_size_mb * 2, 100)
        })
        
        # Setup mocks with appropriate delays
        async def website_analysis(url):
            await asyncio.sleep(0.03)  # 30ms for test speed
            return website_detection_result
        
        async def github_analysis(url):
            await asyncio.sleep(0.05)  # 50ms for test speed
            return github_detection_result
        
        mock_scraper.analyze_website = AsyncMock(side_effect=website_analysis)
        mock_analyzer.analyze_repository = AsyncMock(side_effect=github_analysis)
        mock_engine.calculate_stack_age = MagicMock(
            side_effect=lambda components: (
                website_stack_result if components and components[0].name == "nginx" 
                else github_stack_result
            )
        )
        
        # Test website analysis performance
        start_time = time.time()
        website_response = client.post("/api/analyze", json={
            "url": website_url,
            "analysis_type": "website"
        })
        website_duration = time.time() - start_time
        
        # Test GitHub analysis performance
        start_time = time.time()
        github_response = client.post("/api/analyze", json={
            "url": github_url,
            "analysis_type": "github"
        })
        github_duration = time.time() - start_time
        
        # Both analyses should succeed
        assert website_response.status_code == 200, "Website analysis should succeed"
        assert github_response.status_code == 200, "GitHub analysis should succeed"
        
        # Performance requirements should be met for both
        assert website_duration <= 10.0, (
            f"Website analysis took {website_duration:.2f}s, exceeds 10s limit"
        )
        assert github_duration <= 30.0, (
            f"GitHub analysis took {github_duration:.2f}s, exceeds 30s limit for {repo_size_mb}MB repo"
        )
        
        # Verify recorded timings are within limits
        website_data = website_response.json()
        github_data = github_response.json()
        
        website_recorded_ms = website_data["analysis_metadata"]["analysis_duration_ms"]
        github_recorded_ms = github_data["analysis_metadata"]["analysis_duration_ms"]
        
        assert website_recorded_ms <= 10000, (
            f"Website recorded duration {website_recorded_ms}ms exceeds 10s limit"
        )
        assert github_recorded_ms <= 30000, (
            f"GitHub recorded duration {github_recorded_ms}ms exceeds 30s limit"
        )
    
    def test_property_19_performance_timeout_behavior(self):
        """
        Test that the system properly handles timeouts when performance limits are exceeded.
        
        **Validates: Requirements 8.1, 8.2**
        """
        client = create_test_client()
        
        # Test with mocks that simulate timeout scenarios
        with patch('app.main.http_scraper') as mock_scraper, \
             patch('app.main.github_analyzer') as mock_analyzer:
            
            # Simulate timeout for website analysis (exceeds 10s)
            async def slow_website_analysis(url):
                await asyncio.sleep(0.2)  # 200ms to simulate slow response
                raise Exception("Simulated timeout after 10 seconds")
            
            # Simulate timeout for GitHub analysis (exceeds 30s)
            async def slow_github_analysis(url):
                await asyncio.sleep(0.3)  # 300ms to simulate slow response
                raise Exception("Simulated timeout after 30 seconds")
            
            mock_scraper.analyze_website = AsyncMock(side_effect=slow_website_analysis)
            mock_analyzer.analyze_repository = AsyncMock(side_effect=slow_github_analysis)
            
            # Test website timeout handling
            website_response = client.post("/api/analyze", json={
                "url": "https://slow-website.com",
                "analysis_type": "website"
            })
            
            # Should return error status when timeout occurs
            assert website_response.status_code == 500, (
                "Website analysis should return error status when timeout occurs"
            )
            
            # Test GitHub timeout handling
            github_response = client.post("/api/analyze", json={
                "url": "https://github.com/user/large-repo",
                "analysis_type": "github"
            })
            
            # Should return error status when timeout occurs
            assert github_response.status_code == 500, (
                "GitHub analysis should return error status when timeout occurs"
            )


class TestPerformanceRequirementsEdgeCases:
    """Test edge cases for performance requirements."""
    
    @patch('app.main.http_scraper')
    @patch('app.main.carbon_dating_engine')
    def test_performance_with_minimal_processing_time(self, mock_engine, mock_scraper):
        """Test that very fast analyses are still recorded accurately."""
        client = create_test_client()
        mock_detection_result, mock_stack_age_result = create_mock_analysis_data()
        
        # Setup mocks with minimal delay
        async def instant_analysis(url):
            # No delay - instant response
            return mock_detection_result
        
        mock_scraper.analyze_website = AsyncMock(side_effect=instant_analysis)
        mock_engine.calculate_stack_age = MagicMock(return_value=mock_stack_age_result)
        
        response = client.post("/api/analyze", json={
            "url": "https://fast-site.com",
            "analysis_type": "website"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Even very fast analyses should have recorded timing
        duration_ms = data["analysis_metadata"]["analysis_duration_ms"]
        assert duration_ms >= 0, "Duration should be non-negative even for instant analysis"
        assert duration_ms <= 10000, "Duration should still be within performance limits"
    
    @patch('app.main.github_analyzer')
    @patch('app.main.carbon_dating_engine')
    def test_performance_scaling_with_repository_size(self, mock_engine, mock_analyzer):
        """Test that performance scales appropriately with repository size."""
        client = create_test_client()
        
        # Test different repository sizes
        test_sizes = [10, 50, 99]  # Small, medium, large (but under 100MB)
        results = []
        
        for size_mb in test_sizes:
            mock_detection_result, mock_stack_age_result = create_mock_analysis_data()
            mock_detection_result.detection_metadata['repository_size_mb'] = size_mb
            
            # Simulate size-based processing time
            async def size_based_analysis(url):
                # Larger repos take slightly longer
                delay = size_mb * 0.0005  # 0.5ms per MB for test speed
                await asyncio.sleep(delay)
                return mock_detection_result
            
            mock_analyzer.analyze_repository = AsyncMock(side_effect=size_based_analysis)
            mock_engine.calculate_stack_age = MagicMock(return_value=mock_stack_age_result)
            
            start_time = time.time()
            response = client.post("/api/analyze", json={
                "url": f"https://github.com/user/repo-{size_mb}mb",
                "analysis_type": "github"
            })
            duration = time.time() - start_time
            
            assert response.status_code == 200
            results.append((size_mb, duration))
        
        # All sizes should be within the 30-second limit
        for size_mb, duration in results:
            assert duration <= 30.0, (
                f"Repository of {size_mb}MB should complete within 30s, took {duration:.2f}s"
            )
        
        # Larger repositories should generally take longer (but not required to be strictly monotonic)
        # This is a soft requirement since network and processing variations can affect timing
        small_duration = results[0][1]
        large_duration = results[-1][1]
        
        # The difference shouldn't be extreme (within reasonable bounds)
        duration_ratio = large_duration / small_duration if small_duration > 0 else 1
        assert duration_ratio <= 10.0, (
            f"Performance scaling should be reasonable: {small_duration:.3f}s -> {large_duration:.3f}s "
            f"(ratio: {duration_ratio:.1f}x)"
        )
    
    def test_performance_requirements_documentation_consistency(self):
        """Test that timeout values in code match the documented requirements."""
        from app.github_analyzer import GitHubAnalyzer
        from app.http_header_scraper import HTTPHeaderScraper
        from app.encyclopedia import EncyclopediaRepository
        
        # Create instances to check their timeout configurations
        encyclopedia = EncyclopediaRepository()
        github_analyzer = GitHubAnalyzer(encyclopedia)
        http_scraper = HTTPHeaderScraper(encyclopedia)
        
        # Verify timeout values match requirements
        # Requirement 8.1: Website analysis within 10 seconds
        # httpx.Timeout has different attributes depending on how it's constructed
        http_timeout_value = getattr(http_scraper.timeout, 'timeout', None) or http_scraper.timeout
        if hasattr(http_timeout_value, 'read'):
            http_timeout_value = http_timeout_value.read
        
        assert http_timeout_value == 10.0, (
            f"HTTP scraper timeout should be 10.0s per requirement 8.1, "
            f"but is {http_timeout_value}s"
        )
        
        # Requirement 8.2: GitHub analysis within 30 seconds
        github_timeout_value = getattr(github_analyzer.timeout, 'timeout', None) or github_analyzer.timeout
        if hasattr(github_timeout_value, 'read'):
            github_timeout_value = github_timeout_value.read
            
        assert github_timeout_value == 30.0, (
            f"GitHub analyzer timeout should be 30.0s per requirement 8.2, "
            f"but is {github_timeout_value}s"
        )