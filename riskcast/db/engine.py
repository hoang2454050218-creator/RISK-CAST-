"""
Database engine, session factory, and declarative base for RiskCast V2.

Uses async SQLAlchemy 2.0 with asyncpg.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from riskcast.config import settings

logger = structlog.get_logger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for V2 models."""

    pass


# Lazy-initialized singletons
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine() -> AsyncEngine:
    """Get or create the async database engine."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.async_database_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_recycle=settings.db_pool_recycle,
            echo=settings.debug,
        )
        logger.info("v2_database_engine_created")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the async session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session with automatic cleanup."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize the database engine and create tables if needed.
    
    In development mode, auto-creates all V2 tables from ORM models.
    In production, expects tables to be managed via Alembic migrations.
    """
    engine = get_engine()

    # Import all models so Base.metadata is populated
    import riskcast.db.models  # noqa: F401

    if settings.environment.lower() == "development":
        # Dev mode: auto-create all V2 tables from models
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("v2_tables_created", mode="development", db=settings.async_database_url.split("@")[-1] if "@" in settings.async_database_url else "sqlite")
    else:
        logger.info("v2_skipping_auto_create", reason="production uses alembic")

    logger.info("v2_database_initialized")


async def close_db() -> None:
    """Close the database engine (call at shutdown)."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("v2_database_closed")
