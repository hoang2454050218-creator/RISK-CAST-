"""
Signal Service — Upsert pattern for signal lifecycle.

Uses ORM for cross-database compatibility (SQLite dev + PostgreSQL prod).
"""

import uuid
from datetime import datetime, timedelta

import structlog
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.analyzers.base import InternalSignal
from riskcast.db.models import Signal

logger = structlog.get_logger(__name__)


class SignalService:
    """Manages signal upsert and lifecycle."""

    async def upsert_signals(
        self,
        session: AsyncSession,
        company_id: str,
        signals: list[InternalSignal],
    ) -> int:
        """
        Upsert signals using ORM.

        For each signal:
        - Check if exists by composite key
        - Update if exists, insert if new
        - Deactivate stale signals from scanned sources
        """
        if not signals:
            return 0

        upserted = 0
        cid = uuid.UUID(company_id) if isinstance(company_id, str) else company_id

        for signal in signals:
            entity_id = uuid.UUID(signal.entity_id) if signal.entity_id else None

            # Try to find existing
            result = await session.execute(
                select(Signal).where(
                    and_(
                        Signal.company_id == cid,
                        Signal.source == signal.source,
                        Signal.signal_type == signal.signal_type,
                        Signal.entity_type == signal.entity_type,
                        Signal.entity_id == entity_id,
                    )
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing
                existing.confidence = signal.confidence
                existing.severity_score = signal.severity_score
                existing.evidence = signal.evidence
                existing.context = signal.context
                existing.is_active = True
                existing.updated_at = datetime.utcnow()
            else:
                # Insert new
                new_signal = Signal(
                    company_id=cid,
                    source=signal.source,
                    signal_type=signal.signal_type,
                    entity_type=signal.entity_type,
                    entity_id=entity_id,
                    confidence=signal.confidence,
                    severity_score=signal.severity_score,
                    evidence=signal.evidence,
                    context=signal.context,
                    is_active=True,
                )
                session.add(new_signal)

            upserted += 1

        await session.flush()

        # Deactivate stale signals from scanned sources
        scanned_sources = {s.source for s in signals}
        if scanned_sources:
            cutoff = datetime.utcnow() - timedelta(minutes=1)
            stale = await session.execute(
                select(Signal).where(
                    and_(
                        Signal.company_id == cid,
                        Signal.source.in_(list(scanned_sources)),
                        Signal.is_active == True,  # noqa: E712
                        Signal.updated_at < cutoff,
                    )
                )
            )
            for s in stale.scalars().all():
                s.is_active = False
                s.updated_at = datetime.utcnow()

        logger.info(
            "signals_upserted",
            company_id=company_id,
            count=upserted,
            sources=list(scanned_sources),
        )
        return upserted

    async def expire_stale_signals(self, session: AsyncSession) -> int:
        """Deactivate signals past their expiry date."""
        now = datetime.utcnow()
        result = await session.execute(
            select(Signal).where(
                and_(
                    Signal.is_active == True,  # noqa: E712
                    Signal.expires_at.isnot(None),
                    Signal.expires_at < now,
                )
            )
        )
        count = 0
        for s in result.scalars().all():
            s.is_active = False
            count += 1

        if count:
            logger.info("signals_expired", count=count)
        return count
