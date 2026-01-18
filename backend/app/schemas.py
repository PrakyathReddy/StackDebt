"""
Pydantic schemas for StackDebt API request/response models and data validation.
"""

from enum import Enum
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict


class ComponentCategory(str, Enum):
    """Enum for component categories."""
    OPERATING_SYSTEM = "operating_system"
    PROGRAMMING_LANGUAGE = "programming_language"
    DATABASE = "database"
    WEB_SERVER = "web_server"
    FRAMEWORK = "framework"
    LIBRARY = "library"
    DEVELOPMENT_TOOL = "development_tool"


class RiskLevel(str, Enum):
    """Enum for risk levels based on component age."""
    CRITICAL = "critical"
    WARNING = "warning"
    OK = "ok"


class Component(BaseModel):
    """Pydantic model for a software component with version and risk information."""
    model_config = ConfigDict(use_enum_values=True)
    
    name: str = Field(..., description="Name of the software component")
    version: str = Field(..., description="Version string of the component")
    release_date: date = Field(..., description="Release date of this version")
    end_of_life_date: Optional[date] = Field(None, description="End of life date if known")
    category: ComponentCategory = Field(..., description="Category of the component")
    risk_level: RiskLevel = Field(..., description="Risk level based on age")
    age_years: float = Field(..., ge=0, description="Age of the component in years")
    weight: float = Field(..., ge=0, le=1, description="Weight factor for age calculation")

    @field_validator('age_years')
    @classmethod
    def validate_age_years(cls, v):
        """Ensure age is calculated with proper precision."""
        return round(v, 1)


class StackAgeResult(BaseModel):
    """Pydantic model for the calculated stack age result."""
    model_config = ConfigDict(use_enum_values=True)
    
    effective_age: float = Field(..., ge=0, description="Calculated effective age in years")
    total_components: int = Field(..., ge=0, description="Total number of components analyzed")
    risk_distribution: Dict[RiskLevel, int] = Field(..., description="Count of components by risk level")
    oldest_critical_component: Optional[Component] = Field(None, description="The oldest critical component found")
    roast_commentary: str = Field(..., description="Engaging commentary about the infrastructure age")

    @field_validator('effective_age')
    @classmethod
    def validate_effective_age_precision(cls, v):
        """Ensure effective age is formatted with exactly one decimal place."""
        return round(v, 1)


class AnalysisRequest(BaseModel):
    """Pydantic model for analysis request."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://github.com/user/repo",
                "analysis_type": "github"
            }
        }
    )
    
    url: str = Field(..., description="URL to analyze (website or GitHub repository)")
    analysis_type: str = Field(..., description="Type of analysis: 'website' or 'github'")

    @field_validator('analysis_type')
    @classmethod
    def validate_analysis_type(cls, v):
        """Ensure analysis type is valid."""
        if v not in ['website', 'github']:
            raise ValueError("analysis_type must be 'website' or 'github'")
        return v

    @field_validator('url')
    @classmethod
    def validate_url_format(cls, v):
        """Basic URL format validation."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        return v


class AnalysisResponse(BaseModel):
    """Pydantic model for analysis response."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "stack_age_result": {
                    "effective_age": 3.2,
                    "total_components": 5,
                    "risk_distribution": {
                        "critical": 1,
                        "warning": 2,
                        "ok": 2
                    },
                    "oldest_critical_component": None,
                    "roast_commentary": "Your stack is showing its age!"
                },
                "components": [],
                "analysis_metadata": {
                    "analysis_duration_ms": 1500,
                    "components_detected": 5,
                    "components_failed": 0
                },
                "generated_at": "2024-01-01T12:00:00"
            }
        }
    )
    
    stack_age_result: StackAgeResult = Field(..., description="Calculated stack age results")
    components: List[Component] = Field(..., description="List of detected components")
    analysis_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional analysis metadata")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(), description="Timestamp when analysis was generated")


# Additional utility models for specific use cases

class RiskSummary(BaseModel):
    """Summary of risk levels across components."""
    critical_count: int = Field(0, ge=0)
    warning_count: int = Field(0, ge=0)
    ok_count: int = Field(0, ge=0)
    total_count: int = Field(0, ge=0)

    def model_post_init(self, __context):
        """Calculate total count after initialization."""
        expected_total = self.critical_count + self.warning_count + self.ok_count
        if self.total_count != expected_total:
            self.total_count = expected_total


class ComponentDetectionResult(BaseModel):
    """Result of component detection process."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detected_components": [],
                "failed_detections": ["unknown-package@1.0.0"],
                "detection_metadata": {
                    "files_analyzed": 3,
                    "detection_time_ms": 500
                }
            }
        }
    )
    
    detected_components: List[Component] = Field(default_factory=list)
    failed_detections: List[str] = Field(default_factory=list)
    detection_metadata: Dict[str, Any] = Field(default_factory=dict)