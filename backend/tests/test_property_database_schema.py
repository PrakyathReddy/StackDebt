"""
Property-based tests for StackDebt Encyclopedia database schema.
**Feature: stackdebt, Property 16: Encyclopedia Completeness**
"""

import pytest
import asyncio
import asyncpg
from hypothesis import given, strategies as st, settings
from typing import List, Set
import os
from datetime import date

# Database connection URL
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://stackdebt_user:stackdebt_password@localhost:5432/stackdebt_encyclopedia"
)

# Expected major software categories and examples
EXPECTED_CATEGORIES = {
    'operating_system': ['Ubuntu', 'CentOS', 'Windows Server'],
    'programming_language': ['Python', 'Node.js', 'Java', 'Go'],
    'database': ['PostgreSQL', 'MySQL', 'MongoDB', 'Redis'],
    'web_server': ['Apache HTTP Server', 'nginx'],
    'framework': ['React', 'Django', 'Express', 'FastAPI']
}

class TestProperty16EncyclopediaCompleteness:
    """
    **Feature: stackdebt, Property 16: Encyclopedia Completeness**
    **Validates: Requirements 7.1, 7.2, 7.3, 7.4**
    
    Property: For any major software category (OS, languages, databases, frameworks), 
    the Encyclopedia database should contain release date information for commonly used versions.
    """

    @pytest.fixture(scope="class")
    async def db_connection(self):
        """Create database connection for tests."""
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            yield conn
            await conn.close()
        except Exception as e:
            pytest.skip(f"Database not available: {e}")

    @pytest.mark.asyncio
    async def test_property_16_encyclopedia_completeness_categories_exist(self):
        """
        **Feature: stackdebt, Property 16: Encyclopedia Completeness**
        Test that all expected major software categories exist in the database.
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        
        try:
            # Check that all expected categories exist in the enum
            categories_query = """
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = (
                    SELECT oid FROM pg_type WHERE typname = 'component_category'
                )
            """
            db_categories = await conn.fetch(categories_query)
            db_category_names = {row['enumlabel'] for row in db_categories}
            
            expected_category_names = set(EXPECTED_CATEGORIES.keys())
            
            # Property: All major software categories should exist
            assert expected_category_names.issubset(db_category_names), \
                f"Missing categories: {expected_category_names - db_category_names}"
            
        finally:
            await conn.close()

    @pytest.mark.asyncio
    async def test_property_16_encyclopedia_completeness_major_software_exists(self):
        """
        **Feature: stackdebt, Property 16: Encyclopedia Completeness**
        Test that major software examples exist for each category.
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        
        try:
            for category, expected_software in EXPECTED_CATEGORIES.items():
                # Check that at least some major software exists for each category
                software_query = """
                    SELECT DISTINCT software_name 
                    FROM version_releases 
                    WHERE category = $1
                """
                db_software = await conn.fetch(software_query, category)
                db_software_names = {row['software_name'] for row in db_software}
                
                # Property: Each major category should have at least one expected software
                intersection = set(expected_software) & db_software_names
                assert len(intersection) > 0, \
                    f"Category '{category}' missing expected software. Expected any of: {expected_software}, Found: {list(db_software_names)}"
                
        finally:
            await conn.close()

    @pytest.mark.asyncio
    async def test_property_16_encyclopedia_completeness_release_dates_valid(self):
        """
        **Feature: stackdebt, Property 16: Encyclopedia Completeness**
        Test that all version records have valid release dates.
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        
        try:
            # Check that all records have valid release dates
            invalid_dates_query = """
                SELECT software_name, version, release_date 
                FROM version_releases 
                WHERE release_date IS NULL 
                   OR release_date > CURRENT_DATE
                   OR release_date < '1970-01-01'
                LIMIT 10
            """
            invalid_records = await conn.fetch(invalid_dates_query)
            
            # Property: All version records should have valid release dates
            assert len(invalid_records) == 0, \
                f"Found records with invalid release dates: {[dict(r) for r in invalid_records]}"
            
        finally:
            await conn.close()

    @pytest.mark.asyncio
    async def test_property_16_encyclopedia_completeness_version_uniqueness(self):
        """
        **Feature: stackdebt, Property 16: Encyclopedia Completeness**
        Test that software name + version combinations are unique.
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        
        try:
            # Check for duplicate software_name + version combinations
            duplicates_query = """
                SELECT software_name, version, COUNT(*) as count
                FROM version_releases 
                GROUP BY software_name, version 
                HAVING COUNT(*) > 1
                LIMIT 10
            """
            duplicates = await conn.fetch(duplicates_query)
            
            # Property: Each software name + version combination should be unique
            assert len(duplicates) == 0, \
                f"Found duplicate software+version combinations: {[dict(r) for r in duplicates]}"
            
        finally:
            await conn.close()

    @given(st.sampled_from(list(EXPECTED_CATEGORIES.keys())))
    @settings(max_examples=5)
    @pytest.mark.asyncio
    async def test_property_16_encyclopedia_completeness_category_has_versions(self, category):
        """
        **Feature: stackdebt, Property 16: Encyclopedia Completeness**
        Property test: For any major software category, there should be version records.
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        
        try:
            # Check that the category has at least one version record
            count_query = """
                SELECT COUNT(*) as count
                FROM version_releases 
                WHERE category = $1
            """
            result = await conn.fetchrow(count_query, category)
            count = result['count']
            
            # Property: Each major category should have at least one version record
            assert count > 0, \
                f"Category '{category}' has no version records in the database"
            
        finally:
            await conn.close()

    @pytest.mark.asyncio
    async def test_property_16_encyclopedia_completeness_comprehensive_coverage(self):
        """
        **Feature: stackdebt, Property 16: Encyclopedia Completeness**
        Test that the database has comprehensive coverage of major software.
        """
        try:
            conn = await asyncpg.connect(DATABASE_URL)
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        
        try:
            # Check minimum expected counts for comprehensive coverage
            coverage_requirements = {
                'operating_system': 5,      # At least 5 OS versions
                'programming_language': 10, # At least 10 language versions  
                'database': 8,              # At least 8 database versions
                'web_server': 5,            # At least 5 web server versions
                'framework': 8              # At least 8 framework versions
            }
            
            for category, min_count in coverage_requirements.items():
                count_query = """
                    SELECT COUNT(*) as count
                    FROM version_releases 
                    WHERE category = $1
                """
                result = await conn.fetchrow(count_query, category)
                actual_count = result['count']
                
                # Property: Each category should have comprehensive coverage
                assert actual_count >= min_count, \
                    f"Category '{category}' has insufficient coverage: {actual_count} < {min_count} required"
            
        finally:
            await conn.close()


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
    test_instance = TestProperty16EncyclopediaCompleteness()
    
    print("Running Property 16: Encyclopedia Completeness tests...")
    
    try:
        run_async_test(test_instance.test_property_16_encyclopedia_completeness_categories_exist())
        print("✅ Categories exist test passed")
        
        run_async_test(test_instance.test_property_16_encyclopedia_completeness_major_software_exists())
        print("✅ Major software exists test passed")
        
        run_async_test(test_instance.test_property_16_encyclopedia_completeness_release_dates_valid())
        print("✅ Release dates valid test passed")
        
        run_async_test(test_instance.test_property_16_encyclopedia_completeness_version_uniqueness())
        print("✅ Version uniqueness test passed")
        
        run_async_test(test_instance.test_property_16_encyclopedia_completeness_comprehensive_coverage())
        print("✅ Comprehensive coverage test passed")
        
        print("\n🎉 All Property 16 tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        exit(1)