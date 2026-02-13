"""
Signal Ledger — Immutable record of every signal received from OMEN.

DESIGN:
  1. Every signal from OMEN is FIRST written to the ledger (before DB insert).
  2. The ledger is append-only — entries are never modified or deleted.
  3. Reconcile reads the ledger to find signals that failed to ingest.

This guarantees zero signal loss even if the DB insert fails.
"""

import uuid
from datetime import datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.models import SignalLedger
from riskcast.schemas.omen_signal import SignalEvent

logger = structlog.get_logger(__name__)


class LedgerService:
    """Manages the immutable signal ledger."""

    async def record(
        self,
        session: AsyncSession,
        event: SignalEvent,
    ) -> SignalLedger:
        """
        Record a signal event in the ledger (append-only).

        This MUST be called before attempting the main DB insert.
        Returns the ledger entry so the caller can update its status later.
        """
        entry = SignalLedger(
            signal_id=event.signal_id,
            payload=event.model_dump(mode="json"),
            status="received",
            recorded_at=datetime.utcnow(),
        )
        session.add(entry)
        await session.flush()

        logger.info(
            "ledger_recorded",
            signal_id=event.signal_id,
            ledger_id=str(entry.id),
        )
        return entry

    async def mark_ingested(
        self,
        session: AsyncSession,
        ledger_entry: SignalLedger,
        ack_id: str,
    ) -> None:
        """Mark a ledger entry as successfully ingested."""
        ledger_entry.status = "ingested"
        ledger_entry.ack_id = ack_id
        ledger_entry.ingested_at = datetime.utcnow()

    async def mark_failed(
        self,
        session: AsyncSession,
        ledger_entry: SignalLedger,
        error: str,
    ) -> None:
        """Mark a ledger entry as failed."""
        ledger_entry.status = "failed"
        ledger_entry.error_message = error[:2000]

    async def get_unprocessed(
        self,
        session: AsyncSession,
        since: datetime,
    ) -> list[SignalLedger]:
        """
        Get ledger entries that were received but never ingested.

        Used by reconcile to find missed signals.
        """
        result = await session.execute(
            select(SignalLedger)
            .where(
                SignalLedger.status.in_(["received", "failed"]),
                SignalLedger.recorded_at >= since,
            )
            .order_by(SignalLedger.recorded_at.asc())
        )
        return list(result.scalars().all())

    async def get_signal_ids_since(
        self,
        session: AsyncSession,
        since: datetime,
    ) -> set[str]:
        """Get all signal IDs recorded in ledger since a given time."""
        result = await session.execute(
            select(SignalLedger.signal_id).where(
                SignalLedger.recorded_at >= since,
            )
        )
        return {row[0] for row in result.all()}
