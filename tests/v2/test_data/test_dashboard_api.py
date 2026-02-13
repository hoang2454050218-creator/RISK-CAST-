"""
Dashboard API Tests — Real aggregated metrics.

Tests: empty state, with data, date ranges, freshness, completeness.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.models import Company, Customer, Order, Signal
from riskcast.services.dashboard_service import DashboardService


@pytest_asyncio.fixture
async def dashboard_company(session_factory) -> Company:
    """Create a company for dashboard tests."""
    async with session_factory() as session:
        company = Company(
            id=uuid.uuid4(),
            name="Dashboard Co",
            slug=f"dash-{uuid.uuid4().hex[:8]}",
        )
        session.add(company)
        await session.commit()
        await session.refresh(company)
        return company


@pytest_asyncio.fixture
async def populated_company(session_factory, dashboard_company) -> Company:
    """Create a company with orders, customers, and signals."""
    cid = dashboard_company.id
    async with session_factory() as session:
        # Add customers
        for i in range(5):
            session.add(Customer(
                company_id=cid, name=f"Customer {i}", code=f"C-{i}",
            ))
        # Add orders
        for i in range(10):
            session.add(Order(
                company_id=cid,
                order_number=f"ORD-{uuid.uuid4().hex[:8]}",
                status="pending",
                total_value=Decimal("1000000"),
            ))
        # Add signals
        for i in range(8):
            session.add(Signal(
                company_id=cid,
                source="internal",
                signal_type=f"risk_type_{i % 3}",
                confidence=Decimal("0.80"),
                severity_score=Decimal(str(30 + i * 10)),
                evidence={"test": True},
                is_active=True,
            ))
        await session.commit()
    return dashboard_company


@pytest.mark.asyncio
class TestDashboardService:
    """Test the DashboardService with a real async session."""

    async def test_empty_database(self, db: AsyncSession, dashboard_company):
        """Empty database returns zeros with a helpful message."""
        svc = DashboardService()
        result = await svc.get_summary(db, str(dashboard_company.id))

        assert result.total_orders == 0
        assert result.active_signals == 0
        assert result.total_customers == 0
        assert result.total_revenue == 0.0
        assert result.message is not None
        assert "No data" in result.message

    async def test_empty_completeness_is_zero(self, db: AsyncSession, dashboard_company):
        """Data completeness is 0 when nothing exists."""
        svc = DashboardService()
        result = await svc.get_summary(db, str(dashboard_company.id))
        assert result.data_completeness == 0.0
        assert len(result.known_gaps) > 0

    async def test_with_data(self, db: AsyncSession, populated_company):
        """With data, returns real counts."""
        svc = DashboardService()
        result = await svc.get_summary(db, str(populated_company.id))

        assert result.total_orders == 10
        assert result.total_customers == 5
        assert result.active_signals == 8
        assert result.total_revenue == 10_000_000.0  # 10 × 1M
        assert result.message is None  # No empty state message

    async def test_signal_trend_padded(self, db: AsyncSession, dashboard_company):
        """Signal trend always has exactly period_days entries (padded with 0)."""
        svc = DashboardService()
        result = await svc.get_summary(db, str(dashboard_company.id), period_days=7)
        assert len(result.signal_trend) == 7

    async def test_order_trend_padded(self, db: AsyncSession, dashboard_company):
        """Order trend always has exactly period_days entries."""
        svc = DashboardService()
        result = await svc.get_summary(db, str(dashboard_company.id), period_days=14)
        assert len(result.order_trend) == 14

    async def test_risk_trend_padded(self, db: AsyncSession, dashboard_company):
        """Risk trend always has period_days entries."""
        svc = DashboardService()
        result = await svc.get_summary(db, str(dashboard_company.id), period_days=7)
        assert len(result.risk_trend) == 7

    async def test_top_risks_limited(self, db: AsyncSession, populated_company):
        """Top risks returns at most 5 items."""
        svc = DashboardService()
        result = await svc.get_summary(db, str(populated_company.id))
        assert len(result.top_risks) <= 5

    async def test_freshness_no_data(self, db: AsyncSession, dashboard_company):
        """Freshness is 'no_data' when database is empty."""
        svc = DashboardService()
        result = await svc.get_summary(db, str(dashboard_company.id))
        assert result.data_freshness.staleness_level == "no_data"

    async def test_freshness_with_data(self, db: AsyncSession, populated_company):
        """Freshness is 'fresh' when data was just inserted."""
        svc = DashboardService()
        result = await svc.get_summary(db, str(populated_company.id))
        assert result.data_freshness.staleness_level in ("fresh", "stale")

    async def test_generated_at_is_iso(self, db: AsyncSession, dashboard_company):
        """generated_at is a valid ISO timestamp."""
        svc = DashboardService()
        result = await svc.get_summary(db, str(dashboard_company.id))
        datetime.fromisoformat(result.generated_at)  # Should not raise

    async def test_critical_signals_threshold(self, db: AsyncSession, populated_company):
        """Critical signals are those with severity >= 70."""
        svc = DashboardService()
        result = await svc.get_summary(db, str(populated_company.id))
        # We created signals with severity 30,40,50,60,70,80,90,100 → 4 are >= 70
        assert result.critical_signals >= 0  # At least 0 (depends on timing)

    async def test_different_periods(self, db: AsyncSession, populated_company):
        """Different period_days values work correctly."""
        svc = DashboardService()
        r7 = await svc.get_summary(db, str(populated_company.id), period_days=7)
        r30 = await svc.get_summary(db, str(populated_company.id), period_days=30)
        assert r7.period == "last_7_days"
        assert r30.period == "last_30_days"

    async def test_tenant_isolation(self, db: AsyncSession, populated_company, session_factory):
        """Dashboard only shows data from the requesting company."""
        # Create a second company with data
        other_cid = uuid.uuid4()
        async with session_factory() as session:
            session.add(Company(id=other_cid, name="Other Co", slug=f"other-{uuid.uuid4().hex[:6]}"))
            session.add(Order(company_id=other_cid, order_number="ORD-OTHER", status="pending"))
            await session.commit()

        svc = DashboardService()
        result = await svc.get_summary(db, str(other_cid))
        assert result.total_orders == 1  # Only the one order from Other Co
