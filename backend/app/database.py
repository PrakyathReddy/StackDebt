"""
Database configuration and connection management for StackDebt Encyclopedia.
"""

import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import asyncpg
from typing import AsyncGenerator

# Database URL from environment variable
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://stackdebt_user:stackdebt_password@localhost:5432/stackdebt_encyclopedia"
)

# SQLAlchemy setup for sync operations
engine = create_engine(
    DATABASE_URL,
    poolclass=StaticPool,
    echo=True  # Set to False in production
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
metadata = MetaData()

# Async database connection for FastAPI
async def get_database_connection():
    """Get async database connection for FastAPI endpoints."""
    connection = await asyncpg.connect(DATABASE_URL)
    try:
        yield connection
    finally:
        await connection.close()

def get_db():
    """Get sync database session for SQLAlchemy operations."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def create_database_pool():
    """Create async connection pool for high-performance operations."""
    return await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=10,
        command_timeout=60
    )

# Global connection pool
db_pool = None

async def init_database():
    """Initialize database connection pool."""
    global db_pool
    db_pool = await create_database_pool()
    return db_pool

async def close_database():
    """Close database connection pool."""
    global db_pool
    if db_pool:
        await db_pool.close()

class DatabaseConnection:
    """Async context manager for database connections."""
    
    def __init__(self):
        self.connection = None
    
    async def __aenter__(self):
        global db_pool
        if not db_pool:
            db_pool = await init_database()
        
        self.connection = await db_pool.acquire()
        return self.connection
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            await db_pool.release(self.connection)

def get_db_connection():
    """Get database connection context manager."""
    return DatabaseConnection()