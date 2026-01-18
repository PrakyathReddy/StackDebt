"""
Property-based tests for analysis resilience functionality.

**Feature: stackdebt, Property 5: Analysis Resilience**
**Validates: Requirements 2.6**

Property 5: Analysis Resilience
For any analysis where some component detection fails, the system should continue 
processing with available data and log failures without crashing
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


def create_mock_partial_analysis():
    """Create mock data for partial analysis with some failures."""
    # Some components succeed
    successful_components = [
        Component(
            name="python",
            version="3.9.0",
            release_date=date(2020, 10, 5),
            category=ComponentCategory.PROGRAMMING_LANGUAGE,
            risk_level=RiskLevel.WARNING,
            age_years=3.2,
            weight=0.7
        ),
        Component(
            name="nginx",
            version="1.18.0",
            release_date=date(2020, 4, 21),
            category=ComponentCategory.WEB_SERVER,
            risk_level=RiskLevel.WARNING,
            age_years=3.7,
            weight=0.3
        )
    ]
    
    # Some components fail
    failed_detections = [
        "unknown-package@1.0.0: not found in database",
        "invalid-component@2.0.0: parsing error",
        "missing-version@latest: version not specified"
    ]
    
    mock_detection_result = ComponentDetectionResult(
        detected_components=successful_components,
        failed_detections=failed_detections,
        detection_metadata={
            'analysis_type': 'github',
            'detection_time_ms': 800,
            'files_analyzed': 5,
            'components_detected': 2,
            'components_failed': 3
        }
    )
    
    mock_stack_age_result = StackAgeResult(
        effective_age=3.4,
        total_components=2,  # Only successful components
        risk_distribution={
            RiskLevel.CRITICAL: 0,
            RiskLevel.WARNING: 2,
            RiskLevel.OK: 0
        },
        oldest_critical_component=None,
        roast_commentary="Your stack is showing its age, but some components couldn't be analyzed!"
    )
    
    return mock_detection_result, mock_stack_age_result


# Strategy for generating failure scenarios
failure_scenarios = st.lists(
    st.text(min_size=5, max_size=50),  # Failed component names
    min_size=1,
    max_size=10
)

# Strategy for generating URLs
test_urls = st.sampled_from([
    "https://github.com/user/repo",
    "https://example.com",
    "https://test-site.org"
])

analysis_types = st.sampled_from(['website', 'github'])


class TestProperty5AnalysisResilience:
    """
    Test Property 5: Analysis Resilience
    
    For any analysis where some component detection fails, the system should continue 
    processing with available data and log failures without crashing.
    """
    
    @given(url=test_urls, analysis_type=analysis_types, failed_components=failure_scenarios)
    @settings(
        max_examples=30,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @patch('app.main.github_analyzer')
    @patch('app.main.http_scraper')
    @patch('app.main.carbon_dating_engine')
    def test_property_5_analysis_resilience_with_failures(self, mock_engine, mock_scraper, 
                                                         mock_analyzer, url, analysis_type, 
                                                         failed_components):
        """
        **Feature: stackdebt, Property 5: Analysis Resilience**
        
        For any analysis where some component detection fails, the system should continue 
        processing with available data and log failures without crashing.
        
        **Validates: Requirements 2.6**
        """
        client = create_test_client()
        mock_detection_result, mock_stack_age_result = create_mock_partial_analysis()
        
        # Customize failed detections with generated data
        mock_detection_result.failed_detections = [
            f"{component}: simulated failure" for component in failed_components
        ]
        mock_detection_result.detection_metadata['components_failed'] = len(failed_components)
        
        # Setup mocks based on URL and analysis type compatibility
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
            # For incompatible combinations, skip this test case
            pytest.skip(f"Incompatible URL/analysis_type combination: {url} as {analysis_type}")
        
        mock_engine.calculate_stack_age = MagicMock(return_value=mock_stack_age_result)
        
        # Make the analysis request
        response = client.post("/api/analyze", json={
            "url": url,
            "analysis_type": analysis_type
        })
        
        # Property: System should continue processing despite failures
        assert response.status_code == 200, (
            f"Analysis should succeed despite {len(failed_components)} component failures"
        )
        
        # Verify analysis completed with available data
        data = response.json()
        
        # Should return results despite failures
        assert "stack_age_result" in data, "Should return stack age results despite failures"
        assert "components" in data, "Should return detected components despite failures"
        assert "analysis_metadata" in data, "Should return analysis metadata despite failures"
        
        # Should track both successful and failed components
        metadata = data["analysis_metadata"]
        assert metadata["components_detected"] > 0, "Should have some successful detections"
        assert metadata["components_failed"] == len(failed_components), "Should track failed detections"
        
        # Should continue with carbon dating calculation using available components
        mock_engine.calculate_stack_age.assert_called_once()
        
        # Verify the components returned are only the successful ones
        returned_components = data["components"]
        assert len(returned_components) == mock_stack_age_result.total_components, (
            "Should only return successfully detected components"
        )
        
        # Stack age should be calculated from available components
        assert data["stack_age_result"]["total_components"] > 0, (
            "Should calculate age from available components"
        )
    
    @patch('app.main.github_analyzer')
    @patch('app.main.carbon_dating_engine')
    def test_property_5_analysis_resilience_partial_success_logging(self, mock_engine, mock_analyzer):
        """
        Test that partial failures are properly logged while analysis continues.
        
        **Validates: Requirements 2.6**
        """
        client = create_test_client()
        mock_detection_result, mock_stack_age_result = create_mock_partial_analysis()
        
        mock_analyzer.analyze_repository = AsyncMock(return_value=mock_detection_result)
        mock_engine.calculate_stack_age = MagicMock(return_value=mock_stack_age_result)
        
        # Capture logs to verify failure logging
        with patch('app.main.logger') as mock_logger:
            response = client.post("/api/analyze", json={
                "url": "https://github.com/user/repo",
                "analysis_type": "github"
            })
            
            assert response.status_code == 200
            
            # Should log warnings about failed detections
            mock_logger.warning.assert_called()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "Failed to detect" in warning_call, "Should log failed detections"
    
    @patch('app.main.github_analyzer')
    @patch('app.main.carbon_dating_engine')
    def test_property_5_analysis_resilience_enrichment_failures(self, mock_engine, mock_analyzer):
        """
        Test resilience when component enrichment fails but detection succeeds.
        
        **Validates: Requirements 2.6**
        """
        client = create_test_client()
        
        # Create components that will fail enrichment
        raw_components = [
            Component(
                name="unknown-software",
                version="1.0.0",
                release_date=date.today(),
                category=ComponentCategory.LIBRARY,
                risk_level=RiskLevel.OK,
                age_years=0.0,
                weight=0.1
            )
        ]
        
        # Mock detection succeeds but enrichment fails for some components
        mock_detection_result = ComponentDetectionResult(
            detected_components=raw_components,
            failed_detections=["enrichment-failed@1.0.0: not found in encyclopedia"],
            detection_metadata={
                'analysis_type': 'github',
                'detection_time_ms': 600
            }
        )
        
        mock_stack_age_result = StackAgeResult(
            effective_age=1.0,
            total_components=1,
            risk_distribution={RiskLevel.OK: 1, RiskLevel.WARNING: 0, RiskLevel.CRITICAL: 0},
            oldest_critical_component=None,
            roast_commentary="Fresh components with some unknowns!"
        )
        
        mock_analyzer.analyze_repository = AsyncMock(return_value=mock_detection_result)
        mock_engine.calculate_stack_age = MagicMock(return_value=mock_stack_age_result)
        
        response = client.post("/api/analyze", json={
            "url": "https://github.com/user/repo",
            "analysis_type": "github"
        })
        
        # Should succeed despite enrichment failures
        assert response.status_code == 200
        data = response.json()
        
        # Should include components even if enrichment failed
        assert len(data["components"]) > 0, "Should include components despite enrichment failures"
        assert data["analysis_metadata"]["components_failed"] > 0, "Should track enrichment failures"
    
    def test_property_5_analysis_resilience_no_crash_on_empty_results(self):
        """
        Test that system handles gracefully when no components are detected.
        
        **Validates: Requirements 2.6**
        """
        client = create_test_client()
        
        # Mock complete detection failure
        empty_detection_result = ComponentDetectionResult(
            detected_components=[],
            failed_detections=[
                "package.json: parsing failed",
                "requirements.txt: file not found",
                "Dockerfile: invalid format"
            ],
            detection_metadata={
                'analysis_type': 'github',
                'detection_time_ms': 300,
                'files_analyzed': 3,
                'components_detected': 0,
                'components_failed': 3
            }
        )
        
        with patch('app.main.github_analyzer') as mock_analyzer:
            mock_analyzer.analyze_repository = AsyncMock(return_value=empty_detection_result)
            
            response = client.post("/api/analyze", json={
                "url": "https://github.com/user/empty-repo",
                "analysis_type": "github"
            })
            
            # Should return appropriate error, not crash
            assert response.status_code == 422, "Should return validation error for no components"
            
            # Error should be informative about the failure
            error_detail = response.json()["detail"]
            assert "No software components detected" in error_detail["message"]
            assert "failed_detections" in error_detail, "Should include failure information"
    
    @given(failure_count=st.integers(min_value=1, max_value=20))
    @settings(max_examples=10)
    @patch('app.main.github_analyzer')
    @patch('app.main.carbon_dating_engine')
    def test_property_5_analysis_resilience_scales_with_failure_count(self, mock_engine, 
                                                                    mock_analyzer, failure_count):
        """
        Test that resilience scales appropriately with the number of failures.
        
        **Validates: Requirements 2.6**
        """
        client = create_test_client()
        
        # Create successful components
        successful_components = [
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
        
        # Generate failures based on the count
        failed_detections = [f"failed-component-{i}@1.0.0: error" for i in range(failure_count)]
        
        mock_detection_result = ComponentDetectionResult(
            detected_components=successful_components,
            failed_detections=failed_detections,
            detection_metadata={
                'analysis_type': 'github',
                'components_detected': 1,
                'components_failed': failure_count
            }
        )
        
        mock_stack_age_result = StackAgeResult(
            effective_age=3.2,
            total_components=1,
            risk_distribution={RiskLevel.WARNING: 1, RiskLevel.OK: 0, RiskLevel.CRITICAL: 0},
            oldest_critical_component=None,
            roast_commentary="Analysis completed despite failures!"
        )
        
        mock_analyzer.analyze_repository = AsyncMock(return_value=mock_detection_result)
        mock_engine.calculate_stack_age = MagicMock(return_value=mock_stack_age_result)
        
        response = client.post("/api/analyze", json={
            "url": "https://github.com/user/repo",
            "analysis_type": "github"
        })
        
        # Should succeed regardless of failure count
        assert response.status_code == 200, f"Should handle {failure_count} failures gracefully"
        
        data = response.json()
        metadata = data["analysis_metadata"]
        
        # Should accurately track the number of failures
        assert metadata["components_failed"] == failure_count, (
            f"Should track exactly {failure_count} failures"
        )
        
        # Should still produce valid results from successful components
        assert data["stack_age_result"]["total_components"] > 0, (
            "Should calculate results from successful components"
        )


class TestAnalysisResilienceEdgeCases:
    """Test edge cases for analysis resilience."""
    
    @patch('app.main.github_analyzer')
    def test_analyzer_exception_handling(self, mock_analyzer):
        """Test that analyzer exceptions are handled gracefully."""
        client = create_test_client()
        
        # Mock analyzer to raise an exception
        mock_analyzer.analyze_repository = AsyncMock(
            side_effect=Exception("Simulated analyzer failure")
        )
        
        response = client.post("/api/analyze", json={
            "url": "https://github.com/user/repo",
            "analysis_type": "github"
        })
        
        # Should return error but not crash
        assert response.status_code == 500
        assert "error" in response.json()["detail"]
    
    @patch('app.main.github_analyzer')
    @patch('app.main.carbon_dating_engine')
    def test_carbon_dating_engine_resilience(self, mock_engine, mock_analyzer):
        """Test resilience when carbon dating engine encounters issues."""
        client = create_test_client()
        
        # Mock successful detection but engine failure
        mock_detection_result, _ = create_mock_partial_analysis()
        mock_analyzer.analyze_repository = AsyncMock(return_value=mock_detection_result)
        mock_engine.calculate_stack_age = MagicMock(
            side_effect=ValueError("Invalid component data")
        )
        
        response = client.post("/api/analyze", json={
            "url": "https://github.com/user/repo",
            "analysis_type": "github"
        })
        
        # Should return appropriate error for calculation failure
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        assert "Unable to calculate stack age" in error_detail["message"]