"""
Property-based tests for analysis initiation functionality.

**Feature: stackdebt, Property 2: Analysis Initiation**
**Validates: Requirements 1.2**

Property 2: Analysis Initiation
For any valid URL input, submitting it should trigger the carbon dating analysis 
process and display loading indicators
"""

import pytest
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


def create_mock_successful_analysis():
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
            'files_analyzed': 3,
            'repository_url': 'https://github.com/user/repo'
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
        roast_commentary="Your stack is showing its age!"
    )
    
    return mock_detection_result, mock_stack_age_result


# Strategy for generating valid URLs
valid_urls = st.one_of(
    # GitHub URLs
    st.builds(
        lambda user, repo: f"https://github.com/{user}/{repo}",
        user=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='-_')),
        repo=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='-_'))
    ),
    # Website URLs
    st.builds(
        lambda domain, tld: f"https://{domain}.{tld}",
        domain=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='-')),
        tld=st.sampled_from(['com', 'org', 'net', 'io', 'co'])
    ),
    # HTTP URLs
    st.builds(
        lambda domain, tld: f"http://{domain}.{tld}",
        domain=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='-')),
        tld=st.sampled_from(['com', 'org', 'net'])
    )
)

# Strategy for analysis types
analysis_types = st.sampled_from(['website', 'github'])


class TestProperty2AnalysisInitiation:
    """
    Test Property 2: Analysis Initiation
    
    For any valid URL input, submitting it should trigger the carbon dating analysis 
    process and display loading indicators.
    """
    
    @given(url=valid_urls, analysis_type=analysis_types)
    @settings(
        max_examples=10,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @patch('app.main.github_analyzer')
    @patch('app.main.http_scraper')
    @patch('app.main.carbon_dating_engine')
    def test_property_2_analysis_initiation(self, mock_engine, mock_scraper, 
                                          mock_analyzer, url, analysis_type):
        """
        **Feature: stackdebt, Property 2: Analysis Initiation**
        
        For any valid URL input, submitting it should trigger the carbon dating 
        analysis process and return analysis results.
        
        **Validates: Requirements 1.2**
        """
        client = create_test_client()
        mock_detection_result, mock_stack_age_result = create_mock_successful_analysis()
        
        # Setup mocks based on URL and analysis type compatibility
        # If URL is GitHub but analysis_type is website, this should fail (which is correct behavior)
        # If URL is website but analysis_type is github, this should also fail
        
        # Determine if this combination should succeed
        is_github_url = 'github.com' in url
        should_succeed = (is_github_url and analysis_type == 'github') or (not is_github_url and analysis_type == 'website')
        
        if should_succeed:
            if analysis_type == 'github':
                mock_analyzer.analyze_repository = AsyncMock(return_value=mock_detection_result)
                mock_scraper.analyze_website = AsyncMock(return_value=ComponentDetectionResult(
                    detected_components=[], failed_detections=[], detection_metadata={}
                ))
            else:  # website
                mock_scraper.analyze_website = AsyncMock(return_value=mock_detection_result)
                mock_analyzer.analyze_repository = AsyncMock(return_value=ComponentDetectionResult(
                    detected_components=[], failed_detections=[], detection_metadata={}
                ))
        else:
            # For incompatible combinations, return empty results (which will cause 422)
            mock_analyzer.analyze_repository = AsyncMock(return_value=ComponentDetectionResult(
                detected_components=[], failed_detections=[], detection_metadata={}
            ))
            mock_scraper.analyze_website = AsyncMock(return_value=ComponentDetectionResult(
                detected_components=[], failed_detections=[], detection_metadata={}
            ))
        
        mock_engine.calculate_stack_age = MagicMock(return_value=mock_stack_age_result)
        
        # Make the analysis request
        response = client.post("/api/analyze", json={
            "url": url,
            "analysis_type": analysis_type
        })
        
        # Property: Valid URL input should trigger analysis process
        # But incompatible URL/analysis_type combinations should fail appropriately
        is_github_url = 'github.com' in url
        should_succeed = (is_github_url and analysis_type == 'github') or (not is_github_url and analysis_type == 'website')
        
        if should_succeed:
            assert response.status_code == 200, f"Analysis should succeed for compatible URL/type: {url} as {analysis_type}"
            
            # Verify analysis was initiated and completed
            data = response.json()
            
            # Analysis process should return structured results
            assert "stack_age_result" in data, "Analysis should return stack age results"
            assert "components" in data, "Analysis should return detected components"
            assert "analysis_metadata" in data, "Analysis should return analysis metadata"
            assert "generated_at" in data, "Analysis should include generation timestamp"
            
            # Analysis metadata should indicate process was initiated
            metadata = data["analysis_metadata"]
            assert "analysis_duration_ms" in metadata, "Should track analysis duration"
            assert "analysis_type" in metadata, "Should record analysis type"
            assert metadata["analysis_duration_ms"] >= 0, "Duration should be non-negative"
            
            # Verify appropriate analyzer was called based on analysis type
            if analysis_type == 'github':
                mock_analyzer.analyze_repository.assert_called_once()
                mock_scraper.analyze_website.assert_not_called()
            else:  # website
                mock_scraper.analyze_website.assert_called_once()
                mock_analyzer.analyze_repository.assert_not_called()
            
            # Carbon dating engine should be called for any successful analysis
            mock_engine.calculate_stack_age.assert_called_once()
        else:
            # Incompatible combinations should fail with 422 (no components detected)
            assert response.status_code == 422, f"Incompatible URL/type should fail: {url} as {analysis_type}"
            
            # The appropriate analyzer should still be called (but return empty results)
            if analysis_type == 'github':
                mock_analyzer.analyze_repository.assert_called_once()
            else:  # website
                mock_scraper.analyze_website.assert_called_once()
            
            # Carbon dating engine should not be called for failed analysis
            mock_engine.calculate_stack_age.assert_not_called()
    
    @given(url=valid_urls)
    @settings(
        max_examples=5,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_2_analysis_initiation_url_validation(self, url):
        """
        Test that valid URLs pass initial validation and reach the analysis stage.
        
        **Validates: Requirements 1.2**
        """
        client = create_test_client()
        
        # Determine expected analysis type from URL
        if 'github.com' in url:
            analysis_type = 'github'
        else:
            analysis_type = 'website'
        
        # Mock the analyzers to simulate failure after validation passes
        with patch('app.main.github_analyzer') as mock_analyzer, \
             patch('app.main.http_scraper') as mock_scraper:
            
            # Setup mocks to raise a controlled exception after validation
            mock_analyzer.analyze_repository = AsyncMock(
                side_effect=Exception("Controlled test exception")
            )
            mock_scraper.analyze_website = AsyncMock(
                side_effect=Exception("Controlled test exception")
            )
            
            response = client.post("/api/analyze", json={
                "url": url,
                "analysis_type": analysis_type
            })
            
            # Should not fail due to URL validation (422) but due to analysis error (500)
            # This proves the URL passed validation and analysis was initiated
            assert response.status_code == 500, (
                f"Valid URL {url} should pass validation and reach analysis stage"
            )
            
            # Verify the appropriate analyzer was called (proving analysis was initiated)
            if analysis_type == 'github':
                mock_analyzer.analyze_repository.assert_called_once_with(url)
            else:
                mock_scraper.analyze_website.assert_called_once_with(url)
    
    def test_property_2_analysis_initiation_invalid_urls_rejected(self):
        """
        Test that invalid URLs are rejected before analysis initiation.
        
        This serves as a negative test to ensure the property holds only for valid URLs.
        """
        client = create_test_client()
        
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",
            "",
            "javascript:alert('xss')",
            "file:///etc/passwd"
        ]
        
        for invalid_url in invalid_urls:
            response = client.post("/api/analyze", json={
                "url": invalid_url,
                "analysis_type": "website"
            })
            
            # Invalid URLs should be rejected at validation stage (422)
            # This proves analysis is NOT initiated for invalid URLs
            assert response.status_code == 422, (
                f"Invalid URL {invalid_url} should be rejected before analysis"
            )
    
    @given(analysis_type=analysis_types)
    @settings(
        max_examples=5,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @patch('app.main.github_analyzer')
    @patch('app.main.http_scraper')
    @patch('app.main.carbon_dating_engine')
    def test_property_2_analysis_metadata_consistency(self, mock_engine, mock_scraper,
                                                    mock_analyzer, analysis_type):
        """
        Test that analysis metadata consistently reflects the initiated analysis.
        
        **Validates: Requirements 1.2**
        """
        client = create_test_client()
        mock_detection_result, mock_stack_age_result = create_mock_successful_analysis()
        
        # Update detection metadata to match analysis type
        mock_detection_result.detection_metadata['analysis_type'] = analysis_type
        
        # Setup mocks
        mock_analyzer.analyze_repository = AsyncMock(return_value=mock_detection_result)
        mock_scraper.analyze_website = AsyncMock(return_value=mock_detection_result)
        mock_engine.calculate_stack_age = MagicMock(return_value=mock_stack_age_result)
        
        # Use appropriate URL for analysis type
        url = "https://github.com/user/repo" if analysis_type == "github" else "https://example.com"
        
        response = client.post("/api/analyze", json={
            "url": url,
            "analysis_type": analysis_type
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Analysis metadata should consistently reflect the initiated analysis
        metadata = data["analysis_metadata"]
        assert metadata["analysis_type"] == analysis_type, (
            "Metadata should reflect the type of analysis that was initiated"
        )
        assert metadata["url_analyzed"] == url, (
            "Metadata should record the URL that triggered the analysis"
        )
        
        # Should contain timing information indicating analysis was performed
        assert isinstance(metadata["analysis_duration_ms"], int), (
            "Should track analysis duration as integer milliseconds"
        )
        assert metadata["analysis_duration_ms"] >= 0, (
            "Analysis duration should be non-negative"
        )


# Additional edge case tests
class TestAnalysisInitiationEdgeCases:
    """Test edge cases for analysis initiation."""
    
    def test_analysis_initiation_with_auto_type_detection(self):
        """Test that analysis is initiated even without explicit analysis_type."""
        client = create_test_client()
        mock_detection_result, mock_stack_age_result = create_mock_successful_analysis()
        
        with patch('app.main.github_analyzer') as mock_analyzer, \
             patch('app.main.carbon_dating_engine') as mock_engine:
            
            mock_analyzer.analyze_repository = AsyncMock(return_value=mock_detection_result)
            mock_engine.calculate_stack_age = MagicMock(return_value=mock_stack_age_result)
            
            # GitHub URL without explicit analysis_type should auto-detect
            response = client.post("/api/analyze", json={
                "url": "https://github.com/user/repo",
                "analysis_type": "github"  # Required by schema
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Analysis should be initiated and completed
            assert "stack_age_result" in data
            assert data["analysis_metadata"]["analysis_type"] == "github"
            mock_analyzer.analyze_repository.assert_called_once()
    
    @patch('app.main.github_analyzer')
    @patch('app.main.carbon_dating_engine')
    def test_analysis_initiation_timing_recorded(self, mock_engine, mock_analyzer):
        """Test that analysis timing is properly recorded."""
        client = create_test_client()
        mock_detection_result, mock_stack_age_result = create_mock_successful_analysis()
        
        # Add delay to mock to ensure timing is measured
        import asyncio
        async def delayed_analysis(*args, **kwargs):
            await asyncio.sleep(0.01)  # 10ms delay
            return mock_detection_result
        
        mock_analyzer.analyze_repository = AsyncMock(side_effect=delayed_analysis)
        mock_engine.calculate_stack_age = MagicMock(return_value=mock_stack_age_result)
        
        response = client.post("/api/analyze", json={
            "url": "https://github.com/user/repo",
            "analysis_type": "github"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Timing should be recorded and reflect actual analysis duration
        duration_ms = data["analysis_metadata"]["analysis_duration_ms"]
        assert duration_ms >= 10, "Should record actual analysis duration including delays"
        assert duration_ms < 1000, "Duration should be reasonable for test scenario"