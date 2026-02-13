"""
Multi-Factor Signal Fusion Engine.

Combines multiple risk signals into a single composite score using:
- Configurable factor weights (must sum to 1.0)
- Uncertainty propagation through the fusion
- Factor-level contribution tracking

Every output is fully traceable to its input signals.
"""

import math
from dataclasses import dataclass, field
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


# ── Configuration ─────────────────────────────────────────────────────────

DEFAULT_WEIGHTS: dict[str, float] = {
    "payment_risk": 0.30,
    "route_disruption": 0.25,
    "order_risk_composite": 0.20,
    "customer_creditworthiness": 0.15,
    "market_volatility": 0.10,
}


@dataclass(frozen=True)
class SignalInput:
    """A single signal to be fused."""
    signal_type: str
    severity_score: float        # 0-100
    confidence: float            # 0-1
    weight: Optional[float] = None  # Override default weight
    source: str = "internal"


@dataclass(frozen=True)
class FusionFactor:
    """How a single factor contributed to the fused score."""
    signal_type: str
    raw_score: float
    confidence: float
    weight: float
    weighted_contribution: float  # weight × confidence × raw_score
    pct_contribution: float       # % of total fused score


@dataclass(frozen=True)
class FusedRiskScore:
    """
    Output of multi-factor signal fusion.

    The fused_score accounts for both signal severity AND confidence:
      fused = Σ(weight_i × confidence_i × severity_i) / Σ(weight_i × confidence_i)

    This means low-confidence signals have less influence on the composite.
    """
    fused_score: float            # Composite risk score (0-100)
    fused_confidence: float       # Composite confidence (0-1)
    ci_lower: float               # Lower bound
    ci_upper: float               # Upper bound
    n_signals: int                # Number of signals fused
    factors: list[FusionFactor]   # Per-factor breakdown
    weights_used: dict[str, float]  # Weights that were applied
    algorithm: str = "weighted_confidence_fusion"

    @property
    def dominant_factor(self) -> Optional[FusionFactor]:
        """The single factor contributing most to the fused score."""
        if not self.factors:
            return None
        return max(self.factors, key=lambda f: f.pct_contribution)


class SignalFusionEngine:
    """
    Multi-factor signal fusion with confidence weighting.

    Weights are configurable per company via risk_appetite overrides.
    """

    def __init__(self, weights: Optional[dict[str, float]] = None):
        self.weights = weights or DEFAULT_WEIGHTS.copy()

    def fuse(self, signals: list[SignalInput]) -> FusedRiskScore:
        """
        Fuse multiple signals into a single composite risk score.

        Formula:
          fused = Σ(w_i × c_i × s_i) / Σ(w_i × c_i)

        Where:
          w_i = weight for signal type i
          c_i = confidence of signal i (0-1)
          s_i = severity score of signal i (0-100)
        """
        if not signals:
            return FusedRiskScore(
                fused_score=0.0,
                fused_confidence=0.0,
                ci_lower=0.0,
                ci_upper=0.0,
                n_signals=0,
                factors=[],
                weights_used=self.weights,
            )

        weighted_sum = 0.0
        weight_conf_sum = 0.0
        factors: list[FusionFactor] = []

        for sig in signals:
            w = sig.weight if sig.weight is not None else self.weights.get(sig.signal_type, 0.1)
            contribution = w * sig.confidence * sig.severity_score
            weighted_sum += contribution
            weight_conf_sum += w * sig.confidence
            factors.append(FusionFactor(
                signal_type=sig.signal_type,
                raw_score=sig.severity_score,
                confidence=sig.confidence,
                weight=w,
                weighted_contribution=round(contribution, 4),
                pct_contribution=0.0,  # Will be computed below
            ))

        # Compute fused score
        if weight_conf_sum > 0:
            fused_score = weighted_sum / weight_conf_sum
        else:
            fused_score = 0.0

        # Compute per-factor percentages
        total_contribution = sum(f.weighted_contribution for f in factors)
        if total_contribution > 0:
            factors = [
                FusionFactor(
                    signal_type=f.signal_type,
                    raw_score=f.raw_score,
                    confidence=f.confidence,
                    weight=f.weight,
                    weighted_contribution=f.weighted_contribution,
                    pct_contribution=round(f.weighted_contribution / total_contribution * 100, 1),
                )
                for f in factors
            ]

        # Composite confidence: weighted average of individual confidences
        total_weight = sum(
            (sig.weight if sig.weight is not None else self.weights.get(sig.signal_type, 0.1))
            for sig in signals
        )
        if total_weight > 0:
            fused_confidence = sum(
                (sig.weight if sig.weight is not None else self.weights.get(sig.signal_type, 0.1)) * sig.confidence
                for sig in signals
            ) / total_weight
        else:
            fused_confidence = 0.0

        # Uncertainty: propagate via root-sum-squares of weighted uncertainties
        uncertainties = []
        for sig in signals:
            w = sig.weight if sig.weight is not None else self.weights.get(sig.signal_type, 0.1)
            # Uncertainty of each signal ≈ score × (1 - confidence)
            u = w * sig.severity_score * (1.0 - sig.confidence)
            uncertainties.append(u)

        combined_uncertainty = math.sqrt(sum(u ** 2 for u in uncertainties)) if uncertainties else 0.0
        ci_lower = max(0.0, fused_score - combined_uncertainty)
        ci_upper = min(100.0, fused_score + combined_uncertainty)

        return FusedRiskScore(
            fused_score=round(fused_score, 2),
            fused_confidence=round(fused_confidence, 4),
            ci_lower=round(ci_lower, 2),
            ci_upper=round(ci_upper, 2),
            n_signals=len(signals),
            factors=factors,
            weights_used=self.weights,
        )

    def update_weights(self, overrides: dict[str, float]) -> None:
        """Update weights (e.g. from company risk appetite)."""
        self.weights.update(overrides)
        # Normalize to sum to 1.0
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in self.weights.items()}
