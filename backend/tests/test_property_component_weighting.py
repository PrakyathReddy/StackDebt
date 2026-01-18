"""
Property-based tests for component weighting system.
**Feature: stackdebt, Property 7: Component Weighting System**
**Validates: Requirements 3.1, 3.2**
"""

import pytest
from hypothesis import given, strategies as st, assume
from datetime import date, timedelta
from typing import List

from app.carbon_dating_engine import CarbonDatingEngine
from app.schemas import Component, ComponentCategory, RiskLevel
from app.utils import get_component_weight


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
        age_years=st.floats(min_value=0, max_value=50, allow_nan=False, allow_infinity=False),
        weight=st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False)
    )


@given(components=st.lists(component_strategy(), min_size=1, max_size=10))
def test_property_7_component_weighting_system(components):
    """
    **Feature: stackdebt, Property 7: Component Weighting System**
    
    For any set of detected components, critical components (OS, languages, databases) 
    should receive higher weights than non-critical components (libraries, tools).
    
    **Validates: Requirements 3.1, 3.2**
    """
    engine = CarbonDatingEngine()
    
    # Separate components by criticality
    critical_categories = {
        ComponentCategory.OPERATING_SYSTEM,
        ComponentCategory.PROGRAMMING_LANGUAGE,
        ComponentCategory.DATABASE
    }
    
    critical_components = [c for c in components if c.category in critical_categories]
    non_critical_components = [c for c in components if c.category not in critical_categories]
    
    # Property: If we have both critical and non-critical components,
    # critical components should have higher base weights
    if critical_components and non_critical_components:
        critical_weights = [get_component_weight(c.category) for c in critical_components]
        non_critical_weights = [get_component_weight(c.category) for c in non_critical_components]
        
        max_critical_weight = max(critical_weights)
        max_non_critical_weight = max(non_critical_weights)
        
        assert max_critical_weight > max_non_critical_weight, \
            f"Critical components should have higher weights than non-critical. " \
            f"Max critical: {max_critical_weight}, Max non-critical: {max_non_critical_weight}"
    
    # Property: All critical components should have the same high weight (0.7)
    for component in critical_components:
        weight = get_component_weight(component.category)
        assert weight == 0.7, f"Critical component {component.category} should have weight 0.7, got {weight}"
    
    # Property: Non-critical components should have lower weights
    for component in non_critical_components:
        weight = get_component_weight(component.category)
        assert weight < 0.7, f"Non-critical component {component.category} should have weight < 0.7, got {weight}"


@given(components=st.lists(component_strategy(), min_size=2, max_size=5))
def test_property_7_weight_consistency(components):
    """
    **Feature: stackdebt, Property 7: Component Weighting System**
    
    For any component category, the weight should be consistent across all 
    components of that category.
    
    **Validates: Requirements 3.1, 3.2**
    """
    # Group components by category
    category_weights = {}
    
    for component in components:
        weight = get_component_weight(component.category)
        
        if component.category in category_weights:
            # Property: Same category should always have same weight
            assert category_weights[component.category] == weight, \
                f"Category {component.category} should have consistent weight. " \
                f"Expected {category_weights[component.category]}, got {weight}"
        else:
            category_weights[component.category] = weight
    
    # Property: Weights should be within valid range
    for category, weight in category_weights.items():
        assert 0 < weight <= 1.0, f"Weight for {category} should be in (0, 1], got {weight}"


@given(
    critical_component=st.builds(
        Component,
        name=st.text(min_size=1, max_size=20),
        version=st.text(min_size=1, max_size=10),
        release_date=st.dates(min_value=date(2000, 1, 1), max_value=date.today()),
        category=st.sampled_from([
            ComponentCategory.OPERATING_SYSTEM,
            ComponentCategory.PROGRAMMING_LANGUAGE,
            ComponentCategory.DATABASE
        ]),
        risk_level=st.sampled_from(RiskLevel),
        age_years=st.floats(min_value=0, max_value=20, allow_nan=False, allow_infinity=False),
        weight=st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False)
    ),
    non_critical_component=st.builds(
        Component,
        name=st.text(min_size=1, max_size=20),
        version=st.text(min_size=1, max_size=10),
        release_date=st.dates(min_value=date(2000, 1, 1), max_value=date.today()),
        category=st.sampled_from([
            ComponentCategory.LIBRARY,
            ComponentCategory.DEVELOPMENT_TOOL,
            ComponentCategory.WEB_SERVER,
            ComponentCategory.FRAMEWORK
        ]),
        risk_level=st.sampled_from(RiskLevel),
        age_years=st.floats(min_value=0, max_value=20, allow_nan=False, allow_infinity=False),
        weight=st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
)
def test_property_7_critical_vs_non_critical_weighting(critical_component, non_critical_component):
    """
    **Feature: stackdebt, Property 7: Component Weighting System**
    
    For any critical component and any non-critical component, the critical 
    component should receive a higher base weight.
    
    **Validates: Requirements 3.1, 3.2**
    """
    critical_weight = get_component_weight(critical_component.category)
    non_critical_weight = get_component_weight(non_critical_component.category)
    
    # Property: Critical components always have higher base weight
    assert critical_weight > non_critical_weight, \
        f"Critical component ({critical_component.category}) weight {critical_weight} " \
        f"should be higher than non-critical ({non_critical_component.category}) weight {non_critical_weight}"


@given(components=st.lists(component_strategy(), min_size=1, max_size=8))
def test_property_7_weighted_age_calculation_influence(components):
    """
    **Feature: stackdebt, Property 7: Component Weighting System**
    
    For any set of components, the weighting system should influence the final 
    effective age calculation, with critical components having more impact.
    
    **Validates: Requirements 3.1, 3.2**
    """
    engine = CarbonDatingEngine()
    
    # Apply component weights
    weighted_components = engine._apply_component_weights(components)
    
    # Property: Each component should have a final weight that reflects its category
    for wc in weighted_components:
        component = wc['component']
        base_weight = get_component_weight(component.category)
        
        # The final weight should be based on the base weight
        assert wc['base_weight'] == base_weight, \
            f"Base weight should match category weight for {component.category}"
        
        # Final weight should be base weight * risk multiplier
        expected_final_weight = base_weight * wc['risk_multiplier']
        assert abs(wc['final_weight'] - expected_final_weight) < 0.001, \
            f"Final weight calculation incorrect for {component.name}"
        
        # Weighted age should be age * final weight
        expected_weighted_age = component.age_years * wc['final_weight']
        assert abs(wc['weighted_age'] - expected_weighted_age) < 0.001, \
            f"Weighted age calculation incorrect for {component.name}"


@given(
    age_years=st.floats(min_value=0.1, max_value=20, allow_nan=False, allow_infinity=False),
    category=st.sampled_from(ComponentCategory)
)
def test_property_7_weight_category_mapping(age_years, category):
    """
    **Feature: stackdebt, Property 7: Component Weighting System**
    
    For any component category, the weight assignment should follow the 
    documented category-to-weight mapping.
    
    **Validates: Requirements 3.1, 3.2**
    """
    weight = get_component_weight(category)
    
    # Property: Weight assignment follows documented rules
    critical_categories = {
        ComponentCategory.OPERATING_SYSTEM,
        ComponentCategory.PROGRAMMING_LANGUAGE,
        ComponentCategory.DATABASE
    }
    
    important_categories = {
        ComponentCategory.WEB_SERVER,
        ComponentCategory.FRAMEWORK
    }
    
    if category in critical_categories:
        assert weight == 0.7, f"Critical category {category} should have weight 0.7, got {weight}"
    elif category in important_categories:
        assert weight == 0.3, f"Important category {category} should have weight 0.3, got {weight}"
    else:
        assert weight == 0.1, f"Minor category {category} should have weight 0.1, got {weight}"


@given(components=st.lists(component_strategy(), min_size=3, max_size=5))
def test_property_7_weight_distribution_impact(components):
    """
    **Feature: stackdebt, Property 7: Component Weighting System**
    
    For any set of components with mixed categories, the presence of critical 
    components should have a measurable impact on the overall weight distribution.
    
    **Validates: Requirements 3.1, 3.2**
    """
    engine = CarbonDatingEngine()
    
    # Separate critical and non-critical components
    critical_categories = {
        ComponentCategory.OPERATING_SYSTEM,
        ComponentCategory.PROGRAMMING_LANGUAGE,
        ComponentCategory.DATABASE
    }
    
    critical_components = [c for c in components if c.category in critical_categories]
    non_critical_components = [c for c in components if c.category not in critical_categories]
    
    if critical_components and non_critical_components:
        # Calculate weights for all components
        all_weighted = engine._apply_component_weights(components)
        critical_weighted = engine._apply_component_weights(critical_components)
        non_critical_weighted = engine._apply_component_weights(non_critical_components)
        
        # Property: Critical components should contribute more to total weight
        total_critical_weight = sum(wc['final_weight'] for wc in critical_weighted)
        total_non_critical_weight = sum(wc['final_weight'] for wc in non_critical_weighted)
        
        # If we have equal numbers of critical and non-critical components,
        # critical should have higher total weight
        if len(critical_components) == len(non_critical_components):
            assert total_critical_weight > total_non_critical_weight, \
                f"Equal numbers of critical and non-critical components should result in " \
                f"higher total weight for critical components. " \
                f"Critical: {total_critical_weight}, Non-critical: {total_non_critical_weight}"


# Edge case tests for specific scenarios
def test_component_weighting_edge_cases():
    """Test edge cases for component weighting."""
    
    # Test all category types have valid weights
    for category in ComponentCategory:
        weight = get_component_weight(category)
        assert 0 < weight <= 1.0, f"Category {category} should have valid weight, got {weight}"
    
    # Test specific weight values match design document
    assert get_component_weight(ComponentCategory.OPERATING_SYSTEM) == 0.7
    assert get_component_weight(ComponentCategory.PROGRAMMING_LANGUAGE) == 0.7
    assert get_component_weight(ComponentCategory.DATABASE) == 0.7
    assert get_component_weight(ComponentCategory.WEB_SERVER) == 0.3
    assert get_component_weight(ComponentCategory.FRAMEWORK) == 0.3
    assert get_component_weight(ComponentCategory.LIBRARY) == 0.1
    assert get_component_weight(ComponentCategory.DEVELOPMENT_TOOL) == 0.1


def test_component_weighting_deterministic():
    """Test that component weighting is deterministic."""
    
    # Same category should always return same weight
    for _ in range(10):
        assert get_component_weight(ComponentCategory.OPERATING_SYSTEM) == 0.7
        assert get_component_weight(ComponentCategory.LIBRARY) == 0.1
        assert get_component_weight(ComponentCategory.WEB_SERVER) == 0.3