"""
Data validation module for software version entries in StackDebt Encyclopedia.

This module provides comprehensive validation for software version data,
including format validation, consistency checks, and business rule enforcement.
"""

import re
import logging
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple, Set
from dataclasses import dataclass
from enum import Enum

from app.models import ComponentCategory, VersionRelease
from app.encyclopedia import EncyclopediaRepository

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"      # Blocks addition
    WARNING = "warning"  # Allows addition but logs concern
    INFO = "info"        # Informational only


@dataclass
class ValidationIssue:
    """Represents a validation issue found during version validation."""
    severity: ValidationSeverity
    code: str
    message: str
    field: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of version validation with issues and overall status."""
    is_valid: bool
    issues: List[ValidationIssue]
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any error-level issues."""
        return any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are any warning-level issues."""
        return any(issue.severity == ValidationSeverity.WARNING for issue in self.issues)
    
    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Get all issues of a specific severity level."""
        return [issue for issue in self.issues if issue.severity == severity]


class VersionValidator:
    """
    Comprehensive validator for software version data.
    
    Provides validation for individual versions and batch operations
    with configurable rules and business logic enforcement.
    """
    
    def __init__(self, encyclopedia: Optional[EncyclopediaRepository] = None):
        """
        Initialize the version validator.
        
        Args:
            encyclopedia: Encyclopedia repository for database checks (optional)
        """
        self.encyclopedia = encyclopedia or EncyclopediaRepository()
        
        # Version format patterns for different software types
        self.version_patterns = {
            'semantic': re.compile(r'^\d+\.\d+\.\d+(?:-[a-zA-Z0-9\-\.]+)?(?:\+[a-zA-Z0-9\-\.]+)?$'),
            'major_minor': re.compile(r'^\d+\.\d+(?:\.\d+)?(?:-[a-zA-Z0-9\-\.]+)?$'),
            'date_based': re.compile(r'^\d{4}\.\d{1,2}(?:\.\d{1,2})?$'),
            'single_number': re.compile(r'^\d+(?:\.\d+)*$'),
            'alphanumeric': re.compile(r'^[a-zA-Z0-9\.\-_+]+$')
        }
        
        # Software-specific validation rules
        self.software_rules = {
            'Python': {
                'expected_pattern': 'major_minor',
                'min_release_year': 1991,
                'typical_release_cycle_months': 18,
                'category': ComponentCategory.PROGRAMMING_LANGUAGE
            },
            'Node.js': {
                'expected_pattern': 'major_minor',
                'min_release_year': 2009,
                'typical_release_cycle_months': 6,
                'category': ComponentCategory.PROGRAMMING_LANGUAGE
            },
            'Java': {
                'expected_pattern': 'single_number',
                'min_release_year': 1995,
                'typical_release_cycle_months': 6,
                'category': ComponentCategory.PROGRAMMING_LANGUAGE
            },
            'React': {
                'expected_pattern': 'major_minor',
                'min_release_year': 2013,
                'typical_release_cycle_months': 6,
                'category': ComponentCategory.FRAMEWORK
            },
            'Vue.js': {
                'expected_pattern': 'major_minor',
                'min_release_year': 2014,
                'typical_release_cycle_months': 6,
                'category': ComponentCategory.FRAMEWORK
            },
            'Angular': {
                'expected_pattern': 'single_number',
                'min_release_year': 2010,
                'typical_release_cycle_months': 6,
                'category': ComponentCategory.FRAMEWORK
            },
            'PostgreSQL': {
                'expected_pattern': 'major_minor',
                'min_release_year': 1996,
                'typical_release_cycle_months': 12,
                'category': ComponentCategory.DATABASE
            },
            'MySQL': {
                'expected_pattern': 'major_minor',
                'min_release_year': 1995,
                'typical_release_cycle_months': 12,
                'category': ComponentCategory.DATABASE
            },
            'nginx': {
                'expected_pattern': 'major_minor',
                'min_release_year': 2004,
                'typical_release_cycle_months': 3,
                'category': ComponentCategory.WEB_SERVER
            },
            'Apache HTTP Server': {
                'expected_pattern': 'major_minor',
                'min_release_year': 1995,
                'typical_release_cycle_months': 6,
                'category': ComponentCategory.WEB_SERVER
            }
        }
        
        # Common prerelease indicators
        self.prerelease_indicators = {
            'alpha', 'beta', 'rc', 'pre', 'dev', 'snapshot', 
            'nightly', 'canary', 'next', 'preview', 'test'
        }
    
    async def validate_single_version(self, software_name: str, version: str, 
                                    release_date: date, category: ComponentCategory,
                                    end_of_life_date: Optional[date] = None,
                                    is_lts: bool = False) -> ValidationResult:
        """
        Validate a single software version entry.
        
        Args:
            software_name: Name of the software
            version: Version string
            release_date: Release date
            category: Component category
            end_of_life_date: Optional end of life date
            is_lts: Whether this is an LTS version
            
        Returns:
            ValidationResult with issues and overall validity
            
        Validates: Requirements 7.6
        """
        issues = []
        
        # Basic field validation
        issues.extend(self._validate_software_name(software_name))
        issues.extend(self._validate_version_string(version, software_name))
        issues.extend(self._validate_release_date(release_date, software_name))
        issues.extend(self._validate_category(category, software_name))
        
        if end_of_life_date:
            issues.extend(self._validate_eol_date(end_of_life_date, release_date))
        
        # Cross-field validation
        issues.extend(self._validate_version_consistency(software_name, version, category))
        issues.extend(await self._validate_against_existing_data(software_name, version, release_date))
        
        # Business rule validation
        issues.extend(self._validate_business_rules(software_name, version, release_date, is_lts))
        
        # Determine overall validity (no errors)
        is_valid = not any(issue.severity == ValidationSeverity.ERROR for issue in issues)
        
        return ValidationResult(is_valid=is_valid, issues=issues)
    
    async def validate_batch_versions(self, versions: List[Dict[str, Any]]) -> Dict[str, ValidationResult]:
        """
        Validate a batch of version entries.
        
        Args:
            versions: List of version dictionaries to validate
            
        Returns:
            Dictionary mapping version keys to validation results
            
        Validates: Requirements 7.6
        """
        results = {}
        version_keys = set()
        
        # First pass: individual validation and duplicate detection
        for i, version_data in enumerate(versions):
            try:
                software_name = version_data['software_name']
                version = version_data['version']
                release_date = version_data['release_date']
                category = version_data['category']
                end_of_life_date = version_data.get('end_of_life_date')
                is_lts = version_data.get('is_lts', False)
                
                # Check for duplicates within batch
                version_key = f"{software_name}:{version}"
                if version_key in version_keys:
                    result = ValidationResult(
                        is_valid=False,
                        issues=[ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            code="DUPLICATE_IN_BATCH",
                            message=f"Duplicate version in batch: {software_name} {version}",
                            suggestion="Remove duplicate entries from the batch"
                        )]
                    )
                else:
                    version_keys.add(version_key)
                    result = await self.validate_single_version(
                        software_name, version, release_date, category, end_of_life_date, is_lts
                    )
                
                results[f"{i}:{version_key}"] = result
                
            except Exception as e:
                logger.error(f"Error validating batch item {i}: {e}")
                results[f"{i}:error"] = ValidationResult(
                    is_valid=False,
                    issues=[ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="VALIDATION_ERROR",
                        message=f"Error during validation: {str(e)}"
                    )]
                )
        
        # Second pass: cross-version validation
        await self._validate_batch_consistency(versions, results)
        
        return results
    
    def _validate_software_name(self, software_name: str) -> List[ValidationIssue]:
        """Validate software name format and content."""
        issues = []
        
        if not software_name or not software_name.strip():
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="EMPTY_SOFTWARE_NAME",
                message="Software name cannot be empty",
                field="software_name"
            ))
            return issues
        
        # Check length
        if len(software_name) > 255:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="SOFTWARE_NAME_TOO_LONG",
                message="Software name exceeds 255 characters",
                field="software_name",
                suggestion="Shorten the software name"
            ))
        
        # Check for invalid characters
        if not re.match(r'^[a-zA-Z0-9\s\.\-_@/]+$', software_name):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="INVALID_SOFTWARE_NAME_CHARS",
                message="Software name contains invalid characters",
                field="software_name",
                suggestion="Use only letters, numbers, spaces, dots, hyphens, underscores, @ and /"
            ))
        
        # Check for excessive whitespace
        if re.search(r'\s{2,}', software_name):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="EXCESSIVE_WHITESPACE",
                message="Software name contains excessive whitespace",
                field="software_name",
                suggestion="Remove extra spaces"
            ))
        
        return issues
    
    def _validate_version_string(self, version: str, software_name: str) -> List[ValidationIssue]:
        """Validate version string format."""
        issues = []
        
        if not version or not version.strip():
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="EMPTY_VERSION",
                message="Version cannot be empty",
                field="version"
            ))
            return issues
        
        # Check length
        if len(version) > 100:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VERSION_TOO_LONG",
                message="Version exceeds 100 characters",
                field="version",
                suggestion="Shorten the version string"
            ))
        
        # Check basic format
        if not self.version_patterns['alphanumeric'].match(version):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="INVALID_VERSION_CHARS",
                message="Version contains invalid characters",
                field="version",
                suggestion="Use only letters, numbers, dots, hyphens, underscores, and plus signs"
            ))
            return issues
        
        # Check against software-specific patterns
        if software_name in self.software_rules:
            expected_pattern = self.software_rules[software_name]['expected_pattern']
            if not self.version_patterns[expected_pattern].match(version):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="UNEXPECTED_VERSION_FORMAT",
                    message=f"Version format doesn't match expected pattern for {software_name}",
                    field="version",
                    suggestion=f"Expected {expected_pattern} format"
                ))
        
        # Check for prerelease indicators
        version_lower = version.lower()
        if any(indicator in version_lower for indicator in self.prerelease_indicators):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                code="PRERELEASE_VERSION",
                message="Version appears to be a prerelease",
                field="version"
            ))
        
        return issues
    
    def _validate_release_date(self, release_date: date, software_name: str) -> List[ValidationIssue]:
        """Validate release date."""
        issues = []
        
        # Check if date is in the future
        if release_date > date.today():
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="FUTURE_RELEASE_DATE",
                message="Release date cannot be in the future",
                field="release_date",
                suggestion="Use today's date or earlier"
            ))
        
        # Check minimum date (Unix epoch)
        if release_date < date(1970, 1, 1):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="RELEASE_DATE_TOO_OLD",
                message="Release date is before Unix epoch (1970-01-01)",
                field="release_date",
                suggestion="Use a more recent date"
            ))
        
        # Check against software-specific minimum dates
        if software_name in self.software_rules:
            min_year = self.software_rules[software_name]['min_release_year']
            if release_date.year < min_year:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="RELEASE_DATE_BEFORE_SOFTWARE_CREATION",
                    message=f"Release date is before {software_name} was created ({min_year})",
                    field="release_date",
                    suggestion=f"Check if the date is correct for {software_name}"
                ))
        
        # Check if date is very recent (might be a mistake)
        if release_date == date.today():
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                code="RELEASE_DATE_TODAY",
                message="Release date is today - confirm this is correct",
                field="release_date"
            ))
        
        return issues
    
    def _validate_category(self, category: ComponentCategory, software_name: str) -> List[ValidationIssue]:
        """Validate component category."""
        issues = []
        
        # Check against software-specific expected categories
        if software_name in self.software_rules:
            expected_category = self.software_rules[software_name]['category']
            if category != expected_category:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="UNEXPECTED_CATEGORY",
                    message=f"Category {category.value} doesn't match expected category for {software_name}",
                    field="category",
                    suggestion=f"Consider using {expected_category.value}"
                ))
        
        return issues
    
    def _validate_eol_date(self, eol_date: date, release_date: date) -> List[ValidationIssue]:
        """Validate end of life date."""
        issues = []
        
        # EOL date must be after release date
        if eol_date <= release_date:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="EOL_BEFORE_RELEASE",
                message="End of life date must be after release date",
                field="end_of_life_date",
                suggestion="Use a date after the release date"
            ))
        
        # Check if EOL date is too far in the future (more than 20 years)
        max_eol_date = date.today() + timedelta(days=20*365)
        if eol_date > max_eol_date:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="EOL_DATE_FAR_FUTURE",
                message="End of life date is more than 20 years in the future",
                field="end_of_life_date",
                suggestion="Verify the EOL date is correct"
            ))
        
        return issues
    
    def _validate_version_consistency(self, software_name: str, version: str, 
                                    category: ComponentCategory) -> List[ValidationIssue]:
        """Validate consistency between version, software name, and category."""
        issues = []
        
        # Check for common naming inconsistencies
        software_lower = software_name.lower()
        version_lower = version.lower()
        
        # Check if version contains software name (might be redundant)
        if software_lower in version_lower and len(software_name) > 3:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="VERSION_CONTAINS_SOFTWARE_NAME",
                message="Version string contains software name",
                field="version",
                suggestion="Remove software name from version string"
            ))
        
        # Check for version/category mismatches
        if category == ComponentCategory.OPERATING_SYSTEM:
            if not any(os_indicator in software_lower for os_indicator in ['ubuntu', 'centos', 'windows', 'macos', 'debian', 'fedora']):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="OS_CATEGORY_MISMATCH",
                    message="Software doesn't appear to be an operating system",
                    field="category",
                    suggestion="Verify the category is correct"
                ))
        
        return issues
    
    async def _validate_against_existing_data(self, software_name: str, version: str, 
                                            release_date: date) -> List[ValidationIssue]:
        """Validate against existing database data."""
        issues = []
        
        try:
            # Check if version already exists
            existing_version = await self.encyclopedia.lookup_version(software_name, version)
            if existing_version:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="VERSION_ALREADY_EXISTS",
                    message=f"Version {software_name} {version} already exists in database",
                    suggestion="Use a different version number or update the existing entry"
                ))
                return issues
            
            # Check for similar versions (potential duplicates)
            existing_versions = await self.encyclopedia.get_software_versions(software_name, limit=100)
            
            if existing_versions:
                # Check for chronological consistency
                newer_versions = [v for v in existing_versions if v.release_date > release_date]
                older_versions = [v for v in existing_versions if v.release_date < release_date]
                
                # Simple version comparison (this could be more sophisticated)
                if newer_versions and self._is_version_newer(version, newer_versions[0].version):
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="VERSION_CHRONOLOGY_INCONSISTENT",
                        message="Version appears newer than existing versions with later release dates",
                        suggestion="Verify the release date and version number are correct"
                    ))
                
                # Check for very similar version strings
                for existing in existing_versions[:10]:  # Check first 10
                    if self._versions_are_similar(version, existing.version):
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            code="SIMILAR_VERSION_EXISTS",
                            message=f"Similar version exists: {existing.version}",
                            suggestion="Verify this is not a duplicate"
                        ))
                        break
        
        except Exception as e:
            logger.warning(f"Error validating against existing data: {e}")
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="DATABASE_CHECK_FAILED",
                message="Could not validate against existing database data",
                suggestion="Manual verification recommended"
            ))
        
        return issues
    
    def _validate_business_rules(self, software_name: str, version: str, 
                               release_date: date, is_lts: bool) -> List[ValidationIssue]:
        """Validate business rules and best practices."""
        issues = []
        
        # Check LTS designation consistency
        if is_lts:
            # LTS versions should typically be major releases
            if '.' in version:
                parts = version.split('.')
                if len(parts) >= 2 and parts[1] != '0':
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        code="LTS_NOT_MAJOR_RELEASE",
                        message="LTS version is not a major release (x.0)",
                        suggestion="Verify LTS designation is correct"
                    ))
        
        # Check release timing patterns
        if software_name in self.software_rules:
            typical_cycle = self.software_rules[software_name]['typical_release_cycle_months']
            
            # This is a simplified check - in practice you'd compare against actual release history
            if typical_cycle <= 6 and release_date.weekday() > 4:  # Weekend release
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    code="WEEKEND_RELEASE",
                    message="Release date is on a weekend",
                    suggestion="Verify the release date is correct"
                ))
        
        return issues
    
    async def _validate_batch_consistency(self, versions: List[Dict[str, Any]], 
                                        results: Dict[str, ValidationResult]) -> None:
        """Validate consistency across a batch of versions."""
        # Group versions by software
        software_groups = {}
        for i, version_data in enumerate(versions):
            software_name = version_data.get('software_name', '')
            if software_name not in software_groups:
                software_groups[software_name] = []
            software_groups[software_name].append((i, version_data))
        
        # Check for chronological consistency within each software group
        for software_name, version_list in software_groups.items():
            if len(version_list) > 1:
                # Sort by release date
                sorted_versions = sorted(version_list, key=lambda x: x[1].get('release_date', date.min))
                
                for j in range(len(sorted_versions) - 1):
                    current_idx, current_data = sorted_versions[j]
                    next_idx, next_data = sorted_versions[j + 1]
                    
                    current_version = current_data.get('version', '')
                    next_version = next_data.get('version', '')
                    
                    # Check if version ordering matches date ordering
                    if self._is_version_newer(current_version, next_version):
                        # Add issue to both versions
                        issue = ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            code="BATCH_CHRONOLOGY_INCONSISTENT",
                            message=f"Version ordering inconsistent with release dates in batch",
                            suggestion="Verify version numbers and release dates are correct"
                        )
                        
                        current_key = f"{current_idx}:{software_name}:{current_version}"
                        next_key = f"{next_idx}:{software_name}:{next_version}"
                        
                        for key in results:
                            if current_key in key or next_key in key:
                                results[key].issues.append(issue)
    
    def _is_version_newer(self, version1: str, version2: str) -> bool:
        """
        Simple version comparison (version1 > version2).
        
        This is a simplified implementation - a production system would use
        a more sophisticated version comparison library.
        """
        try:
            # Split versions into parts
            parts1 = [int(x) for x in re.findall(r'\d+', version1)]
            parts2 = [int(x) for x in re.findall(r'\d+', version2)]
            
            # Pad shorter version with zeros
            max_len = max(len(parts1), len(parts2))
            parts1.extend([0] * (max_len - len(parts1)))
            parts2.extend([0] * (max_len - len(parts2)))
            
            return parts1 > parts2
        except (ValueError, TypeError):
            # Fallback to string comparison
            return version1 > version2
    
    def _versions_are_similar(self, version1: str, version2: str) -> bool:
        """Check if two versions are very similar (potential duplicates)."""
        # Remove common separators and compare
        clean1 = re.sub(r'[.\-_+]', '', version1.lower())
        clean2 = re.sub(r'[.\-_+]', '', version2.lower())
        
        # Check if they're identical after cleaning
        if clean1 == clean2:
            return True
        
        # Check if one is a substring of the other (with some tolerance)
        if len(clean1) > 3 and len(clean2) > 3:
            if clean1 in clean2 or clean2 in clean1:
                return True
        
        return False


# Global validator instance
version_validator = VersionValidator()