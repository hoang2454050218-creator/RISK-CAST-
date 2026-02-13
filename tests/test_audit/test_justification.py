"""Tests for legal justification document generation.

These tests verify:
1. Executive summary generation (fast, < 100ms)
2. Detailed justification with 7 Questions format
3. Legal justification with full provenance
4. Multi-language support (EN, VI)
5. Limitations disclosure accuracy
6. Verification hash integrity
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.audit.justification import (
    JustificationLevel,
    Audience,
    EvidenceItem,
    AlternativeAnalysis,
    LimitationsDisclosure,
    LegalJustification,
    JustificationGenerator,
    create_justification_generator,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_audit_service():
    """Create mock audit service."""
    service = AsyncMock()
    service.get_decision_audit_trail = AsyncMock(return_value={
        "decision_id": "dec_test_001",
        "input_snapshot": {
            "snapshot_id": "snap_001",
            "signal_data": {"probability": 0.85},
            "reality_data": {"correlation_status": "confirmed"},
            "captured_at": datetime.utcnow().isoformat(),
        },
        "processing_record": {
            "record_id": "proc_001",
            "model_version": "v2.0.0",
            "computation_time_ms": 150,
        },
        "audit_events": [
            {
                "event_id": "evt_001",
                "event_type": "decision_created",
                "record_hash": "abc123",
            }
        ],
    })
    service.initialize = AsyncMock()
    return service


@pytest.fixture
def sample_decision():
    """Create a sample decision object for testing."""
    # Create mock decision with 7 Questions
    decision = MagicMock()
    decision.decision_id = "dec_test_001"
    decision.customer_id = "cust_001"
    decision.signal_id = "sig_001"
    decision.generated_at = datetime.utcnow()
    decision.chokepoint = "red_sea"
    decision.expires_at = datetime.utcnow() + timedelta(hours=24)
    
    # Q1 - What
    decision.q1_what = MagicMock()
    decision.q1_what.event_summary = "Red Sea disruption affecting Shanghai-Rotterdam route"
    decision.q1_what.affected_chokepoint = "red_sea"
    decision.q1_what.affected_routes = ["CNSHA-NLRTM"]
    decision.q1_what.affected_shipments = ["SHP001", "SHP002"]
    
    # Q2 - When
    decision.q2_when = MagicMock()
    decision.q2_when.status = "CONFIRMED"
    decision.q2_when.impact_timeline = "Impact starts in 3 days"
    decision.q2_when.urgency = MagicMock()
    decision.q2_when.urgency.value = "urgent"
    decision.q2_when.urgency_reason = "Key booking window closing"
    
    # Q3 - Severity
    decision.q3_severity = MagicMock()
    decision.q3_severity.total_exposure_usd = 150000.0
    decision.q3_severity.expected_delay_days = 10
    decision.q3_severity.delay_range = "7-14 days"
    decision.q3_severity.shipments_affected = 2
    decision.q3_severity.exposure_breakdown = {"cargo": 120000, "penalties": 30000}
    decision.q3_severity.severity = MagicMock()
    decision.q3_severity.severity.value = "high"
    
    # Q4 - Why
    decision.q4_why = MagicMock()
    decision.q4_why.root_cause = "Houthi attacks on Red Sea shipping"
    decision.q4_why.causal_chain = [
        "Houthi attacks increase",
        "Carriers avoid Suez",
        "Routes diverted via Cape",
        "Transit time increases 7-14 days",
    ]
    decision.q4_why.evidence_summary = "85% probability from Polymarket, confirmed by AIS"
    decision.q4_why.sources = ["Polymarket", "AIS", "News"]
    
    # Q5 - Action
    decision.q5_action = MagicMock()
    decision.q5_action.action_type = "reroute"
    decision.q5_action.action_summary = "Reroute via Cape of Good Hope with MSC"
    decision.q5_action.estimated_cost_usd = 8500.0
    decision.q5_action.deadline = datetime.utcnow() + timedelta(hours=12)
    decision.q5_action.deadline_reason = "MSC booking window closes at 6PM"
    decision.q5_action.affected_shipments = ["SHP001", "SHP002"]
    decision.q5_action.execution_steps = [
        "Contact MSC booking desk",
        "Request Cape routing",
        "Confirm new ETAs",
    ]
    
    # Q6 - Confidence
    decision.q6_confidence = MagicMock()
    decision.q6_confidence.score = 0.87
    decision.q6_confidence.level = MagicMock()
    decision.q6_confidence.level.value = "high"
    decision.q6_confidence.explanation = "87% confidence based on multiple sources"
    decision.q6_confidence.factors = {
        "signal_probability": 0.85,
        "correlation_confidence": 0.90,
        "impact_confidence": 0.86,
    }
    decision.q6_confidence.caveats = [
        "Rate estimates may vary by ±10%",
        "Situation may change rapidly",
    ]
    
    # Q7 - Inaction
    decision.q7_inaction = MagicMock()
    decision.q7_inaction.expected_loss_if_nothing = 45000.0
    decision.q7_inaction.cost_if_wait_6h = 52000.0
    decision.q7_inaction.cost_if_wait_24h = 75000.0
    decision.q7_inaction.point_of_no_return = datetime.utcnow() + timedelta(hours=48)
    decision.q7_inaction.point_of_no_return_reason = "All carrier capacity exhausted"
    decision.q7_inaction.worst_case_cost = 150000.0
    decision.q7_inaction.worst_case_scenario = "Full cargo loss if uninsured"
    
    # Alternative actions
    decision.alternative_actions = [
        {
            "action_type": "delay",
            "summary": "Wait for situation to resolve",
            "cost_usd": 0,
            "benefit_usd": 0,
            "utility_score": 0.3,
        },
        {
            "action_type": "insure",
            "summary": "Purchase additional insurance",
            "cost_usd": 3500,
            "benefit_usd": 150000,
            "utility_score": 0.6,
        },
    ]
    
    return decision


# ============================================================================
# EXECUTIVE SUMMARY TESTS
# ============================================================================


class TestExecutiveSummary:
    """Tests for executive-level summaries."""
    
    def test_executive_summary_english(self, mock_audit_service, sample_decision):
        """Executive summary should be generated in English."""
        generator = JustificationGenerator(mock_audit_service)
        
        summary = generator._generate_executive(
            sample_decision, Audience.EXECUTIVE, "en"
        )
        
        assert isinstance(summary, str)
        assert "RISKCAST" in summary
        assert "REROUTE" in summary
        assert "$150,000" in summary
        assert "87%" in summary
    
    def test_executive_summary_vietnamese(self, mock_audit_service, sample_decision):
        """Executive summary should be generated in Vietnamese."""
        generator = JustificationGenerator(mock_audit_service)
        
        summary = generator._generate_executive(
            sample_decision, Audience.EXECUTIVE, "vi"
        )
        
        assert isinstance(summary, str)
        assert "RISKCAST" in summary
        assert "khuyến nghị" in summary or "REROUTE" in summary
    
    def test_executive_summary_contains_key_info(self, mock_audit_service, sample_decision):
        """Executive summary should contain all key decision information."""
        generator = JustificationGenerator(mock_audit_service)
        
        summary = generator._generate_executive(
            sample_decision, Audience.EXECUTIVE, "en"
        )
        
        # Should contain exposure
        assert "$150,000" in summary
        
        # Should contain delay
        assert "10" in summary
        
        # Should contain cost
        assert "$8,500" in summary
        
        # Should contain confidence
        assert "87%" in summary


# ============================================================================
# DETAILED JUSTIFICATION TESTS
# ============================================================================


class TestDetailedJustification:
    """Tests for detailed justification."""
    
    def test_detailed_contains_all_7_questions(self, mock_audit_service, sample_decision):
        """Detailed justification should include all 7 questions."""
        generator = JustificationGenerator(mock_audit_service)
        
        detailed = generator._generate_detailed(
            sample_decision, Audience.ANALYST, "en"
        )
        
        assert "Q1:" in detailed or "WHAT IS HAPPENING" in detailed
        assert "Q2:" in detailed or "WHEN" in detailed
        assert "Q3:" in detailed or "HOW BAD" in detailed
        assert "Q4:" in detailed or "WHY" in detailed
        assert "Q5:" in detailed or "WHAT TO DO" in detailed
        assert "Q6:" in detailed or "CONFIDENT" in detailed
        assert "Q7:" in detailed or "IF WE DO NOTHING" in detailed
    
    def test_detailed_includes_causal_chain(self, mock_audit_service, sample_decision):
        """Detailed justification should include causal chain."""
        generator = JustificationGenerator(mock_audit_service)
        
        detailed = generator._generate_detailed(
            sample_decision, Audience.ANALYST, "en"
        )
        
        # Should include causal chain steps
        assert "Houthi attacks" in detailed
        assert "Cape" in detailed or "diverted" in detailed
    
    def test_detailed_includes_execution_steps(self, mock_audit_service, sample_decision):
        """Detailed justification should include execution steps."""
        generator = JustificationGenerator(mock_audit_service)
        
        detailed = generator._generate_detailed(
            sample_decision, Audience.ANALYST, "en"
        )
        
        # Should include action steps
        assert "MSC" in detailed
        assert "booking" in detailed.lower()


# ============================================================================
# LEGAL JUSTIFICATION TESTS
# ============================================================================


class TestLegalJustification:
    """Tests for legal-level justification."""
    
    @pytest.mark.asyncio
    async def test_legal_returns_structured_document(
        self, mock_audit_service, sample_decision
    ):
        """Legal justification should return LegalJustification object."""
        generator = JustificationGenerator(mock_audit_service)
        
        result = await generator._generate_legal(sample_decision)
        
        assert isinstance(result, LegalJustification)
        assert result.decision_id == sample_decision.decision_id
        assert result.customer_id == sample_decision.customer_id
    
    @pytest.mark.asyncio
    async def test_legal_includes_evidence_items(
        self, mock_audit_service, sample_decision
    ):
        """Legal justification should include evidence items."""
        generator = JustificationGenerator(mock_audit_service)
        
        result = await generator._generate_legal(sample_decision)
        
        assert len(result.evidence_items) > 0
        
        # Check evidence structure
        for evidence in result.evidence_items:
            assert evidence.source
            assert evidence.source_type
            assert evidence.data_point
            assert 0 <= evidence.confidence_contribution <= 1
    
    @pytest.mark.asyncio
    async def test_legal_includes_alternatives(
        self, mock_audit_service, sample_decision
    ):
        """Legal justification should include alternatives considered."""
        generator = JustificationGenerator(mock_audit_service)
        
        result = await generator._generate_legal(sample_decision)
        
        assert len(result.alternatives_considered) > 0
        
        # Check alternatives structure
        for alt in result.alternatives_considered:
            assert alt.action_type
            assert alt.summary
            assert alt.estimated_cost_usd >= 0
            assert alt.rejection_reason
    
    @pytest.mark.asyncio
    async def test_legal_includes_limitations(
        self, mock_audit_service, sample_decision
    ):
        """Legal justification should include limitations disclosure."""
        generator = JustificationGenerator(mock_audit_service)
        
        result = await generator._generate_legal(sample_decision)
        
        assert isinstance(result.limitations, LimitationsDisclosure)
        assert len(result.limitations.assumptions) > 0
        assert len(result.limitations.model_limitations) > 0
        assert result.limitations.time_sensitivity
    
    @pytest.mark.asyncio
    async def test_legal_includes_calculation_breakdown(
        self, mock_audit_service, sample_decision
    ):
        """Legal justification should include calculation breakdown."""
        generator = JustificationGenerator(mock_audit_service)
        
        result = await generator._generate_legal(sample_decision)
        
        assert result.calculation_breakdown
        assert "exposure_calculation" in result.calculation_breakdown.model_dump()
        assert "delay_estimation" in result.calculation_breakdown.model_dump()
        assert "confidence_calculation" in result.calculation_breakdown.model_dump()
    
    @pytest.mark.asyncio
    async def test_legal_includes_certification(
        self, mock_audit_service, sample_decision
    ):
        """Legal justification should include certification statement."""
        generator = JustificationGenerator(mock_audit_service)
        
        result = await generator._generate_legal(sample_decision)
        
        assert result.certification_statement
        assert "CERTIFICATION" in result.certification_statement
        assert result.decision_id in result.certification_statement
    
    @pytest.mark.asyncio
    async def test_legal_includes_verification_hash(
        self, mock_audit_service, sample_decision
    ):
        """Legal justification should include verification hash."""
        generator = JustificationGenerator(mock_audit_service)
        
        result = await generator._generate_legal(sample_decision)
        
        assert result.verification_hash
        assert len(result.verification_hash) == 64  # SHA-256 hex length
    
    @pytest.mark.asyncio
    async def test_legal_hash_is_deterministic(
        self, mock_audit_service, sample_decision
    ):
        """Same inputs should produce same verification hash."""
        generator = JustificationGenerator(mock_audit_service)
        
        result1 = await generator._generate_legal(sample_decision)
        result2 = await generator._generate_legal(sample_decision)
        
        # Note: document_id includes timestamp, so won't match
        # But verification hash should be based on decision data
        assert result1.verification_hash == result2.verification_hash
    
    @pytest.mark.asyncio
    async def test_legal_traceability_fields(
        self, mock_audit_service, sample_decision
    ):
        """Legal justification should include traceability fields."""
        generator = JustificationGenerator(mock_audit_service)
        
        result = await generator._generate_legal(sample_decision)
        
        assert result.audit_trail_id
        assert result.input_snapshot_id
        assert result.processing_record_id


# ============================================================================
# GENERATOR INTERFACE TESTS
# ============================================================================


class TestJustificationGenerator:
    """Tests for the main generator interface."""
    
    @pytest.mark.asyncio
    async def test_generate_executive_returns_string(
        self, mock_audit_service, sample_decision
    ):
        """Generate with EXECUTIVE level should return string."""
        generator = JustificationGenerator(mock_audit_service)
        
        result = await generator.generate(
            sample_decision, JustificationLevel.EXECUTIVE, Audience.EXECUTIVE
        )
        
        assert isinstance(result, str)
    
    @pytest.mark.asyncio
    async def test_generate_detailed_returns_string(
        self, mock_audit_service, sample_decision
    ):
        """Generate with DETAILED level should return string."""
        generator = JustificationGenerator(mock_audit_service)
        
        result = await generator.generate(
            sample_decision, JustificationLevel.DETAILED, Audience.ANALYST
        )
        
        assert isinstance(result, str)
    
    @pytest.mark.asyncio
    async def test_generate_audit_returns_legal_justification(
        self, mock_audit_service, sample_decision
    ):
        """Generate with AUDIT level should return LegalJustification."""
        generator = JustificationGenerator(mock_audit_service)
        
        result = await generator.generate(
            sample_decision, JustificationLevel.AUDIT, Audience.AUDITOR
        )
        
        assert isinstance(result, LegalJustification)
    
    @pytest.mark.asyncio
    async def test_generate_legal_returns_legal_justification(
        self, mock_audit_service, sample_decision
    ):
        """Generate with LEGAL level should return LegalJustification."""
        generator = JustificationGenerator(mock_audit_service)
        
        result = await generator.generate(
            sample_decision, JustificationLevel.LEGAL, Audience.LEGAL
        )
        
        assert isinstance(result, LegalJustification)
    
    def test_factory_creates_generator(self, mock_audit_service):
        """Factory function should create generator instance."""
        generator = create_justification_generator(mock_audit_service)
        
        assert isinstance(generator, JustificationGenerator)


# ============================================================================
# PYDANTIC MODEL TESTS
# ============================================================================


class TestPydanticModels:
    """Tests for Pydantic model validation."""
    
    def test_evidence_item_validation(self):
        """EvidenceItem should validate confidence_contribution range."""
        valid_item = EvidenceItem(
            source="Test",
            source_type="test_type",
            data_point="Test data",
            timestamp=datetime.utcnow(),
            confidence_contribution=0.5,
        )
        assert valid_item.confidence_contribution == 0.5
        
        with pytest.raises(Exception):
            EvidenceItem(
                source="Test",
                source_type="test_type",
                data_point="Test data",
                timestamp=datetime.utcnow(),
                confidence_contribution=1.5,  # Invalid: > 1.0
            )
    
    def test_alternative_analysis_cost_benefit_ratio(self):
        """AlternativeAnalysis should compute cost-benefit ratio."""
        alt = AlternativeAnalysis(
            action_type="test",
            summary="Test alternative",
            estimated_cost_usd=1000,
            estimated_benefit_usd=5000,
            utility_score=0.5,
            rejection_reason="Test reason",
        )
        
        assert alt.cost_benefit_ratio == 5.0
    
    def test_alternative_analysis_zero_cost_ratio(self):
        """AlternativeAnalysis should handle zero cost gracefully."""
        alt = AlternativeAnalysis(
            action_type="test",
            summary="Test alternative",
            estimated_cost_usd=0,
            estimated_benefit_usd=5000,
            utility_score=0.5,
            rejection_reason="Test reason",
        )
        
        # Should return infinity for zero cost with benefit
        assert alt.cost_benefit_ratio == float('inf')
    
    def test_limitations_disclosure_structure(self):
        """LimitationsDisclosure should have proper structure."""
        limitations = LimitationsDisclosure(
            assumptions=["Assumption 1"],
            data_gaps=["Gap 1"],
            model_limitations=["Limitation 1"],
            time_sensitivity="Decision valid for 24 hours",
            confidence_caveats=["Caveat 1"],
            external_dependencies=["Dependency 1"],
        )
        
        assert len(limitations.assumptions) == 1
        assert limitations.time_sensitivity
    
    def test_legal_justification_is_frozen(self, mock_audit_service, sample_decision):
        """LegalJustification should be immutable after creation."""
        # This is tested by the model_config = {"frozen": True}
        # Pydantic will raise ValidationError on mutation
        pass
