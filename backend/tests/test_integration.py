"""
Integration tests for the FastAPI application.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import date

from app.main import app
from app.schemas import (
    Component, ComponentCategory, RiskLevel, 
    ComponentDetectionResult, StackAgeResult
)


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestFullIntegration:
    """Test full integration scenarios."""
    
    @patch('app.main.github_analyzer')
    @patch('app.main.carbon_dating_engine')
    def test_full_github_analysis_flow(self, mock_engine, mock_analyzer, client):
        """Test the complete GitHub analysis flow."""
        # Create realistic mock data
        mock_components = [
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
                name="django",
                version="3.2.0",
                release_date=date(2021, 4, 6),
                category=ComponentCategory.FRAMEWORK,
                risk_level=RiskLevel.WARNING,
                age_years=2.7,
                weight=0.3
            ),
            Component(
                name="requests",
                version="2.28.0",
                release_date=date(2022, 6, 29),
                category=ComponentCategory.LIBRARY,
                risk_level=RiskLevel.OK,
                age_years=1.4,
                weight=0.1
            )
        ]
        
        mock_detection_result = ComponentDetectionResult(
            detected_components=mock_components,
            failed_detections=["unknown-package@1.0.0: not found in database"],
            detection_metadata={
                'repository_url': 'https://github.com/user/django-app',
                'owner': 'user',
                'repo': 'django-app',
                'files_analyzed': 5,
                'detection_time_ms': 1200,
                'analysis_type': 'github'
            }
        )
        
        mock_stack_age_result = StackAgeResult(
            effective_age=2.8,
            total_components=3,
            risk_distribution={
                RiskLevel.CRITICAL: 0,
                RiskLevel.WARNING: 2,
                RiskLevel.OK: 1
            },
            oldest_critical_component=None,
            roast_commentary="⚠️ Getting a bit long in the tooth. Time to start planning some updates!"
        )
        
        # Setup mocks
        mock_analyzer.analyze_repository = AsyncMock(return_value=mock_detection_result)
        mock_engine.calculate_stack_age = MagicMock(return_value=mock_stack_age_result)
        
        # Make the request
        response = client.post("/api/analyze", json={
            "url": "https://github.com/user/django-app",
            "analysis_type": "github"
        })
        
        # Verify the response
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "stack_age_result" in data
        assert "components" in data
        assert "analysis_metadata" in data
        assert "generated_at" in data
        
        # Check stack age result
        stack_result = data["stack_age_result"]
        assert stack_result["effective_age"] == 2.8
        assert stack_result["total_components"] == 3
        assert stack_result["risk_distribution"]["warning"] == 2
        assert stack_result["risk_distribution"]["ok"] == 1
        assert stack_result["risk_distribution"]["critical"] == 0
        assert "Getting a bit long in the tooth" in stack_result["roast_commentary"]
        
        # Check components
        components = data["components"]
        assert len(components) == 3
        
        # Check Python component
        python_component = next(c for c in components if c["name"] == "python")
        assert python_component["version"] == "3.9.0"
        assert python_component["category"] == "programming_language"
        assert python_component["risk_level"] == "warning"
        assert python_component["age_years"] == 3.2
        assert python_component["weight"] == 0.7
        
        # Check analysis metadata
        metadata = data["analysis_metadata"]
        assert metadata["analysis_type"] == "github"
        assert metadata["components_detected"] == 3
        assert metadata["components_failed"] == 1
        assert "analysis_duration_ms" in metadata
        
        # Verify mocks were called correctly
        mock_analyzer.analyze_repository.assert_called_once_with("https://github.com/user/django-app")
        mock_engine.calculate_stack_age.assert_called_once_with(mock_components)
    
    @patch('app.main.http_scraper')
    @patch('app.main.carbon_dating_engine')
    def test_full_website_analysis_flow(self, mock_engine, mock_scraper, client):
        """Test the complete website analysis flow."""
        # Create realistic mock data for website analysis
        mock_components = [
            Component(
                name="nginx",
                version="1.18.0",
                release_date=date(2020, 4, 21),
                category=ComponentCategory.WEB_SERVER,
                risk_level=RiskLevel.WARNING,
                age_years=3.7,
                weight=0.3
            ),
            Component(
                name="php",
                version="7.4.3",
                release_date=date(2020, 2, 13),
                category=ComponentCategory.PROGRAMMING_LANGUAGE,
                risk_level=RiskLevel.WARNING,
                age_years=3.8,
                weight=0.7
            )
        ]
        
        mock_detection_result = ComponentDetectionResult(
            detected_components=mock_components,
            failed_detections=[],
            detection_metadata={
                'url_analyzed': 'https://example.com',
                'headers_found': 8,
                'detection_time_ms': 800,
                'analysis_type': 'website'
            }
        )
        
        mock_stack_age_result = StackAgeResult(
            effective_age=3.6,
            total_components=2,
            risk_distribution={
                RiskLevel.CRITICAL: 0,
                RiskLevel.WARNING: 2,
                RiskLevel.OK: 0
            },
            oldest_critical_component=None,
            roast_commentary="⚠️ Getting a bit long in the tooth. Time to start planning some updates!"
        )
        
        # Setup mocks
        mock_scraper.analyze_website = AsyncMock(return_value=mock_detection_result)
        mock_engine.calculate_stack_age = MagicMock(return_value=mock_stack_age_result)
        
        # Make the request
        response = client.post("/api/analyze", json={
            "url": "https://example.com",
            "analysis_type": "website"
        })
        
        # Verify the response
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert data["stack_age_result"]["effective_age"] == 3.6
        assert len(data["components"]) == 2
        
        # Check that website-specific components are detected
        component_names = [c["name"] for c in data["components"]]
        assert "nginx" in component_names
        assert "php" in component_names
        
        # Check analysis metadata
        metadata = data["analysis_metadata"]
        assert metadata["analysis_type"] == "website"
        assert metadata["url_analyzed"] == "https://example.com"
        
        # Verify mocks were called correctly
        mock_scraper.analyze_website.assert_called_once_with("https://example.com")
        mock_engine.calculate_stack_age.assert_called_once_with(mock_components)
    
    def test_cors_headers(self, client):
        """Test that CORS headers are properly configured."""
        response = client.options("/api/analyze", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        })
        
        # CORS preflight should be handled
        assert response.status_code in [200, 204]
    
    def test_api_documentation_available(self, client):
        """Test that API documentation endpoints are available."""
        # Test OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        openapi_data = response.json()
        assert "openapi" in openapi_data
        assert "info" in openapi_data
        assert openapi_data["info"]["title"] == "StackDebt Archeologist"
        
        # Check that our endpoints are documented
        paths = openapi_data["paths"]
        assert "/api/analyze" in paths
        assert "/api/components/{software_name}/versions" in paths
        assert "/api/encyclopedia/stats" in paths
        assert "/api/encyclopedia/search" in paths
    
    def test_request_validation(self, client):
        """Test that request validation works correctly."""
        # Test missing required fields
        response = client.post("/api/analyze", json={
            "url": "https://example.com"
            # Missing analysis_type
        })
        assert response.status_code == 422
        
        # Test invalid field types
        response = client.post("/api/analyze", json={
            "url": 123,  # Should be string
            "analysis_type": "website"
        })
        assert response.status_code == 422
        
        # Test empty request body
        response = client.post("/api/analyze", json={})
        assert response.status_code == 422
    
    @patch('app.main.encyclopedia')
    def test_encyclopedia_endpoints_integration(self, mock_encyclopedia, client):
        """Test encyclopedia endpoints work together."""
        # Mock search results
        mock_search_results = [
            {
                'software_name': 'python',
                'category': 'programming_language',
                'version_count': 15,
                'latest_release': date(2023, 10, 2)
            }
        ]
        mock_encyclopedia.search_software = AsyncMock(return_value=mock_search_results)
        
        # Mock stats
        mock_stats = {
            'total_versions': 500,
            'total_software': 100,
            'total_categories': 7
        }
        mock_encyclopedia.get_database_stats = AsyncMock(return_value=mock_stats)
        
        # Test search
        search_response = client.get("/api/encyclopedia/search?q=python")
        assert search_response.status_code == 200
        search_data = search_response.json()
        assert search_data["total_results"] == 1
        assert search_data["results"][0]["software_name"] == "python"
        
        # Test stats
        stats_response = client.get("/api/encyclopedia/stats")
        assert stats_response.status_code == 200
        stats_data = stats_response.json()
        assert stats_data["database_stats"]["total_versions"] == 500
        assert stats_data["status"] == "healthy"
        
        # Verify mocks were called
        mock_encyclopedia.search_software.assert_called_once_with("python", 20)
        mock_encyclopedia.get_database_stats.assert_called_once()


class TestErrorScenarios:
    """Test various error scenarios."""
    
    def test_malformed_json_request(self, client):
        """Test handling of malformed JSON requests."""
        response = client.post(
            "/api/analyze",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_unsupported_http_methods(self, client):
        """Test that unsupported HTTP methods return appropriate errors."""
        # PUT should not be supported on analyze endpoint
        response = client.put("/api/analyze", json={
            "url": "https://example.com",
            "analysis_type": "website"
        })
        assert response.status_code == 405  # Method Not Allowed
        
        # DELETE should not be supported
        response = client.delete("/api/analyze")
        assert response.status_code == 405
    
    def test_nonexistent_endpoints(self, client):
        """Test that nonexistent endpoints return 404."""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404
        
        response = client.post("/api/invalid/endpoint")
        assert response.status_code == 404