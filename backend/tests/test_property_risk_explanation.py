"""
Property-based tests for risk classification explanation.
**Feature: stackdebt, Property 11: Risk Classification Explanation**
**Validates: Requirements 4.5**
"""

import pytest
from hypothesis import given, strategies as st, assume
from datetime import date, timedelta
from typing import List

from app.carbon_dating_engine import CarbonDatingEngine, generate_risk_explanation
from app.schemas import Component, ComponentCategory, RiskLevel


# Strategy for generating valid components
def component_strategy():
    """Generate valid Component instances for property testing."""
    return st.builds(
        Component,
        name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc'))),
        version=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd'))),
        release_date=st.dates(min_value=date(1990, 1, 1), max_value=date.today()),
        end_of_life_date=st.one_of(st.none(), st.dates(min_value=date(1990, 1, 1), max_value=date.today() + timedelta(days=3650))),
        category=st.sampled_from(ComponentCategory),
        risk_level=st.sampled_from(RiskLevel),
        age_years=st.floats(min_value=0.1, max_value=50, allow_nan=False, allow_infinity=False),
        weight=st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False)
    )


@given(component=component_strategy())
def test_property_11_risk_classification_explanation(component):
    """
    **Feature: stackdebt, Property 11: Risk Classification Explanation**
    
    For any component with an assigned risk level, the system should provide 
    contextual information explaining why that classification was assigned.
    
    **Validates: Requirements 4.5**
    """
    engine = CarbonDatingEngine()
    
    explanation = engine.generate_risk_explanation(component)
    
    # Property: Explanation should be a non-empty string
    assert isinstance(explanation, str), "Risk explanation should be a string"
    assert len(explanation) > 0, "Risk explanation should not be empty"
    
    # Property: Explanation should contain the component name and version
    assert component.name in explanation, f"Explanation should contain component name '{component.name}'"
    assert component.version in explanation, f"Explanation should contain component version '{component.version}'"
    
    # Property: Explanation should contain the risk level (but may be overridden by EOL logic)
    # If component is past EOL, it will always be CRITICAL regardless of input risk level
    actual_risk_level = "CRITICAL" if (component.end_of_life_date and date.today() > component.end_of_life_date) else component.risk_level
    risk_level_text = actual_risk_level.upper() if isinstance(actual_risk_level, str) else actual_risk_level.value.upper()
    assert risk_level_text in explanation, f"Explanation should contain actual risk level '{risk_level_text}'"
    
    # Property: Explanation should contain age information (unless overridden by EOL)
    if component.end_of_life_date and date.today() > component.end_of_life_date:
        # EOL explanations may not contain age information
        assert "end-of-life" in explanation.lower() or "eol" in explanation.lower(), \
            "EOL explanation should mention end-of-life"
    else:
        # Non-EOL explanations should contain age
        age_str = str(component.age_years)
        assert age_str in explanation, f"Explanation should contain age information '{age_str}'"
    
    # Property: Explanation should be contextually appropriate for the actual risk level
    actual_risk_level = "CRITICAL" if (component.end_of_life_date and date.today() > component.end_of_life_date) else component.risk_level
    
    if actual_risk_level == RiskLevel.CRITICAL or actual_risk_level == "CRITICAL":
        assert "CRITICAL" in explanation, "Critical risk explanation should contain 'CRITICAL'"
        # Should mention either age or EOL
        assert ("years old" in explanation or "end-of-life" in explanation), \
            "Critical explanation should mention age or end-of-life"
    elif actual_risk_level == RiskLevel.WARNING or actual_risk_level == "WARNING":
        assert "WARNING" in explanation, "Warning risk explanation should contain 'WARNING'"
        assert "years old" in explanation, "Warning explanation should mention age"
    else:  # RiskLevel.OK
        assert "OK" in explanation, "OK risk explanation should contain 'OK'"
        assert "years old" in explanation, "OK explanation should mention age"


@given(
    age_years=st.floats(min_value=5.1, max_value=50, allow_nan=False, allow_infinity=False),
    name=st.text(min_size=1, max_size=30),
    version=st.text(min_size=1, max_size=15)
)
def test_property_11_critical_age_explanation(age_years, name, version):
    """
    **Feature: stackdebt, Property 11: Risk Classification Explanation**
    
    For any component classified as CRITICAL due to age (>5 years), the explanation 
    should mention that it's outdated and likely missing security patches.
    
    **Validates: Requirements 4.5**
    """
    engine = CarbonDatingEngine()
    
    critical_component = Component(
        name=name,
        version=version,
        release_date=date(2020, 1, 1),
        category=ComponentCategory.LIBRARY,
        risk_level=RiskLevel.CRITICAL,
        age_years=age_years,
        weight=0.1
    )
    
    explanation = engine.generate_risk_explanation(critical_component)
    
    # Property: Critical age explanation should mention being outdated
    assert "outdated" in explanation.lower(), "Critical age explanation should mention 'outdated'"
    
    # Property: Should mention security implications
    security_keywords = ["security", "patches", "updates"]
    has_security_mention = any(keyword in explanation.lower() for keyword in security_keywords)
    assert has_security_mention, f"Critical explanation should mention security concerns: {explanation}"
    
    # Property: Should mention the specific age (rounded to 1 decimal place)
    age_rounded = round(age_years, 1)
    assert str(age_rounded) in explanation, f"Explanation should contain the rounded age {age_rounded}"


@given(
    days_past_eol=st.integers(min_value=1, max_value=3650),
    name=st.text(min_size=1, max_size=30),
    version=st.text(min_size=1, max_size=15)
)
def test_property_11_eol_explanation(days_past_eol, name, version):
    """
    **Feature: stackdebt, Property 11: Risk Classification Explanation**
    
    For any component classified as CRITICAL due to being past end-of-life, 
    the explanation should mention EOL status and lack of security updates.
    
    **Validates: Requirements 4.5**
    """
    engine = CarbonDatingEngine()
    
    eol_date = date.today() - timedelta(days=days_past_eol)
    
    eol_component = Component(
        name=name,
        version=version,
        release_date=date(2020, 1, 1),
        end_of_life_date=eol_date,
        category=ComponentCategory.LIBRARY,
        risk_level=RiskLevel.CRITICAL,
        age_years=2.0,  # Not critical by age, but critical by EOL
        weight=0.1
    )
    
    explanation = engine.generate_risk_explanation(eol_component)
    
    # Property: EOL explanation should mention end-of-life
    eol_keywords = ["end-of-life", "eol"]
    has_eol_mention = any(keyword in explanation.lower() for keyword in eol_keywords)
    assert has_eol_mention, f"EOL explanation should mention end-of-life: {explanation}"
    
    # Property: Should mention security updates are no longer available
    security_keywords = ["security updates", "no longer available", "not available"]
    has_security_mention = any(keyword in explanation.lower() for keyword in security_keywords)
    assert has_security_mention, f"EOL explanation should mention lack of security updates: {explanation}"
    
    # Property: Should mention the EOL date
    eol_date_str = str(eol_date)
    assert eol_date_str in explanation, f"Explanation should contain the EOL date {eol_date_str}"
    
    # Property: Should mention how many days past EOL
    assert str(days_past_eol) in explanation, f"Explanation should mention days past EOL: {days_past_eol}"


@given(
    age_years=st.floats(min_value=2.0, max_value=5.0, allow_nan=False, allow_infinity=False),
    name=st.text(min_size=1, max_size=30),
    version=st.text(min_size=1, max_size=15)
)
def test_property_11_warning_explanation(age_years, name, version):
    """
    **Feature: stackdebt, Property 11: Risk Classification Explanation**
    
    For any component classified as WARNING (2-5 years old), the explanation 
    should mention moderate age and suggest considering updates.
    
    **Validates: Requirements 4.5**
    """
    engine = CarbonDatingEngine()
    
    warning_component = Component(
        name=name,
        version=version,
        release_date=date(2020, 1, 1),
        category=ComponentCategory.FRAMEWORK,
        risk_level=RiskLevel.WARNING,
        age_years=age_years,
        weight=0.3
    )
    
    explanation = engine.generate_risk_explanation(warning_component)
    
    # Property: Warning explanation should mention moderate age
    moderate_keywords = ["moderately", "moderate", "outdated"]
    has_moderate_mention = any(keyword in explanation.lower() for keyword in moderate_keywords)
    assert has_moderate_mention, f"Warning explanation should mention moderate age: {explanation}"
    
    # Property: Should suggest updates or consideration
    update_keywords = ["updates", "considered", "should be"]
    has_update_mention = any(keyword in explanation.lower() for keyword in update_keywords)
    assert has_update_mention, f"Warning explanation should suggest updates: {explanation}"
    
    # Property: Should mention the specific age (rounded to 1 decimal place)
    age_rounded = round(age_years, 1)
    assert str(age_rounded) in explanation, f"Explanation should contain the rounded age {age_rounded}"


@given(
    age_years=st.floats(min_value=0.1, max_value=1.9, allow_nan=False, allow_infinity=False),
    name=st.text(min_size=1, max_size=30),
    version=st.text(min_size=1, max_size=15)
)
def test_property_11_ok_explanation(age_years, name, version):
    """
    **Feature: stackdebt, Property 11: Risk Classification Explanation**
    
    For any component classified as OK (<2 years old), the explanation 
    should mention that it's current and well-maintained.
    
    **Validates: Requirements 4.5**
    """
    engine = CarbonDatingEngine()
    
    ok_component = Component(
        name=name,
        version=version,
        release_date=date(2023, 1, 1),
        category=ComponentCategory.LIBRARY,
        risk_level=RiskLevel.OK,
        age_years=age_years,
        weight=0.1
    )
    
    explanation = engine.generate_risk_explanation(ok_component)
    
    # Property: OK explanation should mention being current or well-maintained
    positive_keywords = ["current", "well-maintained", "relatively current"]
    has_positive_mention = any(keyword in explanation.lower() for keyword in positive_keywords)
    assert has_positive_mention, f"OK explanation should mention positive status: {explanation}"
    
    # Property: Should mention the specific age (rounded to 1 decimal place)
    age_rounded = round(age_years, 1)
    assert str(age_rounded) in explanation, f"Explanation should contain the rounded age {age_rounded}"


@given(components=st.lists(component_strategy(), min_size=1, max_size=10))
def test_property_11_explanation_consistency(components):
    """
    **Feature: stackdebt, Property 11: Risk Classification Explanation**
    
    For any set of components, each component should receive a consistent 
    explanation based on its risk level and characteristics.
    
    **Validates: Requirements 4.5**
    """
    engine = CarbonDatingEngine()
    
    for component in components:
        explanation = engine.generate_risk_explanation(component)
        
        # Property: Explanation should be deterministic
        explanation2 = engine.generate_risk_explanation(component)
        assert explanation == explanation2, "Risk explanation should be deterministic"
        
        # Property: Explanation format should be consistent (actual risk level may differ from input)
        actual_risk_level = "CRITICAL" if (component.end_of_life_date and date.today() > component.end_of_life_date) else component.risk_level
        risk_level_text = actual_risk_level.upper() if isinstance(actual_risk_level, str) else actual_risk_level.value.upper()
        assert explanation.startswith(risk_level_text + ":"), \
            f"Explanation should start with actual risk level: {explanation}"
        
        # Property: Explanation should contain component identification
        assert component.name in explanation, "Explanation should contain component name"
        assert component.version in explanation, "Explanation should contain component version"


@given(
    component1=component_strategy(),
    component2=component_strategy()
)
def test_property_11_different_components_different_explanations(component1, component2):
    """
    **Feature: stackdebt, Property 11: Risk Classification Explanation**
    
    For any two different components, they should receive different explanations 
    (unless they have identical characteristics).
    
    **Validates: Requirements 4.5**
    """
    assume(component1.name != component2.name or component1.version != component2.version)
    
    engine = CarbonDatingEngine()
    
    explanation1 = engine.generate_risk_explanation(component1)
    explanation2 = engine.generate_risk_explanation(component2)
    
    # Property: Different components should have different explanations
    # (unless they happen to have identical risk characteristics)
    if (component1.risk_level == component2.risk_level and 
        component1.age_years == component2.age_years and
        component1.end_of_life_date == component2.end_of_life_date):
        # Components with identical risk characteristics may have similar explanations
        # but should still contain their specific names and versions
        assert component1.name in explanation1, "Explanation1 should contain component1 name"
        assert component2.name in explanation2, "Explanation2 should contain component2 name"
    else:
        # Components with different characteristics should have different explanations
        assert explanation1 != explanation2, \
            f"Different components should have different explanations. " \
            f"Component1: {component1.name} {component1.version} ({component1.risk_level}), " \
            f"Component2: {component2.name} {component2.version} ({component2.risk_level})"


@given(component=component_strategy())
def test_property_11_explanation_completeness(component):
    """
    **Feature: stackdebt, Property 11: Risk Classification Explanation**
    
    For any component, the risk explanation should provide complete contextual 
    information about why the risk classification was assigned.
    
    **Validates: Requirements 4.5**
    """
    engine = CarbonDatingEngine()
    
    explanation = engine.generate_risk_explanation(component)
    
    # Property: Explanation should be comprehensive
    assert len(explanation) > 20, "Explanation should be reasonably detailed"
    
    # Property: Explanation should be human-readable
    assert explanation[0].isupper(), "Explanation should start with capital letter"
    assert explanation.endswith('.'), "Explanation should end with period"
    
    # Property: Explanation should contain key information elements
    actual_risk_level = "CRITICAL" if (component.end_of_life_date and date.today() > component.end_of_life_date) else component.risk_level
    risk_level_text = actual_risk_level.upper() if isinstance(actual_risk_level, str) else actual_risk_level.value.upper()
    
    required_elements = [
        component.name,
        component.version,
        risk_level_text
    ]
    
    # Age may not be present in EOL explanations
    if not (component.end_of_life_date and date.today() > component.end_of_life_date):
        required_elements.append(str(component.age_years))
    
    for element in required_elements:
        assert element in explanation, f"Explanation should contain '{element}': {explanation}"
    
    # Property: Explanation should be contextually appropriate
    if component.end_of_life_date and date.today() > component.end_of_life_date:
        # Past EOL should be mentioned
        assert "end-of-life" in explanation.lower() or "eol" in explanation.lower(), \
            "Past EOL component should mention end-of-life in explanation"
    
    # Property: Explanation should provide actionable context
    if component.risk_level == RiskLevel.CRITICAL:
        # Should suggest urgency or security concerns
        urgency_keywords = ["security", "patches", "outdated", "missing", "no longer"]
        has_urgency = any(keyword in explanation.lower() for keyword in urgency_keywords)
        assert has_urgency, f"Critical explanation should convey urgency: {explanation}"


# Edge case tests
def test_risk_explanation_edge_cases():
    """Test edge cases for risk explanation generation."""
    engine = CarbonDatingEngine()
    
    # Test with very old component
    very_old = Component(
        name="AncientSoftware",
        version="0.1.0",
        release_date=date(1995, 1, 1),
        category=ComponentCategory.LIBRARY,
        risk_level=RiskLevel.CRITICAL,
        age_years=29.0,
        weight=0.1
    )
    
    explanation = engine.generate_risk_explanation(very_old)
    assert "29.0" in explanation, "Should mention specific age for very old component"
    assert "CRITICAL" in explanation, "Should indicate critical risk"
    
    # Test with component exactly at EOL
    today = date.today()
    eol_today = Component(
        name="EOLToday",
        version="1.0.0",
        release_date=date(2020, 1, 1),
        end_of_life_date=today,
        category=ComponentCategory.FRAMEWORK,
        risk_level=RiskLevel.OK,  # Not past EOL yet
        age_years=4.0,
        weight=0.3
    )
    
    explanation_eol_today = engine.generate_risk_explanation(eol_today)
    assert "OK" in explanation_eol_today, "Component with EOL today should be OK"
    
    # Test with very new component
    very_new = Component(
        name="BrandNew",
        version="2.0.0",
        release_date=date.today(),
        category=ComponentCategory.LIBRARY,
        risk_level=RiskLevel.OK,
        age_years=0.0,
        weight=0.1
    )
    
    explanation_new = engine.generate_risk_explanation(very_new)
    assert "0.0" in explanation_new, "Should mention zero age for brand new component"
    assert "OK" in explanation_new, "Brand new component should be OK"


def test_convenience_function():
    """Test the convenience function for risk explanation."""
    component = Component(
        name="TestComponent",
        version="1.0.0",
        release_date=date(2020, 1, 1),
        category=ComponentCategory.LIBRARY,
        risk_level=RiskLevel.WARNING,
        age_years=3.0,
        weight=0.1
    )
    
    # Test convenience function
    explanation = generate_risk_explanation(component)
    assert isinstance(explanation, str)
    assert len(explanation) > 0
    assert "TestComponent" in explanation
    assert "WARNING" in explanation