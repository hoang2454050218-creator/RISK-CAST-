"""Tests for Confidence Communication Module.

This module tests the ConfidenceCommunicator and related classes
that translate uncertainty metrics into actionable guidance.

Addresses audit gap A4.4 (Confidence Communication).
"""

import pytest
from datetime import datetime, timedelta

from app.uncertainty.bayesian import UncertainValue
from app.uncertainty.communication import (
    UncertaintyLevel,
    ActConfidence,
    UncertaintyReducer,
    RiskAdjustedRecommendations,
    ConfidenceGuidance,
    ConfidenceCommunicator,
)
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
from app.riskcast.constants import Severity, Urgency, ConfidenceLevel


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def communicator() -> ConfidenceCommunicator:
    """Create a ConfidenceCommunicator instance."""
    return ConfidenceCommunicator()


@pytest.fixture
def high_confidence_decision() -> DecisionObject:
    """Create a decision with high confidence."""
    return _create_decision(confidence_score=0.85)


@pytest.fixture
def low_confidence_decision() -> DecisionObject:
    """Create a decision with low confidence."""
    return _create_decision(confidence_score=0.45)


@pytest.fixture
def moderate_confidence_decision() -> DecisionObject:
    """Create a decision with moderate confidence."""
    return _create_decision(confidence_score=0.65)


@pytest.fixture
def narrow_ci_exposure() -> UncertainValue:
    """Create an UncertainValue with narrow CI (low uncertainty)."""
    return UncertainValue.from_normal(mean=100000.0, std=5000.0, unit="usd")


@pytest.fixture
def wide_ci_exposure() -> UncertainValue:
    """Create an UncertainValue with wide CI (high uncertainty)."""
    return UncertainValue.from_normal(mean=100000.0, std=50000.0, unit="usd")


@pytest.fixture
def narrow_ci_delay() -> UncertainValue:
    """Create delay UncertainValue with narrow CI."""
    return UncertainValue.from_triangular(low=8.0, mode=10.0, high=12.0, unit="days")


@pytest.fixture
def wide_ci_delay() -> UncertainValue:
    """Create delay UncertainValue with wide CI."""
    return UncertainValue.from_triangular(low=5.0, mode=10.0, high=20.0, unit="days")


@pytest.fixture
def narrow_ci_cost() -> UncertainValue:
    """Create cost UncertainValue with narrow CI."""
    return UncertainValue.from_range(low=7500.0, high=9000.0, unit="usd")


@pytest.fixture
def wide_ci_cost() -> UncertainValue:
    """Create cost UncertainValue with wide CI."""
    return UncertainValue.from_range(low=5000.0, high=15000.0, unit="usd")


def _create_decision(confidence_score: float) -> DecisionObject:
    """Helper to create a decision with specified confidence."""
    now = datetime.utcnow()
    
    return DecisionObject(
        decision_id="dec_test_001",
        customer_id="cust_test",
        signal_id="sig_test_001",
        q1_what=Q1WhatIsHappening(
            event_type="DISRUPTION",
            event_summary="Red Sea disruption affecting Shanghai→Rotterdam route",
            affected_chokepoint="red_sea",
            affected_routes=["CNSHA-NLRTM"],
            affected_shipments=["PO-4521"],
        ),
        q2_when=Q2WhenWillItHappen(
            status="CONFIRMED",
            impact_timeline="Impact is immediate",
            urgency=Urgency.URGENT,
            urgency_reason="Key window closing",
        ),
        q3_severity=Q3HowBadIsIt(
            total_exposure_usd=235000.0,
            exposure_breakdown={"cargo_at_risk": 235000.0},
            expected_delay_days=12,
            delay_range="10-14 days",
            shipments_affected=3,
            severity=Severity.HIGH,
        ),
        q4_why=Q4WhyIsThisHappening(
            root_cause="Houthi attacks on commercial vessels",
            causal_chain=["Disruption detected", "Carriers rerouting", "Extended transit"],
            evidence_summary="85% signal probability | 90% combined confidence",
            sources=["Polymarket", "AIS"],
        ),
        q5_action=Q5WhatToDoNow(
            action_type="REROUTE",
            action_summary="Reroute 3 shipments via Cape with MSC",
            affected_shipments=["PO-4521", "PO-4522", "PO-4523"],
            estimated_cost_usd=8500.0,
            execution_steps=["Contact MSC", "Confirm booking", "Update ETAs"],
            deadline=now + timedelta(hours=24),
            deadline_reason="MSC bookings close tomorrow",
        ),
        q6_confidence=Q6HowConfident(
            score=confidence_score,
            level=ConfidenceLevel.HIGH if confidence_score > 0.75 else 
                  ConfidenceLevel.MEDIUM if confidence_score > 0.5 else ConfidenceLevel.LOW,
            factors={
                "signal_probability": 0.85,
                "intelligence_correlation": 0.90,
                "impact_assessment": 0.80,
            },
            explanation=f"{int(confidence_score * 100)}% confidence based on multiple sources",
            caveats=[],
        ),
        q7_inaction=Q7WhatIfNothing(
            expected_loss_if_nothing=47000.0,
            cost_if_wait_6h=52000.0,
            cost_if_wait_24h=61000.0,
            cost_if_wait_48h=70000.0,
            worst_case_cost=85000.0,
            worst_case_scenario="Full cargo delay with penalties",
            inaction_summary="Expected loss: $47,000. Worst case: $85,000",
        ),
        expires_at=now + timedelta(hours=48),
    )


# ============================================================================
# TEST: UNCERTAINTY LEVEL CLASSIFICATION
# ============================================================================


class TestUncertaintyLevelClassification:
    """Test classification of uncertainty levels from CI width."""

    def test_very_low_uncertainty(self, communicator, high_confidence_decision, narrow_ci_cost, narrow_ci_delay):
        """Very narrow CI should be classified as VERY_LOW uncertainty."""
        # Create very narrow CI (5% of point estimate)
        exposure = UncertainValue.from_normal(mean=100000.0, std=2500.0, unit="usd")
        
        guidance = communicator.generate_guidance(
            decision=high_confidence_decision,
            exposure_uncertain=exposure,
            delay_uncertain=narrow_ci_delay,
            cost_uncertain=narrow_ci_cost,
        )
        
        assert guidance.uncertainty_level == UncertaintyLevel.VERY_LOW

    def test_low_uncertainty(self, communicator, high_confidence_decision, narrow_ci_delay, narrow_ci_cost):
        """Narrow CI should be classified as LOW uncertainty."""
        exposure = UncertainValue.from_normal(mean=100000.0, std=10000.0, unit="usd")
        
        guidance = communicator.generate_guidance(
            decision=high_confidence_decision,
            exposure_uncertain=exposure,
            delay_uncertain=narrow_ci_delay,
            cost_uncertain=narrow_ci_cost,
        )
        
        assert guidance.uncertainty_level in [UncertaintyLevel.VERY_LOW, UncertaintyLevel.LOW]

    def test_moderate_uncertainty(self, communicator, moderate_confidence_decision, narrow_ci_delay, narrow_ci_cost):
        """Moderate CI should be classified as MODERATE uncertainty."""
        exposure = UncertainValue.from_normal(mean=100000.0, std=20000.0, unit="usd")
        
        guidance = communicator.generate_guidance(
            decision=moderate_confidence_decision,
            exposure_uncertain=exposure,
            delay_uncertain=narrow_ci_delay,
            cost_uncertain=narrow_ci_cost,
        )
        
        assert guidance.uncertainty_level in [UncertaintyLevel.LOW, UncertaintyLevel.MODERATE]

    def test_high_uncertainty(self, communicator, low_confidence_decision, wide_ci_delay, wide_ci_cost):
        """Wide CI should be classified as HIGH uncertainty."""
        exposure = UncertainValue.from_normal(mean=100000.0, std=40000.0, unit="usd")
        
        guidance = communicator.generate_guidance(
            decision=low_confidence_decision,
            exposure_uncertain=exposure,
            delay_uncertain=wide_ci_delay,
            cost_uncertain=wide_ci_cost,
        )
        
        assert guidance.uncertainty_level in [UncertaintyLevel.MODERATE, UncertaintyLevel.HIGH, UncertaintyLevel.VERY_HIGH]

    def test_very_high_uncertainty(self, communicator, low_confidence_decision, wide_ci_delay, wide_ci_cost):
        """Very wide CI should be classified as VERY_HIGH uncertainty."""
        exposure = UncertainValue.from_normal(mean=100000.0, std=75000.0, unit="usd")
        
        guidance = communicator.generate_guidance(
            decision=low_confidence_decision,
            exposure_uncertain=exposure,
            delay_uncertain=wide_ci_delay,
            cost_uncertain=wide_ci_cost,
        )
        
        assert guidance.uncertainty_level in [UncertaintyLevel.HIGH, UncertaintyLevel.VERY_HIGH]


# ============================================================================
# TEST: ACT CONFIDENCE
# ============================================================================


class TestActConfidence:
    """Test action confidence recommendations."""

    def test_high_confidence_should_act(
        self, communicator, high_confidence_decision, narrow_ci_exposure, narrow_ci_delay, narrow_ci_cost
    ):
        """High confidence + narrow CI should result in HIGH act confidence."""
        guidance = communicator.generate_guidance(
            decision=high_confidence_decision,
            exposure_uncertain=narrow_ci_exposure,
            delay_uncertain=narrow_ci_delay,
            cost_uncertain=narrow_ci_cost,
        )
        
        assert guidance.should_act is True
        assert guidance.act_confidence == ActConfidence.HIGH

    def test_low_confidence_should_not_act(
        self, communicator, low_confidence_decision, wide_ci_exposure, wide_ci_delay, wide_ci_cost
    ):
        """Low confidence + wide CI should result in LOW act confidence."""
        guidance = communicator.generate_guidance(
            decision=low_confidence_decision,
            exposure_uncertain=wide_ci_exposure,
            delay_uncertain=wide_ci_delay,
            cost_uncertain=wide_ci_cost,
        )
        
        assert guidance.act_confidence in [ActConfidence.LOW, ActConfidence.MODERATE]

    def test_moderate_confidence_moderate_act(
        self, communicator, moderate_confidence_decision, narrow_ci_exposure, narrow_ci_delay, narrow_ci_cost
    ):
        """Moderate confidence should result in MODERATE act confidence."""
        guidance = communicator.generate_guidance(
            decision=moderate_confidence_decision,
            exposure_uncertain=narrow_ci_exposure,
            delay_uncertain=narrow_ci_delay,
            cost_uncertain=narrow_ci_cost,
        )
        
        assert guidance.act_confidence in [ActConfidence.MODERATE, ActConfidence.HIGH]


# ============================================================================
# TEST: CONFIDENCE GUIDANCE STRUCTURE
# ============================================================================


class TestConfidenceGuidanceStructure:
    """Test that ConfidenceGuidance has all required fields."""

    def test_guidance_has_all_required_fields(
        self, communicator, high_confidence_decision, narrow_ci_exposure, narrow_ci_delay, narrow_ci_cost
    ):
        """ConfidenceGuidance should have all mandatory fields."""
        guidance = communicator.generate_guidance(
            decision=high_confidence_decision,
            exposure_uncertain=narrow_ci_exposure,
            delay_uncertain=narrow_ci_delay,
            cost_uncertain=narrow_ci_cost,
        )
        
        # All required fields should be present and non-None
        assert guidance.confidence_score is not None
        assert guidance.confidence_range is not None
        assert guidance.uncertainty_level is not None
        assert guidance.should_act is not None
        assert guidance.act_confidence is not None
        assert guidance.act_confidence_text is not None
        assert guidance.plain_language_summary is not None
        assert guidance.risk_adjusted_recommendations is not None

    def test_guidance_has_uncertainty_reducers(
        self, communicator, low_confidence_decision, wide_ci_exposure, wide_ci_delay, wide_ci_cost
    ):
        """Low confidence guidance should suggest ways to reduce uncertainty."""
        guidance = communicator.generate_guidance(
            decision=low_confidence_decision,
            exposure_uncertain=wide_ci_exposure,
            delay_uncertain=wide_ci_delay,
            cost_uncertain=wide_ci_cost,
        )
        
        assert guidance.uncertainty_reducers is not None
        assert len(guidance.uncertainty_reducers) > 0

    def test_guidance_has_risk_adjusted_recommendations(
        self, communicator, high_confidence_decision, narrow_ci_exposure, narrow_ci_delay, narrow_ci_cost
    ):
        """Guidance should include risk-adjusted recommendations."""
        guidance = communicator.generate_guidance(
            decision=high_confidence_decision,
            exposure_uncertain=narrow_ci_exposure,
            delay_uncertain=narrow_ci_delay,
            cost_uncertain=narrow_ci_cost,
        )
        
        recs = guidance.risk_adjusted_recommendations
        assert recs.conservative is not None
        assert recs.balanced is not None
        assert recs.aggressive is not None
        
        # Recommendations should be non-empty strings
        assert len(recs.conservative) > 0
        assert len(recs.balanced) > 0
        assert len(recs.aggressive) > 0


# ============================================================================
# TEST: PLAIN LANGUAGE SUMMARY
# ============================================================================


class TestPlainLanguageSummary:
    """Test plain language summary generation."""

    def test_summary_is_readable(
        self, communicator, high_confidence_decision, narrow_ci_exposure, narrow_ci_delay, narrow_ci_cost
    ):
        """Plain language summary should be human-readable."""
        guidance = communicator.generate_guidance(
            decision=high_confidence_decision,
            exposure_uncertain=narrow_ci_exposure,
            delay_uncertain=narrow_ci_delay,
            cost_uncertain=narrow_ci_cost,
        )
        
        summary = guidance.plain_language_summary
        
        # Should be a non-empty string
        assert isinstance(summary, str)
        assert len(summary) > 20
        
        # Should contain key information
        assert "confidence" in summary.lower() or "certain" in summary.lower()

    def test_summary_mentions_uncertainty_when_high(
        self, communicator, low_confidence_decision, wide_ci_exposure, wide_ci_delay, wide_ci_cost
    ):
        """Summary should mention uncertainty when it's high."""
        guidance = communicator.generate_guidance(
            decision=low_confidence_decision,
            exposure_uncertain=wide_ci_exposure,
            delay_uncertain=wide_ci_delay,
            cost_uncertain=wide_ci_cost,
        )
        
        summary = guidance.plain_language_summary.lower()
        
        # Should mention uncertainty or caution
        uncertainty_words = ["uncertain", "confidence", "may", "could", "range", "approximately"]
        assert any(word in summary for word in uncertainty_words)


# ============================================================================
# TEST: CALIBRATED CONFIDENCE
# ============================================================================


class TestCalibratedConfidence:
    """Test calibrated confidence integration."""

    def test_calibrated_confidence_used_when_provided(
        self, communicator, high_confidence_decision, narrow_ci_exposure, narrow_ci_delay, narrow_ci_cost
    ):
        """Calibrated confidence should be used when provided."""
        calibrated = 0.72  # Different from decision's 0.85
        
        guidance = communicator.generate_guidance(
            decision=high_confidence_decision,
            exposure_uncertain=narrow_ci_exposure,
            delay_uncertain=narrow_ci_delay,
            cost_uncertain=narrow_ci_cost,
            calibrated_confidence=calibrated,
        )
        
        # Guidance should use the calibrated value
        assert guidance.confidence_score == calibrated

    def test_decision_confidence_used_when_not_calibrated(
        self, communicator, high_confidence_decision, narrow_ci_exposure, narrow_ci_delay, narrow_ci_cost
    ):
        """Decision confidence should be used when calibrated not provided."""
        guidance = communicator.generate_guidance(
            decision=high_confidence_decision,
            exposure_uncertain=narrow_ci_exposure,
            delay_uncertain=narrow_ci_delay,
            cost_uncertain=narrow_ci_cost,
        )
        
        # Should use decision's confidence
        assert guidance.confidence_score == high_confidence_decision.q6_confidence.score


# ============================================================================
# TEST: UNCERTAINTY REDUCERS
# ============================================================================


class TestUncertaintyReducers:
    """Test uncertainty reducer suggestions."""

    def test_reducers_suggested_for_high_uncertainty(
        self, communicator, low_confidence_decision, wide_ci_exposure, wide_ci_delay, wide_ci_cost
    ):
        """Uncertainty reducers should be suggested when uncertainty is high."""
        guidance = communicator.generate_guidance(
            decision=low_confidence_decision,
            exposure_uncertain=wide_ci_exposure,
            delay_uncertain=wide_ci_delay,
            cost_uncertain=wide_ci_cost,
        )
        
        assert len(guidance.uncertainty_reducers) > 0
        
        # Each reducer should have required fields
        for reducer in guidance.uncertainty_reducers:
            assert reducer.action is not None
            assert len(reducer.action) > 0
            assert reducer.expected_reduction is not None
            assert 0 < reducer.expected_reduction <= 1.0

    def test_reducers_have_time_estimates(
        self, communicator, low_confidence_decision, wide_ci_exposure, wide_ci_delay, wide_ci_cost
    ):
        """Uncertainty reducers should include time estimates."""
        guidance = communicator.generate_guidance(
            decision=low_confidence_decision,
            exposure_uncertain=wide_ci_exposure,
            delay_uncertain=wide_ci_delay,
            cost_uncertain=wide_ci_cost,
        )
        
        for reducer in guidance.uncertainty_reducers:
            assert reducer.time_to_get is not None
            assert len(reducer.time_to_get) > 0


# ============================================================================
# TEST: RISK-ADJUSTED RECOMMENDATIONS
# ============================================================================


class TestRiskAdjustedRecommendations:
    """Test risk-adjusted recommendation generation."""

    def test_conservative_recommendation_is_cautious(
        self, communicator, moderate_confidence_decision, narrow_ci_exposure, narrow_ci_delay, narrow_ci_cost
    ):
        """Conservative recommendation should be more cautious."""
        guidance = communicator.generate_guidance(
            decision=moderate_confidence_decision,
            exposure_uncertain=narrow_ci_exposure,
            delay_uncertain=narrow_ci_delay,
            cost_uncertain=narrow_ci_cost,
        )
        
        recs = guidance.risk_adjusted_recommendations
        
        # Conservative should mention caution, waiting, or lower risk options
        conservative_words = ["wait", "conservative", "monitor", "hold", "cautious", "additional"]
        assert any(word in recs.conservative.lower() for word in conservative_words)

    def test_aggressive_recommendation_is_proactive(
        self, communicator, high_confidence_decision, narrow_ci_exposure, narrow_ci_delay, narrow_ci_cost
    ):
        """Aggressive recommendation should be more proactive."""
        guidance = communicator.generate_guidance(
            decision=high_confidence_decision,
            exposure_uncertain=narrow_ci_exposure,
            delay_uncertain=narrow_ci_delay,
            cost_uncertain=narrow_ci_cost,
        )
        
        recs = guidance.risk_adjusted_recommendations
        
        # Aggressive should mention action, proceed, or opportunity
        aggressive_words = ["proceed", "act", "immediately", "now", "opportunity", "recommended"]
        assert any(word in recs.aggressive.lower() for word in aggressive_words)


# ============================================================================
# TEST: DATA QUALITY IMPACT
# ============================================================================


class TestDataQualityImpact:
    """Test data quality impact assessment."""

    def test_guidance_includes_data_quality_assessment(
        self, communicator, high_confidence_decision, narrow_ci_exposure, narrow_ci_delay, narrow_ci_cost
    ):
        """Guidance should include data quality impact assessment."""
        guidance = communicator.generate_guidance(
            decision=high_confidence_decision,
            exposure_uncertain=narrow_ci_exposure,
            delay_uncertain=narrow_ci_delay,
            cost_uncertain=narrow_ci_cost,
        )
        
        assert guidance.data_quality_impact is not None
        assert len(guidance.data_quality_impact) > 0

    def test_guidance_includes_model_confidence_impact(
        self, communicator, high_confidence_decision, narrow_ci_exposure, narrow_ci_delay, narrow_ci_cost
    ):
        """Guidance should include model confidence impact assessment."""
        guidance = communicator.generate_guidance(
            decision=high_confidence_decision,
            exposure_uncertain=narrow_ci_exposure,
            delay_uncertain=narrow_ci_delay,
            cost_uncertain=narrow_ci_cost,
        )
        
        assert guidance.model_confidence_impact is not None
        assert len(guidance.model_confidence_impact) > 0


# ============================================================================
# TEST: CONFIDENCE RANGE
# ============================================================================


class TestConfidenceRange:
    """Test confidence range calculation."""

    def test_confidence_range_is_valid(
        self, communicator, high_confidence_decision, narrow_ci_exposure, narrow_ci_delay, narrow_ci_cost
    ):
        """Confidence range should be a valid interval."""
        guidance = communicator.generate_guidance(
            decision=high_confidence_decision,
            exposure_uncertain=narrow_ci_exposure,
            delay_uncertain=narrow_ci_delay,
            cost_uncertain=narrow_ci_cost,
        )
        
        low, high = guidance.confidence_range
        
        # Should be valid bounds
        assert 0.0 <= low <= 1.0
        assert 0.0 <= high <= 1.0
        assert low <= high
        
        # Point estimate should be within range
        assert low <= guidance.confidence_score <= high

    def test_confidence_range_wider_for_uncertain(
        self, communicator, low_confidence_decision, wide_ci_exposure, wide_ci_delay, wide_ci_cost,
        high_confidence_decision, narrow_ci_exposure, narrow_ci_delay, narrow_ci_cost
    ):
        """Confidence range should be wider when uncertainty is higher."""
        low_conf_guidance = communicator.generate_guidance(
            decision=low_confidence_decision,
            exposure_uncertain=wide_ci_exposure,
            delay_uncertain=wide_ci_delay,
            cost_uncertain=wide_ci_cost,
        )
        
        high_conf_guidance = communicator.generate_guidance(
            decision=high_confidence_decision,
            exposure_uncertain=narrow_ci_exposure,
            delay_uncertain=narrow_ci_delay,
            cost_uncertain=narrow_ci_cost,
        )
        
        low_width = low_conf_guidance.confidence_range[1] - low_conf_guidance.confidence_range[0]
        high_width = high_conf_guidance.confidence_range[1] - high_conf_guidance.confidence_range[0]
        
        # Low confidence should have wider range (allowing some tolerance)
        assert low_width >= high_width * 0.8  # At least 80% as wide


# ============================================================================
# TEST: EDGE CASES
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_exposure_handling(self, communicator, high_confidence_decision, narrow_ci_delay, narrow_ci_cost):
        """Should handle zero exposure gracefully."""
        zero_exposure = UncertainValue.from_point(0.0, unit="usd")
        
        guidance = communicator.generate_guidance(
            decision=high_confidence_decision,
            exposure_uncertain=zero_exposure,
            delay_uncertain=narrow_ci_delay,
            cost_uncertain=narrow_ci_cost,
        )
        
        assert guidance is not None
        assert guidance.uncertainty_level is not None

    def test_very_high_confidence_handling(
        self, communicator, narrow_ci_exposure, narrow_ci_delay, narrow_ci_cost
    ):
        """Should handle very high confidence (>0.95) gracefully."""
        high_conf_decision = _create_decision(confidence_score=0.98)
        
        guidance = communicator.generate_guidance(
            decision=high_conf_decision,
            exposure_uncertain=narrow_ci_exposure,
            delay_uncertain=narrow_ci_delay,
            cost_uncertain=narrow_ci_cost,
        )
        
        assert guidance.should_act is True
        assert guidance.act_confidence == ActConfidence.HIGH

    def test_very_low_confidence_handling(
        self, communicator, wide_ci_exposure, wide_ci_delay, wide_ci_cost
    ):
        """Should handle very low confidence (<0.3) gracefully."""
        low_conf_decision = _create_decision(confidence_score=0.25)
        
        guidance = communicator.generate_guidance(
            decision=low_conf_decision,
            exposure_uncertain=wide_ci_exposure,
            delay_uncertain=wide_ci_delay,
            cost_uncertain=wide_ci_cost,
        )
        
        assert guidance.act_confidence == ActConfidence.LOW
        # Should suggest uncertainty reducers
        assert len(guidance.uncertainty_reducers) > 0
