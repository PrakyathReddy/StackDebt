"""
Unit tests for specific error scenarios.

Tests specific error conditions mentioned in requirements:
- Private repository access (Requirement 9.1)
- Unreachable websites and blocked scraping (Requirement 9.2)  
- No components detected (Requirement 9.3)

**Validates: Requirements 9.1, 9.2, 9.3**
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import date
import httpx

from app.main import app
from app.schemas import (
    Component, ComponentCategory, RiskLevel, 
    ComponentDetectionResult, StackAgeResult
)


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestPrivateRepositoryAccess:
    """
    Test private repository access error scenarios.
    
    **Validates: Requirement 9.1**
    WHEN a GitHub repository is private or inaccessible, THE StackDebt_System 
    SHALL display a clear error message explaining access requirements
    """
    
    @patch('app.main.github_analyzer')
    def test_private_repository_403_error(self, mock_analyzer, client):
        """Test handling of 403 Forbidden error for private repositories."""
        # Create a mock 403 response
        mock_response = MagicMock()
        mock_response.status_code = 403
        
        # Setup GitHub analyzer to raise 403 error
        mock_analyzer.analyze_repository = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Forbidden", 
                request=httpx.Request("GET", "https://api.github.com/repos/user/private-repo"),
                response=mock_response
            )
        )
        
        response = client.post("/api/analyze", json={
            "url": "https://github.com/user/private-repo",
            "analysis_type": "github"
        })
        
        # Should return 403 status code
        assert response.status_code == 403
        
        error_detail = response.json()["detail"]
        
        # Should provide clear error message about access
        assert "Access forbidden" in error_detail["message"]
        assert "repository may be private" in error_detail["message"]
        
        # Should provide helpful suggestions
        assert "suggestions" in error_detail
        suggestions = error_detail["suggestions"]
        assert any("repository is public" in suggestion for suggestion in suggestions)
        assert any("rate limits" in suggestion for suggestion in suggestions)
        assert any("Try again later" in suggestion for suggestion in suggestions)
    
    @patch('app.main.github_analyzer')
    def test_private_repository_404_error(self, mock_analyzer, client):
        """Test handling of 404 Not Found error for private/non-existent repositories."""
        # Create a mock 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        # Setup GitHub analyzer to raise 404 error
        mock_analyzer.analyze_repository = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Not found", 
                request=httpx.Request("GET", "https://api.github.com/repos/user/nonexistent"),
                response=mock_response
            )
        )
        
        response = client.post("/api/analyze", json={
            "url": "https://github.com/user/nonexistent",
            "analysis_type": "github"
        })
        
        # Should return 404 status code
        assert response.status_code == 404
        
        error_detail = response.json()["detail"]
        
        # Should provide clear error message
        assert "Repository not found" in error_detail["message"]
        assert "not accessible" in error_detail["message"]
        
        # Should provide helpful suggestions
        assert "suggestions" in error_detail
        suggestions = error_detail["suggestions"]
        assert any("URL is correct" in suggestion for suggestion in suggestions)
        assert any("repository is public" in suggestion for suggestion in suggestions)
        assert any("accessible" in suggestion for suggestion in suggestions)
    
    @patch('app.main.github_analyzer')
    def test_github_api_rate_limit_error(self, mock_analyzer, client):
        """Test handling of GitHub API rate limiting."""
        # Create a mock 403 response with rate limit headers
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.headers = {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "1640995200"
        }
        
        # Setup GitHub analyzer to raise rate limit error
        mock_analyzer.analyze_repository = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "API rate limit exceeded", 
                request=httpx.Request("GET", "https://api.github.com/repos/user/repo"),
                response=mock_response
            )
        )
        
        response = client.post("/api/analyze", json={
            "url": "https://github.com/user/repo",
            "analysis_type": "github"
        })
        
        # Should return 403 status code
        assert response.status_code == 403
        
        error_detail = response.json()["detail"]
        
        # Should mention rate limiting in suggestions
        suggestions = error_detail["suggestions"]
        assert any("rate limits" in suggestion for suggestion in suggestions)
        assert any("Try again later" in suggestion for suggestion in suggestions)
    
    @patch('app.main.github_analyzer')
    def test_github_authentication_required_error(self, mock_analyzer, client):
        """Test handling when GitHub requires authentication for private repo."""
        # Create a mock 401 response
        mock_response = MagicMock()
        mock_response.status_code = 401
        
        # Setup GitHub analyzer to raise authentication error
        mock_analyzer.analyze_repository = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Requires authentication", 
                request=httpx.Request("GET", "https://api.github.com/repos/user/private-repo"),
                response=mock_response
            )
        )
        
        response = client.post("/api/analyze", json={
            "url": "https://github.com/user/private-repo",
            "analysis_type": "github"
        })
        
        # Should return 401 status code (mapped from HTTPStatusError)
        assert response.status_code == 401
        
        error_detail = response.json()["detail"]
        
        # Should provide clear error message about authentication
        assert "HTTP error 401" in error_detail["message"]
        assert "error" in error_detail
    
    def test_invalid_github_url_format(self, client):
        """Test handling of invalid GitHub URL formats."""
        response = client.post("/api/analyze", json={
            "url": "https://github.com/user",  # Missing repository name
            "analysis_type": "github"
        })
        
        # Currently returns 500 because GitHub URL validation happens in analyzer
        # This is caught by the general exception handler
        assert response.status_code == 500
        
        # Should provide user-friendly error message (not technical details)
        error_detail = response.json()["detail"]
        assert "message" in error_detail
        assert "An unexpected error occurred" in error_detail["message"]
        assert "error" in error_detail
        assert error_detail["error"] == "Internal server error"


class TestUnreachableWebsites:
    """
    Test unreachable website and blocked scraping error scenarios.
    
    **Validates: Requirement 9.2**
    WHEN a website is unreachable or blocks scraping, THE StackDebt_System 
    SHALL inform the user and suggest alternatives
    """
    
    @patch('app.main.http_scraper')
    def test_website_connection_timeout(self, mock_scraper, client):
        """Test handling of website connection timeout."""
        # Setup HTTP scraper to raise timeout error
        mock_scraper.analyze_website = AsyncMock(
            side_effect=httpx.TimeoutException("Request timed out after 10 seconds")
        )
        
        response = client.post("/api/analyze", json={
            "url": "https://slow-website.example.com",
            "analysis_type": "website"
        })
        
        # Should return 503 Service Unavailable
        assert response.status_code == 503
        
        error_detail = response.json()["detail"]
        
        # Should provide clear error message about timeout
        assert "Unable to access the provided URL" in error_detail["message"]
        
        # Should provide helpful suggestions
        assert "suggestions" in error_detail
        suggestions = error_detail["suggestions"]
        assert any("URL is correct" in suggestion for suggestion in suggestions)
        assert any("internet connection" in suggestion for suggestion in suggestions)
        assert any("Try again" in suggestion for suggestion in suggestions)
    
    @patch('app.main.http_scraper')
    def test_website_connection_refused(self, mock_scraper, client):
        """Test handling of website connection refused."""
        # Setup HTTP scraper to raise connection error
        mock_scraper.analyze_website = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        
        response = client.post("/api/analyze", json={
            "url": "https://unreachable-site.example.com",
            "analysis_type": "website"
        })
        
        # Should return 503 Service Unavailable
        assert response.status_code == 503
        
        error_detail = response.json()["detail"]
        
        # Should provide clear error message about connection
        assert "Unable to access the provided URL" in error_detail["message"]
        
        # Should provide helpful suggestions
        suggestions = error_detail["suggestions"]
        assert any("URL is correct" in suggestion for suggestion in suggestions)
        assert any("internet connection" in suggestion for suggestion in suggestions)
    
    @patch('app.main.http_scraper')
    def test_website_blocks_scraping_403(self, mock_scraper, client):
        """Test handling when website blocks scraping with 403 Forbidden."""
        # Create a mock 403 response
        mock_response = MagicMock()
        mock_response.status_code = 403
        
        # Setup HTTP scraper to raise 403 error
        mock_scraper.analyze_website = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Forbidden", 
                request=httpx.Request("GET", "https://protected-site.example.com"),
                response=mock_response
            )
        )
        
        response = client.post("/api/analyze", json={
            "url": "https://protected-site.example.com",
            "analysis_type": "website"
        })
        
        # Should return 403 Forbidden
        assert response.status_code == 403
        
        error_detail = response.json()["detail"]
        
        # Should provide clear error message about access
        assert "Access forbidden" in error_detail["message"]
        
        # Should provide helpful suggestions
        suggestions = error_detail["suggestions"]
        assert any("repository is public" in suggestion for suggestion in suggestions)
        assert any("rate limits" in suggestion for suggestion in suggestions)
    
    @patch('app.main.http_scraper')
    def test_website_not_found_404(self, mock_scraper, client):
        """Test handling when website returns 404 Not Found."""
        # Create a mock 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        # Setup HTTP scraper to raise 404 error
        mock_scraper.analyze_website = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Not Found", 
                request=httpx.Request("GET", "https://missing-page.example.com"),
                response=mock_response
            )
        )
        
        response = client.post("/api/analyze", json={
            "url": "https://missing-page.example.com",
            "analysis_type": "website"
        })
        
        # Should return 404 Not Found
        assert response.status_code == 404
        
        error_detail = response.json()["detail"]
        
        # Should provide clear error message
        assert "Repository not found" in error_detail["message"]
        assert "not accessible" in error_detail["message"]
        
        # Should provide helpful suggestions
        suggestions = error_detail["suggestions"]
        assert any("URL is correct" in suggestion for suggestion in suggestions)
        assert any("online and accessible" in suggestion for suggestion in suggestions)
    
    @patch('app.main.http_scraper')
    def test_website_server_error_500(self, mock_scraper, client):
        """Test handling when website returns 500 Internal Server Error."""
        # Create a mock 500 response
        mock_response = MagicMock()
        mock_response.status_code = 500
        
        # Setup HTTP scraper to raise 500 error
        mock_scraper.analyze_website = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Internal Server Error", 
                request=httpx.Request("GET", "https://broken-site.example.com"),
                response=mock_response
            )
        )
        
        response = client.post("/api/analyze", json={
            "url": "https://broken-site.example.com",
            "analysis_type": "website"
        })
        
        # Should return 500 Internal Server Error
        assert response.status_code == 500
        
        error_detail = response.json()["detail"]
        
        # Should provide clear error message about HTTP error
        assert "HTTP error 500" in error_detail["message"]
        assert "error" in error_detail
    
    @patch('app.main.http_scraper')
    def test_website_dns_resolution_failure(self, mock_scraper, client):
        """Test handling of DNS resolution failures."""
        # Setup HTTP scraper to raise DNS error
        mock_scraper.analyze_website = AsyncMock(
            side_effect=httpx.ConnectError("Name or service not known")
        )
        
        response = client.post("/api/analyze", json={
            "url": "https://nonexistent-domain.invalid",
            "analysis_type": "website"
        })
        
        # Should return 503 Service Unavailable
        assert response.status_code == 503
        
        error_detail = response.json()["detail"]
        
        # Should provide clear error message
        assert "Unable to access the provided URL" in error_detail["message"]
        
        # Should provide helpful suggestions
        suggestions = error_detail["suggestions"]
        assert any("URL is correct" in suggestion for suggestion in suggestions)
    
    @patch('app.main.http_scraper')
    def test_website_ssl_certificate_error(self, mock_scraper, client):
        """Test handling of SSL certificate errors."""
        # Setup HTTP scraper to raise SSL error
        mock_scraper.analyze_website = AsyncMock(
            side_effect=httpx.ConnectError("SSL certificate verification failed")
        )
        
        response = client.post("/api/analyze", json={
            "url": "https://invalid-ssl.example.com",
            "analysis_type": "website"
        })
        
        # Should return 503 Service Unavailable
        assert response.status_code == 503
        
        error_detail = response.json()["detail"]
        
        # Should provide clear error message
        assert "Unable to access the provided URL" in error_detail["message"]


class TestNoComponentsDetected:
    """
    Test scenarios where no components are detected.
    
    **Validates: Requirement 9.3**
    WHEN analysis produces no detectable components, THE StackDebt_System 
    SHALL explain possible reasons and suggest troubleshooting steps
    """
    
    @patch('app.main.github_analyzer')
    def test_empty_github_repository(self, mock_analyzer, client):
        """Test handling of empty GitHub repository with no package files."""
        # Setup analyzer to return empty result
        empty_result = ComponentDetectionResult(
            detected_components=[],
            failed_detections=[
                "package.json: file not found",
                "requirements.txt: file not found",
                "go.mod: file not found",
                "pom.xml: file not found"
            ],
            detection_metadata={
                'analysis_type': 'github',
                'files_analyzed': 0,
                'detection_time_ms': 200
            }
        )
        
        mock_analyzer.analyze_repository = AsyncMock(return_value=empty_result)
        
        response = client.post("/api/analyze", json={
            "url": "https://github.com/user/empty-repo",
            "analysis_type": "github"
        })
        
        # Should return 422 Unprocessable Entity
        assert response.status_code == 422
        
        error_detail = response.json()["detail"]
        
        # Should provide clear error message
        assert "No software components detected" in error_detail["message"]
        
        # Should provide helpful suggestions
        assert "suggestions" in error_detail
        suggestions = error_detail["suggestions"]
        assert any("package files" in suggestion for suggestion in suggestions)
        assert any("package.json" in suggestion for suggestion in suggestions)
        assert any("requirements.txt" in suggestion for suggestion in suggestions)
        assert any("URL is correct" in suggestion for suggestion in suggestions)
        
        # Should include failed detections for debugging
        assert "failed_detections" in error_detail
        assert len(error_detail["failed_detections"]) == 4
        assert "package.json: file not found" in error_detail["failed_detections"]
    
    @patch('app.main.http_scraper')
    def test_website_no_detectable_technologies(self, mock_scraper, client):
        """Test handling of website with no detectable technologies."""
        # Setup scraper to return empty result
        empty_result = ComponentDetectionResult(
            detected_components=[],
            failed_detections=[
                "Server header: not present",
                "X-Powered-By header: not present",
                "X-Generator header: not present"
            ],
            detection_metadata={
                'analysis_type': 'website',
                'headers_analyzed': 3,
                'detection_time_ms': 150
            }
        )
        
        mock_scraper.analyze_website = AsyncMock(return_value=empty_result)
        
        response = client.post("/api/analyze", json={
            "url": "https://static-site.example.com",
            "analysis_type": "website"
        })
        
        # Should return 422 Unprocessable Entity
        assert response.status_code == 422
        
        error_detail = response.json()["detail"]
        
        # Should provide clear error message
        assert "No software components detected" in error_detail["message"]
        
        # Should provide helpful suggestions
        suggestions = error_detail["suggestions"]
        assert any("publicly accessible" in suggestion for suggestion in suggestions)
        assert any("URL is correct" in suggestion for suggestion in suggestions)
        
        # Should include failed detections
        assert "failed_detections" in error_detail
        assert "Server header: not present" in error_detail["failed_detections"]
    
    @patch('app.main.github_analyzer')
    def test_repository_with_parsing_failures(self, mock_analyzer, client):
        """Test handling of repository where all package files fail to parse."""
        # Setup analyzer to return result with parsing failures
        failed_result = ComponentDetectionResult(
            detected_components=[],
            failed_detections=[
                "package.json: JSON parsing error on line 5",
                "requirements.txt: invalid format",
                "go.mod: syntax error",
                "pom.xml: XML parsing failed"
            ],
            detection_metadata={
                'analysis_type': 'github',
                'files_analyzed': 4,
                'files_failed': 4,
                'detection_time_ms': 800
            }
        )
        
        mock_analyzer.analyze_repository = AsyncMock(return_value=failed_result)
        
        response = client.post("/api/analyze", json={
            "url": "https://github.com/user/corrupted-repo",
            "analysis_type": "github"
        })
        
        # Should return 422 Unprocessable Entity
        assert response.status_code == 422
        
        error_detail = response.json()["detail"]
        
        # Should provide clear error message
        assert "No software components detected" in error_detail["message"]
        
        # Should include specific parsing failures
        failed_detections = error_detail["failed_detections"]
        assert any("JSON parsing error" in failure for failure in failed_detections)
        assert any("invalid format" in failure for failure in failed_detections)
        assert any("syntax error" in failure for failure in failed_detections)
        assert any("XML parsing failed" in failure for failure in failed_detections)
    
    @patch('app.main.github_analyzer')
    def test_repository_with_unrecognized_files(self, mock_analyzer, client):
        """Test handling of repository with only unrecognized file types."""
        # Setup analyzer to return result with unrecognized files
        unrecognized_result = ComponentDetectionResult(
            detected_components=[],
            failed_detections=[
                "custom-config.yaml: unrecognized format",
                "build.sh: shell script, no version info",
                "README.md: documentation file",
                "LICENSE: license file"
            ],
            detection_metadata={
                'analysis_type': 'github',
                'files_analyzed': 4,
                'files_recognized': 0,
                'detection_time_ms': 300
            }
        )
        
        mock_analyzer.analyze_repository = AsyncMock(return_value=unrecognized_result)
        
        response = client.post("/api/analyze", json={
            "url": "https://github.com/user/docs-only-repo",
            "analysis_type": "github"
        })
        
        # Should return 422 Unprocessable Entity
        assert response.status_code == 422
        
        error_detail = response.json()["detail"]
        
        # Should provide clear error message
        assert "No software components detected" in error_detail["message"]
        
        # Should provide helpful suggestions
        suggestions = error_detail["suggestions"]
        assert any("recognizable package files" in suggestion for suggestion in suggestions)
        
        # Should include information about unrecognized files
        failed_detections = error_detail["failed_detections"]
        assert any("unrecognized format" in failure for failure in failed_detections)
        assert any("no version info" in failure for failure in failed_detections)
    
    @patch('app.main.github_analyzer')
    @patch('app.main.carbon_dating_engine')
    def test_components_detected_but_calculation_fails(self, mock_engine, mock_analyzer, client):
        """Test when components are detected but age calculation fails."""
        # Setup analyzer to return components
        components = [
            Component(
                name="unknown-package",
                version="unknown",
                release_date=date.today(),
                category=ComponentCategory.LIBRARY,
                risk_level=RiskLevel.OK,
                age_years=0.0,
                weight=0.1
            )
        ]
        
        detection_result = ComponentDetectionResult(
            detected_components=components,
            failed_detections=[],
            detection_metadata={'analysis_type': 'github'}
        )
        
        mock_analyzer.analyze_repository = AsyncMock(return_value=detection_result)
        
        # Setup carbon dating engine to fail
        mock_engine.calculate_stack_age = MagicMock(
            side_effect=ValueError("No valid components for age calculation")
        )
        
        response = client.post("/api/analyze", json={
            "url": "https://github.com/user/unknown-components-repo",
            "analysis_type": "github"
        })
        
        # Should return 422 Unprocessable Entity
        assert response.status_code == 422
        
        error_detail = response.json()["detail"]
        
        # Should provide clear error message about calculation failure
        assert "Unable to calculate stack age" in error_detail["message"]
        assert "No valid components for age calculation" in error_detail["message"]
        
        # Should include information about detected components
        assert "detected_components" in error_detail
        assert error_detail["detected_components"] == 1
    
    def test_invalid_url_format_error_message(self, client):
        """Test error message for invalid URL formats."""
        response = client.post("/api/analyze", json={
            "url": "not-a-valid-url",
            "analysis_type": "website"
        })
        
        # Should return 422 for validation error
        assert response.status_code == 422
        
        # Should provide clear error message about URL format
        error_detail = response.json()["detail"]
        assert isinstance(error_detail, list)  # Pydantic validation errors
        
        # Find the URL validation error
        url_error = next((err for err in error_detail if 'url' in err.get('loc', [])), None)
        assert url_error is not None
        assert "URL must start with http://" in url_error['msg']
    
    def test_unsupported_analysis_type_error(self, client):
        """Test error message for unsupported analysis types."""
        response = client.post("/api/analyze", json={
            "url": "https://example.com",
            "analysis_type": "unsupported"
        })
        
        # Should return 422 for validation error
        assert response.status_code == 422
        
        # Should provide clear error message about analysis type
        error_detail = response.json()["detail"]
        assert isinstance(error_detail, list)  # Pydantic validation errors
        
        # Find the analysis_type validation error
        type_error = next((err for err in error_detail if 'analysis_type' in err.get('loc', [])), None)
        assert type_error is not None
        assert "analysis_type must be" in type_error['msg']


class TestErrorMessageQuality:
    """
    Test the quality and helpfulness of error messages.
    
    Ensures error messages are user-friendly and provide actionable guidance.
    """
    
    @patch('app.main.github_analyzer')
    def test_error_message_structure_consistency(self, mock_analyzer, client):
        """Test that error messages follow consistent structure."""
        # Setup a 403 error
        mock_response = MagicMock()
        mock_response.status_code = 403
        
        mock_analyzer.analyze_repository = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Forbidden", 
                request=httpx.Request("GET", "https://api.github.com/repos/user/private"),
                response=mock_response
            )
        )
        
        response = client.post("/api/analyze", json={
            "url": "https://github.com/user/private",
            "analysis_type": "github"
        })
        
        error_detail = response.json()["detail"]
        
        # Should have consistent structure
        assert isinstance(error_detail, dict)
        assert "message" in error_detail
        assert "suggestions" in error_detail
        
        # Message should be user-friendly
        message = error_detail["message"]
        assert len(message) > 0
        assert not any(tech_term in message.lower() for tech_term in [
            'exception', 'traceback', 'null pointer', 'stack trace'
        ])
        
        # Suggestions should be actionable
        suggestions = error_detail["suggestions"]
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        for suggestion in suggestions:
            assert isinstance(suggestion, str)
            assert len(suggestion) > 10  # Should be meaningful
    
    @patch('app.main.http_scraper')
    def test_error_suggestions_are_relevant(self, mock_scraper, client):
        """Test that error suggestions are relevant to the error type."""
        # Setup a timeout error
        mock_scraper.analyze_website = AsyncMock(
            side_effect=httpx.TimeoutException("Request timed out")
        )
        
        response = client.post("/api/analyze", json={
            "url": "https://slow-site.example.com",
            "analysis_type": "website"
        })
        
        error_detail = response.json()["detail"]
        suggestions = error_detail["suggestions"]
        
        # Suggestions should be relevant to timeout errors
        suggestion_text = " ".join(suggestions).lower()
        assert any(keyword in suggestion_text for keyword in [
            "slow", "timeout", "try again", "moments", "accessible"
        ])
        
        # Should not contain irrelevant suggestions
        assert "repository is public" not in suggestion_text  # This is for GitHub errors
    
    @patch('app.main.github_analyzer')
    def test_error_logging_contains_technical_details(self, mock_analyzer, client):
        """Test that technical details are logged but not shown to user."""
        # Setup an error with technical details
        technical_error = Exception("Database connection pool exhausted: max_connections=20")
        mock_analyzer.analyze_repository = AsyncMock(side_effect=technical_error)
        
        with patch('app.main.logger') as mock_logger:
            response = client.post("/api/analyze", json={
                "url": "https://github.com/user/repo",
                "analysis_type": "github"
            })
            
            # Should log technical details
            mock_logger.error.assert_called()
            logged_message = mock_logger.error.call_args[0][0]
            assert "Unexpected error" in logged_message
            
            # User should get friendly message
            error_detail = response.json()["detail"]
            user_message = error_detail["message"]
            assert "An unexpected error occurred" in user_message
            assert "database connection pool" not in user_message.lower()