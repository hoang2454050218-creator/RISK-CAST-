"""
OMEN Signal Ingest Service.

Handles the full ingest pipeline:
  1. Write to Ledger (immutable, always succeeds first)
  2. Check idempotency (deduplicate by signal_id)
  3. Insert into OmenIngestSignal table
  4. Return ack_id

This is the CORE integration point between OMEN and RiskCast.
"""

import uuid
from datetime import datetime
from decimal import Decimal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.models import OmenIngestSignal
from riskcast.schemas.omen_signal import IngestAck, SignalEvent
from riskcast.services.ledger import LedgerService

logger = structlog.get_logger(__name__)

# ── Metrics counters (in-memory, exported via /metrics) ──────────────────

_ingest_metrics = {
    "total_received": 0,
    "total_ingested": 0,
    "total_duplicates": 0,
    "total_errors": 0,
}


def get_ingest_metrics() -> dict:
    """Get current ingest metrics snapshot."""
    return dict(_ingest_metrics)


class IngestService:
    """
    Ingest pipeline for OMEN signals.

    Flow:
      SignalEvent → Ledger → Idempotency check → DB insert → ack_id
    """

    def __init__(self) -> None:
        self.ledger = LedgerService()

    async def ingest(
        self,
        session: AsyncSession,
        event: SignalEvent,
    ) -> tuple[IngestAck, int]:
        """
        Ingest a signal event from OMEN.

        Returns:
            (IngestAck, http_status_code)
            200 for new signal, 409 for duplicate (both are success).
        """
        _ingest_metrics["total_received"] += 1

        # ── Step 1: Check idempotency FIRST (fast path for duplicates) ──
        existing = await self._find_existing(session, event.signal_id)
        if existing:
            _ingest_metrics["total_duplicates"] += 1
            logger.info(
                "signal_duplicate",
                signal_id=event.signal_id,
                ack_id=existing.ack_id,
            )
            return IngestAck(ack_id=existing.ack_id, duplicate=True), 409

        # ── Step 2: Record in Ledger (immutable, before DB insert) ───────
        ledger_entry = await self.ledger.record(session, event)

        # ── Step 3: Insert into main signal store ────────────────────────
        ack_id = f"riskcast-ack-{uuid.uuid4().hex[:8]}"
        try:
            signal_row = self._build_signal_row(event, ack_id)
            session.add(signal_row)
            await session.flush()

            # Mark ledger as ingested
            await self.ledger.mark_ingested(session, ledger_entry, ack_id)

            _ingest_metrics["total_ingested"] += 1
            logger.info(
                "signal_ingested",
                signal_id=event.signal_id,
                ack_id=ack_id,
                category=event.signal.category,
            )

            # ── Auto-trigger alerts for high-severity signals ──────
            try:
                from riskcast.alerting.auto_trigger import on_signal_ingested
                await on_signal_ingested(
                    signal_id=event.signal_id,
                    severity_score=float(event.signal.confidence_score) * 100,
                    confidence_score=float(event.signal.confidence_score),
                    category=event.signal.category,
                    title=event.signal.title,
                )
            except Exception as alert_err:
                logger.debug("signal_alert_skip", error=str(alert_err))

            return IngestAck(ack_id=ack_id), 200

        except Exception as e:
            _ingest_metrics["total_errors"] += 1
            await self.ledger.mark_failed(session, ledger_entry, str(e))
            logger.error(
                "signal_ingest_failed",
                signal_id=event.signal_id,
                error=str(e),
            )
            raise

    async def replay_from_ledger(
        self,
        session: AsyncSession,
        signal_id: str,
        payload: dict,
    ) -> tuple[IngestAck, bool]:
        """
        Replay a signal from ledger data (used by reconcile).

        Returns (ack, was_new). was_new=False means it already existed.
        """
        existing = await self._find_existing(session, signal_id)
        if existing:
            return IngestAck(ack_id=existing.ack_id, duplicate=True), False

        event = SignalEvent.model_validate(payload)
        ack_id = f"riskcast-ack-{uuid.uuid4().hex[:8]}"
        signal_row = self._build_signal_row(event, ack_id)
        session.add(signal_row)
        await session.flush()

        _ingest_metrics["total_ingested"] += 1
        logger.info("signal_replayed", signal_id=signal_id, ack_id=ack_id)
        return IngestAck(ack_id=ack_id), True

    # ── Private helpers ──────────────────────────────────────────────────

    async def _find_existing(
        self,
        session: AsyncSession,
        signal_id: str,
    ) -> OmenIngestSignal | None:
        """Check if signal_id already exists (idempotency)."""
        result = await session.execute(
            select(OmenIngestSignal).where(
                OmenIngestSignal.signal_id == signal_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _build_signal_row(event: SignalEvent, ack_id: str) -> OmenIngestSignal:
        """Build an OmenIngestSignal ORM instance from a SignalEvent."""
        sig = event.signal
        return OmenIngestSignal(
            signal_id=event.signal_id,
            ack_id=ack_id,
            schema_version=event.schema_version,
            deterministic_trace_id=event.deterministic_trace_id,
            input_event_hash=event.input_event_hash,
            source_event_id=event.source_event_id,
            ruleset_version=event.ruleset_version or sig.ruleset_version,
            observed_at=event.observed_at,
            emitted_at=event.emitted_at,
            title=sig.title,
            description=sig.description,
            probability=Decimal(str(sig.probability)),
            confidence_score=Decimal(str(sig.confidence_score)),
            confidence_level=sig.confidence_level,
            category=sig.category,
            tags=sig.tags,
            geographic=sig.geographic.model_dump() if sig.geographic else None,
            temporal=sig.temporal.model_dump() if sig.temporal else None,
            evidence=[e.model_dump() for e in sig.evidence],
            raw_payload=event.model_dump(mode="json"),
            ingested_at=datetime.utcnow(),
        )
