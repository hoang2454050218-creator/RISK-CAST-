"""
Database Session Module.

Production-grade database session management with:
- Async SQLAlchemy 2.0
- Connection pooling
- Health monitoring
- Graceful shutdown
"""

from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from sqlalchemy import event, text
import structlog

from app.core.config import settings
from app.core.metrics import METRICS

logger = structlog.get_logger(__name__)


# ============================================================================
# ENGINE CONFIGURATION
# ============================================================================


def create_engine(
    database_url: Optional[str] = None,
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_pre_ping: bool = True,
    pool_recycle: int = 3600,
    echo: bool = False,
) -> AsyncEngine:
    """
    Create an async database engine with production settings.
    
    Args:
        database_url: Database connection string
        pool_size: Number of connections in the pool
        max_overflow: Max connections beyond pool_size
        pool_pre_ping: Test connections before use
        pool_recycle: Recycle connections after N seconds
        echo: Log SQL statements
    
    Returns:
        Configured async engine
    """
    url = database_url or settings.database_url
    
    # Use NullPool for testing, QueuePool for production
    pool_class = NullPool if settings.testing else AsyncAdaptedQueuePool
    
    engine = create_async_engine(
        url,
        poolclass=pool_class,
        pool_size=pool_size if pool_class != NullPool else None,
        max_overflow=max_overflow if pool_class != NullPool else None,
        pool_pre_ping=pool_pre_ping,
        pool_recycle=pool_recycle,
        echo=echo,
        future=True,
    )
    
    # Register event listeners for metrics
    _register_engine_events(engine)
    
    logger.info(
        "database_engine_created",
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_class=pool_class.__name__,
    )
    
    return engine


def _register_engine_events(engine: AsyncEngine) -> None:
    """Register engine event listeners for monitoring."""
    
    @event.listens_for(engine.sync_engine, "checkout")
    def on_checkout(dbapi_conn, connection_record, connection_proxy):
        """Track connection checkout."""
        METRICS.db_connections_active.inc()
    
    @event.listens_for(engine.sync_engine, "checkin")
    def on_checkin(dbapi_conn, connection_record):
        """Track connection checkin."""
        METRICS.db_connections_active.dec()


# ============================================================================
# SESSION FACTORY
# ============================================================================


def create_session_factory(
    engine: AsyncEngine,
    expire_on_commit: bool = False,
    autocommit: bool = False,
    autoflush: bool = False,
) -> async_sessionmaker[AsyncSession]:
    """
    Create a session factory.
    
    Args:
        engine: Database engine
        expire_on_commit: Expire objects on commit
        autocommit: Auto-commit mode
        autoflush: Auto-flush mode
    
    Returns:
        Session factory
    """
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=expire_on_commit,
        autocommit=autocommit,
        autoflush=autoflush,
    )


# ============================================================================
# GLOBAL INSTANCES
# ============================================================================

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine() -> AsyncEngine:
    """Get the global database engine."""
    global _engine
    if _engine is None:
        _engine = create_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get the global session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = create_session_factory(get_engine())
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database sessions.
    
    Usage:
        @app.get("/items")
        async def get_items(session: AsyncSession = Depends(get_session)):
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
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions.
    
    Usage:
        async with get_session_context() as session:
            result = await session.execute(query)
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ============================================================================
# LIFECYCLE
# ============================================================================


async def init_db() -> None:
    """Initialize database connection on startup."""
    engine = get_engine()
    
    # Test connection
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    
    logger.info("database_initialized")


async def close_db() -> None:
    """Close database connection on shutdown."""
    global _engine, _session_factory
    
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
    
    logger.info("database_closed")


# ============================================================================
# TRANSACTION HELPERS
# ============================================================================


@asynccontextmanager
async def transaction(session: AsyncSession):
    """
    Context manager for explicit transactions.
    
    Usage:
        async with transaction(session):
            await session.execute(...)
            await session.execute(...)
    """
    try:
        yield
        await session.commit()
    except Exception:
        await session.rollback()
        raise


class UnitOfWork:
    """
    Unit of Work pattern for managing transactions.
    
    Usage:
        async with UnitOfWork() as uow:
            customer = await uow.customers.get(customer_id)
            customer.name = "New Name"
            await uow.commit()
    """
    
    def __init__(self, session_factory: Optional[async_sessionmaker] = None):
        self._session_factory = session_factory or get_session_factory()
        self._session: Optional[AsyncSession] = None
    
    async def __aenter__(self) -> "UnitOfWork":
        self._session = self._session_factory()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        await self._session.close()
    
    @property
    def session(self) -> AsyncSession:
        """Get the current session."""
        if self._session is None:
            raise RuntimeError("UnitOfWork not started")
        return self._session
    
    async def commit(self) -> None:
        """Commit the transaction."""
        await self._session.commit()
    
    async def rollback(self) -> None:
        """Rollback the transaction."""
        await self._session.rollback()
    
    async def flush(self) -> None:
        """Flush pending changes."""
        await self._session.flush()
