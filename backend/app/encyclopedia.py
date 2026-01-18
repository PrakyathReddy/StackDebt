"""
Encyclopedia database service for StackDebt version lookups.

This module provides the EncyclopediaRepository class for querying software version
release dates and handling missing data scenarios.
"""

import asyncio
import logging
import os
from datetime import date, datetime
from typing import List, Optional, Dict, Any, Tuple
import asyncpg
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc

from app.database import get_db_connection, SessionLocal
from app.models import VersionRelease, ComponentCategory
from app.schemas import Component, RiskLevel

logger = logging.getLogger(__name__)

# Database connection URL
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://stackdebt_user:stackdebt_password@localhost:5432/stackdebt_encyclopedia"
)


class EncyclopediaRepository:
    """
    Repository class for Encyclopedia database operations.
    
    Handles version lookups, missing data logging, and database performance optimization
    for the StackDebt carbon dating system.
    """

    def __init__(self):
        """Initialize the Encyclopedia repository."""
        self.missing_versions_cache = set()  # Cache for missing versions to avoid repeated logs
        
    async def lookup_version(self, software_name: str, version: str) -> Optional[VersionRelease]:
        """
        Look up a specific software version in the Encyclopedia database.
        
        Args:
            software_name: Name of the software (e.g., "Python", "nginx")
            version: Version string (e.g., "3.9.0", "1.18.0")
            
        Returns:
            VersionRelease object if found, None if not found
            
        Validates: Requirements 2.7, 7.5
        """
        # Import here to avoid circular imports
        from app.performance_monitor import track_database_query
        
        try:
            from app.performance_monitor import performance_monitor
            async with performance_monitor.track_operation("database_query", {"operation": "single_version_lookup", "software": software_name}):
                conn = await asyncpg.connect(DATABASE_URL)
                try:
                    query = """
                        SELECT id, software_name, version, release_date, end_of_life_date, 
                               category, is_lts, created_at, updated_at
                        FROM version_releases 
                        WHERE software_name = $1 AND version = $2
                        LIMIT 1
                    """
                    
                    result = await conn.fetchrow(query, software_name, version)
                    
                    if result:
                        return VersionRelease(
                            id=result['id'],
                            software_name=result['software_name'],
                            version=result['version'],
                            release_date=result['release_date'],
                            end_of_life_date=result['end_of_life_date'],
                            category=ComponentCategory(result['category']),
                            is_lts=result['is_lts'],
                            created_at=result['created_at'],
                            updated_at=result['updated_at']
                        )
                    else:
                        # Log missing version for future database updates
                        await self._log_missing_version(software_name, version)
                        return None
                finally:
                    await conn.close()
                        
        except Exception as e:
            logger.error(f"Error looking up version {software_name} {version}: {e}")
            return None

    async def lookup_versions_batch(self, software_versions: List[Tuple[str, str]]) -> Dict[Tuple[str, str], Optional[VersionRelease]]:
        """
        Look up multiple software versions in a single database query for performance.
        
        Args:
            software_versions: List of (software_name, version) tuples
            
        Returns:
            Dictionary mapping (software_name, version) to VersionRelease or None
            
        Validates: Requirements 2.7, 8.1, 8.2
        """
        if not software_versions:
            return {}
        
        # Import here to avoid circular imports
        from app.performance_monitor import track_database_query
        
        results = {}
        
        try:
            from app.performance_monitor import performance_monitor
            async with performance_monitor.track_operation("database_query", {"operation": "batch_version_lookup", "count": len(software_versions)}):
                conn = await asyncpg.connect(DATABASE_URL)
                try:
                    # Build parameterized query for batch lookup
                    placeholders = []
                    params = []
                    for i, (software_name, version) in enumerate(software_versions):
                        placeholders.append(f"(${i*2+1}, ${i*2+2})")
                        params.extend([software_name, version])
                    
                    query = f"""
                        SELECT software_name, version, id, release_date, end_of_life_date, 
                               category, is_lts, created_at, updated_at
                        FROM version_releases 
                        WHERE (software_name, version) IN ({', '.join(placeholders)})
                    """
                    
                    db_results = await conn.fetch(query, *params)
                    
                    # Create lookup dictionary from database results
                    found_versions = {}
                    for row in db_results:
                        key = (row['software_name'], row['version'])
                        found_versions[key] = VersionRelease(
                            id=row['id'],
                            software_name=row['software_name'],
                            version=row['version'],
                            release_date=row['release_date'],
                            end_of_life_date=row['end_of_life_date'],
                            category=ComponentCategory(row['category']),
                            is_lts=row['is_lts'],
                            created_at=row['created_at'],
                            updated_at=row['updated_at']
                        )
                    
                    # Build complete results dictionary, logging missing versions
                    for software_name, version in software_versions:
                        key = (software_name, version)
                        if key in found_versions:
                            results[key] = found_versions[key]
                        else:
                            results[key] = None
                            await self._log_missing_version(software_name, version)
                finally:
                    await conn.close()
                            
        except Exception as e:
            logger.error(f"Error in batch version lookup: {e}")
            # Return None for all requested versions on error
            for software_name, version in software_versions:
                results[(software_name, version)] = None
                
        return results

    async def get_software_versions(self, software_name: str, limit: int = 50) -> List[VersionRelease]:
        """
        Get all available versions for a specific software.
        
        Args:
            software_name: Name of the software
            limit: Maximum number of versions to return (default 50)
            
        Returns:
            List of VersionRelease objects ordered by release date (newest first)
            
        Validates: Requirements 7.1, 7.2, 7.3, 7.4
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            try:
                query = """
                    SELECT id, software_name, version, release_date, end_of_life_date, 
                           category, is_lts, created_at, updated_at
                    FROM version_releases 
                    WHERE software_name = $1
                    ORDER BY release_date DESC
                    LIMIT $2
                """
                
                results = await conn.fetch(query, software_name, limit)
                
                return [
                    VersionRelease(
                        id=row['id'],
                        software_name=row['software_name'],
                        version=row['version'],
                        release_date=row['release_date'],
                        end_of_life_date=row['end_of_life_date'],
                        category=ComponentCategory(row['category']),
                        is_lts=row['is_lts'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at']
                    )
                    for row in results
                ]
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"Error getting versions for {software_name}: {e}")
            return []

    async def get_software_by_category(self, category: ComponentCategory, limit: int = 100) -> List[str]:
        """
        Get list of software names in a specific category.
        
        Args:
            category: Component category to filter by
            limit: Maximum number of software names to return
            
        Returns:
            List of unique software names in the category
            
        Validates: Requirements 7.1, 7.2, 7.3, 7.4
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            try:
                query = """
                    SELECT DISTINCT software_name
                    FROM version_releases 
                    WHERE category = $1
                    ORDER BY software_name
                    LIMIT $2
                """
                
                # Handle both enum and string inputs
                category_value = category.value if hasattr(category, 'value') else str(category)
                results = await conn.fetch(query, category_value, limit)
                return [row['software_name'] for row in results]
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"Error getting software for category {category}: {e}")
            return []

    async def search_software(self, search_term: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for software by name (case-insensitive partial matching).
        
        Args:
            search_term: Term to search for in software names
            limit: Maximum number of results to return
            
        Returns:
            List of dictionaries with software info (name, category, version_count)
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            try:
                query = """
                    SELECT software_name, category, COUNT(*) as version_count,
                           MAX(release_date) as latest_release
                    FROM version_releases 
                    WHERE software_name ILIKE $1
                    GROUP BY software_name, category
                    ORDER BY software_name
                    LIMIT $2
                """
                
                search_pattern = f"%{search_term}%"
                results = await conn.fetch(query, search_pattern, limit)
                
                return [
                    {
                        'software_name': row['software_name'],
                        'category': row['category'],
                        'version_count': row['version_count'],
                        'latest_release': row['latest_release']
                    }
                    for row in results
                ]
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"Error searching software with term '{search_term}': {e}")
            return []

    async def add_version(self, software_name: str, version: str, release_date: date, 
                         category: ComponentCategory, end_of_life_date: Optional[date] = None,
                         is_lts: bool = False) -> bool:
        """
        Add a new software version to the Encyclopedia database.
        
        Args:
            software_name: Name of the software
            version: Version string
            release_date: Date when this version was released
            category: Component category
            end_of_life_date: Optional end of life date
            is_lts: Whether this is a Long Term Support version
            
        Returns:
            True if successfully added, False otherwise
            
        Validates: Requirements 7.6
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            try:
                query = """
                    INSERT INTO version_releases 
                    (software_name, version, release_date, end_of_life_date, category, is_lts)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (software_name, version) DO NOTHING
                    RETURNING id
                """
                
                result = await conn.fetchrow(
                    query, software_name, version, release_date, 
                    end_of_life_date, category.value, is_lts
                )
                
                if result:
                    logger.info(f"Added version: {software_name} {version}")
                    return True
                else:
                    logger.warning(f"Version already exists: {software_name} {version}")
                    return False
            finally:
                await conn.close()
                    
        except Exception as e:
            logger.error(f"Error adding version {software_name} {version}: {e}")
            return False

    async def get_database_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the Encyclopedia database content.
        
        Returns:
            Dictionary with database statistics
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            try:
                stats_query = """
                    SELECT 
                        COUNT(*) as total_versions,
                        COUNT(DISTINCT software_name) as total_software,
                        COUNT(DISTINCT category) as total_categories,
                        MIN(release_date) as oldest_release,
                        MAX(release_date) as newest_release
                    FROM version_releases
                """
                
                category_query = """
                    SELECT category, COUNT(*) as count
                    FROM version_releases
                    GROUP BY category
                    ORDER BY count DESC
                """
                
                stats_result = await conn.fetchrow(stats_query)
                category_results = await conn.fetch(category_query)
                
                return {
                    'total_versions': stats_result['total_versions'],
                    'total_software': stats_result['total_software'],
                    'total_categories': stats_result['total_categories'],
                    'oldest_release': stats_result['oldest_release'],
                    'newest_release': stats_result['newest_release'],
                    'versions_by_category': {
                        row['category']: row['count'] 
                        for row in category_results
                    }
                }
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}

    async def _log_missing_version(self, software_name: str, version: str) -> None:
        """
        Log missing version for future database updates.
        
        Uses caching to avoid duplicate log entries for the same missing version.
        
        Args:
            software_name: Name of the software
            version: Version string that was not found
            
        Validates: Requirements 7.5
        """
        cache_key = f"{software_name}:{version}"
        
        if cache_key not in self.missing_versions_cache:
            self.missing_versions_cache.add(cache_key)
            logger.warning(
                f"Missing version data: {software_name} {version} - "
                f"Consider adding to Encyclopedia database for future analyses"
            )

    def clear_missing_versions_cache(self) -> None:
        """Clear the missing versions cache (useful for testing)."""
        self.missing_versions_cache.clear()


# Global repository instance
encyclopedia_repo = EncyclopediaRepository()


# Convenience functions for common operations
async def lookup_version(software_name: str, version: str) -> Optional[VersionRelease]:
    """Convenience function for single version lookup."""
    return await encyclopedia_repo.lookup_version(software_name, version)


async def lookup_versions_batch(software_versions: List[Tuple[str, str]]) -> Dict[Tuple[str, str], Optional[VersionRelease]]:
    """Convenience function for batch version lookup."""
    return await encyclopedia_repo.lookup_versions_batch(software_versions)


async def get_software_versions(software_name: str, limit: int = 50) -> List[VersionRelease]:
    """Convenience function for getting all versions of software."""
    return await encyclopedia_repo.get_software_versions(software_name, limit)


async def add_version(software_name: str, version: str, release_date: date, 
                     category: ComponentCategory, end_of_life_date: Optional[date] = None,
                     is_lts: bool = False) -> bool:
    """Convenience function for adding a new version."""
    return await encyclopedia_repo.add_version(
        software_name, version, release_date, category, end_of_life_date, is_lts
    )