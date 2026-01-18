"""
Unit tests for Pydantic schemas and data validation.
"""

import pytest
from datetime import date, datetime
from pydantic import ValidationError
from app.schemas import (
    Component, StackAgeResult, AnalysisRequest, AnalysisResponse,
    ComponentCategory, RiskLevel, RiskSummary, ComponentDetectionResult
)


class TestComponentCategory:
    """Test ComponentCategory enum."""
    
    def test_all_categories_exist(self):
        """Test that all required categories are defined."""
        expected_categories = {
            "operating_system",
            "programming_language", 
            "database",
            "web_server",
            "framework",
            "library",
            "development_tool"
        }
        actual_categories = {cat.value for cat in ComponentCategory}
        assert actual_categories == expected_categories


class TestRiskLevel:
    """Test RiskLevel enum."""
    
    def test_all_risk_levels_exist(self):
        """Test that all required risk levels are defined."""
        expected_levels = {"critical", "warning", "ok"}
        actual_levels = {level.value for level in RiskLevel}
        assert actual_levels == expected_levels


class TestComponent:
    """Test Component model validation."""
    
    def test_valid_component_creation(self):
        """Test creating a valid component."""
        component = Component(
            name="Python",
            version="3.9.0",
            release_date=date(2020, 10, 5),
            end_of_life_date=date(2025, 10, 5),
            category=ComponentCategory.PROGRAMMING_LANGUAGE,
            risk_level=RiskLevel.WARNING,
            age_years=3.2,
            weight=0.7
        )
        
        assert component.name == "Python"
        assert component.version == "3.9.0"
        assert component.category == ComponentCategory.PROGRAMMING_LANGUAGE
        assert component.risk_level == RiskLevel.WARNING
        assert component.age_years == 3.2
        assert component.weight == 0.7
    
    def test_age_years_precision_validation(self):
        """Test that age_years is rounded to one decimal place."""
        component = Component(
            name="Python",
            version="3.9.0",
            release_date=date(2020, 10, 5),
            category=ComponentCategory.PROGRAMMING_LANGUAGE,
            risk_level=RiskLevel.WARNING,
            age_years=3.23456,  # Should be rounded to 3.2
            weight=0.7
        )
        
        assert component.age_years == 3.2
    
    def test_negative_age_validation(self):
        """Test that negative age is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Component(
                name="Python",
                version="3.9.0",
                release_date=date(2020, 10, 5),
                category=ComponentCategory.PROGRAMMING_LANGUAGE,
                risk_level=RiskLevel.WARNING,
                age_years=-1.0,
                weight=0.7
            )
        
        assert "Input should be greater than or equal to 0" in str(exc_info.value)
    
    def test_weight_bounds_validation(self):
        """Test that weight is bounded between 0 and 1."""
        # Test weight > 1
        with pytest.raises(ValidationError):
            Component(
                name="Python",
                version="3.9.0",
                release_date=date(2020, 10, 5),
                category=ComponentCategory.PROGRAMMING_LANGUAGE,
                risk_level=RiskLevel.WARNING,
                age_years=3.2,
                weight=1.5
            )
        
        # Test weight < 0
        with pytest.raises(ValidationError):
            Component(
                name="Python",
                version="3.9.0",
                release_date=date(2020, 10, 5),
                category=ComponentCategory.PROGRAMMING_LANGUAGE,
                risk_level=RiskLevel.WARNING,
                age_years=3.2,
                weight=-0.1
            )


class TestStackAgeResult:
    """Test StackAgeResult model validation."""
    
    def test_valid_stack_age_result(self):
        """Test creating a valid stack age result."""
        result = StackAgeResult(
            effective_age=3.2,
            total_components=5,
            risk_distribution={
                RiskLevel.CRITICAL: 1,
                RiskLevel.WARNING: 2,
                RiskLevel.OK: 2
            },
            roast_commentary="Your stack is showing its age!"
        )
        
        assert result.effective_age == 3.2
        assert result.total_components == 5
        assert result.risk_distribution[RiskLevel.CRITICAL] == 1
        assert result.roast_commentary == "Your stack is showing its age!"
    
    def test_effective_age_precision_validation(self):
        """Test that effective_age is rounded to one decimal place."""
        result = StackAgeResult(
            effective_age=3.23456,  # Should be rounded to 3.2
            total_components=5,
            risk_distribution={RiskLevel.OK: 5},
            roast_commentary="Test"
        )
        
        assert result.effective_age == 3.2
    
    def test_negative_values_validation(self):
        """Test that negative values are rejected."""
        with pytest.raises(ValidationError):
            StackAgeResult(
                effective_age=-1.0,
                total_components=5,
                risk_distribution={RiskLevel.OK: 5},
                roast_commentary="Test"
            )
        
        with pytest.raises(ValidationError):
            StackAgeResult(
                effective_age=3.2,
                total_components=-1,
                risk_distribution={RiskLevel.OK: 5},
                roast_commentary="Test"
            )


class TestAnalysisRequest:
    """Test AnalysisRequest model validation."""
    
    def test_valid_website_request(self):
        """Test creating a valid website analysis request."""
        request = AnalysisRequest(
            url="https://example.com",
            analysis_type="website"
        )
        
        assert request.url == "https://example.com"
        assert request.analysis_type == "website"
    
    def test_valid_github_request(self):
        """Test creating a valid GitHub analysis request."""
        request = AnalysisRequest(
            url="https://github.com/user/repo",
            analysis_type="github"
        )
        
        assert request.url == "https://github.com/user/repo"
        assert request.analysis_type == "github"
    
    def test_invalid_analysis_type(self):
        """Test that invalid analysis types are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            AnalysisRequest(
                url="https://example.com",
                analysis_type="invalid"
            )
        
        assert "analysis_type must be 'website' or 'github'" in str(exc_info.value)
    
    def test_invalid_url_format(self):
        """Test that invalid URL formats are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            AnalysisRequest(
                url="not-a-url",
                analysis_type="website"
            )
        
        assert "URL must start with http:// or https://" in str(exc_info.value)


class TestAnalysisResponse:
    """Test AnalysisResponse model validation."""
    
    def test_valid_analysis_response(self):
        """Test creating a valid analysis response."""
        stack_age_result = StackAgeResult(
            effective_age=3.2,
            total_components=1,
            risk_distribution={RiskLevel.WARNING: 1},
            roast_commentary="Test commentary"
        )
        
        component = Component(
            name="Python",
            version="3.9.0",
            release_date=date(2020, 10, 5),
            category=ComponentCategory.PROGRAMMING_LANGUAGE,
            risk_level=RiskLevel.WARNING,
            age_years=3.2,
            weight=0.7
        )
        
        response = AnalysisResponse(
            stack_age_result=stack_age_result,
            components=[component],
            analysis_metadata={"test": "data"},
            generated_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        assert response.stack_age_result.effective_age == 3.2
        assert len(response.components) == 1
        assert response.components[0].name == "Python"
        assert response.analysis_metadata["test"] == "data"
        assert response.generated_at == datetime(2024, 1, 1, 12, 0, 0)
    
    def test_default_values(self):
        """Test that default values are set correctly."""
        stack_age_result = StackAgeResult(
            effective_age=3.2,
            total_components=0,
            risk_distribution={},
            roast_commentary="Test"
        )
        
        response = AnalysisResponse(
            stack_age_result=stack_age_result,
            components=[]
        )
        
        assert response.analysis_metadata == {}
        assert isinstance(response.generated_at, datetime)


class TestRiskSummary:
    """Test RiskSummary utility model."""
    
    def test_total_count_calculation(self):
        """Test that total_count is calculated correctly."""
        summary = RiskSummary(
            critical_count=2,
            warning_count=3,
            ok_count=5
        )
        
        assert summary.total_count == 10
    
    def test_total_count_override(self):
        """Test that incorrect total_count is corrected."""
        summary = RiskSummary(
            critical_count=2,
            warning_count=3,
            ok_count=5,
            total_count=999  # Should be corrected to 10
        )
        
        assert summary.total_count == 10


class TestComponentDetectionResult:
    """Test ComponentDetectionResult utility model."""
    
    def test_empty_detection_result(self):
        """Test creating an empty detection result."""
        result = ComponentDetectionResult()
        
        assert result.detected_components == []
        assert result.failed_detections == []
        assert result.detection_metadata == {}
    
    def test_detection_result_with_data(self):
        """Test creating a detection result with data."""
        component = Component(
            name="Python",
            version="3.9.0",
            release_date=date(2020, 10, 5),
            category=ComponentCategory.PROGRAMMING_LANGUAGE,
            risk_level=RiskLevel.WARNING,
            age_years=3.2,
            weight=0.7
        )
        
        result = ComponentDetectionResult(
            detected_components=[component],
            failed_detections=["unknown-package"],
            detection_metadata={"files_analyzed": 3}
        )
        
        assert len(result.detected_components) == 1
        assert result.detected_components[0].name == "Python"
        assert result.failed_detections == ["unknown-package"]
        assert result.detection_metadata["files_analyzed"] == 3