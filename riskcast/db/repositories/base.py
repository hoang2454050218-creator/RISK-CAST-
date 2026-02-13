"""
Generic async CRUD repository.

All queries are automatically filtered by RLS (via SET LOCAL in middleware).
No manual WHERE company_id = needed.
"""

import uuid
from typing import Any, Generic, Optional, Sequence, Type, TypeVar

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.engine import Base

ModelT = TypeVar("ModelT", bound=Base)
CreateSchemaT = TypeVar("CreateSchemaT", bound=BaseModel)
UpdateSchemaT = TypeVar("UpdateSchemaT", bound=BaseModel)


class BaseRepository(Generic[ModelT, CreateSchemaT, UpdateSchemaT]):
    """
    Generic async CRUD operations.

    RLS handles tenant isolation — no need for manual company_id filters.
    """

    def __init__(self, model: Type[ModelT]):
        self.model = model

    async def create(
        self,
        db: AsyncSession,
        data: CreateSchemaT,
        company_id: uuid.UUID,
        **extra_fields: Any,
    ) -> ModelT:
        """Create a new record."""
        values = data.model_dump(exclude_unset=True, by_alias=False)
        # Remap metadata alias if present
        # model_dump(by_alias=False) returns "metadata" (field name), not "metadata_extra" (alias)
        if "metadata" in values:
            values["metadata_"] = values.pop("metadata")
        elif "metadata_extra" in values:
            values["metadata_"] = values.pop("metadata_extra")
        values["company_id"] = company_id
        values.update(extra_fields)

        obj = self.model(**values)
        db.add(obj)
        await db.flush()
        await db.refresh(obj)
        return obj

    async def get_by_id(self, db: AsyncSession, id: uuid.UUID) -> Optional[ModelT]:
        """Get a single record by ID. RLS ensures tenant isolation."""
        result = await db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        db: AsyncSession,
        offset: int = 0,
        limit: int = 50,
        order_by: str = "created_at",
        descending: bool = True,
    ) -> Sequence[ModelT]:
        """List records with pagination. RLS ensures tenant isolation."""
        col = getattr(self.model, order_by, self.model.created_at)
        stmt = select(self.model).order_by(
            col.desc() if descending else col.asc()
        ).offset(offset).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def count(self, db: AsyncSession) -> int:
        """Count records visible to current tenant."""
        result = await db.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar_one()

    async def update(
        self,
        db: AsyncSession,
        id: uuid.UUID,
        data: UpdateSchemaT,
    ) -> Optional[ModelT]:
        """Update a record. RLS ensures you can only update your own."""
        obj = await self.get_by_id(db, id)
        if obj is None:
            return None

        values = data.model_dump(exclude_unset=True, by_alias=False)
        # Remap metadata alias if present
        if "metadata" in values:
            values["metadata_"] = values.pop("metadata")
        elif "metadata_extra" in values:
            values["metadata_"] = values.pop("metadata_extra")

        for key, value in values.items():
            if value is not None:
                setattr(obj, key, value)

        await db.flush()
        await db.refresh(obj)
        return obj

    async def delete(self, db: AsyncSession, id: uuid.UUID) -> bool:
        """Delete a record. RLS ensures you can only delete your own."""
        obj = await self.get_by_id(db, id)
        if obj is None:
            return False
        await db.delete(obj)
        await db.flush()
        return True
