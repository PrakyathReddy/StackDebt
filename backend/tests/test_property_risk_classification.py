"""
Property-based tests for risk classification system.
**Feature: stackdebt, Property 10: Risk Classification System**
**Validates: Requirements 4.1, 4.2, 4.3**
"""

import pytest
from hypothesis import given, strategies as st
from datetime import date, timedelta
from app.utils import determine_risk_level
from app.schemas import RiskLevel


@given(
    age_years=st.floats(min_value=0, max_value=20, allow_nan=False, allow_infinity=False)
)
def test_property_10_risk_classification_by_age(age_years):
    """
    **Feature: stackdebt, Property 10: Risk Classification System**
    
    For any component with a known release date, its risk level should be Critical 
    if >5 years old or past EOL, Warning if 2-5 years old, and OK if <2 years old.
    
    **Validates: Requirements 4.1, 4.2, 4.3**
    """
    risk_level = determine_risk_level(age_years)
    
    # Property: Risk classification based on age boundaries
    if age_years > 5.0:
        assert risk_level == RiskLevel.CRITICAL, f"Component aged {age_years} years should be CRITICAL, got {risk_level}"
    elif age_years >= 2.0:
        assert risk_level == RiskLevel.WARNING, f"Component aged {age_years} years should be WARNING, got {risk_level}"
    else:
        assert risk_level == RiskLevel.OK, f"Component aged {age_years} years should be OK, got {risk_level}"


@given(
    age_years=st.floats(min_value=0, max_value=10, allow_nan=False, allow_infinity=False),
    days_past_eol=st.integers(min_value=1, max_value=365)
)
def test_property_10_risk_classification_past_eol(age_years, days_past_eol):
    """
    **Feature: stackdebt, Property 10: Risk Classification System**
    
    For any component that is past its end-of-life date, it should be classified 
    as CRITICAL regardless of age.
    
    **Validates: Requirements 4.1**
    """
    # Create an EOL date in the past
    eol_date = date.today() - timedelta(days=days_past_eol)
    
    risk_level = determine_risk_level(age_years, eol_date)
    
    # Property: Any component past EOL should be CRITICAL
    assert risk_level == RiskLevel.CRITICAL, f"Component past EOL should be CRITICAL, got {risk_level}"


@given(
    age_years=st.floats(min_value=0, max_value=10, allow_nan=False, allow_infinity=False),
    days_until_eol=st.integers(min_value=1, max_value=365)
)
def test_property_10_risk_classification_future_eol(age_years, days_until_eol):
    """
    **Feature: stackdebt, Property 10: Risk Classification System**
    
    For any component with a future EOL date, risk should be based on age only.
    
    **Validates: Requirements 4.1, 4.2, 4.3**
    """
    # Create an EOL date in the future
    eol_date = date.today() + timedelta(days=days_until_eol)
    
    risk_level = determine_risk_level(age_years, eol_date)
    
    # Property: Risk classification should be based on age when EOL is in future
    if age_years > 5.0:
        assert risk_level == RiskLevel.CRITICAL, f"Old component with future EOL should be CRITICAL, got {risk_level}"
    elif age_years >= 2.0:
        assert risk_level == RiskLevel.WARNING, f"Medium-age component with future EOL should be WARNING, got {risk_level}"
    else:
        assert risk_level == RiskLevel.OK, f"New component with future EOL should be OK, got {risk_level}"


def test_risk_classification_boundary_conditions():
    """Test exact boundary conditions for risk classification."""
    
    # Test exact boundaries
    assert determine_risk_level(1.9) == RiskLevel.OK, "1.9 years should be OK"
    assert determine_risk_level(2.0) == RiskLevel.WARNING, "2.0 years should be WARNING"
    assert determine_risk_level(4.9) == RiskLevel.WARNING, "4.9 years should be WARNING"
    assert determine_risk_level(5.0) == RiskLevel.WARNING, "5.0 years should be WARNING"
    assert determine_risk_level(5.1) == RiskLevel.CRITICAL, "5.1 years should be CRITICAL"
    
    # Test zero age
    assert determine_risk_level(0.0) == RiskLevel.OK, "0.0 years should be OK"
    
    # Test very old components
    assert determine_risk_level(10.0) == RiskLevel.CRITICAL, "10.0 years should be CRITICAL"
    assert determine_risk_level(20.0) == RiskLevel.CRITICAL, "20.0 years should be CRITICAL"


def test_risk_classification_eol_edge_cases():
    """Test edge cases for EOL-based risk classification."""
    
    # Test EOL exactly today
    today = date.today()
    assert determine_risk_level(1.0, today) == RiskLevel.OK, "Component with EOL today should be OK (not past EOL yet)"
    
    # Test EOL yesterday
    yesterday = today - timedelta(days=1)
    assert determine_risk_level(1.0, yesterday) == RiskLevel.CRITICAL, "Component with EOL yesterday should be CRITICAL"
    
    # Test very young component past EOL
    assert determine_risk_level(0.1, yesterday) == RiskLevel.CRITICAL, "Even very young component past EOL should be CRITICAL"
    
    # Test old component with future EOL
    future_eol = today + timedelta(days=365)
    assert determine_risk_level(6.0, future_eol) == RiskLevel.CRITICAL, "Old component with future EOL should still be CRITICAL based on age"


@given(
    age_years=st.floats(min_value=0, max_value=20, allow_nan=False, allow_infinity=False)
)
def test_property_10_risk_level_consistency(age_years):
    """
    **Feature: stackdebt, Property 10: Risk Classification System**
    
    For any given age, the risk classification should be consistent and deterministic.
    
    **Validates: Requirements 4.1, 4.2, 4.3**
    """
    # Call the function multiple times with the same input
    risk1 = determine_risk_level(age_years)
    risk2 = determine_risk_level(age_years)
    risk3 = determine_risk_level(age_years)
    
    # Property: Risk classification should be deterministic
    assert risk1 == risk2 == risk3, f"Risk classification should be consistent for age {age_years}"
    
    # Property: Risk level should be one of the valid enum values
    assert risk1 in [RiskLevel.CRITICAL, RiskLevel.WARNING, RiskLevel.OK], f"Risk level should be valid enum value, got {risk1}"


@given(
    age_years_1=st.floats(min_value=0, max_value=1.9, allow_nan=False, allow_infinity=False),
    age_years_2=st.floats(min_value=2.0, max_value=5.0, allow_nan=False, allow_infinity=False),
    age_years_3=st.floats(min_value=5.1, max_value=20, allow_nan=False, allow_infinity=False)
)
def test_property_10_risk_level_ordering(age_years_1, age_years_2, age_years_3):
    """
    **Feature: stackdebt, Property 10: Risk Classification System**
    
    Risk levels should follow a logical ordering: newer components are less risky.
    
    **Validates: Requirements 4.1, 4.2, 4.3**
    """
    risk_ok = determine_risk_level(age_years_1)      # Should be OK
    risk_warning = determine_risk_level(age_years_2)  # Should be WARNING
    risk_critical = determine_risk_level(age_years_3) # Should be CRITICAL
    
    # Property: Risk levels should follow expected ordering
    assert risk_ok == RiskLevel.OK, f"Young component ({age_years_1} years) should be OK"
    assert risk_warning == RiskLevel.WARNING, f"Medium-age component ({age_years_2} years) should be WARNING"
    assert risk_critical == RiskLevel.CRITICAL, f"Old component ({age_years_3} years) should be CRITICAL"
    
    # Property: Risk severity increases with age (in terms of enum ordering)
    risk_values = {RiskLevel.OK: 0, RiskLevel.WARNING: 1, RiskLevel.CRITICAL: 2}
    assert risk_values[risk_ok] < risk_values[risk_warning] < risk_values[risk_critical], \
        "Risk severity should increase with component age"