"""
Property-based tests for age calculation precision.
**Feature: stackdebt, Property 9: Age Calculation Precision**
**Validates: Requirements 3.5**
"""

import pytest
from hypothesis import given, strategies as st
from datetime import date, timedelta
from app.utils import calculate_age_years
from app.schemas import Component, ComponentCategory, RiskLevel


@given(
    release_date=st.dates(min_value=date(1990, 1, 1), max_value=date.today()),
    reference_date=st.dates(min_value=date(1990, 1, 1), max_value=date.today() + timedelta(days=365))
)
def test_property_9_age_calculation_precision(release_date, reference_date):
    """
    **Feature: stackdebt, Property 9: Age Calculation Precision**
    
    For any calculated stack age, the output should be formatted as a decimal number 
    with exactly one decimal place.
    
    **Validates: Requirements 3.5**
    """
    # Ensure reference_date is after release_date for valid age calculation
    if reference_date < release_date:
        reference_date, release_date = release_date, reference_date
    
    age_years = calculate_age_years(release_date, reference_date)
    
    # Property: Age should be formatted with exactly one decimal place
    age_str = str(age_years)
    
    # Check that the result has exactly one decimal place
    if '.' in age_str:
        decimal_part = age_str.split('.')[1]
        assert len(decimal_part) == 1, f"Age {age_years} should have exactly one decimal place, got {len(decimal_part)}"
    else:
        # If no decimal point, it should be a whole number (which is valid with .0)
        assert age_years == int(age_years), f"Age {age_years} should be a whole number if no decimal point"
    
    # Property: Age should be non-negative
    assert age_years >= 0, f"Age should be non-negative, got {age_years}"
    
    # Property: Age should be reasonable (not more than 100 years for software)
    assert age_years <= 100, f"Age should be reasonable (<= 100 years), got {age_years}"


@given(
    name=st.text(min_size=1, max_size=50),
    version=st.text(min_size=1, max_size=20),
    release_date=st.dates(min_value=date(1990, 1, 1), max_value=date.today()),
    category=st.sampled_from(ComponentCategory),
    risk_level=st.sampled_from(RiskLevel),
    age_years=st.floats(min_value=0, max_value=50, allow_nan=False, allow_infinity=False),
    weight=st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False)
)
def test_property_9_component_age_precision_validation(name, version, release_date, category, risk_level, age_years, weight):
    """
    **Feature: stackdebt, Property 9: Age Calculation Precision**
    
    For any Component model with age_years field, the age should be rounded to 
    exactly one decimal place during validation.
    
    **Validates: Requirements 3.5**
    """
    component = Component(
        name=name,
        version=version,
        release_date=release_date,
        category=category,
        risk_level=risk_level,
        age_years=age_years,
        weight=weight
    )
    
    # Property: Component age_years should have exactly one decimal place precision
    age_str = str(component.age_years)
    if '.' in age_str:
        decimal_part = age_str.split('.')[1]
        assert len(decimal_part) == 1, f"Component age {component.age_years} should have exactly one decimal place"
    
    # Property: The rounded age should be close to the original (within rounding tolerance)
    assert abs(component.age_years - round(age_years, 1)) < 0.001, f"Age should be rounded to 1 decimal place"


@given(
    effective_age=st.floats(min_value=0, max_value=50, allow_nan=False, allow_infinity=False),
    total_components=st.integers(min_value=0, max_value=100),
    roast_commentary=st.text(min_size=1, max_size=200)
)
def test_property_9_stack_age_result_precision_validation(effective_age, total_components, roast_commentary):
    """
    **Feature: stackdebt, Property 9: Age Calculation Precision**
    
    For any StackAgeResult with effective_age field, the age should be rounded to 
    exactly one decimal place during validation.
    
    **Validates: Requirements 3.5**
    """
    from app.schemas import StackAgeResult, RiskLevel
    
    stack_age_result = StackAgeResult(
        effective_age=effective_age,
        total_components=total_components,
        risk_distribution={RiskLevel.OK: total_components},
        roast_commentary=roast_commentary
    )
    
    # Property: StackAgeResult effective_age should have exactly one decimal place precision
    age_str = str(stack_age_result.effective_age)
    if '.' in age_str:
        decimal_part = age_str.split('.')[1]
        assert len(decimal_part) == 1, f"Effective age {stack_age_result.effective_age} should have exactly one decimal place"
    
    # Property: The rounded age should be close to the original (within rounding tolerance)
    assert abs(stack_age_result.effective_age - round(effective_age, 1)) < 0.001, f"Effective age should be rounded to 1 decimal place"


# Additional edge case tests for precision
def test_age_calculation_precision_edge_cases():
    """Test edge cases for age calculation precision."""
    
    # Test very small age differences
    release_date = date(2023, 12, 31)
    reference_date = date(2024, 1, 1)  # 1 day difference
    age = calculate_age_years(release_date, reference_date)
    assert age == 0.0, f"Very small age should be 0.0, got {age}"
    
    # Test exact year boundaries
    release_date = date(2020, 1, 1)
    reference_date = date(2023, 1, 1)  # Exactly 3 years
    age = calculate_age_years(release_date, reference_date)
    assert age == 3.0, f"Exact year boundary should be 3.0, got {age}"
    
    # Test leap year handling
    release_date = date(2020, 2, 29)  # Leap year
    reference_date = date(2021, 2, 28)  # Non-leap year
    age = calculate_age_years(release_date, reference_date)
    assert isinstance(age, float), f"Age should be float, got {type(age)}"
    assert age >= 0.9 and age <= 1.1, f"Leap year age should be around 1.0, got {age}"