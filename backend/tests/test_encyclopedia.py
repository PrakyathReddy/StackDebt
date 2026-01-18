"""
Unit tests for Encyclopedia database service.

Tests the EncyclopediaRepository class functionality including version lookups,
batch operations, missing data handling, and database performance.
"""

import pytest
import asyncio
from datetime import date
from unittest.mock import AsyncMock, patch, MagicMock
from typing import List, Dict, Tuple, Optional

from app.encyclopedia import EncyclopediaRepository, encyclopedia_repo
from app.models import VersionRelease, ComponentCategory
from app.schemas import Component, RiskLevel


class TestEncyclopediaRepository:
    """Unit tests for EncyclopediaRepository class."""

    @pytest.fixture
    def repo(self):
        """Create a fresh repository instance for each test."""
        return EncyclopediaRepository()

    @pytest.fixture
    def sample_version_release(self):
        """Sample VersionRelease object for testing."""
        return VersionRelease(
            id=1,
            software_name="Python",
            version="3.9.0",
            release_date=date(2020, 10, 5),
            end_of_life_date=date(2025, 10, 5),
            category=ComponentCategory.PROGRAMMING_LANGUAGE,
            is_lts=False,
            created_at=None,
            updated_at=None
        )

    @pytest.mark.asyncio
    async def test_lookup_version_found(self, repo, sample_version_release):
        """Test successful version lookup."""
        mock_row = {
            'id': 1,
            'software_name': 'Python',
            'version': '3.9.0',
            'release_date': date(2020, 10, 5),
            'end_of_life_date': date(2025, 10, 5),
            'category': 'programming_language',
            'is_lts': False,
            'created_at': None,
            'updated_at': None
        }
        
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchrow.return_value = mock_row
            mock_connect.return_value = mock_conn
            
            result = await repo.lookup_version("Python", "3.9.0")
            
            assert result is not None
            assert result.software_name == "Python"
            assert result.version == "3.9.0"
            assert result.category == ComponentCategory.PROGRAMMING_LANGUAGE
            mock_conn.fetchrow.assert_called_once()
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_lookup_version_not_found(self, repo):
        """Test version lookup when version is not found."""
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchrow.return_value = None
            mock_connect.return_value = mock_conn
            
            with patch.object(repo, '_log_missing_version') as mock_log:
                result = await repo.lookup_version("UnknownSoftware", "1.0.0")
                
                assert result is None
                mock_log.assert_called_once_with("UnknownSoftware", "1.0.0")
                mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_lookup_version_database_error(self, repo):
        """Test version lookup when database error occurs."""
        with patch('app.encyclopedia.get_db_connection') as mock_get_conn:
            mock_get_conn.side_effect = Exception("Database connection failed")
            
            result = await repo.lookup_version("Python", "3.9.0")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_lookup_versions_batch_success(self, repo):
        """Test successful batch version lookup."""
        software_versions = [("Python", "3.9.0"), ("Node.js", "16.0.0")]
        
        mock_rows = [
            {
                'software_name': 'Python',
                'version': '3.9.0',
                'id': 1,
                'release_date': date(2020, 10, 5),
                'end_of_life_date': date(2025, 10, 5),
                'category': 'programming_language',
                'is_lts': False,
                'created_at': None,
                'updated_at': None
            }
        ]
        
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetch.return_value = mock_rows
            mock_connect.return_value = mock_conn
            
            with patch.object(repo, '_log_missing_version') as mock_log:
                results = await repo.lookup_versions_batch(software_versions)
                
                assert len(results) == 2
                assert results[("Python", "3.9.0")] is not None
                assert results[("Node.js", "16.0.0")] is None
                mock_log.assert_called_once_with("Node.js", "16.0.0")
                mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_lookup_versions_batch_empty_input(self, repo):
        """Test batch lookup with empty input."""
        result = await repo.lookup_versions_batch([])
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_software_versions(self, repo):
        """Test getting all versions for a software."""
        mock_rows = [
            {
                'id': 1,
                'software_name': 'Python',
                'version': '3.10.0',
                'release_date': date(2021, 10, 4),
                'end_of_life_date': None,
                'category': 'programming_language',
                'is_lts': False,
                'created_at': None,
                'updated_at': None
            },
            {
                'id': 2,
                'software_name': 'Python',
                'version': '3.9.0',
                'release_date': date(2020, 10, 5),
                'end_of_life_date': date(2025, 10, 5),
                'category': 'programming_language',
                'is_lts': False,
                'created_at': None,
                'updated_at': None
            }
        ]
        
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetch.return_value = mock_rows
            mock_connect.return_value = mock_conn
            
            results = await repo.get_software_versions("Python")
            
            assert len(results) == 2
            assert results[0].version == "3.10.0"
            assert results[1].version == "3.9.0"
            mock_conn.fetch.assert_called_once()
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_software_by_category(self, repo):
        """Test getting software names by category."""
        mock_rows = [
            {'software_name': 'Python'},
            {'software_name': 'Node.js'},
            {'software_name': 'Java'}
        ]
        
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetch.return_value = mock_rows
            mock_connect.return_value = mock_conn
            
            results = await repo.get_software_by_category(ComponentCategory.PROGRAMMING_LANGUAGE)
            
            assert len(results) == 3
            assert "Python" in results
            assert "Node.js" in results
            assert "Java" in results
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_software(self, repo):
        """Test software search functionality."""
        mock_rows = [
            {
                'software_name': 'Python',
                'category': 'programming_language',
                'version_count': 5,
                'latest_release': date(2023, 10, 2)
            }
        ]
        
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetch.return_value = mock_rows
            mock_connect.return_value = mock_conn
            
            results = await repo.search_software("Py")
            
            assert len(results) == 1
            assert results[0]['software_name'] == 'Python'
            assert results[0]['version_count'] == 5
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_version_success(self, repo):
        """Test successful version addition."""
        mock_row = {'id': 123}
        
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchrow.return_value = mock_row
            mock_connect.return_value = mock_conn
            
            result = await repo.add_version(
                "NewSoftware", "1.0.0", date(2024, 1, 1), 
                ComponentCategory.LIBRARY, None, False
            )
            
            assert result is True
            mock_conn.fetchrow.assert_called_once()
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_version_already_exists(self, repo):
        """Test adding version that already exists."""
        with patch('app.encyclopedia.get_db_connection') as mock_get_conn:
            mock_conn = AsyncMock()
            mock_conn.fetchrow.return_value = None  # ON CONFLICT DO NOTHING returns None
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            result = await repo.add_version(
                "ExistingSoftware", "1.0.0", date(2024, 1, 1), 
                ComponentCategory.LIBRARY, None, False
            )
            
            assert result is False

    @pytest.mark.asyncio
    async def test_get_database_stats(self, repo):
        """Test getting database statistics."""
        mock_stats = {
            'total_versions': 100,
            'total_software': 25,
            'total_categories': 7,
            'oldest_release': date(2010, 1, 1),
            'newest_release': date(2024, 1, 1)
        }
        
        mock_categories = [
            {'category': 'programming_language', 'count': 40},
            {'category': 'framework', 'count': 30},
            {'category': 'database', 'count': 20},
            {'category': 'library', 'count': 10}
        ]
        
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchrow.return_value = mock_stats
            mock_conn.fetch.return_value = mock_categories
            mock_connect.return_value = mock_conn
            
            results = await repo.get_database_stats()
            
            assert results['total_versions'] == 100
            assert results['total_software'] == 25
            assert len(results['versions_by_category']) == 4
            assert results['versions_by_category']['programming_language'] == 40
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_missing_version_caching(self, repo):
        """Test that missing version logging uses caching to avoid duplicates."""
        with patch('app.encyclopedia.logger') as mock_logger:
            # First call should log
            await repo._log_missing_version("TestSoft", "1.0.0")
            assert mock_logger.warning.call_count == 1
            
            # Second call should not log (cached)
            await repo._log_missing_version("TestSoft", "1.0.0")
            assert mock_logger.warning.call_count == 1
            
            # Different version should log
            await repo._log_missing_version("TestSoft", "2.0.0")
            assert mock_logger.warning.call_count == 2

    def test_clear_missing_versions_cache(self, repo):
        """Test clearing the missing versions cache."""
        repo.missing_versions_cache.add("test:1.0.0")
        assert len(repo.missing_versions_cache) == 1
        
        repo.clear_missing_versions_cache()
        assert len(repo.missing_versions_cache) == 0


class TestEncyclopediaConvenienceFunctions:
    """Test the convenience functions for common operations."""

    @pytest.mark.asyncio
    async def test_lookup_version_convenience(self):
        """Test the convenience lookup_version function."""
        with patch.object(encyclopedia_repo, 'lookup_version') as mock_lookup:
            mock_lookup.return_value = None
            
            from app.encyclopedia import lookup_version
            result = await lookup_version("Python", "3.9.0")
            
            mock_lookup.assert_called_once_with("Python", "3.9.0")
            assert result is None

    @pytest.mark.asyncio
    async def test_lookup_versions_batch_convenience(self):
        """Test the convenience lookup_versions_batch function."""
        with patch.object(encyclopedia_repo, 'lookup_versions_batch') as mock_batch:
            mock_batch.return_value = {}
            
            from app.encyclopedia import lookup_versions_batch
            result = await lookup_versions_batch([("Python", "3.9.0")])
            
            mock_batch.assert_called_once_with([("Python", "3.9.0")])
            assert result == {}

    @pytest.mark.asyncio
    async def test_get_software_versions_convenience(self):
        """Test the convenience get_software_versions function."""
        with patch.object(encyclopedia_repo, 'get_software_versions') as mock_get:
            mock_get.return_value = []
            
            from app.encyclopedia import get_software_versions
            result = await get_software_versions("Python", 10)
            
            mock_get.assert_called_once_with("Python", 10)
            assert result == []

    @pytest.mark.asyncio
    async def test_add_version_convenience(self):
        """Test the convenience add_version function."""
        with patch.object(encyclopedia_repo, 'add_version') as mock_add:
            mock_add.return_value = True
            
            from app.encyclopedia import add_version
            result = await add_version(
                "Test", "1.0.0", date(2024, 1, 1), 
                ComponentCategory.LIBRARY, None, False
            )
            
            mock_add.assert_called_once_with(
                "Test", "1.0.0", date(2024, 1, 1), 
                ComponentCategory.LIBRARY, None, False
            )
            assert result is True


if __name__ == "__main__":
    # Run tests directly for development
    pytest.main([__file__, "-v"])