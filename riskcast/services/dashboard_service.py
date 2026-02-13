"""
Dashboard Service — Real aggregated metrics from SQL queries.

Every number traces to a real query. Zero mock data.
If database is empty, returns zeros with a helpful message.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.models import Customer, Incident, Order, Payment, Signal
from riskcast.schemas.dashboard import (
    DailyCount,
    DailyRiskLevel,
    DashboardSummary,
    DataFreshness,
    TopRisk,
)

logger = structlog.get_logger(__name__)


class DashboardService:
    """Compute dashboard metrics from real database queries."""

    async def get_summary(
        self,
        session: AsyncSession,
        company_id: str,
        period_days: int = 7,
    ) -> DashboardSummary:
        """Build the full dashboard summary from real data."""
        now = datetime.utcnow()
        cutoff = now - timedelta(days=period_days)
        period_label = f"last_{period_days}_days"

        # ── Core Counts ──────────────────────────────────────────
        total_orders = await self._count(session, Order, company_id)
        total_customers = await self._count(session, Customer, company_id)
        active_signals = await self._count_where(
            session, Signal, company_id, Signal.is_active.is_(True)
        )
        critical_signals = await self._count_where(
            session, Signal, company_id,
            and_(Signal.is_active.is_(True), Signal.severity_score >= 70),
        )

        # Total revenue
        rev_result = await session.execute(
            select(func.coalesce(func.sum(Order.total_value), 0))
            .where(Order.company_id == company_id)
        )
        total_revenue = float(rev_result.scalar_one() or 0)

        # Orders at risk (orders linked to active high-severity signals)
        risk_result = await session.execute(
            select(func.count(func.distinct(Signal.entity_id)))
            .where(
                and_(
                    Signal.company_id == company_id,
                    Signal.is_active.is_(True),
                    Signal.severity_score >= 50,
                    Signal.entity_type == "order",
                )
            )
        )
        orders_at_risk = risk_result.scalar_one() or 0

        # ── Trends (last N days) ──────────────────────────────────
        signal_trend = await self._daily_counts(
            session, Signal, company_id, Signal.created_at, cutoff, period_days
        )
        order_trend = await self._daily_counts(
            session, Order, company_id, Order.created_at, cutoff, period_days
        )
        risk_trend = await self._daily_risk(session, company_id, cutoff, period_days)

        # ── Top Risks ────────────────────────────────────────────
        top_risks_result = await session.execute(
            select(Signal)
            .where(
                and_(
                    Signal.company_id == company_id,
                    Signal.is_active.is_(True),
                )
            )
            .order_by(Signal.severity_score.desc().nullslast())
            .limit(5)
        )
        top_risks = [
            TopRisk(
                signal_id=str(s.id),
                signal_type=s.signal_type,
                severity_score=float(s.severity_score) if s.severity_score else 0,
                entity_type=s.entity_type,
                entity_id=str(s.entity_id) if s.entity_id else None,
                summary=f"{s.signal_type}: severity {float(s.severity_score or 0):.0f}",
            )
            for s in top_risks_result.scalars().all()
        ]

        # ── Data Freshness ────────────────────────────────────────
        freshness = await self._compute_freshness(session, company_id, now)

        # ── Data Completeness ─────────────────────────────────────
        completeness, gaps = self._assess_completeness(
            total_orders, total_customers, active_signals, freshness
        )

        # Empty state message
        message = None
        if total_orders == 0 and active_signals == 0:
            message = (
                "No data yet. Import orders via CSV or connect OMEN "
                "to start receiving signals."
            )

        return DashboardSummary(
            period=period_label,
            generated_at=now.isoformat(),
            data_freshness=freshness,
            total_orders=total_orders,
            active_signals=active_signals,
            critical_signals=critical_signals,
            orders_at_risk=orders_at_risk,
            total_revenue=total_revenue,
            total_customers=total_customers,
            signal_trend=signal_trend,
            order_trend=order_trend,
            risk_trend=risk_trend,
            pending_decisions=0,  # Will be populated when decision engine exists
            top_risks=top_risks,
            recent_actions=[],
            data_completeness=completeness,
            known_gaps=gaps,
            message=message,
        )

    # ── Private helpers ───────────────────────────────────────────────

    async def _count(self, session: AsyncSession, model, company_id: str) -> int:
        result = await session.execute(
            select(func.count()).select_from(model).where(model.company_id == company_id)
        )
        return result.scalar_one() or 0

    async def _count_where(self, session: AsyncSession, model, company_id: str, *conditions):
        result = await session.execute(
            select(func.count())
            .select_from(model)
            .where(model.company_id == company_id, *conditions)
        )
        return result.scalar_one() or 0

    async def _daily_counts(
        self, session, model, company_id, date_col, cutoff, period_days
    ) -> list[DailyCount]:
        result = await session.execute(
            select(
                func.date(date_col).label("day"),
                func.count().label("cnt"),
            )
            .where(and_(model.company_id == company_id, date_col >= cutoff))
            .group_by(func.date(date_col))
            .order_by(func.date(date_col))
        )
        rows = {str(r.day): r.cnt for r in result.all()}

        # Pad missing days with zeros
        today = datetime.utcnow().date()
        series = []
        for i in range(period_days):
            d = today - timedelta(days=period_days - 1 - i)
            series.append(DailyCount(date=str(d), count=rows.get(str(d), 0)))
        return series

    async def _daily_risk(
        self, session, company_id, cutoff, period_days
    ) -> list[DailyRiskLevel]:
        result = await session.execute(
            select(
                func.date(Signal.created_at).label("day"),
                func.avg(Signal.severity_score).label("avg_risk"),
                func.count().label("cnt"),
            )
            .where(and_(Signal.company_id == company_id, Signal.created_at >= cutoff))
            .group_by(func.date(Signal.created_at))
            .order_by(func.date(Signal.created_at))
        )
        rows = {str(r.day): (float(r.avg_risk or 0), r.cnt) for r in result.all()}

        today = datetime.utcnow().date()
        series = []
        for i in range(period_days):
            d = today - timedelta(days=period_days - 1 - i)
            avg_r, cnt = rows.get(str(d), (0.0, 0))
            series.append(DailyRiskLevel(
                date=str(d), avg_risk_score=round(avg_r, 2), signal_count=cnt
            ))
        return series

    async def _compute_freshness(
        self, session: AsyncSession, company_id: str, now: datetime
    ) -> DataFreshness:
        async def _max_date(model, col):
            r = await session.execute(
                select(func.max(col)).where(model.company_id == company_id)
            )
            return r.scalar_one()

        last_signal = await _max_date(Signal, Signal.created_at)
        last_order = await _max_date(Order, Order.created_at)
        last_payment = await _max_date(Payment, Payment.created_at)

        # Determine staleness
        most_recent = max(filter(None, [last_signal, last_order, last_payment]), default=None)
        # Strip tzinfo for consistent arithmetic (DB may return aware datetimes)
        if most_recent is not None and most_recent.tzinfo is not None:
            most_recent = most_recent.replace(tzinfo=None)
        if most_recent is None:
            staleness = "no_data"
        elif (now - most_recent).total_seconds() < 3600:
            staleness = "fresh"
        elif (now - most_recent).total_seconds() < 86400:
            staleness = "stale"
        else:
            staleness = "outdated"

        return DataFreshness(
            last_signal_at=last_signal.isoformat() if last_signal else None,
            last_order_at=last_order.isoformat() if last_order else None,
            last_payment_at=last_payment.isoformat() if last_payment else None,
            staleness_level=staleness,
        )

    def _assess_completeness(
        self, orders: int, customers: int, signals: int, freshness: DataFreshness
    ) -> tuple[float, list[str]]:
        score = 0.0
        gaps: list[str] = []
        checks = 0

        if orders > 0:
            score += 1
        else:
            gaps.append("No order data imported")
        checks += 1

        if customers > 0:
            score += 1
        else:
            gaps.append("No customer data")
        checks += 1

        if signals > 0:
            score += 1
        else:
            gaps.append("No signals — connect OMEN or run a scan")
        checks += 1

        if freshness.staleness_level in ("fresh", "stale"):
            score += 1
        else:
            gaps.append("Data is outdated or missing")
        checks += 1

        return round(score / max(checks, 1), 2), gaps
