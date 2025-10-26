"""
Database configuration and connection management for Agentify
"""
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://agentify_user:agentify_pass@localhost:5432/agentify"
)

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DB_ECHO", "false").lower() == "true",  # Set to true for SQL logging
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Validate connections before use
    pool_recycle=3600,   # Recycle connections every hour
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    """Base class for all database models"""
    pass

async def get_db() -> AsyncSession:
    """
    Dependency function to get database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()

async def init_database():
    """
    Initialize database - create all tables
    """
    try:
        async with engine.begin() as conn:
            # Import all models to ensure they're registered
            from .models import User, ChatThread, ChatMessage, MCPServer, LLMConfiguration, UserSession, UserPreferences
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

async def close_database():
    """
    Close database connections
    """
    await engine.dispose()
    logger.info("Database connections closed")

# Health check function
async def check_database_health() -> bool:
    """
    Check if database is accessible
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False