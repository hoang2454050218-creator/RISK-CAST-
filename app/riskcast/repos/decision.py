"""Decision Repository - Data Access Layer for Decisions.

Provides persistence for decision objects.

Implementations:
- InMemoryDecisionRepository: For development/testing (DEPRECATED)
- PostgresDecisionRepository: For production
- CachedDecisionRepository: PostgreSQL + Redis caching
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List
import uuid

import structlog
from sqlalchemy import select, and_, or_, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.riskcast.schemas.decision import DecisionObject
from app.riskcast.constants import Severity, Urgency

logger = structlog.get_logger(__name__)


# ============================================================================
# EXCEPTIONS
# ============================================================================


class DecisionNotFoundError(Exception):
    """Decision not found in repository."""

    def __init__(self, decision_id: str):
        self.decision_id = decision_id
        super().__init__(f"Decision not found: {decision_id}")


class DuplicateDecisionError(Exception):
    """Decision already exists."""

    def __init__(self, decision_id: str):
        self.decision_id = decision_id
        super().__init__(f"Decision already exists: {decision_id}")


# ============================================================================
# ABSTRACT REPOSITORY INTERFACE
# ============================================================================


class DecisionRepositoryInterface(ABC):
    """Abstract interface for decision repository."""

    @abstractmethod
    async def save(self, decision: DecisionObject) -> DecisionObject:
        """Save a decision."""
        pass

    @abstractmethod
    async def get(self, decision_id: str) -> Optional[DecisionObject]:
        """Get a decision by ID."""
        pass

    @abstractmethod
    async def get_by_customer(
        self,
        customer_id: str,
        include_expired: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[DecisionObject], int]:
        """Get decisions for a customer with pagination."""
        pass

    @abstractmethod
    async def get_by_signal(
        self,
        signal_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[DecisionObject], int]:
        """Get decisions for a signal with pagination."""
        pass

    @abstractmethod
    async def get_active(
        self,
        customer_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[DecisionObject], int]:
        """Get active (non-expired) decisions with pagination."""
        pass

    @abstractmethod
    async def update(
        self,
        decision_id: str,
        was_acted_upon: Optional[bool] = None,
        user_feedback: Optional[str] = None,
    ) -> Optional[DecisionObject]:
        """Update decision tracking fields."""
        pass

    @abstractmethod
    async def delete_expired(self) -> int:
        """Delete expired decisions. Returns count deleted."""
        pass

    @abstractmethod
    async def count(
        self,
        customer_id: Optional[str] = None,
        include_expired: bool = True,
    ) -> int:
        """Count decisions."""
        pass


# ============================================================================
# POSTGRESQL IMPLEMENTATION
# ============================================================================


class PostgresDecisionRepository(DecisionRepositoryInterface):
    """
    PostgreSQL decision repository for production.

    Uses async SQLAlchemy for database operations.
    Thread-safe and supports concurrent requests.
    """

    def __init__(self, session: AsyncSession):
        """Initialize with database session."""
        self._session = session

    def _decision_from_model(self, model: "DecisionModel") -> DecisionObject:
        """Convert SQLAlchemy model to Pydantic model."""
        from app.riskcast.schemas.decision import (
            Q1WhatIsHappening,
            Q2WhenWillItHappen,
            Q3HowBadIsIt,
            Q4WhyIsThisHappening,
            Q5WhatToDoNow,
            Q6HowConfident,
            Q7WhatIfNothing,
        )

        return DecisionObject(
            decision_id=model.decision_id,
            customer_id=model.customer_id,
            signal_id=model.signal_id,
            q1_what=Q1WhatIsHappening(**model.q1_what),
            q2_when=Q2WhenWillItHappen(**model.q2_when),
            q3_severity=Q3HowBadIsIt(**model.q3_severity),
            q4_why=Q4WhyIsThisHappening(**model.q4_why),
            q5_action=Q5WhatToDoNow(**model.q5_action),
            q6_confidence=Q6HowConfident(**model.q6_confidence),
            q7_inaction=Q7WhatIfNothing(**model.q7_inaction),
            alternative_actions=model.alternative_actions or [],
            generated_at=model.created_at,
            expires_at=model.valid_until,
            was_acted_upon=model.is_acted_upon,
            user_feedback=model.customer_action,
        )

    def _model_from_decision(self, decision: DecisionObject) -> "DecisionModel":
        """Convert Pydantic model to SQLAlchemy model."""
        from app.db.models import DecisionModel

        return DecisionModel(
            decision_id=decision.decision_id,
            customer_id=decision.customer_id,
            signal_id=decision.signal_id,
            chokepoint=decision.q1_what.affected_chokepoint,
            severity=decision.q3_severity.severity.value,
            urgency=decision.q2_when.urgency.value,
            q1_what=decision.q1_what.model_dump(mode="json"),
            q2_when=decision.q2_when.model_dump(mode="json"),
            q3_severity=decision.q3_severity.model_dump(mode="json"),
            q4_why=decision.q4_why.model_dump(mode="json"),
            q5_action=decision.q5_action.model_dump(mode="json"),
            q6_confidence=decision.q6_confidence.model_dump(mode="json"),
            q7_inaction=decision.q7_inaction.model_dump(mode="json"),
            exposure_usd=decision.q3_severity.total_exposure_usd,
            potential_loss_usd=decision.q7_inaction.expected_loss_if_nothing,
            potential_delay_days=decision.q3_severity.expected_delay_days,
            recommended_action=decision.q5_action.action_type,
            action_cost_usd=decision.q5_action.estimated_cost_usd,
            action_deadline=decision.q5_action.deadline,
            confidence_score=decision.q6_confidence.score,
            valid_until=decision.expires_at,
            is_expired=decision.is_expired,
            alternative_actions=decision.alternative_actions,
        )

    async def save(self, decision: DecisionObject) -> DecisionObject:
        """Save a decision."""
        from app.db.models import DecisionModel

        # Check for existing
        existing = await self.get(decision.decision_id)
        if existing:
            raise DuplicateDecisionError(decision.decision_id)

        model = self._model_from_decision(decision)
        self._session.add(model)
        await self._session.flush()

        logger.info(
            "decision_saved",
            decision_id=decision.decision_id,
            customer_id=decision.customer_id,
            signal_id=decision.signal_id,
        )

        return decision

    async def get(self, decision_id: str) -> Optional[DecisionObject]:
        """Get a decision by ID."""
        from app.db.models import DecisionModel

        result = await self._session.execute(
            select(DecisionModel).where(DecisionModel.decision_id == decision_id)
        )
        model = result.scalar_one_or_none()
        return self._decision_from_model(model) if model else None

    async def get_by_customer(
        self,
        customer_id: str,
        include_expired: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[DecisionObject], int]:
        """Get decisions for a customer with pagination."""
        from app.db.models import DecisionModel

        # Build query
        conditions = [DecisionModel.customer_id == customer_id]
        if not include_expired:
            conditions.append(DecisionModel.is_expired == False)

        # Count total
        count_result = await self._session.execute(
            select(func.count(DecisionModel.id)).where(and_(*conditions))
        )
        total = count_result.scalar_one()

        # Get page
        result = await self._session.execute(
            select(DecisionModel)
            .where(and_(*conditions))
            .order_by(DecisionModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        models = result.scalars().all()

        decisions = [self._decision_from_model(m) for m in models]
        return decisions, total

    async def get_by_signal(
        self,
        signal_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[DecisionObject], int]:
        """Get decisions for a signal with pagination."""
        from app.db.models import DecisionModel

        # Count total
        count_result = await self._session.execute(
            select(func.count(DecisionModel.id)).where(
                DecisionModel.signal_id == signal_id
            )
        )
        total = count_result.scalar_one()

        # Get page
        result = await self._session.execute(
            select(DecisionModel)
            .where(DecisionModel.signal_id == signal_id)
            .order_by(DecisionModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        models = result.scalars().all()

        decisions = [self._decision_from_model(m) for m in models]
        return decisions, total

    async def get_active(
        self,
        customer_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[DecisionObject], int]:
        """Get active (non-expired) decisions with pagination."""
        from app.db.models import DecisionModel

        conditions = [
            DecisionModel.is_expired == False,
            DecisionModel.valid_until > datetime.utcnow(),
        ]
        if customer_id:
            conditions.append(DecisionModel.customer_id == customer_id)

        # Count total
        count_result = await self._session.execute(
            select(func.count(DecisionModel.id)).where(and_(*conditions))
        )
        total = count_result.scalar_one()

        # Get page
        result = await self._session.execute(
            select(DecisionModel)
            .where(and_(*conditions))
            .order_by(DecisionModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        models = result.scalars().all()

        decisions = [self._decision_from_model(m) for m in models]
        return decisions, total

    async def update(
        self,
        decision_id: str,
        was_acted_upon: Optional[bool] = None,
        user_feedback: Optional[str] = None,
    ) -> Optional[DecisionObject]:
        """Update decision tracking fields."""
        from app.db.models import DecisionModel

        result = await self._session.execute(
            select(DecisionModel).where(DecisionModel.decision_id == decision_id)
        )
        model = result.scalar_one_or_none()

        if not model:
            return None

        if was_acted_upon is not None:
            model.is_acted_upon = was_acted_upon
            model.acknowledged_at = datetime.utcnow()

        if user_feedback is not None:
            model.customer_action = user_feedback

        await self._session.flush()

        logger.info(
            "decision_updated",
            decision_id=decision_id,
            was_acted_upon=was_acted_upon,
            has_feedback=user_feedback is not None,
        )

        return self._decision_from_model(model)

    async def delete_expired(self) -> int:
        """Delete expired decisions. Returns count deleted."""
        from app.db.models import DecisionModel

        # First mark as expired
        await self._session.execute(
            update(DecisionModel)
            .where(
                and_(
                    DecisionModel.is_expired == False,
                    DecisionModel.valid_until < datetime.utcnow(),
                )
            )
            .values(is_expired=True)
        )

        # Then delete old expired (older than 30 days)
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=30)
        result = await self._session.execute(
            select(func.count(DecisionModel.id)).where(
                and_(
                    DecisionModel.is_expired == True,
                    DecisionModel.created_at < cutoff,
                )
            )
        )
        count = result.scalar_one()

        if count > 0:
            await self._session.execute(
                DecisionModel.__table__.delete().where(
                    and_(
                        DecisionModel.is_expired == True,
                        DecisionModel.created_at < cutoff,
                    )
                )
            )
            await self._session.flush()

            logger.info("expired_decisions_deleted", count=count)

        return count

    async def count(
        self,
        customer_id: Optional[str] = None,
        include_expired: bool = True,
    ) -> int:
        """Count decisions."""
        from app.db.models import DecisionModel

        conditions = []
        if customer_id:
            conditions.append(DecisionModel.customer_id == customer_id)
        if not include_expired:
            conditions.append(DecisionModel.is_expired == False)

        query = select(func.count(DecisionModel.id))
        if conditions:
            query = query.where(and_(*conditions))

        result = await self._session.execute(query)
        return result.scalar_one()

    async def get_summary(
        self,
        customer_id: Optional[str] = None,
    ) -> dict:
        """Get summary statistics."""
        from app.db.models import DecisionModel

        conditions = []
        if customer_id:
            conditions.append(DecisionModel.customer_id == customer_id)

        # Total count
        total_query = select(func.count(DecisionModel.id))
        if conditions:
            total_query = total_query.where(and_(*conditions))
        total = (await self._session.execute(total_query)).scalar_one()

        # Active count
        active_conditions = conditions + [DecisionModel.is_expired == False]
        active = (
            await self._session.execute(
                select(func.count(DecisionModel.id)).where(and_(*active_conditions))
            )
        ).scalar_one()

        # Acted upon count
        acted_conditions = conditions + [DecisionModel.is_acted_upon == True]
        acted = (
            await self._session.execute(
                select(func.count(DecisionModel.id)).where(and_(*acted_conditions))
            )
        ).scalar_one()

        # Total exposure
        exposure_query = select(func.sum(DecisionModel.exposure_usd)).where(
            and_(*active_conditions)
        )
        total_exposure = (await self._session.execute(exposure_query)).scalar_one() or 0

        return {
            "total_decisions": total,
            "active_decisions": active,
            "expired_decisions": total - active,
            "acted_upon": acted,
            "total_exposure_usd": float(total_exposure),
        }


# ============================================================================
# CACHED REPOSITORY (PostgreSQL + Redis)
# ============================================================================


class CachedDecisionRepository(DecisionRepositoryInterface):
    """
    Decision repository with Redis caching layer.

    Combines PostgreSQL persistence with Redis caching for performance.
    Cache is invalidated on writes.
    """

    def __init__(
        self,
        postgres_repo: PostgresDecisionRepository,
        cache_ttl: int = 300,  # 5 minutes
    ):
        self._postgres = postgres_repo
        self._cache_ttl = cache_ttl

    async def _get_cache_key(self, decision_id: str) -> str:
        return f"decision:{decision_id}"

    async def _get_from_cache(self, decision_id: str) -> Optional[DecisionObject]:
        from app.core.database import cache

        key = await self._get_cache_key(decision_id)
        cached = await cache.get(key)
        if cached:
            try:
                data = json.loads(cached)
                # Import all Q schemas
                from app.riskcast.schemas.decision import (
                    Q1WhatIsHappening,
                    Q2WhenWillItHappen,
                    Q3HowBadIsIt,
                    Q4WhyIsThisHappening,
                    Q5WhatToDoNow,
                    Q6HowConfident,
                    Q7WhatIfNothing,
                )

                return DecisionObject(**data)
            except Exception:
                pass
        return None

    async def _set_cache(self, decision: DecisionObject) -> None:
        from app.core.database import cache

        key = await self._get_cache_key(decision.decision_id)
        await cache.set(
            key,
            decision.model_dump_json(),
            ttl=self._cache_ttl,
        )

    async def _invalidate_cache(self, decision_id: str) -> None:
        from app.core.database import cache

        key = await self._get_cache_key(decision_id)
        await cache.delete(key)

    async def save(self, decision: DecisionObject) -> DecisionObject:
        result = await self._postgres.save(decision)
        await self._set_cache(result)
        return result

    async def get(self, decision_id: str) -> Optional[DecisionObject]:
        # Try cache first
        cached = await self._get_from_cache(decision_id)
        if cached:
            logger.debug("decision_cache_hit", decision_id=decision_id)
            return cached

        # Fall back to database
        decision = await self._postgres.get(decision_id)
        if decision:
            await self._set_cache(decision)
            logger.debug("decision_cache_miss", decision_id=decision_id)

        return decision

    async def get_by_customer(
        self,
        customer_id: str,
        include_expired: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[DecisionObject], int]:
        # Always go to database for list queries
        return await self._postgres.get_by_customer(
            customer_id, include_expired, limit, offset
        )

    async def get_by_signal(
        self,
        signal_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[DecisionObject], int]:
        return await self._postgres.get_by_signal(signal_id, limit, offset)

    async def get_active(
        self,
        customer_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[DecisionObject], int]:
        return await self._postgres.get_active(customer_id, limit, offset)

    async def update(
        self,
        decision_id: str,
        was_acted_upon: Optional[bool] = None,
        user_feedback: Optional[str] = None,
    ) -> Optional[DecisionObject]:
        result = await self._postgres.update(decision_id, was_acted_upon, user_feedback)
        if result:
            await self._invalidate_cache(decision_id)
        return result

    async def delete_expired(self) -> int:
        return await self._postgres.delete_expired()

    async def count(
        self,
        customer_id: Optional[str] = None,
        include_expired: bool = True,
    ) -> int:
        return await self._postgres.count(customer_id, include_expired)


# ============================================================================
# FACTORY
# ============================================================================


def create_decision_repository(
    session: AsyncSession,
    use_cache: bool = True,
    cache_ttl: int = 300,
) -> DecisionRepositoryInterface:
    """
    Create decision repository instance.

    Args:
        session: Database session
        use_cache: Whether to use Redis caching
        cache_ttl: Cache TTL in seconds

    Returns:
        DecisionRepositoryInterface implementation
    """
    postgres_repo = PostgresDecisionRepository(session)

    if use_cache:
        return CachedDecisionRepository(postgres_repo, cache_ttl)

    return postgres_repo


def get_postgres_decision_repository(
    session: AsyncSession,
) -> PostgresDecisionRepository:
    """Get PostgreSQL decision repository with given session."""
    return PostgresDecisionRepository(session)
