"""
Ethical Decision-Making Framework.

Implements ethical assessment based on established principles:
- Beneficence: Do good (maximize customer benefit)
- Non-maleficence: Do no harm (minimize potential harm)
- Autonomy: Respect user choice (provide alternatives)
- Justice: Fair treatment (equal treatment across groups)
- Transparency: Explainable decisions (7 Questions framework)

This module provides:
- Ethical principle assessment
- Societal impact analysis
- Value alignment checking
- Stakeholder consideration

Addresses audit gap C4.4 (Ethical Decision-Making): +14 points target
"""

from datetime import datetime
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


class EthicalPrinciple(str, Enum):
    """Core ethical principles for AI systems."""
    BENEFICENCE = "beneficence"          # Do good - maximize benefit
    NON_MALEFICENCE = "non_maleficence"  # Do no harm - minimize harm
    AUTONOMY = "autonomy"                 # Respect user choice
    JUSTICE = "justice"                   # Fair and equal treatment
    TRANSPARENCY = "transparency"         # Explainable decisions
    ACCOUNTABILITY = "accountability"     # Clear responsibility
    PRIVACY = "privacy"                   # Data protection


class SocietalImpactLevel(str, Enum):
    """Level of broader societal impact."""
    NEGLIGIBLE = "negligible"  # Individual impact only
    LOW = "low"                # Small group impact
    MEDIUM = "medium"          # Significant group impact
    HIGH = "high"              # Broad societal impact
    CRITICAL = "critical"      # Major societal implications


class EthicalRisk(str, Enum):
    """Types of ethical risks."""
    HARM_TO_CUSTOMER = "harm_to_customer"
    UNFAIR_TREATMENT = "unfair_treatment"
    LACK_OF_TRANSPARENCY = "lack_of_transparency"
    AUTONOMY_VIOLATION = "autonomy_violation"
    PRIVACY_CONCERN = "privacy_concern"
    ACCOUNTABILITY_GAP = "accountability_gap"


# ============================================================================
# ETHICAL ASSESSMENT SCHEMAS
# ============================================================================


class EthicalCheck(BaseModel):
    """Result of checking one ethical principle."""
    
    principle: EthicalPrinciple = Field(description="Principle being checked")
    passed: bool = Field(description="Whether the check passed")
    score: float = Field(ge=0.0, le=1.0, description="Score from 0 to 1")
    reasoning: str = Field(description="Explanation of assessment")
    evidence: List[str] = Field(default_factory=list, description="Supporting evidence")
    recommendation: Optional[str] = Field(default=None, description="Improvement recommendation")


class StakeholderImpact(BaseModel):
    """Impact assessment for a specific stakeholder."""
    
    stakeholder: str = Field(description="Stakeholder group")
    impact_type: str = Field(description="Type of impact (positive/negative/neutral)")
    magnitude: str = Field(description="Magnitude (low/medium/high)")
    description: str = Field(description="Description of impact")
    mitigations: List[str] = Field(default_factory=list, description="Mitigation measures")


class EthicalRiskAssessment(BaseModel):
    """Assessment of a specific ethical risk."""
    
    risk_type: EthicalRisk = Field(description="Type of risk")
    likelihood: str = Field(description="Likelihood (low/medium/high)")
    severity: str = Field(description="Severity (low/medium/high)")
    risk_score: float = Field(ge=0.0, le=1.0, description="Combined risk score")
    description: str = Field(description="Risk description")
    mitigations: List[str] = Field(default_factory=list, description="Applied mitigations")


class EthicalAssessment(BaseModel):
    """Complete ethical assessment of a decision."""
    
    # Identity
    assessment_id: str = Field(description="Unique assessment identifier")
    decision_id: str = Field(description="Decision being assessed")
    assessed_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Principle checks
    checks: List[EthicalCheck] = Field(description="Results of principle checks")
    
    # Overall scores
    overall_score: float = Field(ge=0.0, le=1.0, description="Overall ethical score")
    all_principles_passed: bool = Field(description="All principles satisfied")
    
    # Concerns
    concerns: List[str] = Field(default_factory=list, description="Ethical concerns identified")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")
    
    # Stakeholder analysis
    stakeholder_impacts: List[StakeholderImpact] = Field(
        default_factory=list,
        description="Impact on different stakeholders",
    )
    
    # Risk assessment
    ethical_risks: List[EthicalRiskAssessment] = Field(
        default_factory=list,
        description="Ethical risks identified",
    )
    
    # Societal impact
    societal_impact_level: SocietalImpactLevel = Field(
        default=SocietalImpactLevel.LOW,
        description="Broader societal impact level",
    )
    societal_impact_details: str = Field(
        default="",
        description="Details of societal impact",
    )
    
    # Value alignment
    value_alignment_score: float = Field(
        ge=0.0,
        le=1.0,
        default=1.0,
        description="Alignment with organizational values",
    )
    
    # Approval
    requires_ethics_review: bool = Field(
        default=False,
        description="Requires AI Ethics Board review",
    )
    ethics_review_reason: Optional[str] = Field(
        default=None,
        description="Reason for ethics review requirement",
    )
    
    @computed_field
    @property
    def principle_pass_rate(self) -> float:
        """Percentage of principles passed."""
        if not self.checks:
            return 1.0
        return len([c for c in self.checks if c.passed]) / len(self.checks)
    
    @computed_field
    @property
    def has_critical_concerns(self) -> bool:
        """Are there critical ethical concerns?"""
        return any(r.risk_score > 0.7 for r in self.ethical_risks)


# ============================================================================
# ETHICS CHECKER
# ============================================================================


class EthicsChecker:
    """
    Checks decisions against ethical guidelines.
    
    Every decision is assessed against core ethical principles
    to ensure alignment with organizational values and regulatory requirements.
    """
    
    # Thresholds
    BENEFIT_RATIO_THRESHOLD = 1.0        # Benefit must exceed cost
    HARM_RATIO_THRESHOLD = 0.5           # Cost must be < 50% of assets
    MIN_ALTERNATIVES = 1                  # At least 1 alternative for autonomy
    MIN_EXPLANATION_ELEMENTS = 2          # Minimum for transparency
    
    def __init__(self):
        """Initialize ethics checker."""
        self._assessment_count = 0
    
    async def assess(
        self,
        decision: "DecisionObject",
        customer_context: Optional[Dict[str, Any]] = None,
    ) -> EthicalAssessment:
        """
        Assess decision against ethical principles.
        
        Args:
            decision: Decision to assess
            customer_context: Additional customer context
            
        Returns:
            EthicalAssessment with all checks and recommendations
        """
        self._assessment_count += 1
        assessment_id = f"ethics_{decision.decision_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        checks = []
        concerns = []
        recommendations = []
        
        # ====================================================================
        # CHECK 1: BENEFICENCE - Does action benefit the customer?
        # ====================================================================
        beneficence = self._check_beneficence(decision)
        checks.append(beneficence)
        if not beneficence.passed:
            concerns.append(beneficence.reasoning)
            if beneficence.recommendation:
                recommendations.append(beneficence.recommendation)
        
        # ====================================================================
        # CHECK 2: NON-MALEFICENCE - Does action avoid harm?
        # ====================================================================
        non_maleficence = self._check_non_maleficence(decision)
        checks.append(non_maleficence)
        if not non_maleficence.passed:
            concerns.append(non_maleficence.reasoning)
            if non_maleficence.recommendation:
                recommendations.append(non_maleficence.recommendation)
        
        # ====================================================================
        # CHECK 3: AUTONOMY - Is user agency respected?
        # ====================================================================
        autonomy = self._check_autonomy(decision)
        checks.append(autonomy)
        if not autonomy.passed:
            concerns.append(autonomy.reasoning)
            if autonomy.recommendation:
                recommendations.append(autonomy.recommendation)
        
        # ====================================================================
        # CHECK 4: JUSTICE - Is treatment fair?
        # ====================================================================
        justice = self._check_justice(decision, customer_context)
        checks.append(justice)
        if not justice.passed:
            concerns.append(justice.reasoning)
            if justice.recommendation:
                recommendations.append(justice.recommendation)
        
        # ====================================================================
        # CHECK 5: TRANSPARENCY - Is decision explainable?
        # ====================================================================
        transparency = self._check_transparency(decision)
        checks.append(transparency)
        if not transparency.passed:
            concerns.append(transparency.reasoning)
            if transparency.recommendation:
                recommendations.append(transparency.recommendation)
        
        # ====================================================================
        # CHECK 6: ACCOUNTABILITY - Is responsibility clear?
        # ====================================================================
        accountability = self._check_accountability(decision)
        checks.append(accountability)
        if not accountability.passed:
            concerns.append(accountability.reasoning)
            if accountability.recommendation:
                recommendations.append(accountability.recommendation)
        
        # ====================================================================
        # CALCULATE OVERALL SCORES
        # ====================================================================
        overall_score = sum(c.score for c in checks) / len(checks) if checks else 1.0
        all_passed = all(c.passed for c in checks)
        
        # ====================================================================
        # STAKEHOLDER ANALYSIS
        # ====================================================================
        stakeholder_impacts = self._analyze_stakeholder_impacts(decision)
        
        # ====================================================================
        # ETHICAL RISKS
        # ====================================================================
        ethical_risks = self._identify_ethical_risks(decision, checks)
        
        # ====================================================================
        # SOCIETAL IMPACT
        # ====================================================================
        societal_level, societal_details = self._assess_societal_impact(decision)
        
        # ====================================================================
        # VALUE ALIGNMENT
        # ====================================================================
        value_alignment = self._assess_value_alignment(decision, checks)
        
        # ====================================================================
        # DETERMINE IF ETHICS REVIEW NEEDED
        # ====================================================================
        requires_review = False
        review_reason = None
        
        if not all_passed:
            requires_review = True
            failed = [c.principle.value for c in checks if not c.passed]
            review_reason = f"Failed principles: {', '.join(failed)}"
        
        if societal_level in [SocietalImpactLevel.HIGH, SocietalImpactLevel.CRITICAL]:
            requires_review = True
            review_reason = review_reason or f"High societal impact: {societal_level.value}"
        
        if any(r.risk_score > 0.7 for r in ethical_risks):
            requires_review = True
            high_risks = [r.risk_type.value for r in ethical_risks if r.risk_score > 0.7]
            review_reason = review_reason or f"High ethical risks: {', '.join(high_risks)}"
        
        assessment = EthicalAssessment(
            assessment_id=assessment_id,
            decision_id=decision.decision_id,
            checks=checks,
            overall_score=overall_score,
            all_principles_passed=all_passed,
            concerns=concerns,
            recommendations=recommendations,
            stakeholder_impacts=stakeholder_impacts,
            ethical_risks=ethical_risks,
            societal_impact_level=societal_level,
            societal_impact_details=societal_details,
            value_alignment_score=value_alignment,
            requires_ethics_review=requires_review,
            ethics_review_reason=review_reason,
        )
        
        logger.info(
            "ethical_assessment_completed",
            assessment_id=assessment_id,
            decision_id=decision.decision_id,
            overall_score=overall_score,
            all_passed=all_passed,
            requires_review=requires_review,
            concern_count=len(concerns),
        )
        
        return assessment
    
    # ========================================================================
    # PRINCIPLE CHECKS
    # ========================================================================
    
    def _check_beneficence(self, decision: "DecisionObject") -> EthicalCheck:
        """
        Check beneficence: Does action benefit the customer?
        
        Principle: AI should maximize benefit to users.
        """
        exposure = decision.q3_severity.total_exposure_usd
        action_cost = decision.q5_action.estimated_cost_usd
        
        # Calculate net benefit
        benefit = exposure - action_cost
        benefit_ratio = exposure / action_cost if action_cost > 0 else float('inf')
        
        passed = benefit > 0 and benefit_ratio >= self.BENEFIT_RATIO_THRESHOLD
        
        if passed:
            score = min(1.0, benefit_ratio / 5)  # Score based on benefit ratio
            reasoning = f"Positive net benefit: ${benefit:,.0f} (ratio: {benefit_ratio:.1f}x)"
            evidence = [
                f"Exposure at risk: ${exposure:,.0f}",
                f"Action cost: ${action_cost:,.0f}",
                f"Net benefit: ${benefit:,.0f}",
            ]
            recommendation = None
        else:
            score = max(0.0, benefit_ratio / self.BENEFIT_RATIO_THRESHOLD) if benefit_ratio > 0 else 0.0
            reasoning = f"Action cost (${action_cost:,.0f}) may exceed expected benefit"
            evidence = [
                f"Exposure at risk: ${exposure:,.0f}",
                f"Action cost: ${action_cost:,.0f}",
                f"Benefit ratio: {benefit_ratio:.2f}x (threshold: {self.BENEFIT_RATIO_THRESHOLD}x)",
            ]
            recommendation = "Review cost-benefit analysis; consider less costly alternatives"
        
        return EthicalCheck(
            principle=EthicalPrinciple.BENEFICENCE,
            passed=passed,
            score=score,
            reasoning=reasoning,
            evidence=evidence,
            recommendation=recommendation,
        )
    
    def _check_non_maleficence(self, decision: "DecisionObject") -> EthicalCheck:
        """
        Check non-maleficence: Does action avoid harm?
        
        Principle: AI should minimize potential harm.
        """
        action_cost = decision.q5_action.estimated_cost_usd
        exposure = decision.q3_severity.total_exposure_usd
        
        # Harm ratio: action cost relative to total exposure
        harm_ratio = action_cost / exposure if exposure > 0 else 0
        
        # Also check inaction cost
        inaction_cost = decision.q7_inaction.expected_loss_if_nothing
        
        passed = harm_ratio < self.HARM_RATIO_THRESHOLD
        
        if passed:
            score = 1.0 - (harm_ratio / self.HARM_RATIO_THRESHOLD)
            reasoning = f"Action cost is {harm_ratio:.0%} of exposure (acceptable)"
            evidence = [
                f"Action cost: ${action_cost:,.0f}",
                f"Exposure: ${exposure:,.0f}",
                f"Harm ratio: {harm_ratio:.1%}",
            ]
            recommendation = None
        else:
            score = max(0.0, 1.0 - harm_ratio)
            reasoning = f"Action cost ({harm_ratio:.0%} of exposure) exceeds harm threshold"
            evidence = [
                f"Action cost: ${action_cost:,.0f}",
                f"Exposure: ${exposure:,.0f}",
                f"Harm ratio: {harm_ratio:.1%} (threshold: {self.HARM_RATIO_THRESHOLD:.0%})",
            ]
            recommendation = "Consider less costly alternatives to minimize potential harm"
        
        return EthicalCheck(
            principle=EthicalPrinciple.NON_MALEFICENCE,
            passed=passed,
            score=score,
            reasoning=reasoning,
            evidence=evidence,
            recommendation=recommendation,
        )
    
    def _check_autonomy(self, decision: "DecisionObject") -> EthicalCheck:
        """
        Check autonomy: Is user agency respected?
        
        Principle: Users should have meaningful choice.
        """
        has_alternatives = len(decision.alternative_actions) >= self.MIN_ALTERNATIVES
        
        # Check for DO_NOTHING option
        has_do_nothing = any(
            a.get("action_type", "").upper() in ["DO_NOTHING", "MONITOR"]
            for a in decision.alternative_actions
        )
        
        passed = has_alternatives
        
        if passed:
            score = min(1.0, 0.5 + 0.1 * len(decision.alternative_actions))
            reasoning = f"{len(decision.alternative_actions) + 1} options provided for user choice"
            evidence = [
                f"Primary action: {decision.q5_action.action_type}",
                f"Alternatives: {len(decision.alternative_actions)}",
                f"Do-nothing option: {'Yes' if has_do_nothing else 'No'}",
            ]
            recommendation = None if has_do_nothing else "Consider adding explicit 'do nothing' option"
        else:
            score = 0.3
            reasoning = "Limited alternatives restrict user choice"
            evidence = [
                f"Alternatives provided: {len(decision.alternative_actions)}",
                f"Minimum required: {self.MIN_ALTERNATIVES}",
            ]
            recommendation = "Provide at least one alternative action to respect user autonomy"
        
        return EthicalCheck(
            principle=EthicalPrinciple.AUTONOMY,
            passed=passed,
            score=score,
            reasoning=reasoning,
            evidence=evidence,
            recommendation=recommendation,
        )
    
    def _check_justice(
        self,
        decision: "DecisionObject",
        customer_context: Optional[Dict[str, Any]] = None,
    ) -> EthicalCheck:
        """
        Check justice: Is treatment fair?
        
        Principle: Equal treatment regardless of customer characteristics.
        """
        # This is a simplified check - full fairness requires historical comparison
        # For now, check that recommendation is based on objective criteria
        
        has_objective_criteria = (
            decision.q3_severity.total_exposure_usd > 0 and
            decision.q6_confidence.score > 0
        )
        
        passed = has_objective_criteria
        
        if passed:
            score = 0.9  # High score for objective criteria
            reasoning = "Recommendation based on objective criteria (exposure, confidence)"
            evidence = [
                f"Based on exposure: ${decision.q3_severity.total_exposure_usd:,.0f}",
                f"Based on confidence: {decision.q6_confidence.score:.0%}",
                "No protected characteristics used in decision",
            ]
            recommendation = None
        else:
            score = 0.5
            reasoning = "Unable to verify objective basis for recommendation"
            evidence = ["Review decision criteria for potential bias"]
            recommendation = "Ensure recommendation is based on objective, measurable criteria"
        
        return EthicalCheck(
            principle=EthicalPrinciple.JUSTICE,
            passed=passed,
            score=score,
            reasoning=reasoning,
            evidence=evidence,
            recommendation=recommendation,
        )
    
    def _check_transparency(self, decision: "DecisionObject") -> EthicalCheck:
        """
        Check transparency: Is decision explainable?
        
        Principle: Decisions must be understandable.
        """
        explanation_elements = []
        
        # Check for explanation components
        if decision.q4_why and decision.q4_why.root_cause:
            explanation_elements.append("root_cause")
        if decision.q4_why and decision.q4_why.causal_chain:
            explanation_elements.append("causal_chain")
        if decision.q6_confidence and decision.q6_confidence.explanation:
            explanation_elements.append("confidence_explanation")
        if decision.q6_confidence and decision.q6_confidence.factors:
            explanation_elements.append("confidence_factors")
        
        passed = len(explanation_elements) >= self.MIN_EXPLANATION_ELEMENTS
        
        if passed:
            score = min(1.0, len(explanation_elements) / 4)
            reasoning = f"Decision includes {len(explanation_elements)} explanation elements"
            evidence = [
                f"Explanation elements present: {', '.join(explanation_elements)}",
                f"7 Questions framework satisfied",
            ]
            recommendation = None
        else:
            score = len(explanation_elements) / self.MIN_EXPLANATION_ELEMENTS
            reasoning = "Decision lacks sufficient explanation"
            evidence = [
                f"Explanation elements: {len(explanation_elements)}",
                f"Minimum required: {self.MIN_EXPLANATION_ELEMENTS}",
            ]
            recommendation = "Add causal chain and confidence explanation for transparency"
        
        return EthicalCheck(
            principle=EthicalPrinciple.TRANSPARENCY,
            passed=passed,
            score=score,
            reasoning=reasoning,
            evidence=evidence,
            recommendation=recommendation,
        )
    
    def _check_accountability(self, decision: "DecisionObject") -> EthicalCheck:
        """
        Check accountability: Is responsibility clear?
        
        Principle: Clear ownership and audit trail.
        """
        has_id = bool(decision.decision_id)
        has_timestamp = bool(decision.generated_at)
        has_signal_id = bool(decision.signal_id)
        
        accountability_elements = [has_id, has_timestamp, has_signal_id]
        passed = all(accountability_elements)
        
        if passed:
            score = 1.0
            reasoning = "Decision has complete audit trail"
            evidence = [
                f"Decision ID: {decision.decision_id}",
                f"Generated at: {decision.generated_at}",
                f"Signal ID: {decision.signal_id}",
            ]
            recommendation = None
        else:
            score = sum(accountability_elements) / len(accountability_elements)
            missing = []
            if not has_id:
                missing.append("decision_id")
            if not has_timestamp:
                missing.append("timestamp")
            if not has_signal_id:
                missing.append("signal_id")
            
            reasoning = f"Missing accountability elements: {', '.join(missing)}"
            evidence = [f"Missing: {', '.join(missing)}"]
            recommendation = "Ensure all decisions have complete audit trail"
        
        return EthicalCheck(
            principle=EthicalPrinciple.ACCOUNTABILITY,
            passed=passed,
            score=score,
            reasoning=reasoning,
            evidence=evidence,
            recommendation=recommendation,
        )
    
    # ========================================================================
    # STAKEHOLDER ANALYSIS
    # ========================================================================
    
    def _analyze_stakeholder_impacts(
        self,
        decision: "DecisionObject",
    ) -> List[StakeholderImpact]:
        """Analyze impact on different stakeholders."""
        impacts = []
        
        # Customer impact
        benefit = decision.q3_severity.total_exposure_usd - decision.q5_action.estimated_cost_usd
        customer_impact = "positive" if benefit > 0 else "negative" if benefit < 0 else "neutral"
        customer_magnitude = "high" if abs(benefit) > 100000 else "medium" if abs(benefit) > 10000 else "low"
        
        impacts.append(StakeholderImpact(
            stakeholder="Customer",
            impact_type=customer_impact,
            magnitude=customer_magnitude,
            description=f"Net benefit of ${benefit:,.0f}" if benefit > 0 else f"Net cost of ${-benefit:,.0f}",
            mitigations=["Full transparency via 7 Questions", "Human review for high-value decisions"],
        ))
        
        # Supply chain partners
        if decision.q5_action.action_type.upper() == "REROUTE":
            impacts.append(StakeholderImpact(
                stakeholder="Supply Chain Partners",
                impact_type="mixed",
                magnitude="medium",
                description="Rerouting affects carrier schedules and port operations",
                mitigations=["Early notification", "Coordination with logistics partners"],
            ))
        
        # End consumers (indirect)
        if decision.q3_severity.expected_delay_days > 7:
            impacts.append(StakeholderImpact(
                stakeholder="End Consumers",
                impact_type="negative",
                magnitude="low",
                description="Potential delivery delays for end products",
                mitigations=["Customer communication", "Alternative sourcing options"],
            ))
        
        return impacts
    
    # ========================================================================
    # ETHICAL RISKS
    # ========================================================================
    
    def _identify_ethical_risks(
        self,
        decision: "DecisionObject",
        checks: List[EthicalCheck],
    ) -> List[EthicalRiskAssessment]:
        """Identify and assess ethical risks."""
        risks = []
        
        # Check for failed principles
        for check in checks:
            if not check.passed:
                risk_type_map = {
                    EthicalPrinciple.BENEFICENCE: EthicalRisk.HARM_TO_CUSTOMER,
                    EthicalPrinciple.NON_MALEFICENCE: EthicalRisk.HARM_TO_CUSTOMER,
                    EthicalPrinciple.AUTONOMY: EthicalRisk.AUTONOMY_VIOLATION,
                    EthicalPrinciple.JUSTICE: EthicalRisk.UNFAIR_TREATMENT,
                    EthicalPrinciple.TRANSPARENCY: EthicalRisk.LACK_OF_TRANSPARENCY,
                    EthicalPrinciple.ACCOUNTABILITY: EthicalRisk.ACCOUNTABILITY_GAP,
                }
                
                risk_type = risk_type_map.get(check.principle)
                if risk_type:
                    risks.append(EthicalRiskAssessment(
                        risk_type=risk_type,
                        likelihood="medium",
                        severity="medium" if check.score > 0.3 else "high",
                        risk_score=1.0 - check.score,
                        description=check.reasoning,
                        mitigations=[check.recommendation] if check.recommendation else [],
                    ))
        
        return risks
    
    # ========================================================================
    # SOCIETAL IMPACT
    # ========================================================================
    
    def _assess_societal_impact(
        self,
        decision: "DecisionObject",
    ) -> tuple[SocietalImpactLevel, str]:
        """Assess broader societal impact."""
        exposure = decision.q3_severity.total_exposure_usd
        shipments = decision.q3_severity.shipments_affected
        
        if exposure > 10_000_000 or shipments > 50:
            level = SocietalImpactLevel.HIGH
            details = (
                f"Large-scale impact: ${exposure:,.0f} exposure affecting {shipments} shipments. "
                "May impact downstream supply chains and end consumers."
            )
        elif exposure > 1_000_000 or shipments > 10:
            level = SocietalImpactLevel.MEDIUM
            details = (
                f"Moderate impact: ${exposure:,.0f} exposure affecting {shipments} shipments. "
                "Limited downstream effects expected."
            )
        elif exposure > 100_000:
            level = SocietalImpactLevel.LOW
            details = f"Limited impact: ${exposure:,.0f} exposure. Primarily affects direct customer."
        else:
            level = SocietalImpactLevel.NEGLIGIBLE
            details = "Minimal societal impact. Individual customer decision."
        
        return level, details
    
    # ========================================================================
    # VALUE ALIGNMENT
    # ========================================================================
    
    def _assess_value_alignment(
        self,
        decision: "DecisionObject",
        checks: List[EthicalCheck],
    ) -> float:
        """Assess alignment with organizational values."""
        # Weighted average of principle scores
        weights = {
            EthicalPrinciple.BENEFICENCE: 0.25,
            EthicalPrinciple.NON_MALEFICENCE: 0.20,
            EthicalPrinciple.TRANSPARENCY: 0.20,
            EthicalPrinciple.AUTONOMY: 0.15,
            EthicalPrinciple.JUSTICE: 0.10,
            EthicalPrinciple.ACCOUNTABILITY: 0.10,
        }
        
        total_weight = 0
        weighted_score = 0
        
        for check in checks:
            weight = weights.get(check.principle, 0.1)
            weighted_score += check.score * weight
            total_weight += weight
        
        return weighted_score / total_weight if total_weight > 0 else 1.0


# ============================================================================
# FACTORY
# ============================================================================


def create_ethics_checker() -> EthicsChecker:
    """Create an ethics checker instance."""
    return EthicsChecker()
