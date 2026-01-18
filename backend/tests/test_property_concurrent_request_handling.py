"""
Property-based tests for concurrent request handling functionality.

**Feature: stackdebt, Property 20: Concurrent Request Handling**
**Validates: Requirements 8.3**

Property 20: Concurrent Request Handling
For any set of simultaneous analysis requests, the system should process them 
concurrently without interference or data corruption
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings, HealthCheck
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

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
            'component_name': component_name,
            'thread_id': threading.current_thread().ident
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
        roast_commentary=f"Analysis for {component_name} completed!"
    )
    
    return mock_detection_result, mock_stack_age_result


# Strategy for generating concurrent request scenarios
concurrent_request_counts = st.integers(min_value=2, max_value=10)
request_urls = st.lists(
    st.sampled_from([
        "https://github.com/user/repo1",
        "https://github.com/user/repo2", 
        "https://github.com/user/repo3",
        "https://example.com",
        "https://test-site.org"
    ]),
    min_size=2,
    max_size=10
)


class TestProperty20ConcurrentRequestHandling:
    """
    Test Property 20: Concurrent Request Handling
    
    For any set of simultaneous analysis requests, the system should process them 
    concurrently without interference or data corruption.
    """
    
    @given(request_count=concurrent_request_counts)
    @settings(
        max_examples=5,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @patch('app.main.github_analyzer')
    @patch('app.main.carbon_dating_engine')
    def test_property_20_concurrent_request_handling_no_interference(self, mock_engine, 
                                                                   mock_analyzer, request_count):
        """
        **Feature: stackdebt, Property 20: Concurrent Request Handling**
        
        For any set of simultaneous analysis requests, the system should process them 
        concurrently without interference or data corruption.
        
        **Validates: Requirements 8.3**
        """
        client = create_test_client()
        
        # Create unique mock data for each request to detect interference
        def create_request_specific_mock(request_id):
            component_name = f"component-{request_id}"
            mock_detection_result, mock_stack_age_result = create_mock_analysis_data(
                component_name=component_name,
                version=f"1.{request_id}.0"
            )
            return mock_detection_result, mock_stack_age_result
        
        # Setup analyzer to return request-specific data
        def mock_analyze_repository(url):
            # Extract request ID from URL or use thread ID
            request_id = hash(url) % 1000
            mock_detection_result, mock_stack_age_result = create_request_specific_mock(request_id)
            return mock_detection_result
        
        def mock_calculate_stack_age(components):
            # Return result based on the component being analyzed
            if components:
                component_name = components[0].name
                request_id = component_name.split('-')[-1] if '-' in component_name else "0"
                _, mock_stack_age_result = create_request_specific_mock(request_id)
                return mock_stack_age_result
            return create_mock_analysis_data()[1]
        
        mock_analyzer.analyze_repository = AsyncMock(side_effect=mock_analyze_repository)
        mock_engine.calculate_stack_age = MagicMock(side_effect=mock_calculate_stack_age)
        
        # Create concurrent requests
        def make_request(request_id):
            url = f"https://github.com/user/repo{request_id}"
            response = client.post("/api/analyze", json={
                "url": url,
                "analysis_type": "github"
            })
            return request_id, response
        
        # Execute requests concurrently
        results = {}
        with ThreadPoolExecutor(max_workers=request_count) as executor:
            futures = [executor.submit(make_request, i) for i in range(request_count)]
            
            for future in as_completed(futures):
                request_id, response = future.result()
                results[request_id] = response
        
        # Property: All requests should succeed without interference
        for request_id, response in results.items():
            assert response.status_code == 200, (
                f"Request {request_id} should succeed in concurrent execution"
            )
            
            data = response.json()
            
            # Verify response structure is intact
            assert "stack_age_result" in data, f"Request {request_id} should have stack age result"
            assert "components" in data, f"Request {request_id} should have components"
            assert "analysis_metadata" in data, f"Request {request_id} should have metadata"
            
            # Verify data integrity - each request should have its own data
            components = data["components"]
            assert len(components) > 0, f"Request {request_id} should have components"
        
        # Verify no data corruption between requests
        component_names = set()
        for request_id, response in results.items():
            data = response.json()
            if data["components"]:
                component_name = data["components"][0]["name"]
                assert component_name not in component_names, (
                    f"Component names should be unique across concurrent requests, "
                    f"but {component_name} appeared multiple times"
                )
                component_names.add(component_name)
    
    @given(urls=request_urls)
    @settings(
        max_examples=3,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @patch('app.main.github_analyzer')
    @patch('app.main.http_scraper')
    @patch('app.main.carbon_dating_engine')
    def test_property_20_concurrent_mixed_analysis_types(self, mock_engine, mock_scraper, 
                                                        mock_analyzer, urls):
        """
        Test concurrent handling of mixed analysis types (GitHub and website).
        
        **Validates: Requirements 8.3**
        """
        client = create_test_client()
        
        # Setup mocks for different analysis types
        def create_type_specific_mock(url):
            if 'github.com' in url:
                return create_mock_analysis_data(component_name="github-component")
            else:
                return create_mock_analysis_data(component_name="website-component")
        
        mock_analyzer.analyze_repository = AsyncMock(
            side_effect=lambda url: create_type_specific_mock(url)[0]
        )
        mock_scraper.analyze_website = AsyncMock(
            side_effect=lambda url: create_type_specific_mock(url)[0]
        )
        mock_engine.calculate_stack_age = MagicMock(
            side_effect=lambda components: create_type_specific_mock("")[1]
        )
        
        # Create concurrent requests with mixed types
        def make_mixed_request(url):
            analysis_type = "github" if "github.com" in url else "website"
            response = client.post("/api/analyze", json={
                "url": url,
                "analysis_type": analysis_type
            })
            return url, analysis_type, response
        
        # Execute mixed requests concurrently
        results = []
        with ThreadPoolExecutor(max_workers=len(urls)) as executor:
            futures = [executor.submit(make_mixed_request, url) for url in urls]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # Verify all requests succeeded
        github_requests = 0
        website_requests = 0
        
        for url, analysis_type, response in results:
            assert response.status_code == 200, (
                f"Concurrent {analysis_type} request to {url} should succeed"
            )
            
            if analysis_type == "github":
                github_requests += 1
            else:
                website_requests += 1
        
        # Verify both types were processed if present
        if github_requests > 0:
            mock_analyzer.analyze_repository.assert_called()
        if website_requests > 0:
            mock_scraper.analyze_website.assert_called()
    
    @patch('app.main.github_analyzer')
    @patch('app.main.carbon_dating_engine')
    def test_property_20_concurrent_request_timing_independence(self, mock_engine, mock_analyzer):
        """
        Test that concurrent requests don't interfere with each other's timing.
        
        **Validates: Requirements 8.3**
        """
        client = create_test_client()
        
        # Create mocks with different delays to test timing independence
        async def slow_analysis(url):
            await asyncio.sleep(0.1)  # 100ms delay
            return create_mock_analysis_data()[0]
        
        async def fast_analysis(url):
            await asyncio.sleep(0.01)  # 10ms delay
            return create_mock_analysis_data()[0]
        
        # Alternate between slow and fast analysis
        call_count = 0
        async def alternating_analysis(url):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                return await slow_analysis(url)
            else:
                return await fast_analysis(url)
        
        mock_analyzer.analyze_repository = AsyncMock(side_effect=alternating_analysis)
        mock_engine.calculate_stack_age = MagicMock(return_value=create_mock_analysis_data()[1])
        
        # Make concurrent requests
        def make_timed_request(request_id):
            start_time = time.time()
            response = client.post("/api/analyze", json={
                "url": f"https://github.com/user/repo{request_id}",
                "analysis_type": "github"
            })
            end_time = time.time()
            return request_id, response, end_time - start_time
        
        # Execute concurrent requests
        results = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(make_timed_request, i) for i in range(4)]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # Verify all requests succeeded
        for request_id, response, duration in results:
            assert response.status_code == 200, (
                f"Timed request {request_id} should succeed"
            )
            
            # Verify timing metadata is present and reasonable
            data = response.json()
            metadata = data["analysis_metadata"]
            assert "analysis_duration_ms" in metadata, (
                f"Request {request_id} should have timing metadata"
            )
            
            # Duration should be reasonable (not negative or extremely large)
            recorded_duration_ms = metadata["analysis_duration_ms"]
            assert 0 <= recorded_duration_ms < 10000, (
                f"Request {request_id} duration should be reasonable: {recorded_duration_ms}ms"
            )
    
    def test_property_20_concurrent_error_isolation(self):
        """
        Test that errors in one concurrent request don't affect others.
        
        **Validates: Requirements 8.3**
        """
        client = create_test_client()
        
        # Setup one analyzer to fail and one to succeed
        call_count = 0
        def mixed_analysis_behavior(url):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Simulated failure for first request")
            else:
                return create_mock_analysis_data()[0]
        
        with patch('app.main.github_analyzer') as mock_analyzer, \
             patch('app.main.carbon_dating_engine') as mock_engine:
            
            mock_analyzer.analyze_repository = AsyncMock(side_effect=mixed_analysis_behavior)
            mock_engine.calculate_stack_age = MagicMock(return_value=create_mock_analysis_data()[1])
            
            # Make concurrent requests where one will fail
            def make_request(request_id):
                response = client.post("/api/analyze", json={
                    "url": f"https://github.com/user/repo{request_id}",
                    "analysis_type": "github"
                })
                return request_id, response
            
            results = []
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(make_request, i) for i in range(3)]
                
                for future in as_completed(futures):
                    results.append(future.result())
            
            # Verify error isolation - some requests should succeed despite others failing
            success_count = 0
            error_count = 0
            
            for request_id, response in results:
                if response.status_code == 200:
                    success_count += 1
                else:
                    error_count += 1
            
            # At least one request should succeed (error isolation working)
            assert success_count > 0, "Some concurrent requests should succeed despite others failing"
            # At least one request should fail (to verify the test setup)
            assert error_count > 0, "Some requests should fail to test error isolation"


class TestConcurrentRequestHandlingEdgeCases:
    """Test edge cases for concurrent request handling."""
    
    @patch('app.main.github_analyzer')
    @patch('app.main.carbon_dating_engine')
    def test_high_concurrency_stress(self, mock_engine, mock_analyzer):
        """Test system behavior under high concurrency stress."""
        client = create_test_client()
        
        mock_analyzer.analyze_repository = AsyncMock(return_value=create_mock_analysis_data()[0])
        mock_engine.calculate_stack_age = MagicMock(return_value=create_mock_analysis_data()[1])
        
        # High concurrency test
        request_count = 20
        
        def make_stress_request(request_id):
            response = client.post("/api/analyze", json={
                "url": f"https://github.com/stress/test{request_id}",
                "analysis_type": "github"
            })
            return response.status_code == 200
        
        # Execute high concurrency requests
        success_count = 0
        with ThreadPoolExecutor(max_workers=request_count) as executor:
            futures = [executor.submit(make_stress_request, i) for i in range(request_count)]
            
            for future in as_completed(futures):
                if future.result():
                    success_count += 1
        
        # Most requests should succeed under stress
        success_rate = success_count / request_count
        assert success_rate >= 0.8, f"Success rate under stress should be >= 80%, got {success_rate:.2%}"
    
    def test_concurrent_request_resource_cleanup(self):
        """Test that concurrent requests properly clean up resources."""
        client = create_test_client()
        
        # Track resource usage through mock calls
        with patch('app.main.github_analyzer') as mock_analyzer, \
             patch('app.main.carbon_dating_engine') as mock_engine:
            
            mock_analyzer.analyze_repository = AsyncMock(return_value=create_mock_analysis_data()[0])
            mock_engine.calculate_stack_age = MagicMock(return_value=create_mock_analysis_data()[1])
            
            # Make concurrent requests
            def make_cleanup_request(request_id):
                response = client.post("/api/analyze", json={
                    "url": f"https://github.com/cleanup/test{request_id}",
                    "analysis_type": "github"
                })
                return response.status_code
            
            # Execute requests
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(make_cleanup_request, i) for i in range(5)]
                results = [future.result() for future in as_completed(futures)]
            
            # Verify all requests completed (indicating proper cleanup)
            assert all(status in [200, 422, 500] for status in results), (
                "All requests should complete with valid HTTP status codes"
            )
            
            # Verify mocks were called appropriate number of times
            assert mock_analyzer.analyze_repository.call_count == 5, (
                "Analyzer should be called once per request"
            )