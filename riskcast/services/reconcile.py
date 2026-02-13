"""
Reconciliation Service — ensures zero signal loss between OMEN and RiskCast.

FLOW:
  1. Read all signal_ids from Ledger for the target date range
  2. Read all signal_ids from OmenIngestSignal for the same range
  3. Diff: find signals in Ledger but NOT in OmenIngestSignal (= missed)
  4. Replay each missed signal from ledger payload
  5. Log the reconcile run

This is the safety net: if POST /ingest fails for any reason,
the reconcile job will catch it and replay the signal.
"""

import uuid
from datetime import date, datetime, timedelta
from typing import Optional

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.models import OmenIngestSignal, ReconcileLog, SignalLedger
from riskcast.schemas.omen_signal import (
    ReconcileHistoryResponse,
    ReconcileResult,
    ReconcileStatusResponse,
)
from riskcast.services.ingest_service import IngestService

logger = structlog.get_logger(__name__)


class ReconcileService:
    """Reconciliation engine for OMEN → RiskCast signal pipeline."""

    def __init__(self) -> None:
        self.ingest = IngestService()

    async def run(
        self,
        session: AsyncSession,
        since_days: int = 7,
    ) -> ReconcileResult:
        """
        Run reconciliation for the last N days.

        Finds signals in ledger that are missing from the ingest table,
        then replays them.
        """
        reconcile_id = f"recon-{uuid.uuid4().hex[:12]}"
        since = datetime.utcnow() - timedelta(days=since_days)
        target_date_str = date.today().isoformat()
        started_at = datetime.utcnow()

        logger.info(
            "reconcile_started",
            reconcile_id=reconcile_id,
            since_days=since_days,
        )

        # Create log entry
        log_entry = ReconcileLog(
            reconcile_id=reconcile_id,
            target_date=date.today(),
            status="running",
            started_at=started_at,
        )
        session.add(log_entry)
        await session.flush()

        try:
            # ── Get all signal_ids from Ledger ──────────────────────────
            ledger_result = await session.execute(
                select(SignalLedger.signal_id, SignalLedger.payload)
                .where(SignalLedger.recorded_at >= since)
            )
            ledger_rows = ledger_result.all()
            ledger_map = {row[0]: row[1] for row in ledger_rows}
            total_in_ledger = len(ledger_map)

            # ── Get all signal_ids from ingest table ────────────────────
            ingest_result = await session.execute(
                select(OmenIngestSignal.signal_id)
                .where(OmenIngestSignal.ingested_at >= since)
            )
            ingested_ids = {row[0] for row in ingest_result.all()}
            total_in_db = len(ingested_ids)

            # ── Find missing signals ────────────────────────────────────
            missing_ids = set(ledger_map.keys()) - ingested_ids
            missing_count = len(missing_ids)

            logger.info(
                "reconcile_diff",
                reconcile_id=reconcile_id,
                total_in_ledger=total_in_ledger,
                total_in_db=total_in_db,
                missing=missing_count,
            )

            # ── Replay missing signals ──────────────────────────────────
            replayed = 0
            failed = 0
            for signal_id in missing_ids:
                try:
                    payload = ledger_map[signal_id]
                    ack, was_new = await self.ingest.replay_from_ledger(
                        session, signal_id, payload
                    )
                    if was_new:
                        replayed += 1

                        # Update ledger entry
                        ledger_entry_result = await session.execute(
                            select(SignalLedger)
                            .where(
                                SignalLedger.signal_id == signal_id,
                                SignalLedger.status.in_(["received", "failed"]),
                            )
                            .order_by(SignalLedger.recorded_at.desc())
                            .limit(1)
                        )
                        ledger_entry = ledger_entry_result.scalar_one_or_none()
                        if ledger_entry:
                            ledger_entry.status = "ingested"
                            ledger_entry.ack_id = ack.ack_id
                            ledger_entry.ingested_at = datetime.utcnow()

                    logger.debug(
                        "reconcile_replay_ok",
                        signal_id=signal_id,
                        was_new=was_new,
                    )
                except Exception as e:
                    failed += 1
                    logger.error(
                        "reconcile_replay_failed",
                        signal_id=signal_id,
                        error=str(e),
                    )

            # ── Determine final status ──────────────────────────────────
            if failed == 0 and missing_count == 0:
                status = "completed"
            elif failed == 0:
                status = "completed"
            elif replayed > 0:
                status = "partial"
            else:
                status = "failed"

            completed_at = datetime.utcnow()

            # Update log
            log_entry.total_in_ledger = total_in_ledger
            log_entry.total_in_db = total_in_db
            log_entry.missing_count = missing_count
            log_entry.replayed_count = replayed
            log_entry.failed_count = failed
            log_entry.status = status
            log_entry.completed_at = completed_at

            logger.info(
                "reconcile_completed",
                reconcile_id=reconcile_id,
                status=status,
                missing=missing_count,
                replayed=replayed,
                failed=failed,
            )

            return ReconcileResult(
                reconcile_id=reconcile_id,
                date=target_date_str,
                total_in_ledger=total_in_ledger,
                total_in_db=total_in_db,
                missing_count=missing_count,
                replayed_count=replayed,
                failed_count=failed,
                status=status,
                started_at=started_at,
                completed_at=completed_at,
            )

        except Exception as e:
            log_entry.status = "failed"
            log_entry.error_message = str(e)[:2000]
            log_entry.completed_at = datetime.utcnow()
            logger.error("reconcile_failed", reconcile_id=reconcile_id, error=str(e))
            raise

    async def get_status(
        self,
        session: AsyncSession,
        target_date: date,
    ) -> ReconcileStatusResponse:
        """Get reconciliation status for a specific date."""
        result = await session.execute(
            select(ReconcileLog)
            .where(ReconcileLog.target_date == target_date)
            .order_by(ReconcileLog.started_at.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()

        if latest is None:
            return ReconcileStatusResponse(
                date=target_date.isoformat(),
                last_run=None,
                is_consistent=False,  # No reconcile run yet = unknown
            )

        return ReconcileStatusResponse(
            date=target_date.isoformat(),
            last_run=self._log_to_result(latest),
            is_consistent=(
                latest.status == "completed" and latest.missing_count == 0
            ),
        )

    async def get_history(
        self,
        session: AsyncSession,
        target_date: date,
    ) -> ReconcileHistoryResponse:
        """Get all reconciliation runs for a specific date."""
        result = await session.execute(
            select(ReconcileLog)
            .where(ReconcileLog.target_date == target_date)
            .order_by(ReconcileLog.started_at.desc())
        )
        logs = result.scalars().all()

        return ReconcileHistoryResponse(
            date=target_date.isoformat(),
            runs=[self._log_to_result(log) for log in logs],
        )

    @staticmethod
    def _log_to_result(log: ReconcileLog) -> ReconcileResult:
        """Convert a ReconcileLog ORM instance to a ReconcileResult schema."""
        return ReconcileResult(
            reconcile_id=log.reconcile_id,
            date=log.target_date.isoformat(),
            total_in_ledger=log.total_in_ledger,
            total_in_db=log.total_in_db,
            missing_count=log.missing_count,
            replayed_count=log.replayed_count,
            failed_count=log.failed_count,
            status=log.status,
            started_at=log.started_at,
            completed_at=log.completed_at,
        )
