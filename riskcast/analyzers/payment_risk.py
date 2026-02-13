"""
Payment Risk Analyzer.

Detects:
1. High late payment ratio (>30% late in 90 days)
2. Sudden behavior change (recent avg delay > 1.5x historical)
"""

import structlog

from riskcast.analyzers.base import BaseAnalyzer, InternalSignal

logger = structlog.get_logger(__name__)


class PaymentRiskAnalyzer(BaseAnalyzer):
    """Analyzes payment patterns to detect customer payment risk."""

    async def analyze(self, company_id: str) -> list[InternalSignal]:
        signals = []
        customers = await self.db.get_customers_with_payments(company_id)

        for customer in customers:
            history = await self.db.get_payment_history(
                company_id, str(customer.id), days=90
            )
            if not history:
                continue

            # ── Pattern 1: High late payment ratio ────────────────────
            late_count = sum(1 for p in history if self._days_overdue(p) > 0)
            late_ratio = late_count / len(history)

            if late_ratio > 0.3:
                avg_overdue = (
                    sum(self._days_overdue(p) for p in history if self._days_overdue(p) > 0)
                    / max(late_count, 1)
                )
                signals.append(
                    InternalSignal(
                        source="internal_payment",
                        signal_type="payment_risk",
                        entity_type="customer",
                        entity_id=str(customer.id),
                        confidence=min(0.95, late_ratio + 0.2),
                        severity_score=late_ratio * 100,
                        evidence={
                            "late_ratio_90d": round(late_ratio, 2),
                            "total_payments": len(history),
                            "late_payments": late_count,
                            "avg_days_overdue": round(avg_overdue, 1),
                            "trend": self._calc_trend(history),
                        },
                        context={
                            "customer_name": customer.name,
                            "customer_tier": customer.tier,
                        },
                    )
                )

            # ── Pattern 2: Sudden behavior change ────────────────────
            recent = history[-5:] if len(history) >= 5 else []
            older = history[:-5] if len(history) > 5 else []

            if recent and older:
                recent_avg = sum(self._days_overdue(p) for p in recent) / len(recent)
                older_avg = sum(self._days_overdue(p) for p in older) / len(older)

                if older_avg > 0 and recent_avg > older_avg * 1.5 and recent_avg > 5:
                    signals.append(
                        InternalSignal(
                            source="internal_payment",
                            signal_type="payment_behavior_change",
                            entity_type="customer",
                            entity_id=str(customer.id),
                            confidence=0.75,
                            severity_score=min(
                                80, (recent_avg / max(older_avg, 1)) * 30
                            ),
                            evidence={
                                "recent_avg_delay": round(recent_avg, 1),
                                "historical_avg_delay": round(older_avg, 1),
                                "change_ratio": round(
                                    recent_avg / max(older_avg, 1), 2
                                ),
                            },
                            context={"customer_name": customer.name},
                        )
                    )

        logger.info(
            "payment_risk_analyzed",
            company_id=company_id,
            customers_scanned=len(customers),
            signals_found=len(signals),
        )
        return signals

    def _days_overdue(self, payment) -> int:
        """Calculate days overdue for a payment."""
        from datetime import date as date_type

        if payment.paid_date and payment.due_date:
            delta = payment.paid_date - payment.due_date
            return max(0, delta.days)
        elif payment.due_date and payment.paid_date is None:
            today = date_type.today()
            if payment.due_date < today:
                return (today - payment.due_date).days
        return 0

    def _calc_trend(self, history) -> str:
        """Calculate payment trend from history."""
        if len(history) < 4:
            return "insufficient_data"

        recent_avg = sum(self._days_overdue(p) for p in history[-3:]) / 3
        older_slice = history[-6:-3]
        if not older_slice:
            return "insufficient_data"
        older_avg = sum(self._days_overdue(p) for p in older_slice) / len(older_slice)

        if older_avg == 0:
            return "stable" if recent_avg == 0 else "worsening"
        if recent_avg > older_avg * 1.2:
            return "worsening"
        elif recent_avg < older_avg * 0.8:
            return "improving"
        return "stable"
