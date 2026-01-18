#!/usr/bin/env python3
"""
Enhanced data seeding script for StackDebt Encyclopedia database.

This script provides comprehensive seeding of software version data beyond the basic
SQL seed file, including more recent versions and additional software packages.
"""

import asyncio
import asyncpg
import logging
from datetime import date
from typing import List, Tuple
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://stackdebt_user:stackdebt_password@localhost:5432/stackdebt_encyclopedia"
)

# Additional seed data for comprehensive coverage
ADDITIONAL_SEED_DATA = [
    # More Python versions
    ("Python", "3.13", date(2024, 10, 7), None, "programming_language", False),
    ("Python", "3.6", date(2016, 12, 23), date(2021, 12, 23), "programming_language", False),
    ("Python", "3.5", date(2015, 9, 13), date(2020, 9, 13), "programming_language", False),
    
    # More Node.js versions
    ("Node.js", "22.0.0", date(2024, 4, 24), None, "programming_language", True),
    ("Node.js", "19.0.0", date(2022, 10, 18), date(2023, 6, 1), "programming_language", False),
    ("Node.js", "17.0.0", date(2021, 10, 19), date(2022, 6, 1), "programming_language", False),
    ("Node.js", "15.0.0", date(2020, 10, 20), date(2021, 6, 1), "programming_language", False),
    ("Node.js", "13.0.0", date(2019, 10, 22), date(2020, 6, 1), "programming_language", False),
    ("Node.js", "10.0.0", date(2018, 4, 24), date(2021, 4, 30), "programming_language", True),
    
    # More Java versions
    ("Java", "22", date(2024, 3, 19), None, "programming_language", False),
    ("Java", "19", date(2022, 9, 20), date(2023, 3, 21), "programming_language", False),
    ("Java", "15", date(2020, 9, 15), date(2021, 3, 16), "programming_language", False),
    ("Java", "7", date(2011, 7, 28), date(2022, 7, 19), "programming_language", False),
    
    # More Go versions
    ("Go", "1.22", date(2024, 2, 6), None, "programming_language", False),
    ("Go", "1.17", date(2021, 8, 16), date(2022, 8, 2), "programming_language", False),
    ("Go", "1.16", date(2021, 2, 16), date(2022, 3, 15), "programming_language", False),
    ("Go", "1.15", date(2020, 8, 11), date(2021, 8, 16), "programming_language", False),
    
    # Additional PHP versions
    ("PHP", "8.3", date(2023, 11, 23), None, "programming_language", False),
    ("PHP", "8.2", date(2022, 12, 8), None, "programming_language", False),
    ("PHP", "8.1", date(2021, 11, 25), None, "programming_language", False),
    ("PHP", "8.0", date(2020, 11, 26), date(2023, 11, 26), "programming_language", False),
    ("PHP", "7.4", date(2019, 11, 28), date(2022, 11, 28), "programming_language", False),
    ("PHP", "7.3", date(2018, 12, 6), date(2021, 12, 6), "programming_language", False),
    ("PHP", "7.2", date(2017, 11, 30), date(2020, 11, 30), "programming_language", False),
    ("PHP", "5.6", date(2014, 8, 28), date(2018, 12, 31), "programming_language", False),
    
    # Ruby versions
    ("Ruby", "3.3", date(2023, 12, 25), None, "programming_language", False),
    ("Ruby", "3.2", date(2022, 12, 25), None, "programming_language", False),
    ("Ruby", "3.1", date(2021, 12, 25), None, "programming_language", False),
    ("Ruby", "3.0", date(2020, 12, 25), None, "programming_language", False),
    ("Ruby", "2.7", date(2019, 12, 25), date(2023, 3, 31), "programming_language", False),
    ("Ruby", "2.6", date(2018, 12, 25), date(2022, 3, 31), "programming_language", False),
    
    # C# / .NET versions
    (".NET", "8.0", date(2023, 11, 14), None, "programming_language", True),
    (".NET", "7.0", date(2022, 11, 8), date(2024, 5, 14), "programming_language", False),
    (".NET", "6.0", date(2021, 11, 8), None, "programming_language", True),
    (".NET", "5.0", date(2020, 11, 10), date(2022, 5, 10), "programming_language", False),
    (".NET Core", "3.1", date(2019, 12, 3), date(2022, 12, 13), "programming_language", True),
    (".NET Core", "2.1", date(2018, 5, 30), date(2021, 8, 21), "programming_language", True),
    
    # Rust versions
    ("Rust", "1.75", date(2023, 12, 28), None, "programming_language", False),
    ("Rust", "1.70", date(2023, 6, 1), None, "programming_language", False),
    ("Rust", "1.65", date(2022, 11, 3), None, "programming_language", False),
    ("Rust", "1.60", date(2022, 4, 7), None, "programming_language", False),
    ("Rust", "1.55", date(2021, 9, 9), None, "programming_language", False),
    
    # Additional PostgreSQL versions
    ("PostgreSQL", "10", date(2017, 10, 5), date(2022, 11, 10), "database", False),
    ("PostgreSQL", "9.6", date(2016, 9, 29), date(2021, 11, 11), "database", False),
    ("PostgreSQL", "9.5", date(2016, 1, 7), date(2021, 2, 11), "database", False),
    
    # Additional MySQL versions
    ("MySQL", "8.1", date(2023, 7, 18), None, "database", False),
    ("MySQL", "8.2", date(2023, 10, 25), None, "database", False),
    ("MySQL", "5.5", date(2010, 12, 3), date(2018, 12, 3), "database", False),
    
    # MariaDB versions
    ("MariaDB", "11.2", date(2023, 11, 16), None, "database", False),
    ("MariaDB", "11.1", date(2023, 8, 21), None, "database", False),
    ("MariaDB", "10.11", date(2023, 2, 16), None, "database", True),
    ("MariaDB", "10.6", date(2021, 7, 6), None, "database", True),
    ("MariaDB", "10.5", date(2020, 6, 24), date(2025, 6, 24), "database", True),
    ("MariaDB", "10.4", date(2019, 6, 18), date(2024, 6, 18), "database", True),
    
    # Additional MongoDB versions
    ("MongoDB", "6.3", date(2023, 3, 13), None, "database", False),
    ("MongoDB", "4.2", date(2019, 8, 13), date(2023, 4, 30), "database", False),
    ("MongoDB", "4.0", date(2018, 6, 26), date(2022, 4, 30), "database", False),
    ("MongoDB", "3.6", date(2017, 11, 28), date(2021, 4, 30), "database", False),
    
    # Elasticsearch versions
    ("Elasticsearch", "8.11", date(2023, 11, 10), None, "database", False),
    ("Elasticsearch", "8.0", date(2022, 2, 10), None, "database", False),
    ("Elasticsearch", "7.17", date(2022, 2, 1), None, "database", False),
    ("Elasticsearch", "7.0", date(2019, 4, 10), date(2023, 8, 1), "database", False),
    ("Elasticsearch", "6.8", date(2019, 5, 20), date(2022, 2, 10), "database", False),
    
    # Additional Redis versions
    ("Redis", "6.2.14", date(2023, 9, 13), None, "database", False),
    ("Redis", "5.0", date(2018, 10, 17), date(2022, 4, 30), "database", False),
    ("Redis", "4.0", date(2017, 7, 14), date(2020, 7, 14), "database", False),
    
    # Additional web servers
    ("Apache HTTP Server", "2.4.59", date(2024, 4, 4), None, "web_server", False),
    ("Apache HTTP Server", "2.4.54", date(2022, 6, 8), None, "web_server", False),
    ("Apache HTTP Server", "2.4.48", date(2021, 6, 1), None, "web_server", False),
    
    # Additional nginx versions
    ("nginx", "1.26.0", date(2024, 5, 29), None, "web_server", False),
    ("nginx", "1.23.4", date(2023, 3, 28), None, "web_server", False),
    ("nginx", "1.21.6", date(2022, 1, 25), None, "web_server", False),
    ("nginx", "1.19.10", date(2021, 4, 13), None, "web_server", False),
    
    # IIS versions (Windows)
    ("IIS", "10.0", date(2016, 7, 29), None, "web_server", False),
    ("IIS", "8.5", date(2013, 10, 17), date(2023, 1, 10), "web_server", False),
    ("IIS", "8.0", date(2012, 10, 26), date(2023, 1, 10), "web_server", False),
    
    # Additional React versions
    ("React", "18.3.0", date(2024, 4, 25), None, "framework", False),
    ("React", "18.1.0", date(2022, 4, 26), None, "framework", False),
    ("React", "18.0.0", date(2022, 3, 29), None, "framework", False),
    ("React", "17.0.0", date(2020, 10, 20), None, "framework", False),
    ("React", "16.13.1", date(2020, 3, 19), None, "framework", False),
    ("React", "16.8.0", date(2019, 2, 6), None, "framework", False),
    ("React", "15.6.2", date(2017, 9, 25), date(2020, 10, 20), "framework", False),
    
    # Vue.js versions
    ("Vue.js", "3.4", date(2023, 12, 28), None, "framework", False),
    ("Vue.js", "3.3", date(2023, 5, 11), None, "framework", False),
    ("Vue.js", "3.2", date(2021, 8, 5), None, "framework", False),
    ("Vue.js", "3.0", date(2020, 9, 18), None, "framework", False),
    ("Vue.js", "2.7", date(2022, 7, 1), None, "framework", False),
    ("Vue.js", "2.6", date(2019, 2, 4), date(2023, 12, 31), "framework", False),
    ("Vue.js", "2.5", date(2017, 10, 13), date(2019, 2, 4), "framework", False),
    
    # Angular versions
    ("Angular", "17", date(2023, 11, 8), None, "framework", False),
    ("Angular", "16", date(2023, 5, 3), None, "framework", False),
    ("Angular", "15", date(2022, 11, 16), None, "framework", False),
    ("Angular", "14", date(2022, 6, 2), None, "framework", False),
    ("Angular", "13", date(2021, 11, 3), None, "framework", False),
    ("Angular", "12", date(2021, 5, 12), None, "framework", False),
    ("Angular", "11", date(2020, 11, 11), None, "framework", False),
    ("Angular", "10", date(2020, 6, 24), None, "framework", False),
    
    # Additional Django versions
    ("Django", "5.0", date(2023, 12, 4), None, "framework", False),
    ("Django", "4.0", date(2021, 12, 7), date(2023, 4, 1), "framework", False),
    ("Django", "3.1", date(2020, 8, 4), date(2021, 12, 7), "framework", False),
    ("Django", "3.0", date(2019, 12, 2), date(2021, 4, 5), "framework", False),
    ("Django", "1.11", date(2017, 4, 4), date(2020, 4, 11), "framework", True),
    
    # Flask versions
    ("Flask", "3.0", date(2023, 9, 30), None, "framework", False),
    ("Flask", "2.3", date(2023, 4, 25), None, "framework", False),
    ("Flask", "2.2", date(2022, 8, 1), None, "framework", False),
    ("Flask", "2.1", date(2022, 3, 28), None, "framework", False),
    ("Flask", "2.0", date(2021, 5, 11), None, "framework", False),
    ("Flask", "1.1", date(2019, 7, 4), date(2023, 9, 30), "framework", False),
    
    # Spring Boot versions
    ("Spring Boot", "3.2", date(2023, 11, 23), None, "framework", False),
    ("Spring Boot", "3.1", date(2023, 5, 18), None, "framework", False),
    ("Spring Boot", "3.0", date(2022, 11, 24), None, "framework", False),
    ("Spring Boot", "2.7", date(2022, 5, 19), None, "framework", False),
    ("Spring Boot", "2.6", date(2021, 11, 17), date(2023, 11, 24), "framework", False),
    ("Spring Boot", "2.5", date(2021, 5, 20), date(2023, 8, 24), "framework", False),
    
    # Laravel versions
    ("Laravel", "10", date(2023, 2, 14), None, "framework", False),
    ("Laravel", "9", date(2022, 2, 8), None, "framework", False),
    ("Laravel", "8", date(2020, 9, 8), date(2023, 1, 24), "framework", False),
    ("Laravel", "7", date(2020, 3, 3), date(2022, 10, 6), "framework", False),
    ("Laravel", "6", date(2019, 9, 3), date(2022, 9, 6), "framework", True),
    
    # Ruby on Rails versions
    ("Ruby on Rails", "7.1", date(2023, 10, 5), None, "framework", False),
    ("Ruby on Rails", "7.0", date(2021, 12, 15), None, "framework", False),
    ("Ruby on Rails", "6.1", date(2020, 12, 9), None, "framework", False),
    ("Ruby on Rails", "6.0", date(2019, 8, 16), date(2023, 6, 1), "framework", False),
    ("Ruby on Rails", "5.2", date(2018, 4, 9), date(2022, 6, 1), "framework", False),
    
    # Additional Express.js versions
    ("Express", "4.19", date(2024, 3, 25), None, "framework", False),
    ("Express", "4.18", date(2022, 4, 25), None, "framework", False),
    ("Express", "4.17", date(2019, 5, 16), None, "framework", False),
    ("Express", "4.16", date(2017, 10, 9), None, "framework", False),
    
    # Next.js versions
    ("Next.js", "14", date(2023, 10, 26), None, "framework", False),
    ("Next.js", "13", date(2022, 10, 25), None, "framework", False),
    ("Next.js", "12", date(2021, 10, 26), None, "framework", False),
    ("Next.js", "11", date(2021, 6, 15), None, "framework", False),
    ("Next.js", "10", date(2020, 10, 27), None, "framework", False),
    
    # Nuxt.js versions
    ("Nuxt.js", "3.8", date(2023, 11, 14), None, "framework", False),
    ("Nuxt.js", "3.0", date(2022, 11, 16), None, "framework", False),
    ("Nuxt.js", "2.17", date(2023, 8, 25), None, "framework", False),
    ("Nuxt.js", "2.16", date(2022, 12, 20), None, "framework", False),
    ("Nuxt.js", "2.15", date(2021, 3, 22), None, "framework", False),
    
    # Additional FastAPI versions
    ("FastAPI", "0.109", date(2024, 1, 18), None, "framework", False),
    ("FastAPI", "0.105", date(2023, 11, 2), None, "framework", False),
    ("FastAPI", "0.103", date(2023, 9, 17), None, "framework", False),
    ("FastAPI", "0.100", date(2023, 6, 9), None, "framework", False),
    ("FastAPI", "0.90", date(2023, 1, 7), None, "framework", False),
    ("FastAPI", "0.85", date(2022, 11, 12), None, "framework", False),
    
    # Popular libraries
    ("jQuery", "3.7.1", date(2023, 8, 28), None, "library", False),
    ("jQuery", "3.6.0", date(2021, 3, 2), None, "library", False),
    ("jQuery", "3.5.1", date(2020, 5, 4), None, "library", False),
    ("jQuery", "2.2.4", date(2016, 5, 20), date(2020, 5, 4), "library", False),
    ("jQuery", "1.12.4", date(2016, 5, 20), date(2020, 5, 4), "library", False),
    
    # Bootstrap versions
    ("Bootstrap", "5.3", date(2023, 5, 30), None, "library", False),
    ("Bootstrap", "5.2", date(2022, 7, 19), None, "library", False),
    ("Bootstrap", "5.1", date(2021, 8, 4), None, "library", False),
    ("Bootstrap", "5.0", date(2021, 5, 5), None, "library", False),
    ("Bootstrap", "4.6", date(2021, 1, 19), None, "library", False),
    ("Bootstrap", "4.5", date(2020, 6, 16), None, "library", False),
    ("Bootstrap", "3.4.1", date(2019, 2, 13), date(2021, 5, 5), "library", False),
    
    # Tailwind CSS versions
    ("Tailwind CSS", "3.4", date(2023, 12, 7), None, "library", False),
    ("Tailwind CSS", "3.3", date(2023, 3, 30), None, "library", False),
    ("Tailwind CSS", "3.2", date(2022, 11, 11), None, "library", False),
    ("Tailwind CSS", "3.1", date(2022, 6, 2), None, "library", False),
    ("Tailwind CSS", "3.0", date(2021, 12, 9), None, "library", False),
    ("Tailwind CSS", "2.2", date(2021, 6, 17), None, "library", False),
    
    # Webpack versions
    ("Webpack", "5.89", date(2023, 11, 16), None, "development_tool", False),
    ("Webpack", "5.88", date(2023, 7, 10), None, "development_tool", False),
    ("Webpack", "5.75", date(2022, 11, 26), None, "development_tool", False),
    ("Webpack", "5.0", date(2020, 10, 10), None, "development_tool", False),
    ("Webpack", "4.46.0", date(2020, 8, 19), date(2022, 10, 10), "development_tool", False),
    
    # Vite versions
    ("Vite", "5.0", date(2023, 11, 16), None, "development_tool", False),
    ("Vite", "4.5", date(2023, 9, 18), None, "development_tool", False),
    ("Vite", "4.0", date(2022, 12, 9), None, "development_tool", False),
    ("Vite", "3.2", date(2022, 10, 10), None, "development_tool", False),
    ("Vite", "3.0", date(2022, 7, 13), None, "development_tool", False),
    ("Vite", "2.9", date(2022, 3, 30), None, "development_tool", False),
    
    # Docker versions
    ("Docker", "24.0", date(2023, 5, 15), None, "development_tool", False),
    ("Docker", "23.0", date(2023, 2, 1), None, "development_tool", False),
    ("Docker", "20.10", date(2020, 12, 8), None, "development_tool", False),
    ("Docker", "19.03", date(2019, 7, 22), date(2023, 6, 1), "development_tool", False),
    ("Docker", "18.09", date(2018, 11, 8), date(2022, 6, 1), "development_tool", False),
    
    # Kubernetes versions
    ("Kubernetes", "1.29", date(2023, 12, 13), None, "development_tool", False),
    ("Kubernetes", "1.28", date(2023, 8, 15), None, "development_tool", False),
    ("Kubernetes", "1.27", date(2023, 4, 11), None, "development_tool", False),
    ("Kubernetes", "1.26", date(2022, 12, 8), None, "development_tool", False),
    ("Kubernetes", "1.25", date(2022, 8, 23), None, "development_tool", False),
    ("Kubernetes", "1.24", date(2022, 5, 3), None, "development_tool", False),
]


async def seed_additional_data():
    """Seed additional comprehensive version data into the Encyclopedia database."""
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        logger.info("Connected to Encyclopedia database")
        
        # Insert additional seed data
        insert_query = """
            INSERT INTO version_releases 
            (software_name, version, release_date, end_of_life_date, category, is_lts)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (software_name, version) DO NOTHING
        """
        
        inserted_count = 0
        for software_name, version, release_date, eol_date, category, is_lts in ADDITIONAL_SEED_DATA:
            try:
                await conn.execute(
                    insert_query, 
                    software_name, version, release_date, eol_date, category, is_lts
                )
                inserted_count += 1
                if inserted_count % 50 == 0:
                    logger.info(f"Inserted {inserted_count} records...")
            except Exception as e:
                logger.warning(f"Failed to insert {software_name} {version}: {e}")
        
        logger.info(f"Successfully processed {inserted_count} additional version records")
        
        # Get final statistics
        stats_query = """
            SELECT 
                COUNT(*) as total_versions,
                COUNT(DISTINCT software_name) as total_software,
                COUNT(DISTINCT category) as total_categories
            FROM version_releases
        """
        stats = await conn.fetchrow(stats_query)
        
        logger.info(f"Encyclopedia database now contains:")
        logger.info(f"  - {stats['total_versions']} total versions")
        logger.info(f"  - {stats['total_software']} unique software packages")
        logger.info(f"  - {stats['total_categories']} categories")
        
        await conn.close()
        logger.info("Database seeding completed successfully")
        
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(seed_additional_data())