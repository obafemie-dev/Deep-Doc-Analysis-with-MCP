"""
Database configuration for analytics
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from typing import AsyncGenerator

from .config import settings

# Create async engine for analytics database
analytics_engine = create_async_engine(
    settings.ANALYTICS_DB_URL,
    echo=False,  # Set to True for SQL query logging
    future=True,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    analytics_engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevent "IO in unexpected place" errors
    autocommit=False,
    autoflush=False,
)

# Base class for SQLAlchemy models
Base = declarative_base()


async def get_analytics_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get analytics database session.

    Yields:
        AsyncSession: Database session

    Usage:
        @app.get("/example")
        async def example(db: AsyncSession = Depends(get_analytics_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_analytics_db():
    """
    Initialize analytics database tables.
    Should be called on application startup.
    """
    async with analytics_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
