"""
Utility functions for data validation, conversion, and business logic.
"""

from datetime import date, datetime
from typing import List, Optional
from app.schemas import Component, ComponentCategory, RiskLevel


def calculate_age_years(release_date: date, reference_date: Optional[date] = None) -> float:
    """
    Calculate the age of a component in years from its release date.
    
    Args:
        release_date: The release date of the component
        reference_date: The reference date to calculate age from (defaults to today)
    
    Returns:
        Age in years with one decimal place precision
    """
    if reference_date is None:
        reference_date = date.today()
    
    age_days = (reference_date - release_date).days
    age_years = age_days / 365.25  # Account for leap years
    return round(age_years, 1)


def determine_risk_level(age_years: float, end_of_life_date: Optional[date] = None) -> RiskLevel:
    """
    Determine the risk level of a component based on its age and EOL status.
    
    Args:
        age_years: Age of the component in years
        end_of_life_date: End of life date if known
    
    Returns:
        Risk level (CRITICAL, WARNING, or OK)
    """
    # Check if component is past end of life
    if end_of_life_date and date.today() > end_of_life_date:
        return RiskLevel.CRITICAL
    
    # Age-based risk classification
    if age_years > 5.0:
        return RiskLevel.CRITICAL
    elif age_years >= 2.0:
        return RiskLevel.WARNING
    else:
        return RiskLevel.OK


def get_component_weight(category: ComponentCategory) -> float:
    """
    Get the weight factor for a component based on its category.
    
    Args:
        category: The component category
    
    Returns:
        Weight factor between 0 and 1
    """
    # Critical components get higher weights
    critical_categories = {
        ComponentCategory.OPERATING_SYSTEM,
        ComponentCategory.PROGRAMMING_LANGUAGE,
        ComponentCategory.DATABASE
    }
    
    # Important components get medium weights
    important_categories = {
        ComponentCategory.WEB_SERVER,
        ComponentCategory.FRAMEWORK
    }
    
    if category in critical_categories:
        return 0.7
    elif category in important_categories:
        return 0.3
    else:
        return 0.1


def convert_sqlalchemy_to_pydantic_component(
    software_name: str,
    version: str,
    release_date: date,
    end_of_life_date: Optional[date],
    category: ComponentCategory,
    reference_date: Optional[date] = None
) -> Component:
    """
    Convert SQLAlchemy VersionRelease data to a Pydantic Component model.
    
    Args:
        software_name: Name of the software
        version: Version string
        release_date: Release date
        end_of_life_date: End of life date if known
        category: Component category
        reference_date: Reference date for age calculation
    
    Returns:
        Pydantic Component model
    """
    age_years = calculate_age_years(release_date, reference_date)
    risk_level = determine_risk_level(age_years, end_of_life_date)
    weight = get_component_weight(category)
    
    return Component(
        name=software_name,
        version=version,
        release_date=release_date,
        end_of_life_date=end_of_life_date,
        category=category,
        risk_level=risk_level,
        age_years=age_years,
        weight=weight
    )


def validate_url_format(url: str) -> tuple[bool, str]:
    """
    Validate URL format and determine analysis type.
    
    Args:
        url: URL string to validate
    
    Returns:
        Tuple of (is_valid, analysis_type or error_message)
    """
    if not url:
        return False, "URL cannot be empty"
    
    if not url.startswith(('http://', 'https://')):
        return False, "URL must start with http:// or https://"
    
    # Determine analysis type
    if 'github.com' in url.lower():
        return True, 'github'
    else:
        return True, 'website'


def format_roast_commentary(effective_age: float, oldest_component: Optional[Component] = None) -> str:
    """
    Generate engaging roast commentary based on stack age.
    
    Args:
        effective_age: The calculated effective age
        oldest_component: The oldest critical component if any
    
    Returns:
        Roast commentary string
    """
    if effective_age < 1.0:
        return "🚀 Fresh as morning dew! Your stack is so new it still has that new-code smell."
    elif effective_age < 2.0:
        return "✨ Pretty modern! Your stack is aging like fine wine, not like milk."
    elif effective_age < 3.0:
        return "⚠️ Getting a bit long in the tooth. Time to start planning some updates!"
    elif effective_age < 5.0:
        return "🦴 Your stack is showing its age. Some components are getting creaky!"
    else:
        oldest_info = ""
        if oldest_component:
            oldest_info = f" That {oldest_component.name} {oldest_component.version} is practically archaeological!"
        return f"💀 Ancient! Your stack is {effective_age} years old on average.{oldest_info} Time for a serious modernization effort!"


def calculate_risk_multiplier(risk_level: RiskLevel) -> float:
    """
    Get the risk multiplier for age calculation based on risk level.
    
    Args:
        risk_level: The risk level of the component
    
    Returns:
        Risk multiplier factor
    """
    multipliers = {
        RiskLevel.CRITICAL: 2.0,
        RiskLevel.WARNING: 1.5,
        RiskLevel.OK: 1.0
    }
    return multipliers.get(risk_level, 1.0)