"""
Property-based tests for database update capability in Encyclopedia database.
**Feature: stackdebt, Property 18: Database Update Capability**
"""

import pytest
import asyncio
import asyncpg
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from typing import List, Tuple, Optional
import os
from datetime import date, datetime, timedelta
from unittest.mock import patch, AsyncMock
import logging

from app.encyclopedia import EncyclopediaRepository, add_version
from app.models import ComponentCategory, VersionRelease

# Database connection URL
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://stackdebt_user:stackdebt_password@localhost:5432/stackdebt_encyclopedia"
)

# Strategy for generating valid software names
software_names_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters=" .-"),
    min_size=3,
    max_size=30
).filter(lambda x: len(x.strip()) > 2 and not x.startswith('.') and not x.endswith('.'))

# Strategy for generating valid version strings
version_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Nd", "Pc"), whitelist_characters=".-alpha-beta-rc"),
    min_size=1,
    max_size=20
).filter(lambda x: len(x.strip()) > 0 and not x.startswith('.') and not x.endswith('.') and '.' in x)

# Strategy for generating valid release dates (not in the future)
release_date_strategy = st.dates(
    min_value=date(1970, 1, 1),
    max_value=date.today()
)

# Strategy for generating optional end of life dates
eol_date_strategy = st.one_of(
    st.none(),
    st.dates(min_value=date(1970, 1, 1), max_value=date.today() + timedelta(days=3650))  # Up to 10 years in future
)

# Strategy for component categories
category_strategy = st.sampled_from(list(ComponentCategory))


class TestProperty18DatabaseUpdateCapability:
    """
    **Feature: stackdebt, Property 18: Database Update Capability**
    **Validates: Requirements 7.6**
    
    Property: For any new software release data, the Encyclopedia should support 
    adding it to the database for future analyses.
    """

    @pytest.fixture
    def encyclopedia_repo(self):
        """Create Encyclopedia repository instance."""
        return EncyclopediaRepository()

    @pytest.mark.asyncio
    async def test_property_18_add_new_version_success(self, encyclopedia_repo):
        """
        **Feature: stackdebt, Property 18: Database Update Capability**
        Test that new software versions can be successfully added to the database.
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.close()
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        
        # Generate unique test data to avoid conflicts
        test_software = f"TestSoftware_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        test_version = "1.0.0"
        test_release_date = date(2023, 1, 15)
        test_category = ComponentCategory.LIBRARY
        
        # Property: New versions should be addable to the database
        result = await encyclopedia_repo.add_version(
            software_name=test_software,
            version=test_version,
            release_date=test_release_date,
            category=test_category,
            is_lts=False
        )
        
        assert result is True, f"Adding new version {test_software} {test_version} should succeed"
        
        # Verify the version was actually added and can be retrieved
        retrieved_version = await encyclopedia_repo.lookup_version(test_software, test_version)
        
        assert retrieved_version is not None, "Added version should be retrievable"
        assert retrieved_version.software_name == test_software
        assert retrieved_version.version == test_version
        assert retrieved_version.release_date == test_release_date
        assert retrieved_version.category == test_category
        assert retrieved_version.is_lts is False
        
        # Clean up test data
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.execute(
                "DELETE FROM version_releases WHERE software_name = $1 AND version = $2",
                test_software, test_version
            )
            await conn.close()
        except Exception as e:
            logging.warning(f"Failed to clean up test data: {e}")

    @given(
        software_names_strategy,
        version_strategy,
        release_date_strategy,
        category_strategy,
        st.booleans()
    )
    @settings(max_examples=5, deadline=30000, suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much])
    @pytest.mark.asyncio
    async def test_property_18_add_version_with_random_data(self, encyclopedia_repo, software_name, version, release_date, category, is_lts):
        """
        **Feature: stackdebt, Property 18: Database Update Capability**
        Property test: Any valid software release data should be addable to the database.
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.close()
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        
        # Filter inputs to reasonable values
        assume(len(software_name.strip()) >= 3)
        assume(len(version.strip()) >= 3)
        assume(release_date <= date.today())  # No future dates
        
        # Make software name unique to avoid conflicts
        unique_software_name = f"{software_name.strip()}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Property: Valid software release data should be addable
        result = await encyclopedia_repo.add_version(
            software_name=unique_software_name,
            version=version,
            release_date=release_date,
            category=category,
            is_lts=is_lts
        )
        
        # Should succeed for valid data
        assert result is True, f"Adding valid version data should succeed: {unique_software_name} {version}"
        
        # Verify the data was stored correctly
        retrieved = await encyclopedia_repo.lookup_version(unique_software_name, version)
        assert retrieved is not None, "Added version should be retrievable"
        assert retrieved.software_name == unique_software_name
        assert retrieved.version == version
        assert retrieved.release_date == release_date
        assert retrieved.category == category
        assert retrieved.is_lts == is_lts
        
        # Clean up
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.execute(
                "DELETE FROM version_releases WHERE software_name = $1 AND version = $2",
                unique_software_name, version
            )
            await conn.close()
        except Exception as e:
            logging.warning(f"Failed to clean up test data: {e}")

    @pytest.mark.asyncio
    async def test_property_18_add_version_with_eol_date(self, encyclopedia_repo):
        """
        **Feature: stackdebt, Property 18: Database Update Capability**
        Test that versions with end-of-life dates can be added successfully.
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.close()
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        
        # Test data with EOL date
        test_software = f"EOLTestSoftware_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        test_version = "2.0.0"
        test_release_date = date(2020, 1, 1)
        test_eol_date = date(2023, 1, 1)
        test_category = ComponentCategory.PROGRAMMING_LANGUAGE
        
        # Property: Versions with EOL dates should be addable
        result = await encyclopedia_repo.add_version(
            software_name=test_software,
            version=test_version,
            release_date=test_release_date,
            category=test_category,
            end_of_life_date=test_eol_date,
            is_lts=True
        )
        
        assert result is True, "Adding version with EOL date should succeed"
        
        # Verify EOL date was stored correctly
        retrieved = await encyclopedia_repo.lookup_version(test_software, test_version)
        assert retrieved is not None
        assert retrieved.end_of_life_date == test_eol_date
        assert retrieved.is_lts is True
        
        # Clean up
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.execute(
                "DELETE FROM version_releases WHERE software_name = $1 AND version = $2",
                test_software, test_version
            )
            await conn.close()
        except Exception as e:
            logging.warning(f"Failed to clean up test data: {e}")

    @pytest.mark.asyncio
    async def test_property_18_duplicate_version_handling(self, encyclopedia_repo):
        """
        **Feature: stackdebt, Property 18: Database Update Capability**
        Test that duplicate versions are handled gracefully (no crash, appropriate response).
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.close()
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        
        # Test data
        test_software = f"DuplicateTestSoftware_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        test_version = "1.0.0"
        test_release_date = date(2023, 6, 1)
        test_category = ComponentCategory.FRAMEWORK
        
        # Add version first time
        result1 = await encyclopedia_repo.add_version(
            software_name=test_software,
            version=test_version,
            release_date=test_release_date,
            category=test_category
        )
        
        assert result1 is True, "First addition should succeed"
        
        # Property: Adding duplicate version should not crash and should return False
        result2 = await encyclopedia_repo.add_version(
            software_name=test_software,
            version=test_version,
            release_date=test_release_date,
            category=test_category
        )
        
        assert result2 is False, "Duplicate version addition should return False"
        
        # Verify only one record exists
        retrieved = await encyclopedia_repo.lookup_version(test_software, test_version)
        assert retrieved is not None, "Version should still be retrievable"
        
        # Clean up
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.execute(
                "DELETE FROM version_releases WHERE software_name = $1 AND version = $2",
                test_software, test_version
            )
            await conn.close()
        except Exception as e:
            logging.warning(f"Failed to clean up test data: {e}")

    @pytest.mark.asyncio
    async def test_property_18_batch_version_addition(self, encyclopedia_repo):
        """
        **Feature: stackdebt, Property 18: Database Update Capability**
        Test that multiple versions can be added for the same software.
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.close()
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        
        # Test data - multiple versions of same software
        test_software = f"BatchTestSoftware_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        test_versions = [
            ("1.0.0", date(2020, 1, 1)),
            ("1.1.0", date(2020, 6, 1)),
            ("2.0.0", date(2021, 1, 1)),
            ("2.1.0", date(2021, 6, 1)),
            ("3.0.0", date(2022, 1, 1)),
        ]
        test_category = ComponentCategory.DATABASE
        
        # Property: Multiple versions of same software should be addable
        added_versions = []
        for version, release_date in test_versions:
            result = await encyclopedia_repo.add_version(
                software_name=test_software,
                version=version,
                release_date=release_date,
                category=test_category
            )
            assert result is True, f"Adding version {version} should succeed"
            added_versions.append(version)
        
        # Verify all versions are retrievable
        for version, expected_date in test_versions:
            retrieved = await encyclopedia_repo.lookup_version(test_software, version)
            assert retrieved is not None, f"Version {version} should be retrievable"
            assert retrieved.release_date == expected_date
        
        # Verify get_software_versions returns all versions
        all_versions = await encyclopedia_repo.get_software_versions(test_software)
        assert len(all_versions) == len(test_versions), "Should retrieve all added versions"
        
        # Verify versions are ordered by release date (newest first)
        for i in range(len(all_versions) - 1):
            assert all_versions[i].release_date >= all_versions[i + 1].release_date, \
                "Versions should be ordered by release date (newest first)"
        
        # Clean up
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            for version, _ in test_versions:
                await conn.execute(
                    "DELETE FROM version_releases WHERE software_name = $1 AND version = $2",
                    test_software, version
                )
            await conn.close()
        except Exception as e:
            logging.warning(f"Failed to clean up test data: {e}")

    @pytest.mark.asyncio
    async def test_property_18_added_versions_available_for_analysis(self, encyclopedia_repo):
        """
        **Feature: stackdebt, Property 18: Database Update Capability**
        Test that newly added versions are immediately available for future analyses.
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.close()
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        
        # Test data
        test_software = f"AnalysisTestSoftware_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        test_version = "1.5.0"
        test_release_date = date(2023, 3, 15)
        test_category = ComponentCategory.WEB_SERVER
        
        # Verify version doesn't exist initially
        initial_lookup = await encyclopedia_repo.lookup_version(test_software, test_version)
        assert initial_lookup is None, "Version should not exist initially"
        
        # Add the version
        add_result = await encyclopedia_repo.add_version(
            software_name=test_software,
            version=test_version,
            release_date=test_release_date,
            category=test_category
        )
        
        assert add_result is True, "Version addition should succeed"
        
        # Property: Newly added version should be immediately available for analysis
        immediate_lookup = await encyclopedia_repo.lookup_version(test_software, test_version)
        assert immediate_lookup is not None, "Newly added version should be immediately retrievable"
        
        # Test batch lookup includes the new version
        batch_results = await encyclopedia_repo.lookup_versions_batch([(test_software, test_version)])
        assert (test_software, test_version) in batch_results
        assert batch_results[(test_software, test_version)] is not None
        
        # Test search functionality finds the new software
        search_results = await encyclopedia_repo.search_software(test_software[:10])
        software_names = [result['software_name'] for result in search_results]
        assert test_software in software_names, "Search should find newly added software"
        
        # Test category listing includes the new software
        category_software = await encyclopedia_repo.get_software_by_category(test_category)
        assert test_software in category_software, "Category listing should include new software"
        
        # Clean up
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.execute(
                "DELETE FROM version_releases WHERE software_name = $1 AND version = $2",
                test_software, test_version
            )
            await conn.close()
        except Exception as e:
            logging.warning(f"Failed to clean up test data: {e}")

    @pytest.mark.asyncio
    async def test_property_18_database_stats_update_after_addition(self, encyclopedia_repo):
        """
        **Feature: stackdebt, Property 18: Database Update Capability**
        Test that database statistics are updated after adding new versions.
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.close()
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        
        # Get initial stats
        initial_stats = await encyclopedia_repo.get_database_stats()
        initial_total = initial_stats.get('total_versions', 0)
        initial_software_count = initial_stats.get('total_software', 0)
        
        # Test data
        test_software = f"StatsTestSoftware_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        test_version = "1.0.0"
        test_release_date = date(2023, 8, 1)
        test_category = ComponentCategory.DEVELOPMENT_TOOL
        
        # Add new version
        add_result = await encyclopedia_repo.add_version(
            software_name=test_software,
            version=test_version,
            release_date=test_release_date,
            category=test_category
        )
        
        assert add_result is True, "Version addition should succeed"
        
        # Property: Database stats should reflect the new addition
        updated_stats = await encyclopedia_repo.get_database_stats()
        updated_total = updated_stats.get('total_versions', 0)
        updated_software_count = updated_stats.get('total_software', 0)
        
        assert updated_total == initial_total + 1, "Total versions should increase by 1"
        assert updated_software_count == initial_software_count + 1, "Total software should increase by 1"
        
        # Check category-specific stats
        category_stats = updated_stats.get('versions_by_category', {})
        category_key = test_category.value
        assert category_key in category_stats, f"Category {category_key} should be in stats"
        
        # Clean up
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.execute(
                "DELETE FROM version_releases WHERE software_name = $1 AND version = $2",
                test_software, test_version
            )
            await conn.close()
        except Exception as e:
            logging.warning(f"Failed to clean up test data: {e}")

    @pytest.mark.asyncio
    async def test_property_18_database_error_handling_during_addition(self, encyclopedia_repo):
        """
        **Feature: stackdebt, Property 18: Database Update Capability**
        Test that database errors during version addition are handled gracefully.
        """
        # Test with invalid data that should cause database errors
        invalid_test_cases = [
            # Empty software name - should be handled gracefully
            ("", "1.0.0", date(2023, 1, 1), ComponentCategory.LIBRARY),
            # Empty version - should be handled gracefully  
            ("ValidSoftware", "", date(2023, 1, 1), ComponentCategory.LIBRARY),
        ]
        
        for software_name, version, release_date, category in invalid_test_cases:
            # Property: Invalid data should not crash the system
            try:
                result = await encyclopedia_repo.add_version(
                    software_name=software_name,
                    version=version,
                    release_date=release_date,
                    category=category
                )
                # The system should handle invalid data gracefully
                # It may return True or False, but should not crash
                assert isinstance(result, bool), f"Should return boolean for invalid data: {software_name}, {version}"
            except Exception as e:
                # If an exception is raised, it should be a validation/database error, not a crash
                error_msg = str(e).lower()
                assert any(keyword in error_msg for keyword in ["validation", "constraint", "null", "empty", "invalid"]), \
                    f"Should be a validation/database error, not a crash: {e}"

    @pytest.mark.asyncio
    async def test_property_18_concurrent_version_additions(self, encyclopedia_repo):
        """
        **Feature: stackdebt, Property 18: Database Update Capability**
        Test that concurrent version additions are handled correctly.
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.close()
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        
        # Test data for concurrent additions
        base_software = f"ConcurrentTestSoftware_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        concurrent_versions = [
            (f"{base_software}_1", "1.0.0", date(2023, 1, 1), ComponentCategory.LIBRARY),
            (f"{base_software}_2", "1.0.0", date(2023, 1, 2), ComponentCategory.FRAMEWORK),
            (f"{base_software}_3", "1.0.0", date(2023, 1, 3), ComponentCategory.DATABASE),
            (f"{base_software}_4", "1.0.0", date(2023, 1, 4), ComponentCategory.WEB_SERVER),
            (f"{base_software}_5", "1.0.0", date(2023, 1, 5), ComponentCategory.DEVELOPMENT_TOOL),
        ]
        
        # Create concurrent addition tasks
        tasks = [
            encyclopedia_repo.add_version(
                software_name=software_name,
                version=version,
                release_date=release_date,
                category=category
            )
            for software_name, version, release_date, category in concurrent_versions
        ]
        
        # Property: Concurrent additions should complete without errors
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All additions should succeed
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Concurrent addition {i} should not raise exception: {result}"
            assert result is True, f"Concurrent addition {i} should succeed"
        
        # Verify all versions were added correctly
        for software_name, version, expected_date, expected_category in concurrent_versions:
            retrieved = await encyclopedia_repo.lookup_version(software_name, version)
            assert retrieved is not None, f"Concurrently added version should be retrievable: {software_name}"
            assert retrieved.release_date == expected_date
            assert retrieved.category == expected_category
        
        # Clean up
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            for software_name, version, _, _ in concurrent_versions:
                await conn.execute(
                    "DELETE FROM version_releases WHERE software_name = $1 AND version = $2",
                    software_name, version
                )
            await conn.close()
        except Exception as e:
            logging.warning(f"Failed to clean up test data: {e}")

    @pytest.mark.asyncio
    async def test_property_18_convenience_function_integration(self):
        """
        **Feature: stackdebt, Property 18: Database Update Capability**
        Test that the convenience add_version function works correctly.
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.close()
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        
        # Test data
        test_software = f"ConvenienceTestSoftware_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        test_version = "2.5.0"
        test_release_date = date(2023, 9, 15)
        test_category = ComponentCategory.PROGRAMMING_LANGUAGE
        test_eol_date = date(2026, 9, 15)
        
        # Property: Convenience function should work the same as repository method
        result = await add_version(
            software_name=test_software,
            version=test_version,
            release_date=test_release_date,
            category=test_category,
            end_of_life_date=test_eol_date,
            is_lts=True
        )
        
        assert result is True, "Convenience function should succeed"
        
        # Verify using repository lookup
        repo = EncyclopediaRepository()
        retrieved = await repo.lookup_version(test_software, test_version)
        
        assert retrieved is not None, "Version added via convenience function should be retrievable"
        assert retrieved.software_name == test_software
        assert retrieved.version == test_version
        assert retrieved.release_date == test_release_date
        assert retrieved.category == test_category
        assert retrieved.end_of_life_date == test_eol_date
        assert retrieved.is_lts is True
        
        # Clean up
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.execute(
                "DELETE FROM version_releases WHERE software_name = $1 AND version = $2",
                test_software, test_version
            )
            await conn.close()
        except Exception as e:
            logging.warning(f"Failed to clean up test data: {e}")


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
    test_instance = TestProperty18DatabaseUpdateCapability()
    repo = EncyclopediaRepository()
    
    print("Running Property 18: Database Update Capability tests...")
    
    try:
        run_async_test(test_instance.test_property_18_add_new_version_success(repo))
        print("✅ Add new version success test passed")
        
        run_async_test(test_instance.test_property_18_add_version_with_eol_date(repo))
        print("✅ Add version with EOL date test passed")
        
        run_async_test(test_instance.test_property_18_duplicate_version_handling(repo))
        print("✅ Duplicate version handling test passed")
        
        run_async_test(test_instance.test_property_18_batch_version_addition(repo))
        print("✅ Batch version addition test passed")
        
        run_async_test(test_instance.test_property_18_added_versions_available_for_analysis(repo))
        print("✅ Added versions available for analysis test passed")
        
        run_async_test(test_instance.test_property_18_database_stats_update_after_addition(repo))
        print("✅ Database stats update test passed")
        
        run_async_test(test_instance.test_property_18_database_error_handling_during_addition(repo))
        print("✅ Database error handling test passed")
        
        run_async_test(test_instance.test_property_18_concurrent_version_additions(repo))
        print("✅ Concurrent version additions test passed")
        
        run_async_test(test_instance.test_property_18_convenience_function_integration())
        print("✅ Convenience function integration test passed")
        
        print("\n🎉 All Property 18 tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        exit(1)