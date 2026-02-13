"""
Unified Risk Engine Integration Tests.

Tests the full pipeline: signals → temporal → correlation → fusion → bayesian → ensemble → decomposition.
"""

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.models import Company, Order, Route, Signal
from riskcast.engine.risk_engine import RiskEngine


@pytest_asyncio.fixture
async def engine_company(session_factory) -> Company:
    async with session_factory() as session:
        company = Company(
            id=uuid.uuid4(),
            name="Engine Test Co",
            slug=f"engine-{uuid.uuid4().hex[:8]}",
        )
        session.add(company)
        await session.commit()
        await session.refresh(company)
        return company


@pytest_asyncio.fixture
async def entity_with_signals(session_factory, engine_company) -> tuple:
    """Create an order with multiple signals for testing."""
    cid = engine_company.id
    order_id = uuid.uuid4()
    route_id = uuid.uuid4()

    async with session_factory() as session:
        session.add(Route(
            id=route_id, company_id=cid,
            name="Test Route", origin="A", destination="B",
        ))
        session.add(Order(
            id=order_id, company_id=cid,
            order_number="ORD-ENGINE-1", status="pending",
            route_id=route_id, total_value=Decimal("500000"),
        ))

        # Multiple signals for this order
        session.add(Signal(
            company_id=cid, source="internal_1",
            signal_type="payment_risk", entity_type="order",
            entity_id=order_id, confidence=Decimal("0.85"),
            severity_score=Decimal("72"), evidence={"test": True},
            is_active=True,
        ))
        session.add(Signal(
            company_id=cid, source="internal_2",
            signal_type="route_disruption", entity_type="order",
            entity_id=order_id, confidence=Decimal("0.70"),
            severity_score=Decimal("55"), evidence={"test": True},
            is_active=True,
        ))
        session.add(Signal(
            company_id=cid, source="internal_3",
            signal_type="order_risk_composite", entity_type="order",
            entity_id=order_id, confidence=Decimal("0.60"),
            severity_score=Decimal("48"), evidence={"test": True},
            is_active=True,
        ))
        await session.commit()

    return engine_company, order_id, route_id


@pytest.mark.asyncio
class TestRiskEngineIntegration:
    """Test the unified risk engine end-to-end."""

    async def test_assess_empty_entity(self, db: AsyncSession, engine_company):
        """Entity with no signals → valid empty assessment."""
        engine = RiskEngine()
        result = await engine.assess_order(db, str(engine_company.id), str(uuid.uuid4()))
        assert result.risk_score == 0.0
        assert result.confidence == 0.0
        assert not result.is_reliable
        assert result.n_signals == 0
        assert "No signals" in result.summary

    async def test_assess_order_with_signals(self, db: AsyncSession, entity_with_signals):
        """Order with signals → full assessment with factors."""
        company, order_id, _ = entity_with_signals
        engine = RiskEngine()
        result = await engine.assess_order(db, str(company.id), str(order_id))

        assert result.risk_score > 0
        assert result.confidence > 0
        assert result.n_signals == 3
        assert result.n_active_signals >= 1
        assert len(result.factors) > 0
        assert result.severity_label in ("low", "moderate", "high", "critical")
        assert result.generated_at != ""

    async def test_algorithm_trace_present(self, db: AsyncSession, entity_with_signals):
        """Assessment includes algorithm trace for auditability."""
        company, order_id, _ = entity_with_signals
        engine = RiskEngine()
        result = await engine.assess_order(db, str(company.id), str(order_id))

        assert "fusion_score" in result.algorithm_trace
        assert "bayesian_probability" in result.algorithm_trace
        assert "ensemble_disagreement" in result.algorithm_trace
        assert "temporal_freshness" in result.algorithm_trace

    async def test_ci_bounds_valid(self, db: AsyncSession, entity_with_signals):
        """CI lower <= score <= CI upper."""
        company, order_id, _ = entity_with_signals
        engine = RiskEngine()
        result = await engine.assess_order(db, str(company.id), str(order_id))
        assert result.ci_lower <= result.risk_score <= result.ci_upper

    async def test_factors_have_explanations(self, db: AsyncSession, entity_with_signals):
        """Every factor has an explanation and recommendation."""
        company, order_id, _ = entity_with_signals
        engine = RiskEngine()
        result = await engine.assess_order(db, str(company.id), str(order_id))
        for factor in result.factors:
            assert "explanation" in factor
            assert "recommendation" in factor
            assert len(factor["explanation"]) > 0

    async def test_primary_driver_present(self, db: AsyncSession, entity_with_signals):
        """Primary driver is identified."""
        company, order_id, _ = entity_with_signals
        engine = RiskEngine()
        result = await engine.assess_order(db, str(company.id), str(order_id))
        assert result.primary_driver != "none"

    async def test_assess_customer(self, db: AsyncSession, engine_company):
        """Customer assessment works (empty case)."""
        engine = RiskEngine()
        result = await engine.assess_customer(db, str(engine_company.id), str(uuid.uuid4()))
        assert result.entity_type == "customer"
        assert result.risk_score == 0.0

    async def test_assess_route(self, db: AsyncSession, engine_company):
        """Route assessment works (empty case)."""
        engine = RiskEngine()
        result = await engine.assess_route(db, str(engine_company.id), str(uuid.uuid4()))
        assert result.entity_type == "route"
        assert result.risk_score == 0.0
