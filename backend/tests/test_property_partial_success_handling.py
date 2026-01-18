"""
Property-based tests for partial success handling functionality.

**Feature: stackdebt, Property 24: Partial Success Handling**
**Validates: Requirements 9.5**

Property 24: Partial Success Handling
For any analysis that partially succeeds, the system should display available results 
with clear warnings about incomplete data
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import date
from typing import List

from app.main import app
from app.schemas import (
    Component, ComponentCategory, RiskLevel, 
    ComponentDetectionResult, StackAgeResult
)


def create_test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


# Strategies for generating partial success scenarios
successful_components_strategy = st.lists(
    st.builds(
        Component,
        name=st.sampled_from(["python", "nginx", "postgresql", "react", "django"]),
        version=st.sampled_from(["3.9.0", "1.18.0", "13.0", "18.2.0", "4.2.0"]),
        release_date=st.dates(min_value=date(2018, 1, 1), max_value=date(2023, 12, 31)),
        category=st.sampled_from(list(ComponentCategory)),
        risk_level=st.sampled_from(list(RiskLevel)),
        age_years=st.floats(min_value=0.1, max_value=10.0),
        weight=st.floats(min_value=0.1, max_value=1.0)
    ),
    min_size=1,
    max_size=5
)

failed_detections_strategy = st.lists(
    st.text(min_size=10, max_size=100).map(lambda x: f"{x}: detection failed"),
    min_size=1,
    max_size=10
)

analysis_types = st.sampled_from(['website', 'github'])
test_urls = st.sampled_from([
    "https://github.com/user/repo",
    "https://example.com",
    "https://test-site.org"
])


class TestProperty24PartialSuccessHandling:
    """
    Test Property 24: Partial Success Handling
    
    For any analysis that partially succeeds, the system should display available results 
    with clear warnings about incomplete data.
    """
    
    @given(
        successful_components=successful_components_strategy,
        failed_detections=failed_detections_strategy,
        url=test_urls,
        analysis_type=analysis_types
    )
    @settings(
        max_examples=10,  # Reduced for faster execution as requested
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_24_partial_success_handling(self, successful_components, failed_detections, url, analysis_type):
        """
        **Feature: stackdebt, Property 24: Partial Success Handling**
        
        For any analysis that partially succeeds, the system should display available results 
        with clear warnings about incomplete data.
        
        **Validates: Requirements 9.5**
        """
        client = create_test_client()
        
        # Skip incompatible URL/analysis_type combinations
        is_github_url = 'github.com' in url
        should_proceed = (is_github_url and analysis_type == 'github') or (not is_github_url and analysis_type == 'website')
        
        if not should_proceed:
            pytest.skip(f"Incompatible URL/analysis_type combination: {url} as {analysis_type}")
        
        # Create partial success detection result
        partial_detection_result = ComponentDetectionResult(
            detected_components=successful_components,
            failed_detections=failed_detections,
            detection_metadata={
                'analysis_type': analysis_type,
                'detection_time_ms': 800,
                'files_analyzed': len(successful_components) + len(failed_detections),
                'components_detected': len(successful_components),
                'components_failed': len(failed_detections)
            }
        )
        
        # Create corresponding stack age result
        risk_distribution = {RiskLevel.CRITICAL: 0, RiskLevel.WARNING: 0, RiskLevel.OK: 0}
        for component in successful_components:
            risk_distribution[component.risk_level] += 1
        
        stack_age_result = StackAgeResult(
            effective_age=round(sum(c.age_years * c.weight for c in successful_components) / len(successful_components), 1),
            total_components=len(successful_components),
            risk_distribution=risk_distribution,
            oldest_critical_component=None,
            roast_commentary=f"Analysis completed with {len(failed_detections)} components that couldn't be analyzed!"
        )
        
        with patch('app.main.github_analyzer') as mock_analyzer, \
             patch('app.main.http_scraper') as mock_scraper, \
             patch('app.main.carbon_dating_engine') as mock_engine:
            
            # Setup mocks based on analysis type
            if analysis_type == 'github':
                mock_analyzer.analyze_repository = AsyncMock(return_value=partial_detection_result)
                mock_scraper.analyze_website = AsyncMock(return_value=ComponentDetectionResult(
                    detected_components=[], failed_detections=[], detection_metadata={}
                ))
            else:  # website
                mock_scraper.analyze_website = AsyncMock(return_value=partial_detection_result)
                mock_analyzer.analyze_repository = AsyncMock(return_value=ComponentDetectionResult(
                    detected_components=[], failed_detections=[], detection_metadata={}
                ))
            
            mock_engine.calculate_stack_age = MagicMock(return_value=stack_age_result)
            
            # Capture logs to verify warning messages
            with patch('app.main.logger') as mock_logger:
                response = client.post("/api/analyze", json={
                    "url": url,
                    "analysis_type": analysis_type
                })
                
                # Property: System should display available results despite partial failures
                assert response.status_code == 200, (
                    f"Should succeed with partial results when {len(successful_components)} components "
                    f"succeed and {len(failed_detections)} fail"
                )
                
                response_data = response.json()
                
                # Property: Should include successful components in results
                assert "components" in response_data, "Should include detected components in response"
                returned_components = response_data["components"]
                assert len(returned_components) == len(successful_components), (
                    "Should return all successfully detected components"
                )
                
                # Verify component data integrity
                for i, component in enumerate(returned_components):
                    expected = successful_components[i]
                    assert component["name"] == expected.name, "Component names should match"
                    assert component["version"] == expected.version, "Component versions should match"
                    assert component["category"] == expected.category.value, "Component categories should match"
                    assert component["risk_level"] == expected.risk_level.value, "Risk levels should match"
                
                # Property: Should include stack age calculation from available components
                assert "stack_age_result" in response_data, "Should include stack age results"
                stack_age = response_data["stack_age_result"]
                assert stack_age["total_components"] == len(successful_components), (
                    "Stack age should be calculated from successful components only"
                )
                assert stack_age["effective_age"] > 0, "Should calculate meaningful effective age"
                
                # Property: Should provide clear warnings about incomplete data
                assert "analysis_metadata" in response_data, "Should include analysis metadata"
                metadata = response_data["analysis_metadata"]
                
                # Should track both successful and failed detections
                assert metadata["components_detected"] == len(successful_components), (
                    "Should track number of successful detections"
                )
                assert metadata["components_failed"] == len(failed_detections), (
                    "Should track number of failed detections"
                )
                
                # Should log warnings about failures
                mock_logger.warning.assert_called()
                warning_message = mock_logger.warning.call_args[0][0]
                assert "Failed to detect" in warning_message, (
                    "Should log warning about failed detections"
                )
                assert str(len(failed_detections)) in warning_message, (
                    "Should include count of failed detections in warning"
                )
                
                # Property: Roast commentary should acknowledge incomplete analysis
                roast_commentary = stack_age["roast_commentary"]
                assert len(roast_commentary) > 0, "Should provide roast commentary"
                # Commentary should hint at incomplete analysis when there are failures
                if len(failed_detections) > 2:
                    assert any(keyword in roast_commentary.lower() for keyword in [
                        "couldn't", "failed", "incomplete", "missing", "some"
                    ]), "Commentary should acknowledge incomplete analysis for significant failures"
    
    @given(
        successful_count=st.integers(min_value=1, max_value=8),
        failed_count=st.integers(min_value=1, max_value=15)
    )
    @settings(max_examples=8)
    def test_property_24_partial_success_scaling(self, successful_count, failed_count):
        """
        Test that partial success handling scales appropriately with different ratios 
        of successful to failed detections.
        
        **Validates: Requirements 9.5**
        """
        client = create_test_client()
        
        # Generate components based on counts
        successful_components = []
        for i in range(successful_count):
            component = Component(
                name=f"component-{i}",
                version="1.0.0",
                release_date=date(2022, 1, 1),
                category=ComponentCategory.LIBRARY,
                risk_level=RiskLevel.OK,
                age_years=2.0,
                weight=0.1
            )
            successful_components.append(component)
        
        failed_detections = [f"failed-component-{i}@1.0.0: error" for i in range(failed_count)]
        
        partial_result = ComponentDetectionResult(
            detected_components=successful_components,
            failed_detections=failed_detections,
            detection_metadata={
                'analysis_type': 'github',
                'components_detected': successful_count,
                'components_failed': failed_count
            }
        )
        
        stack_age_result = StackAgeResult(
            effective_age=2.0,
            total_components=successful_count,
            risk_distribution={RiskLevel.OK: successful_count, RiskLevel.WARNING: 0, RiskLevel.CRITICAL: 0},
            oldest_critical_component=None,
            roast_commentary=f"Found {successful_count} components, but {failed_count} couldn't be analyzed!"
        )
        
        with patch('app.main.github_analyzer') as mock_analyzer, \
             patch('app.main.carbon_dating_engine') as mock_engine:
            
            mock_analyzer.analyze_repository = AsyncMock(return_value=partial_result)
            mock_engine.calculate_stack_age = MagicMock(return_value=stack_age_result)
            
            response = client.post("/api/analyze", json={
                "url": "https://github.com/user/repo",
                "analysis_type": "github"
            })
            
            # Should succeed regardless of failure ratio
            assert response.status_code == 200, (
                f"Should handle {successful_count} successes and {failed_count} failures"
            )
            
            data = response.json()
            metadata = data["analysis_metadata"]
            
            # Should accurately track both counts
            assert metadata["components_detected"] == successful_count
            assert metadata["components_failed"] == failed_count
            
            # Should return only successful components
            assert len(data["components"]) == successful_count
            
            # Stack age should reflect only successful components
            assert data["stack_age_result"]["total_components"] == successful_count
    
    def test_property_24_partial_success_with_mixed_categories(self):
        """
        Test partial success handling with mixed component categories and risk levels.
        
        **Validates: Requirements 9.5**
        """
        client = create_test_client()
        
        # Create diverse successful components
        successful_components = [
            Component(
                name="python",
                version="3.8.0",
                release_date=date(2019, 10, 14),
                category=ComponentCategory.PROGRAMMING_LANGUAGE,
                risk_level=RiskLevel.WARNING,
                age_years=4.2,
                weight=0.7
            ),
            Component(
                name="nginx",
                version="1.20.0",
                release_date=date(2021, 4, 20),
                category=ComponentCategory.WEB_SERVER,
                risk_level=RiskLevel.WARNING,
                age_years=2.8,
                weight=0.3
            ),
            Component(
                name="react",
                version="18.0.0",
                release_date=date(2022, 3, 29),
                category=ComponentCategory.FRAMEWORK,
                risk_level=RiskLevel.OK,
                age_years=1.8,
                weight=0.2
            )
        ]
        
        # Mix of different failure types
        failed_detections = [
            "unknown-database@5.0.0: not found in encyclopedia",
            "legacy-tool@1.0.0: version parsing failed",
            "custom-library@latest: version not specified",
            "deprecated-framework@2.0.0: end-of-life data missing"
        ]
        
        partial_result = ComponentDetectionResult(
            detected_components=successful_components,
            failed_detections=failed_detections,
            detection_metadata={
                'analysis_type': 'github',
                'components_detected': 3,
                'components_failed': 4,
                'categories_detected': ['programming_language', 'web_server', 'framework'],
                'categories_failed': ['database', 'development_tool', 'library', 'framework']
            }
        )
        
        stack_age_result = StackAgeResult(
            effective_age=3.1,
            total_components=3,
            risk_distribution={RiskLevel.CRITICAL: 0, RiskLevel.WARNING: 2, RiskLevel.OK: 1},
            oldest_critical_component=None,
            roast_commentary="Your stack has some aging components, plus several unknowns lurking in the shadows!"
        )
        
        with patch('app.main.github_analyzer') as mock_analyzer, \
             patch('app.main.carbon_dating_engine') as mock_engine:
            
            mock_analyzer.analyze_repository = AsyncMock(return_value=partial_result)
            mock_engine.calculate_stack_age = MagicMock(return_value=stack_age_result)
            
            response = client.post("/api/analyze", json={
                "url": "https://github.com/user/repo",
                "analysis_type": "github"
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Should include all successful components with their categories
            components = data["components"]
            assert len(components) == 3
            
            categories_found = {c["category"] for c in components}
            expected_categories = {"programming_language", "web_server", "framework"}
            assert categories_found == expected_categories, "Should preserve component categories"
            
            # Should reflect mixed risk levels in distribution
            risk_dist = data["stack_age_result"]["risk_distribution"]
            assert risk_dist["warning"] == 2, "Should count warning-level components"
            assert risk_dist["ok"] == 1, "Should count ok-level components"
            assert risk_dist["critical"] == 0, "Should count critical-level components"
            
            # Should track failure information
            metadata = data["analysis_metadata"]
            assert metadata["components_failed"] == 4, "Should track all failures"
    
    def test_property_24_partial_success_warning_clarity(self):
        """
        Test that warnings about incomplete data are clear and actionable.
        
        **Validates: Requirements 9.5**
        """
        client = create_test_client()
        
        successful_components = [
            Component(
                name="django",
                version="4.1.0",
                release_date=date(2022, 8, 3),
                category=ComponentCategory.FRAMEWORK,
                risk_level=RiskLevel.OK,
                age_years=1.4,
                weight=0.5
            )
        ]
        
        # Specific failure scenarios that should generate clear warnings
        failed_detections = [
            "requirements.txt: file not found",
            "package.json: parsing error on line 15",
            "Dockerfile: base image version not specified",
            "unknown-package@1.0.0: not found in encyclopedia database"
        ]
        
        partial_result = ComponentDetectionResult(
            detected_components=successful_components,
            failed_detections=failed_detections,
            detection_metadata={
                'analysis_type': 'github',
                'components_detected': 1,
                'components_failed': 4,
                'warning_level': 'high'  # High failure rate
            }
        )
        
        stack_age_result = StackAgeResult(
            effective_age=1.4,
            total_components=1,
            risk_distribution={RiskLevel.OK: 1, RiskLevel.WARNING: 0, RiskLevel.CRITICAL: 0},
            oldest_critical_component=None,
            roast_commentary="Only found one component - there's definitely more hiding in this codebase!"
        )
        
        with patch('app.main.github_analyzer') as mock_analyzer, \
             patch('app.main.carbon_dating_engine') as mock_engine, \
             patch('app.main.logger') as mock_logger:
            
            mock_analyzer.analyze_repository = AsyncMock(return_value=partial_result)
            mock_engine.calculate_stack_age = MagicMock(return_value=stack_age_result)
            
            response = client.post("/api/analyze", json={
                "url": "https://github.com/user/repo",
                "analysis_type": "github"
            })
            
            assert response.status_code == 200
            
            # Should log clear warnings about the failures
            mock_logger.warning.assert_called()
            warning_message = mock_logger.warning.call_args[0][0]
            
            # Warning should be informative
            assert "Failed to detect 4 components" in warning_message, (
                "Should specify exact number of failures"
            )
            
            # Should include sample failures for context
            assert any(failure.split(':')[0] in warning_message for failure in failed_detections[:3]), (
                "Should include examples of what failed"
            )
            
            data = response.json()
            
            # Metadata should provide detailed failure tracking
            metadata = data["analysis_metadata"]
            assert metadata["components_failed"] == 4, "Should track failure count"
            
            # Commentary should acknowledge the incomplete analysis
            commentary = data["stack_age_result"]["roast_commentary"]
            assert any(keyword in commentary.lower() for keyword in [
                "only", "one", "more", "hiding", "missing"
            ]), "Commentary should acknowledge incomplete analysis"


class TestPartialSuccessHandlingEdgeCases:
    """Test edge cases for partial success handling."""
    
    def test_high_failure_rate_partial_success(self):
        """Test partial success when failure rate is very high."""
        client = create_test_client()
        
        # Only 1 success, many failures
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
        
        # Many failures (20 failed vs 1 success)
        failed_detections = [f"failed-component-{i}@1.0.0: various errors" for i in range(20)]
        
        partial_result = ComponentDetectionResult(
            detected_components=successful_components,
            failed_detections=failed_detections,
            detection_metadata={
                'analysis_type': 'github',
                'components_detected': 1,
                'components_failed': 20,
                'failure_rate': 0.95  # 95% failure rate
            }
        )
        
        stack_age_result = StackAgeResult(
            effective_age=3.2,
            total_components=1,
            risk_distribution={RiskLevel.WARNING: 1, RiskLevel.OK: 0, RiskLevel.CRITICAL: 0},
            oldest_critical_component=None,
            roast_commentary="Found only 1 component out of 21 attempts - this analysis is highly incomplete!"
        )
        
        with patch('app.main.github_analyzer') as mock_analyzer, \
             patch('app.main.carbon_dating_engine') as mock_engine:
            
            mock_analyzer.analyze_repository = AsyncMock(return_value=partial_result)
            mock_engine.calculate_stack_age = MagicMock(return_value=stack_age_result)
            
            response = client.post("/api/analyze", json={
                "url": "https://github.com/user/repo",
                "analysis_type": "github"
            })
            
            # Should still succeed but with strong warnings
            assert response.status_code == 200
            
            data = response.json()
            metadata = data["analysis_metadata"]
            
            # Should accurately track the high failure rate
            assert metadata["components_detected"] == 1
            assert metadata["components_failed"] == 20
            
            # Should still provide the one successful result
            assert len(data["components"]) == 1
            assert data["components"][0]["name"] == "python"
    
    def test_partial_success_with_critical_components_only(self):
        """Test partial success when only critical components are detected."""
        client = create_test_client()
        
        # Only critical components succeed
        successful_components = [
            Component(
                name="ubuntu",
                version="16.04",
                release_date=date(2016, 4, 21),
                category=ComponentCategory.OPERATING_SYSTEM,
                risk_level=RiskLevel.CRITICAL,
                age_years=7.8,
                weight=0.8
            ),
            Component(
                name="python",
                version="2.7.0",
                release_date=date(2010, 7, 3),
                category=ComponentCategory.PROGRAMMING_LANGUAGE,
                risk_level=RiskLevel.CRITICAL,
                age_years=13.5,
                weight=0.7
            )
        ]
        
        # Many non-critical components failed
        failed_detections = [
            "modern-library@3.0.0: not found",
            "new-framework@2.1.0: parsing failed",
            "recent-tool@1.5.0: version lookup failed"
        ]
        
        partial_result = ComponentDetectionResult(
            detected_components=successful_components,
            failed_detections=failed_detections,
            detection_metadata={
                'analysis_type': 'github',
                'components_detected': 2,
                'components_failed': 3,
                'critical_components_found': 2
            }
        )
        
        stack_age_result = StackAgeResult(
            effective_age=9.8,  # High age due to critical components
            total_components=2,
            risk_distribution={RiskLevel.CRITICAL: 2, RiskLevel.WARNING: 0, RiskLevel.OK: 0},
            oldest_critical_component=successful_components[1],  # Python 2.7
            roast_commentary="Your infrastructure is ancient! Plus there are newer components we couldn't analyze."
        )
        
        with patch('app.main.github_analyzer') as mock_analyzer, \
             patch('app.main.carbon_dating_engine') as mock_engine:
            
            mock_analyzer.analyze_repository = AsyncMock(return_value=partial_result)
            mock_engine.calculate_stack_age = MagicMock(return_value=stack_age_result)
            
            response = client.post("/api/analyze", json={
                "url": "https://github.com/user/repo",
                "analysis_type": "github"
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Should highlight the critical nature of detected components
            risk_dist = data["stack_age_result"]["risk_distribution"]
            assert risk_dist["critical"] == 2, "Should show critical components"
            
            # Should have high effective age due to critical components
            assert data["stack_age_result"]["effective_age"] > 9.0, "Should reflect critical component ages"
            
            # Should still track the failed detections
            assert data["analysis_metadata"]["components_failed"] == 3
    
    def test_partial_success_metadata_completeness(self):
        """Test that partial success includes complete metadata about what succeeded and failed."""
        client = create_test_client()
        
        successful_components = [
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
        
        failed_detections = [
            "package.json: file not found",
            "requirements.txt: parsing error"
        ]
        
        # Rich metadata about the partial analysis
        detection_metadata = {
            'analysis_type': 'website',
            'detection_time_ms': 1200,
            'files_analyzed': 5,
            'files_successful': 1,
            'files_failed': 2,
            'files_skipped': 2,
            'components_detected': 1,
            'components_failed': 2,
            'detection_methods_used': ['http_headers', 'response_analysis'],
            'detection_methods_failed': ['file_parsing', 'api_lookup']
        }
        
        partial_result = ComponentDetectionResult(
            detected_components=successful_components,
            failed_detections=failed_detections,
            detection_metadata=detection_metadata
        )
        
        stack_age_result = StackAgeResult(
            effective_age=3.7,
            total_components=1,
            risk_distribution={RiskLevel.WARNING: 1, RiskLevel.OK: 0, RiskLevel.CRITICAL: 0},
            oldest_critical_component=None,
            roast_commentary="Found one aging web server, but the full picture remains elusive!"
        )
        
        with patch('app.main.http_scraper') as mock_scraper, \
             patch('app.main.carbon_dating_engine') as mock_engine:
            
            mock_scraper.analyze_website = AsyncMock(return_value=partial_result)
            mock_engine.calculate_stack_age = MagicMock(return_value=stack_age_result)
            
            response = client.post("/api/analyze", json={
                "url": "https://example.com",
                "analysis_type": "website"
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Should include comprehensive metadata
            metadata = data["analysis_metadata"]
            
            # Basic counts
            assert metadata["components_detected"] == 1
            assert metadata["components_failed"] == 2
            
            # Should preserve rich detection metadata
            assert metadata["files_analyzed"] == 5
            assert metadata["files_successful"] == 1
            assert metadata["files_failed"] == 2
            assert metadata["detection_time_ms"] == 1200
            
            # Should include method information
            assert "detection_methods_used" in metadata
            assert "detection_methods_failed" in metadata