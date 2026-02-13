"""Database Configuration.

Provides async PostgreSQL and Redis connections.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import redis.asyncio as redis
import structlog
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

logger = structlog.get_logger(__name__)


# SQLAlchemy Base
class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""

    pass


# Database engine (lazy initialization)
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None

# Redis client (lazy initialization)
_redis_client: Optional[redis.Redis] = None


def get_engine() -> AsyncEngine:
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            echo=settings.debug,
        )
        logger.info("database_engine_created", url=settings.database_url.split("@")[-1])
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session for dependency injection.

    Usage:
        @app.get("/")
        async def endpoint(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session as context manager.

    Usage:
        async with get_db_context() as db:
            ...
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_redis_client() -> redis.Redis:
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info("redis_client_created", url=settings.redis_url.split("@")[-1])
    return _redis_client


async def close_connections() -> None:
    """Close all database connections."""
    global _engine, _redis_client

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("database_engine_closed")

    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
        logger.info("redis_client_closed")


async def init_db() -> None:
    """Initialize database (create tables)."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_initialized")


# Redis helper functions
class RedisCache:
    """Redis cache helper."""

    def __init__(self, prefix: str = "riskcast"):
        self.prefix = prefix

    def _key(self, key: str) -> str:
        """Generate prefixed key."""
        return f"{self.prefix}:{key}"

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        client = await get_redis_client()
        return await client.get(self._key(key))

    async def set(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None,
    ) -> None:
        """Set value in cache."""
        client = await get_redis_client()
        await client.set(
            self._key(key),
            value,
            ex=ttl or settings.redis_cache_ttl,
        )

    async def delete(self, key: str) -> None:
        """Delete value from cache."""
        client = await get_redis_client()
        await client.delete(self._key(key))

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        client = await get_redis_client()
        return await client.exists(self._key(key)) > 0


# Global cache instance
cache = RedisCache()
