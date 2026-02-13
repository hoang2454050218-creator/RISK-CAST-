"""
Unified Risk Engine — Orchestrates all algorithm components.

This is the single entry point for risk assessment. It:
1. Collects signals for an entity
2. Applies temporal decay (old signals matter less)
3. Detects correlations (avoid double-counting)
4. Fuses signals via weighted fusion
5. Validates through Bayesian posterior
6. Runs ensemble aggregation across methods
7. Decomposes the result into explainable factors
8. Calibrates the final confidence score

Every output includes full audit trail of how the score was computed.
"""

from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.models import Incident, Order, Payment, Signal
from riskcast.engine.bayesian import BayesianRiskEngine, RiskScore
from riskcast.engine.calibration import CalibrationEngine
from riskcast.engine.correlation import CorrelationEngine, SignalObservation
from riskcast.engine.decomposition import DecompositionEngine
from riskcast.engine.ensemble import EnsembleEngine, ModelPrediction
from riskcast.engine.fusion import SignalFusionEngine, SignalInput
from riskcast.engine.temporal import TemporalDecayEngine

logger = structlog.get_logger(__name__)


@dataclass
class RiskAssessment:
    """
    Complete risk assessment output — fully traceable.

    Every field answers a question:
    - risk_score: How risky? (0-100)
    - confidence: How sure are we? (0-1)
    - ci_lower/ci_upper: What's the range?
    - is_reliable: Do we have enough data?
    - needs_human_review: Should a human check this?
    - factors: WHY is this the score?
    - algorithm_trace: HOW was it computed?
    """
    entity_type: str
    entity_id: str
    risk_score: float                  # Final composite (0-100)
    confidence: float                  # Final calibrated confidence (0-1)
    ci_lower: float                    # Lower bound
    ci_upper: float                    # Upper bound
    severity_label: str                # "low" | "moderate" | "high" | "critical"
    is_reliable: bool                  # Enough data to trust?
    needs_human_review: bool           # Models disagree?
    n_signals: int                     # Signals that fed the assessment
    n_active_signals: int              # Non-expired signals
    data_freshness: str                # "fresh" | "aging" | "stale"
    primary_driver: str                # Main risk factor
    factors: list[dict] = field(default_factory=list)
    summary: str = ""
    algorithm_trace: dict = field(default_factory=dict)
    generated_at: str = ""


class RiskEngine:
    """
    Production risk assessment engine.

    Orchestrates: Temporal → Correlation → Fusion → Bayesian → Ensemble → Decomposition → Calibration
    """

    def __init__(self):
        self.bayesian = BayesianRiskEngine()
        self.fusion = SignalFusionEngine()
        self.calibration = CalibrationEngine()
        self.correlation = CorrelationEngine()
        self.ensemble = EnsembleEngine()
        self.temporal = TemporalDecayEngine()
        self.decomposition = DecompositionEngine()

    async def assess_entity(
        self,
        session: AsyncSession,
        company_id: str,
        entity_type: str,
        entity_id: str,
    ) -> RiskAssessment:
        """
        Full risk assessment for a single entity.

        Steps:
        1. Fetch all signals for this entity
        2. Apply temporal decay
        3. Detect correlations
        4. Fuse via weighted fusion
        5. Compute Bayesian posterior
        6. Ensemble the two methods
        7. Decompose into explainable factors
        """
        now = datetime.utcnow()

        # ── 1. Fetch signals ─────────────────────────────────────────
        result = await session.execute(
            select(Signal).where(
                and_(
                    Signal.company_id == company_id,
                    Signal.entity_type == entity_type,
                    Signal.entity_id == entity_id,
                    Signal.is_active.is_(True),
                )
            )
        )
        signals = result.scalars().all()

        if not signals:
            return self._empty_assessment(entity_type, entity_id, now)

        # ── 2. Temporal decay ────────────────────────────────────────
        temporal_inputs = [
            (s.signal_type, float(s.severity_score or 0), s.created_at)
            for s in signals
        ]
        temporal_result = self.temporal.aggregate(temporal_inputs, now)

        # ── 3. Correlation detection ─────────────────────────────────
        corr_observations = [
            SignalObservation(
                signal_type=s.signal_type,
                entity_id=str(s.entity_id),
                severity_score=float(s.severity_score or 0),
                timestamp=s.created_at.isoformat(),
            )
            for s in signals
        ]
        corr_report = self.correlation.analyze_correlations(corr_observations)

        # Apply correlation discount to scores
        raw_scores = {s.signal_type: float(s.severity_score or 0) for s in signals}
        adjusted_scores = self.correlation.apply_discount(raw_scores, corr_report)

        # ── 4. Weighted fusion ───────────────────────────────────────
        fusion_inputs = []
        for s in signals:
            adj_score = adjusted_scores.get(s.signal_type, float(s.severity_score or 0))
            fusion_inputs.append(SignalInput(
                signal_type=s.signal_type,
                severity_score=adj_score,
                confidence=float(s.confidence or 0.5),
            ))
        fusion_result = self.fusion.fuse(fusion_inputs)

        # ── 5. Bayesian posterior ────────────────────────────────────
        # Use historical outcomes for this entity type
        bad_outcomes = sum(1 for s in signals if (s.severity_score or 0) >= 70)
        good_outcomes = max(0, len(signals) - bad_outcomes)
        bayesian_result = self.bayesian.compute_risk_score(
            entity_type=entity_type,
            entity_id=entity_id,
            bad_outcomes=bad_outcomes,
            good_outcomes=good_outcomes,
            severity=fusion_result.fused_score,
        )

        # ── 6. Ensemble aggregation ──────────────────────────────────
        ensemble_result = self.ensemble.aggregate([
            ModelPrediction(
                model_name="weighted_fusion",
                risk_score=fusion_result.fused_score,
                confidence=fusion_result.fused_confidence,
                weight=0.6,
            ),
            ModelPrediction(
                model_name="bayesian_posterior",
                risk_score=bayesian_result.risk_probability * 100,
                confidence=bayesian_result.confidence,
                weight=0.4,
            ),
        ])

        # ── 7. Decomposition ────────────────────────────────────────
        factor_scores = {f.signal_type: f.raw_score for f in fusion_result.factors}
        factor_weights = {f.signal_type: f.weight for f in fusion_result.factors}
        decomp = self.decomposition.decompose(
            entity_type=entity_type,
            entity_id=entity_id,
            composite_score=ensemble_result.ensemble_score,
            confidence=ensemble_result.ensemble_confidence,
            factor_scores=factor_scores,
            factor_weights=factor_weights,
        )

        # ── Severity label ────────────────────────────────────────────
        score = ensemble_result.ensemble_score
        if score >= 75:
            severity_label = "critical"
        elif score >= 50:
            severity_label = "high"
        elif score >= 25:
            severity_label = "moderate"
        else:
            severity_label = "low"

        return RiskAssessment(
            entity_type=entity_type,
            entity_id=entity_id,
            risk_score=ensemble_result.ensemble_score,
            confidence=ensemble_result.ensemble_confidence,
            ci_lower=ensemble_result.ci_lower,
            ci_upper=ensemble_result.ci_upper,
            severity_label=severity_label,
            is_reliable=bayesian_result.is_reliable,
            needs_human_review=ensemble_result.needs_human_review,
            n_signals=len(signals),
            n_active_signals=temporal_result.n_active,
            data_freshness=temporal_result.freshness,
            primary_driver=decomp.primary_driver,
            factors=[
                {
                    "name": f.display_name,
                    "score": f.score,
                    "contribution_pct": f.contribution_pct,
                    "explanation": f.explanation,
                    "recommendation": f.recommendation,
                }
                for f in decomp.factors
            ],
            summary=decomp.summary,
            algorithm_trace={
                "fusion_score": fusion_result.fused_score,
                "bayesian_probability": bayesian_result.risk_probability,
                "ensemble_disagreement": ensemble_result.disagreement,
                "temporal_freshness": temporal_result.freshness,
                "n_correlated_pairs": corr_report.n_correlated_pairs,
            },
            generated_at=now.isoformat(),
        )

    async def assess_order(
        self,
        session: AsyncSession,
        company_id: str,
        order_id: str,
    ) -> RiskAssessment:
        """Assess risk for a specific order."""
        return await self.assess_entity(session, company_id, "order", order_id)

    async def assess_customer(
        self,
        session: AsyncSession,
        company_id: str,
        customer_id: str,
    ) -> RiskAssessment:
        """Assess risk for a specific customer."""
        return await self.assess_entity(session, company_id, "customer", customer_id)

    async def assess_route(
        self,
        session: AsyncSession,
        company_id: str,
        route_id: str,
    ) -> RiskAssessment:
        """Assess risk for a specific route."""
        return await self.assess_entity(session, company_id, "route", route_id)

    def _empty_assessment(
        self, entity_type: str, entity_id: str, now: datetime
    ) -> RiskAssessment:
        """Return a valid assessment when no signals exist."""
        return RiskAssessment(
            entity_type=entity_type,
            entity_id=entity_id,
            risk_score=0.0,
            confidence=0.0,
            ci_lower=0.0,
            ci_upper=0.0,
            severity_label="low",
            is_reliable=False,
            needs_human_review=False,
            n_signals=0,
            n_active_signals=0,
            data_freshness="stale",
            primary_driver="none",
            factors=[],
            summary="No signals available for this entity. Import data or run a scan.",
            algorithm_trace={},
            generated_at=now.isoformat(),
        )
