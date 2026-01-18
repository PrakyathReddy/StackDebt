#!/usr/bin/env python3
"""
Performance analysis script for Encyclopedia database indexing.

This script demonstrates the performance benefits of the database indexes
by showing query execution plans and timing comparisons.
"""

import asyncio
import asyncpg
import time
import os
import logging
from datetime import date

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://stackdebt_user:stackdebt_password@localhost:5432/stackdebt_encyclopedia"
)


async def analyze_query_performance():
    """Analyze query performance with and without indexes."""
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        logger.info("Connected to Encyclopedia database for performance analysis")
        
        # Test queries that benefit from our indexes
        test_queries = [
            {
                "name": "Single version lookup (uses idx_software_version)",
                "query": "SELECT * FROM version_releases WHERE software_name = $1 AND version = $2",
                "params": ["Python", "3.11"]
            },
            {
                "name": "Software versions by name (uses idx_software_name)",
                "query": "SELECT * FROM version_releases WHERE software_name = $1 ORDER BY release_date DESC",
                "params": ["Python"]
            },
            {
                "name": "Software by category (uses idx_category)",
                "query": "SELECT DISTINCT software_name FROM version_releases WHERE category = $1",
                "params": ["programming_language"]
            },
            {
                "name": "Recent releases (uses idx_release_date)",
                "query": "SELECT * FROM version_releases WHERE release_date >= $1 ORDER BY release_date DESC LIMIT 10",
                "params": [date(2023, 1, 1)]
            }
        ]
        
        for test in test_queries:
            logger.info(f"\n--- {test['name']} ---")
            
            # Get query execution plan
            explain_query = f"EXPLAIN (ANALYZE, BUFFERS) {test['query']}"
            plan = await conn.fetch(explain_query, *test['params'])
            
            logger.info("Execution Plan:")
            for row in plan:
                logger.info(f"  {row['QUERY PLAN']}")
            
            # Time the actual query
            start_time = time.time()
            results = await conn.fetch(test['query'], *test['params'])
            execution_time = time.time() - start_time
            
            logger.info(f"Results: {len(results)} rows in {execution_time:.4f}s")
        
        # Show index usage statistics
        logger.info("\n--- Index Usage Statistics ---")
        index_stats = await conn.fetch("""
            SELECT 
                schemaname,
                relname as tablename,
                indexrelname as indexname,
                idx_scan as scans,
                idx_tup_read as tuples_read,
                idx_tup_fetch as tuples_fetched
            FROM pg_stat_user_indexes 
            WHERE relname = 'version_releases'
            ORDER BY idx_scan DESC
        """)
        
        for stat in index_stats:
            logger.info(f"  {stat['indexname']}: {stat['scans']} scans, "
                       f"{stat['tuples_read']} tuples read, "
                       f"{stat['tuples_fetched']} tuples fetched")
        
        # Show table statistics
        logger.info("\n--- Table Statistics ---")
        table_stats = await conn.fetchrow("""
            SELECT 
                n_tup_ins as inserts,
                n_tup_upd as updates,
                n_tup_del as deletes,
                n_tup_hot_upd as hot_updates,
                n_live_tup as live_tuples,
                n_dead_tup as dead_tuples,
                seq_scan as sequential_scans,
                seq_tup_read as sequential_tuples_read,
                idx_scan as index_scans,
                idx_tup_fetch as index_tuples_fetched
            FROM pg_stat_user_tables 
            WHERE relname = 'version_releases'
        """)
        
        if table_stats:
            logger.info(f"  Live tuples: {table_stats['live_tuples']}")
            logger.info(f"  Sequential scans: {table_stats['sequential_scans']}")
            logger.info(f"  Index scans: {table_stats['index_scans']}")
            logger.info(f"  Index scan ratio: {table_stats['index_scans'] / (table_stats['sequential_scans'] + table_stats['index_scans']) * 100:.1f}%")
        
        await conn.close()
        logger.info("\nPerformance analysis completed successfully")
        
    except Exception as e:
        logger.error(f"Error during performance analysis: {e}")
        raise


async def benchmark_batch_operations():
    """Benchmark batch operations vs individual operations."""
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        logger.info("\n--- Batch Operation Benchmarks ---")
        
        # Test data
        test_versions = [
            ("Python", "3.11"), ("Python", "3.10"), ("Python", "3.9"),
            ("Node.js", "18.0.0"), ("Node.js", "16.0.0"), ("Node.js", "14.0.0"),
            ("Java", "17"), ("Java", "11"), ("Java", "8"),
            ("Go", "1.21"), ("Go", "1.20"), ("Go", "1.19")
        ]
        
        # Individual lookups
        start_time = time.time()
        individual_results = []
        for software, version in test_versions:
            result = await conn.fetchrow(
                "SELECT * FROM version_releases WHERE software_name = $1 AND version = $2",
                software, version
            )
            individual_results.append(result)
        individual_time = time.time() - start_time
        
        # Batch lookup using IN clause
        start_time = time.time()
        placeholders = []
        params = []
        for i, (software, version) in enumerate(test_versions):
            placeholders.append(f"(${i*2+1}, ${i*2+2})")
            params.extend([software, version])
        
        batch_query = f"""
            SELECT * FROM version_releases 
            WHERE (software_name, version) IN ({', '.join(placeholders)})
        """
        batch_results = await conn.fetch(batch_query, *params)
        batch_time = time.time() - start_time
        
        logger.info(f"Individual lookups: {len(individual_results)} results in {individual_time:.4f}s")
        logger.info(f"Batch lookup: {len(batch_results)} results in {batch_time:.4f}s")
        logger.info(f"Performance improvement: {individual_time / batch_time:.1f}x faster")
        
        await conn.close()
        
    except Exception as e:
        logger.error(f"Error during batch benchmark: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(analyze_query_performance())
    asyncio.run(benchmark_batch_operations())