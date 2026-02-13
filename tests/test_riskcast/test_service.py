"""Tests for RISKCAST Service.

Tests the high-level service API:
1. Process signal for all customers (broadcast)
2. Process signal for one customer (targeted)
3. Decision retrieval
4. Feedback tracking
"""

from datetime import datetime, timedelta

import pytest

from app.oracle.schemas import CorrelatedIntelligence
from app.riskcast.repos.customer import InMemoryCustomerRepository
from app.riskcast.schemas.customer import CustomerContext, CustomerProfile, Shipment
from app.riskcast.service import (
    InMemoryDecisionStore,
    RiskCastService,
    create_riskcast_service,
    get_riskcast_service,
)


class TestInMemoryDecisionStore:
    """Tests for the in-memory decision store."""

    @pytest.fixture
    def store(self) -> InMemoryDecisionStore:
        """Create fresh store."""
        return InMemoryDecisionStore()

    @pytest.fixture
    def sample_decision(
        self,
        confirmed_intelligence,
        sample_customer_context,
    ):
        """Create a sample decision for testing."""
        from app.riskcast.composers.decision import create_decision_composer
        composer = create_decision_composer()
        return composer.compose(confirmed_intelligence, sample_customer_context)

    def test_save_and_get(
        self,
        store: InMemoryDecisionStore,
        sample_decision,
    ):
        """Should save and retrieve decisions."""
        store.save(sample_decision)

        retrieved = store.get(sample_decision.decision_id)

        assert retrieved is not None
        assert retrieved.decision_id == sample_decision.decision_id
        assert retrieved.customer_id == sample_decision.customer_id

    def test_get_nonexistent_returns_none(
        self,
        store: InMemoryDecisionStore,
    ):
        """Should return None for nonexistent decision."""
        result = store.get("nonexistent_id")
        assert result is None

    def test_get_by_customer(
        self,
        store: InMemoryDecisionStore,
        sample_decision,
    ):
        """Should retrieve decisions by customer."""
        store.save(sample_decision)

        decisions = store.get_by_customer(sample_decision.customer_id)

        assert len(decisions) == 1
        assert decisions[0].decision_id == sample_decision.decision_id

    def test_get_by_signal(
        self,
        store: InMemoryDecisionStore,
        sample_decision,
    ):
        """Should retrieve decisions by signal."""
        store.save(sample_decision)

        decisions = store.get_by_signal(sample_decision.signal_id)

        assert len(decisions) == 1
        assert decisions[0].decision_id == sample_decision.decision_id

    def test_update_decision(
        self,
        store: InMemoryDecisionStore,
        sample_decision,
    ):
        """Should update decision tracking fields."""
        store.save(sample_decision)

        updated = store.update(
            sample_decision.decision_id,
            was_acted_upon=True,
            user_feedback="Good recommendation",
        )

        assert updated is not None
        assert updated.was_acted_upon is True
        assert updated.user_feedback == "Good recommendation"

    def test_filter_expired(
        self,
        store: InMemoryDecisionStore,
        sample_decision,
    ):
        """Should filter expired decisions by default."""
        # Create an expired decision
        from app.riskcast.schemas.decision import (
            DecisionObject,
            Q1WhatIsHappening,
            Q2WhenWillItHappen,
            Q3HowBadIsIt,
            Q4WhyIsThisHappening,
            Q5WhatToDoNow,
            Q6HowConfident,
            Q7WhatIfNothing,
        )
        from app.riskcast.constants import ConfidenceLevel, Severity, Urgency

        expired = DecisionObject(
            decision_id="dec_expired",
            customer_id=sample_decision.customer_id,
            signal_id="sig_old",
            q1_what=Q1WhatIsHappening(
                event_type="TEST",
                event_summary="Expired test",
                affected_chokepoint="red_sea",
                affected_routes=[],
                affected_shipments=[],
            ),
            q2_when=Q2WhenWillItHappen(
                status="PAST",
                impact_timeline="Past",
                urgency=Urgency.WATCH,
                urgency_reason="Expired",
            ),
            q3_severity=Q3HowBadIsIt(
                total_exposure_usd=0,
                exposure_breakdown={},
                expected_delay_days=0,
                delay_range="0",
                shipments_affected=0,
                shipments_with_penalties=0,
                severity=Severity.LOW,
            ),
            q4_why=Q4WhyIsThisHappening(
                root_cause="Test",
                causal_chain=["Test cause"],
                evidence_summary="Test",
                sources=[],
            ),
            q5_action=Q5WhatToDoNow(
                action_type="MONITOR",
                action_summary="Test",
                affected_shipments=[],
                estimated_cost_usd=0,
                execution_steps=[],
                deadline=datetime.utcnow(),
                deadline_reason="Test",
            ),
            q6_confidence=Q6HowConfident(
                score=0.5,
                level=ConfidenceLevel.MEDIUM,
                factors={},
                explanation="Test",
                caveats=[],
            ),
            q7_inaction=Q7WhatIfNothing(
                expected_loss_if_nothing=0,
                cost_if_wait_6h=0,
                cost_if_wait_24h=0,
                cost_if_wait_48h=0,
                worst_case_cost=0,
                worst_case_scenario="Test",
                inaction_summary="Test",
            ),
            expires_at=datetime.utcnow() - timedelta(hours=1),  # Expired
        )

        store.save(sample_decision)  # Not expired
        store.save(expired)  # Expired

        # Default should exclude expired
        decisions = store.get_by_customer(sample_decision.customer_id)
        assert len(decisions) == 1
        assert decisions[0].decision_id == sample_decision.decision_id

        # With flag should include expired
        all_decisions = store.get_by_customer(
            sample_decision.customer_id, include_expired=True
        )
        assert len(all_decisions) == 2


class TestRiskCastService:
    """Tests for the main RISKCAST service."""

    @pytest.fixture
    def populated_repository(
        self,
        sample_customer_profile,
        sample_shipment,
        high_value_shipment,
    ) -> InMemoryCustomerRepository:
        """Create repository with sample data."""
        repo = InMemoryCustomerRepository()
        repo._profiles[sample_customer_profile.customer_id] = sample_customer_profile
        repo._customer_shipments[sample_customer_profile.customer_id] = set()
        # Store shipments by ID and index them
        repo._shipments[sample_shipment.shipment_id] = sample_shipment
        repo._shipments[high_value_shipment.shipment_id] = high_value_shipment
        repo._customer_shipments[sample_customer_profile.customer_id].add(sample_shipment.shipment_id)
        repo._customer_shipments[sample_customer_profile.customer_id].add(high_value_shipment.shipment_id)
        return repo

    @pytest.fixture
    def service(
        self,
        populated_repository: InMemoryCustomerRepository,
    ) -> RiskCastService:
        """Create service with populated repository."""
        return create_riskcast_service(
            customer_repository=populated_repository,
        )

    def test_process_signal_for_customer(
        self,
        service: RiskCastService,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_profile: CustomerProfile,
    ):
        """Should generate decision for specific customer."""
        decision = service.process_signal_for_customer(
            confirmed_intelligence,
            sample_customer_profile.customer_id,
        )

        assert decision is not None
        assert decision.customer_id == sample_customer_profile.customer_id
        assert decision.signal_id == confirmed_intelligence.signal.signal_id

    def test_process_signal_for_nonexistent_customer(
        self,
        service: RiskCastService,
        confirmed_intelligence: CorrelatedIntelligence,
    ):
        """Should return None for nonexistent customer."""
        decision = service.process_signal_for_customer(
            confirmed_intelligence,
            "nonexistent_customer",
        )

        assert decision is None

    def test_process_signal_broadcast(
        self,
        service: RiskCastService,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_profile: CustomerProfile,
    ):
        """Should generate decisions for all affected customers."""
        decisions = service.process_signal(confirmed_intelligence)

        # Should have at least one decision (for our sample customer)
        assert len(decisions) >= 1

    def test_get_decision(
        self,
        service: RiskCastService,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_profile: CustomerProfile,
    ):
        """Should retrieve saved decisions."""
        # First create a decision
        decision = service.process_signal_for_customer(
            confirmed_intelligence,
            sample_customer_profile.customer_id,
        )

        # Then retrieve it
        retrieved = service.get_decision(decision.decision_id)

        assert retrieved is not None
        assert retrieved.decision_id == decision.decision_id

    def test_get_decisions_for_customer(
        self,
        service: RiskCastService,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_profile: CustomerProfile,
    ):
        """Should retrieve all decisions for a customer."""
        # Create a decision
        service.process_signal_for_customer(
            confirmed_intelligence,
            sample_customer_profile.customer_id,
        )

        # Get all decisions for customer
        decisions = service.get_decisions_for_customer(
            sample_customer_profile.customer_id
        )

        assert len(decisions) >= 1

    def test_record_action_taken(
        self,
        service: RiskCastService,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_profile: CustomerProfile,
    ):
        """Should record when customer takes action."""
        decision = service.process_signal_for_customer(
            confirmed_intelligence,
            sample_customer_profile.customer_id,
        )

        updated = service.record_action_taken(decision.decision_id)

        assert updated is not None
        assert updated.was_acted_upon is True

    def test_record_feedback(
        self,
        service: RiskCastService,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_profile: CustomerProfile,
    ):
        """Should record user feedback."""
        decision = service.process_signal_for_customer(
            confirmed_intelligence,
            sample_customer_profile.customer_id,
        )

        updated = service.record_feedback(
            decision.decision_id,
            "Great recommendation, saved us money!",
        )

        assert updated is not None
        assert "Great recommendation" in updated.user_feedback

    def test_get_active_decisions(
        self,
        service: RiskCastService,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_profile: CustomerProfile,
    ):
        """Should retrieve only non-expired decisions."""
        service.process_signal_for_customer(
            confirmed_intelligence,
            sample_customer_profile.customer_id,
        )

        active = service.get_active_decisions()

        # All returned should be active
        for decision in active:
            assert not decision.is_expired

    def test_get_summary(
        self,
        service: RiskCastService,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_profile: CustomerProfile,
    ):
        """Should provide summary statistics."""
        service.process_signal_for_customer(
            confirmed_intelligence,
            sample_customer_profile.customer_id,
        )

        summary = service.get_summary()

        assert "total_decisions" in summary
        assert "active_decisions" in summary
        assert "by_severity" in summary
        assert "by_urgency" in summary
        assert "total_exposure_usd" in summary


class TestRiskCastServiceFactory:
    """Tests for factory functions."""

    def test_create_riskcast_service(self):
        """Factory should create valid instance."""
        service = create_riskcast_service()
        assert isinstance(service, RiskCastService)

    def test_get_riskcast_service_singleton(self):
        """Should return same instance."""
        service1 = get_riskcast_service()
        service2 = get_riskcast_service()

        # Should be the same instance
        assert service1 is service2


class TestEndToEndFlow:
    """End-to-end integration tests."""

    @pytest.fixture
    def full_service(
        self,
        sample_customer_profile,
        sample_shipment,
        high_value_shipment,
        in_transit_shipment,
    ) -> RiskCastService:
        """Create service with diverse shipments."""
        repo = InMemoryCustomerRepository()
        repo._profiles[sample_customer_profile.customer_id] = sample_customer_profile
        repo._customer_shipments[sample_customer_profile.customer_id] = set()
        # Store and index shipments
        for shipment in [sample_shipment, high_value_shipment, in_transit_shipment]:
            repo._shipments[shipment.shipment_id] = shipment
            repo._customer_shipments[sample_customer_profile.customer_id].add(shipment.shipment_id)
        return create_riskcast_service(customer_repository=repo)

    def test_full_decision_flow(
        self,
        full_service: RiskCastService,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_profile: CustomerProfile,
    ):
        """Test complete flow from signal to decision to feedback."""
        # 1. Process signal
        decision = full_service.process_signal_for_customer(
            confirmed_intelligence,
            sample_customer_profile.customer_id,
        )
        assert decision is not None

        # 2. Verify all questions answered
        assert decision.q1_what is not None
        assert decision.q2_when is not None
        assert decision.q3_severity is not None
        assert decision.q4_why is not None
        assert decision.q5_action is not None
        assert decision.q6_confidence is not None
        assert decision.q7_inaction is not None

        # 3. Retrieve decision
        retrieved = full_service.get_decision(decision.decision_id)
        assert retrieved is not None

        # 4. Record action
        full_service.record_action_taken(decision.decision_id)

        # 5. Record feedback
        full_service.record_feedback(
            decision.decision_id,
            "Followed the recommendation to reroute. Worked well.",
        )

        # 6. Check final state
        final = full_service.get_decision(decision.decision_id)
        assert final.was_acted_upon is True
        assert final.user_feedback is not None

        # 7. Check summary
        summary = full_service.get_summary()
        assert summary["total_decisions"] >= 1
        assert summary["acted_upon"] >= 1
