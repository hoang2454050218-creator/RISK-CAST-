"""Tests for Decision Schemas (Q1-Q7).

Tests the final output format of RISKCAST:
- Q1: What is happening?
- Q2: When?
- Q3: How bad?
- Q4: Why?
- Q5: What to do?
- Q6: How confident?
- Q7: What if nothing?
"""

from datetime import datetime, timedelta

import pytest

from app.riskcast.constants import ConfidenceLevel, Severity, Urgency
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


class TestQ1WhatIsHappening:
    """Tests for Q1: What is happening?"""

    def test_personalized_summary(self):
        """Q1 must include customer-specific information."""
        q1 = Q1WhatIsHappening(
            event_type="DISRUPTION",
            event_summary="Red Sea disruption affecting YOUR Shanghai-Rotterdam route",
            affected_chokepoint="red_sea",
            affected_routes=["CNSHA-NLRTM", "VNHCM-NLRTM"],
            affected_shipments=["PO-4521", "PO-4522"],
        )

        assert "YOUR" in q1.event_summary or "Shanghai" in q1.event_summary
        assert q1.shipment_count == 2
        assert len(q1.affected_routes) == 2

    def test_shipment_count_computed(self):
        """Shipment count should be computed from list."""
        q1 = Q1WhatIsHappening(
            event_type="CONGESTION",
            event_summary="Port congestion at Singapore",
            affected_chokepoint="malacca",
            affected_routes=["VNHCM-NLRTM"],
            affected_shipments=["PO-001", "PO-002", "PO-003"],
        )

        assert q1.shipment_count == 3


class TestQ2WhenWillItHappen:
    """Tests for Q2: When will it happen?"""

    def test_timeline_specific(self):
        """Q2 must include specific timeline."""
        earliest = datetime.utcnow() + timedelta(days=3)
        q2 = Q2WhenWillItHappen(
            status="CONFIRMED",
            impact_timeline="Impact starts in 3 days for your earliest shipment",
            earliest_impact=earliest,
            latest_resolution=datetime.utcnow() + timedelta(days=30),
            urgency=Urgency.URGENT,
            urgency_reason="Key window closing - decide today",
        )

        assert "3 days" in q2.impact_timeline
        assert q2.urgency == Urgency.URGENT

    def test_days_until_impact_computed(self):
        """Days until impact should be computed."""
        earliest = datetime.utcnow() + timedelta(days=5)
        q2 = Q2WhenWillItHappen(
            status="PREDICTED",
            impact_timeline="Impact in 5 days",
            earliest_impact=earliest,
            urgency=Urgency.SOON,
            urgency_reason="Time available",
        )

        # Should be approximately 5 (allow some variance for test timing)
        assert 4 <= q2.days_until_impact <= 6

    def test_days_until_impact_none_when_no_earliest(self):
        """Days until impact should be None when no earliest_impact."""
        q2 = Q2WhenWillItHappen(
            status="PREDICTED",
            impact_timeline="Impact timing unclear",
            urgency=Urgency.WATCH,
            urgency_reason="Monitor situation",
        )

        assert q2.days_until_impact is None


class TestQ3HowBadIsIt:
    """Tests for Q3: How severe is this?"""

    def test_specific_dollar_amounts(self):
        """Q3 must include specific dollar amounts."""
        q3 = Q3HowBadIsIt(
            total_exposure_usd=235000,
            exposure_breakdown={
                "cargo_at_risk": 200000,
                "potential_penalties": 35000,
            },
            expected_delay_days=12,
            delay_range="10-14 days",
            shipments_affected=3,
            shipments_with_penalties=2,
            severity=Severity.HIGH,
        )

        assert q3.total_exposure_usd == 235000
        assert q3.exposure_str == "$235,000"
        assert q3.severity == Severity.HIGH

    def test_has_penalty_risk_computed(self):
        """Has penalty risk should be computed from shipment count."""
        q3_with_penalty = Q3HowBadIsIt(
            total_exposure_usd=50000,
            exposure_breakdown={},
            expected_delay_days=7,
            delay_range="7 days",
            shipments_affected=2,
            shipments_with_penalties=1,
            severity=Severity.MEDIUM,
        )
        assert q3_with_penalty.has_penalty_risk is True

        q3_without_penalty = Q3HowBadIsIt(
            total_exposure_usd=50000,
            exposure_breakdown={},
            expected_delay_days=7,
            delay_range="7 days",
            shipments_affected=2,
            shipments_with_penalties=0,
            severity=Severity.MEDIUM,
        )
        assert q3_without_penalty.has_penalty_risk is False


class TestQ4WhyIsThisHappening:
    """Tests for Q4: Why is this happening?"""

    def test_causal_chain_readable(self):
        """Q4 must include understandable causal chain."""
        q4 = Q4WhyIsThisHappening(
            root_cause="Houthi attacks on commercial vessels",
            causal_chain=[
                "Houthi forces attack ships",
                "Carriers avoid Red Sea",
                "Ships reroute via Cape",
                "Extended transit times",
            ],
            evidence_summary="78% signal probability | 87% combined confidence",
            sources=["Polymarket", "MarineTraffic", "OMEN"],
        )

        assert len(q4.causal_chain) == 4
        assert "→" in q4.chain_str
        assert "Houthi" in q4.root_cause

    def test_chain_str_format(self):
        """Chain string should join with arrows."""
        q4 = Q4WhyIsThisHappening(
            root_cause="Port congestion",
            causal_chain=["Congestion", "Delays", "Rate increases"],
            evidence_summary="Evidence",
            sources=["OMEN"],
        )

        assert q4.chain_str == "Congestion → Delays → Rate increases"


class TestQ5WhatToDoNow:
    """Tests for Q5: What should I do RIGHT NOW?"""

    def test_specific_action_with_deadline(self):
        """Q5 must include specific action with deadline."""
        deadline = datetime.utcnow() + timedelta(hours=6)
        q5 = Q5WhatToDoNow(
            action_type="REROUTE",
            action_summary="Reroute 3 shipments via Cape with MSC",
            affected_shipments=["PO-4521", "PO-4522", "PO-4523"],
            recommended_carrier="MSCU",
            estimated_cost_usd=8500,
            execution_steps=[
                "Contact MSC booking desk",
                "Request Cape routing",
                "Confirm by 6PM today",
            ],
            deadline=deadline,
            deadline_reason="Booking window closes",
            who_to_contact="MSC Mediterranean Shipping",
            contact_info="+1-800-555-1234",
        )

        assert q5.action_type == "REROUTE"
        assert q5.cost_str == "$8,500"
        assert len(q5.execution_steps) == 3
        assert q5.deadline is not None

    def test_hours_until_deadline_computed(self):
        """Hours until deadline should be computed."""
        deadline = datetime.utcnow() + timedelta(hours=12)
        q5 = Q5WhatToDoNow(
            action_type="MONITOR",
            action_summary="Monitor for 12 hours",
            affected_shipments=["PO-001"],
            estimated_cost_usd=0,
            execution_steps=["Watch situation"],
            deadline=deadline,
            deadline_reason="Re-evaluate then",
        )

        # Should be approximately 12 hours
        assert 11 <= q5.hours_until_deadline <= 13


class TestQ6HowConfident:
    """Tests for Q6: How confident are we?"""

    def test_confidence_with_factors(self):
        """Q6 must include factors explaining confidence."""
        q6 = Q6HowConfident(
            score=0.87,
            level=ConfidenceLevel.HIGH,
            factors={
                "signal_probability": 0.78,
                "intelligence_correlation": 0.90,
                "impact_assessment": 0.85,
            },
            explanation="87% confidence, high signal probability, strong correlation",
            caveats=["Situation evolving"],
        )

        assert q6.score == 0.87
        assert q6.level == ConfidenceLevel.HIGH
        assert len(q6.factors) >= 1
        assert q6.score_pct == "87%"

    def test_is_actionable_computed(self):
        """Is actionable should be True if confidence >= 0.6."""
        high_conf = Q6HowConfident(
            score=0.75,
            level=ConfidenceLevel.HIGH,
            factors={},
            explanation="High confidence",
            caveats=[],
        )
        assert high_conf.is_actionable is True

        low_conf = Q6HowConfident(
            score=0.45,
            level=ConfidenceLevel.LOW,
            factors={},
            explanation="Low confidence",
            caveats=["Many uncertainties"],
        )
        assert low_conf.is_actionable is False


class TestQ7WhatIfNothing:
    """Tests for Q7: What happens if I don't act?"""

    def test_time_based_cost_escalation(self):
        """Q7 must include time-based cost projections."""
        ponr = datetime.utcnow() + timedelta(hours=24)
        q7 = Q7WhatIfNothing(
            expected_loss_if_nothing=47000,
            cost_if_wait_6h=51700,
            cost_if_wait_24h=61100,
            cost_if_wait_48h=70500,
            point_of_no_return=ponr,
            point_of_no_return_reason="Reroute option closes",
            worst_case_cost=94000,
            worst_case_scenario="All shipments trigger penalties, 28+ day delay",
            inaction_summary="Point of no return in 24h. Expected loss: $47,000",
        )

        assert q7.expected_loss_if_nothing == 47000
        assert q7.cost_if_wait_6h > q7.expected_loss_if_nothing
        assert q7.cost_if_wait_24h > q7.cost_if_wait_6h

    def test_cost_escalation_computed(self):
        """Cost escalation percentages should be computed."""
        q7 = Q7WhatIfNothing(
            expected_loss_if_nothing=10000,
            cost_if_wait_6h=11000,
            cost_if_wait_24h=13000,
            cost_if_wait_48h=15000,
            worst_case_cost=20000,
            worst_case_scenario="Worst case",
            inaction_summary="Summary",
        )

        assert q7.cost_escalation_6h == 10.0  # 10% increase
        assert q7.cost_escalation_24h == 30.0  # 30% increase

    def test_hours_until_no_return_computed(self):
        """Hours until PONR should be computed."""
        ponr = datetime.utcnow() + timedelta(hours=36)
        q7 = Q7WhatIfNothing(
            expected_loss_if_nothing=50000,
            cost_if_wait_6h=55000,
            cost_if_wait_24h=65000,
            cost_if_wait_48h=75000,
            point_of_no_return=ponr,
            point_of_no_return_reason="Options close",
            worst_case_cost=100000,
            worst_case_scenario="Worst case",
            inaction_summary="Summary",
        )

        # Should be approximately 36 hours
        assert 35 <= q7.hours_until_no_return <= 37


class TestDecisionObject:
    """Tests for DecisionObject - the complete output."""

    @pytest.fixture
    def sample_decision(self) -> DecisionObject:
        """Create a sample complete decision."""
        now = datetime.utcnow()
        expires = now + timedelta(hours=24)
        deadline = now + timedelta(hours=6)
        ponr = now + timedelta(hours=18)
        earliest = now + timedelta(days=3)

        return DecisionObject(
            decision_id="dec_20240205143022_cust_abc",
            customer_id="cust_abc123",
            signal_id="OMEN-RS-2024-001",
            q1_what=Q1WhatIsHappening(
                event_type="DISRUPTION",
                event_summary="Red Sea disruption affecting your route",
                affected_chokepoint="red_sea",
                affected_routes=["VNHCM-NLRTM"],
                affected_shipments=["PO-4521"],
            ),
            q2_when=Q2WhenWillItHappen(
                status="CONFIRMED",
                impact_timeline="Impact in 3 days",
                earliest_impact=earliest,
                urgency=Urgency.URGENT,
                urgency_reason="Decide today",
            ),
            q3_severity=Q3HowBadIsIt(
                total_exposure_usd=235000,
                exposure_breakdown={"cargo": 235000},
                expected_delay_days=12,
                delay_range="10-14 days",
                shipments_affected=1,
                shipments_with_penalties=1,
                severity=Severity.HIGH,
            ),
            q4_why=Q4WhyIsThisHappening(
                root_cause="Houthi attacks",
                causal_chain=["Attack", "Reroute", "Delay"],
                evidence_summary="87% confidence",
                sources=["OMEN"],
            ),
            q5_action=Q5WhatToDoNow(
                action_type="REROUTE",
                action_summary="Reroute via Cape",
                affected_shipments=["PO-4521"],
                recommended_carrier="MSCU",
                estimated_cost_usd=8500,
                execution_steps=["Contact MSC", "Book"],
                deadline=deadline,
                deadline_reason="Booking closes",
            ),
            q6_confidence=Q6HowConfident(
                score=0.87,
                level=ConfidenceLevel.HIGH,
                factors={"signal": 0.78},
                explanation="High confidence",
                caveats=[],
            ),
            q7_inaction=Q7WhatIfNothing(
                expected_loss_if_nothing=47000,
                cost_if_wait_6h=51700,
                cost_if_wait_24h=61100,
                cost_if_wait_48h=70500,
                point_of_no_return=ponr,
                point_of_no_return_reason="Options close",
                worst_case_cost=94000,
                worst_case_scenario="All penalties trigger",
                inaction_summary="PONR in 18h",
            ),
            expires_at=expires,
        )

    def test_all_questions_answered(self, sample_decision: DecisionObject):
        """Decision must answer all 7 questions."""
        assert sample_decision.q1_what is not None
        assert sample_decision.q2_when is not None
        assert sample_decision.q3_severity is not None
        assert sample_decision.q4_why is not None
        assert sample_decision.q5_action is not None
        assert sample_decision.q6_confidence is not None
        assert sample_decision.q7_inaction is not None

    def test_computed_properties(self, sample_decision: DecisionObject):
        """Computed properties should work."""
        assert sample_decision.primary_action_type == "REROUTE"
        assert sample_decision.is_actionable is True
        assert sample_decision.hours_until_expiry > 0

    def test_is_expired(self):
        """Expired decisions should be detected."""
        expired = DecisionObject(
            decision_id="dec_expired",
            customer_id="cust_123",
            signal_id="sig_123",
            q1_what=Q1WhatIsHappening(
                event_type="TEST",
                event_summary="Test",
                affected_chokepoint="red_sea",
                affected_routes=[],
                affected_shipments=[],
            ),
            q2_when=Q2WhenWillItHappen(
                status="TEST",
                impact_timeline="Test",
                urgency=Urgency.WATCH,
                urgency_reason="Test",
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

        assert expired.is_expired is True

    def test_get_summary(self, sample_decision: DecisionObject):
        """Summary should be one line with key info."""
        summary = sample_decision.get_summary()
        assert "REROUTE" in summary
        assert "$" in summary

    def test_get_inaction_warning(self, sample_decision: DecisionObject):
        """Inaction warning should mention cost."""
        warning = sample_decision.get_inaction_warning()
        assert "$" in warning
        assert "loss" in warning.lower()

    def test_is_actionable_false_for_monitor(self):
        """MONITOR decisions should not be actionable."""
        monitor_decision = DecisionObject(
            decision_id="dec_monitor",
            customer_id="cust_123",
            signal_id="sig_123",
            q1_what=Q1WhatIsHappening(
                event_type="TEST",
                event_summary="Test",
                affected_chokepoint="red_sea",
                affected_routes=[],
                affected_shipments=[],
            ),
            q2_when=Q2WhenWillItHappen(
                status="TEST",
                impact_timeline="Test",
                urgency=Urgency.WATCH,
                urgency_reason="Test",
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
                action_type="MONITOR",  # Monitor action
                action_summary="Watch and wait",
                affected_shipments=[],
                estimated_cost_usd=0,
                execution_steps=[],
                deadline=datetime.utcnow() + timedelta(hours=24),
                deadline_reason="Re-evaluate",
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
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )

        assert monitor_decision.is_actionable is False
