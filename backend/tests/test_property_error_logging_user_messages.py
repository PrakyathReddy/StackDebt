"""
Property-based tests for error logging and user messages functionality.

**Feature: stackdebt, Property 23: Error Logging and User Messages**
**Validates: Requirements 9.4**

Property 23: Error Logging and User Messages
For any error condition, the system should log detailed error information for debugging 
while displaying user-friendly messages to the user
"""

import pytest
import asyncio
import logging
from hypothesis import given, strategies as st, settings, HealthCheck
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import date
import httpx

from app.main import app
from app.schemas import (
    Component, ComponentCategory, RiskLevel, 
    ComponentDetectionResult, StackAgeResult
)


def create_test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


# Strategies for generating different types of errors
error_scenarios = st.sampled_from([
    'network_timeout',
    'connection_error', 
    'http_404',
    'http_403',
    'http_500',
    'invalid_url',
    'no_components_detected',
    'calculation_error',
    'unexpected_exception'
])

test_urls = st.sampled_from([
    "https://github.com/user/repo",
    "https://example.com",
    "https://test-site.org",
    "https://unreachable-site.invalid"
])

analysis_types = st.sampled_from(['website', 'github'])


class TestProperty23ErrorLoggingAndUserMessages:
    """
    Test Property 23: Error Logging and User Messages
    
    For any error condition, the system should log detailed error information for debugging 
    while displaying user-friendly messages to the user.
    """
    
    @given(error_scenario=error_scenarios)
    @settings(
        max_examples=10,  # Reduced for faster execution as requested
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_23_error_logging_and_user_messages(self, error_scenario):
        """
        **Feature: stackdebt, Property 23: Error Logging and User Messages**
        
        For any error condition, the system should log detailed error information for debugging 
        while displaying user-friendly messages to the user.
        
        **Validates: Requirements 9.4**
        """
        client = create_test_client()
        
        # Use compatible URL/analysis type combination
        url = "https://github.com/user/repo"
        analysis_type = "github"
        
        with patch('app.main.github_analyzer') as mock_analyzer, \
             patch('app.main.http_scraper') as mock_scraper, \
             patch('app.main.carbon_dating_engine') as mock_engine:
            
            # Setup error scenario
            self._setup_error_scenario(mock_analyzer, mock_scraper, mock_engine, error_scenario, url)
            
            # Capture logs to verify detailed error logging
            with patch('app.main.logger') as mock_logger:
                response = client.post("/api/analyze", json={
                    "url": url,
                    "analysis_type": analysis_type
                })
                
                # Property: System should log detailed error information for debugging
                if error_scenario in ['network_timeout', 'connection_error', 'http_404', 'http_403', 'http_500']:
                    # Network and HTTP errors should be logged with technical details
                    mock_logger.error.assert_called()
                    error_log_call = mock_logger.error.call_args[0][0]
                    assert any(keyword in error_log_call.lower() for keyword in ['error', 'failed', 'exception']), (
                        "Should log detailed technical error information"
                    )
                elif error_scenario == 'unexpected_exception':
                    # Unexpected exceptions should be logged with full details
                    mock_logger.error.assert_called()
                    error_log_call = mock_logger.error.call_args[0][0]
                    assert "Unexpected error" in error_log_call, (
                        "Should log unexpected errors with technical details"
                    )
                elif error_scenario == 'no_components_detected':
                    # Component detection failures should be logged as warnings
                    if hasattr(mock_logger, 'warning') and mock_logger.warning.called:
                        warning_log_call = mock_logger.warning.call_args[0][0]
                        assert any(keyword in warning_log_call.lower() for keyword in ['failed', 'detect', 'component']), (
                            "Should log component detection failures"
                        )
                
                # Property: System should display user-friendly messages to the user
                assert response.status_code in [400, 403, 404, 422, 500, 503, 504], (
                    "Should return appropriate HTTP status code for errors"
                )
                
                response_data = response.json()
                assert "detail" in response_data, "Should include error details in response"
                
                error_detail = response_data["detail"]
                if isinstance(error_detail, dict):
                    # Structured error response
                    assert "message" in error_detail, "Should include user-friendly message"
                    user_message = error_detail["message"]
                    
                    # User message should be friendly and non-technical
                    assert len(user_message) > 0, "User message should not be empty"
                    assert not any(tech_term in user_message.lower() for tech_term in [
                        'exception', 'traceback', 'stack trace', 'internal error', 'null pointer'
                    ]), "User message should not contain technical jargon"
                    
                    # Should provide helpful suggestions when appropriate
                    if "suggestions" in error_detail:
                        suggestions = error_detail["suggestions"]
                        assert isinstance(suggestions, list), "Suggestions should be a list"
                        assert len(suggestions) > 0, "Should provide helpful suggestions"
                        for suggestion in suggestions:
                            assert isinstance(suggestion, str), "Each suggestion should be a string"
                            assert len(suggestion) > 10, "Suggestions should be meaningful"
                else:
                    # Simple string error response
                    assert isinstance(error_detail, str), "Error detail should be a string"
                    assert len(error_detail) > 0, "Error message should not be empty"
    
    def _setup_error_scenario(self, mock_analyzer, mock_scraper, mock_engine, error_scenario, url):
        """Setup mocks to simulate different error scenarios."""
        
        if error_scenario == 'network_timeout':
            if 'github.com' in url:
                mock_analyzer.analyze_repository = AsyncMock(
                    side_effect=httpx.TimeoutException("Request timed out")
                )
            else:
                mock_scraper.analyze_website = AsyncMock(
                    side_effect=httpx.TimeoutException("Request timed out")
                )
        
        elif error_scenario == 'connection_error':
            if 'github.com' in url:
                mock_analyzer.analyze_repository = AsyncMock(
                    side_effect=httpx.ConnectError("Connection failed")
                )
            else:
                mock_scraper.analyze_website = AsyncMock(
                    side_effect=httpx.ConnectError("Connection failed")
                )
        
        elif error_scenario == 'http_404':
            http_error = httpx.HTTPStatusError(
                "Not found", 
                request=httpx.Request("GET", url),
                response=httpx.Response(404)
            )
            if 'github.com' in url:
                mock_analyzer.analyze_repository = AsyncMock(side_effect=http_error)
            else:
                mock_scraper.analyze_website = AsyncMock(side_effect=http_error)
        
        elif error_scenario == 'http_403':
            http_error = httpx.HTTPStatusError(
                "Forbidden", 
                request=httpx.Request("GET", url),
                response=httpx.Response(403)
            )
            if 'github.com' in url:
                mock_analyzer.analyze_repository = AsyncMock(side_effect=http_error)
            else:
                mock_scraper.analyze_website = AsyncMock(side_effect=http_error)
        
        elif error_scenario == 'http_500':
            http_error = httpx.HTTPStatusError(
                "Internal Server Error", 
                request=httpx.Request("GET", url),
                response=httpx.Response(500)
            )
            if 'github.com' in url:
                mock_analyzer.analyze_repository = AsyncMock(side_effect=http_error)
            else:
                mock_scraper.analyze_website = AsyncMock(side_effect=http_error)
        
        elif error_scenario == 'no_components_detected':
            empty_result = ComponentDetectionResult(
                detected_components=[],
                failed_detections=["package.json: parsing failed", "requirements.txt: not found"],
                detection_metadata={'analysis_type': 'github' if 'github.com' in url else 'website'}
            )
            if 'github.com' in url:
                mock_analyzer.analyze_repository = AsyncMock(return_value=empty_result)
            else:
                mock_scraper.analyze_website = AsyncMock(return_value=empty_result)
        
        elif error_scenario == 'calculation_error':
            # Setup successful detection but calculation failure
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
            detection_result = ComponentDetectionResult(
                detected_components=successful_components,
                failed_detections=[],
                detection_metadata={'analysis_type': 'github' if 'github.com' in url else 'website'}
            )
            
            if 'github.com' in url:
                mock_analyzer.analyze_repository = AsyncMock(return_value=detection_result)
            else:
                mock_scraper.analyze_website = AsyncMock(return_value=detection_result)
            
            mock_engine.calculate_stack_age = MagicMock(
                side_effect=ValueError("Invalid component data for calculation")
            )
        
        elif error_scenario == 'unexpected_exception':
            if 'github.com' in url:
                mock_analyzer.analyze_repository = AsyncMock(
                    side_effect=Exception("Unexpected internal error")
                )
            else:
                mock_scraper.analyze_website = AsyncMock(
                    side_effect=Exception("Unexpected internal error")
                )
    
    @patch('app.main.github_analyzer')
    @patch('app.main.logger')
    def test_property_23_detailed_logging_vs_user_messages(self, mock_logger, mock_analyzer):
        """
        Test that detailed technical information is logged while user gets friendly messages.
        
        **Validates: Requirements 9.4**
        """
        client = create_test_client()
        
        # Setup a specific error scenario with technical details
        technical_error = Exception("Database connection pool exhausted: max_connections=20, active=20, idle=0")
        mock_analyzer.analyze_repository = AsyncMock(side_effect=technical_error)
        
        response = client.post("/api/analyze", json={
            "url": "https://github.com/user/repo",
            "analysis_type": "github"
        })
        
        # Should log detailed technical information
        mock_logger.error.assert_called()
        logged_message = mock_logger.error.call_args[0][0]
        assert "Unexpected error" in logged_message, "Should log technical error details"
        
        # Should return user-friendly message
        assert response.status_code == 500
        error_detail = response.json()["detail"]
        assert "message" in error_detail
        user_message = error_detail["message"]
        
        # User message should be friendly, not technical
        assert "An unexpected error occurred" in user_message, "Should provide user-friendly message"
        assert "database connection pool" not in user_message.lower(), "Should not expose technical details to user"
        assert "Internal server error" in error_detail["error"], "Should provide generic error type"
    
    @given(error_types=st.lists(error_scenarios, min_size=1, max_size=3, unique=True))
    @settings(max_examples=5)
    @patch('app.main.github_analyzer')
    @patch('app.main.http_scraper')
    @patch('app.main.carbon_dating_engine')
    @patch('app.main.logger')
    def test_property_23_consistent_error_handling_pattern(self, mock_logger, mock_engine, 
                                                          mock_scraper, mock_analyzer, error_types):
        """
        Test that error handling pattern is consistent across different error types.
        
        **Validates: Requirements 9.4**
        """
        client = create_test_client()
        
        for error_type in error_types:
            # Reset mocks for each error type
            mock_logger.reset_mock()
            
            # Setup error scenario
            self._setup_error_scenario(mock_analyzer, mock_scraper, mock_engine, error_type, "https://github.com/user/repo")
            
            response = client.post("/api/analyze", json={
                "url": "https://github.com/user/repo",
                "analysis_type": "github"
            })
            
            # All errors should follow the same pattern
            assert response.status_code >= 400, f"Error {error_type} should return error status code"
            
            response_data = response.json()
            assert "detail" in response_data, f"Error {error_type} should include detail"
            
            # Should have appropriate logging based on error type
            if error_type in ['network_timeout', 'connection_error', 'http_404', 'http_403', 'http_500', 'unexpected_exception']:
                assert mock_logger.error.called or mock_logger.warning.called, (
                    f"Error {error_type} should be logged"
                )


class TestErrorLoggingAndUserMessagesEdgeCases:
    """Test edge cases for error logging and user messages."""
    
    def test_invalid_url_format_error_handling(self):
        """Test error handling for invalid URL formats."""
        client = create_test_client()
        
        with patch('app.main.logger') as mock_logger:
            response = client.post("/api/analyze", json={
                "url": "not-a-valid-url",
                "analysis_type": "website"
            })
            
            # Should return validation error (422 is the actual status code for validation errors)
            assert response.status_code == 422
            error_detail = response.json()["detail"]
            
            # Error detail is a list of validation errors
            assert isinstance(error_detail, list), "Should return validation error list"
            assert len(error_detail) > 0, "Should have at least one validation error"
            
            # Check that the URL validation error is present
            url_error = next((err for err in error_detail if 'url' in err.get('loc', [])), None)
            assert url_error is not None, "Should have URL validation error"
            assert "URL must start with http://" in url_error['msg'], "Should provide clear URL format guidance"
    
    @patch('app.main.github_analyzer')
    @patch('app.main.logger')
    def test_partial_failure_logging_and_messaging(self, mock_logger, mock_analyzer):
        """Test logging and messaging for partial failures."""
        client = create_test_client()
        
        # Setup partial success scenario
        partial_result = ComponentDetectionResult(
            detected_components=[
                Component(
                    name="python",
                    version="3.9.0",
                    release_date=date(2020, 10, 5),
                    category=ComponentCategory.PROGRAMMING_LANGUAGE,
                    risk_level=RiskLevel.WARNING,
                    age_years=3.2,
                    weight=0.7
                )
            ],
            failed_detections=["unknown-package@1.0.0: not found", "invalid-file: parsing error"],
            detection_metadata={'analysis_type': 'github'}
        )
        
        mock_analyzer.analyze_repository = AsyncMock(return_value=partial_result)
        
        with patch('app.main.carbon_dating_engine') as mock_engine:
            mock_engine.calculate_stack_age = MagicMock(return_value=StackAgeResult(
                effective_age=3.2,
                total_components=1,
                risk_distribution={RiskLevel.WARNING: 1, RiskLevel.OK: 0, RiskLevel.CRITICAL: 0},
                oldest_critical_component=None,
                roast_commentary="Analysis completed with some failures"
            ))
            
            response = client.post("/api/analyze", json={
                "url": "https://github.com/user/repo",
                "analysis_type": "github"
            })
            
            # Should succeed but log warnings about failures
            assert response.status_code == 200
            mock_logger.warning.assert_called()
            
            # Should include failure information in metadata
            data = response.json()
            assert data["analysis_metadata"]["components_failed"] == 2
    
    def test_empty_error_message_handling(self):
        """Test handling of empty or None error messages."""
        client = create_test_client()
        
        with patch('app.main.github_analyzer') as mock_analyzer:
            # Setup error with empty message
            mock_analyzer.analyze_repository = AsyncMock(
                side_effect=Exception("")  # Empty error message
            )
            
            response = client.post("/api/analyze", json={
                "url": "https://github.com/user/repo",
                "analysis_type": "github"
            })
            
            # Should still provide meaningful error response
            assert response.status_code == 500
            error_detail = response.json()["detail"]
            assert "message" in error_detail
            assert len(error_detail["message"]) > 0, "Should provide meaningful error message even when exception message is empty"