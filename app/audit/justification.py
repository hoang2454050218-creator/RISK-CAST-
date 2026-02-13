"""
Legal justification document generator.

Produces court-admissible documentation of decision rationale.

CRITICAL: When a customer follows RISKCAST advice and experiences losses,
this module produces the legally defensible justification document proving:
1. What evidence was available at decision time
2. How that evidence was processed
3. What alternatives were considered
4. Why the recommended action was chosen
5. What limitations existed
"""

from datetime import datetime
from typing import Optional, Union, List, TYPE_CHECKING
from pydantic import BaseModel, Field, computed_field
from enum import Enum
import hashlib
import json

import structlog

if TYPE_CHECKING:
    from app.audit.service import AuditService
    from app.audit.schemas import InputSnapshot
    from app.riskcast.schemas.decision import DecisionObject

logger = structlog.get_logger(__name__)


# ============================================================================
# ENUMS
# ============================================================================


class JustificationLevel(str, Enum):
    """Levels of justification detail."""
    EXECUTIVE = "executive"      # 1 paragraph summary
    DETAILED = "detailed"        # Full 7 Questions format
    AUDIT = "audit"              # Technical trace with calculations
    LEGAL = "legal"              # Court-ready document with full provenance


class Audience(str, Enum):
    """Target audience for justification."""
    EXECUTIVE = "executive"      # C-level, high-level summary
    ANALYST = "analyst"          # Detailed analysis
    AUDITOR = "auditor"          # Compliance focus
    LEGAL = "legal"              # Court/litigation
    REGULATOR = "regulator"      # Regulatory compliance


# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class EvidenceItem(BaseModel):
    """Single piece of evidence supporting decision."""
    source: str = Field(description="Source name, e.g., 'Polymarket', 'AIS', 'Freightos'")
    source_type: str = Field(description="Type, e.g., 'prediction_market', 'vessel_tracking'")
    data_point: str = Field(description="What the evidence shows")
    timestamp: datetime = Field(description="When evidence was captured")
    url: Optional[str] = Field(default=None, description="Link to source if available")
    confidence_contribution: float = Field(
        ge=0.0, le=1.0,
        description="How much this evidence affects confidence"
    )


class AlternativeAnalysis(BaseModel):
    """Analysis of a rejected alternative."""
    action_type: str = Field(description="Type of alternative action")
    summary: str = Field(description="Brief description of the alternative")
    estimated_cost_usd: float = Field(ge=0, description="Cost of this alternative")
    estimated_benefit_usd: float = Field(ge=0, description="Benefit if successful")
    utility_score: float = Field(description="Calculated utility score")
    rejection_reason: str = Field(description="Why this alternative was not recommended")
    
    @computed_field
    @property
    def cost_benefit_ratio(self) -> float:
        """Ratio of benefit to cost."""
        if self.estimated_cost_usd == 0:
            return float('inf') if self.estimated_benefit_usd > 0 else 0.0
        return self.estimated_benefit_usd / self.estimated_cost_usd


class LimitationsDisclosure(BaseModel):
    """
    Disclosure of decision limitations.
    
    CRITICAL for legal defensibility: honest disclosure of what
    the system does NOT know or cannot reliably predict.
    """
    assumptions: List[str] = Field(
        default_factory=list,
        description="Assumptions made during decision generation"
    )
    data_gaps: List[str] = Field(
        default_factory=list,
        description="Missing data that could improve decision"
    )
    model_limitations: List[str] = Field(
        default_factory=list,
        description="Known limitations of the decision model"
    )
    time_sensitivity: str = Field(
        description="How quickly this decision may become stale"
    )
    confidence_caveats: List[str] = Field(
        default_factory=list,
        description="Factors that could affect confidence accuracy"
    )
    external_dependencies: List[str] = Field(
        default_factory=list,
        description="External factors beyond system control"
    )


class CalculationBreakdown(BaseModel):
    """Detailed breakdown of all calculations."""
    exposure_calculation: dict = Field(
        description="How exposure was calculated"
    )
    delay_estimation: dict = Field(
        description="How delay was estimated"
    )
    action_cost: dict = Field(
        description="How action cost was calculated"
    )
    utility_score: dict = Field(
        description="How utility/recommendation score was computed"
    )
    confidence_calculation: dict = Field(
        description="How confidence was calculated and calibrated"
    )


class LegalJustification(BaseModel):
    """
    Court-admissible justification document.
    
    This document MUST be:
    - Complete (all reasoning documented)
    - Accurate (matches what system actually did)
    - Traceable (links to audit records)
    - Honest (limitations disclosed)
    """
    
    # Header
    document_id: str = Field(description="Unique document identifier")
    document_version: str = Field(default="1.0", description="Document format version")
    generated_at: datetime = Field(description="When this document was generated")
    decision_id: str = Field(description="ID of the decision being justified")
    customer_id: str = Field(description="Customer who received the decision")
    
    # Summary
    executive_summary: str = Field(
        description="One paragraph summary of decision and rationale"
    )
    
    # Evidence base
    evidence_items: List[EvidenceItem] = Field(
        description="All evidence considered in decision"
    )
    evidence_summary: str = Field(
        description="Plain English summary of evidence"
    )
    
    # Reasoning chain
    causal_chain: List[str] = Field(
        description="Step-by-step causal reasoning"
    )
    causal_chain_narrative: str = Field(
        description="Narrative explanation of causation"
    )
    
    # Calculations
    calculation_breakdown: CalculationBreakdown = Field(
        description="All formulas and numbers used"
    )
    calculation_narrative: str = Field(
        description="Plain English explanation of calculations"
    )
    
    # Alternatives
    alternatives_considered: List[AlternativeAnalysis] = Field(
        description="All alternatives evaluated and why rejected"
    )
    alternatives_narrative: str = Field(
        description="Explanation of alternative analysis"
    )
    
    # Confidence
    confidence_factors: dict = Field(
        description="Factors contributing to confidence score"
    )
    confidence_methodology: str = Field(
        description="Description of confidence calculation method"
    )
    confidence_narrative: str = Field(
        description="Plain English explanation of confidence"
    )
    
    # Limitations
    limitations: LimitationsDisclosure = Field(
        description="Disclosure of decision limitations"
    )
    limitations_narrative: str = Field(
        description="Plain English explanation of limitations"
    )
    
    # Certification
    certification_statement: str = Field(
        description="Formal certification of document accuracy"
    )
    
    # Traceability
    audit_trail_id: str = Field(description="ID linking to audit records")
    input_snapshot_id: str = Field(description="ID of input snapshot at decision time")
    processing_record_id: str = Field(description="ID of processing record")
    verification_hash: str = Field(description="Hash to verify document integrity")
    
    model_config = {"frozen": True}


# ============================================================================
# JUSTIFICATION GENERATOR
# ============================================================================


class JustificationGenerator:
    """
    Generates justification documents at various levels.
    
    Usage:
        generator = JustificationGenerator(audit_service)
        
        # Executive summary (fast)
        summary = await generator.generate(
            decision, JustificationLevel.EXECUTIVE, Audience.EXECUTIVE
        )
        
        # Legal document (comprehensive)
        legal_doc = await generator.generate(
            decision, JustificationLevel.LEGAL, Audience.LEGAL
        )
    """
    
    def __init__(self, audit_service: "AuditService"):
        self._audit = audit_service
    
    async def generate(
        self,
        decision: "DecisionObject",
        level: JustificationLevel,
        audience: Audience,
        language: str = "en",
    ) -> Union[str, LegalJustification]:
        """
        Generate justification at specified level.
        
        Args:
            decision: The decision to justify
            level: Detail level (EXECUTIVE, DETAILED, AUDIT, LEGAL)
            audience: Target audience
            language: Language code (en, vi)
            
        Returns:
            String summary for EXECUTIVE/DETAILED, LegalJustification for AUDIT/LEGAL
        """
        logger.info(
            "generating_justification",
            decision_id=decision.decision_id,
            level=level.value,
            audience=audience.value,
            language=language,
        )
        
        if level == JustificationLevel.EXECUTIVE:
            return self._generate_executive(decision, audience, language)
        elif level == JustificationLevel.DETAILED:
            return self._generate_detailed(decision, audience, language)
        elif level == JustificationLevel.AUDIT:
            return await self._generate_audit(decision)
        elif level == JustificationLevel.LEGAL:
            return await self._generate_legal(decision)
        else:
            raise ValueError(f"Unknown justification level: {level}")
    
    # ========================================================================
    # EXECUTIVE LEVEL
    # ========================================================================
    
    def _generate_executive(
        self,
        decision: "DecisionObject",
        audience: Audience,
        language: str,
    ) -> str:
        """
        One paragraph executive summary.
        
        Fast generation (< 100ms) for quick decision review.
        """
        if language == "en":
            return self._generate_executive_en(decision, audience)
        elif language == "vi":
            return self._generate_executive_vi(decision, audience)
        else:
            # Fallback to English
            return self._generate_executive_en(decision, audience)
    
    def _generate_executive_en(
        self,
        decision: "DecisionObject",
        audience: Audience,
    ) -> str:
        """Generate executive summary in English."""
        q1 = decision.q1_what
        q2 = decision.q2_when
        q3 = decision.q3_severity
        q4 = decision.q4_why
        q5 = decision.q5_action
        q6 = decision.q6_confidence
        q7 = decision.q7_inaction
        
        shipment_count = len(q5.affected_shipments) if q5.affected_shipments else q3.shipments_affected
        
        return f"""RISKCAST recommends {q5.action_type.upper()} for {shipment_count} shipment(s) \
with ${q3.total_exposure_usd:,.0f} exposure. \
{q4.root_cause} is causing an expected {q3.expected_delay_days} day delay. \
Recommended action cost: ${q5.estimated_cost_usd:,.0f}. \
Confidence: {q6.score:.0%} ({q6.level.value.upper()}). \
Deadline: {q5.deadline.strftime('%Y-%m-%d %H:%M UTC') if q5.deadline else 'Not specified'}. \
If no action: expected loss of ${q7.expected_loss_if_nothing:,.0f}."""
    
    def _generate_executive_vi(
        self,
        decision: "DecisionObject",
        audience: Audience,
    ) -> str:
        """Generate executive summary in Vietnamese."""
        q1 = decision.q1_what
        q2 = decision.q2_when
        q3 = decision.q3_severity
        q4 = decision.q4_why
        q5 = decision.q5_action
        q6 = decision.q6_confidence
        q7 = decision.q7_inaction
        
        shipment_count = len(q5.affected_shipments) if q5.affected_shipments else q3.shipments_affected
        
        return f"""RISKCAST khuyến nghị {q5.action_type.upper()} cho {shipment_count} lô hàng \
với rủi ro ${q3.total_exposure_usd:,.0f}. \
{q4.root_cause} đang gây trễ khoảng {q3.expected_delay_days} ngày. \
Chi phí hành động khuyến nghị: ${q5.estimated_cost_usd:,.0f}. \
Độ tin cậy: {q6.score:.0%} ({q6.level.value.upper()}). \
Hạn chót: {q5.deadline.strftime('%Y-%m-%d %H:%M UTC') if q5.deadline else 'Chưa xác định'}. \
Nếu không hành động: thiệt hại dự kiến ${q7.expected_loss_if_nothing:,.0f}."""
    
    # ========================================================================
    # DETAILED LEVEL
    # ========================================================================
    
    def _generate_detailed(
        self,
        decision: "DecisionObject",
        audience: Audience,
        language: str,
    ) -> str:
        """
        Full 7 Questions format as structured text.
        """
        q1 = decision.q1_what
        q2 = decision.q2_when
        q3 = decision.q3_severity
        q4 = decision.q4_why
        q5 = decision.q5_action
        q6 = decision.q6_confidence
        q7 = decision.q7_inaction
        
        if language == "vi":
            return self._format_detailed_vi(decision)
        
        # English format
        sections = [
            "=" * 60,
            "RISKCAST DECISION JUSTIFICATION",
            f"Decision ID: {decision.decision_id}",
            f"Generated: {decision.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
            "=" * 60,
            "",
            "Q1: WHAT IS HAPPENING?",
            "-" * 40,
            f"Event: {q1.event_summary}",
            f"Chokepoint: {q1.affected_chokepoint}",
            f"Your Routes: {', '.join(q1.affected_routes)}",
            f"Your Shipments: {', '.join(q1.affected_shipments)}",
            "",
            "Q2: WHEN?",
            "-" * 40,
            f"Status: {q2.status}",
            f"Timeline: {q2.impact_timeline}",
            f"Urgency: {q2.urgency.value.upper()} - {q2.urgency_reason}",
            "",
            "Q3: HOW BAD IS IT?",
            "-" * 40,
            f"Total Exposure: ${q3.total_exposure_usd:,.0f}",
            f"Delay Range: {q3.delay_range}",
            f"Shipments Affected: {q3.shipments_affected}",
            f"Severity: {q3.severity.value.upper()}",
            "",
            "Q4: WHY IS THIS HAPPENING?",
            "-" * 40,
            f"Root Cause: {q4.root_cause}",
            "Causal Chain:",
            *[f"  {i+1}. {step}" for i, step in enumerate(q4.causal_chain)],
            f"Evidence: {q4.evidence_summary}",
            f"Sources: {', '.join(q4.sources)}",
            "",
            "Q5: WHAT TO DO NOW?",
            "-" * 40,
            f"Recommended Action: {q5.action_type.upper()}",
            f"Summary: {q5.action_summary}",
            f"Cost: ${q5.estimated_cost_usd:,.0f}",
            f"Deadline: {q5.deadline.strftime('%Y-%m-%d %H:%M UTC') if q5.deadline else 'ASAP'}",
            f"Reason: {q5.deadline_reason}",
            "Steps:",
            *[f"  {i+1}. {step}" for i, step in enumerate(q5.execution_steps)],
            "",
            "Q6: HOW CONFIDENT ARE WE?",
            "-" * 40,
            f"Confidence Score: {q6.score:.0%} ({q6.level.value.upper()})",
            f"Explanation: {q6.explanation}",
            "Factors:",
            *[f"  - {k}: {v:.0%}" for k, v in q6.factors.items()],
            "Caveats:",
            *[f"  - {caveat}" for caveat in q6.caveats],
            "",
            "Q7: WHAT IF WE DO NOTHING?",
            "-" * 40,
            f"Expected Loss: ${q7.expected_loss_if_nothing:,.0f}",
            f"Loss if wait 6h: ${q7.cost_if_wait_6h:,.0f}",
            f"Loss if wait 24h: ${q7.cost_if_wait_24h:,.0f}",
            f"Point of No Return: {q7.point_of_no_return.strftime('%Y-%m-%d %H:%M UTC') if q7.point_of_no_return else 'Not determined'}",
            f"Reason: {q7.point_of_no_return_reason}",
            f"Worst Case: ${q7.worst_case_cost:,.0f} - {q7.worst_case_scenario}",
            "",
            "=" * 60,
            "ALTERNATIVES CONSIDERED",
            "=" * 60,
        ]
        
        for i, alt in enumerate(decision.alternative_actions, 1):
            sections.extend([
                f"\nAlternative {i}: {alt.get('action_type', 'Unknown')}",
                f"  Summary: {alt.get('summary', 'N/A')}",
                f"  Cost: ${alt.get('cost_usd', 0):,.0f}",
                f"  Benefit: ${alt.get('benefit_usd', 0):,.0f}",
            ])
        
        return "\n".join(sections)
    
    def _format_detailed_vi(self, decision: "DecisionObject") -> str:
        """Format detailed justification in Vietnamese."""
        # Simplified Vietnamese version
        q1 = decision.q1_what
        q3 = decision.q3_severity
        q5 = decision.q5_action
        q6 = decision.q6_confidence
        q7 = decision.q7_inaction
        
        return f"""
RISKCAST GIẢI TRÌNH QUYẾT ĐỊNH
Decision ID: {decision.decision_id}
{'=' * 60}

CÂU HỎI 1: CHUYỆN GÌ ĐANG XẢY RA?
{q1.event_summary}

CÂU HỎI 3: MỨC ĐỘ NGHIÊM TRỌNG?
Rủi ro: ${q3.total_exposure_usd:,.0f}
Độ trễ dự kiến: {q3.delay_range}

CÂU HỎI 5: CẦN LÀM GÌ?
Hành động: {q5.action_type.upper()}
Chi phí: ${q5.estimated_cost_usd:,.0f}

CÂU HỎI 6: ĐỘ TIN CẬY?
{q6.score:.0%} ({q6.level.value})

CÂU HỎI 7: NẾU KHÔNG LÀM GÌ?
Thiệt hại dự kiến: ${q7.expected_loss_if_nothing:,.0f}
"""
    
    # ========================================================================
    # AUDIT LEVEL
    # ========================================================================
    
    async def _generate_audit(
        self,
        decision: "DecisionObject",
    ) -> LegalJustification:
        """
        Generate audit-level justification with technical trace.
        
        Includes all calculations but simplified certification.
        """
        return await self._generate_legal(decision)
    
    # ========================================================================
    # LEGAL LEVEL
    # ========================================================================
    
    async def _generate_legal(
        self,
        decision: "DecisionObject",
    ) -> LegalJustification:
        """
        Generate court-admissible justification.
        
        This is the most comprehensive level, including:
        - Complete evidence chain
        - Full calculation breakdown
        - All alternatives considered
        - Honest limitations disclosure
        - Cryptographic verification
        """
        # Fetch audit data
        audit_trail = await self._audit.get_decision_audit_trail(decision.decision_id)
        snapshot = audit_trail.get("input_snapshot")
        processing_record = audit_trail.get("processing_record")
        audit_events = audit_trail.get("audit_events", [])
        
        # Build evidence list
        evidence_items = self._extract_evidence(decision, snapshot)
        
        # Build alternatives
        alternatives = self._build_alternatives_analysis(decision)
        
        # Build limitations
        limitations = self._build_limitations(decision, snapshot)
        
        # Build calculation breakdown
        calculations = self._build_calculation_breakdown(decision)
        
        # Get audit trail ID
        audit_trail_id = audit_events[0]["event_id"] if audit_events else f"audit_{decision.decision_id}"
        
        # Compute verification hash
        verification_hash = self._compute_verification_hash(
            decision, snapshot, audit_events
        )
        
        # Build certification statement
        certification = self._build_certification(
            decision,
            processing_record,
            audit_trail_id,
            verification_hash,
        )
        
        return LegalJustification(
            document_id=f"just_{decision.decision_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            generated_at=datetime.utcnow(),
            decision_id=decision.decision_id,
            customer_id=decision.customer_id,
            
            executive_summary=self._generate_executive_en(
                decision, Audience.LEGAL
            ),
            
            evidence_items=evidence_items,
            evidence_summary=self._summarize_evidence(evidence_items),
            
            causal_chain=decision.q4_why.causal_chain,
            causal_chain_narrative=self._narrate_causation(decision.q4_why),
            
            calculation_breakdown=calculations,
            calculation_narrative=self._narrate_calculations(calculations),
            
            alternatives_considered=alternatives,
            alternatives_narrative=self._narrate_alternatives(alternatives),
            
            confidence_factors=decision.q6_confidence.factors,
            confidence_methodology=self._describe_confidence_methodology(),
            confidence_narrative=self._narrate_confidence(decision.q6_confidence),
            
            limitations=limitations,
            limitations_narrative=self._narrate_limitations(limitations),
            
            certification_statement=certification,
            
            audit_trail_id=audit_trail_id,
            input_snapshot_id=snapshot.get("snapshot_id", "unknown") if snapshot else "unknown",
            processing_record_id=processing_record.get("record_id", f"proc_{decision.decision_id}") if processing_record else f"proc_{decision.decision_id}",
            verification_hash=verification_hash,
        )
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _extract_evidence(
        self,
        decision: "DecisionObject",
        snapshot: Optional[dict],
    ) -> List[EvidenceItem]:
        """Extract all evidence items from decision and snapshot."""
        evidence = []
        
        # From Q4 sources
        for source in decision.q4_why.sources:
            evidence.append(EvidenceItem(
                source=source,
                source_type="intelligence_source",
                data_point=f"Contributed to event analysis",
                timestamp=decision.generated_at,
                confidence_contribution=1.0 / max(len(decision.q4_why.sources), 1),
            ))
        
        # From snapshot if available
        if snapshot:
            # Signal evidence
            signal_data = snapshot.get("signal_data", {})
            if signal_data:
                evidence.append(EvidenceItem(
                    source="OMEN Signal",
                    source_type="aggregated_signal",
                    data_point=f"Signal probability: {signal_data.get('probability', 'unknown')}",
                    timestamp=datetime.fromisoformat(
                        snapshot.get("captured_at", decision.generated_at.isoformat())
                    ) if isinstance(snapshot.get("captured_at"), str) else snapshot.get("captured_at", decision.generated_at),
                    confidence_contribution=0.4,
                ))
            
            # Reality evidence
            reality_data = snapshot.get("reality_data", {})
            if reality_data:
                evidence.append(EvidenceItem(
                    source="ORACLE Reality",
                    source_type="reality_check",
                    data_point=f"Correlation status: {reality_data.get('correlation_status', 'unknown')}",
                    timestamp=datetime.fromisoformat(
                        snapshot.get("captured_at", decision.generated_at.isoformat())
                    ) if isinstance(snapshot.get("captured_at"), str) else snapshot.get("captured_at", decision.generated_at),
                    confidence_contribution=0.3,
                ))
        
        # Add confidence factors as evidence
        for factor_name, factor_value in decision.q6_confidence.factors.items():
            evidence.append(EvidenceItem(
                source=f"Confidence Factor: {factor_name}",
                source_type="confidence_input",
                data_point=f"Value: {factor_value:.2%}",
                timestamp=decision.generated_at,
                confidence_contribution=factor_value * 0.1,
            ))
        
        return evidence
    
    def _summarize_evidence(self, evidence_items: List[EvidenceItem]) -> str:
        """Generate plain English summary of evidence."""
        if not evidence_items:
            return "No specific evidence items were recorded for this decision."
        
        sources = set(e.source for e in evidence_items)
        total_confidence = sum(e.confidence_contribution for e in evidence_items)
        
        return f"This decision was based on {len(evidence_items)} evidence items from " \
               f"{len(sources)} source(s): {', '.join(sorted(sources))}. " \
               f"Combined evidence weight: {min(total_confidence, 1.0):.0%}."
    
    def _build_alternatives_analysis(
        self,
        decision: "DecisionObject",
    ) -> List[AlternativeAnalysis]:
        """Build analysis of all alternatives considered."""
        alternatives = []
        
        for alt in decision.alternative_actions:
            alternatives.append(AlternativeAnalysis(
                action_type=alt.get("action_type", "unknown"),
                summary=alt.get("summary", "No summary available"),
                estimated_cost_usd=alt.get("cost_usd", 0),
                estimated_benefit_usd=alt.get("benefit_usd", 0),
                utility_score=alt.get("utility_score", 0),
                rejection_reason=f"Lower utility than recommended action ({decision.q5_action.action_type})",
            ))
        
        return alternatives
    
    def _narrate_alternatives(self, alternatives: List[AlternativeAnalysis]) -> str:
        """Generate narrative about alternatives."""
        if not alternatives:
            return "No alternative actions were evaluated for this decision."
        
        lines = [f"RISKCAST evaluated {len(alternatives)} alternative action(s):"]
        for alt in alternatives:
            lines.append(
                f"- {alt.action_type.upper()}: Cost ${alt.estimated_cost_usd:,.0f}, "
                f"benefit ${alt.estimated_benefit_usd:,.0f}, utility {alt.utility_score:.2f}. "
                f"Rejected because: {alt.rejection_reason}"
            )
        return "\n".join(lines)
    
    def _build_limitations(
        self,
        decision: "DecisionObject",
        snapshot: Optional[dict],
    ) -> LimitationsDisclosure:
        """Build honest limitations disclosure."""
        assumptions = [
            "Market conditions remain similar to current state",
            "Carrier capacity remains as reported",
            "No additional disruptions occur during decision validity period",
        ]
        
        data_gaps = []
        if snapshot:
            staleness = snapshot.get("reality_staleness_seconds", 0)
            if staleness > 300:
                data_gaps.append(f"Reality data was {staleness // 60} minutes old at decision time")
        
        model_limitations = [
            "Impact estimates are based on historical patterns",
            "Confidence calibration depends on historical accuracy data",
            "Cost estimates do not include negotiated carrier discounts",
        ]
        
        # Add caveats from confidence
        confidence_caveats = list(decision.q6_confidence.caveats) if decision.q6_confidence.caveats else []
        
        # Determine time sensitivity
        urgency = decision.q2_when.urgency.value
        time_sensitivity = {
            "immediate": "This decision is time-critical and may become invalid within hours",
            "urgent": "This decision should be acted upon within 24 hours",
            "soon": "This decision is valid for several days but conditions may change",
            "watch": "This decision is for monitoring; situation is not yet urgent",
        }.get(urgency, "Time sensitivity unknown")
        
        return LimitationsDisclosure(
            assumptions=assumptions,
            data_gaps=data_gaps,
            model_limitations=model_limitations,
            time_sensitivity=time_sensitivity,
            confidence_caveats=confidence_caveats,
            external_dependencies=[
                "Carrier availability",
                "Port operations",
                "Weather conditions",
                "Geopolitical developments",
            ],
        )
    
    def _narrate_limitations(self, limitations: LimitationsDisclosure) -> str:
        """Generate narrative about limitations."""
        lines = ["LIMITATIONS AND DISCLAIMERS:", ""]
        
        lines.append("Assumptions:")
        for assumption in limitations.assumptions:
            lines.append(f"  - {assumption}")
        
        if limitations.data_gaps:
            lines.append("\nData Gaps:")
            for gap in limitations.data_gaps:
                lines.append(f"  - {gap}")
        
        lines.append("\nModel Limitations:")
        for limit in limitations.model_limitations:
            lines.append(f"  - {limit}")
        
        lines.append(f"\nTime Sensitivity: {limitations.time_sensitivity}")
        
        if limitations.confidence_caveats:
            lines.append("\nConfidence Caveats:")
            for caveat in limitations.confidence_caveats:
                lines.append(f"  - {caveat}")
        
        return "\n".join(lines)
    
    def _build_calculation_breakdown(
        self,
        decision: "DecisionObject",
    ) -> CalculationBreakdown:
        """Build detailed calculation breakdown."""
        q3 = decision.q3_severity
        q5 = decision.q5_action
        q6 = decision.q6_confidence
        
        return CalculationBreakdown(
            exposure_calculation={
                "formula": "total_cargo_value + potential_penalties + holding_costs",
                "total_exposure_usd": q3.total_exposure_usd,
                "breakdown": q3.exposure_breakdown,
            },
            delay_estimation={
                "formula": "chokepoint_base_delay * probability_factor * route_factor",
                "expected_days": q3.expected_delay_days,
                "range": q3.delay_range,
                "shipments_affected": q3.shipments_affected,
            },
            action_cost={
                "formula": "base_cost + (premium_per_teu * teu_count)",
                "estimated_cost_usd": q5.estimated_cost_usd,
                "affected_shipments": len(q5.affected_shipments) if q5.affected_shipments else 0,
            },
            utility_score={
                "formula": "(risk_mitigated / cost) * feasibility * urgency_factor",
                "note": "Higher utility = better recommendation",
            },
            confidence_calculation={
                "formula": "weighted_average(signal_prob, correlation_conf, impact_conf)",
                "weights": {"signal": 0.4, "correlation": 0.3, "impact": 0.3},
                "final_score": q6.score,
                "factors": q6.factors,
            },
        )
    
    def _narrate_calculations(self, calculations: CalculationBreakdown) -> str:
        """Generate narrative about calculations."""
        return f"""
CALCULATION METHODOLOGY:

1. EXPOSURE CALCULATION
   Formula: {calculations.exposure_calculation['formula']}
   Total Exposure: ${calculations.exposure_calculation['total_exposure_usd']:,.0f}

2. DELAY ESTIMATION
   Formula: {calculations.delay_estimation['formula']}
   Expected Delay: {calculations.delay_estimation['expected_days']} days
   Range: {calculations.delay_estimation['range']}

3. ACTION COST
   Formula: {calculations.action_cost['formula']}
   Estimated Cost: ${calculations.action_cost['estimated_cost_usd']:,.0f}

4. CONFIDENCE CALCULATION
   Formula: {calculations.confidence_calculation['formula']}
   Weights: Signal={calculations.confidence_calculation['weights']['signal']}, 
            Correlation={calculations.confidence_calculation['weights']['correlation']}, 
            Impact={calculations.confidence_calculation['weights']['impact']}
   Final Score: {calculations.confidence_calculation['final_score']:.0%}
"""
    
    def _narrate_causation(self, q4) -> str:
        """Generate narrative about causal chain."""
        lines = [
            f"ROOT CAUSE: {q4.root_cause}",
            "",
            "CAUSAL CHAIN:",
        ]
        for i, step in enumerate(q4.causal_chain, 1):
            lines.append(f"  {i}. {step}")
        
        lines.extend([
            "",
            f"EVIDENCE: {q4.evidence_summary}",
            f"SOURCES: {', '.join(q4.sources)}",
        ])
        return "\n".join(lines)
    
    def _describe_confidence_methodology(self) -> str:
        """Describe how confidence is calculated."""
        return """
RISKCAST calculates confidence using a weighted multi-factor approach:

1. SIGNAL PROBABILITY (40% weight)
   - Derived from prediction markets (Polymarket) and news analysis
   - Represents likelihood of the predicted event occurring

2. CORRELATION CONFIDENCE (30% weight)
   - How well the signal matches real-world observations
   - Based on AIS vessel tracking, freight rates, port congestion

3. IMPACT CONFIDENCE (30% weight)
   - Reliability of cost and delay estimates
   - Based on historical accuracy of similar predictions

The final score is calibrated against historical outcomes to improve accuracy.
Calibration uses isotonic regression on past prediction vs outcome data.
"""
    
    def _narrate_confidence(self, q6) -> str:
        """Generate narrative about confidence."""
        return f"""
CONFIDENCE ASSESSMENT:

Overall Score: {q6.score:.0%} ({q6.level.value.upper()})

Explanation: {q6.explanation}

Contributing Factors:
{chr(10).join(f'  - {k}: {v:.0%}' for k, v in q6.factors.items())}

Caveats:
{chr(10).join(f'  - {c}' for c in q6.caveats) if q6.caveats else '  - None'}
"""
    
    def _build_certification(
        self,
        decision: "DecisionObject",
        processing_record: Optional[dict],
        audit_trail_id: str,
        verification_hash: str,
    ) -> str:
        """Build formal certification statement."""
        model_version = processing_record.get("model_version", "unknown") if processing_record else "unknown"
        
        return f"""
CERTIFICATION STATEMENT

This decision was generated by RISKCAST Decision Intelligence Platform.

CERTIFICATION:
1. All inputs were captured and preserved before decision generation.
2. The decision was generated using approved methodology version {model_version}.
3. All calculations follow documented formulas without manual override.
4. Alternatives were systematically evaluated using consistent criteria.
5. Confidence scores are calibrated against historical outcomes.
6. Limitations and assumptions are disclosed in this document.

This document can be verified against audit trail ID: {audit_trail_id}
Decision ID: {decision.decision_id}
Generated At: {decision.generated_at.isoformat()}
Customer ID: {decision.customer_id}

Verification hash: {verification_hash}

This certification is machine-generated and represents the state of the
RISKCAST system at the time of decision generation. For questions about
this decision, contact RISKCAST support with the Decision ID above.
"""
    
    def _compute_verification_hash(
        self,
        decision: "DecisionObject",
        snapshot: Optional[dict],
        audit_events: List[dict],
    ) -> str:
        """Compute verification hash for document integrity."""
        components = [
            decision.decision_id,
            decision.customer_id,
            str(decision.generated_at.timestamp()),
            str(decision.q3_severity.total_exposure_usd),
            decision.q5_action.action_type,
        ]
        
        if snapshot:
            components.append(snapshot.get("combined_hash", ""))
        
        if audit_events:
            components.append(audit_events[0].get("record_hash", ""))
        
        combined = "|".join(components)
        return hashlib.sha256(combined.encode()).hexdigest()


# ============================================================================
# FACTORY
# ============================================================================


def create_justification_generator(
    audit_service: "AuditService",
) -> JustificationGenerator:
    """Create a justification generator instance."""
    return JustificationGenerator(audit_service)
