"""
Signal-to-Decision Traceability — Full audit chain.

Traces the complete path:
  Signal (OMEN) → Ingest → Risk Assessment → Decision → Outcome

Every step is traceable with timestamps, IDs, and metadata.
This is the core of auditability and regulatory compliance.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.models import OmenIngestSignal, Outcome, Signal, SignalLedger

logger = structlog.get_logger(__name__)


class TraceStep:
    """A single step in the signal-to-decision trace."""

    def __init__(
        self,
        step_name: str,
        step_id: str,
        timestamp: str,
        status: str,
        data: dict,
    ):
        self.step_name = step_name
        self.step_id = step_id
        self.timestamp = timestamp
        self.status = status
        self.data = data

    def to_dict(self) -> dict:
        return {
            "step": self.step_name,
            "id": self.step_id,
            "timestamp": self.timestamp,
            "status": self.status,
            "data": self.data,
        }


class TraceChain:
    """Complete trace from signal to decision/outcome."""

    def __init__(
        self,
        trace_id: str,
        signal_id: str,
        steps: list[TraceStep],
        is_complete: bool,
        missing_steps: list[str],
    ):
        self.trace_id = trace_id
        self.signal_id = signal_id
        self.steps = steps
        self.is_complete = is_complete
        self.missing_steps = missing_steps

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "signal_id": self.signal_id,
            "steps": [s.to_dict() for s in self.steps],
            "total_steps": len(self.steps),
            "is_complete": self.is_complete,
            "missing_steps": self.missing_steps,
        }


class TraceabilityEngine:
    """
    Traces signals through the entire pipeline.

    Given a signal_id, reconstructs the full chain:
    1. Ledger entry (immutable record of receipt)
    2. Ingest record (DB storage)
    3. Internal signal (processed)
    4. Outcome (if recorded)
    """

    async def trace_signal(
        self,
        session: AsyncSession,
        signal_id: str,
    ) -> TraceChain:
        """
        Trace a signal through the pipeline.

        Args:
            session: Database session
            signal_id: The OMEN signal ID to trace

        Returns:
            TraceChain with all discovered steps
        """
        trace_id = f"trace_{uuid.uuid4().hex[:12]}"
        steps: list[TraceStep] = []
        missing: list[str] = []

        # ── Step 1: Ledger entry ──────────────────────────────────────
        ledger = await self._find_ledger_entry(session, signal_id)
        if ledger:
            steps.append(TraceStep(
                step_name="ledger_receipt",
                step_id=str(ledger.id),
                timestamp=ledger.recorded_at.isoformat() if ledger.recorded_at else "",
                status=ledger.status,
                data={
                    "signal_id": ledger.signal_id,
                    "ack_id": ledger.ack_id,
                    "status": ledger.status,
                },
            ))
        else:
            missing.append("ledger_receipt")

        # ── Step 2: Ingest record ─────────────────────────────────────
        ingest = await self._find_ingest_record(session, signal_id)
        if ingest:
            steps.append(TraceStep(
                step_name="ingest_record",
                step_id=str(ingest.id),
                timestamp=ingest.ingested_at.isoformat() if ingest.ingested_at else "",
                status="ingested" if not ingest.processed else "processed",
                data={
                    "signal_id": ingest.signal_id,
                    "ack_id": ingest.ack_id,
                    "category": ingest.category,
                    "title": ingest.title,
                    "probability": float(ingest.probability),
                    "confidence_score": float(ingest.confidence_score),
                    "is_active": ingest.is_active,
                    "processed": ingest.processed,
                },
            ))
        else:
            missing.append("ingest_record")

        is_complete = len(missing) == 0

        chain = TraceChain(
            trace_id=trace_id,
            signal_id=signal_id,
            steps=steps,
            is_complete=is_complete,
            missing_steps=missing,
        )

        logger.info(
            "signal_traced",
            trace_id=trace_id,
            signal_id=signal_id,
            steps=len(steps),
            is_complete=is_complete,
            missing=missing,
        )

        return chain

    async def trace_decision(
        self,
        session: AsyncSession,
        decision_id: str,
        company_id: str,
    ) -> dict:
        """
        Trace a decision back to its source signals and forward to its outcome.

        Returns a dict with the full trace chain.
        """
        trace_id = f"trace_{uuid.uuid4().hex[:12]}"
        result = {
            "trace_id": trace_id,
            "decision_id": decision_id,
            "company_id": company_id,
            "signals_used": [],
            "outcome": None,
            "is_complete": False,
        }

        # Find outcome for this decision
        outcome_result = await session.execute(
            select(Outcome).where(
                Outcome.decision_id == decision_id,
                Outcome.company_id == company_id,
            )
        )
        outcome = outcome_result.scalar_one_or_none()
        if outcome:
            result["outcome"] = {
                "outcome_type": outcome.outcome_type,
                "actual_loss_usd": float(outcome.actual_loss_usd),
                "predicted_loss_usd": float(outcome.predicted_loss_usd),
                "risk_materialized": outcome.risk_materialized,
                "was_accurate": outcome.was_accurate,
                "value_generated_usd": float(outcome.value_generated_usd),
                "recorded_at": outcome.recorded_at.isoformat() if outcome.recorded_at else "",
            }
            result["is_complete"] = True

        return result

    async def get_pipeline_coverage(
        self,
        session: AsyncSession,
        hours_back: int = 24,
    ) -> dict:
        """
        Get pipeline traceability coverage stats.

        Returns what % of signals have full trace chains.
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours_back)

        # Total signals in ledger
        ledger_count_result = await session.execute(
            select(func.count(SignalLedger.id)).where(
                SignalLedger.recorded_at >= cutoff,
            )
        )
        total_ledger = ledger_count_result.scalar_one() or 0

        # Successfully ingested
        ingested_count_result = await session.execute(
            select(func.count(OmenIngestSignal.id)).where(
                OmenIngestSignal.ingested_at >= cutoff,
            )
        )
        total_ingested = ingested_count_result.scalar_one() or 0

        # Failed in ledger
        failed_result = await session.execute(
            select(func.count(SignalLedger.id)).where(
                SignalLedger.recorded_at >= cutoff,
                SignalLedger.status == "failed",
            )
        )
        total_failed = failed_result.scalar_one() or 0

        # Coverage
        ingest_coverage = total_ingested / max(total_ledger, 1)

        return {
            "period_hours": hours_back,
            "total_in_ledger": total_ledger,
            "total_ingested": total_ingested,
            "total_failed": total_failed,
            "ingest_coverage": round(ingest_coverage, 4),
            "needs_reconciliation": total_ledger > total_ingested + total_failed,
        }

    async def _find_ledger_entry(
        self, session: AsyncSession, signal_id: str
    ) -> Optional[SignalLedger]:
        result = await session.execute(
            select(SignalLedger).where(
                SignalLedger.signal_id == signal_id,
            ).order_by(SignalLedger.recorded_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def _find_ingest_record(
        self, session: AsyncSession, signal_id: str
    ) -> Optional[OmenIngestSignal]:
        result = await session.execute(
            select(OmenIngestSignal).where(
                OmenIngestSignal.signal_id == signal_id,
            )
        )
        return result.scalar_one_or_none()
