"""
Risk Decomposition Engine.

Breaks a composite risk score into explainable factors.
Every score must answer: "WHY is this entity at risk?"

Provides:
- Factor-level contributions (% of total)
- Natural language explanations
- Actionable recommendations per factor
"""

from dataclasses import dataclass, field
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class RiskFactor:
    """A single factor contributing to an entity's risk score."""
    factor_name: str              # e.g. "payment_risk"
    display_name: str             # e.g. "Payment Risk"
    score: float                  # 0-100
    weight: float                 # Factor weight used
    contribution_pct: float       # % of composite score
    explanation: str              # Human-readable WHY
    recommendation: str           # Actionable suggestion
    evidence: dict = field(default_factory=dict)  # Supporting data


@dataclass(frozen=True)
class RiskDecomposition:
    """
    Full decomposition of a composite risk score.

    Every number traces back to specific evidence and computations.
    """
    entity_type: str
    entity_id: str
    composite_score: float
    confidence: float
    factors: list[RiskFactor]
    primary_driver: str            # Factor with highest contribution
    summary: str                   # One-line summary
    data_gaps: list[str] = field(default_factory=list)  # Missing data that would improve accuracy


# ── Factor explanation templates ─────────────────────────────────────────

FACTOR_TEMPLATES: dict[str, dict] = {
    "payment_risk": {
        "display_name": "Payment Risk",
        "explanation_high": "Customer has a high late payment rate ({late_pct:.0f}% late in last 90 days). Recent average delay is {avg_delay:.0f} days.",
        "explanation_low": "Customer payment behavior is normal. {on_time_pct:.0f}% on-time in last 90 days.",
        "recommendation_high": "Consider requiring advance payment or reducing credit terms.",
        "recommendation_low": "No action needed. Continue monitoring.",
    },
    "route_disruption": {
        "display_name": "Route Disruption",
        "explanation_high": "Route {route_name} has a {delay_rate:.0f}% delay rate. {incident_count} incidents in the last 14 days.",
        "explanation_low": "Route is performing normally with {on_time_rate:.0f}% on-time rate.",
        "recommendation_high": "Consider alternative routes or adding buffer time to delivery estimates.",
        "recommendation_low": "No action needed.",
    },
    "order_risk_composite": {
        "display_name": "Order Composite Risk",
        "explanation_high": "Order combines multiple risk factors: customer creditworthiness ({customer_score:.0f}), route reliability ({route_score:.0f}), and value exposure (${value:,.0f}).",
        "explanation_low": "Order risk factors are within normal parameters.",
        "recommendation_high": "Review order before approval. Consider splitting shipment or requiring insurance.",
        "recommendation_low": "Standard processing recommended.",
    },
    "customer_creditworthiness": {
        "display_name": "Customer Creditworthiness",
        "explanation_high": "Customer tier: {tier}. Payment terms: {payment_terms} days. Outstanding exposure is elevated.",
        "explanation_low": "Customer is in good standing. Tier: {tier}.",
        "recommendation_high": "Review credit limits and consider additional collateral.",
        "recommendation_low": "No action needed.",
    },
    "market_volatility": {
        "display_name": "Market Volatility",
        "explanation_high": "Market conditions show elevated volatility. Freight rates changed {rate_change:.1f}% in the last week.",
        "explanation_low": "Market conditions are stable.",
        "recommendation_high": "Lock in rates where possible. Monitor daily.",
        "recommendation_low": "Standard market monitoring.",
    },
}

DEFAULT_TEMPLATE = {
    "display_name": "Risk Factor",
    "explanation_high": "Risk score is elevated at {score:.0f}/100.",
    "explanation_low": "Risk level is acceptable at {score:.0f}/100.",
    "recommendation_high": "Investigate and take appropriate action.",
    "recommendation_low": "No action needed.",
}


class DecompositionEngine:
    """
    Break composite risk scores into explainable factors.
    """

    def decompose(
        self,
        entity_type: str,
        entity_id: str,
        composite_score: float,
        confidence: float,
        factor_scores: dict[str, float],
        factor_weights: dict[str, float],
        factor_evidence: Optional[dict[str, dict]] = None,
    ) -> RiskDecomposition:
        """
        Decompose a composite score into explainable factors.

        Args:
            entity_type: "order", "customer", "route"
            entity_id: UUID
            composite_score: The composite risk score (0-100)
            confidence: Overall confidence (0-1)
            factor_scores: Per-factor scores (0-100)
            factor_weights: Per-factor weights (should sum to ~1.0)
            factor_evidence: Per-factor supporting data
        """
        evidence = factor_evidence or {}
        total_weighted = sum(
            factor_scores.get(k, 0) * factor_weights.get(k, 0)
            for k in factor_scores
        )

        factors: list[RiskFactor] = []
        data_gaps: list[str] = []

        for factor_name, score in factor_scores.items():
            weight = factor_weights.get(factor_name, 0.1)
            weighted = score * weight
            pct = (weighted / total_weighted * 100) if total_weighted > 0 else 0

            template = FACTOR_TEMPLATES.get(factor_name, DEFAULT_TEMPLATE)
            ev = evidence.get(factor_name, {"score": score})

            # Select high/low explanation based on score
            is_high = score >= 50
            explanation_key = "explanation_high" if is_high else "explanation_low"
            rec_key = "recommendation_high" if is_high else "recommendation_low"

            try:
                explanation = template[explanation_key].format(**ev, score=score)
            except (KeyError, TypeError):
                explanation = template[explanation_key].format(score=score) if "{score" in template[explanation_key] else template[explanation_key]

            try:
                recommendation = template[rec_key].format(**ev, score=score)
            except (KeyError, TypeError):
                recommendation = template[rec_key]

            factors.append(RiskFactor(
                factor_name=factor_name,
                display_name=template.get("display_name", factor_name),
                score=round(score, 1),
                weight=round(weight, 3),
                contribution_pct=round(pct, 1),
                explanation=explanation,
                recommendation=recommendation,
                evidence=ev,
            ))

            # Check for data gaps
            if factor_name not in evidence:
                data_gaps.append(f"No evidence data for {factor_name}")

        # Sort by contribution (highest first)
        factors.sort(key=lambda f: f.contribution_pct, reverse=True)

        primary_driver = factors[0].display_name if factors else "Unknown"

        # Build summary
        if composite_score >= 70:
            summary = f"HIGH RISK ({composite_score:.0f}/100): Primary driver is {primary_driver}."
        elif composite_score >= 40:
            summary = f"MODERATE RISK ({composite_score:.0f}/100): Key factor is {primary_driver}."
        else:
            summary = f"LOW RISK ({composite_score:.0f}/100): All factors within acceptable range."

        return RiskDecomposition(
            entity_type=entity_type,
            entity_id=entity_id,
            composite_score=round(composite_score, 1),
            confidence=round(confidence, 4),
            factors=factors,
            primary_driver=primary_driver,
            summary=summary,
            data_gaps=data_gaps,
        )
