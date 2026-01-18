"""
Carbon Dating Engine for StackDebt infrastructure age calculation.

This module implements the core Carbon Dating algorithm that calculates the "Effective Age"
of software infrastructure using the Weakest Link Theory approach.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import date

from app.schemas import Component, StackAgeResult, RiskLevel, ComponentCategory
from app.utils import (
    calculate_age_years, 
    determine_risk_level, 
    get_component_weight, 
    calculate_risk_multiplier,
    format_roast_commentary
)

logger = logging.getLogger(__name__)


class CarbonDatingEngine:
    """
    Carbon Dating Engine that calculates infrastructure age using Weakest Link Theory.
    
    The engine implements a weighted age calculation that emphasizes older critical
    components more heavily than newer non-critical components, providing a realistic
    assessment of infrastructure risk.
    
    Validates: Requirements 3.1, 3.2, 3.3, 3.4, 4.5
    """

    def __init__(self):
        """Initialize the Carbon Dating Engine."""
        self.logger = logging.getLogger(__name__)

    def calculate_stack_age(self, components: List[Component]) -> StackAgeResult:
        """
        Calculate weighted effective age using Weakest Link theory.
        
        Args:
            components: List of detected software components
            
        Returns:
            StackAgeResult with calculated age and analysis
            
        Raises:
            ValueError: If no components are provided or no valid components found
            
        Validates: Requirements 3.3, 3.4, 3.5
        """
        if not components:
            raise ValueError("No components provided for age calculation")
        
        # Filter out components with invalid data
        valid_components = [c for c in components if c.age_years >= 0 and c.weight > 0]
        
        if not valid_components:
            raise ValueError("No valid components found for age calculation")
        
        self.logger.info(f"Calculating stack age for {len(valid_components)} valid components")
        
        # Apply component weights and risk multipliers
        weighted_components = self._apply_component_weights(valid_components)
        
        # Calculate effective age using Weakest Link Theory
        effective_age = self._calculate_weakest_link_age(weighted_components)
        
        # Generate risk distribution
        risk_distribution = self._calculate_risk_distribution(valid_components)
        
        # Find oldest critical component
        oldest_critical = self._find_oldest_critical_component(valid_components)
        
        # Generate roast commentary
        roast_commentary = format_roast_commentary(effective_age, oldest_critical)
        
        result = StackAgeResult(
            effective_age=effective_age,
            total_components=len(valid_components),
            risk_distribution=risk_distribution,
            oldest_critical_component=oldest_critical,
            roast_commentary=roast_commentary
        )
        
        self.logger.info(f"Calculated stack age: {effective_age} years from {len(valid_components)} components")
        return result

    def _apply_component_weights(self, components: List[Component]) -> List[Dict[str, Any]]:
        """
        Apply category-based weights to components.
        
        Args:
            components: List of components to weight
            
        Returns:
            List of weighted component data dictionaries
            
        Validates: Requirements 3.1, 3.2
        """
        weighted_components = []
        
        for component in components:
            # Get base weight from component category
            base_weight = get_component_weight(component.category)
            
            # Apply risk multiplier to emphasize problematic components
            risk_multiplier = calculate_risk_multiplier(component.risk_level)
            
            # Calculate final weight (Weakest Link Theory)
            final_weight = base_weight * risk_multiplier
            
            weighted_component = {
                'component': component,
                'base_weight': base_weight,
                'risk_multiplier': risk_multiplier,
                'final_weight': final_weight,
                'weighted_age': component.age_years * final_weight
            }
            
            weighted_components.append(weighted_component)
            
            self.logger.debug(
                f"Weighted {component.name} {component.version}: "
                f"age={component.age_years}, base_weight={base_weight}, "
                f"risk_multiplier={risk_multiplier}, final_weight={final_weight}"
            )
        
        return weighted_components

    def _calculate_weakest_link_age(self, weighted_components: List[Dict[str, Any]]) -> float:
        """
        Calculate effective age using Weakest Link Theory.
        
        The algorithm weights toward older critical components rather than using
        simple averaging, emphasizing the age of components that pose the highest risk.
        
        Args:
            weighted_components: List of weighted component data
            
        Returns:
            Effective age in years with one decimal place precision
            
        Validates: Requirements 3.3, 3.4, 3.5
        """
        if not weighted_components:
            return 0.0
        
        # Calculate weighted sum of ages
        total_weighted_age = sum(wc['weighted_age'] for wc in weighted_components)
        total_weight = sum(wc['final_weight'] for wc in weighted_components)
        
        if total_weight == 0:
            return 0.0
        
        # Weakest Link calculation: weighted average with emphasis on critical components
        effective_age = total_weighted_age / total_weight
        
        # Apply additional emphasis for critical components (Weakest Link Theory)
        critical_components = [
            wc for wc in weighted_components 
            if wc['component'].risk_level == RiskLevel.CRITICAL
        ]
        
        if critical_components:
            # Find the oldest critical component and apply additional weight
            oldest_critical_age = max(wc['component'].age_years for wc in critical_components)
            critical_emphasis = min(oldest_critical_age * 0.1, 2.0)  # Cap at 2 years additional
            effective_age += critical_emphasis
            
            self.logger.debug(
                f"Applied critical emphasis: +{critical_emphasis} years "
                f"(oldest critical: {oldest_critical_age} years)"
            )
        
        # Ensure precision is exactly one decimal place
        return round(effective_age, 1)

    def _calculate_risk_distribution(self, components: List[Component]) -> Dict[RiskLevel, int]:
        """
        Calculate the distribution of components by risk level.
        
        Args:
            components: List of components to analyze
            
        Returns:
            Dictionary mapping risk levels to component counts
            
        Validates: Requirements 4.1, 4.2, 4.3
        """
        distribution = {
            RiskLevel.CRITICAL: 0,
            RiskLevel.WARNING: 0,
            RiskLevel.OK: 0
        }
        
        for component in components:
            distribution[component.risk_level] += 1
        
        return distribution

    def _find_oldest_critical_component(self, components: List[Component]) -> Optional[Component]:
        """
        Find the oldest component classified as critical risk.
        
        Args:
            components: List of components to search
            
        Returns:
            Oldest critical component or None if no critical components found
            
        Validates: Requirements 4.1
        """
        critical_components = [
            c for c in components 
            if c.risk_level == RiskLevel.CRITICAL
        ]
        
        if not critical_components:
            return None
        
        # Return the component with the highest age
        return max(critical_components, key=lambda c: c.age_years)

    def assign_risk_levels(self, components: List[Component]) -> List[Component]:
        """
        Assign risk levels to components based on age and EOL status.
        
        This method updates the risk_level field of each component based on
        the current risk assessment rules.
        
        Args:
            components: List of components to update
            
        Returns:
            List of components with updated risk levels
            
        Validates: Requirements 4.1, 4.2, 4.3, 4.5
        """
        updated_components = []
        
        for component in components:
            # Recalculate risk level based on current rules
            new_risk_level = determine_risk_level(
                component.age_years, 
                component.end_of_life_date
            )
            
            # Create updated component with new risk level
            updated_component = Component(
                name=component.name,
                version=component.version,
                release_date=component.release_date,
                end_of_life_date=component.end_of_life_date,
                category=component.category,
                risk_level=new_risk_level,
                age_years=component.age_years,
                weight=component.weight
            )
            
            updated_components.append(updated_component)
            
            if new_risk_level != component.risk_level:
                self.logger.info(
                    f"Updated risk level for {component.name} {component.version}: "
                    f"{component.risk_level} -> {new_risk_level}"
                )
        
        return updated_components

    def generate_risk_explanation(self, component: Component) -> str:
        """
        Generate contextual explanation for why a component received its risk classification.
        
        Args:
            component: Component to explain
            
        Returns:
            Human-readable explanation of the risk classification
            
        Validates: Requirements 4.5
        """
        age_years = component.age_years
        eol_date = component.end_of_life_date
        risk_level = component.risk_level
        
        # Check if past EOL
        if eol_date and date.today() > eol_date:
            days_past_eol = (date.today() - eol_date).days
            return (
                f"CRITICAL: {component.name} {component.version} is {days_past_eol} days "
                f"past its end-of-life date ({eol_date}). Security updates are no longer available."
            )
        
        # Age-based explanations
        if risk_level == RiskLevel.CRITICAL:
            return (
                f"CRITICAL: {component.name} {component.version} is {age_years} years old, "
                f"significantly outdated and likely missing important security patches and features."
            )
        elif risk_level == RiskLevel.WARNING:
            return (
                f"WARNING: {component.name} {component.version} is {age_years} years old, "
                f"moderately outdated and should be considered for updates."
            )
        else:  # RiskLevel.OK
            return (
                f"OK: {component.name} {component.version} is {age_years} years old, "
                f"relatively current and well-maintained."
            )

    def get_component_weights_info(self, components: List[Component]) -> Dict[str, Any]:
        """
        Get detailed information about component weighting for analysis transparency.
        
        Args:
            components: List of components to analyze
            
        Returns:
            Dictionary with weighting information and statistics
            
        Validates: Requirements 3.1, 3.2
        """
        if not components:
            return {}
        
        category_weights = {}
        category_counts = {}
        
        for component in components:
            category = component.category
            weight = get_component_weight(category)
            
            if category not in category_weights:
                category_weights[category] = weight
                category_counts[category] = 0
            
            category_counts[category] += 1
        
        # Calculate weight distribution
        total_components = len(components)
        weight_distribution = {
            (category.value if hasattr(category, 'value') else str(category)): {
                'weight': weight,
                'count': category_counts[category],
                'percentage': round((category_counts[category] / total_components) * 100, 1)
            }
            for category, weight in category_weights.items()
        }
        
        # Identify critical vs non-critical breakdown
        critical_categories = {
            ComponentCategory.OPERATING_SYSTEM,
            ComponentCategory.PROGRAMMING_LANGUAGE,
            ComponentCategory.DATABASE
        }
        
        critical_count = sum(
            category_counts.get(cat, 0) 
            for cat in critical_categories
        )
        
        return {
            'total_components': total_components,
            'critical_components': critical_count,
            'non_critical_components': total_components - critical_count,
            'weight_distribution': weight_distribution,
            'weighting_strategy': 'Weakest Link Theory with category-based weights'
        }


# Global engine instance for convenience
carbon_dating_engine = CarbonDatingEngine()


# Convenience functions
def calculate_stack_age(components: List[Component]) -> StackAgeResult:
    """Convenience function for calculating stack age."""
    return carbon_dating_engine.calculate_stack_age(components)


def assign_risk_levels(components: List[Component]) -> List[Component]:
    """Convenience function for assigning risk levels."""
    return carbon_dating_engine.assign_risk_levels(components)


def generate_risk_explanation(component: Component) -> str:
    """Convenience function for generating risk explanations."""
    return carbon_dating_engine.generate_risk_explanation(component)