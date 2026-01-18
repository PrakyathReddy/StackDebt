"""
Property-based tests for missing version handling in Encyclopedia database.
**Feature: stackdebt, Property 17: Missing Version Handling**
"""

import pytest
import asyncio
import asyncpg
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from typing import List, Tuple, Optional
import os
from datetime import date
from unittest.mock import patch, AsyncMock
import logging

from app.encyclopedia import EncyclopediaRepository

# Database connection URL
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://stackdebt_user:stackdebt_password@localhost:5432/stackdebt_encyclopedia"
)

# Strategy for generating software names and versions that likely don't exist
non_existent_software_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    min_size=5,
    max_size=20
).filter(lambda x: x not in [
    "Python", "Node.js", "Java", "Go", "PHP", "Ruby", ".NET", "Rust",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "nginx", "Apache",
    "React", "Vue.js", "Angular", "Django", "Flask", "Express"
])

non_existent_version_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Nd", "Pc"), whitelist_characters=".-alpha-beta-rc"),
    min_size=3,
    max_size=15
).filter(lambda x: len(x.strip()) > 0 and not x.startswith('.') and not x.endswith('.'))


class TestProperty17MissingVersionHandling:
    """
    **Feature: stackdebt, Property 17: Missing Version Handling**
    **Validates: Requirements 7.5**
    
    Property: For any component version not found in the Encyclopedia, the system should 
    log the missing data and exclude it from age calculations without failing.
    """

    @pytest.fixture
    def encyclopedia_repo(self):
        """Create Encyclopedia repository instance with fresh cache."""
        repo = EncyclopediaRepository()
        repo.clear_missing_versions_cache()
        return repo

    @pytest.mark.asyncio
    async def test_property_17_missing_version_returns_none(self, encyclopedia_repo):
        """
        **Feature: stackdebt, Property 17: Missing Version Handling**
        Test that missing versions return None without crashing the system.
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.close()
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        
        # Test with obviously non-existent versions
        non_existent_cases = [
            ("NonExistentSoftware123", "999.999.999"),
            ("FakeToolXYZ", "0.0.0-nonexistent"),
            ("TestSoftwareABC", "invalid.version.format"),
            ("", "1.0.0"),  # Empty software name
            ("ValidSoftware", ""),  # Empty version
        ]
        
        for software_name, version in non_existent_cases:
            result = await encyclopedia_repo.lookup_version(software_name, version)
            
            # Property: Missing versions should return None, not crash
            assert result is None, f"Non-existent version {software_name}:{version} should return None"

    @given(non_existent_software_strategy, non_existent_version_strategy)
    @settings(max_examples=5, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much])
    @pytest.mark.asyncio
    async def test_property_17_random_missing_versions_handled(self, encyclopedia_repo, software_name, version):
        """
        **Feature: stackdebt, Property 17: Missing Version Handling**
        Property test: Any randomly generated software/version combination that doesn't exist 
        should be handled gracefully.
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.close()
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        
        # Skip empty or very short inputs
        assume(len(software_name.strip()) >= 3)
        assume(len(version.strip()) >= 3)
        assume('.' in version or '-' in version)  # Reasonable version format
        
        result = await encyclopedia_repo.lookup_version(software_name, version)
        
        # Property: Any missing version should return None without exception
        # (We can't assert it's None because it might actually exist, but it shouldn't crash)
        assert result is None or hasattr(result, 'software_name'), \
            f"Result should be None or valid VersionRelease object for {software_name}:{version}"

    @pytest.mark.asyncio
    async def test_property_17_missing_version_logging(self, encyclopedia_repo):
        """
        **Feature: stackdebt, Property 17: Missing Version Handling**
        Test that missing versions are properly logged for future database updates.
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.close()
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        
        with patch('app.encyclopedia.logger') as mock_logger:
            # Test missing version logging
            await encyclopedia_repo.lookup_version("NonExistentSoftware", "1.0.0")
            
            # Property: Missing versions should be logged
            mock_logger.warning.assert_called_once()
            log_call = mock_logger.warning.call_args[0][0]
            assert "Missing version data" in log_call
            assert "NonExistentSoftware" in log_call
            assert "1.0.0" in log_call

    @pytest.mark.asyncio
    async def test_property_17_missing_version_caching_prevents_duplicate_logs(self, encyclopedia_repo):
        """
        **Feature: stackdebt, Property 17: Missing Version Handling**
        Test that missing version logging uses caching to prevent duplicate log entries.
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.close()
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        
        with patch('app.encyclopedia.logger') as mock_logger:
            # First lookup should log
            await encyclopedia_repo.lookup_version("TestSoftware", "1.0.0")
            assert mock_logger.warning.call_count == 1
            
            # Second lookup of same version should not log (cached)
            await encyclopedia_repo.lookup_version("TestSoftware", "1.0.0")
            assert mock_logger.warning.call_count == 1
            
            # Different version should log
            await encyclopedia_repo.lookup_version("TestSoftware", "2.0.0")
            assert mock_logger.warning.call_count == 2
            
            # Different software should log
            await encyclopedia_repo.lookup_version("OtherSoftware", "1.0.0")
            assert mock_logger.warning.call_count == 3

    @given(st.lists(
        st.tuples(non_existent_software_strategy, non_existent_version_strategy),
        min_size=1,
        max_size=10,
        unique=True
    ))
    @settings(max_examples=10, deadline=15000, suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much])
    @pytest.mark.asyncio
    async def test_property_17_batch_missing_version_handling(self, encyclopedia_repo, software_versions):
        """
        **Feature: stackdebt, Property 17: Missing Version Handling**
        Property test: Batch lookups should handle missing versions gracefully.
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.close()
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        
        # Filter to reasonable inputs
        filtered_versions = []
        for software_name, version in software_versions:
            if (len(software_name.strip()) >= 3 and len(version.strip()) >= 3 and 
                ('.' in version or '-' in version)):
                filtered_versions.append((software_name, version))
        
        if not filtered_versions:
            return  # Skip if no valid versions
        
        # Take only first 5 to keep test reasonable
        test_versions = filtered_versions[:5]
        
        # Property: Batch lookup should handle missing versions without crashing
        results = await encyclopedia_repo.lookup_versions_batch(test_versions)
        
        # Should return results for all requested versions
        assert len(results) == len(test_versions)
        
        # Each result should be either None or a valid VersionRelease
        for key, result in results.items():
            assert result is None or hasattr(result, 'software_name'), \
                f"Result for {key} should be None or valid VersionRelease"

    @pytest.mark.asyncio
    async def test_property_17_missing_version_exclusion_from_calculations(self, encyclopedia_repo):
        """
        **Feature: stackdebt, Property 17: Missing Version Handling**
        Test that missing versions are excluded from age calculations without breaking the process.
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.close()
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        
        # Mix of existing and non-existing versions
        mixed_versions = [
            ("Python", "3.9.0"),  # Likely exists
            ("NonExistentSoftware", "1.0.0"),  # Definitely doesn't exist
            ("Node.js", "16.0.0"),  # Likely exists
            ("FakeTool", "2.0.0"),  # Definitely doesn't exist
        ]
        
        results = await encyclopedia_repo.lookup_versions_batch(mixed_versions)
        
        # Property: System should handle mixed results gracefully
        existing_results = [r for r in results.values() if r is not None]
        missing_results = [r for r in results.values() if r is None]
        
        # Should have some missing results (our fake ones)
        assert len(missing_results) >= 2, "Should have missing results for fake software"
        
        # Existing results should be valid
        for result in existing_results:
            assert hasattr(result, 'software_name')
            assert hasattr(result, 'version')
            assert hasattr(result, 'release_date')
            assert hasattr(result, 'category')

    @pytest.mark.asyncio
    async def test_property_17_database_error_handling(self, encyclopedia_repo):
        """
        **Feature: stackdebt, Property 17: Missing Version Handling**
        Test that database errors are handled gracefully and don't crash the system.
        """
        # Mock database connection to simulate errors
        with patch('app.encyclopedia.get_db_connection') as mock_get_conn:
            # Simulate database connection error
            mock_get_conn.side_effect = Exception("Database connection failed")
            
            result = await encyclopedia_repo.lookup_version("TestSoftware", "1.0.0")
            
            # Property: Database errors should return None, not crash
            assert result is None, "Database errors should return None gracefully"

    @pytest.mark.asyncio
    async def test_property_17_concurrent_missing_version_handling(self, encyclopedia_repo):
        """
        **Feature: stackdebt, Property 17: Missing Version Handling**
        Test that concurrent lookups of missing versions are handled correctly.
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.close()
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        
        # Create multiple concurrent lookups of non-existent versions
        non_existent_versions = [
            ("ConcurrentTest1", "1.0.0"),
            ("ConcurrentTest2", "1.0.0"),
            ("ConcurrentTest3", "1.0.0"),
            ("ConcurrentTest4", "1.0.0"),
            ("ConcurrentTest5", "1.0.0"),
        ]
        
        # Run concurrent lookups
        tasks = [
            encyclopedia_repo.lookup_version(software, version)
            for software, version in non_existent_versions
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Property: All concurrent lookups should complete without exceptions
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), \
                f"Concurrent lookup {i} should not raise exception: {result}"
            assert result is None, f"Non-existent version should return None: {non_existent_versions[i]}"

    @pytest.mark.asyncio
    async def test_property_17_missing_version_metadata_preservation(self, encyclopedia_repo):
        """
        **Feature: stackdebt, Property 17: Missing Version Handling**
        Test that missing version information is preserved for analysis metadata.
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.close()
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        
        # Test that we can track which versions were missing
        test_versions = [
            ("ExistingSoftware", "1.0.0"),  # May or may not exist
            ("DefinitelyMissingSoftware", "999.0.0"),  # Definitely missing
        ]
        
        results = await encyclopedia_repo.lookup_versions_batch(test_versions)
        
        # Property: We should be able to identify which versions were missing
        missing_versions = []
        found_versions = []
        
        for (software, version), result in results.items():
            if result is None:
                missing_versions.append((software, version))
            else:
                found_versions.append((software, version))
        
        # Should have at least one missing version (our fake one)
        assert len(missing_versions) >= 1, "Should identify missing versions"
        assert ("DefinitelyMissingSoftware", "999.0.0") in missing_versions, \
            "Should identify obviously missing version"


# Synchronous wrapper for running async tests
def run_async_test(coro):
    """Helper to run async tests in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


if __name__ == "__main__":
    # Run tests directly for development
    test_instance = TestProperty17MissingVersionHandling()
    repo = EncyclopediaRepository()
    
    print("Running Property 17: Missing Version Handling tests...")
    
    try:
        run_async_test(test_instance.test_property_17_missing_version_returns_none(repo))
        print("✅ Missing version returns None test passed")
        
        run_async_test(test_instance.test_property_17_missing_version_logging(repo))
        print("✅ Missing version logging test passed")
        
        run_async_test(test_instance.test_property_17_missing_version_caching_prevents_duplicate_logs(repo))
        print("✅ Missing version caching test passed")
        
        run_async_test(test_instance.test_property_17_missing_version_exclusion_from_calculations(repo))
        print("✅ Missing version exclusion test passed")
        
        run_async_test(test_instance.test_property_17_database_error_handling(repo))
        print("✅ Database error handling test passed")
        
        run_async_test(test_instance.test_property_17_concurrent_missing_version_handling(repo))
        print("✅ Concurrent missing version handling test passed")
        
        print("\n🎉 All Property 17 tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        exit(1)