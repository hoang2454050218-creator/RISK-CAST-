"""Company repository — not filtered by RLS (companies table has no RLS)."""

import uuid
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.models import Company


class CompanyRepository:
    """Company CRUD — no RLS on companies table."""

    async def get_by_id(self, db: AsyncSession, id: uuid.UUID) -> Optional[Company]:
        result = await db.execute(select(Company).where(Company.id == id))
        return result.scalar_one_or_none()

    async def get_by_slug(self, db: AsyncSession, slug: str) -> Optional[Company]:
        result = await db.execute(select(Company).where(Company.slug == slug))
        return result.scalar_one_or_none()

    async def list(self, db: AsyncSession, offset: int = 0, limit: int = 50) -> Sequence[Company]:
        result = await db.execute(
            select(Company).order_by(Company.created_at.desc()).offset(offset).limit(limit)
        )
        return result.scalars().all()

    async def update(self, db: AsyncSession, id: uuid.UUID, **kwargs) -> Optional[Company]:
        obj = await self.get_by_id(db, id)
        if obj is None:
            return None
        for key, value in kwargs.items():
            if value is not None:
                setattr(obj, key, value)
        await db.flush()
        await db.refresh(obj)
        return obj


company_repo = CompanyRepository()
