"""
Tests for the main FastAPI application endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
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


@pytest.fixture
def mock_components():
    """Create mock components for testing."""
    return [
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


@pytest.fixture
def mock_detection_result(mock_components):
    """Create mock detection result."""
    return ComponentDetectionResult(
        detected_components=mock_components,
        failed_detections=[],
        detection_metadata={
            'analysis_type': 'github',
            'files_analyzed': 3,
            'detection_time_ms': 500
        }
    )


@pytest.fixture
def mock_stack_age_result(mock_components):
    """Create mock stack age result."""
    return StackAgeResult(
        effective_age=3.4,
        total_components=2,
        risk_distribution={
            RiskLevel.CRITICAL: 0,
            RiskLevel.WARNING: 2,
            RiskLevel.OK: 0
        },
        oldest_critical_component=None,
        roast_commentary="Your stack is showing its age. Some components are getting creaky!"
    )


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_root_endpoint(self, client):
        """Test the root endpoint returns correct message."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "StackDebt Archeologist is running"}
    
    def test_health_endpoint(self, client):
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "archeologist"


class TestAnalysisEndpoint:
    """Test the main analysis endpoint."""
    
    @patch('app.main.github_analyzer')
    @patch('app.main.carbon_dating_engine')
    def test_analyze_github_repository_success(self, mock_engine, mock_analyzer, 
                                             client, mock_detection_result, mock_stack_age_result):
        """Test successful GitHub repository analysis."""
        # Setup mocks
        mock_analyzer.analyze_repository = AsyncMock(return_value=mock_detection_result)
        mock_engine.calculate_stack_age = MagicMock(return_value=mock_stack_age_result)
        
        # Make request
        response = client.post("/api/analyze", json={
            "url": "https://github.com/user/repo",
            "analysis_type": "github"
        })
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert "stack_age_result" in data
        assert "components" in data
        assert "analysis_metadata" in data
        assert "generated_at" in data
        
        assert data["stack_age_result"]["effective_age"] == 3.4
        assert data["stack_age_result"]["total_components"] == 2
        assert len(data["components"]) == 2
        
        # Verify mocks were called
        mock_analyzer.analyze_repository.assert_called_once_with("https://github.com/user/repo")
        mock_engine.calculate_stack_age.assert_called_once()
    
    @patch('app.main.http_scraper')
    @patch('app.main.carbon_dating_engine')
    def test_analyze_website_success(self, mock_engine, mock_scraper, 
                                   client, mock_detection_result, mock_stack_age_result):
        """Test successful website analysis."""
        # Setup mocks
        mock_scraper.analyze_website = AsyncMock(return_value=mock_detection_result)
        mock_engine.calculate_stack_age = MagicMock(return_value=mock_stack_age_result)
        
        # Make request
        response = client.post("/api/analyze", json={
            "url": "https://example.com",
            "analysis_type": "website"
        })
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["stack_age_result"]["effective_age"] == 3.4
        assert len(data["components"]) == 2
        
        # Verify mocks were called
        mock_scraper.analyze_website.assert_called_once_with("https://example.com")
        mock_engine.calculate_stack_age.assert_called_once()
    
    def test_analyze_invalid_url_format(self, client):
        """Test analysis with invalid URL format."""
        response = client.post("/api/analyze", json={
            "url": "invalid-url",
            "analysis_type": "website"
        })
        
        assert response.status_code == 422  # Pydantic validation error
        assert "URL must start with http://" in str(response.json())
    
    def test_analyze_invalid_analysis_type(self, client):
        """Test analysis with invalid analysis type."""
        response = client.post("/api/analyze", json={
            "url": "https://example.com",
            "analysis_type": "invalid"
        })
        
        assert response.status_code == 422  # Pydantic validation error
        assert "analysis_type must be" in str(response.json())
    
    @patch('app.main.github_analyzer')
    def test_analyze_no_components_detected(self, mock_analyzer, client):
        """Test analysis when no components are detected."""
        # Setup mock to return empty result
        empty_result = ComponentDetectionResult(
            detected_components=[],
            failed_detections=["some-package@1.0.0: not found"],
            detection_metadata={}
        )
        mock_analyzer.analyze_repository = AsyncMock(return_value=empty_result)
        
        response = client.post("/api/analyze", json={
            "url": "https://github.com/user/empty-repo",
            "analysis_type": "github"
        })
        
        assert response.status_code == 422
        data = response.json()
        assert "No software components detected" in data["detail"]["message"]
        assert "suggestions" in data["detail"]
        assert "failed_detections" in data["detail"]
    
    @patch('app.main.github_analyzer')
    @patch('app.main.carbon_dating_engine')
    def test_analyze_carbon_dating_error(self, mock_engine, mock_analyzer, 
                                       client, mock_detection_result):
        """Test analysis when carbon dating calculation fails."""
        # Setup mocks
        mock_analyzer.analyze_repository = AsyncMock(return_value=mock_detection_result)
        mock_engine.calculate_stack_age = MagicMock(side_effect=ValueError("No valid components"))
        
        response = client.post("/api/analyze", json={
            "url": "https://github.com/user/repo",
            "analysis_type": "github"
        })
        
        assert response.status_code == 422
        data = response.json()
        assert "Unable to calculate stack age" in data["detail"]["message"]


class TestComponentVersionsEndpoint:
    """Test the component versions endpoint."""
    
    @patch('app.main.encyclopedia')
    def test_get_software_versions_success(self, mock_encyclopedia, client):
        """Test successful retrieval of software versions."""
        # Mock version releases
        from app.models import VersionRelease, ComponentCategory
        
        mock_versions = [
            VersionRelease(
                id=1,
                software_name="python",
                version="3.9.0",
                release_date=date(2020, 10, 5),
                end_of_life_date=None,
                category=ComponentCategory.PROGRAMMING_LANGUAGE,
                is_lts=False,
                created_at=None,
                updated_at=None
            ),
            VersionRelease(
                id=2,
                software_name="python",
                version="3.8.0",
                release_date=date(2019, 10, 14),
                end_of_life_date=None,
                category=ComponentCategory.PROGRAMMING_LANGUAGE,
                is_lts=False,
                created_at=None,
                updated_at=None
            )
        ]
        
        mock_encyclopedia.get_software_versions = AsyncMock(return_value=mock_versions)
        
        response = client.get("/api/components/python/versions")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["software_name"] == "python"
        assert data["total_versions"] == 2
        assert len(data["versions"]) == 2
        
        # Check version data structure
        version_data = data["versions"][0]
        assert "version" in version_data
        assert "release_date" in version_data
        assert "category" in version_data
        assert "risk_level" in version_data
        assert "age_years" in version_data
        
        mock_encyclopedia.get_software_versions.assert_called_once_with("python", 50)
    
    @patch('app.main.encyclopedia')
    def test_get_software_versions_not_found(self, mock_encyclopedia, client):
        """Test retrieval of versions for non-existent software."""
        mock_encyclopedia.get_software_versions = AsyncMock(return_value=[])
        
        response = client.get("/api/components/nonexistent/versions")
        
        assert response.status_code == 404
        data = response.json()
        assert "No versions found" in data["detail"]["message"]
        assert "suggestions" in data["detail"]
    
    @patch('app.main.encyclopedia')
    def test_get_software_versions_with_limit(self, mock_encyclopedia, client):
        """Test retrieval of versions with custom limit."""
        mock_encyclopedia.get_software_versions = AsyncMock(return_value=[])
        
        response = client.get("/api/components/python/versions?limit=10")
        
        mock_encyclopedia.get_software_versions.assert_called_once_with("python", 10)


class TestEncyclopediaEndpoints:
    """Test encyclopedia-related endpoints."""
    
    @patch('app.main.encyclopedia')
    def test_get_encyclopedia_stats(self, mock_encyclopedia, client):
        """Test retrieval of encyclopedia statistics."""
        mock_stats = {
            'total_versions': 1000,
            'total_software': 200,
            'total_categories': 7,
            'versions_by_category': {
                'programming_language': 300,
                'web_server': 100,
                'database': 150
            }
        }
        
        mock_encyclopedia.get_database_stats = AsyncMock(return_value=mock_stats)
        
        response = client.get("/api/encyclopedia/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "database_stats" in data
        assert data["status"] == "healthy"
        assert data["database_stats"]["total_versions"] == 1000
    
    @patch('app.main.encyclopedia')
    def test_search_software_success(self, mock_encyclopedia, client):
        """Test successful software search."""
        mock_results = [
            {
                'software_name': 'python',
                'category': 'programming_language',
                'version_count': 10,
                'latest_release': date(2023, 10, 2)
            },
            {
                'software_name': 'python-requests',
                'category': 'library',
                'version_count': 5,
                'latest_release': date(2023, 5, 15)
            }
        ]
        
        mock_encyclopedia.search_software = AsyncMock(return_value=mock_results)
        
        response = client.get("/api/encyclopedia/search?q=python")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["query"] == "python"
        assert data["total_results"] == 2
        assert len(data["results"]) == 2
        
        mock_encyclopedia.search_software.assert_called_once_with("python", 20)
    
    def test_search_software_short_query(self, client):
        """Test search with query that's too short."""
        response = client.get("/api/encyclopedia/search?q=p")
        
        assert response.status_code == 400
        assert "at least 2 characters" in response.json()["detail"]
    
    def test_search_software_empty_query(self, client):
        """Test search with empty query."""
        response = client.get("/api/encyclopedia/search?q=")
        
        assert response.status_code == 400
        assert "at least 2 characters" in response.json()["detail"]


class TestErrorHandling:
    """Test error handling scenarios."""
    
    @patch('app.main.github_analyzer')
    def test_network_error_handling(self, mock_analyzer, client):
        """Test handling of network errors."""
        import httpx
        mock_analyzer.analyze_repository = AsyncMock(
            side_effect=httpx.RequestError("Connection failed")
        )
        
        response = client.post("/api/analyze", json={
            "url": "https://github.com/user/repo",
            "analysis_type": "github"
        })
        
        assert response.status_code == 503
        data = response.json()
        assert "Unable to access the provided URL" in data["detail"]["message"]
        assert "suggestions" in data["detail"]
    
    @patch('app.main.github_analyzer')
    def test_http_404_error_handling(self, mock_analyzer, client):
        """Test handling of HTTP 404 errors."""
        import httpx
        
        # Create a mock response for 404
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        mock_analyzer.analyze_repository = AsyncMock(
            side_effect=httpx.HTTPStatusError("Not found", request=None, response=mock_response)
        )
        
        response = client.post("/api/analyze", json={
            "url": "https://github.com/user/nonexistent",
            "analysis_type": "github"
        })
        
        assert response.status_code == 404
        data = response.json()
        assert "Repository not found" in data["detail"]["message"]
        assert "suggestions" in data["detail"]
    
    @patch('app.main.github_analyzer')
    def test_http_403_error_handling(self, mock_analyzer, client):
        """Test handling of HTTP 403 errors."""
        import httpx
        
        # Create a mock response for 403
        mock_response = MagicMock()
        mock_response.status_code = 403
        
        mock_analyzer.analyze_repository = AsyncMock(
            side_effect=httpx.HTTPStatusError("Forbidden", request=None, response=mock_response)
        )
        
        response = client.post("/api/analyze", json={
            "url": "https://github.com/user/private-repo",
            "analysis_type": "github"
        })
        
        assert response.status_code == 403
        data = response.json()
        assert "Access forbidden" in data["detail"]["message"]
        assert "suggestions" in data["detail"]