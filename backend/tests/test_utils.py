"""
Unit tests for utility functions.
"""

import pytest
from datetime import date
from app.utils import (
    calculate_age_years, determine_risk_level, get_component_weight,
    validate_url_format, format_roast_commentary, calculate_risk_multiplier
)
from app.schemas import ComponentCategory, RiskLevel, Component


class TestCalculateAgeYears:
    """Test age calculation function."""
    
    def test_age_calculation_basic(self):
        """Test basic age calculation."""
        release_date = date(2020, 1, 1)
        reference_date = date(2023, 1, 1)
        
        age = calculate_age_years(release_date, reference_date)
        assert age == 3.0
    
    def test_age_calculation_with_months(self):
        """Test age calculation with partial years."""
        release_date = date(2020, 1, 1)
        reference_date = date(2023, 7, 1)  # 3.5 years later
        
        age = calculate_age_years(release_date, reference_date)
        assert abs(age - 3.5) < 0.1  # Allow for small rounding differences
    
    def test_age_calculation_precision(self):
        """Test that age is rounded to one decimal place."""
        release_date = date(2020, 1, 1)
        reference_date = date(2023, 4, 15)  # ~3.29 years
        
        age = calculate_age_years(release_date, reference_date)
        assert len(str(age).split('.')[1]) == 1  # One decimal place
    
    def test_age_calculation_default_reference_date(self):
        """Test age calculation with default reference date (today)."""
        release_date = date(2020, 1, 1)
        
        age = calculate_age_years(release_date)
        assert age >= 0  # Should be positive
        assert isinstance(age, float)


class TestDetermineRiskLevel:
    """Test risk level determination."""
    
    def test_critical_risk_old_component(self):
        """Test critical risk for old components."""
        risk = determine_risk_level(6.0)
        assert risk == RiskLevel.CRITICAL
    
    def test_critical_risk_eol_component(self):
        """Test critical risk for end-of-life components."""
        yesterday = date.today().replace(day=date.today().day - 1)
        risk = determine_risk_level(1.0, end_of_life_date=yesterday)
        assert risk == RiskLevel.CRITICAL
    
    def test_warning_risk_medium_age(self):
        """Test warning risk for medium age components."""
        risk = determine_risk_level(3.0)
        assert risk == RiskLevel.WARNING
    
    def test_warning_risk_boundary(self):
        """Test warning risk at boundaries."""
        risk_2_years = determine_risk_level(2.0)
        risk_5_years = determine_risk_level(5.0)
        
        assert risk_2_years == RiskLevel.WARNING
        assert risk_5_years == RiskLevel.WARNING
    
    def test_ok_risk_new_component(self):
        """Test OK risk for new components."""
        risk = determine_risk_level(1.0)
        assert risk == RiskLevel.OK
    
    def test_ok_risk_very_new(self):
        """Test OK risk for very new components."""
        risk = determine_risk_level(0.1)
        assert risk == RiskLevel.OK


class TestGetComponentWeight:
    """Test component weight calculation."""
    
    def test_critical_component_weights(self):
        """Test weights for critical components."""
        os_weight = get_component_weight(ComponentCategory.OPERATING_SYSTEM)
        lang_weight = get_component_weight(ComponentCategory.PROGRAMMING_LANGUAGE)
        db_weight = get_component_weight(ComponentCategory.DATABASE)
        
        assert os_weight == 0.7
        assert lang_weight == 0.7
        assert db_weight == 0.7
    
    def test_important_component_weights(self):
        """Test weights for important components."""
        server_weight = get_component_weight(ComponentCategory.WEB_SERVER)
        framework_weight = get_component_weight(ComponentCategory.FRAMEWORK)
        
        assert server_weight == 0.3
        assert framework_weight == 0.3
    
    def test_minor_component_weights(self):
        """Test weights for minor components."""
        library_weight = get_component_weight(ComponentCategory.LIBRARY)
        tool_weight = get_component_weight(ComponentCategory.DEVELOPMENT_TOOL)
        
        assert library_weight == 0.1
        assert tool_weight == 0.1


class TestValidateUrlFormat:
    """Test URL validation function."""
    
    def test_valid_website_url(self):
        """Test validation of website URLs."""
        is_valid, analysis_type = validate_url_format("https://example.com")
        assert is_valid is True
        assert analysis_type == "website"
    
    def test_valid_github_url(self):
        """Test validation of GitHub URLs."""
        is_valid, analysis_type = validate_url_format("https://github.com/user/repo")
        assert is_valid is True
        assert analysis_type == "github"
    
    def test_github_url_case_insensitive(self):
        """Test GitHub URL detection is case insensitive."""
        is_valid, analysis_type = validate_url_format("https://GITHUB.COM/user/repo")
        assert is_valid is True
        assert analysis_type == "github"
    
    def test_invalid_url_no_protocol(self):
        """Test invalid URL without protocol."""
        is_valid, error_msg = validate_url_format("example.com")
        assert is_valid is False
        assert "must start with http://" in error_msg
    
    def test_empty_url(self):
        """Test empty URL validation."""
        is_valid, error_msg = validate_url_format("")
        assert is_valid is False
        assert "cannot be empty" in error_msg
    
    def test_http_url(self):
        """Test HTTP URLs are accepted."""
        is_valid, analysis_type = validate_url_format("http://example.com")
        assert is_valid is True
        assert analysis_type == "website"


class TestFormatRoastCommentary:
    """Test roast commentary generation."""
    
    def test_very_new_stack(self):
        """Test commentary for very new stacks."""
        commentary = format_roast_commentary(0.5)
        assert "Fresh as morning dew" in commentary
        assert "🚀" in commentary
    
    def test_modern_stack(self):
        """Test commentary for modern stacks."""
        commentary = format_roast_commentary(1.5)
        assert "Pretty modern" in commentary
        assert "✨" in commentary
    
    def test_aging_stack(self):
        """Test commentary for aging stacks."""
        commentary = format_roast_commentary(2.5)
        assert "long in the tooth" in commentary
        assert "⚠️" in commentary
    
    def test_old_stack(self):
        """Test commentary for old stacks."""
        commentary = format_roast_commentary(4.0)
        assert "showing its age" in commentary
        assert "🦴" in commentary
    
    def test_ancient_stack(self):
        """Test commentary for ancient stacks."""
        commentary = format_roast_commentary(6.0)
        assert "Ancient" in commentary
        assert "💀" in commentary
        assert "6.0 years old" in commentary
    
    def test_ancient_stack_with_oldest_component(self):
        """Test commentary for ancient stacks with oldest component info."""
        oldest_component = Component(
            name="Python",
            version="2.7.0",
            release_date=date(2010, 7, 3),
            category=ComponentCategory.PROGRAMMING_LANGUAGE,
            risk_level=RiskLevel.CRITICAL,
            age_years=13.0,
            weight=0.7
        )
        
        commentary = format_roast_commentary(6.0, oldest_component)
        assert "Ancient" in commentary
        assert "Python 2.7.0" in commentary
        assert "archaeological" in commentary


class TestCalculateRiskMultiplier:
    """Test risk multiplier calculation."""
    
    def test_critical_risk_multiplier(self):
        """Test multiplier for critical risk."""
        multiplier = calculate_risk_multiplier(RiskLevel.CRITICAL)
        assert multiplier == 2.0
    
    def test_warning_risk_multiplier(self):
        """Test multiplier for warning risk."""
        multiplier = calculate_risk_multiplier(RiskLevel.WARNING)
        assert multiplier == 1.5
    
    def test_ok_risk_multiplier(self):
        """Test multiplier for OK risk."""
        multiplier = calculate_risk_multiplier(RiskLevel.OK)
        assert multiplier == 1.0