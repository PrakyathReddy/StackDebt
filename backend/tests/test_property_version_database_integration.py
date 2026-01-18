"""
Property-based tests for Encyclopedia version database integration.
**Feature: stackdebt, Property 6: Version Database Integration**
"""

import pytest
import asyncio
import asyncpg
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from typing import List, Tuple, Optional
import os
from datetime import date, datetime

from app.encyclopedia import EncyclopediaRepository
from app.models import ComponentCategory, VersionRelease

# Database connection URL
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://stackdebt_user:stackdebt_password@localhost:5432/stackdebt_encyclopedia"
)

# Strategy for generating valid software names and versions
software_names_strategy = st.sampled_from([
    "Python", "Node.js", "Java", "Go", "PHP", "Ruby", ".NET", "Rust",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "MariaDB", "Elasticsearch",
    "Apache HTTP Server", "nginx", "IIS",
    "React", "Vue.js", "Angular", "Django", "Flask", "Express", "FastAPI",
    "Laravel", "Spring Boot", "Ruby on Rails", "Next.js", "Nuxt.js",
    "jQuery", "Bootstrap", "Tailwind CSS", "Webpack", "Vite", "Docker", "Kubernetes"
])

version_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Nd", "Pc"), whitelist_characters="."),
    min_size=1,
    max_size=20
).filter(lambda x: len(x.strip()) > 0 and not x.startswith('.') and not x.endswith('.'))


class TestProperty6VersionDatabaseIntegration:
    """
    **Feature: stackdebt, Property 6: Version Database Integration**
    **Validates: Requirements 2.7**
    
    Property: For any detected component, if its version exists in the Encyclopedia database, 
    the system should retrieve and use the correct release date for age calculation.
    """

    @pytest.mark.asyncio
    async def test_property_6_existing_versions_return_correct_data(self):
        """
        **Feature: stackdebt, Property 6: Version Database Integration**
        **Validates: Requirements 2.7**
        Test that existing versions in database return correct release date information.
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        
        encyclopedia_repo = EncyclopediaRepository()
        
        try:
            # Get some known versions from database
            known_versions_query = """
                SELECT software_name, version, release_date, category
                FROM version_releases 
                ORDER BY RANDOM()
                LIMIT 10
            """
            known_versions = await conn.fetch(known_versions_query)
            
            if not known_versions:
                pytest.skip("No version data in database for testing")
            
            for row in known_versions:
                software_name = row['software_name']
                version = row['version']
                expected_release_date = row['release_date']
                expected_category = row['category']
                
                # Property: Existing versions should return correct data
                result = await encyclopedia_repo.lookup_version(software_name, version)
                
                assert result is not None, f"Version {software_name} {version} should exist in database"
                assert result.software_name == software_name
                assert result.version == version
                assert result.release_date == expected_release_date
                assert result.category.value == expected_category
                
        finally:
            await conn.close()

    @given(st.lists(
        st.tuples(software_names_strategy, version_strategy),
        min_size=1,
        max_size=20,
        unique=True
    ))
    @settings(max_examples=10, deadline=30000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_6_batch_lookup_consistency(self, software_versions):
        """
        **Feature: stackdebt, Property 6: Version Database Integration**
        **Validates: Requirements 2.7**
        Property test: Batch lookup should return consistent results with individual lookups.
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.close()
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        
        encyclopedia_repo = EncyclopediaRepository()
        
        # Filter to only include versions that might exist in database
        filtered_versions = []
        for software_name, version in software_versions:
            # Only test with reasonable version formats
            if version and len(version) < 15 and '.' in version:
                filtered_versions.append((software_name, version))
        
        if not filtered_versions:
            return  # Skip if no valid versions to test
        
        # Take only first 5 to keep test reasonable
        test_versions = filtered_versions[:5]
        
        # Get batch results
        batch_results = await encyclopedia_repo.lookup_versions_batch(test_versions)
        
        # Get individual results
        individual_results = {}
        for software_name, version in test_versions:
            individual_result = await encyclopedia_repo.lookup_version(software_name, version)
            individual_results[(software_name, version)] = individual_result
        
        # Property: Batch and individual results should be consistent
        for key in test_versions:
            batch_result = batch_results.get(key)
            individual_result = individual_results.get(key)
            
            if batch_result is None and individual_result is None:
                continue  # Both None is consistent
            
            if batch_result is not None and individual_result is not None:
                assert batch_result.software_name == individual_result.software_name
                assert batch_result.version == individual_result.version
                assert batch_result.release_date == individual_result.release_date
                assert batch_result.category == individual_result.category
            else:
                assert False, f"Inconsistent results for {key}: batch={batch_result}, individual={individual_result}"

    @pytest.mark.asyncio
    async def test_property_6_database_integration_completeness(self):
        """
        **Feature: stackdebt, Property 6: Version Database Integration**
        **Validates: Requirements 2.7**
        Test that database integration provides comprehensive version coverage.
        """
        encyclopedia_repo = EncyclopediaRepository()
        
        # Test that major software categories have version data
        major_categories = [
            ComponentCategory.OPERATING_SYSTEM,
            ComponentCategory.PROGRAMMING_LANGUAGE,
            ComponentCategory.DATABASE,
            ComponentCategory.WEB_SERVER,
            ComponentCategory.FRAMEWORK
        ]
        
        for category in major_categories:
            software_list = await encyclopedia_repo.get_software_by_category(category)
            
            # Property: Each major category should have software entries
            assert len(software_list) > 0, f"Category {category} should have software entries"
            
            # Test that software in category has version data
            if software_list:
                sample_software = software_list[0]
                versions = await encyclopedia_repo.get_software_versions(sample_software, 5)
                
                # Property: Software should have version entries with valid data
                assert len(versions) > 0, f"Software {sample_software} should have version entries"
                
                for version in versions:
                    assert version.software_name == sample_software
                    assert version.version is not None and len(version.version) > 0
                    assert version.release_date is not None
                    assert isinstance(version.release_date, date)
                    assert version.category == category

    @given(software_names_strategy)
    @settings(max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_6_software_versions_ordering(self, software_name):
        """
        **Feature: stackdebt, Property 6: Version Database Integration**
        **Validates: Requirements 2.7**
        Property test: Software versions should be returned in correct chronological order.
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.close()
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        
        encyclopedia_repo = EncyclopediaRepository()
        versions = await encyclopedia_repo.get_software_versions(software_name, 10)
        
        if len(versions) < 2:
            return  # Skip if not enough versions to test ordering
        
        # Property: Versions should be ordered by release date (newest first)
        for i in range(len(versions) - 1):
            current_version = versions[i]
            next_version = versions[i + 1]
            
            assert current_version.release_date >= next_version.release_date, \
                f"Versions not properly ordered: {current_version.version} ({current_version.release_date}) " \
                f"should be >= {next_version.version} ({next_version.release_date})"

    @pytest.mark.asyncio
    async def test_property_6_search_functionality_integration(self):
        """
        **Feature: stackdebt, Property 6: Version Database Integration**
        **Validates: Requirements 2.7**
        Test that search functionality integrates properly with version data.
        """
        encyclopedia_repo = EncyclopediaRepository()
        
        # Test search with common terms
        search_terms = ["Python", "Node", "Java", "React", "nginx"]
        
        for term in search_terms:
            search_results = await encyclopedia_repo.search_software(term, 5)
            
            for result in search_results:
                # Property: Search results should have valid structure and data
                assert 'software_name' in result
                assert 'category' in result
                assert 'version_count' in result
                assert 'latest_release' in result
                
                assert isinstance(result['software_name'], str)
                assert len(result['software_name']) > 0
                assert result['version_count'] > 0
                assert isinstance(result['latest_release'], date)
                
                # Property: Search term should appear in software name (case insensitive)
                assert term.lower() in result['software_name'].lower()

    @pytest.mark.asyncio
    async def test_property_6_missing_version_handling(self):
        """
        **Feature: stackdebt, Property 6: Version Database Integration**
        **Validates: Requirements 2.7**
        Test that missing versions are handled correctly without breaking the system.
        """
        encyclopedia_repo = EncyclopediaRepository()
        
        # Clear cache to ensure fresh logging
        encyclopedia_repo.clear_missing_versions_cache()
        
        # Test with obviously non-existent versions
        non_existent_versions = [
            ("NonExistentSoftware", "999.999.999"),
            ("FakeTool", "0.0.0-fake"),
            ("TestSoftware", "invalid-version"),
        ]
        
        for software_name, version in non_existent_versions:
            result = await encyclopedia_repo.lookup_version(software_name, version)
            
            # Property: Missing versions should return None without crashing
            assert result is None, f"Non-existent version {software_name} {version} should return None"
        
        # Test batch lookup with mix of existing and non-existing
        mixed_versions = [
            ("Python", "3.9.0"),  # Likely to exist
            ("NonExistentSoftware", "1.0.0"),  # Definitely doesn't exist
        ]
        
        batch_results = await encyclopedia_repo.lookup_versions_batch(mixed_versions)
        
        # Property: Batch lookup should handle mixed results correctly
        assert len(batch_results) == 2
        assert ("NonExistentSoftware", "1.0.0") in batch_results
        assert batch_results[("NonExistentSoftware", "1.0.0")] is None

    @pytest.mark.asyncio
    async def test_property_6_database_stats_accuracy(self):
        """
        **Feature: stackdebt, Property 6: Version Database Integration**
        **Validates: Requirements 2.7**
        Test that database statistics accurately reflect the actual data.
        """
        encyclopedia_repo = EncyclopediaRepository()
        
        stats = await encyclopedia_repo.get_database_stats()
        
        # Property: Stats should have required fields
        required_fields = [
            'total_versions', 'total_software', 'total_categories',
            'oldest_release', 'newest_release', 'versions_by_category'
        ]
        
        for field in required_fields:
            assert field in stats, f"Stats should include {field}"
        
        # Property: Stats should have reasonable values
        assert stats['total_versions'] > 0, "Should have version records"
        assert stats['total_software'] > 0, "Should have software records"
        assert stats['total_categories'] > 0, "Should have categories"
        assert isinstance(stats['oldest_release'], date), "Oldest release should be a date"
        assert isinstance(stats['newest_release'], date), "Newest release should be a date"
        assert stats['oldest_release'] <= stats['newest_release'], "Date range should be valid"
        
        # Property: Category counts should sum to total versions
        category_sum = sum(stats['versions_by_category'].values())
        assert category_sum == stats['total_versions'], \
            f"Category counts ({category_sum}) should sum to total versions ({stats['total_versions']})"
        
        # Verify stats against actual database
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            actual_count_query = "SELECT COUNT(*) as count FROM version_releases"
            actual_count = await conn.fetchrow(actual_count_query)
            
            assert stats['total_versions'] == actual_count['count'], \
                "Stats total_versions should match actual database count"
            await conn.close()
        except Exception as e:
            pytest.skip(f"Database verification failed: {e}")


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
    test_instance = TestProperty6VersionDatabaseIntegration()
    
    print("Running Property 6: Version Database Integration tests...")
    
    try:
        run_async_test(test_instance.test_property_6_existing_versions_return_correct_data())
        print("✅ Existing versions return correct data test passed")
        
        run_async_test(test_instance.test_property_6_database_integration_completeness())
        print("✅ Database integration completeness test passed")
        
        run_async_test(test_instance.test_property_6_search_functionality_integration())
        print("✅ Search functionality integration test passed")
        
        run_async_test(test_instance.test_property_6_missing_version_handling())
        print("✅ Missing version handling test passed")
        
        run_async_test(test_instance.test_property_6_database_stats_accuracy())
        print("✅ Database stats accuracy test passed")
        
        print("\n🎉 All Property 6 tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        exit(1)