"""
Empty State Tests — Verify graceful handling when database is empty.

Every service must return valid responses (not crash) with empty data.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.models import Company
from riskcast.services.dashboard_service import DashboardService
from riskcast.services.analytics_service import AnalyticsService


@pytest_asyncio.fixture
async def empty_company(session_factory) -> Company:
    """Create a company with zero data."""
    async with session_factory() as session:
        company = Company(
            id=uuid.uuid4(),
            name="Empty Co",
            slug=f"empty-{uuid.uuid4().hex[:8]}",
        )
        session.add(company)
        await session.commit()
        await session.refresh(company)
        return company


@pytest.mark.asyncio
class TestEmptyStates:
    """All services must handle empty databases gracefully."""

    async def test_dashboard_empty(self, db: AsyncSession, empty_company):
        svc = DashboardService()
        result = await svc.get_summary(db, str(empty_company.id))
        assert result.total_orders == 0
        assert result.active_signals == 0
        assert result.total_revenue == 0.0
        assert result.data_freshness.staleness_level == "no_data"
        assert result.message is not None

    async def test_risk_over_time_empty(self, db: AsyncSession, empty_company):
        svc = AnalyticsService()
        result = await svc.risk_over_time(db, str(empty_company.id))
        assert result.data_points == 0
        assert result.data_sufficiency == "insufficient"

    async def test_risk_by_category_empty(self, db: AsyncSession, empty_company):
        svc = AnalyticsService()
        result = await svc.risk_by_category(db, str(empty_company.id))
        assert len(result.categories) == 0

    async def test_risk_by_route_empty(self, db: AsyncSession, empty_company):
        svc = AnalyticsService()
        result = await svc.risk_by_route(db, str(empty_company.id))
        assert len(result.routes) == 0

    async def test_top_risk_factors_empty(self, db: AsyncSession, empty_company):
        svc = AnalyticsService()
        result = await svc.top_risk_factors(db, str(empty_company.id))
        assert len(result.factors) == 0

    async def test_nonexistent_company(self, db: AsyncSession):
        """Querying a nonexistent company returns empty results (not an error)."""
        fake_cid = str(uuid.uuid4())
        svc = DashboardService()
        result = await svc.get_summary(db, fake_cid)
        assert result.total_orders == 0

    async def test_dashboard_trends_all_zeros(self, db: AsyncSession, empty_company):
        """Trends return padded zeros, not empty arrays."""
        svc = DashboardService()
        result = await svc.get_summary(db, str(empty_company.id), period_days=7)
        assert len(result.signal_trend) == 7
        assert all(p.count == 0 for p in result.signal_trend)
        assert len(result.order_trend) == 7
        assert all(p.count == 0 for p in result.order_trend)
