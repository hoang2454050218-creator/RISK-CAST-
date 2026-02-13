"""
Tests for Signal-to-Decision Traceability.

Covers:
- Signal tracing (ledger → ingest → processing)
- Decision tracing (signals → decision → outcome)
- Pipeline coverage stats
- Missing step detection
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.models import OmenIngestSignal, Outcome, SignalLedger
from riskcast.pipeline.traceability import TraceabilityEngine


@pytest.fixture
def trace_engine():
    return TraceabilityEngine()


# ── Helpers ───────────────────────────────────────────────────────────


async def _insert_signal_with_ledger(
    session: AsyncSession,
    signal_id: str,
) -> None:
    """Insert both a ledger entry and ingest record for a signal."""
    now = datetime.now(timezone.utc)
    _id = uuid.uuid4()

    # Ledger entry
    await session.execute(insert(SignalLedger).values(
        id=uuid.uuid4(),
        signal_id=signal_id,
        payload={},
        status="ingested",
        ack_id=f"ack-{signal_id}",
        recorded_at=now,
    ))

    # Ingest record
    await session.execute(insert(OmenIngestSignal).values(
        id=_id,
        signal_id=signal_id,
        ack_id=f"ack-{signal_id}",
        schema_version="1.0.0",
        title="Test signal",
        probability=Decimal("0.7"),
        confidence_score=Decimal("0.8"),
        category="SUPPLY_CHAIN",
        tags=[],
        evidence=[],
        raw_payload={},
        is_active=True,
        processed=False,
        ingested_at=now,
    ))
    await session.flush()


async def _insert_ledger_only(
    session: AsyncSession,
    signal_id: str,
) -> None:
    """Insert only a ledger entry (no ingest record)."""
    await session.execute(insert(SignalLedger).values(
        id=uuid.uuid4(),
        signal_id=signal_id,
        payload={},
        status="pending",
        recorded_at=datetime.now(timezone.utc),
    ))
    await session.flush()


async def _insert_outcome(
    session: AsyncSession,
    decision_id: str,
    company_id: uuid.UUID,
) -> None:
    """Insert an outcome record."""
    await session.execute(insert(Outcome).values(
        id=uuid.uuid4(),
        decision_id=decision_id,
        company_id=company_id,
        entity_type="order",
        entity_id="ORD-123",
        predicted_risk_score=Decimal("0.7"),
        predicted_confidence=Decimal("0.8"),
        predicted_loss_usd=Decimal("50000"),
        predicted_action="insure",
        outcome_type="loss_avoided",
        actual_loss_usd=Decimal("0"),
        actual_delay_days=Decimal("0"),
        action_taken="insure",
        action_followed_recommendation=True,
        risk_materialized=True,
        prediction_error=Decimal("0.1"),
        was_accurate=True,
        value_generated_usd=Decimal("45000"),
        recorded_at=datetime.now(timezone.utc),
    ))
    await session.flush()


# ── Signal Tracing ─────────────────────────────────────────────────────


class TestSignalTracing:
    @pytest.mark.asyncio
    async def test_full_trace(self, trace_engine, db):
        """Signal with both ledger + ingest → complete trace."""
        signal_id = "OMEN-TRACE-001"
        await _insert_signal_with_ledger(db, signal_id)

        chain = await trace_engine.trace_signal(db, signal_id)
        assert chain.is_complete is True
        assert len(chain.steps) >= 2
        assert chain.signal_id == signal_id
        step_names = [s.step_name for s in chain.steps]
        assert "ledger_receipt" in step_names
        assert "ingest_record" in step_names

    @pytest.mark.asyncio
    async def test_ledger_only_trace(self, trace_engine, db):
        """Signal in ledger but not ingested → incomplete trace."""
        signal_id = "OMEN-TRACE-002"
        await _insert_ledger_only(db, signal_id)

        chain = await trace_engine.trace_signal(db, signal_id)
        assert chain.is_complete is False
        assert "ingest_record" in chain.missing_steps

    @pytest.mark.asyncio
    async def test_nonexistent_signal(self, trace_engine, db):
        """Unknown signal_id → no steps found."""
        chain = await trace_engine.trace_signal(db, "OMEN-NOPE-999")
        assert chain.is_complete is False
        assert len(chain.steps) == 0

    @pytest.mark.asyncio
    async def test_trace_serialization(self, trace_engine, db):
        """Trace chain serializes correctly."""
        signal_id = "OMEN-TRACE-003"
        await _insert_signal_with_ledger(db, signal_id)

        chain = await trace_engine.trace_signal(db, signal_id)
        d = chain.to_dict()
        assert "trace_id" in d
        assert "steps" in d
        assert "is_complete" in d


# ── Decision Tracing ──────────────────────────────────────────────────


class TestDecisionTracing:
    @pytest.mark.asyncio
    async def test_decision_with_outcome(self, trace_engine, db):
        """Decision with outcome → outcome included."""
        decision_id = "DEC-001"
        company_id = uuid.uuid4()
        await _insert_outcome(db, decision_id, company_id)

        result = await trace_engine.trace_decision(db, decision_id, str(company_id))
        assert result["outcome"] is not None
        assert result["is_complete"] is True

    @pytest.mark.asyncio
    async def test_decision_without_outcome(self, trace_engine, db):
        """Decision without outcome → outcome is None."""
        result = await trace_engine.trace_decision(db, "DEC-NOPE", str(uuid.uuid4()))
        assert result["outcome"] is None
        assert result["is_complete"] is False


# ── Pipeline Coverage ──────────────────────────────────────────────────


class TestPipelineCoverage:
    @pytest.mark.asyncio
    async def test_empty_coverage(self, trace_engine, db):
        """No data in this session → valid coverage dict (may have shared DB data)."""
        cov = await trace_engine.get_pipeline_coverage(db, hours_back=24)
        assert cov["total_in_ledger"] >= 0
        assert cov["total_ingested"] >= 0

    @pytest.mark.asyncio
    async def test_full_coverage(self, trace_engine, db):
        """All signals ingested → coverage includes our 5."""
        for i in range(5):
            await _insert_signal_with_ledger(db, f"OMEN-COV-{i}")

        cov = await trace_engine.get_pipeline_coverage(db, hours_back=24)
        assert cov["total_in_ledger"] >= 5
        assert cov["total_ingested"] >= 5

    @pytest.mark.asyncio
    async def test_partial_coverage(self, trace_engine, db):
        """Some signals not ingested → ledger > ingested."""
        for i in range(3):
            await _insert_signal_with_ledger(db, f"OMEN-PC-{i}")
        for i in range(2):
            await _insert_ledger_only(db, f"OMEN-MISS-{i}")

        cov = await trace_engine.get_pipeline_coverage(db, hours_back=24)
        assert cov["total_in_ledger"] >= 5
        assert cov["total_in_ledger"] > cov["total_ingested"]  # Ledger has more
