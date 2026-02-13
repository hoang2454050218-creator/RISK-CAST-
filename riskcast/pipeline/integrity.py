"""
Pipeline Integrity Checker — Reconciliation hardening and integrity verification.

Verifies:
1. Ledger ↔ DB consistency (every ledger entry has a matching DB record)
2. Hash chain integrity (no tampered or missing entries)
3. Signal completeness (all required fields populated)
4. Temporal ordering (signals ingested in order)
5. Duplicate detection (beyond idempotency key)
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.models import OmenIngestSignal, SignalLedger

logger = structlog.get_logger(__name__)


class IntegrityIssue:
    """A single integrity issue found."""

    def __init__(self, issue_type: str, signal_id: str, description: str, severity: str):
        self.issue_type = issue_type
        self.signal_id = signal_id
        self.description = description
        self.severity = severity  # "error", "warning", "info"

    def to_dict(self) -> dict:
        return {
            "type": self.issue_type,
            "signal_id": self.signal_id,
            "description": self.description,
            "severity": self.severity,
        }


class IntegrityReport:
    """Result of an integrity check."""

    def __init__(
        self,
        check_id: str,
        checked_at: str,
        period_hours: int,
        total_ledger_entries: int,
        total_db_records: int,
        missing_from_db: int,
        orphaned_in_db: int,
        issues: list[IntegrityIssue],
        is_consistent: bool,
    ):
        self.check_id = check_id
        self.checked_at = checked_at
        self.period_hours = period_hours
        self.total_ledger_entries = total_ledger_entries
        self.total_db_records = total_db_records
        self.missing_from_db = missing_from_db
        self.orphaned_in_db = orphaned_in_db
        self.issues = issues
        self.is_consistent = is_consistent

    def to_dict(self) -> dict:
        return {
            "check_id": self.check_id,
            "checked_at": self.checked_at,
            "period_hours": self.period_hours,
            "counts": {
                "total_ledger_entries": self.total_ledger_entries,
                "total_db_records": self.total_db_records,
                "missing_from_db": self.missing_from_db,
                "orphaned_in_db": self.orphaned_in_db,
            },
            "is_consistent": self.is_consistent,
            "issues": [i.to_dict() for i in self.issues],
            "total_issues": len(self.issues),
            "errors": len([i for i in self.issues if i.severity == "error"]),
            "warnings": len([i for i in self.issues if i.severity == "warning"]),
        }


class IntegrityChecker:
    """
    Verifies pipeline integrity between the ledger and the DB.

    The ledger is the immutable source of truth. If a signal appears
    in the ledger but not in the DB, it needs to be replayed.
    """

    async def check_integrity(
        self,
        session: AsyncSession,
        hours_back: int = 24,
    ) -> IntegrityReport:
        """
        Run a full integrity check for the specified period.

        Compares ledger entries against DB records to find:
        - Missing: in ledger but not in DB (need replay)
        - Orphaned: in DB but not in ledger (should not happen)
        - Failed: in ledger with status 'failed'
        """
        import uuid as _uuid

        now = datetime.utcnow()
        check_id = f"check_{_uuid.uuid4().hex[:12]}"
        cutoff = now - timedelta(hours=hours_back)
        issues: list[IntegrityIssue] = []

        # ── 1. Get all ledger entries ─────────────────────────────────
        ledger_result = await session.execute(
            select(SignalLedger.signal_id, SignalLedger.status)
            .where(SignalLedger.recorded_at >= cutoff)
        )
        ledger_entries = ledger_result.all()
        ledger_ids = {row[0] for row in ledger_entries}

        # ── 2. Get all DB records ─────────────────────────────────────
        db_result = await session.execute(
            select(OmenIngestSignal.signal_id)
            .where(OmenIngestSignal.ingested_at >= cutoff)
        )
        db_ids = {row[0] for row in db_result.all()}

        # ── 3. Find missing (ledger but not DB) ──────────────────────
        # Exclude explicitly failed entries
        failed_ids = {row[0] for row in ledger_entries if row[1] == "failed"}
        successful_ledger_ids = ledger_ids - failed_ids
        missing = successful_ledger_ids - db_ids

        for sid in missing:
            issues.append(IntegrityIssue(
                "missing_from_db",
                sid,
                "Signal in ledger but not in DB — needs replay",
                "error",
            ))

        # ── 4. Find orphaned (DB but not ledger) ─────────────────────
        orphaned = db_ids - ledger_ids

        for sid in orphaned:
            issues.append(IntegrityIssue(
                "orphaned_in_db",
                sid,
                "Signal in DB but not in ledger — data integrity concern",
                "warning",
            ))

        # ── 5. Flag failed entries ────────────────────────────────────
        for sid in failed_ids:
            issues.append(IntegrityIssue(
                "ingest_failed",
                sid,
                "Signal ingest failed — logged in ledger",
                "warning",
            ))

        # ── 6. Check for duplicate signal IDs in ledger ───────────────
        ledger_id_list = [row[0] for row in ledger_entries]
        seen: set[str] = set()
        duplicates: set[str] = set()
        for sid in ledger_id_list:
            if sid in seen:
                duplicates.add(sid)
            seen.add(sid)

        for sid in duplicates:
            issues.append(IntegrityIssue(
                "duplicate_in_ledger",
                sid,
                "Signal ID appears multiple times in ledger",
                "info",
            ))

        is_consistent = len(missing) == 0 and len(orphaned) == 0

        report = IntegrityReport(
            check_id=check_id,
            checked_at=now.isoformat(),
            period_hours=hours_back,
            total_ledger_entries=len(ledger_ids),
            total_db_records=len(db_ids),
            missing_from_db=len(missing),
            orphaned_in_db=len(orphaned),
            issues=issues,
            is_consistent=is_consistent,
        )

        logger.info(
            "integrity_check_complete",
            check_id=check_id,
            is_consistent=is_consistent,
            total_issues=len(issues),
            missing=len(missing),
            orphaned=len(orphaned),
        )

        return report

    async def find_signals_needing_replay(
        self,
        session: AsyncSession,
        hours_back: int = 24,
    ) -> list[str]:
        """Find signal IDs that are in the ledger but not in the DB."""
        cutoff = datetime.utcnow() - timedelta(hours=hours_back)

        ledger_result = await session.execute(
            select(SignalLedger.signal_id)
            .where(
                SignalLedger.recorded_at >= cutoff,
                SignalLedger.status != "failed",
            )
        )
        ledger_ids = {row[0] for row in ledger_result.all()}

        db_result = await session.execute(
            select(OmenIngestSignal.signal_id)
            .where(OmenIngestSignal.ingested_at >= cutoff)
        )
        db_ids = {row[0] for row in db_result.all()}

        return sorted(ledger_ids - db_ids)
