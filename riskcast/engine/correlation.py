"""
Signal Correlation Engine.

Detects correlated signals to prevent double-counting in risk aggregation.

Problem: If payment_risk and order_risk both reflect the same underlying issue
(e.g. a customer defaulting), naively summing them overestimates risk.

Solution:
1. Compute pairwise correlation between signal types
2. Apply correlation discount to overlapping signals
3. Track which signals are correlated for explainability
"""

import math
from dataclasses import dataclass, field
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────

CORRELATION_THRESHOLD: float = 0.5   # Signals correlated if ρ > this
CORRELATION_DISCOUNT: float = 0.5    # Discount factor for correlated signals


@dataclass(frozen=True)
class CorrelationPair:
    """A pair of correlated signal types."""
    signal_a: str
    signal_b: str
    correlation: float         # Pearson correlation coefficient
    n_co_occurrences: int      # How many times they co-occurred
    discount_applied: float    # How much we discounted


@dataclass(frozen=True)
class CorrelationReport:
    """Full correlation analysis of a signal set."""
    n_signals: int
    n_correlated_pairs: int
    pairs: list[CorrelationPair]
    effective_signals: int     # After discounting correlated ones
    total_discount: float      # Total severity discount applied


@dataclass
class SignalObservation:
    """A signal observation for correlation analysis."""
    signal_type: str
    entity_id: str
    severity_score: float
    timestamp: str


class CorrelationEngine:
    """
    Detect and handle correlated signals.

    Two signals are considered correlated if they frequently co-occur
    on the same entity (e.g. same order has both payment_risk and order_risk).
    """

    def __init__(
        self,
        threshold: float = CORRELATION_THRESHOLD,
        discount: float = CORRELATION_DISCOUNT,
    ):
        self.threshold = threshold
        self.discount = discount

    def analyze_correlations(
        self,
        signals: list[SignalObservation],
    ) -> CorrelationReport:
        """
        Analyze signal correlations based on entity co-occurrence.

        Two signal types are correlated if they frequently appear
        on the same entity_id.
        """
        if len(signals) < 2:
            return CorrelationReport(
                n_signals=len(signals),
                n_correlated_pairs=0,
                pairs=[],
                effective_signals=len(signals),
                total_discount=0.0,
            )

        # Group signals by entity
        entity_signals: dict[str, set[str]] = {}
        for s in signals:
            if s.entity_id not in entity_signals:
                entity_signals[s.entity_id] = set()
            entity_signals[s.entity_id].add(s.signal_type)

        # Get unique signal types
        all_types = sorted({s.signal_type for s in signals})

        # Count co-occurrences
        type_entities: dict[str, set[str]] = {}
        for s in signals:
            if s.signal_type not in type_entities:
                type_entities[s.signal_type] = set()
            type_entities[s.signal_type].add(s.entity_id)

        n_entities = len(entity_signals)
        pairs: list[CorrelationPair] = []

        for i, type_a in enumerate(all_types):
            for type_b in all_types[i + 1:]:
                entities_a = type_entities.get(type_a, set())
                entities_b = type_entities.get(type_b, set())

                co_occurring = entities_a & entities_b
                n_co = len(co_occurring)

                if n_co == 0:
                    continue

                # Jaccard similarity as proxy for correlation
                union = len(entities_a | entities_b)
                correlation = n_co / max(union, 1)

                if correlation >= self.threshold:
                    discount = self.discount * correlation
                    pairs.append(CorrelationPair(
                        signal_a=type_a,
                        signal_b=type_b,
                        correlation=round(correlation, 4),
                        n_co_occurrences=n_co,
                        discount_applied=round(discount, 4),
                    ))

        total_discount = sum(p.discount_applied for p in pairs)
        correlated_types = set()
        for p in pairs:
            correlated_types.add(p.signal_a)
            correlated_types.add(p.signal_b)

        effective = len(all_types) - len(correlated_types) * (1 - (1 - self.discount))

        return CorrelationReport(
            n_signals=len(signals),
            n_correlated_pairs=len(pairs),
            pairs=pairs,
            effective_signals=max(1, round(effective)),
            total_discount=round(total_discount, 4),
        )

    def apply_discount(
        self,
        scores: dict[str, float],
        report: CorrelationReport,
    ) -> dict[str, float]:
        """
        Apply correlation discounts to severity scores.

        For each correlated pair, reduce the lower-severity signal's score
        by the discount factor to avoid double-counting.
        """
        adjusted = dict(scores)

        for pair in report.pairs:
            score_a = adjusted.get(pair.signal_a, 0)
            score_b = adjusted.get(pair.signal_b, 0)

            # Discount the weaker signal
            if score_a <= score_b:
                adjusted[pair.signal_a] = score_a * (1 - pair.discount_applied)
            else:
                adjusted[pair.signal_b] = score_b * (1 - pair.discount_applied)

        return adjusted
