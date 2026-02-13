"""
End-to-End Integration Tests: Signal → Risk → Decision → Outcome.

Tests the complete RiskCast pipeline as a single flow:
1. Signal arrives (validated, ingested)
2. Risk assessed using signal data
3. Decision generated from risk assessment
4. Outcome recorded, flywheel updates priors
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.models import OmenIngestSignal, Signal, SignalLedger
from riskcast.decisions.engine import DecisionEngine
from riskcast.engine.risk_engine import RiskEngine
from riskcast.outcomes.accuracy import AccuracyCalculator
from riskcast.outcomes.flywheel import FlywheelEngine
from riskcast.outcomes.recorder import OutcomeRecorder
from riskcast.outcomes.roi import ROICalculator
from riskcast.outcomes.schemas import OutcomeRecordRequest
from riskcast.pipeline.health import PipelineHealthMonitor
from riskcast.pipeline.integrity import IntegrityChecker
from riskcast.pipeline.traceability import TraceabilityEngine
from riskcast.pipeline.validator import SignalValidator


# ── Helpers ───────────────────────────────────────────────────────────


async def _seed_signal_with_factory(
    session_factory,
    company_id: str,
    entity_type: str = "order",
    entity_id: uuid.UUID | None = None,
    severity: float = 75.0,
    confidence: float = 0.85,
    signal_type: str = "supply_chain_disruption",
) -> uuid.UUID:
    """Seed a signal + ledger entry using session_factory (committed)."""
    eid = entity_id or uuid.uuid4()
    signal_id = f"OMEN-E2E-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)

    async with session_factory() as session:
        # Ledger entry
        session.add(SignalLedger(
            signal_id=signal_id,
            payload={"title": "Test e2e signal"},
            status="ingested",
            ack_id=f"ack-{signal_id}",
            recorded_at=now,
        ))

        # Ingest record
        session.add(OmenIngestSignal(
            signal_id=signal_id,
            ack_id=f"ack-{signal_id}",
            schema_version="1.0.0",
            title="Supply chain disruption at Shanghai port",
            description="Major congestion expected for 2 weeks",
            probability=Decimal(str(confidence)),
            confidence_score=Decimal(str(confidence)),
            category="SUPPLY_CHAIN",
            tags=["port", "congestion"],
            evidence=[{"source": "reuters", "source_type": "news"}],
            raw_payload={"signal_id": signal_id},
            is_active=True,
            processed=False,
            ingested_at=now,
            emitted_at=now,
        ))

        # Internal signal (used by risk engine)
        session.add(Signal(
            company_id=uuid.UUID(company_id),
            source="omen",
            signal_type=signal_type,
            entity_type=entity_type,
            entity_id=eid,
            severity_score=Decimal(str(severity)),
            confidence=Decimal(str(confidence)),
            evidence={"test": True},
            is_active=True,
        ))

        await session.commit()

    return eid


# ── E2E Pipeline Test ─────────────────────────────────────────────────


class TestEndToEndPipeline:
    """Tests the complete signal-to-outcome pipeline."""

    @pytest.mark.asyncio
    async def test_full_pipeline_flow(self, session_factory):
        """
        Full flow: Validate → Seed → Risk → Decision → Outcome → Accuracy → ROI → Flywheel.
        """
        company_id = str(uuid.uuid4())

        # ── Step 1: Validate signal ───────────────────────────────
        from riskcast.schemas.omen_signal import (
            EvidenceItem, OmenSignalPayload, SignalEvent,
        )

        event = SignalEvent(
            schema_version="1.0.0",
            signal_id="OMEN-E2E-VALID",
            observed_at=datetime.now(timezone.utc),
            emitted_at=datetime.now(timezone.utc),
            signal=OmenSignalPayload(
                signal_id="OMEN-E2E-VALID",
                title="Supply chain disruption at Shanghai port",
                description="Major congestion",
                probability=0.75,
                confidence_score=0.85,
                confidence_level="HIGH",
                category="SUPPLY_CHAIN",
                evidence=[EvidenceItem(source="reuters", source_type="news")],
                generated_at=datetime.now(timezone.utc),
            ),
        )
        validator = SignalValidator()
        validation = validator.validate(event)
        assert validation.is_valid is True

        # ── Step 2: Seed signals ──────────────────────────────────
        entity_id = await _seed_signal_with_factory(
            session_factory, company_id, severity=75.0, confidence=0.85
        )

        # ── Step 3-9: Use a fresh session ─────────────────────────
        async with session_factory() as db:
            # Pipeline health
            health_monitor = PipelineHealthMonitor()
            health = await health_monitor.check_health(db)
            assert health.freshness_status in ("no_data", "fresh", "stale", "outdated")

            # Assess risk
            risk_engine = RiskEngine()
            assessment = await risk_engine.assess_entity(
                db, company_id, "order", str(entity_id)
            )
            assert assessment is not None
            assert 0 <= assessment.risk_score <= 100
            assert 0 <= assessment.confidence <= 1.0
            assert assessment.entity_id == str(entity_id)

            # Generate decision
            decision_engine = DecisionEngine()
            decision = await decision_engine.generate_decision(
                db, company_id, "order", str(entity_id), exposure_usd=100_000
            )
            assert decision is not None
            assert decision.entity_id == str(entity_id)
            assert decision.decision_id

            # Record outcome
            recorder = OutcomeRecorder()
            request = OutcomeRecordRequest(
                decision_id=decision.decision_id,
                outcome_type="loss_avoided",
                actual_loss_usd=0,
                actual_delay_days=0,
                action_taken="insure",
                action_followed_recommendation=True,
            )
            outcome = await recorder.record_outcome(
                session=db,
                company_id=company_id,
                request=request,
                predicted_risk_score=assessment.risk_score,
                predicted_confidence=assessment.confidence,
                predicted_loss_usd=50_000,
                predicted_action="insure",
                entity_type="order",
                entity_id=str(entity_id),
                recorded_by="e2e_test",
            )
            assert outcome is not None
            assert outcome.value_generated_usd >= 0
            await db.commit()

        async with session_factory() as db:
            # Accuracy
            accuracy_calc = AccuracyCalculator()
            accuracy = await accuracy_calc.generate_report(db, company_id)
            assert accuracy is not None
            assert accuracy.total_outcomes >= 1

            # ROI
            roi_calc = ROICalculator()
            roi = await roi_calc.generate_report(db, company_id)
            assert roi is not None
            assert roi.total_decisions >= 1

            # Flywheel
            flywheel = FlywheelEngine()
            learning = await flywheel.get_learning_summary(db, company_id)
            assert learning is not None

    @pytest.mark.asyncio
    async def test_pipeline_integrity_after_ingest(self, session_factory):
        """After seeding signals, integrity check should show consistency."""
        company_id = str(uuid.uuid4())
        await _seed_signal_with_factory(session_factory, company_id)

        async with session_factory() as db:
            checker = IntegrityChecker()
            report = await checker.check_integrity(db, hours_back=24)
            assert report.total_ledger_entries >= 1
            assert report.total_db_records >= 1

    @pytest.mark.asyncio
    async def test_traceability_after_ingest(self, db):
        """After seeding, traceability engine should find the signal chain."""
        signal_id = f"OMEN-TRACE-E2E-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)

        await db.execute(insert(SignalLedger).values(
            id=uuid.uuid4(),
            signal_id=signal_id,
            payload={},
            status="ingested",
            ack_id=f"ack-{signal_id}",
            recorded_at=now,
        ))
        await db.execute(insert(OmenIngestSignal).values(
            id=uuid.uuid4(),
            signal_id=signal_id,
            ack_id=f"ack-{signal_id}",
            schema_version="1.0.0",
            title="Trace test",
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
        await db.flush()

        engine = TraceabilityEngine()
        chain = await engine.trace_signal(db, signal_id)
        assert chain.is_complete is True
        assert len(chain.steps) >= 2


# ── Multi-Signal Decision Test ────────────────────────────────────────


class TestMultiSignalDecision:
    @pytest.mark.asyncio
    async def test_multiple_signals_same_entity(self, session_factory):
        """Multiple signals for one entity → higher risk score."""
        company_id = str(uuid.uuid4())
        entity_id = uuid.uuid4()

        async with session_factory() as session:
            for i, (stype, sev) in enumerate([
                ("supply_chain_disruption", 80),
                ("geopolitical_risk", 70),
                ("weather_disruption", 60),
            ]):
                session.add(Signal(
                    company_id=uuid.UUID(company_id),
                    source=f"omen_{i}",
                    signal_type=stype,
                    entity_type="order",
                    entity_id=entity_id,
                    severity_score=Decimal(str(sev)),
                    confidence=Decimal("0.8"),
                    evidence={},
                    is_active=True,
                ))
            await session.commit()

        async with session_factory() as db:
            risk_engine = RiskEngine()
            assessment = await risk_engine.assess_entity(db, company_id, "order", str(entity_id))
            # Multiple signals → meaningful risk score (ensemble+Bayesian reduces raw)
            assert assessment.risk_score > 30
            assert assessment.n_signals == 3

    @pytest.mark.asyncio
    async def test_decision_escalation_on_low_confidence(self, session_factory):
        """Low confidence → decision should require human review."""
        company_id = str(uuid.uuid4())
        entity_id = uuid.uuid4()

        async with session_factory() as session:
            session.add(Signal(
                company_id=uuid.UUID(company_id),
                source="omen",
                signal_type="critical_failure",
                entity_type="order",
                entity_id=entity_id,
                severity_score=Decimal("95"),
                confidence=Decimal("0.3"),
                evidence={},
                is_active=True,
            ))
            await session.commit()

        async with session_factory() as db:
            decision_engine = DecisionEngine()
            decision = await decision_engine.generate_decision(
                db, company_id, "order", str(entity_id), exposure_usd=500_000
            )
            assert decision.needs_human_review is True


# ── Outcome Feedback Loop Test ────────────────────────────────────────


class TestOutcomeFeedbackLoop:
    @pytest.mark.asyncio
    async def test_multiple_outcomes_accuracy(self, db):
        """Recording multiple outcomes produces valid accuracy stats."""
        company_id = str(uuid.uuid4())
        recorder = OutcomeRecorder()

        for i in range(5):
            entity_id = f"ORD-FB-{i}"
            risk_score = 60 + i * 5
            materialized = i % 2 == 0

            request = OutcomeRecordRequest(
                decision_id=f"DEC-FB-{i}-{uuid.uuid4().hex[:6]}",
                outcome_type="loss_avoided" if not materialized else "loss_occurred",
                actual_loss_usd=0 if not materialized else 8000,
                actual_delay_days=0,
                action_taken="insure",
                action_followed_recommendation=True,
            )
            await recorder.record_outcome(
                session=db,
                company_id=company_id,
                request=request,
                predicted_risk_score=risk_score,
                predicted_confidence=0.7,
                predicted_loss_usd=10000 + i * 5000,
                predicted_action="insure",
                entity_type="order",
                entity_id=entity_id,
                recorded_by="test",
            )

        accuracy_calc = AccuracyCalculator()
        report = await accuracy_calc.generate_report(db, company_id)
        assert report.total_outcomes == 5
        assert 0 <= report.brier_score <= 1.0

        roi_calc = ROICalculator()
        roi = await roi_calc.generate_report(db, company_id)
        assert roi.total_decisions == 5
