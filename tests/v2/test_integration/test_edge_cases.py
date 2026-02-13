"""
Edge Case & Regression Tests.

Covers:
- Empty database behavior (no signals, no outcomes)
- Boundary values for algorithms
- Validator edge cases
- Engine with zero/one signal
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import insert

from riskcast.db.models import Signal
from riskcast.decisions.engine import DecisionEngine
from riskcast.engine.bayesian import BayesianRiskEngine
from riskcast.engine.fusion import SignalFusionEngine, SignalInput
from riskcast.engine.ensemble import EnsembleEngine, ModelPrediction
from riskcast.engine.temporal import TemporalDecayEngine
from riskcast.engine.correlation import CorrelationEngine, SignalObservation
from riskcast.engine.calibration import CalibrationEngine
from riskcast.engine.decomposition import DecompositionEngine
from riskcast.engine.risk_engine import RiskEngine
from riskcast.outcomes.accuracy import AccuracyCalculator
from riskcast.outcomes.roi import ROICalculator
from riskcast.pipeline.health import PipelineHealthMonitor
from riskcast.pipeline.integrity import IntegrityChecker
from riskcast.pipeline.validator import SignalValidator


# ── Empty Database ─────────────────────────────────────────────────────


class TestEmptyDatabase:
    """All operations should handle empty databases gracefully."""

    @pytest.mark.asyncio
    async def test_risk_engine_empty_db(self, db):
        """Risk engine with no signals → low/zero risk."""
        engine = RiskEngine()
        result = await engine.assess_entity(db, str(uuid.uuid4()), "order", "ORD-NONE")
        assert result is not None
        assert result.risk_score >= 0

    @pytest.mark.asyncio
    async def test_decision_engine_empty_db(self, db):
        """Decision engine with no signals → still generates a decision."""
        engine = DecisionEngine()
        result = await engine.generate_decision(
            db, str(uuid.uuid4()), "order", "ORD-NONE"
        )
        assert result is not None
        assert result.decision_id

    @pytest.mark.asyncio
    async def test_accuracy_empty_db(self, db):
        """Accuracy with no outcomes → valid empty report."""
        calc = AccuracyCalculator()
        result = await calc.generate_report(db, str(uuid.uuid4()))
        assert result is not None
        assert result.total_outcomes == 0

    @pytest.mark.asyncio
    async def test_roi_empty_db(self, db):
        """ROI with no outcomes → valid empty report."""
        calc = ROICalculator()
        result = await calc.generate_report(db, str(uuid.uuid4()))
        assert result is not None
        assert result.total_decisions == 0

    @pytest.mark.asyncio
    async def test_pipeline_health_empty_db(self, db):
        """Pipeline health with no data → no_data status."""
        monitor = PipelineHealthMonitor()
        result = await monitor.check_health(db)
        assert result.freshness_status == "no_data"
        assert result.overall_status == "critical"

    @pytest.mark.asyncio
    async def test_integrity_empty_db(self, db):
        """Integrity check with no data → consistent (vacuously true)."""
        checker = IntegrityChecker()
        result = await checker.check_integrity(db)
        assert result.is_consistent is True


# ── Boundary Values ───────────────────────────────────────────────────


class TestBoundaryValues:
    """Test edge values for algorithms."""

    def test_bayesian_zero_observations(self):
        engine = BayesianRiskEngine()
        result = engine.beta_update(successes=0, failures=0)
        assert 0 <= result.mean <= 1

    def test_bayesian_all_successes(self):
        engine = BayesianRiskEngine()
        result = engine.beta_update(successes=100, failures=0)
        assert result.mean > 0.9

    def test_bayesian_all_failures(self):
        engine = BayesianRiskEngine()
        result = engine.beta_update(successes=0, failures=100)
        assert result.mean < 0.1

    def test_fusion_single_signal(self):
        engine = SignalFusionEngine()
        result = engine.fuse([
            SignalInput(signal_type="test", severity_score=50, confidence=0.8),
        ])
        assert result is not None
        assert 0 <= result.fused_score <= 100

    def test_fusion_empty_signals(self):
        engine = SignalFusionEngine()
        result = engine.fuse([])
        assert result is not None
        assert result.fused_score == 0

    def test_calibration_empty_predictions(self):
        engine = CalibrationEngine()
        result = engine.assess([], [])
        assert result.ece == 0.0

    def test_temporal_fresh_signal(self):
        engine = TemporalDecayEngine()
        now = datetime.now(timezone.utc)
        result = engine.compute_decay("supply_chain_disruption", 75.0, now, now=now)
        assert result.decay_weight >= 0.99  # Fresh signal → almost no decay

    def test_temporal_very_old_signal(self):
        engine = TemporalDecayEngine()
        now = datetime.now(timezone.utc)
        from datetime import timedelta
        old = now - timedelta(hours=10000)
        result = engine.compute_decay("supply_chain_disruption", 75.0, old, now=now)
        assert result.decay_weight < 0.01 or result.is_expired

    def test_correlation_single_signal(self):
        engine = CorrelationEngine()
        result = engine.analyze_correlations([
            SignalObservation(
                signal_type="A", entity_id="E1",
                severity_score=50, timestamp=datetime.now(timezone.utc).isoformat(),
            ),
        ])
        # Single signal → no correlations or empty pairs
        assert result is not None

    def test_ensemble_single_model(self):
        engine = EnsembleEngine()
        result = engine.aggregate([
            ModelPrediction(model_name="m1", risk_score=70, confidence=0.8),
        ])
        assert result.ensemble_score == 70
        assert result.needs_human_review is False

    def test_decomposition_empty(self):
        engine = DecompositionEngine()
        result = engine.decompose(
            entity_type="order",
            entity_id="ORD-1",
            composite_score=0,
            confidence=0.5,
            factor_scores={},
            factor_weights={},
        )
        assert result.composite_score == 0


# ── Validator Edge Cases ──────────────────────────────────────────────


class TestValidatorEdgeCases:
    def test_minimal_valid_signal(self):
        """Signal with absolute minimum required fields."""
        from riskcast.schemas.omen_signal import OmenSignalPayload, SignalEvent
        event = SignalEvent(
            signal_id="OMEN-MINI-12345",
            signal=OmenSignalPayload(
                signal_id="OMEN-MINI-12345",
                title="Minimum valid signal title here",
                probability=0.5,
                confidence_score=0.5,
                category="ECONOMIC",
                generated_at=datetime.now(timezone.utc),
            ),
        )
        validator = SignalValidator()
        result = validator.validate(event)
        assert result.is_valid is True

    def test_max_evidence_items(self):
        """Signal with many evidence items."""
        from riskcast.schemas.omen_signal import (
            EvidenceItem, OmenSignalPayload, SignalEvent,
        )
        evidence = [
            EvidenceItem(source=f"src_{i}", source_type="article")
            for i in range(20)
        ]
        event = SignalEvent(
            signal_id="OMEN-MAXEV-12345",
            signal=OmenSignalPayload(
                signal_id="OMEN-MAXEV-12345",
                title="Signal with lots of evidence",
                probability=0.8,
                confidence_score=0.9,
                category="GEOPOLITICAL",
                evidence=evidence,
                generated_at=datetime.now(timezone.utc),
            ),
        )
        validator = SignalValidator()
        result = validator.validate(event)
        assert result.is_valid is True
        assert result.quality_score > 0.5
