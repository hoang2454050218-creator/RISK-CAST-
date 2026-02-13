"""
Analytics API Tests — Real aggregated analytics.

Tests: data sufficiency, empty state, category breakdown, route metrics.
"""

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.models import Company, Incident, Route, Signal
from riskcast.services.analytics_service import AnalyticsService, _sufficiency


class TestDataSufficiency:
    """Test the data sufficiency classification."""

    def test_insufficient(self):
        assert _sufficiency(0) == "insufficient"
        assert _sufficiency(49) == "insufficient"

    def test_developing(self):
        assert _sufficiency(50) == "developing"
        assert _sufficiency(199) == "developing"

    def test_reliable(self):
        assert _sufficiency(200) == "reliable"
        assert _sufficiency(10000) == "reliable"


@pytest_asyncio.fixture
async def analytics_company(session_factory) -> Company:
    async with session_factory() as session:
        company = Company(
            id=uuid.uuid4(),
            name="Analytics Co",
            slug=f"analytics-{uuid.uuid4().hex[:8]}",
        )
        session.add(company)
        await session.commit()
        await session.refresh(company)
        return company


@pytest_asyncio.fixture
async def analytics_data(session_factory, analytics_company) -> Company:
    """Populate with signals and routes for analytics."""
    cid = analytics_company.id
    async with session_factory() as session:
        # Routes
        route = Route(
            company_id=cid, name="Saigon-Hamburg",
            origin="Ho Chi Minh City", destination="Hamburg",
        )
        session.add(route)
        await session.flush()

        # Signals of different types — each with unique entity_id
        for i in range(20):
            signal_types = ["payment_risk", "order_risk_composite", "route_disruption"]
            sig_type = signal_types[i % 3]
            ent_type = "route" if i % 3 == 2 else "order"
            ent_id = route.id if i % 3 == 2 else uuid.uuid4()
            session.add(Signal(
                company_id=cid,
                source=f"internal_{i}",
                signal_type=sig_type,
                entity_type=ent_type,
                entity_id=ent_id,
                confidence=Decimal("0.75"),
                severity_score=Decimal(str(20 + i * 4)),
                evidence={"test": True, "index": i},
                is_active=True,
            ))

        # Incidents
        session.add(Incident(
            company_id=cid, route_id=route.id,
            type="delay", severity="high", description="Port congestion",
        ))
        await session.commit()
    return analytics_company


@pytest.mark.asyncio
class TestAnalyticsService:

    async def test_risk_over_time_empty(self, db: AsyncSession, analytics_company):
        svc = AnalyticsService()
        result = await svc.risk_over_time(db, str(analytics_company.id))
        assert result.data_sufficiency == "insufficient"
        assert result.data_points == 0
        assert len(result.series) == 0

    async def test_risk_over_time_with_data(self, db: AsyncSession, analytics_data):
        svc = AnalyticsService()
        result = await svc.risk_over_time(db, str(analytics_data.id))
        assert result.data_points > 0
        assert len(result.series) > 0
        assert result.generated_at is not None

    async def test_risk_by_category_empty(self, db: AsyncSession, analytics_company):
        svc = AnalyticsService()
        result = await svc.risk_by_category(db, str(analytics_company.id))
        assert result.data_points == 0
        assert len(result.categories) == 0

    async def test_risk_by_category_with_data(self, db: AsyncSession, analytics_data):
        svc = AnalyticsService()
        result = await svc.risk_by_category(db, str(analytics_data.id))
        assert result.data_points == 20
        assert len(result.categories) == 3
        # Percentages should sum to ~100
        total_pct = sum(c.pct_of_total for c in result.categories)
        assert 99 <= total_pct <= 101

    async def test_risk_by_route_empty(self, db: AsyncSession, analytics_company):
        svc = AnalyticsService()
        result = await svc.risk_by_route(db, str(analytics_company.id))
        assert len(result.routes) == 0

    async def test_risk_by_route_with_data(self, db: AsyncSession, analytics_data):
        svc = AnalyticsService()
        result = await svc.risk_by_route(db, str(analytics_data.id))
        assert len(result.routes) >= 1
        route = result.routes[0]
        assert route.route_name == "Saigon-Hamburg"
        assert route.incident_count >= 1

    async def test_top_risk_factors_empty(self, db: AsyncSession, analytics_company):
        svc = AnalyticsService()
        result = await svc.top_risk_factors(db, str(analytics_company.id))
        assert len(result.factors) == 0

    async def test_top_risk_factors_with_data(self, db: AsyncSession, analytics_data):
        svc = AnalyticsService()
        result = await svc.top_risk_factors(db, str(analytics_data.id))
        assert len(result.factors) > 0
        # Sorted by impact score (avg severity), highest first
        if len(result.factors) > 1:
            assert result.factors[0].impact_score >= result.factors[1].impact_score

    async def test_tenant_isolation(self, db: AsyncSession, analytics_data, session_factory):
        """Analytics only shows data from the requesting company."""
        other_cid = uuid.uuid4()
        async with session_factory() as session:
            session.add(Company(id=other_cid, name="Other", slug=f"other-{uuid.uuid4().hex[:6]}"))
            await session.commit()
        svc = AnalyticsService()
        result = await svc.risk_by_category(db, str(other_cid))
        assert result.data_points == 0
