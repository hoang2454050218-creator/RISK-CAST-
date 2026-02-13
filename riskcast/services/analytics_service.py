"""
Analytics Service — Real aggregated analytics from SQL queries.

Every endpoint reports data_sufficiency to communicate reliability.
"""

from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.models import Incident, Order, Route, Signal
from riskcast.schemas.analytics import (
    CategoryBreakdown,
    RiskByCategoryResponse,
    RiskByRouteResponse,
    RiskOverTimeResponse,
    RouteRisk,
    SystemHealthResponse,
    TimeSeriesPoint,
    TopRiskFactorsResponse,
    RiskFactor,
)

logger = structlog.get_logger(__name__)


def _sufficiency(n: int) -> str:
    if n < 50:
        return "insufficient"
    if n < 200:
        return "developing"
    return "reliable"


class AnalyticsService:
    """Compute analytics from real database data."""

    async def risk_over_time(
        self, session: AsyncSession, company_id: str, days: int = 30
    ) -> RiskOverTimeResponse:
        """Average risk score per day over the period."""
        now = datetime.utcnow()
        cutoff = now - timedelta(days=days)

        result = await session.execute(
            select(
                func.date(Signal.created_at).label("day"),
                func.avg(Signal.severity_score).label("avg_sev"),
                func.count().label("cnt"),
            )
            .where(and_(Signal.company_id == company_id, Signal.created_at >= cutoff))
            .group_by(func.date(Signal.created_at))
            .order_by(func.date(Signal.created_at))
        )
        rows = result.all()
        total_points = sum(r.cnt for r in rows)

        series = [
            TimeSeriesPoint(
                date=str(r.day),
                value=round(float(r.avg_sev or 0), 2),
                count=r.cnt,
            )
            for r in rows
        ]

        return RiskOverTimeResponse(
            period=f"last_{days}_days",
            generated_at=now.isoformat(),
            data_sufficiency=_sufficiency(total_points),
            data_points=total_points,
            series=series,
            message="Insufficient data for reliable trends" if total_points < 50 else None,
        )

    async def risk_by_category(
        self, session: AsyncSession, company_id: str
    ) -> RiskByCategoryResponse:
        """Risk breakdown by signal type/category."""
        now = datetime.utcnow()

        result = await session.execute(
            select(
                Signal.signal_type,
                func.count().label("cnt"),
                func.avg(Signal.severity_score).label("avg_sev"),
                func.max(Signal.severity_score).label("max_sev"),
            )
            .where(and_(Signal.company_id == company_id, Signal.is_active.is_(True)))
            .group_by(Signal.signal_type)
            .order_by(func.count().desc())
        )
        rows = result.all()
        total = sum(r.cnt for r in rows)

        categories = [
            CategoryBreakdown(
                category=r.signal_type,
                count=r.cnt,
                avg_severity=round(float(r.avg_sev or 0), 1),
                max_severity=round(float(r.max_sev or 0), 1),
                pct_of_total=round(r.cnt / max(total, 1) * 100, 1),
            )
            for r in rows
        ]

        return RiskByCategoryResponse(
            period="current",
            generated_at=now.isoformat(),
            data_sufficiency=_sufficiency(total),
            data_points=total,
            categories=categories,
        )

    async def risk_by_route(
        self, session: AsyncSession, company_id: str
    ) -> RiskByRouteResponse:
        """Risk metrics per route."""
        now = datetime.utcnow()

        routes_result = await session.execute(
            select(Route).where(Route.company_id == company_id)
        )
        routes = routes_result.scalars().all()

        route_risks = []
        total_points = 0
        for route in routes:
            # Count signals linked to this route
            sig_result = await session.execute(
                select(func.count(), func.avg(Signal.severity_score))
                .where(and_(
                    Signal.company_id == company_id,
                    Signal.entity_type == "route",
                    Signal.entity_id == route.id,
                ))
            )
            sig_row = sig_result.one()
            sig_count = sig_row[0] or 0
            avg_sev = float(sig_row[1] or 0)

            # Count incidents
            inc_result = await session.execute(
                select(func.count())
                .where(and_(
                    Incident.company_id == company_id,
                    Incident.route_id == route.id,
                ))
            )
            inc_count = inc_result.scalar_one() or 0

            total_points += sig_count

            route_risks.append(RouteRisk(
                route_id=str(route.id),
                route_name=route.name,
                origin=route.origin,
                destination=route.destination,
                signal_count=sig_count,
                avg_severity=round(avg_sev, 1),
                incident_count=inc_count,
            ))

        route_risks.sort(key=lambda r: r.avg_severity, reverse=True)

        return RiskByRouteResponse(
            period="all_time",
            generated_at=now.isoformat(),
            data_sufficiency=_sufficiency(total_points),
            data_points=total_points,
            routes=route_risks,
        )

    async def top_risk_factors(
        self, session: AsyncSession, company_id: str
    ) -> TopRiskFactorsResponse:
        """Most common risk factors across all active signals."""
        now = datetime.utcnow()

        result = await session.execute(
            select(
                Signal.signal_type,
                func.count().label("cnt"),
                func.avg(Signal.severity_score).label("avg_sev"),
            )
            .where(and_(Signal.company_id == company_id, Signal.is_active.is_(True)))
            .group_by(Signal.signal_type)
            .order_by(func.avg(Signal.severity_score).desc())
            .limit(10)
        )
        rows = result.all()
        total = sum(r.cnt for r in rows)

        factors = [
            RiskFactor(
                factor=r.signal_type,
                impact_score=round(float(r.avg_sev or 0), 1),
                occurrence_count=r.cnt,
                pct_contribution=round(r.cnt / max(total, 1) * 100, 1),
            )
            for r in rows
        ]

        return TopRiskFactorsResponse(
            period="current",
            generated_at=now.isoformat(),
            data_sufficiency=_sufficiency(total),
            data_points=total,
            factors=factors,
        )
