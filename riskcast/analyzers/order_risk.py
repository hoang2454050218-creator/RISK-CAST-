"""
Order Risk Scorer.

Computes a composite risk score for each active order based on:
- Customer risk signals (weight: 0.4)
- Route risk signals (weight: 0.3)
- Order value factor (weight: 0.15)
- New customer factor (weight: 0.15)

Respects company risk appetite for weight overrides.
"""

import structlog

from riskcast.analyzers.base import BaseAnalyzer, InternalSignal

logger = structlog.get_logger(__name__)


class OrderRiskScorer(BaseAnalyzer):
    """Computes composite risk scores for active orders."""

    DEFAULT_WEIGHTS = {
        "customer": 0.4,
        "route": 0.3,
        "value": 0.15,
        "new_customer": 0.15,
    }

    async def analyze(self, company_id: str) -> list[InternalSignal]:
        signals = []

        active_orders = await self.db.get_orders_by_status(
            company_id, statuses=["pending", "confirmed", "in_transit"]
        )

        # Load risk appetite for weight overrides
        appetite = await self.db.get_risk_appetite(company_id)
        weights = (
            appetite.get("weights", self.DEFAULT_WEIGHTS)
            if appetite
            else self.DEFAULT_WEIGHTS
        )

        # Batch fetch all active signals (1 query, not N)
        signal_map = await self.db.get_active_signals_map(company_id)

        for order in active_orders:
            # Customer signals
            c_signals = signal_map.get(
                ("customer", str(order.customer_id)), []
            ) if order.customer_id else []

            # Route signals
            r_signals = signal_map.get(
                ("route", str(order.route_id)), []
            ) if order.route_id else []

            c_score = max(
                (float(s.severity_score) for s in c_signals if s.severity_score),
                default=0,
            )
            r_score = max(
                (float(s.severity_score) for s in r_signals if s.severity_score),
                default=0,
            )
            v_factor = self._value_risk(order.total_value)
            n_factor = 20 if getattr(order, "customer_tier", "") == "new" else 0

            composite = (
                c_score * weights.get("customer", 0.4)
                + r_score * weights.get("route", 0.3)
                + v_factor * weights.get("value", 0.15)
                + n_factor * weights.get("new_customer", 0.15)
            )

            if composite > 30:
                signals.append(
                    InternalSignal(
                        source="internal_order",
                        signal_type="order_risk_composite",
                        entity_type="order",
                        entity_id=str(order.id),
                        confidence=self._avg_confidence(c_signals + r_signals),
                        severity_score=min(100, composite),
                        evidence={
                            "customer_risk": round(c_score, 1),
                            "route_risk": round(r_score, 1),
                            "value_factor": round(v_factor, 1),
                            "new_customer_factor": n_factor,
                            "weights": weights,
                        },
                        context={
                            "order_number": order.order_number,
                            "customer_id": str(order.customer_id) if order.customer_id else None,
                            "route_id": str(order.route_id) if order.route_id else None,
                            "total_value": float(order.total_value) if order.total_value else 0,
                        },
                    )
                )

        logger.info(
            "order_risk_scored",
            company_id=company_id,
            orders_scanned=len(active_orders),
            signals_found=len(signals),
        )
        return signals

    def _value_risk(self, value) -> float:
        """Map order value to a risk factor (0-30)."""
        if not value:
            return 0
        v = float(value)
        # Vietnamese dong thresholds
        if v > 500_000_000:  # > 500M VND (~$20k)
            return 30
        elif v > 100_000_000:  # > 100M VND (~$4k)
            return 15
        return 5

    def _avg_confidence(self, signals) -> float:
        """Average confidence of related signals."""
        if not signals:
            return 0.3
        return round(
            sum(float(s.confidence) for s in signals) / len(signals), 2
        )
