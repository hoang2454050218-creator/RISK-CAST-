"""
Tests for Challenge Handling System (C2.2).

Tests the ability for customers to dispute/challenge decisions,
which is critical for legal defensibility.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock

from app.human.service import HumanCollaborationService
from app.human.schemas import (
    ChallengeReason,
    ChallengeStatus,
    ChallengeRequest,
    ChallengeRecord,
    ChallengeResolution,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_audit_service():
    """Create a mock audit service."""
    audit = MagicMock()
    audit.record_event = AsyncMock()
    return audit


@pytest.fixture
def challenge_service(mock_audit_service):
    """Create HumanCollaborationService for challenge testing."""
    return HumanCollaborationService(audit_service=mock_audit_service)


@pytest.fixture
def sample_challenge_request():
    """Create a sample challenge request."""
    return ChallengeRequest(
        decision_id="decision_test123",
        challenger_id="customer_user_001",
        challenger_role="customer",
        reason=ChallengeReason.CALCULATION_ERROR,
        reason_details="The reroute cost estimate of $8,500 was significantly higher than the actual cost of $4,200. This represents a 100% overestimate that led to unnecessary delays.",
        evidence=[
            "Invoice from MSC showing actual cost: $4,200",
            "Original decision showing estimate: $8,500",
        ],
        claimed_impact_usd=15000,
        claimed_delay_days=3,
        requested_remedy="Refund of decision subscription fee and correction to decision model",
        is_urgent=False,
    )


@pytest.fixture
def urgent_challenge_request():
    """Create an urgent challenge request."""
    return ChallengeRequest(
        decision_id="decision_urgent456",
        challenger_id="customer_user_002",
        challenger_role="customer",
        reason=ChallengeReason.INCORRECT_DATA,
        reason_details="The system used outdated vessel tracking data showing my cargo still in transit when it had already arrived at destination 2 days ago. This caused unnecessary panic and incorrect actions.",
        evidence=[
            "Port authority confirmation of arrival",
            "Original decision showing cargo status: in transit",
        ],
        claimed_impact_usd=5000,
        requested_remedy="Immediate correction and apology",
        is_urgent=True,
    )


@pytest.fixture
def sample_resolution():
    """Create a sample challenge resolution."""
    return ChallengeResolution(
        challenge_id="challenge_abc123",
        status=ChallengeStatus.PARTIALLY_UPHELD,
        resolved_by="reviewer_admin_001",
        resolved_at=datetime.utcnow(),
        review_summary="Upon investigation, we found that the cost estimate used outdated fuel surcharge data from the previous month. The methodology was correct but the input data was stale.",
        findings=[
            "Cost estimate used December fuel surcharge instead of January",
            "This resulted in $2,100 overestimate",
            "Methodology and calculation logic were correct",
            "Data feed delay issue identified",
        ],
        original_data_valid=False,
        methodology_valid=True,
        calculations_valid=True,
        corrected_action="Reroute remains the correct action, but at corrected cost of $6,400",
        corrected_exposure_usd=6400,
        remedy_provided="50% discount on next month subscription + model data feed update",
        compensation_usd=500,
        improvement_actions=[
            "Add data staleness check to cost calculation pipeline",
            "Implement real-time fuel surcharge API integration",
            "Add confidence warning when data > 7 days old",
        ],
        model_update_required=True,
        time_to_resolution_hours=36,
    )


# ============================================================================
# TEST: SUBMIT CHALLENGE
# ============================================================================


class TestSubmitChallenge:
    """Tests for challenge submission."""
    
    @pytest.mark.asyncio
    async def test_submit_challenge_creates_record(
        self,
        challenge_service,
        sample_challenge_request,
    ):
        """Submitting a challenge creates a complete record."""
        result = await challenge_service.submit_challenge(sample_challenge_request)
        
        assert result is not None
        assert isinstance(result, ChallengeRecord)
        assert result.challenge_id.startswith("challenge_")
        assert result.decision_id == sample_challenge_request.decision_id
        assert result.challenger_id == sample_challenge_request.challenger_id
        assert result.status == ChallengeStatus.SUBMITTED
    
    @pytest.mark.asyncio
    async def test_submit_challenge_preserves_evidence(
        self,
        challenge_service,
        sample_challenge_request,
    ):
        """Challenge submission preserves all evidence."""
        result = await challenge_service.submit_challenge(sample_challenge_request)
        
        assert result.evidence == sample_challenge_request.evidence
        assert result.claimed_impact_usd == sample_challenge_request.claimed_impact_usd
        assert result.claimed_delay_days == sample_challenge_request.claimed_delay_days
    
    @pytest.mark.asyncio
    async def test_urgent_challenge_gets_higher_priority(
        self,
        challenge_service,
        urgent_challenge_request,
    ):
        """Urgent challenges get critical priority and shorter SLA."""
        result = await challenge_service.submit_challenge(urgent_challenge_request)
        
        assert result.priority == "critical"
        # SLA should be ~24 hours for urgent
        assert result.sla_deadline is not None
        time_until_deadline = result.sla_deadline - datetime.utcnow()
        assert time_until_deadline.total_seconds() <= 24 * 3600 + 60  # 24 hours + buffer
    
    @pytest.mark.asyncio
    async def test_high_value_challenge_gets_high_priority(
        self,
        challenge_service,
    ):
        """High-value challenges (>$100k) get high priority."""
        request = ChallengeRequest(
            decision_id="decision_highvalue",
            challenger_id="customer_big",
            challenger_role="customer",
            reason=ChallengeReason.METHODOLOGY_FLAW,
            reason_details="The risk assessment methodology failed to account for the new Suez Canal expansion, resulting in grossly incorrect delay estimates and massive financial exposure.",
            claimed_impact_usd=250000,
            requested_remedy="Full review of methodology and compensation for losses",
        )
        
        result = await challenge_service.submit_challenge(request)
        
        assert result.priority == "high"
        # SLA should be ~48 hours for high priority
        assert result.sla_deadline is not None
        time_until_deadline = result.sla_deadline - datetime.utcnow()
        assert time_until_deadline.total_seconds() <= 48 * 3600 + 60


# ============================================================================
# TEST: CHALLENGE WORKFLOW
# ============================================================================


class TestChallengeWorkflow:
    """Tests for challenge workflow progression."""
    
    @pytest.mark.asyncio
    async def test_assign_challenge_to_reviewer(
        self,
        challenge_service,
        sample_challenge_request,
    ):
        """Challenge can be assigned to a reviewer."""
        challenge = await challenge_service.submit_challenge(sample_challenge_request)
        
        result = await challenge_service.assign_challenge(
            challenge.challenge_id,
            reviewer_id="reviewer_001",
        )
        
        assert result.assigned_to == "reviewer_001"
        assert result.assigned_at is not None
        assert result.status == ChallengeStatus.UNDER_REVIEW
    
    @pytest.mark.asyncio
    async def test_request_more_info(
        self,
        challenge_service,
        sample_challenge_request,
    ):
        """Reviewer can request more information."""
        challenge = await challenge_service.submit_challenge(sample_challenge_request)
        await challenge_service.assign_challenge(challenge.challenge_id, "reviewer_001")
        
        result = await challenge_service.request_challenge_info(
            challenge.challenge_id,
            reviewer_id="reviewer_001",
            info_needed="Please provide the original invoice number",
        )
        
        assert result.status == ChallengeStatus.NEEDS_INFO
    
    @pytest.mark.asyncio
    async def test_only_assigned_reviewer_can_request_info(
        self,
        challenge_service,
        sample_challenge_request,
    ):
        """Only assigned reviewer can request info."""
        challenge = await challenge_service.submit_challenge(sample_challenge_request)
        await challenge_service.assign_challenge(challenge.challenge_id, "reviewer_001")
        
        with pytest.raises(ValueError, match="Only assigned reviewer"):
            await challenge_service.request_challenge_info(
                challenge.challenge_id,
                reviewer_id="different_reviewer",
                info_needed="Some info",
            )


# ============================================================================
# TEST: CHALLENGE RESOLUTION
# ============================================================================


class TestChallengeResolution:
    """Tests for challenge resolution."""
    
    @pytest.mark.asyncio
    async def test_resolve_challenge_upheld(
        self,
        challenge_service,
        sample_challenge_request,
    ):
        """Challenge can be resolved as upheld (decision was correct)."""
        challenge = await challenge_service.submit_challenge(sample_challenge_request)
        await challenge_service.assign_challenge(challenge.challenge_id, "reviewer_001")
        
        resolution = ChallengeResolution(
            challenge_id=challenge.challenge_id,
            status=ChallengeStatus.UPHELD,
            resolved_by="reviewer_001",
            resolved_at=datetime.utcnow(),
            review_summary="After thorough review, the original cost estimate was found to be accurate. The challenger's invoice appears to be for a different shipment.",
            findings=[
                "Cost estimate matched market rates at time of decision",
                "Challenger's invoice is for a different container (MSKU1234567)",
                "Original decision referenced container MSKU7654321",
            ],
            original_data_valid=True,
            methodology_valid=True,
            calculations_valid=True,
            remedy_provided="No remedy required - challenge not upheld",
            time_to_resolution_hours=24,
        )
        
        result = await challenge_service.resolve_challenge(
            challenge.challenge_id,
            resolution,
        )
        
        assert result.status == ChallengeStatus.UPHELD
        assert result.resolution is not None
        assert result.resolution.original_data_valid is True
    
    @pytest.mark.asyncio
    async def test_resolve_challenge_overturned(
        self,
        challenge_service,
        sample_challenge_request,
    ):
        """Challenge can be resolved as overturned (decision was wrong)."""
        challenge = await challenge_service.submit_challenge(sample_challenge_request)
        await challenge_service.assign_challenge(challenge.challenge_id, "reviewer_001")
        
        resolution = ChallengeResolution(
            challenge_id=challenge.challenge_id,
            status=ChallengeStatus.OVERTURNED,
            resolved_by="reviewer_001",
            resolved_at=datetime.utcnow(),
            review_summary="The challenge is valid. The system used incorrect data that led to a wrong recommendation.",
            findings=[
                "Data source was experiencing outage during decision",
                "Stale cache was used instead of live data",
                "This caused 100% error in cost estimate",
            ],
            original_data_valid=False,
            methodology_valid=True,
            calculations_valid=True,
            corrected_action="MONITOR instead of REROUTE",
            corrected_exposure_usd=4200,
            remedy_provided="Full refund + 3 months free service",
            compensation_usd=1500,
            improvement_actions=[
                "Add data source health check",
                "Implement fallback to alternative data sources",
                "Add confidence penalty when using cached data",
            ],
            model_update_required=True,
            time_to_resolution_hours=48,
        )
        
        result = await challenge_service.resolve_challenge(
            challenge.challenge_id,
            resolution,
        )
        
        assert result.status == ChallengeStatus.OVERTURNED
        assert result.resolution.model_update_required is True
        assert result.resolution.compensation_usd == 1500
    
    @pytest.mark.asyncio
    async def test_cannot_resolve_already_resolved(
        self,
        challenge_service,
        sample_challenge_request,
        sample_resolution,
    ):
        """Cannot resolve an already resolved challenge."""
        challenge = await challenge_service.submit_challenge(sample_challenge_request)
        await challenge_service.assign_challenge(challenge.challenge_id, "reviewer_001")
        
        # Update resolution to match challenge ID
        resolution1 = ChallengeResolution(
            **{**sample_resolution.model_dump(), "challenge_id": challenge.challenge_id}
        )
        await challenge_service.resolve_challenge(challenge.challenge_id, resolution1)
        
        # Try to resolve again
        resolution2 = ChallengeResolution(
            **{**sample_resolution.model_dump(), "challenge_id": challenge.challenge_id}
        )
        with pytest.raises(ValueError, match="already resolved"):
            await challenge_service.resolve_challenge(challenge.challenge_id, resolution2)


# ============================================================================
# TEST: CHALLENGE QUERIES
# ============================================================================


class TestChallengeQueries:
    """Tests for challenge query methods."""
    
    @pytest.mark.asyncio
    async def test_get_challenge_by_id(
        self,
        challenge_service,
        sample_challenge_request,
    ):
        """Can retrieve challenge by ID."""
        challenge = await challenge_service.submit_challenge(sample_challenge_request)
        
        result = await challenge_service.get_challenge(challenge.challenge_id)
        
        assert result is not None
        assert result.challenge_id == challenge.challenge_id
    
    @pytest.mark.asyncio
    async def test_get_challenges_for_decision(
        self,
        challenge_service,
    ):
        """Can retrieve all challenges for a decision."""
        decision_id = "decision_multi_challenge"
        
        # Submit multiple challenges
        for i in range(3):
            request = ChallengeRequest(
                decision_id=decision_id,
                challenger_id=f"customer_{i}",
                challenger_role="customer",
                reason=ChallengeReason.CALCULATION_ERROR,
                reason_details=f"Challenge #{i} - The cost calculation appears to be off by a significant margin based on our analysis.",
                requested_remedy=f"Remedy #{i}",
            )
            await challenge_service.submit_challenge(request)
        
        # Submit one for different decision
        other_request = ChallengeRequest(
            decision_id="other_decision",
            challenger_id="other_customer",
            challenger_role="customer",
            reason=ChallengeReason.INCORRECT_DATA,
            reason_details="This is a challenge for a completely different decision to test filtering.",
            requested_remedy="Other remedy",
        )
        await challenge_service.submit_challenge(other_request)
        
        # Get challenges for target decision
        results = await challenge_service.get_challenges_for_decision(decision_id)
        
        assert len(results) == 3
        for result in results:
            assert result.decision_id == decision_id
    
    @pytest.mark.asyncio
    async def test_get_pending_challenges_sorted(
        self,
        challenge_service,
    ):
        """Pending challenges are sorted by priority then deadline."""
        # Submit challenges with different priorities
        normal = ChallengeRequest(
            decision_id="decision_normal",
            challenger_id="customer_1",
            challenger_role="customer",
            reason=ChallengeReason.OTHER,
            reason_details="Normal priority challenge that should come last in the sorted list.",
            requested_remedy="Normal remedy",
        )
        
        urgent = ChallengeRequest(
            decision_id="decision_urgent",
            challenger_id="customer_2",
            challenger_role="customer",
            reason=ChallengeReason.CALCULATION_ERROR,
            reason_details="Urgent priority challenge that should come first in the sorted list.",
            requested_remedy="Urgent remedy",
            is_urgent=True,
        )
        
        high = ChallengeRequest(
            decision_id="decision_high",
            challenger_id="customer_3",
            challenger_role="customer",
            reason=ChallengeReason.METHODOLOGY_FLAW,
            reason_details="High priority challenge based on claimed impact over $100k threshold.",
            claimed_impact_usd=200000,
            requested_remedy="High remedy",
        )
        
        await challenge_service.submit_challenge(normal)
        await challenge_service.submit_challenge(urgent)
        await challenge_service.submit_challenge(high)
        
        results = await challenge_service.get_pending_challenges()
        
        assert len(results) == 3
        assert results[0].priority == "critical"  # urgent
        assert results[1].priority == "high"
        assert results[2].priority == "normal"


# ============================================================================
# TEST: CHALLENGE METRICS
# ============================================================================


class TestChallengeMetrics:
    """Tests for challenge metrics calculation."""
    
    @pytest.mark.asyncio
    async def test_metrics_with_no_challenges(
        self,
        challenge_service,
    ):
        """Metrics handle empty challenge list."""
        metrics = await challenge_service.get_challenge_metrics()
        
        assert metrics["total_challenges"] == 0
        assert metrics["success_rate"] is None
    
    @pytest.mark.asyncio
    async def test_metrics_calculation(
        self,
        challenge_service,
    ):
        """Metrics are calculated correctly."""
        # Submit and resolve challenges
        requests = [
            ChallengeRequest(
                decision_id=f"decision_{i}",
                challenger_id="customer",
                challenger_role="customer",
                reason=ChallengeReason.CALCULATION_ERROR,
                reason_details="Challenge for metrics testing - detailed reason for the challenge submission.",
                requested_remedy="Test remedy",
            )
            for i in range(5)
        ]
        
        challenges = []
        for req in requests:
            challenge = await challenge_service.submit_challenge(req)
            await challenge_service.assign_challenge(challenge.challenge_id, "reviewer")
            challenges.append(challenge)
        
        # Resolve 3: 1 upheld, 1 overturned, 1 partially upheld
        for i, status in enumerate([
            ChallengeStatus.UPHELD,
            ChallengeStatus.OVERTURNED,
            ChallengeStatus.PARTIALLY_UPHELD,
        ]):
            resolution = ChallengeResolution(
                challenge_id=challenges[i].challenge_id,
                status=status,
                resolved_by="reviewer",
                resolved_at=datetime.utcnow(),
                review_summary="Test resolution summary for metrics calculation and testing purposes.",
                findings=["Finding 1"],
                original_data_valid=True,
                methodology_valid=True,
                calculations_valid=True,
                remedy_provided="Test remedy",
                time_to_resolution_hours=24,
            )
            await challenge_service.resolve_challenge(challenges[i].challenge_id, resolution)
        
        # Leave 2 pending
        
        metrics = await challenge_service.get_challenge_metrics()
        
        assert metrics["total_challenges"] == 5
        assert metrics["resolved"] == 3
        assert metrics["pending"] == 2
        assert metrics["upheld"] == 1
        assert metrics["overturned"] == 1
        assert metrics["partially_upheld"] == 1
        # Success rate = (1 overturned + 1 partial) / 3 resolved = 0.666...
        assert abs(metrics["success_rate"] - (2/3)) < 0.01


# ============================================================================
# TEST: CHALLENGE VALIDATION
# ============================================================================


class TestChallengeValidation:
    """Tests for challenge request validation."""
    
    def test_reason_details_minimum_length(self):
        """Reason details must be at least 50 characters."""
        with pytest.raises(ValueError, match="at least 50 characters"):
            ChallengeRequest(
                decision_id="test",
                challenger_id="user",
                challenger_role="customer",
                reason=ChallengeReason.OTHER,
                reason_details="Too short",  # Less than 50 chars
                requested_remedy="Test",
            )
    
    def test_valid_challenge_request(self):
        """Valid challenge request passes validation."""
        request = ChallengeRequest(
            decision_id="test_decision",
            challenger_id="customer_user",
            challenger_role="customer",
            reason=ChallengeReason.INCOMPLETE_ANALYSIS,
            reason_details="The analysis failed to consider the impact of the new port expansion project which significantly reduces transit times.",
            evidence=["Port authority announcement", "News article"],
            requested_remedy="Recalculation with updated data",
        )
        
        assert request.reason == ChallengeReason.INCOMPLETE_ANALYSIS
        assert len(request.evidence) == 2


# ============================================================================
# TEST: AUDIT INTEGRATION
# ============================================================================


class TestChallengeAuditIntegration:
    """Tests for challenge audit trail integration."""
    
    @pytest.mark.asyncio
    async def test_challenge_creates_audit_trail(
        self,
        challenge_service,
        sample_challenge_request,
    ):
        """Challenge operations should be auditable."""
        # Submit challenge
        challenge = await challenge_service.submit_challenge(sample_challenge_request)
        
        # The challenge should have audit trail IDs list (even if empty initially)
        assert hasattr(challenge, 'audit_trail_ids')
        
        # Core data should be preserved for audit
        assert challenge.reason_details == sample_challenge_request.reason_details
        assert challenge.evidence == sample_challenge_request.evidence
        assert challenge.challenged_at is not None
    
    @pytest.mark.asyncio
    async def test_resolution_preserves_all_findings(
        self,
        challenge_service,
        sample_challenge_request,
    ):
        """Resolution must preserve all findings for legal defensibility."""
        challenge = await challenge_service.submit_challenge(sample_challenge_request)
        await challenge_service.assign_challenge(challenge.challenge_id, "reviewer")
        
        resolution = ChallengeResolution(
            challenge_id=challenge.challenge_id,
            status=ChallengeStatus.PARTIALLY_UPHELD,
            resolved_by="reviewer",
            resolved_at=datetime.utcnow(),
            review_summary="Detailed review finding partial validity to the challenge claims.",
            findings=[
                "Finding A: Data was 2 days old",
                "Finding B: Calculation was correct",
                "Finding C: Methodology needs update",
            ],
            original_data_valid=False,
            methodology_valid=True,
            calculations_valid=True,
            corrected_action="MONITOR",
            corrected_exposure_usd=5000,
            remedy_provided="Partial refund",
            compensation_usd=250,
            improvement_actions=["Add data freshness check"],
            model_update_required=True,
            time_to_resolution_hours=30,
        )
        
        result = await challenge_service.resolve_challenge(challenge.challenge_id, resolution)
        
        # All resolution details preserved
        assert result.resolution.findings == resolution.findings
        assert result.resolution.original_data_valid is False
        assert result.resolution.improvement_actions == ["Add data freshness check"]
        assert result.resolution.model_update_required is True
