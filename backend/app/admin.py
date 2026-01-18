"""
Admin interface for StackDebt Encyclopedia database management.

This module provides administrative functionality for managing software version data,
including adding new versions, bulk imports, and automated updates from package registries.
"""

import asyncio
import logging
import re
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from pydantic import BaseModel, validator, Field
import httpx
import asyncpg

from app.encyclopedia import EncyclopediaRepository
from app.models import ComponentCategory, VersionRelease
from app.schemas import Component
from app.version_validator import VersionValidator, ValidationSeverity

logger = logging.getLogger(__name__)


class VersionAddRequest(BaseModel):
    """Request model for adding a new software version."""
    software_name: str = Field(..., min_length=1, max_length=255)
    version: str = Field(..., min_length=1, max_length=100)
    release_date: date
    end_of_life_date: Optional[date] = None
    category: ComponentCategory
    is_lts: bool = False
    
    @validator('software_name')
    def validate_software_name(cls, v):
        """Validate software name format."""
        if not v or not v.strip():
            raise ValueError("Software name cannot be empty")
        
        # Remove excessive whitespace
        v = re.sub(r'\s+', ' ', v.strip())
        
        # Check for valid characters (letters, numbers, spaces, dots, hyphens)
        if not re.match(r'^[a-zA-Z0-9\s\.\-_]+$', v):
            raise ValueError("Software name contains invalid characters")
        
        return v
    
    @validator('version')
    def validate_version(cls, v):
        """Validate version string format."""
        if not v or not v.strip():
            raise ValueError("Version cannot be empty")
        
        v = v.strip()
        
        # Basic version format validation (allows semantic versioning and other common formats)
        if not re.match(r'^[a-zA-Z0-9\.\-_+]+$', v):
            raise ValueError("Version contains invalid characters")
        
        return v
    
    @validator('release_date')
    def validate_release_date(cls, v):
        """Validate release date is not in the future."""
        if v > date.today():
            raise ValueError("Release date cannot be in the future")
        
        # Check for reasonable minimum date (Unix epoch)
        if v < date(1970, 1, 1):
            raise ValueError("Release date is too old (before 1970)")
        
        return v
    
    @validator('end_of_life_date')
    def validate_eol_date(cls, v, values):
        """Validate end of life date is after release date."""
        if v is not None and 'release_date' in values:
            if v < values['release_date']:
                raise ValueError("End of life date must be after release date")
        
        return v


class BulkVersionImportRequest(BaseModel):
    """Request model for bulk importing software versions."""
    versions: List[VersionAddRequest] = Field(..., min_items=1, max_items=100)
    
    @validator('versions')
    def validate_unique_versions(cls, v):
        """Ensure no duplicate software/version combinations."""
        seen = set()
        for version_req in v:
            key = (version_req.software_name.lower(), version_req.version.lower())
            if key in seen:
                raise ValueError(f"Duplicate version found: {version_req.software_name} {version_req.version}")
            seen.add(key)
        return v


class RegistryUpdateRequest(BaseModel):
    """Request model for updating from package registries."""
    software_name: str = Field(..., min_length=1, max_length=255)
    registry_type: str = Field(..., pattern=r'^(npm|pypi|maven|nuget|rubygems|crates)$')
    max_versions: int = Field(default=10, ge=1, le=50)
    include_prereleases: bool = False


class AdminService:
    """Service class for administrative operations on the Encyclopedia database."""
    
    def __init__(self):
        self.encyclopedia = EncyclopediaRepository()
        self.validator = VersionValidator(self.encyclopedia)
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Registry API endpoints
        self.registry_apis = {
            'npm': 'https://registry.npmjs.org',
            'pypi': 'https://pypi.org/pypi',
            'maven': 'https://search.maven.org/solrsearch/select',
            'nuget': 'https://api.nuget.org/v3-flatcontainer',
            'rubygems': 'https://rubygems.org/api/v1/gems',
            'crates': 'https://crates.io/api/v1/crates'
        }
    
    async def add_single_version(self, request: VersionAddRequest) -> Dict[str, Any]:
        """
        Add a single software version to the database.
        
        Args:
            request: Version addition request with validation
            
        Returns:
            Dictionary with operation result and details
            
        Validates: Requirements 7.6
        """
        try:
            # Validate the version data
            validation_result = await self.validator.validate_single_version(
                software_name=request.software_name,
                version=request.version,
                release_date=request.release_date,
                category=request.category,
                end_of_life_date=request.end_of_life_date,
                is_lts=request.is_lts
            )
            
            # Check for validation errors
            if not validation_result.is_valid:
                error_messages = [
                    issue.message for issue in validation_result.issues 
                    if issue.severity == ValidationSeverity.ERROR
                ]
                return {
                    'success': False,
                    'error': 'validation_failed',
                    'message': 'Version data validation failed',
                    'validation_errors': error_messages,
                    'validation_warnings': [
                        issue.message for issue in validation_result.issues 
                        if issue.severity == ValidationSeverity.WARNING
                    ]
                }
            
            # Log validation warnings
            warnings = validation_result.get_issues_by_severity(ValidationSeverity.WARNING)
            if warnings:
                logger.warning(f"Validation warnings for {request.software_name} {request.version}: {[w.message for w in warnings]}")
            
            # Check if version already exists (redundant with validation, but explicit)
            existing = await self.encyclopedia.lookup_version(
                request.software_name, request.version
            )
            
            if existing:
                return {
                    'success': False,
                    'error': 'version_exists',
                    'message': f'Version {request.software_name} {request.version} already exists',
                    'existing_version': {
                        'software_name': existing.software_name,
                        'version': existing.version,
                        'release_date': existing.release_date.isoformat(),
                        'category': existing.category.value
                    }
                }
            
            # Add the version
            success = await self.encyclopedia.add_version(
                software_name=request.software_name,
                version=request.version,
                release_date=request.release_date,
                category=request.category,
                end_of_life_date=request.end_of_life_date,
                is_lts=request.is_lts
            )
            
            if success:
                logger.info(f"Admin: Added version {request.software_name} {request.version}")
                return {
                    'success': True,
                    'message': f'Successfully added {request.software_name} {request.version}',
                    'version_data': {
                        'software_name': request.software_name,
                        'version': request.version,
                        'release_date': request.release_date.isoformat(),
                        'category': request.category.value,
                        'is_lts': request.is_lts
                    },
                    'validation_warnings': [w.message for w in warnings] if warnings else []
                }
            else:
                return {
                    'success': False,
                    'error': 'database_error',
                    'message': f'Failed to add {request.software_name} {request.version} to database'
                }
                
        except Exception as e:
            logger.error(f"Error adding version {request.software_name} {request.version}: {e}")
            return {
                'success': False,
                'error': 'internal_error',
                'message': f'Internal error: {str(e)}'
            }
    
    async def bulk_import_versions(self, request: BulkVersionImportRequest) -> Dict[str, Any]:
        """
        Import multiple software versions in bulk.
        
        Args:
            request: Bulk import request with list of versions
            
        Returns:
            Dictionary with operation results and statistics
            
        Validates: Requirements 7.6
        """
        results = {
            'total_requested': len(request.versions),
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'details': [],
            'errors': []
        }
        
        try:
            for version_req in request.versions:
                try:
                    result = await self.add_single_version(version_req)
                    
                    if result['success']:
                        results['successful'] += 1
                        results['details'].append({
                            'software_name': version_req.software_name,
                            'version': version_req.version,
                            'status': 'added'
                        })
                    elif result.get('error') == 'version_exists':
                        results['skipped'] += 1
                        results['details'].append({
                            'software_name': version_req.software_name,
                            'version': version_req.version,
                            'status': 'skipped',
                            'reason': 'already_exists'
                        })
                    else:
                        results['failed'] += 1
                        results['errors'].append({
                            'software_name': version_req.software_name,
                            'version': version_req.version,
                            'error': result.get('error', 'unknown'),
                            'message': result.get('message', 'Unknown error')
                        })
                        
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'software_name': version_req.software_name,
                        'version': version_req.version,
                        'error': 'processing_error',
                        'message': str(e)
                    })
            
            logger.info(
                f"Admin: Bulk import completed - {results['successful']} added, "
                f"{results['skipped']} skipped, {results['failed']} failed"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error in bulk import: {e}")
            results['errors'].append({
                'error': 'bulk_import_error',
                'message': str(e)
            })
            return results
    
    async def update_from_registry(self, request: RegistryUpdateRequest) -> Dict[str, Any]:
        """
        Update software versions from package registries.
        
        Args:
            request: Registry update request
            
        Returns:
            Dictionary with update results and new versions found
            
        Validates: Requirements 7.6
        """
        try:
            registry_type = request.registry_type.lower()
            
            if registry_type not in self.registry_apis:
                return {
                    'success': False,
                    'error': 'unsupported_registry',
                    'message': f'Registry type {registry_type} is not supported'
                }
            
            # Fetch versions from registry
            versions_data = await self._fetch_from_registry(
                registry_type, request.software_name, request.max_versions, request.include_prereleases
            )
            
            if not versions_data:
                return {
                    'success': False,
                    'error': 'no_versions_found',
                    'message': f'No versions found for {request.software_name} in {registry_type}'
                }
            
            # Convert to version add requests
            version_requests = []
            for version_data in versions_data:
                try:
                    version_req = VersionAddRequest(
                        software_name=request.software_name,
                        version=version_data['version'],
                        release_date=version_data['release_date'],
                        category=self._determine_category_from_registry(registry_type),
                        is_lts=version_data.get('is_lts', False)
                    )
                    version_requests.append(version_req)
                except Exception as e:
                    logger.warning(f"Skipping invalid version data {version_data}: {e}")
            
            if not version_requests:
                return {
                    'success': False,
                    'error': 'no_valid_versions',
                    'message': 'No valid versions found after processing registry data'
                }
            
            # Bulk import the versions
            bulk_request = BulkVersionImportRequest(versions=version_requests)
            import_result = await self.bulk_import_versions(bulk_request)
            
            return {
                'success': True,
                'registry': registry_type,
                'software_name': request.software_name,
                'versions_found': len(versions_data),
                'import_result': import_result
            }
            
        except Exception as e:
            logger.error(f"Error updating from registry {request.registry_type}: {e}")
            return {
                'success': False,
                'error': 'registry_update_error',
                'message': str(e)
            }
    
    async def _fetch_from_registry(self, registry_type: str, software_name: str, 
                                 max_versions: int, include_prereleases: bool) -> List[Dict[str, Any]]:
        """
        Fetch version data from a specific package registry.
        
        Args:
            registry_type: Type of registry (npm, pypi, etc.)
            software_name: Name of the software package
            max_versions: Maximum number of versions to fetch
            include_prereleases: Whether to include prerelease versions
            
        Returns:
            List of version data dictionaries
        """
        try:
            if registry_type == 'npm':
                return await self._fetch_from_npm(software_name, max_versions, include_prereleases)
            elif registry_type == 'pypi':
                return await self._fetch_from_pypi(software_name, max_versions, include_prereleases)
            elif registry_type == 'maven':
                return await self._fetch_from_maven(software_name, max_versions, include_prereleases)
            elif registry_type == 'nuget':
                return await self._fetch_from_nuget(software_name, max_versions, include_prereleases)
            elif registry_type == 'rubygems':
                return await self._fetch_from_rubygems(software_name, max_versions, include_prereleases)
            elif registry_type == 'crates':
                return await self._fetch_from_crates(software_name, max_versions, include_prereleases)
            else:
                logger.warning(f"Unsupported registry type: {registry_type}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching from {registry_type} registry: {e}")
            return []
    
    async def _fetch_from_npm(self, package_name: str, max_versions: int, include_prereleases: bool) -> List[Dict[str, Any]]:
        """Fetch versions from npm registry."""
        try:
            url = f"{self.registry_apis['npm']}/{package_name}"
            response = await self.http_client.get(url)
            response.raise_for_status()
            
            data = response.json()
            versions = []
            
            # Get version data from the versions object
            version_data = data.get('versions', {})
            time_data = data.get('time', {})
            
            for version, version_info in version_data.items():
                # Skip prereleases if not requested
                if not include_prereleases and self._is_prerelease(version):
                    continue
                
                # Get release date from time data
                release_date_str = time_data.get(version)
                if not release_date_str:
                    continue
                
                try:
                    release_date = datetime.fromisoformat(release_date_str.replace('Z', '+00:00')).date()
                    versions.append({
                        'version': version,
                        'release_date': release_date,
                        'is_lts': version_info.get('lts', False)
                    })
                except Exception as e:
                    logger.warning(f"Error parsing date for npm {package_name} {version}: {e}")
            
            # Sort by release date (newest first) and limit
            versions.sort(key=lambda x: x['release_date'], reverse=True)
            return versions[:max_versions]
            
        except Exception as e:
            logger.error(f"Error fetching npm data for {package_name}: {e}")
            return []
    
    async def _fetch_from_pypi(self, package_name: str, max_versions: int, include_prereleases: bool) -> List[Dict[str, Any]]:
        """Fetch versions from PyPI registry."""
        try:
            url = f"{self.registry_apis['pypi']}/{package_name}/json"
            response = await self.http_client.get(url)
            response.raise_for_status()
            
            data = response.json()
            versions = []
            
            # Get releases data
            releases = data.get('releases', {})
            
            for version, release_files in releases.items():
                # Skip prereleases if not requested
                if not include_prereleases and self._is_prerelease(version):
                    continue
                
                # Skip if no release files
                if not release_files:
                    continue
                
                # Get the earliest upload date from release files
                upload_dates = []
                for file_info in release_files:
                    upload_time = file_info.get('upload_time')
                    if upload_time:
                        try:
                            upload_date = datetime.fromisoformat(upload_time.replace('Z', '+00:00')).date()
                            upload_dates.append(upload_date)
                        except Exception:
                            continue
                
                if upload_dates:
                    versions.append({
                        'version': version,
                        'release_date': min(upload_dates),  # Use earliest upload date
                        'is_lts': False  # PyPI doesn't have LTS concept
                    })
            
            # Sort by release date (newest first) and limit
            versions.sort(key=lambda x: x['release_date'], reverse=True)
            return versions[:max_versions]
            
        except Exception as e:
            logger.error(f"Error fetching PyPI data for {package_name}: {e}")
            return []
    
    async def _fetch_from_maven(self, artifact_id: str, max_versions: int, include_prereleases: bool) -> List[Dict[str, Any]]:
        """Fetch versions from Maven Central registry."""
        try:
            # Maven search requires group:artifact format, but we'll try with just artifact
            url = f"{self.registry_apis['maven']}?q=a:{artifact_id}&rows={max_versions}&wt=json"
            response = await self.http_client.get(url)
            response.raise_for_status()
            
            data = response.json()
            versions = []
            
            docs = data.get('response', {}).get('docs', [])
            
            for doc in docs:
                version = doc.get('latestVersion')
                timestamp = doc.get('timestamp')
                
                if not version or not timestamp:
                    continue
                
                # Skip prereleases if not requested
                if not include_prereleases and self._is_prerelease(version):
                    continue
                
                try:
                    # Convert timestamp to date
                    release_date = datetime.fromtimestamp(timestamp / 1000).date()
                    versions.append({
                        'version': version,
                        'release_date': release_date,
                        'is_lts': False
                    })
                except Exception as e:
                    logger.warning(f"Error parsing Maven timestamp for {artifact_id} {version}: {e}")
            
            return versions[:max_versions]
            
        except Exception as e:
            logger.error(f"Error fetching Maven data for {artifact_id}: {e}")
            return []
    
    async def _fetch_from_nuget(self, package_name: str, max_versions: int, include_prereleases: bool) -> List[Dict[str, Any]]:
        """Fetch versions from NuGet registry."""
        try:
            # NuGet API requires lowercase package names
            package_name_lower = package_name.lower()
            url = f"{self.registry_apis['nuget']}/{package_name_lower}/index.json"
            response = await self.http_client.get(url)
            response.raise_for_status()
            
            data = response.json()
            versions = []
            
            version_list = data.get('versions', [])
            
            for version in version_list:
                # Skip prereleases if not requested
                if not include_prereleases and self._is_prerelease(version):
                    continue
                
                # NuGet doesn't provide release dates in the index, so we use today as approximation
                # In a real implementation, you'd need to fetch individual version metadata
                versions.append({
                    'version': version,
                    'release_date': date.today(),  # Placeholder - would need individual API calls
                    'is_lts': False
                })
            
            return versions[:max_versions]
            
        except Exception as e:
            logger.error(f"Error fetching NuGet data for {package_name}: {e}")
            return []
    
    async def _fetch_from_rubygems(self, gem_name: str, max_versions: int, include_prereleases: bool) -> List[Dict[str, Any]]:
        """Fetch versions from RubyGems registry."""
        try:
            url = f"{self.registry_apis['rubygems']}/{gem_name}/versions.json"
            response = await self.http_client.get(url)
            response.raise_for_status()
            
            data = response.json()
            versions = []
            
            for version_info in data:
                version = version_info.get('number')
                created_at = version_info.get('created_at')
                prerelease = version_info.get('prerelease', False)
                
                if not version or not created_at:
                    continue
                
                # Skip prereleases if not requested
                if not include_prereleases and prerelease:
                    continue
                
                try:
                    release_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).date()
                    versions.append({
                        'version': version,
                        'release_date': release_date,
                        'is_lts': False
                    })
                except Exception as e:
                    logger.warning(f"Error parsing RubyGems date for {gem_name} {version}: {e}")
            
            # Sort by release date (newest first) and limit
            versions.sort(key=lambda x: x['release_date'], reverse=True)
            return versions[:max_versions]
            
        except Exception as e:
            logger.error(f"Error fetching RubyGems data for {gem_name}: {e}")
            return []
    
    async def _fetch_from_crates(self, crate_name: str, max_versions: int, include_prereleases: bool) -> List[Dict[str, Any]]:
        """Fetch versions from Crates.io registry."""
        try:
            url = f"{self.registry_apis['crates']}/{crate_name}/versions"
            response = await self.http_client.get(url)
            response.raise_for_status()
            
            data = response.json()
            versions = []
            
            version_list = data.get('versions', [])
            
            for version_info in version_list:
                version = version_info.get('num')
                created_at = version_info.get('created_at')
                yanked = version_info.get('yanked', False)
                
                if not version or not created_at or yanked:
                    continue
                
                # Skip prereleases if not requested
                if not include_prereleases and self._is_prerelease(version):
                    continue
                
                try:
                    release_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).date()
                    versions.append({
                        'version': version,
                        'release_date': release_date,
                        'is_lts': False
                    })
                except Exception as e:
                    logger.warning(f"Error parsing Crates.io date for {crate_name} {version}: {e}")
            
            # Sort by release date (newest first) and limit
            versions.sort(key=lambda x: x['release_date'], reverse=True)
            return versions[:max_versions]
            
        except Exception as e:
            logger.error(f"Error fetching Crates.io data for {crate_name}: {e}")
            return []
    
    def _is_prerelease(self, version: str) -> bool:
        """Check if a version string indicates a prerelease."""
        prerelease_indicators = [
            'alpha', 'beta', 'rc', 'pre', 'dev', 'snapshot', 
            'nightly', 'canary', 'next', 'preview'
        ]
        version_lower = version.lower()
        return any(indicator in version_lower for indicator in prerelease_indicators)
    
    def _determine_category_from_registry(self, registry_type: str) -> ComponentCategory:
        """Determine component category based on registry type."""
        registry_categories = {
            'npm': ComponentCategory.LIBRARY,
            'pypi': ComponentCategory.LIBRARY,
            'maven': ComponentCategory.LIBRARY,
            'nuget': ComponentCategory.LIBRARY,
            'rubygems': ComponentCategory.LIBRARY,
            'crates': ComponentCategory.LIBRARY
        }
        return registry_categories.get(registry_type, ComponentCategory.LIBRARY)
    
    async def get_update_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about recent database updates and system health.
        
        Returns:
            Dictionary with update statistics and system information
        """
        try:
            # Get database statistics
            db_stats = await self.encyclopedia.get_database_stats()
            
            # Get recent additions (last 30 days)
            thirty_days_ago = date.today() - timedelta(days=30)
            
            # This would require additional database queries in a real implementation
            # For now, we'll return the basic stats
            
            return {
                'database_stats': db_stats,
                'last_updated': datetime.now().isoformat(),
                'update_capabilities': {
                    'supported_registries': list(self.registry_apis.keys()),
                    'max_bulk_import': 100,
                    'validation_enabled': True
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting update statistics: {e}")
            return {
                'error': 'statistics_error',
                'message': str(e)
            }
    
    async def close(self):
        """Close HTTP client and cleanup resources."""
        await self.http_client.aclose()


# Global admin service instance
admin_service = AdminService()