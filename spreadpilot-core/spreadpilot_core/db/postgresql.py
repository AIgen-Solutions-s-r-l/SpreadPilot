"""PostgreSQL database connection and setup for P&L data."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)

from ..logging import get_logger
from ..models.pnl import Base

logger = get_logger(__name__)

# Global variables
_engine = None
_async_session_factory = None


def get_postgres_url() -> str:
    """Get PostgreSQL connection URL from environment."""
    # Try specific P&L database URL first, fallback to generic
    postgres_url = os.environ.get("PNL_DATABASE_URL") or os.environ.get("DATABASE_URL")

    if not postgres_url:
        # Build from components if individual vars are set
        host = os.environ.get("POSTGRES_HOST", "localhost")
        port = os.environ.get("POSTGRES_PORT", "5432")
        db = os.environ.get("POSTGRES_DB", "spreadpilot_pnl")
        user = os.environ.get("POSTGRES_USER", "postgres")
        password = os.environ.get("POSTGRES_PASSWORD", "")

        if password:
            postgres_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"
        else:
            postgres_url = f"postgresql+asyncpg://{user}@{host}:{port}/{db}"

    # Ensure we're using asyncpg driver
    if postgres_url.startswith("postgresql://"):
        postgres_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    return postgres_url


async def init_postgres() -> None:
    """Initialize PostgreSQL connection and create tables."""
    global _engine, _async_session_factory

    try:
        postgres_url = get_postgres_url()
        logger.info(
            f"Connecting to PostgreSQL for P&L data: {postgres_url.split('@')[1] if '@' in postgres_url else postgres_url}"
        )

        # Create async engine
        _engine = create_async_engine(
            postgres_url,
            echo=False,  # Set to True for SQL query logging
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,  # 1 hour
        )

        # Create session factory
        _async_session_factory = async_sessionmaker(
            _engine, class_=AsyncSession, expire_on_commit=False
        )

        # Test connection
        async with _engine.begin() as conn:
            await conn.execute(text("SELECT 1"))

        logger.info("PostgreSQL connection established successfully")

        # Create tables if they don't exist
        await create_tables()

    except Exception as e:
        logger.error(f"Failed to initialize PostgreSQL connection: {e}")
        raise


async def create_tables() -> None:
    """Create all P&L tables if they don't exist."""
    global _engine

    if not _engine:
        raise RuntimeError("PostgreSQL engine not initialized")

    try:
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("P&L tables created/verified successfully")

    except Exception as e:
        logger.error(f"Failed to create P&L tables: {e}")
        raise


async def close_postgres() -> None:
    """Close PostgreSQL connection."""
    global _engine, _async_session_factory

    if _engine:
        await _engine.dispose()
        _engine = None
        _async_session_factory = None
        logger.info("PostgreSQL connection closed")


@asynccontextmanager
async def get_postgres_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async PostgreSQL session context manager."""
    global _async_session_factory

    if not _async_session_factory:
        await init_postgres()

    async with _async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_postgres_db() -> AsyncSession:
    """Get PostgreSQL session (for dependency injection)."""
    global _async_session_factory

    if not _async_session_factory:
        await init_postgres()

    return _async_session_factory()


def is_postgres_available() -> bool:
    """Check if PostgreSQL connection is available."""
    global _engine
    return _engine is not None


async def test_postgres_connection() -> bool:
    """Test PostgreSQL connection health."""
    try:
        async with get_postgres_session() as session:
            result = await session.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        logger.error(f"PostgreSQL health check failed: {e}")
        return False
