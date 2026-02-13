"""
AI Governance Policy Implementation.

Compliant with EU AI Act and internal governance requirements.

EU AI Act Classification:
- RISKCAST is classified as LIMITED RISK (not high-risk)
- Transparency obligations apply
- Human oversight required for high-value decisions

This module provides:
- Risk classification per EU AI Act
- Governance policy definition
- Runtime policy enforcement
- Compliance reporting

Addresses audit gap C4.1 (AI Governance): +14 points target
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from pydantic import BaseModel, Field, computed_field
from enum import Enum

import structlog

if TYPE_CHECKING:
    from app.riskcast.schemas.decision import DecisionObject

logger = structlog.get_logger(__name__)


# ============================================================================
# ENUMS
# ============================================================================


class AIRiskLevel(str, Enum):
    """
    EU AI Act risk classification.
    
    Reference: EU AI Act Article 6 & Annex III
    """
    UNACCEPTABLE = "unacceptable"  # Banned (social scoring, manipulation)
    HIGH = "high"                   # Requires conformity assessment
    LIMITED = "limited"             # Transparency obligations only
    MINIMAL = "minimal"             # No specific requirements


class ModelPurpose(str, Enum):
    """Model purpose classification for governance tracking."""
    DECISION_RECOMMENDATION = "decision_recommendation"
    RISK_ASSESSMENT = "risk_assessment"
    OUTCOME_PREDICTION = "outcome_prediction"
    DATA_AGGREGATION = "data_aggregation"
    SIGNAL_PROCESSING = "signal_processing"
    CALIBRATION = "calibration"


class OversightRequirement(str, Enum):
    """Types of human oversight requirements."""
    HUMAN_IN_THE_LOOP = "human_in_the_loop"      # Human must approve before action
    HUMAN_ON_THE_LOOP = "human_on_the_loop"      # Human monitors, can intervene
    HUMAN_IN_COMMAND = "human_in_command"        # Human can override at any time


# ============================================================================
# POLICY SCHEMAS
# ============================================================================


class HumanOversightPolicy(BaseModel):
    """Human oversight requirements per EU AI Act Article 14."""
    
    requirement_type: OversightRequirement = Field(
        default=OversightRequirement.HUMAN_ON_THE_LOOP,
        description="Type of human oversight required",
    )
    
    # Value-based thresholds
    value_threshold_for_review: float = Field(
        default=500000.0,
        ge=0,
        description="USD value above which human review is mandatory",
    )
    
    # Confidence-based thresholds
    confidence_threshold_for_auto: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for automated recommendations",
    )
    
    low_confidence_threshold: float = Field(
        default=0.50,
        ge=0.0,
        le=1.0,
        description="Confidence below this always requires human review",
    )
    
    # Escalation rules
    escalation_timeout_hours: int = Field(
        default=4,
        ge=1,
        description="Hours before unreviewed high-value decisions escalate",
    )
    
    # Override capability
    user_override_always_available: bool = Field(
        default=True,
        description="Users can always override AI recommendations",
    )


class TransparencyPolicy(BaseModel):
    """Transparency requirements per EU AI Act Article 52."""
    
    # Disclosure requirements
    ai_disclosure_required: bool = Field(
        default=True,
        description="Must disclose that system is AI-powered",
    )
    
    # Explainability requirements
    explanation_required: bool = Field(
        default=True,
        description="All decisions must include explanation",
    )
    
    causal_chain_required: bool = Field(
        default=True,
        description="Decisions must include causal reasoning",
    )
    
    confidence_disclosure_required: bool = Field(
        default=True,
        description="Confidence scores must be disclosed",
    )
    
    limitations_disclosure_required: bool = Field(
        default=True,
        description="System limitations must be documented",
    )


class FairnessPolicy(BaseModel):
    """Fairness and non-discrimination requirements."""
    
    bias_monitoring_required: bool = Field(
        default=True,
        description="Regular bias monitoring is mandatory",
    )
    
    monitoring_frequency: str = Field(
        default="quarterly",
        description="How often fairness audits are conducted",
    )
    
    # Protected characteristics
    protected_attributes: List[str] = Field(
        default=["customer_size", "region", "industry"],
        description="Attributes monitored for bias",
    )
    
    # Thresholds
    disparate_impact_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Minimum ratio for demographic parity (80% rule)",
    )
    
    accuracy_parity_threshold: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Minimum accuracy ratio across groups",
    )


class DataGovernancePolicy(BaseModel):
    """Data governance requirements per EU AI Act & GDPR."""
    
    # Data minimization
    purpose_limitation: bool = Field(
        default=True,
        description="Data used only for stated purposes",
    )
    
    data_minimization: bool = Field(
        default=True,
        description="Collect only necessary data",
    )
    
    # Retention
    decision_retention_days: int = Field(
        default=365 * 3,  # 3 years
        description="How long decision records are retained",
    )
    
    audit_log_retention_days: int = Field(
        default=365 * 7,  # 7 years
        description="How long audit logs are retained",
    )
    
    # Rights
    right_to_explanation: bool = Field(
        default=True,
        description="Users can request decision explanations",
    )
    
    right_to_human_review: bool = Field(
        default=True,
        description="Users can request human review of decisions",
    )


class GovernancePolicy(BaseModel):
    """
    Complete AI Governance Policy document.
    
    This is the master policy that governs all AI/ML systems in RISKCAST.
    Compliant with EU AI Act requirements.
    """
    
    # Identity
    policy_id: str = Field(
        default="RISKCAST-GOV-001",
        description="Unique policy identifier",
    )
    version: str = Field(
        default="1.0.0",
        description="Policy version",
    )
    
    # Dates
    effective_date: datetime = Field(
        default_factory=lambda: datetime(2026, 2, 1),
        description="When policy became effective",
    )
    last_review: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last review date",
    )
    next_review: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(days=90),
        description="Next scheduled review",
    )
    
    # Scope
    applicable_systems: List[str] = Field(
        default=[
            "RISKCAST Decision Engine",
            "OMEN Signal Processing",
            "ORACLE Reality Monitoring",
            "Uncertainty Quantification",
            "Calibration System",
        ],
        description="Systems covered by this policy",
    )
    
    # EU AI Act Classification
    risk_classification: AIRiskLevel = Field(
        default=AIRiskLevel.LIMITED,
        description="EU AI Act risk level",
    )
    
    risk_classification_rationale: str = Field(
        default=(
            "RISKCAST is classified as LIMITED RISK because: "
            "(1) It provides recommendations, not autonomous actions; "
            "(2) Humans make final decisions; "
            "(3) Not used for critical infrastructure, employment, or essential services; "
            "(4) Transparency obligations are met through 7 Questions framework."
        ),
        description="Justification for risk classification",
    )
    
    # Core Principles
    principles: List[str] = Field(
        default=[
            "Transparency: All decisions must be explainable via 7 Questions framework",
            "Fairness: No discrimination based on customer size, region, or other protected characteristics",
            "Accountability: Complete audit trail for all decisions with human oversight",
            "Privacy: Minimal data collection with purpose limitation per GDPR",
            "Safety: Fail-safe mechanisms with conservative fallbacks for all critical paths",
            "Human Agency: Users can always override AI recommendations",
            "Beneficence: Recommendations must provide net positive value to customers",
        ],
        description="Core governance principles",
    )
    
    # Sub-policies
    human_oversight: HumanOversightPolicy = Field(
        default_factory=HumanOversightPolicy,
        description="Human oversight requirements",
    )
    
    transparency: TransparencyPolicy = Field(
        default_factory=TransparencyPolicy,
        description="Transparency requirements",
    )
    
    fairness: FairnessPolicy = Field(
        default_factory=FairnessPolicy,
        description="Fairness requirements",
    )
    
    data_governance: DataGovernancePolicy = Field(
        default_factory=DataGovernancePolicy,
        description="Data governance requirements",
    )
    
    # Governance Structure
    ai_ethics_board: List[str] = Field(
        default=[
            "Chief Technology Officer",
            "Chief Risk Officer",
            "Head of Legal & Compliance",
            "External Ethics Advisor",
        ],
        description="AI Ethics Board members",
    )
    
    model_owners: Dict[str, str] = Field(
        default={
            "riskcast-decision-v2": "Decision Team Lead",
            "omen-signal-processor": "Signal Team Lead",
            "oracle-correlator": "Reality Team Lead",
            "uncertainty-bayesian": "Analytics Team Lead",
            "calibration-system": "Quality Team Lead",
        },
        description="Model ownership assignments",
    )
    
    review_cadence: str = Field(
        default="quarterly",
        description="Policy review frequency",
    )
    
    @computed_field
    @property
    def is_due_for_review(self) -> bool:
        """Check if policy review is overdue."""
        return datetime.utcnow() > self.next_review


# ============================================================================
# COMPLIANCE REPORTING
# ============================================================================


class PolicyViolation(BaseModel):
    """A specific policy violation."""
    
    violation_id: str
    severity: str = Field(description="CRITICAL, HIGH, MEDIUM, LOW")
    policy_section: str
    description: str
    decision_id: Optional[str] = None
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    remediation: Optional[str] = None


class PolicyComplianceReport(BaseModel):
    """Compliance check result for a decision."""
    
    decision_id: str
    checked_at: datetime = Field(default_factory=datetime.utcnow)
    policy_version: str
    
    # Overall result
    compliant: bool
    compliance_score: float = Field(ge=0.0, le=1.0)
    
    # Details
    violations: List[PolicyViolation] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    passed_checks: List[str] = Field(default_factory=list)
    
    # Metadata
    human_review_required: bool = False
    human_review_reason: Optional[str] = None
    auto_execution_allowed: bool = True
    
    @computed_field
    @property
    def violation_count(self) -> int:
        """Number of violations."""
        return len(self.violations)
    
    @computed_field
    @property
    def has_critical_violations(self) -> bool:
        """Check for critical violations."""
        return any(v.severity == "CRITICAL" for v in self.violations)


# ============================================================================
# POLICY ENFORCER
# ============================================================================


class PolicyEnforcer:
    """
    Enforces AI governance policy at runtime.
    
    Every decision goes through policy checks before being delivered.
    This ensures compliance with EU AI Act and internal governance requirements.
    """
    
    def __init__(self, policy: Optional[GovernancePolicy] = None):
        """
        Initialize policy enforcer.
        
        Args:
            policy: Governance policy to enforce. Uses default if not provided.
        """
        self.policy = policy or get_default_policy()
        self._violation_count = 0
    
    def check_decision(
        self,
        decision: "DecisionObject",
        customer_context: Optional[Dict[str, Any]] = None,
    ) -> PolicyComplianceReport:
        """
        Check if decision complies with governance policy.
        
        Args:
            decision: The decision to check
            customer_context: Additional customer context for fairness checks
            
        Returns:
            PolicyComplianceReport with compliance status and any violations
        """
        violations = []
        warnings = []
        passed_checks = []
        human_review_required = False
        human_review_reason = None
        auto_execution_allowed = True
        
        # ====================================================================
        # CHECK 1: Human Oversight Requirements
        # ====================================================================
        exposure = decision.q3_severity.total_exposure_usd
        confidence = decision.q6_confidence.score
        
        # High-value decision check
        if exposure > self.policy.human_oversight.value_threshold_for_review:
            human_review_required = True
            human_review_reason = (
                f"High-value decision (${exposure:,.0f}) exceeds review threshold "
                f"(${self.policy.human_oversight.value_threshold_for_review:,.0f})"
            )
            
            # Check if human reviewed (if field exists)
            if hasattr(decision, 'human_reviewed') and not decision.human_reviewed:
                violations.append(PolicyViolation(
                    violation_id=f"HO-001-{decision.decision_id}",
                    severity="HIGH",
                    policy_section="human_oversight.value_threshold",
                    description=human_review_reason,
                    decision_id=decision.decision_id,
                    remediation="Route to human reviewer before delivery",
                ))
            else:
                passed_checks.append("High-value decision flagged for review")
        else:
            passed_checks.append("Value within auto-approval threshold")
        
        # Low confidence check
        if confidence < self.policy.human_oversight.low_confidence_threshold:
            human_review_required = True
            auto_execution_allowed = False
            
            if human_review_reason:
                human_review_reason += f"; Low confidence ({confidence:.0%})"
            else:
                human_review_reason = f"Low confidence ({confidence:.0%}) below threshold"
            
            warnings.append(
                f"Confidence {confidence:.0%} below threshold "
                f"({self.policy.human_oversight.low_confidence_threshold:.0%})"
            )
        elif confidence < self.policy.human_oversight.confidence_threshold_for_auto:
            warnings.append(
                f"Confidence {confidence:.0%} below auto-action threshold "
                f"({self.policy.human_oversight.confidence_threshold_for_auto:.0%})"
            )
            auto_execution_allowed = False
        else:
            passed_checks.append("Confidence within acceptable range")
        
        # ====================================================================
        # CHECK 2: Transparency Requirements
        # ====================================================================
        if self.policy.transparency.explanation_required:
            if not decision.q4_why or not decision.q4_why.root_cause:
                violations.append(PolicyViolation(
                    violation_id=f"TR-001-{decision.decision_id}",
                    severity="MEDIUM",
                    policy_section="transparency.explanation_required",
                    description="Decision lacks root cause explanation",
                    decision_id=decision.decision_id,
                    remediation="Add explanation to Q4 (Why)",
                ))
            else:
                passed_checks.append("Root cause explanation present")
        
        if self.policy.transparency.causal_chain_required:
            if not decision.q4_why or not decision.q4_why.causal_chain:
                warnings.append("Decision lacks causal chain explanation")
            else:
                passed_checks.append("Causal chain present")
        
        if self.policy.transparency.confidence_disclosure_required:
            if not decision.q6_confidence or decision.q6_confidence.score is None:
                violations.append(PolicyViolation(
                    violation_id=f"TR-002-{decision.decision_id}",
                    severity="MEDIUM",
                    policy_section="transparency.confidence_disclosure",
                    description="Decision lacks confidence score",
                    decision_id=decision.decision_id,
                    remediation="Calculate and include confidence score",
                ))
            else:
                passed_checks.append("Confidence score disclosed")
        
        # ====================================================================
        # CHECK 3: User Agency
        # ====================================================================
        if self.policy.human_oversight.user_override_always_available:
            # Check that alternatives are provided
            if not decision.alternative_actions or len(decision.alternative_actions) == 0:
                warnings.append("No alternative actions provided - may limit user agency")
            else:
                passed_checks.append("Alternative actions provided for user choice")
        
        # ====================================================================
        # CHECK 4: Data Governance
        # ====================================================================
        if self.policy.data_governance.right_to_explanation:
            # Ensure all 7 questions are answered
            if all([
                decision.q1_what,
                decision.q2_when,
                decision.q3_severity,
                decision.q4_why,
                decision.q5_action,
                decision.q6_confidence,
                decision.q7_inaction,
            ]):
                passed_checks.append("All 7 questions answered (explainability)")
            else:
                violations.append(PolicyViolation(
                    violation_id=f"DG-001-{decision.decision_id}",
                    severity="HIGH",
                    policy_section="data_governance.right_to_explanation",
                    description="Incomplete decision - not all 7 questions answered",
                    decision_id=decision.decision_id,
                    remediation="Ensure all 7 questions have valid responses",
                ))
        
        # ====================================================================
        # CALCULATE COMPLIANCE SCORE
        # ====================================================================
        total_checks = len(passed_checks) + len(violations) + len(warnings)
        if total_checks > 0:
            compliance_score = len(passed_checks) / total_checks
        else:
            compliance_score = 1.0
        
        # Violations reduce score significantly
        for v in violations:
            if v.severity == "CRITICAL":
                compliance_score = max(0, compliance_score - 0.3)
            elif v.severity == "HIGH":
                compliance_score = max(0, compliance_score - 0.15)
            elif v.severity == "MEDIUM":
                compliance_score = max(0, compliance_score - 0.05)
        
        # ====================================================================
        # BUILD REPORT
        # ====================================================================
        compliant = len(violations) == 0
        
        if violations:
            self._violation_count += len(violations)
            logger.warning(
                "policy_violations_detected",
                decision_id=decision.decision_id,
                violation_count=len(violations),
                severities=[v.severity for v in violations],
            )
        
        logger.info(
            "policy_check_completed",
            decision_id=decision.decision_id,
            compliant=compliant,
            compliance_score=compliance_score,
            violations=len(violations),
            warnings=len(warnings),
            human_review_required=human_review_required,
        )
        
        return PolicyComplianceReport(
            decision_id=decision.decision_id,
            policy_version=self.policy.version,
            compliant=compliant,
            compliance_score=compliance_score,
            violations=violations,
            warnings=warnings,
            passed_checks=passed_checks,
            human_review_required=human_review_required,
            human_review_reason=human_review_reason,
            auto_execution_allowed=auto_execution_allowed,
        )
    
    def get_violation_stats(self) -> Dict[str, Any]:
        """Get violation statistics."""
        return {
            "total_violations": self._violation_count,
            "policy_version": self.policy.version,
        }


# ============================================================================
# FACTORY
# ============================================================================


_default_policy: Optional[GovernancePolicy] = None


def get_default_policy() -> GovernancePolicy:
    """Get the default governance policy (singleton)."""
    global _default_policy
    if _default_policy is None:
        _default_policy = GovernancePolicy()
    return _default_policy


def create_policy_enforcer(
    policy: Optional[GovernancePolicy] = None,
) -> PolicyEnforcer:
    """Create a policy enforcer with the given or default policy."""
    return PolicyEnforcer(policy=policy)
