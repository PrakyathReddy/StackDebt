"""
Test script to verify database setup and connection.
Run this after starting the database to ensure everything is working.
"""

import asyncio
import asyncpg
import os
from datetime import date

async def test_database_connection():
    """Test database connection and basic operations."""
    database_url = os.getenv(
        "DATABASE_URL", 
        "postgresql://stackdebt_user:stackdebt_password@localhost:5432/stackdebt_encyclopedia"
    )
    
    try:
        # Test connection
        conn = await asyncpg.connect(database_url)
        print("✅ Database connection successful")
        
        # Test schema exists
        result = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'version_releases')"
        )
        if result:
            print("✅ version_releases table exists")
        else:
            print("❌ version_releases table not found")
            return False
        
        # Test enum exists
        result = await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'component_category')"
        )
        if result:
            print("✅ component_category enum exists")
        else:
            print("❌ component_category enum not found")
            return False
        
        # Test sample data
        count = await conn.fetchval("SELECT COUNT(*) FROM version_releases")
        print(f"✅ Found {count} version records in database")
        
        # Test a sample query
        python_versions = await conn.fetch(
            "SELECT version, release_date FROM version_releases WHERE software_name = 'Python' ORDER BY release_date DESC LIMIT 3"
        )
        print("✅ Sample Python versions:")
        for version in python_versions:
            print(f"   - Python {version['version']} (released {version['release_date']})")
        
        await conn.close()
        print("✅ All database tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_database_connection())
    exit(0 if success else 1)