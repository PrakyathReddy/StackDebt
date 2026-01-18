"""
SQLAlchemy models for StackDebt Encyclopedia database.
"""

from sqlalchemy import Column, Integer, String, Date, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from app.database import Base
import enum

class ComponentCategory(enum.Enum):
    """Enum for component categories matching database enum."""
    OPERATING_SYSTEM = "operating_system"
    PROGRAMMING_LANGUAGE = "programming_language"
    DATABASE = "database"
    WEB_SERVER = "web_server"
    FRAMEWORK = "framework"
    LIBRARY = "library"
    DEVELOPMENT_TOOL = "development_tool"


class RiskLevel(enum.Enum):
    """Enum for risk levels based on component age."""
    CRITICAL = "critical"
    WARNING = "warning"
    OK = "ok"

class VersionRelease(Base):
    """Model for version_releases table."""
    __tablename__ = "version_releases"

    id = Column(Integer, primary_key=True, index=True)
    software_name = Column(String(255), nullable=False, index=True)
    version = Column(String(100), nullable=False)
    release_date = Column(Date, nullable=False, index=True)
    end_of_life_date = Column(Date, nullable=True)
    category = Column(Enum(ComponentCategory), nullable=False, index=True)
    is_lts = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<VersionRelease(software_name='{self.software_name}', version='{self.version}', release_date='{self.release_date}')>"