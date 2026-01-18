"""
Unit tests for Carbon Dating Engine functionality.
"""

import pytest
from datetime import date, timedelta
from typing import List

from app.carbon_dating_engine import CarbonDatingEngine, calculate_stack_age
from app.schemas import Component, ComponentCategory, RiskLevel, StackAgeResult
from app.utils import convert_sqlalchemy_to_pydantic_component


class TestCarbonDatingEngine:
    """Test suite for CarbonDatingEngine class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = CarbonDatingEngine()
        
        # Create test components with different ages and categories
        self.test_components = [
            Component(
                name="Ubuntu",
                version="18.04",
                release_date=date(2018, 4, 26),
                category=ComponentCategory.OPERATING_SYSTEM,
                risk_level=RiskLevel.CRITICAL,
                age_years=5.8,
                weight=0.7
            ),
            Component(
                name="Python",
                version="3.8.0",
                release_date=date(2019, 10, 14),
                category=ComponentCategory.PROGRAMMING_LANGUAGE,
                risk_level=RiskLevel.WARNING,
                age_years=4.2,
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
            ),
            Component(
                name="requests",
                version="2.25.1",
                release_date=date(2020, 12, 16),
                category=ComponentCategory.LIBRARY,
                risk_level=RiskLevel.WARNING,
                age_years=3.1,
                weight=0.1
            ),
            Component(
                name="React",
                version="18.0.0",
                release_date=date(2022, 3, 29),
                category=ComponentCategory.FRAMEWORK,
                risk_level=RiskLevel.OK,
                age_years=1.8,
                weight=0.3
            )
        ]

    def test_calculate_stack_age_basic(self):
        """Test basic stack age calculation."""
        result = self.engine.calculate_stack_age(self.test_components)
        
        assert isinstance(result, StackAgeResult)
        assert result.effective_age > 0
        assert result.total_components == 5
        assert isinstance(result.roast_commentary, str)
        assert len(result.roast_commentary) > 0

    def test_calculate_stack_age_precision(self):
        """Test that stack age is calculated with one decimal place precision."""
        result = self.engine.calculate_stack_age(self.test_components)
        
        # Check precision
        age_str = str(result.effective_age)
        if '.' in age_str:
            decimal_part = age_str.split('.')[1]
            assert len(decimal_part) == 1, f"Age should have exactly one decimal place, got {len(decimal_part)}"

    def test_calculate_stack_age_empty_components(self):
        """Test that empty component list raises ValueError."""
        with pytest.raises(ValueError, match="No components provided"):
            self.engine.calculate_stack_age([])

    def test_calculate_stack_age_invalid_components(self):
        """Test handling of components with invalid data."""
        # Create a component with zero weight (which should be filtered out)
        invalid_components = [
            Component(
                name="Invalid",
                version="1.0.0",
                release_date=date(2020, 1, 1),
                category=ComponentCategory.LIBRARY,
                risk_level=RiskLevel.OK,
                age_years=1.0,  # Valid age
                weight=0.0  # Invalid zero weight
            )
        ]
        
        with pytest.raises(ValueError, match="No valid components found"):
            self.engine.calculate_stack_age(invalid_components)

    def test_weakest_link_theory_emphasis(self):
        """Test that older critical components are weighted more heavily."""
        # Create two scenarios: one with old critical component, one without
        old_critical = Component(
            name="OldOS",
            version="1.0",
            release_date=date(2015, 1, 1),
            category=ComponentCategory.OPERATING_SYSTEM,
            risk_level=RiskLevel.CRITICAL,
            age_years=9.0,
            weight=0.7
        )
        
        new_library = Component(
            name="NewLib",
            version="2.0",
            release_date=date(2023, 1, 1),
            category=ComponentCategory.LIBRARY,
            risk_level=RiskLevel.OK,
            age_years=1.0,
            weight=0.1
        )
        
        # Scenario 1: Old critical + new library
        result1 = self.engine.calculate_stack_age([old_critical, new_library])
        
        # Scenario 2: Just new library
        result2 = self.engine.calculate_stack_age([new_library])
        
        # The presence of old critical component should significantly increase effective age
        assert result1.effective_age > result2.effective_age
        assert result1.effective_age > 5.0  # Should be influenced by critical component

    def test_risk_distribution_calculation(self):
        """Test risk distribution calculation."""
        result = self.engine.calculate_stack_age(self.test_components)
        
        expected_critical = sum(1 for c in self.test_components if c.risk_level == RiskLevel.CRITICAL)
        expected_warning = sum(1 for c in self.test_components if c.risk_level == RiskLevel.WARNING)
        expected_ok = sum(1 for c in self.test_components if c.risk_level == RiskLevel.OK)
        
        assert result.risk_distribution[RiskLevel.CRITICAL] == expected_critical
        assert result.risk_distribution[RiskLevel.WARNING] == expected_warning
        assert result.risk_distribution[RiskLevel.OK] == expected_ok

    def test_oldest_critical_component_identification(self):
        """Test identification of oldest critical component."""
        result = self.engine.calculate_stack_age(self.test_components)
        
        critical_components = [c for c in self.test_components if c.risk_level == RiskLevel.CRITICAL]
        if critical_components:
            expected_oldest = max(critical_components, key=lambda c: c.age_years)
            assert result.oldest_critical_component is not None
            assert result.oldest_critical_component.name == expected_oldest.name
            assert result.oldest_critical_component.age_years == expected_oldest.age_years

    def test_assign_risk_levels(self):
        """Test risk level assignment functionality."""
        # Create components with outdated risk levels
        components_to_update = [
            Component(
                name="TestComponent",
                version="1.0.0",
                release_date=date(2018, 1, 1),  # 6+ years old
                category=ComponentCategory.LIBRARY,
                risk_level=RiskLevel.OK,  # Incorrect risk level
                age_years=6.0,
                weight=0.1
            )
        ]
        
        updated_components = self.engine.assign_risk_levels(components_to_update)
        
        assert len(updated_components) == 1
        assert updated_components[0].risk_level == RiskLevel.CRITICAL  # Should be updated

    def test_generate_risk_explanation(self):
        """Test risk explanation generation."""
        critical_component = self.test_components[0]  # Ubuntu 18.04
        explanation = self.engine.generate_risk_explanation(critical_component)
        
        assert isinstance(explanation, str)
        assert len(explanation) > 0
        assert "CRITICAL" in explanation
        assert critical_component.name in explanation
        assert critical_component.version in explanation

    def test_generate_risk_explanation_eol(self):
        """Test risk explanation for end-of-life component."""
        eol_component = Component(
            name="EOLSoftware",
            version="1.0.0",
            release_date=date(2020, 1, 1),
            end_of_life_date=date(2022, 1, 1),  # Past EOL
            category=ComponentCategory.LIBRARY,
            risk_level=RiskLevel.CRITICAL,
            age_years=4.0,
            weight=0.1
        )
        
        explanation = self.engine.generate_risk_explanation(eol_component)
        
        assert "end-of-life" in explanation.lower()
        assert "security updates" in explanation.lower()

    def test_get_component_weights_info(self):
        """Test component weights information generation."""
        weights_info = self.engine.get_component_weights_info(self.test_components)
        
        assert 'total_components' in weights_info
        assert 'critical_components' in weights_info
        assert 'weight_distribution' in weights_info
        assert weights_info['total_components'] == 5
        
        # Check that critical components are identified correctly
        critical_categories = {
            ComponentCategory.OPERATING_SYSTEM,
            ComponentCategory.PROGRAMMING_LANGUAGE,
            ComponentCategory.DATABASE
        }
        expected_critical = sum(
            1 for c in self.test_components 
            if c.category in critical_categories
        )
        assert weights_info['critical_components'] == expected_critical

    def test_component_weight_application(self):
        """Test that component weights are applied correctly."""
        weighted_components = self.engine._apply_component_weights(self.test_components)
        
        assert len(weighted_components) == len(self.test_components)
        
        for wc in weighted_components:
            assert 'component' in wc
            assert 'base_weight' in wc
            assert 'risk_multiplier' in wc
            assert 'final_weight' in wc
            assert 'weighted_age' in wc
            
            # Verify calculations
            component = wc['component']
            expected_weighted_age = component.age_years * wc['final_weight']
            assert abs(wc['weighted_age'] - expected_weighted_age) < 0.001

    def test_convenience_functions(self):
        """Test convenience functions work correctly."""
        # Test calculate_stack_age convenience function
        result = calculate_stack_age(self.test_components)
        assert isinstance(result, StackAgeResult)
        
        # Test assign_risk_levels convenience function
        from app.carbon_dating_engine import assign_risk_levels
        updated = assign_risk_levels(self.test_components)
        assert len(updated) == len(self.test_components)

    def test_single_component_calculation(self):
        """Test calculation with a single component."""
        single_component = [self.test_components[0]]
        result = self.engine.calculate_stack_age(single_component)
        
        assert result.total_components == 1
        assert result.effective_age > 0
        assert isinstance(result.roast_commentary, str)

    def test_all_ok_components(self):
        """Test calculation with all OK-level components."""
        ok_components = [
            Component(
                name="NewTech",
                version="1.0.0",
                release_date=date(2023, 1, 1),
                category=ComponentCategory.LIBRARY,
                risk_level=RiskLevel.OK,
                age_years=1.0,
                weight=0.1
            ),
            Component(
                name="AnotherNew",
                version="2.0.0",
                release_date=date(2023, 6, 1),
                category=ComponentCategory.FRAMEWORK,
                risk_level=RiskLevel.OK,
                age_years=0.5,
                weight=0.3
            )
        ]
        
        result = self.engine.calculate_stack_age(ok_components)
        
        assert result.effective_age < 2.0  # Should be low for all OK components
        assert result.risk_distribution[RiskLevel.OK] == 2
        assert result.risk_distribution[RiskLevel.CRITICAL] == 0
        assert result.oldest_critical_component is None

    def test_mixed_category_weighting(self):
        """Test that different categories receive appropriate weights."""
        # Create components from different categories with same age
        os_component = Component(
            name="OS",
            version="1.0",
            release_date=date(2020, 1, 1),
            category=ComponentCategory.OPERATING_SYSTEM,
            risk_level=RiskLevel.WARNING,
            age_years=4.0,
            weight=0.7
        )
        
        lib_component = Component(
            name="Library",
            version="1.0",
            release_date=date(2020, 1, 1),
            category=ComponentCategory.LIBRARY,
            risk_level=RiskLevel.WARNING,
            age_years=4.0,
            weight=0.1
        )
        
        # Test that the weighting system properly applies different weights
        weighted_os = self.engine._apply_component_weights([os_component])
        weighted_lib = self.engine._apply_component_weights([lib_component])
        
        # OS component should have higher final weight due to category
        assert weighted_os[0]['final_weight'] > weighted_lib[0]['final_weight']
        
        # When combined, the OS component should have more influence
        result_combined = self.engine.calculate_stack_age([os_component, lib_component])
        result_lib_only = self.engine.calculate_stack_age([lib_component])
        
        # The combined result should be closer to the OS component's age due to higher weight
        # Since both have same age but different weights, the effective age should be influenced by weighting
        assert result_combined.effective_age >= result_lib_only.effective_age