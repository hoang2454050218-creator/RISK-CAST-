"""
FastAPI dependencies for authentication and tenant context.

For SQLite (dev): no RLS, just pass company_id via request.state.
For PostgreSQL (prod): SET LOCAL for RLS enforcement.
"""

import uuid

from fastapi import HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.config import settings
from riskcast.db.engine import get_session_factory


async def get_db(request: Request) -> AsyncSession:
    """
    Provide an async DB session with tenant context.

    PostgreSQL: SET LOCAL for RLS.
    SQLite: no RLS, queries filter by company_id in repositories.
    """
    factory = get_session_factory()
    async with factory() as session:
        company_id = getattr(request.state, "company_id", None)

        # SET tenant context for PostgreSQL RLS
        # NOTE: asyncpg does not support parameterized SET LOCAL,
        # so we interpolate the UUID directly. This is safe because
        # company_id is a validated UUID from the JWT token.
        if company_id and "postgresql" in settings.async_database_url:
            cid = str(company_id).replace("'", "")  # extra safety
            await session.execute(
                text(f"SET LOCAL app.current_company_id = '{cid}'")
            )

        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_company_id(request: Request) -> uuid.UUID:
    """Extract company_id from request state (set by TenantMiddleware)."""
    company_id = getattr(request.state, "company_id", None)
    if not company_id:
        raise HTTPException(status_code=401, detail="Missing tenant context")
    return uuid.UUID(str(company_id))


def get_user_id(request: Request) -> uuid.UUID:
    """Extract user_id from request state (set by TenantMiddleware)."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user context")
    return uuid.UUID(str(user_id))
