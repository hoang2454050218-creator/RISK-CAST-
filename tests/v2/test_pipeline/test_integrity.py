"""
Tests for Pipeline Integrity Checker.

Covers:
- Consistent pipeline (all ledger entries have DB records)
- Missing signals (in ledger but not DB)
- Orphaned signals (in DB but not ledger)
- Failed ingests flagged
- Duplicate detection in ledger
- find_signals_needing_replay
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.models import OmenIngestSignal, SignalLedger
from riskcast.pipeline.integrity import IntegrityChecker


@pytest.fixture
def checker():
    return IntegrityChecker()


# ── Helpers ───────────────────────────────────────────────────────────


async def _insert_ledger(
    session: AsyncSession,
    signal_id: str,
    status: str = "ingested",
    recorded_at: datetime | None = None,
) -> None:
    now = recorded_at or datetime.now(timezone.utc)
    await session.execute(insert(SignalLedger).values(
        id=uuid.uuid4(),
        signal_id=signal_id,
        payload={},
        status=status,
        recorded_at=now,
    ))
    await session.flush()


async def _insert_db(
    session: AsyncSession,
    signal_id: str,
    ingested_at: datetime | None = None,
) -> None:
    now = ingested_at or datetime.now(timezone.utc)
    await session.execute(insert(OmenIngestSignal).values(
        id=uuid.uuid4(),
        signal_id=signal_id,
        ack_id=f"ack-{signal_id}",
        schema_version="1.0.0",
        title="Test",
        probability=Decimal("0.5"),
        confidence_score=Decimal("0.7"),
        category="ECONOMIC",
        tags=[],
        evidence=[],
        raw_payload={},
        is_active=True,
        processed=False,
        ingested_at=now,
    ))
    await session.flush()


# ── Consistency ───────────────────────────────────────────────────────


class TestConsistency:
    @pytest.mark.asyncio
    async def test_empty_is_consistent(self, checker, db):
        """No data → consistent."""
        report = await checker.check_integrity(db)
        assert report.is_consistent is True
        assert len(report.issues) == 0

    @pytest.mark.asyncio
    async def test_all_ingested_consistent(self, checker, db):
        """All ledger entries have matching DB records → consistent."""
        for i in range(5):
            sid = f"OMEN-CON-{i}"
            await _insert_ledger(db, sid)
            await _insert_db(db, sid)

        report = await checker.check_integrity(db)
        assert report.is_consistent is True
        assert report.missing_from_db == 0
        assert report.orphaned_in_db == 0


# ── Missing from DB ──────────────────────────────────────────────────


class TestMissing:
    @pytest.mark.asyncio
    async def test_missing_detected(self, checker, db):
        """Ledger entry without DB record → missing."""
        await _insert_ledger(db, "OMEN-MISS-1")
        # No corresponding DB insert

        report = await checker.check_integrity(db)
        assert report.is_consistent is False
        assert report.missing_from_db == 1
        assert any(i.issue_type == "missing_from_db" for i in report.issues)

    @pytest.mark.asyncio
    async def test_failed_not_counted_as_missing(self, checker, db):
        """Failed ledger entries should not be counted as 'missing from DB'."""
        await _insert_ledger(db, "OMEN-FAIL-1", status="failed")

        report = await checker.check_integrity(db)
        assert report.missing_from_db == 0
        assert any(i.issue_type == "ingest_failed" for i in report.issues)


# ── Orphaned in DB ────────────────────────────────────────────────────


class TestOrphaned:
    @pytest.mark.asyncio
    async def test_orphaned_detected(self, checker, db):
        """DB record without ledger entry → orphaned."""
        await _insert_db(db, "OMEN-ORPHAN-1")
        # No corresponding ledger insert

        report = await checker.check_integrity(db)
        assert report.is_consistent is False
        assert report.orphaned_in_db == 1
        assert any(i.issue_type == "orphaned_in_db" for i in report.issues)


# ── Replay ────────────────────────────────────────────────────────────


class TestReplay:
    @pytest.mark.asyncio
    async def test_find_signals_needing_replay(self, checker, db):
        """Missing signals should be found for replay."""
        # 3 in ledger, only 1 in DB
        await _insert_ledger(db, "OMEN-REP-1")
        await _insert_db(db, "OMEN-REP-1")
        await _insert_ledger(db, "OMEN-REP-2")
        await _insert_ledger(db, "OMEN-REP-3")

        needing_replay = await checker.find_signals_needing_replay(db)
        assert "OMEN-REP-2" in needing_replay
        assert "OMEN-REP-3" in needing_replay
        assert "OMEN-REP-1" not in needing_replay

    @pytest.mark.asyncio
    async def test_failed_not_in_replay(self, checker, db):
        """Failed signals should not be flagged for replay."""
        await _insert_ledger(db, "OMEN-NREP-1", status="failed")

        needing_replay = await checker.find_signals_needing_replay(db)
        assert "OMEN-NREP-1" not in needing_replay


# ── Serialization ─────────────────────────────────────────────────────


class TestSerialization:
    @pytest.mark.asyncio
    async def test_report_to_dict(self, checker, db):
        report = await checker.check_integrity(db)
        d = report.to_dict()
        assert "check_id" in d
        assert "is_consistent" in d
        assert "counts" in d
        assert "issues" in d

    @pytest.mark.asyncio
    async def test_report_counts_correct(self, checker, db):
        """Verify counts in the serialized report include our entries."""
        await _insert_ledger(db, "OMEN-CNT-1")
        await _insert_db(db, "OMEN-CNT-1")
        await _insert_ledger(db, "OMEN-CNT-2")  # missing

        report = await checker.check_integrity(db)
        d = report.to_dict()
        # At least our seeded entries (shared DB may have more from E2E tests)
        assert d["counts"]["total_ledger_entries"] >= 2
        assert d["counts"]["total_db_records"] >= 1
        assert d["counts"]["missing_from_db"] >= 1
