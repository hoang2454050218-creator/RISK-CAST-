"""
Route Disruption Analyzer.

Detects routes with high delay rates by cross-referencing:
1. Internal order delay data (last 14 days)
2. OMEN macro signals (if available — graceful degradation)
"""

import structlog

from riskcast.analyzers.base import BaseAnalyzer, InternalSignal

logger = structlog.get_logger(__name__)


class RouteDisruptionAnalyzer(BaseAnalyzer):
    """Analyzes route performance to detect disruptions."""

    async def analyze(self, company_id: str) -> list[InternalSignal]:
        signals = []
        routes = await self.db.get_active_routes(company_id)

        for route in routes:
            orders = await self.db.get_route_orders(
                company_id, str(route.id), days=14
            )
            if len(orders) < 3:
                continue

            # Calculate delay rate from internal data
            delayed = sum(
                1
                for o in orders
                if o.actual_date and o.expected_date and o.actual_date > o.expected_date
            )
            delay_rate = delayed / len(orders)

            # Cross-reference OMEN macro signals (graceful if unavailable)
            macro_signals = []
            if self.omen_client:
                macro_signals = await self.omen_client.get_market_signals(
                    location=route.destination
                )

            macro_boost = (
                0.15
                if any(s.confidence > 0.6 for s in macro_signals)
                else 0
            )
            combined = min(0.95, delay_rate + 0.2 + macro_boost)

            if combined > 0.5:
                signals.append(
                    InternalSignal(
                        source="internal_route",
                        signal_type="route_disruption",
                        entity_type="route",
                        entity_id=str(route.id),
                        confidence=combined,
                        severity_score=combined * 100,
                        evidence={
                            "delay_rate_14d": round(delay_rate, 2),
                            "orders_analyzed": len(orders),
                            "delayed_orders": delayed,
                            "macro_signals": [
                                {"type": s.signal_type, "confidence": s.confidence}
                                for s in macro_signals[:3]
                            ],
                        },
                        context={
                            "route_name": route.name,
                            "origin": route.origin,
                            "destination": route.destination,
                        },
                    )
                )

        logger.info(
            "route_disruption_analyzed",
            company_id=company_id,
            routes_scanned=len(routes),
            signals_found=len(signals),
        )
        return signals
